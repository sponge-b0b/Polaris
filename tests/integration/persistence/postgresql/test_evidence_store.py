from __future__ import annotations

import asyncio
import inspect
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from polaris.application.evidence import (
    EvidenceIdempotencyConflict,
    EvidenceObservationService,
    EvidenceObservationStore,
    EvidencePersistenceUnavailable,
    EvidenceSuccessionConflict,
    RecordEvidenceObservationCommand,
)
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceStore,
    create_postgres_engine,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_observation_command_receipts,
    evidence_observations,
)

from .conftest import PostgresTestTarget, postgres_row_counts

OPERATION_ID = UUID("00000000-0000-4000-8000-000000000301")
SECOND_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000302")
OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000303")
SECOND_OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000304")
MISSING_OBSERVATION_ID = UUID("00000000-0000-4000-8000-000000000305")
OBSERVED_AT = datetime(2026, 9, 29, 15, 0, tzinfo=UTC)
ACQUIRED_AT = datetime(2026, 9, 29, 15, 1, tzinfo=UTC)
COMMITTED_AT = datetime(2026, 9, 29, 15, 2, tzinfo=UTC)


def _command(
    operation_id: UUID = OPERATION_ID,
    *,
    supersedes: EvidenceObservationId | None = None,
) -> RecordEvidenceObservationCommand:
    return RecordEvidenceObservationCommand(
        operation_id=OperationId(operation_id),
        source=EvidenceSourceProvenance(
            "fred",
            "series:CPIAUCSL:2026-08",
            "Federal Reserve Bank of St. Louis / source publisher",
        ),
        subject=EvidenceSubjectReference("US:CPI", "2026-08"),
        observed_at=OBSERVED_AT,
        acquired_at=ACQUIRED_AT,
        effective_at=OBSERVED_AT,
        material=EvidenceObservationMaterial(
            retained_representation='{"value": 321.1}',
            verification_reference="sha256:cpi-2026-08",
        ),
        supersedes_observation_id=supersedes,
    )


def _service(
    store: PostgresEvidenceStore,
    *identities: UUID,
) -> EvidenceObservationService:
    values = iter(identities)
    return EvidenceObservationService(
        store=store,
        now=lambda: COMMITTED_AT,
        new_uuid=lambda: next(values),
    )


def test_observation_round_trips_across_process_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresEvidenceStore(engine)
        result = await _service(store, OBSERVATION_ID).record(_command())
        assert result.observation_id == EvidenceObservationId(OBSERVATION_ID)
        await engine.dispose()

        restarted_engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        restarted = PostgresEvidenceStore(restarted_engine)
        try:
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
            assert (
                observation.material.verification_reference
                == "sha256:cpi-2026-08"
            )
        finally:
            await restarted_engine.dispose()

    asyncio.run(scenario())


def test_exact_operation_retry_returns_existing_identity(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresEvidenceStore(engine)
        identities = iter((OBSERVATION_ID, SECOND_OBSERVATION_ID))
        service = EvidenceObservationService(
            store=store,
            now=lambda: COMMITTED_AT,
            new_uuid=lambda: next(identities),
        )
        try:
            first = await service.record(_command())
            second = await service.record(_command())
            assert second.replayed is True
            assert second.observation_id == first.observation_id
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (1, 1)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_changed_request_reusing_operation_id_conflicts(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresEvidenceStore(engine)
        service = _service(store, OBSERVATION_ID)
        try:
            await service.record(_command())
            changed = replace(
                _command(),
                material=EvidenceObservationMaterial(
                    retained_representation='{"value": 999.0}'
                ),
            )
            with pytest.raises(EvidenceIdempotencyConflict):
                await service.record(changed)
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (1, 1)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_distinct_operations_preserve_equivalent_observations_as_distinct_acts(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresEvidenceStore(engine)
        service = _service(store, OBSERVATION_ID, SECOND_OBSERVATION_ID)
        try:
            first = await service.record(_command())
            second = await service.record(_command(SECOND_OPERATION_ID))
            assert first.observation_id != second.observation_id
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (2, 2)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_typed_observation_succession_requires_existing_predecessor(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresEvidenceStore(engine)
        try:
            with pytest.raises(EvidenceSuccessionConflict):
                await _service(store, OBSERVATION_ID).record(
                    _command(
                        supersedes=EvidenceObservationId(MISSING_OBSERVATION_ID)
                    )
                )
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (0, 0)

            first = await _service(store, OBSERVATION_ID).record(_command())
            second = await _service(store, SECOND_OBSERVATION_ID).record(
                _command(
                    SECOND_OPERATION_ID,
                    supersedes=first.observation_id,
                )
            )
            observation = await store.load_observation(second.observation_id)
            assert observation is not None
            assert observation.supersedes_observation_id == first.observation_id
        finally:
            await engine.dispose()

    asyncio.run(scenario())


class _FailAfterObservationStore(PostgresEvidenceStore):
    def _write_completed(self, step: str) -> None:
        if step == "observation":
            raise RuntimeError("injected transaction failure")


def test_failure_after_observation_insert_rolls_back_semantic_write(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = _FailAfterObservationStore(engine)
        try:
            with pytest.raises(EvidencePersistenceUnavailable):
                await _service(store, OBSERVATION_ID).record(_command())
            assert await postgres_row_counts(
                engine,
                evidence_observations,
                evidence_observation_command_receipts,
            ) == (0, 0)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_observation_and_receipt_rows_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        engine = create_postgres_engine(
            postgres_target.database_url,
            schema=postgres_target.schema,
        )
        store = PostgresEvidenceStore(engine)
        await _service(store, OBSERVATION_ID).record(_command())
        try:
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_observations).values(
                            source_authority="rewritten authority"
                        )
                    )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_inward_evidence_port_exposes_no_database_types() -> None:
    for method_name in (
        "get_observation_receipt",
        "commit_observation",
        "load_observation",
    ):
        signature = str(inspect.signature(getattr(EvidenceObservationStore, method_name)))
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
        assert "postgres" not in signature.lower()
