from __future__ import annotations

import asyncio
import inspect
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from polaris.application.evidence import (
    EvidenceCorrectionHistoryConflict,
    EvidenceCorrectionService,
    EvidenceCorrectionStore,
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
    EvidenceRequirementResolver,
    EvidenceRequirementVersionAppended,
    EvidenceSufficiencyBasis,
    RecordEvidenceObservationCorrectionCommand,
)
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceObservationMaterial,
)
from polaris.domain.evidence.sufficiency import EvidenceBindingInterpretationState
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceCorrectionStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
    PostgresEvidenceSufficiencyStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_correction_command_receipts,
    evidence_correction_identities,
    evidence_observation_corrections,
    evidence_support_versions,
)
from tests.binding_support import BINDING_ID, binding_command, binding_service
from tests.configuration_support import requirement_key, requirement_version
from tests.evidence_support import (
    OBSERVATION_ID,
    SECOND_OBSERVATION_ID,
    SECOND_OPERATION_ID,
    evidence_command,
    evidence_service,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store

CORRECTION_RECORDED_AT = datetime(2026, 9, 29, 14, 10, tzinfo=UTC)
OBSERVATION_CORRECTION_ID = UUID("00000000-0000-4000-8000-000000000a01")
RETRACTION_ID = UUID("00000000-0000-4000-8000-000000000a04")
MISSING_CORRECTION_ID = UUID("00000000-0000-4000-8000-000000000a02")
OBSERVATION_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000a11")
RETRACTION_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000a14")


def _correction_service(
    store: EvidenceCorrectionStore,
    *identities: UUID,
) -> EvidenceCorrectionService:
    values = iter(identities)
    return EvidenceCorrectionService(
        store=store,
        now=lambda: CORRECTION_RECORDED_AT,
        new_uuid=lambda: next(values),
    )


async def _seed_observation(target: PostgresTestTarget) -> None:
    key = requirement_key()
    assert key.subject is not None
    command = replace(evidence_command(), subject=key.subject)
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        await evidence_service(store, OBSERVATION_ID).record(command)


async def _seed_binding(target: PostgresTestTarget) -> None:
    async with postgres_store(target, PostgresEvidenceRequirementStore) as (_, store):
        outcome = await store.append_requirement_version(requirement_version())
        assert isinstance(outcome, EvidenceRequirementVersionAppended)
    async with postgres_store(target, PostgresEvidenceBindingStore) as (engine, store):
        await binding_service(
            store,
            BINDING_ID,
            requirements=EvidenceRequirementResolver(
                PostgresEvidenceRequirementStore(engine)
            ),
        ).record(binding_command())


async def _load_observation_only(
    target: PostgresTestTarget,
) -> EvidenceObservation:
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        observation = await store.load_observation(
            EvidenceObservationId(OBSERVATION_ID)
        )
    assert observation is not None
    return observation


async def _seed_and_load_observation(
    target: PostgresTestTarget,
) -> EvidenceObservation:
    await _seed_observation(target)
    return await _load_observation_only(target)


def _observation_correction_command(
    observation: EvidenceObservation,
    *,
    operation_id: UUID = OBSERVATION_OPERATION_ID,
    target: EvidenceObservationId | EvidenceCorrectionId | None = None,
    effect: EvidenceCorrectionEffect = EvidenceCorrectionEffect.RETRACT,
    basis: str = "retraction",
    effective_minutes_before_recording: int = 1,
    replacement: EvidenceObservation | None = None,
) -> RecordEvidenceObservationCorrectionCommand:
    return RecordEvidenceObservationCorrectionCommand(
        OperationId(operation_id),
        observation.observation_id,
        target or observation.observation_id,
        effect,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis(basis),
        CORRECTION_RECORDED_AT - timedelta(minutes=effective_minutes_before_recording),
        replacement,
    )


def test_observation_revision_round_trip_after_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: revision and restoration each construct their own
        # observed assertion so one shared fixture cannot make both proofs agree.
        # arid: disable
        observation = await _seed_and_load_observation(postgres_target)
        revised = replace(
            observation,
            material=EvidenceObservationMaterial(
                retained_representation='{"value": 321.2}',
                verification_reference="sha256:corrected-cpi-2026-08",
            ),
        )
        # arid: enable
        command = _observation_correction_command(
            observation,
            effect=EvidenceCorrectionEffect.REVISE,
            basis="publisher correction",
            effective_minutes_before_recording=3,
            replacement=revised,
        )
        # duplicate-code: this restart round trip owns a distinct store lifetime
        # from retry and basis-invalidating tests.
        # arid: disable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, store):
            # arid: enable
            result = await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                command
            )
        # duplicate-code: reopening the store is the independent restart
        # falsifier, separate from recursive restoration's restart proof.
        # arid: disable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, restarted):
            # arid: enable
            interpreted = await _correction_service(restarted).inspect_observation(
                observation.observation_id,
                effective_at=CORRECTION_RECORDED_AT,
                known_at=CORRECTION_RECORDED_AT,
            )
        assert result.correction_id == EvidenceCorrectionId(OBSERVATION_CORRECTION_ID)
        assert interpreted.state is EvidenceInterpretationState.DETERMINATE
        assert interpreted.assertions == frozenset({revised})
        assert interpreted.fact_support == frozenset(
            {
                observation.observation_id,
                EvidenceCorrectionId(OBSERVATION_CORRECTION_ID),
            }
        )

    asyncio.run(scenario())


