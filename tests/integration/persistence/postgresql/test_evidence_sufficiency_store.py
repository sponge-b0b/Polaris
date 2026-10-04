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
    EvidenceIdempotencyConflict,
    EvidencePersistenceUnavailable,
    EvidenceRequirementResolver,
    EvidenceRequirementVersionAppended,
)
from polaris.application.evidence.sufficiency import (
    EvidenceSufficiencyAssessmentResult,
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyBasisConflict,
    EvidenceSufficiencyHistoryConflict,
    EvidenceSufficiencyService,
    EvidenceSufficiencyStore,
    RecordEvidenceSufficiencyAssessmentCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration import EvidenceRequirementPredecessorEffect
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceObservationId,
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import EvidenceSufficiencyResult
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
    PostgresEvidenceSufficiencyStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_sufficiency_assessments,
    evidence_sufficiency_command_receipts,
    evidence_sufficiency_contributors,
    evidence_support_versions,
)
from tests.binding_support import (
    BINDING_ID,
    SECOND_BINDING_ID,
    SECOND_BINDING_OPERATION_ID,
    binding_command,
    binding_service,
)
from tests.configuration_support import (
    SECOND_VERSION_ID,
    requirement_key,
    requirement_version,
)
from tests.evidence_support import (
    OBSERVATION_ID,
    SECOND_OBSERVATION_ID,
    evidence_command,
    evidence_service,
)
from tests.evidence_support import (
    SECOND_OPERATION_ID as SECOND_OBSERVATION_OPERATION_ID,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store

OPERATION_ID = UUID("00000000-0000-4000-8000-000000000901")
SECOND_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000902")
ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000903")
SECOND_ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000904")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000905")
ASSESSMENT_EFFECTIVE_AT = datetime(2026, 9, 29, 14, 2, tzinfo=UTC)
ASSESSMENT_KNOWN_AT = datetime(2026, 9, 29, 14, 3, tzinfo=UTC)
COMMITTED_AT = datetime(2026, 9, 29, 14, 4, tzinfo=UTC)


async def _seed_observation(
    target: PostgresTestTarget,
    *,
    identity: UUID = OBSERVATION_ID,
    command=None,
) -> None:
    key = requirement_key()
    assert key.subject is not None
    resolved_command = command or replace(evidence_command(), subject=key.subject)
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        await evidence_service(store, identity).record(resolved_command)


async def _seed_requirement(target: PostgresTestTarget, version=None) -> None:
    # duplicate-code: sufficiency integration owns its authority seed explicitly;
    # sharing binding-test setup would couple independent persistence proofs.
    # arid: disable
    async with postgres_store(target, PostgresEvidenceRequirementStore) as (_, store):
        outcome = await store.append_requirement_version(
            version or requirement_version()
        )
        assert isinstance(outcome, EvidenceRequirementVersionAppended)
    # arid: enable


async def _record_binding(
    target: PostgresTestTarget,
    *,
    identity: UUID = BINDING_ID,
    command=None,
) -> None:
    async with postgres_store(target, PostgresEvidenceBindingStore) as (engine, store):
        await binding_service(
            store,
            identity,
            requirements=EvidenceRequirementResolver(
                PostgresEvidenceRequirementStore(engine)
            ),
        ).record(command or binding_command())


async def _seed_basis(target: PostgresTestTarget) -> None:
    await _seed_observation(target)
    await _seed_requirement(target)
    await _record_binding(target)


def _command(
    operation_id: UUID = OPERATION_ID,
    *,
    reassesses: EvidenceSufficiencyAssessmentId | None = None,
    effective_at: datetime = ASSESSMENT_EFFECTIVE_AT,
    known_at: datetime = ASSESSMENT_KNOWN_AT,
) -> RecordEvidenceSufficiencyAssessmentCommand:
    # duplicate-code: this integration command is explicit so persistence tests do
    # not inherit application-unit fixture assumptions.
    # arid: disable
    return RecordEvidenceSufficiencyAssessmentCommand(
        operation_id=OperationId(operation_id),
        applicability_key=requirement_key(),
        attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
        effective_at=effective_at,
        known_at=known_at,
        reassesses_assessment_id=reassesses,
    )
    # arid: enable


def _service(store, *identities: UUID, now: datetime = COMMITTED_AT):
    values = iter(identities)
    return EvidenceSufficiencyService(
        store=store,
        now=lambda: now,
        new_uuid=lambda: next(values),
    )


