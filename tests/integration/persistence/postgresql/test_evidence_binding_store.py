from __future__ import annotations

import asyncio
import inspect
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from polaris.application.evidence import (
    EvidenceBindingObservationReferenceConflict,
    EvidenceBindingResult,
    EvidenceBindingStore,
    EvidencePersistenceUnavailable,
    EvidenceRequirementVersionAppended,
    RecordEvidenceBindingCommand,
)
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceRole,
)
from polaris.domain.evidence.observations import EvidenceBindingId
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_binding_command_receipts,
    evidence_bindings,
)
from tests.binding_support import (
    BINDING_EFFECTIVE_AT,
    BINDING_ID,
    SECOND_BINDING_ID,
    SECOND_BINDING_OPERATION_ID,
    SECOND_TARGET_ID,
    binding_command,
    binding_service,
)
from tests.configuration_support import requirement_version
from tests.evidence_support import (
    OBSERVATION_ID,
    evidence_command,
    evidence_service,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store


async def _seed_observation(target: PostgresTestTarget) -> None:
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        await evidence_service(store, OBSERVATION_ID).record(evidence_command())


async def _seed_requirement(target: PostgresTestTarget) -> None:
    async with postgres_store(target, PostgresEvidenceRequirementStore) as (_, store):
        outcome = await store.append_requirement_version(requirement_version())
        assert isinstance(outcome, EvidenceRequirementVersionAppended)


async def _assert_binding_rows(
    target: PostgresTestTarget,
    expected: tuple[int, int],
) -> None:
    async with postgres_store(target, PostgresEvidenceBindingStore) as (engine, _):
        assert (
            await postgres_row_counts(
                engine,
                evidence_bindings,
                evidence_binding_command_receipts,
            )
            == expected
        )


async def _record_binding(
    target: PostgresTestTarget,
    *,
    identity: UUID = BINDING_ID,
    command: RecordEvidenceBindingCommand | None = None,
) -> EvidenceBindingResult:
    async with postgres_store(target, PostgresEvidenceBindingStore) as (_, store):
        return await binding_service(store, identity).record(
            command or binding_command()
        )


async def _record_binding_pair(
    target: PostgresTestTarget,
    *,
    second_command: RecordEvidenceBindingCommand | None = None,
) -> tuple[EvidenceBindingResult, EvidenceBindingResult]:
    first = await _record_binding(target)
    second = await _record_binding(
        target,
        identity=SECOND_BINDING_ID,
        command=second_command,
    )
    return first, second


async def _record_and_reload_binding(
    target: PostgresTestTarget,
    *,
    command: RecordEvidenceBindingCommand,
) -> EvidenceBinding:
    result = await _record_binding(target, command=command)
    async with postgres_store(
        target,
        PostgresEvidenceBindingStore,
    ) as (_, restarted):
        binding = await restarted.load_binding(result.binding_id)

    assert binding is not None
    return binding


def test_binding_round_trips_across_restart_with_exact_contract(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_requirement(postgres_target)

        binding = await _record_and_reload_binding(
            postgres_target,
            command=binding_command(with_freshness=True),
        )
        assert binding.binding_id == EvidenceBindingId(BINDING_ID)
        assert binding.observation_id.value == OBSERVATION_ID
        assert binding.role is EvidenceRole.SUPPORTING
        assert binding.availability is EvidenceAvailability.AVAILABLE
        assert binding.materially_used is True
        assert binding.material_qualification is not None
        assert binding.material_qualification.statement == "decision-grade source"
        assert binding.freshness_authority is not None
        assert binding.freshness_basis is not None
        assert binding.freshness_basis.reference == "observation:market-price:SPY"

    asyncio.run(scenario())


def test_historical_unknown_availability_round_trips_without_material_use(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        binding = await _record_and_reload_binding(
            postgres_target,
            command=binding_command(
                availability=EvidenceAvailability.UNKNOWN,
                materially_used=False,
            ),
        )
        assert binding.availability is EvidenceAvailability.UNKNOWN
        assert binding.materially_used is False
        assert binding.effective_at == BINDING_EFFECTIVE_AT

    asyncio.run(scenario())


def test_exact_retry_returns_existing_binding_identity(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        first, second = await _record_binding_pair(postgres_target)

        assert second.replayed is True
        assert second.binding_id == first.binding_id
        await _assert_binding_rows(postgres_target, (1, 1))

    asyncio.run(scenario())


def test_distinct_operations_preserve_duplicate_endpoint_tuple(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        first, second = await _record_binding_pair(
            postgres_target,
            second_command=binding_command(SECOND_BINDING_OPERATION_ID),
        )

        assert first.binding_id != second.binding_id
        await _assert_binding_rows(postgres_target, (2, 2))

    asyncio.run(scenario())


def test_missing_observation_rejects_binding_without_partial_write(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        with pytest.raises(EvidenceBindingObservationReferenceConflict):
            await _record_binding(postgres_target)
        await _assert_binding_rows(postgres_target, (0, 0))

    asyncio.run(scenario())


class _FailAfterBindingStore(PostgresEvidenceBindingStore):
    def _write_completed(self, step: str) -> None:
        if step == "binding":
            raise RuntimeError("injected binding transaction failure")


def test_failure_after_binding_insert_rolls_back_binding_and_receipt(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        async with postgres_store(
            postgres_target,
            _FailAfterBindingStore,
        ) as (_, store):
            with pytest.raises(EvidencePersistenceUnavailable):
                await binding_service(store, BINDING_ID).record(binding_command())
        await _assert_binding_rows(postgres_target, (0, 0))

    asyncio.run(scenario())


def test_binding_rows_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _record_binding(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceBindingStore,
        ) as (engine, _):
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_bindings).values(target_id=SECOND_TARGET_ID)
                    )

    asyncio.run(scenario())


def test_inward_binding_port_exposes_no_database_types() -> None:
    for method_name in (
        "get_binding_receipt",
        "commit_binding",
        "load_binding",
    ):
        signature = str(inspect.signature(getattr(EvidenceBindingStore, method_name)))
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
        assert "postgres" not in signature.lower()
