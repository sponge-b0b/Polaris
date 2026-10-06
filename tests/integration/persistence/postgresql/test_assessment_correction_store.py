from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from polaris.application.evidence import (
    EvidenceCorrectionBasisConflict,
    EvidenceCorrectionCommit,
    EvidenceCorrectionHistoryConflict,
    EvidenceCorrectionSemanticRequest,
    EvidenceCorrectionService,
    EvidenceCorrectionStaleBasis,
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
    EvidenceRequirementResolver,
    EvidenceRequirementVersionAppended,
    EvidenceSufficiencyService,
    RecordEvidenceAssessmentCorrectionCommand,
    RecordEvidenceSufficiencyAssessmentCommand,
)
from polaris.domain.actors import (
    ActorId,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.configuration import EvidenceRequirementPredecessorEffect
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceAssessmentCorrection,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    EvidenceSufficiencyAssessmentId,
)
from polaris.domain.evidence.sufficiency import EvidenceSufficiencyResult
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceCorrectionStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
    PostgresEvidenceSufficiencyStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_assessment_corrections,
    evidence_correction_command_receipts,
    evidence_correction_identities,
    evidence_sufficiency_assessments,
    evidence_support_versions,
)
from polaris.infrastructure.persistence.postgresql.sufficiency_codec import (
    sufficiency_assessment_values,
)
from tests.binding_support import BINDING_ID, binding_command, binding_service
from tests.configuration_support import (
    ROOT_VERSION_ID,
    SECOND_VERSION_ID,
    requirement_key,
    requirement_version,
)
from tests.evidence_support import OBSERVATION_ID, evidence_command, evidence_service
from tests.sufficiency_support import derived_assessment

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store

ROOT_UUID = UUID("60000000-0000-4000-8000-000000000001")
ROOT_OPERATION = UUID("60000000-0000-4000-8000-000000000002")
REVISION_UUID = UUID("60000000-0000-4000-8000-000000000003")
REVISION_OPERATION = UUID("60000000-0000-4000-8000-000000000004")
RETRACTION_UUID = UUID("60000000-0000-4000-8000-000000000005")
RETRACTION_OPERATION = UUID("60000000-0000-4000-8000-000000000006")
ROOT_EFFECTIVE_AT = datetime(2026, 9, 29, 14, 2, tzinfo=UTC)
ROOT_KNOWN_AT = datetime(2026, 9, 29, 14, 3, tzinfo=UTC)
ROOT_COMMITTED_AT = datetime(2026, 9, 29, 14, 4, tzinfo=UTC)
PREPARE_AT = datetime(2026, 9, 29, 14, 5, tzinfo=UTC)
TRUSTED_AT = PREPARE_AT + timedelta(seconds=1)
CORRECTION_TABLES = (
    evidence_assessment_corrections,
    evidence_correction_identities,
    evidence_correction_command_receipts,
)


async def _seed_root(
    target: PostgresTestTarget,
    *,
    maximum_age: timedelta = timedelta(minutes=10),
) -> EvidenceSufficiencyAssessmentId:
    key = requirement_key()
    assert key.subject is not None
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        await evidence_service(store, OBSERVATION_ID).record(
            replace(evidence_command(), subject=key.subject)
        )
    async with postgres_store(target, PostgresEvidenceRequirementStore) as (_, store):
        outcome = await store.append_requirement_version(
            requirement_version(maximum_age=maximum_age)
        )
        assert isinstance(outcome, EvidenceRequirementVersionAppended)
    # duplicate-code: this root seed independently proves the assessment path's
    # prerequisite binding; sharing the binding test's private seed would couple proofs.
    # arid: disable
    async with postgres_store(target, PostgresEvidenceBindingStore) as (engine, store):
        await binding_service(
            store,
            BINDING_ID,
            requirements=EvidenceRequirementResolver(
                PostgresEvidenceRequirementStore(engine)
            ),
        ).record(binding_command())
    # arid: enable
    async with postgres_store(target, PostgresEvidenceSufficiencyStore) as (_, store):
        result = await EvidenceSufficiencyService(
            store=store,
            now=lambda: ROOT_COMMITTED_AT,
            new_uuid=lambda: ROOT_UUID,
        ).assess(
            RecordEvidenceSufficiencyAssessmentCommand(
                operation_id=OperationId(ROOT_OPERATION),
                applicability_key=key,
                attribution=UnknownActorAttribution(),
                effective_at=ROOT_EFFECTIVE_AT,
                known_at=ROOT_KNOWN_AT,
            )
        )
    return result.assessment_id