def test_sufficiency_round_trips_complete_derived_proof_across_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    # duplicate-code: restart round-trip setup is local to this falsifier; sharing
    # nested scenario structure would create common-mode persistence proof.
    # arid: disable
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (_, store):
            result = await _service(store, ASSESSMENT_ID).assess(_command())
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, restarted):
            assessment = await restarted.load_sufficiency_assessment(
                result.assessment_id
            )
            counts = await postgres_row_counts(
                engine,
                evidence_sufficiency_assessments,
                evidence_sufficiency_contributors,
                evidence_sufficiency_command_receipts,
            )

        assert result == EvidenceSufficiencyAssessmentResult(
            EvidenceSufficiencyAssessmentId(ASSESSMENT_ID),
            EvidenceSufficiencyResult.SUFFICIENT,
        )
        assert assessment is not None
        assert assessment.assessment_id == result.assessment_id
        assert assessment.contributing_binding_ids == frozenset(
            {EvidenceBindingId(BINDING_ID)}
        )
        assert assessment.known_at == ASSESSMENT_KNOWN_AT
        assert assessment.support_version == EvidenceSupportVersion(1)
        assert counts == (1, 1, 1)

    # arid: enable

    asyncio.run(scenario())


def test_exact_replay_and_changed_semantic_reuse(
    postgres_target: PostgresTestTarget,
) -> None:
    # duplicate-code: replay setup stays local so the idempotency falsifier remains
    # independent from restart and concurrency proofs.
    # arid: disable
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (_, store):
            service = _service(store, ASSESSMENT_ID)
            first = await service.assess(_command())
            replay = await service.assess(_command())
            assert replay.assessment_id == first.assessment_id
            assert replay.replayed
            with pytest.raises(EvidenceIdempotencyConflict):
                await service.assess(
                    replace(
                        _command(),
                        known_at=ASSESSMENT_KNOWN_AT - timedelta(microseconds=1),
                    )
                )

    # arid: enable

    asyncio.run(scenario())


class _FailAfterAssessmentStore(PostgresEvidenceSufficiencyStore):
    def _write_completed(self, step: str) -> None:
        if step == "assessment":
            raise RuntimeError("injected sufficiency transaction failure")


def test_failure_after_assessment_insert_rolls_back_every_row(
    postgres_target: PostgresTestTarget,
) -> None:
    # duplicate-code: rollback setup must expose its exact failure boundary locally;
    # a shared scenario could hide rows inserted before the injected failure.
    # arid: disable
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            _FailAfterAssessmentStore,
        ) as (engine, store):
            with pytest.raises(EvidencePersistenceUnavailable):
                await _service(store, ASSESSMENT_ID).assess(_command())
            assert await postgres_row_counts(
                engine,
                evidence_sufficiency_assessments,
                evidence_sufficiency_contributors,
                evidence_sufficiency_command_receipts,
            ) == (0, 0, 0)

    # arid: enable

    asyncio.run(scenario())


class _InsertBindingBeforeCommitStore(PostgresEvidenceSufficiencyStore):
    def __init__(self, engine, target: PostgresTestTarget) -> None:
        super().__init__(engine)
        self._target = target

    async def commit_sufficiency(self, commit):
        await _record_binding(
            self._target,
            identity=SECOND_BINDING_ID,
            command=binding_command(SECOND_BINDING_OPERATION_ID),
        )
        return await super().commit_sufficiency(commit)


def test_commit_time_revalidation_rejects_new_binding_without_partial_append(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            lambda engine: _InsertBindingBeforeCommitStore(engine, postgres_target),
        ) as (engine, store):
            with pytest.raises(EvidenceSufficiencyBasisConflict, match="basis changed"):
                await _service(store, ASSESSMENT_ID).assess(_command())
            assert await postgres_row_counts(
                engine,
                evidence_sufficiency_assessments,
                evidence_sufficiency_command_receipts,
            ) == (0, 0)

    asyncio.run(scenario())