def test_corrected_future_acquisition_uses_immutable_commit_for_knowledge_cutoff(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        command = replace(
            evidence_command(),
            acquired_at=CORRECTION_RECORDED_AT + timedelta(days=2),
        )
        async with postgres_store(postgres_target, PostgresEvidenceStore) as (_, store):
            await evidence_service(store, OBSERVATION_ID).record(command)
        observation = await _load_observation_only(postgres_target)
        revised = replace(
            observation,
            acquired_at=CORRECTION_RECORDED_AT - timedelta(minutes=9),
        )
        # This corrected acquisition case owns its commit and historical reads.
        # arid: disable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, store):
            service = _correction_service(store, OBSERVATION_CORRECTION_ID)
            await service.record(
                _observation_correction_command(
                    observation,
                    effect=EvidenceCorrectionEffect.REVISE,
                    basis="correct acquisition timestamp",
                    replacement=revised,
                )
            )
            before_commit = await service.inspect_observation(
                observation.observation_id,
                effective_at=CORRECTION_RECORDED_AT,
                known_at=observation.observed_at,
            )
            corrected = await service.inspect_observation(
                observation.observation_id,
                effective_at=CORRECTION_RECORDED_AT,
                known_at=CORRECTION_RECORDED_AT,
            )
        # arid: enable
        assert before_commit.state is EvidenceInterpretationState.NOT_KNOWN
        assert corrected.state is EvidenceInterpretationState.DETERMINATE
        assert corrected.assertions == frozenset({revised})
        assert corrected.fact_support == frozenset(
            {
                observation.observation_id,
                EvidenceCorrectionId(OBSERVATION_CORRECTION_ID),
            }
        )

    asyncio.run(scenario())


def test_recursive_restoration_and_exact_retry_survive_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        observation = await _seed_and_load_observation(postgres_target)
        revised = replace(
            observation,
            material=EvidenceObservationMaterial(
                retained_representation='{"value": 321.2}'
            ),
        )
        revision_command = _observation_correction_command(
            observation,
            effect=EvidenceCorrectionEffect.REVISE,
            basis="publisher correction",
            effective_minutes_before_recording=2,
            replacement=revised,
        )
        # arid: disable
        # The recursive-chain proof owns a separate transaction boundary from
        # the multi-family and cross-family falsifiers.
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, store):
            # arid: enable
            revision_service = _correction_service(store, OBSERVATION_CORRECTION_ID)
            first = await revision_service.record(revision_command)
            replay = await revision_service.record(revision_command)
            assert replay == replace(first, replayed=True)
            await _correction_service(store, RETRACTION_ID).record(
                RecordEvidenceObservationCorrectionCommand(
                    OperationId(RETRACTION_OPERATION_ID),
                    observation.observation_id,
                    first.correction_id,
                    EvidenceCorrectionEffect.RETRACT,
                    UnknownActorAttribution(),
                    EvidenceCorrectionBasis("publisher withdrew its correction"),
                    CORRECTION_RECORDED_AT - timedelta(minutes=1),
                )
            )

        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, restarted):
            interpretation = await _correction_service(restarted).inspect_observation(
                observation.observation_id,
                effective_at=CORRECTION_RECORDED_AT,
                known_at=CORRECTION_RECORDED_AT,
            )
        assert interpretation.state is EvidenceInterpretationState.DETERMINATE
        assert interpretation.assertions == frozenset({observation})
        assert interpretation.fact_support == frozenset(
            {
                observation.observation_id,
                EvidenceCorrectionId(OBSERVATION_CORRECTION_ID),
                EvidenceCorrectionId(RETRACTION_ID),
            }
        )

    asyncio.run(scenario())


