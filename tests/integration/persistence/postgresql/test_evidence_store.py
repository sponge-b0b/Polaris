from __future__ import annotations

import asyncio
import inspect

import pytest
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from polaris.application.evidence import (
    EvidenceIdempotencyConflict,
    EvidenceObservationStore,
    EvidencePersistenceUnavailable,
    EvidenceSuccessionConflict,
)
from polaris.domain.evidence import EvidenceObservationId
from polaris.infrastructure.persistence.postgresql import PostgresEvidenceStore
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_observation_command_receipts,
    evidence_observations,
)
from tests.evidence_support import (
    ACQUIRED_AT,
    MISSING_OBSERVATION_ID,
    OBSERVATION_ID,
    OBSERVED_AT,
    SECOND_OBSERVATION_ID,
    SECOND_OPERATION_ID,
    evidence_command,
    evidence_service,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store


def _store(
    target: PostgresTestTarget,
    store_type: type[PostgresEvidenceStore] = PostgresEvidenceStore,
):
    return postgres_store(target, store_type)


def test_observation_round_trips_across_process_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as (_, store):
            result = await evidence_service(store, OBSERVATION_ID).record(
                evidence_command()
            )
            assert result.observation_id == EvidenceObservationId(OBSERVATION_ID)

        async with _store(postgres_target) as (_, restarted):
            observation = await restarted.load_observation(result.observation_id)
            assert observation is not None
            assert observation.observation_id == result.observation_id
            assert observation.source.source_identity == "fred"
            assert observation.source.source_authority.startswith("Federal Reserve")
            assert observation.subject.subject_identity == "US:CPI"
            assert observation.observed_at == OBSERVED_AT
            assert observation.acquired_at == ACQUIRED_AT
            assert observation.effective_at == OBSERVED_AT
            assert observation.material.retained_representation == '{"value": 321.1}'
            assert observation.material.verification_reference == "sha256:cpi-2026-08"

    asyncio.run(scenario())


def test_exact_operation_retry_returns_existing_identity(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as (engine, store):
            service = evidence_service(
                store,
                OBSERVATION_ID,
                SECOND_OBSERVATION_ID,
            )
            first = await service.record(evidence_command())
            second = await service.record(evidence_command())
            assert second.replayed is True
            assert second.observation_id == first.observation_id
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (1, 1)

    asyncio.run(scenario())


def test_changed_request_reusing_operation_id_conflicts(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as (engine, store):
            service = evidence_service(store, OBSERVATION_ID)
            await service.record(evidence_command())
            with pytest.raises(EvidenceIdempotencyConflict):
                await service.record(
                    evidence_command(retained_representation='{"value": 999.0}')
                )
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (1, 1)

    asyncio.run(scenario())


def test_distinct_operations_preserve_equivalent_observations_as_distinct_acts(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as (engine, store):
            service = evidence_service(
                store,
                OBSERVATION_ID,
                SECOND_OBSERVATION_ID,
            )
            first = await service.record(evidence_command())
            second = await service.record(evidence_command(SECOND_OPERATION_ID))
            assert first.observation_id != second.observation_id
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (2, 2)

    asyncio.run(scenario())


def test_typed_observation_succession_requires_existing_predecessor(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as (engine, store):
            with pytest.raises(EvidenceSuccessionConflict):
                await evidence_service(store, OBSERVATION_ID).record(
                    evidence_command(
                        supersedes=EvidenceObservationId(MISSING_OBSERVATION_ID)
                    )
                )
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (0, 0)

            first = await evidence_service(store, OBSERVATION_ID).record(
                evidence_command()
            )
            second = await evidence_service(store, SECOND_OBSERVATION_ID).record(
                evidence_command(
                    SECOND_OPERATION_ID,
                    supersedes=first.observation_id,
                )
            )
            observation = await store.load_observation(second.observation_id)
            assert observation is not None
            assert observation.supersedes_observation_id == first.observation_id

    asyncio.run(scenario())


class _FailAfterObservationStore(PostgresEvidenceStore):
    def _write_completed(self, step: str) -> None:
        if step == "observation":
            raise RuntimeError("injected transaction failure")


def test_failure_after_observation_insert_rolls_back_semantic_write(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(
            postgres_target,
            _FailAfterObservationStore,
        ) as (engine, store):
            with pytest.raises(EvidencePersistenceUnavailable):
                await evidence_service(store, OBSERVATION_ID).record(evidence_command())
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (0, 0)

    asyncio.run(scenario())


def test_observation_and_receipt_rows_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        async with _store(postgres_target) as (engine, store):
            await evidence_service(store, OBSERVATION_ID).record(evidence_command())
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_observations).values(
                            source_authority="rewritten authority"
                        )
                    )

    asyncio.run(scenario())


def test_inward_evidence_port_exposes_no_database_types() -> None:
    for method_name in (
        "get_observation_receipt",
        "commit_observation",
        "load_observation",
    ):
        signature = str(
            inspect.signature(getattr(EvidenceObservationStore, method_name))
        )
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
        assert "postgres" not in signature.lower()