# duplicate-code: this parameterized initial-load falsifier keeps its complete
# database setup local so late temporal coordinates cannot share commit-time seams.
# arid: disable
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "acquired_at",
            ASSESSMENT_KNOWN_AT + timedelta(microseconds=1),
            "not known",
        ),
        (
            "observed_at",
            ASSESSMENT_KNOWN_AT + timedelta(microseconds=1),
            "not known",
        ),
        (
            "effective_at",
            ASSESSMENT_EFFECTIVE_AT + timedelta(microseconds=1),
            "not effective",
        ),
    ],
)
def test_late_observation_history_fails_closed_before_initial_append(
    postgres_target: PostgresTestTarget,
    field: str,
    value: datetime,
    message: str,
) -> None:
    async def scenario() -> None:
        key = requirement_key()
        assert key.subject is not None
        await _seed_observation(
            postgres_target,
            command=replace(
                evidence_command(),
                subject=key.subject,
                **{field: value},
            ),
        )
        await _seed_requirement(postgres_target)
        await _record_binding(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, store):
            with pytest.raises(EvidenceSufficiencyHistoryConflict, match=message):
                await _service(store, ASSESSMENT_ID).assess(_command())
            assert await postgres_row_counts(
                engine,
                evidence_sufficiency_assessments,
                evidence_sufficiency_command_receipts,
            ) == (0, 0)

    asyncio.run(scenario())


# arid: enable


# duplicate-code: commit-time invalid-history injection must remain independent
# from stale-binding injection so the two typed failure paths cannot self-confirm.
# arid: disable
class _InsertLateObservationBeforeCommitStore(PostgresEvidenceSufficiencyStore):
    def __init__(self, engine, target: PostgresTestTarget) -> None:
        super().__init__(engine)
        self._target = target

    async def commit_sufficiency(self, commit):
        key = requirement_key()
        assert key.subject is not None
        await _seed_observation(
            self._target,
            identity=SECOND_OBSERVATION_ID,
            command=replace(
                evidence_command(SECOND_OBSERVATION_OPERATION_ID),
                subject=key.subject,
                acquired_at=ASSESSMENT_KNOWN_AT + timedelta(microseconds=1),
            ),
        )
        await _record_binding(
            self._target,
            identity=SECOND_BINDING_ID,
            command=replace(
                binding_command(SECOND_BINDING_OPERATION_ID),
                observation_id=EvidenceObservationId(SECOND_OBSERVATION_ID),
            ),
        )
        return await super().commit_sufficiency(commit)


def test_commit_time_late_observation_history_is_not_stale_basis(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            lambda engine: _InsertLateObservationBeforeCommitStore(
                engine,
                postgres_target,
            ),
        ) as (engine, store):
            with pytest.raises(EvidenceSufficiencyHistoryConflict, match="not known"):
                await _service(store, ASSESSMENT_ID).assess(_command())
            assert await postgres_row_counts(
                engine,
                evidence_sufficiency_assessments,
                evidence_sufficiency_command_receipts,
            ) == (0, 0)

    asyncio.run(scenario())


# arid: enable


# duplicate-code: the restart/future-only epoch proof preserves both observation
# boundaries explicitly; sharing scenario steps would obscure which read is asserted.
# arid: disable
def test_support_epoch_is_persisted_per_scope_and_future_only_append_is_inert(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, store):
            first = await store.load_sufficiency_basis(
                requirement_key(),
                effective_at=ASSESSMENT_EFFECTIVE_AT,
                known_at=ASSESSMENT_KNOWN_AT,
            )
            assert isinstance(first, EvidenceSufficiencyBasis)
            assert first.support_version == EvidenceSupportVersion(1)
            assert await postgres_row_counts(
                engine,
                evidence_support_versions,
            ) == (1,)

        future_at = COMMITTED_AT + timedelta(minutes=1)
        await _record_binding(
            postgres_target,
            identity=SECOND_BINDING_ID,
            command=replace(
                binding_command(SECOND_BINDING_OPERATION_ID),
                effective_at=future_at,
            ),
        )
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, restarted):
            current = await restarted.load_sufficiency_basis(
                requirement_key(),
                effective_at=ASSESSMENT_EFFECTIVE_AT,
                known_at=ASSESSMENT_KNOWN_AT,
            )
            assert isinstance(current, EvidenceSufficiencyBasis)
            assert current.support_version == EvidenceSupportVersion(1)
            assert await postgres_row_counts(
                engine,
                evidence_support_versions,
            ) == (1,)

    asyncio.run(scenario())


# arid: enable