def test_missing_ancestry_rejects_without_partial_write(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # arid: disable
        # Keep the injected-rollback transaction and its zero-row assertions
        # independent so a shared helper cannot mask partial-write behavior.
        observation = await _seed_and_load_observation(postgres_target)
        command = _observation_correction_command(
            observation,
            target=EvidenceCorrectionId(MISSING_CORRECTION_ID),
            basis="invalid missing target",
        )
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (engine, store):
            with pytest.raises(EvidenceCorrectionHistoryConflict, match="ancestry"):
                await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                    command
                )
            counts = await postgres_row_counts(
                engine,
                evidence_correction_identities,
                evidence_observation_corrections,
                evidence_correction_command_receipts,
            )
        assert counts == (0, 0, 0)
        # arid: enable

    asyncio.run(scenario())


@pytest.mark.parametrize("predecessor_exists", [False, True])
def test_revision_rejects_invalid_succession_predecessor_without_partial_write(
    postgres_target: PostgresTestTarget,
    predecessor_exists: bool,
) -> None:
    async def scenario() -> None:
        observation = await _seed_and_load_observation(postgres_target)
        predecessor_id = (
            SECOND_OBSERVATION_ID if predecessor_exists else MISSING_CORRECTION_ID
        )
        if predecessor_exists:
            async with postgres_store(postgres_target, PostgresEvidenceStore) as (
                _,
                store,
            ):
                await evidence_service(store, SECOND_OBSERVATION_ID).record(
                    evidence_command(SECOND_OPERATION_ID)
                )
        revised = replace(
            observation,
            supersedes_observation_id=EvidenceObservationId(predecessor_id),
        )
        command = _observation_correction_command(
            observation,
            effect=EvidenceCorrectionEffect.REVISE,
            basis="invalid predecessor",
            replacement=revised,
        )
        # This succession rejection owns an independent transaction boundary.
        # arid: disable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (engine, store):
            with pytest.raises(
                EvidenceCorrectionHistoryConflict, match="predecessor|earlier"
            ):
                await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                    command
                )
            counts = await postgres_row_counts(
                engine,
                evidence_correction_identities,
                evidence_observation_corrections,
                evidence_correction_command_receipts,
            )
        # arid: enable
        assert counts == (0, 0, 0)

    asyncio.run(scenario())


class _FailAfterCorrectionStore(PostgresEvidenceCorrectionStore):
    def _write_completed(self, step: str) -> None:
        if step == "correction":
            raise RuntimeError("injected correction transaction failure")


class _FailAfterSupportVersionStore(PostgresEvidenceCorrectionStore):
    def _write_completed(self, step: str) -> None:
        if step == "support_version":
            raise RuntimeError("injected support version transaction failure")


def test_failure_after_correction_insert_rolls_back_identity_and_history(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: identity rollback owns its own failure transaction;
        # sharing it with epoch rollback could hide partial writes.
        # arid: disable
        observation = await _seed_and_load_observation(postgres_target)
        command = _observation_correction_command(observation)
        async with postgres_store(
            postgres_target,
            _FailAfterCorrectionStore,
        ) as (engine, store):
            with pytest.raises(EvidencePersistenceUnavailable):
                await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                    command
                )
            counts = await postgres_row_counts(
                engine,
                evidence_correction_identities,
                evidence_observation_corrections,
                evidence_correction_command_receipts,
            )
        assert counts == (0, 0, 0)
        # arid: enable

    asyncio.run(scenario())


def test_failure_after_support_version_insert_rolls_back_every_correction_fact(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: epoch rollback seeds its own affected binding
        # so its transaction proof is independent of other tests.
        # arid: disable
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        observation = await _load_observation_only(postgres_target)
        # arid: enable
        # duplicate-code: correction and binding epoch rollback are separate
        # adapter transactions and must retain independent failure injection.
        # arid: disable
        async with postgres_store(
            postgres_target,
            _FailAfterSupportVersionStore,
        ) as (engine, store):
            with pytest.raises(EvidencePersistenceUnavailable):
                # arid: enable
                await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                    _observation_correction_command(observation)
                )
            # duplicate-code: epoch rollback checks its own support row;
            # a shared assertion could miss that partial write.
            # arid: disable
            counts = await postgres_row_counts(
                engine,
                evidence_correction_identities,
                evidence_observation_corrections,
                evidence_correction_command_receipts,
                evidence_support_versions,
            )
        assert counts == (0, 0, 0, 1)
        # arid: enable

    asyncio.run(scenario())