def _command(
    root_id: EvidenceSufficiencyAssessmentId,
    *,
    operation: UUID = REVISION_OPERATION,
    target=None,
    effect: EvidenceCorrectionEffect = EvidenceCorrectionEffect.REVISE,
    basis: str = "correct misrecorded assessment",
) -> RecordEvidenceAssessmentCorrectionCommand:
    return RecordEvidenceAssessmentCorrectionCommand(
        operation_id=OperationId(operation),
        root_id=root_id,
        target=root_id if target is None else target,
        effect=effect,
        attribution=UnknownActorAttribution(),
        basis=EvidenceCorrectionBasis(basis),
        effective_at=ROOT_EFFECTIVE_AT,
    )


def _service(store, correction_id: UUID, *, now: datetime = PREPARE_AT):
    return EvidenceCorrectionService(
        store=store,
        now=lambda: now,
        new_uuid=lambda: correction_id,
    )


@asynccontextmanager
async def _correction_store(
    target: PostgresTestTarget, *, now: datetime = TRUSTED_AT
) -> AsyncIterator[tuple[AsyncEngine, PostgresEvidenceCorrectionStore]]:
    async with postgres_store(
        target,
        lambda engine: PostgresEvidenceCorrectionStore(engine, now=lambda: now),
    ) as pair:
        yield pair