# duplicate-code: this support-only falsifier keeps duplicate-observation setup
# explicit so it cannot reuse the epoch calculation it independently challenges.
# arid: disable
def test_support_only_duplicate_observation_binding_advances_epoch_once(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        await _record_binding(
            postgres_target,
            identity=SECOND_BINDING_ID,
            command=binding_command(SECOND_BINDING_OPERATION_ID),
        )
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, restarted):
            result = await _service(restarted, ASSESSMENT_ID).assess(_command())
            assessment = await restarted.load_sufficiency_assessment(
                result.assessment_id
            )
            assert assessment is not None
            assert assessment.support_version == EvidenceSupportVersion(2)
            assert assessment.requirement_assessments[0].counted_observation_ids == (
                frozenset({EvidenceObservationId(OBSERVATION_ID)})
            )
            assert await postgres_row_counts(
                engine,
                evidence_support_versions,
            ) == (2,)

    asyncio.run(scenario())


# arid: enable


def test_concurrent_distinct_assessments_serialize_and_preserve_both_roots(
    postgres_target: PostgresTestTarget,
) -> None:
    # duplicate-code: concurrency setup remains local so serialization is proved
    # independently from stale-basis rejection and ordinary append behavior.
    # arid: disable
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, store):
            first, second = await asyncio.gather(
                _service(store, ASSESSMENT_ID).assess(_command()),
                _service(store, SECOND_ASSESSMENT_ID).assess(
                    _command(SECOND_OPERATION_ID)
                ),
            )
            assert first.assessment_id != second.assessment_id
            assert await postgres_row_counts(
                engine,
                evidence_sufficiency_assessments,
                evidence_sufficiency_command_receipts,
            ) == (2, 2)

    # arid: enable

    asyncio.run(scenario())


def test_changed_requirement_version_creates_linked_reassessment_root(
    postgres_target: PostgresTestTarget,
) -> None:
    # duplicate-code: reassessment owns an explicit two-version scenario; sharing
    # generic setup would obscure the exact historical-linkage proof.
    # arid: disable
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, store):
            first = await _service(store, ASSESSMENT_ID).assess(_command())
            next_recorded = COMMITTED_AT + timedelta(minutes=1)
            next_effective = next_recorded + timedelta(minutes=1)
            next_version = requirement_version(
                SECOND_VERSION_ID,
                effective_at=next_effective,
                recorded_at=next_recorded,
                predecessor_id=requirement_version().version_id.value,
                effect=EvidenceRequirementPredecessorEffect.SUPERSEDES,
            )
            outcome = await PostgresEvidenceRequirementStore(
                engine
            ).append_requirement_version(next_version)
            assert isinstance(outcome, EvidenceRequirementVersionAppended)
            second = await _service(
                store,
                SECOND_ASSESSMENT_ID,
                now=next_effective + timedelta(minutes=1),
            ).assess(
                _command(
                    SECOND_OPERATION_ID,
                    reassesses=first.assessment_id,
                    effective_at=next_effective,
                    known_at=next_effective,
                )
            )
            prior = await store.load_sufficiency_assessment(first.assessment_id)
            current = await store.load_sufficiency_assessment(second.assessment_id)

        assert prior is not None and current is not None
        assert prior.requirement_version_id != current.requirement_version_id
        assert current.reassesses_assessment_id == prior.assessment_id

    # arid: enable

    asyncio.run(scenario())


def test_sufficiency_rows_are_database_immutable(
    postgres_target: PostgresTestTarget,
) -> None:
    # duplicate-code: the immutability falsifier keeps its database boundary local
    # so a shared scenario cannot bypass the mutation path being rejected.
    # arid: disable
    async def scenario() -> None:
        await _seed_basis(postgres_target)
        async with postgres_store(
            postgres_target,
            PostgresEvidenceSufficiencyStore,
        ) as (engine, store):
            await _service(store, ASSESSMENT_ID).assess(_command())
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_sufficiency_assessments).values(
                            result="insufficient"
                        )
                    )

    # arid: enable

    asyncio.run(scenario())


def test_inward_sufficiency_port_exposes_no_database_types() -> None:
    for method_name in (
        "get_sufficiency_receipt",
        "load_sufficiency_basis",
        "commit_sufficiency",
        "load_sufficiency_assessment",
    ):
        signature = str(
            inspect.signature(getattr(EvidenceSufficiencyStore, method_name))
        )
        assert "sqlalchemy" not in signature.lower()
        assert "asyncpg" not in signature.lower()
        assert "postgres" not in signature.lower()