def test_future_effective_correction_does_not_advance_current_support_epoch(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        observation = await _load_observation_only(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (engine, store):
            await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                _observation_correction_command(
                    observation,
                    effective_minutes_before_recording=-1,
                )
            )
            counts = await postgres_row_counts(engine, evidence_support_versions)
            interpretation = await _correction_service(store).inspect_observation(
                observation.observation_id,
                effective_at=CORRECTION_RECORDED_AT,
                known_at=CORRECTION_RECORDED_AT,
            )
        assert counts == (1,)
        assert interpretation.state is EvidenceInterpretationState.DETERMINATE
        assert interpretation.assertions == frozenset({observation})

    asyncio.run(scenario())


def test_correction_rows_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: immutability uses a separate committed fact;
        # sharing rollback setup could conflate write and update behavior.
        # arid: disable
        observation = await _seed_and_load_observation(postgres_target)
        command = _observation_correction_command(observation)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (engine, store):
            # arid: enable
            await _correction_service(store, OBSERVATION_CORRECTION_ID).record(command)
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_observation_corrections).values(
                            basis_reference="rewritten"
                        )
                    )

    asyncio.run(scenario())


def test_changed_semantic_retry_is_rejected(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        observation = await _seed_and_load_observation(postgres_target)
        command = _observation_correction_command(observation)
        # duplicate-code: changed-request reuse is proved in its own transaction
        # so shared setup cannot conceal receipt behavior.
        # arid: disable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, store):
            # arid: enable
            service = _correction_service(store, OBSERVATION_CORRECTION_ID)
            await service.record(command)
            with pytest.raises(EvidenceIdempotencyConflict):
                await service.record(
                    replace(
                        command,
                        basis=EvidenceCorrectionBasis("changed retraction"),
                    )
                )

    asyncio.run(scenario())


def test_inward_correction_port_exposes_no_database_types() -> None:
    for method_name in (
        "get_correction_receipt",
        "commit_correction",
        "load_observation_history",
    ):
        signature = str(
            inspect.signature(getattr(EvidenceCorrectionStore, method_name))
        )
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
        assert "postgres" not in signature.lower()


def test_observation_retraction_invalidates_sufficiency_basis_and_epoch(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: the current-basis proof seeds its own bound observation.
        # arid: disable
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        observation = await _load_observation_only(postgres_target)
        # arid: enable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, store):
            await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                _observation_correction_command(observation)
            )
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (_, store):
            basis = await store.load_sufficiency_basis(
                requirement_key(),
                effective_at=CORRECTION_RECORDED_AT,
                known_at=CORRECTION_RECORDED_AT,
            )
        assert isinstance(basis, EvidenceSufficiencyBasis)
        assert (
            basis.interpretations[0].state
            is EvidenceBindingInterpretationState.WITHDRAWN
        )
        assert basis.support_version.value == 2
        assert basis.guards.corrections.correction_ids == frozenset(
            {
                EvidenceCorrectionId(OBSERVATION_CORRECTION_ID),
            }
        )

    asyncio.run(scenario())


def test_corrected_observed_time_reaches_sufficiency_basis(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        key = requirement_key()
        assert key.subject is not None
        original_command = replace(
            evidence_command(),
            subject=key.subject,
            observed_at=CORRECTION_RECORDED_AT + timedelta(days=2),
            effective_at=CORRECTION_RECORDED_AT + timedelta(days=2),
        )
        async with postgres_store(postgres_target, PostgresEvidenceStore) as (_, store):
            await evidence_service(store, OBSERVATION_ID).record(original_command)
        await _seed_binding(postgres_target)
        observation = await _load_observation_only(postgres_target)
        revised = replace(
            observation,
            observed_at=CORRECTION_RECORDED_AT - timedelta(minutes=10),
            effective_at=CORRECTION_RECORDED_AT - timedelta(minutes=10),
        )
        # This corrected-time consumer proof owns independent store lifetimes.
        # arid: disable
        async with postgres_store(
            postgres_target,
            PostgresEvidenceCorrectionStore,
        ) as (_, store):
            await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                _observation_correction_command(
                    observation,
                    effect=EvidenceCorrectionEffect.REVISE,
                    basis="correct observed timestamp",
                    replacement=revised,
                )
            )
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (_, store):
            basis = await store.load_sufficiency_basis(
                key,
                effective_at=CORRECTION_RECORDED_AT,
                known_at=CORRECTION_RECORDED_AT,
            )
        # arid: enable
        assert isinstance(basis, EvidenceSufficiencyBasis)
        assert basis.interpretations[0].fact_support == frozenset(
            {
                observation.observation_id,
                EvidenceCorrectionId(OBSERVATION_CORRECTION_ID),
                basis.interpretations[0].binding.binding_id,
            }
        )

    asyncio.run(scenario())