def test_assessment_revision_retraction_round_trip_restart_and_replay(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        async with _correction_store(postgres_target) as (_, store):
            service = _service(store, REVISION_UUID)
            first = await service.record(_command(root_id))
            replay = await service.record(_command(root_id))
            assert replay.replayed and replay.correction_id == first.correction_id
            with pytest.raises(EvidenceIdempotencyConflict):
                await service.record(_command(root_id, basis="changed request"))
        async with _correction_store(
            postgres_target, now=TRUSTED_AT + timedelta(seconds=1)
        ) as (engine, restarted):
            history = await restarted.load_assessment_history(root_id)
            assert history is not None
            assert len(history.corrections) == 1
            assert history.corrections[0].replacement == history.root
            assert history.corrections[0].recorded_at == TRUSTED_AT
            second = await _service(
                restarted,
                RETRACTION_UUID,
                now=TRUSTED_AT + timedelta(milliseconds=1),
            ).record(
                _command(
                    root_id,
                    operation=RETRACTION_OPERATION,
                    target=first.correction_id,
                    effect=EvidenceCorrectionEffect.RETRACT,
                )
            )
            current = await restarted.load_assessment_history(root_id)
            assert current is not None
            interpreted = current.interpret(
                effective_at=ROOT_EFFECTIVE_AT,
                known_at=TRUSTED_AT + timedelta(seconds=1),
            )
            counts = await postgres_row_counts(engine, *CORRECTION_TABLES)
        assert second.correction_id == EvidenceCorrectionId(RETRACTION_UUID)
        assert interpreted.state is EvidenceInterpretationState.DETERMINATE
        assert interpreted.assertions == frozenset({current.root})
        assert counts == (2, 2, 2)

    asyncio.run(scenario())


def test_persisted_misrecorded_proof_is_replaced_by_trusted_derivation(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_root(postgres_target)
        misrecorded = derived_assessment(
            interpretations=(), version=requirement_version()
        )
        assert misrecorded.result is EvidenceSufficiencyResult.INSUFFICIENT
        async with postgres_store(
            postgres_target, PostgresEvidenceSufficiencyStore
        ) as (
            engine,
            _,
        ):
            async with engine.begin() as connection:
                await connection.execute(
                    insert(evidence_sufficiency_assessments).values(
                        **sufficiency_assessment_values(misrecorded)
                    )
                )
        async with _correction_store(postgres_target) as (_, store):
            await _service(store, REVISION_UUID).record(
                _command(misrecorded.assessment_id)
            )
            history = await store.load_assessment_history(misrecorded.assessment_id)
            assert history is not None
            assert len(history.corrections) == 1
            replacement = history.corrections[0].replacement
            assert replacement is not None
            assert replacement.result is EvidenceSufficiencyResult.SUFFICIENT
            assert replacement.requirement_assessments != (
                misrecorded.requirement_assessments
            )
            assert replacement.basis_guards.bindings.binding_ids

    asyncio.run(scenario())


def test_assessment_sibling_withdrawal_and_revision_remain_contested(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        async with _correction_store(postgres_target) as (_, store):
            await _service(store, RETRACTION_UUID).record(
                _command(
                    root_id,
                    operation=RETRACTION_OPERATION,
                    effect=EvidenceCorrectionEffect.RETRACT,
                )
            )
        async with _correction_store(
            postgres_target, now=TRUSTED_AT + timedelta(seconds=1)
        ) as (_, store):
            await _service(
                store,
                REVISION_UUID,
                now=TRUSTED_AT + timedelta(milliseconds=1),
            ).record(_command(root_id))
            history = await store.load_assessment_history(root_id)
            assert history is not None
            interpreted = history.interpret(
                effective_at=ROOT_EFFECTIVE_AT,
                known_at=TRUSTED_AT + timedelta(seconds=1),
            )
        assert interpreted.state is EvidenceInterpretationState.CONTESTED
        assert interpreted.assertions == frozenset({history.root})
        assert {
            EvidenceCorrectionId(RETRACTION_UUID),
            EvidenceCorrectionId(REVISION_UUID),
        } <= interpreted.fact_support

    asyncio.run(scenario())


class _FailAfterAssessmentCorrection(PostgresEvidenceCorrectionStore):
    def _write_completed(self, step: str) -> None:
        if step == "correction":
            raise RuntimeError("injected assessment-correction failure")


def test_assessment_correction_rolls_back_every_row(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        async with postgres_store(
            postgres_target,
            lambda engine: _FailAfterAssessmentCorrection(
                engine, now=lambda: TRUSTED_AT
            ),
        ) as (engine, store):
            with pytest.raises(EvidencePersistenceUnavailable):
                await _service(store, REVISION_UUID).record(_command(root_id))
            counts = await postgres_row_counts(engine, *CORRECTION_TABLES)
        assert counts == (0, 0, 0)

    asyncio.run(scenario())


def test_trusted_instant_rejects_time_only_freshness_change(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target, maximum_age=timedelta(minutes=5))
        late = ROOT_EFFECTIVE_AT + timedelta(minutes=5, seconds=1)
        async with _correction_store(postgres_target, now=late) as (engine, store):
            # duplicate-code: time expiry and changed authority are independent
            # stale-basis falsifiers with separate causal setup.
            # arid: disable
            with pytest.raises(EvidenceCorrectionBasisConflict):
                await _service(store, REVISION_UUID).record(_command(root_id))
            counts = await postgres_row_counts(engine, evidence_assessment_corrections)
        assert counts == (0,)

    asyncio.run(scenario())
    # arid: enable


def test_trusted_instant_rejects_retraction_before_root_is_recorded(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        before_root = ROOT_COMMITTED_AT - timedelta(seconds=1)
        async with _correction_store(postgres_target, now=before_root) as (
            engine,
            store,
        ):
            with pytest.raises(EvidenceCorrectionHistoryConflict):
                # duplicate-code: this clock-order rejection independently
                # constructs the same retraction used by sibling interpretation.
                # arid: disable
                await _service(store, RETRACTION_UUID).record(
                    _command(
                        root_id,
                        operation=RETRACTION_OPERATION,
                        effect=EvidenceCorrectionEffect.RETRACT,
                    )
                )
                # arid: enable
            counts = await postgres_row_counts(engine, *CORRECTION_TABLES)
            history = await store.load_assessment_history(root_id)
            assert history is not None
            assert (
                history.interpret(
                    effective_at=ROOT_EFFECTIVE_AT,
                    known_at=before_root,
                ).state
                is EvidenceInterpretationState.NOT_KNOWN
            )
            assert (
                history.interpret(
                    effective_at=ROOT_EFFECTIVE_AT,
                    known_at=ROOT_COMMITTED_AT,
                ).state
                is EvidenceInterpretationState.DETERMINATE
            )
        assert counts == (0, 0, 0)

    asyncio.run(scenario())


def test_store_rejects_forged_authoritative_replacement_proof(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        async with _correction_store(postgres_target) as (engine, store):
            history = await store.load_assessment_history(root_id)
            assert history is not None
            basis = await store.load_sufficiency_basis(
                history.root.applicability_key,
                effective_at=ROOT_EFFECTIVE_AT,
                known_at=ROOT_KNOWN_AT,
            )
            current = await store.load_sufficiency_basis(
                history.root.applicability_key,
                effective_at=PREPARE_AT,
                known_at=PREPARE_AT,
            )
            from polaris.application.evidence.sufficiency import (
                EvidenceSufficiencyBasis,
            )

            assert isinstance(basis, EvidenceSufficiencyBasis)
            assert isinstance(current, EvidenceSufficiencyBasis)
            forged = replace(
                history.root,
                attribution=KnownActorAttribution(
                    ActorId(UUID("60000000-0000-4000-8000-000000000099"))
                ),
            )
            correction = EvidenceAssessmentCorrection(
                EvidenceCorrectionId(REVISION_UUID),
                root_id,
                root_id,
                EvidenceCorrectionEffect.REVISE,
                UnknownActorAttribution(),
                EvidenceCorrectionBasis("forged proof"),
                ROOT_EFFECTIVE_AT,
                PREPARE_AT,
                forged,
            )
            outcome = await store.commit_correction(
                EvidenceCorrectionCommit(
                    OperationId(REVISION_OPERATION),
                    EvidenceCorrectionSemanticRequest.from_correction(correction),
                    correction,
                    PREPARE_AT,
                    basis,
                    current,
                )
            )
            counts = await postgres_row_counts(engine, evidence_assessment_corrections)
        assert isinstance(outcome, EvidenceCorrectionStaleBasis)
        assert counts == (0,)

    asyncio.run(scenario())


class _AdvanceRequirementBeforeCommit(PostgresEvidenceCorrectionStore):
    async def commit_correction(self, commit):
        replacement = requirement_version(
            SECOND_VERSION_ID,
            predecessor_id=ROOT_VERSION_ID,
            effect=EvidenceRequirementPredecessorEffect.SUPERSEDES,
            maximum_age=timedelta(minutes=10),
            recorded_at=ROOT_COMMITTED_AT + timedelta(seconds=1),
            effective_at=ROOT_COMMITTED_AT + timedelta(seconds=1),
        )
        outcome = await PostgresEvidenceRequirementStore(
            self._engine
        ).append_requirement_version(replacement)
        assert isinstance(outcome, EvidenceRequirementVersionAppended)
        return await super().commit_correction(commit)


def test_concurrent_requirement_change_is_revalidated_before_append(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        async with postgres_store(
            postgres_target,
            lambda engine: _AdvanceRequirementBeforeCommit(
                engine, now=lambda: TRUSTED_AT
            ),
        ) as (engine, store):
            with pytest.raises(EvidenceCorrectionBasisConflict):
                await _service(store, REVISION_UUID).record(_command(root_id))
            counts = await postgres_row_counts(engine, evidence_assessment_corrections)
        assert counts == (0,)

    asyncio.run(scenario())


class _ConcurrentCorrectionStore(PostgresEvidenceCorrectionStore):
    def __init__(self, engine) -> None:
        super().__init__(engine, now=lambda: TRUSTED_AT)
        self.arrivals = 0
        self.both_ready = asyncio.Event()

    async def commit_correction(self, commit):
        self.arrivals += 1
        if self.arrivals == 2:
            self.both_ready.set()
        await self.both_ready.wait()
        return await super().commit_correction(commit)


def test_concurrent_same_root_writers_cannot_commit_stale_support(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        root_id = await _seed_root(postgres_target)
        async with postgres_store(postgres_target, _ConcurrentCorrectionStore) as (
            engine,
            store,
        ):
            results = await asyncio.gather(
                _service(store, REVISION_UUID).record(_command(root_id)),
                _service(store, RETRACTION_UUID).record(
                    _command(root_id, operation=RETRACTION_OPERATION)
                ),
                return_exceptions=True,
            )
            counts = await postgres_row_counts(
                engine, evidence_assessment_corrections, evidence_support_versions
            )
        assert (
            sum(isinstance(value, EvidenceCorrectionBasisConflict) for value in results)
            == 1
        )
        assert sum(not isinstance(value, Exception) for value in results) == 1
        assert counts == (1, 2)

    asyncio.run(scenario())
