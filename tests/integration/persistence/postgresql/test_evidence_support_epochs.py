from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.evidence import (
    EvidenceBindingService,
    EvidenceCorrectionService,
    EvidenceObservationService,
    EvidencePersistenceUnavailable,
    EvidenceRequirementResolver,
    EvidenceRequirementVersionAppended,
    EvidenceSufficiencyService,
    RecordEvidenceObservationCorrectionCommand,
    RecordEvidenceSufficiencyAssessmentCommand,
    ResolvedEvidenceRequirementVersion,
)
from polaris.domain.actors import (
    ActorId,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.decisions import InvestmentDecisionId, OperationId
from polaris.domain.evidence import (
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceObservationId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceUse,
    InvestmentRecommendationRef,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceCorrectionStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
    PostgresEvidenceSufficiencyStore,
    PostgresEvidenceSupportEpochStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_sufficiency_assessments,
)
from tests.binding_support import (
    BINDING_ID,
    BINDING_OPERATION_ID,
    SECOND_BINDING_ID,
    SECOND_BINDING_OPERATION_ID,
    SECOND_TARGET_ID,
    binding_command,
    binding_service,
)
from tests.configuration_support import (
    RequirementResolutionStub,
    requirement_assignment_for_key,
    requirement_key,
    requirement_version,
)
from tests.evidence_support import (
    OBSERVATION_ID,
    SECOND_OBSERVATION_ID,
    SECOND_OPERATION_ID,
    evidence_command,
    evidence_service,
)

from .conftest import PostgresTestTarget, postgres_row_counts, postgres_store

CURRENT = datetime(2026, 9, 29, 14, 5, tzinfo=UTC)
ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000e01")
ASSESSMENT_OPERATION = UUID("00000000-0000-4000-8000-000000000e02")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000e03")
THIRD_BINDING_ID = UUID("00000000-0000-4000-8000-000000000e04")
THIRD_BINDING_OPERATION = UUID("00000000-0000-4000-8000-000000000e05")
CORRECTION_ID = UUID("00000000-0000-4000-8000-000000000e06")
CORRECTION_OPERATION = UUID("00000000-0000-4000-8000-000000000e07")


async def _epoch(
    target: PostgresTestTarget,
    *,
    key: EvidenceRequirementApplicabilityKey | None = None,
    at: datetime = CURRENT,
) -> int:
    resolved_key = key or requirement_key()
    async with postgres_store(target, PostgresEvidenceSupportEpochStore) as (_, store):
        value = await store.load_support_version(
            resolved_key.target,
            resolved_key.scope,
            resolved_key.evidence_use,
            effective_at=at,
            known_at=at,
        )
    assert type(value) is EvidenceSupportVersion
    return value.value


async def _seed_observation(target: PostgresTestTarget) -> None:
    # duplicate-code: this fixture's exact unbound starting state is local to
    # epoch falsifiers; correction tests seed their own independent history.
    # arid: disable
    key = requirement_key()
    assert key.subject is not None
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        await evidence_service(store, OBSERVATION_ID).record(
            replace(evidence_command(), subject=key.subject)
        )
    # arid: enable


async def _seed_binding(target: PostgresTestTarget) -> None:
    # duplicate-code: this test asserts epoch effects of a real binding commit;
    # sharing setup with correction tests would couple separate proof paths.
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


async def _seed_requirement(target: PostgresTestTarget) -> None:
    async with postgres_store(target, PostgresEvidenceRequirementStore) as (_, store):
        outcome = await store.append_requirement_version(requirement_version())
        assert isinstance(outcome, EvidenceRequirementVersionAppended)


async def _record_successor(
    target: PostgresTestTarget, *, future_only: bool = False
) -> None:
    key = requirement_key()
    assert key.subject is not None
    command = evidence_command(
        SECOND_OPERATION_ID,
        supersedes=EvidenceObservationId(OBSERVATION_ID),
    )
    async with postgres_store(target, PostgresEvidenceStore) as (_, store):
        await EvidenceObservationService(
            store=store,
            now=lambda: CURRENT,
            new_uuid=lambda: SECOND_OBSERVATION_ID,
        ).record(
            replace(
                command,
                subject=key.subject,
                effective_at=(
                    CURRENT + timedelta(days=1) if future_only else command.effective_at
                ),
            )
        )


async def _retract_observation(
    target: PostgresTestTarget, observation_id: UUID, *, basis: str
) -> None:
    root = EvidenceObservationId(observation_id)
    async with postgres_store(target, PostgresEvidenceCorrectionStore) as (_, store):
        await EvidenceCorrectionService(
            store=store,
            now=lambda: CURRENT + timedelta(minutes=2),
            new_uuid=lambda: CORRECTION_ID,
        ).record(
            RecordEvidenceObservationCorrectionCommand(
                operation_id=OperationId(CORRECTION_OPERATION),
                root_id=root,
                target=root,
                effect=EvidenceCorrectionEffect.RETRACT,
                attribution=UnknownActorAttribution(),
                basis=EvidenceCorrectionBasis(basis),
                effective_at=CURRENT + timedelta(minutes=1),
            )
        )


def test_epoch_advances_for_assessment_and_bound_observation_succession(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        assert await _epoch(postgres_target) == 0
        await _seed_observation(postgres_target)
        assert await _epoch(postgres_target) == 0

        await _seed_requirement(postgres_target)
        await _seed_binding(postgres_target)
        assert await _epoch(postgres_target) == 1

        # duplicate-code: the assessment append is exercised directly here;
        # reconstruction tests independently construct their own assessment.
        # arid: disable
        async with postgres_store(
            postgres_target, PostgresEvidenceSufficiencyStore
        ) as (_, store):
            service = EvidenceSufficiencyService(
                store=store,
                now=lambda: CURRENT - timedelta(minutes=1),
                new_uuid=lambda: ASSESSMENT_ID,
            )
            await service.assess(
                RecordEvidenceSufficiencyAssessmentCommand(
                    operation_id=OperationId(ASSESSMENT_OPERATION),
                    applicability_key=requirement_key(),
                    attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
                    effective_at=CURRENT - timedelta(minutes=3),
                    known_at=CURRENT - timedelta(minutes=2),
                )
            )
        # arid: enable
        assert await _epoch(postgres_target) == 2

        await _record_successor(postgres_target)
        assert await _epoch(postgres_target) == 3
        assert await _epoch(postgres_target, at=CURRENT - timedelta(minutes=2)) == 1
        # A new adapter instance observes the same independently stored epoch.
        assert await _epoch(postgres_target) == 3

        await _retract_observation(
            postgres_target,
            SECOND_OBSERVATION_ID,
            basis="publisher retracted successor",
        )
        assert await _epoch(postgres_target, at=CURRENT + timedelta(minutes=2)) == 4

    asyncio.run(scenario())


def test_epoch_isolated_by_target_and_use_and_ignores_future_binding(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        async with postgres_store(postgres_target, PostgresEvidenceBindingStore) as (
            engine,
            store,
        ):
            resolver = EvidenceRequirementResolver(
                PostgresEvidenceRequirementStore(engine)
            )
            await binding_service(store, BINDING_ID, requirements=resolver).record(
                binding_command()
            )
            await binding_service(
                store, SECOND_BINDING_ID, requirements=resolver
            ).record(
                binding_command(
                    SECOND_BINDING_OPERATION_ID,
                    target_id=SECOND_TARGET_ID,
                )
            )
            await binding_service(
                store, THIRD_BINDING_ID, requirements=resolver
            ).record(
                replace(
                    binding_command(THIRD_BINDING_OPERATION),
                    effective_at=CURRENT + timedelta(days=1),
                )
            )
        await _record_successor(postgres_target, future_only=True)
        assert await _epoch(postgres_target) == 1
        key = requirement_key()
        bases = (
            BasisScopeKey(
                InvestmentDecisionId(UUID("00000000-0000-4000-8000-000000000e09")),
                key.target,
                key.scope,
                key.evidence_use,
            ),
            BasisScopeKey(
                InvestmentDecisionId(UUID("00000000-0000-4000-8000-000000000e10")),
                key.target,
                key.scope,
                key.evidence_use,
            ),
        )
        async with postgres_store(
            postgres_target, PostgresEvidenceSupportEpochStore
        ) as (_, store):
            consumed = [
                await store.load_support_version(
                    basis.target,
                    basis.scope,
                    basis.use,
                    effective_at=CURRENT,
                    known_at=CURRENT,
                )
                for basis in bases
            ]
        assert consumed == [EvidenceSupportVersion(1), EvidenceSupportVersion(1)]
        assert (
            await _epoch(
                postgres_target,
                key=replace(key, target=InvestmentRecommendationRef(SECOND_TARGET_ID)),
            )
            == 1
        )
        assert (
            await _epoch(
                postgres_target,
                key=replace(key, evidence_use=EvidenceUse.CHALLENGE_BASIS),
            )
            == 0
        )
        assert (
            await _epoch(
                postgres_target,
                key=replace(
                    key,
                    scope=ClaimSpecificEvidenceScope(
                        ClaimId(UUID("00000000-0000-4000-8000-000000000e08"))
                    ),
                ),
            )
            == 0
        )

    asyncio.run(scenario())


def test_concurrent_same_scope_writes_advance_once_each(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: concurrent writers need a separate setup path so
        # their race proof does not inherit the isolation test's sequencing.
        # arid: disable
        await _seed_observation(postgres_target)
        async with postgres_store(postgres_target, PostgresEvidenceBindingStore) as (
            engine,
            first_store,
        ):
            resolver = EvidenceRequirementResolver(
                PostgresEvidenceRequirementStore(engine)
            )
            # arid: enable
            second_store = PostgresEvidenceBindingStore(engine)
            await asyncio.gather(
                binding_service(first_store, BINDING_ID, requirements=resolver).record(
                    binding_command(BINDING_OPERATION_ID)
                ),
                binding_service(
                    second_store, SECOND_BINDING_ID, requirements=resolver
                ).record(binding_command(SECOND_BINDING_OPERATION_ID)),
            )
        assert await _epoch(postgres_target) == 2

    asyncio.run(scenario())


def test_correcting_predecessor_advances_distinct_bound_successor_scope(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_requirement(postgres_target)
        async with postgres_store(postgres_target, PostgresEvidenceBindingStore) as (
            _,
            store,
        ):
            await binding_service(store, BINDING_ID).record(binding_command())
            await binding_service(store, THIRD_BINDING_ID).record(
                binding_command(THIRD_BINDING_OPERATION)
            )

        await _record_successor(postgres_target)
        assert await _epoch(postgres_target) == 3

        key = requirement_key()
        other_key = replace(key, target=InvestmentRecommendationRef(SECOND_TARGET_ID))
        authority = ResolvedEvidenceRequirementVersion(
            requirement_version(assignment=requirement_assignment_for_key(other_key))
        )
        async with postgres_store(postgres_target, PostgresEvidenceBindingStore) as (
            _,
            store,
        ):
            await EvidenceBindingService(
                store=store,
                now=lambda: CURRENT + timedelta(minutes=1),
                new_uuid=lambda: SECOND_BINDING_ID,
                requirements=RequirementResolutionStub(authority),
            ).record(
                replace(
                    binding_command(
                        SECOND_BINDING_OPERATION_ID,
                        target_id=SECOND_TARGET_ID,
                        key=other_key,
                    ),
                    observation_id=EvidenceObservationId(SECOND_OBSERVATION_ID),
                )
            )
        assert (
            await _epoch(
                postgres_target, key=other_key, at=CURRENT + timedelta(minutes=1)
            )
            == 1
        )

        await _retract_observation(
            postgres_target,
            OBSERVATION_ID,
            basis="publisher withdrew predecessor",
        )
        assert await _epoch(postgres_target, at=CURRENT + timedelta(minutes=2)) == 4
        assert (
            await _epoch(
                postgres_target, key=other_key, at=CURRENT + timedelta(minutes=2)
            )
            == 2
        )

    asyncio.run(scenario())


class _FailAfterSupportEpochStore(PostgresEvidenceSufficiencyStore):
    def _write_completed(self, step: str) -> None:
        if step == "support_version":
            raise RuntimeError("injected failure after support epoch append")


def test_assessment_failure_after_epoch_append_rolls_back_fact_and_epoch(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_requirement(postgres_target)
        await _seed_binding(postgres_target)
        async with postgres_store(postgres_target, _FailAfterSupportEpochStore) as (
            engine,
            store,
        ):
            service = EvidenceSufficiencyService(
                store=store,
                now=lambda: CURRENT - timedelta(minutes=1),
                new_uuid=lambda: ASSESSMENT_ID,
            )
            with pytest.raises(EvidencePersistenceUnavailable):
                await service.assess(
                    RecordEvidenceSufficiencyAssessmentCommand(
                        operation_id=OperationId(ASSESSMENT_OPERATION),
                        applicability_key=requirement_key(),
                        attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
                        effective_at=CURRENT - timedelta(minutes=3),
                        known_at=CURRENT - timedelta(minutes=2),
                    )
                )
            assert await postgres_row_counts(
                engine, evidence_sufficiency_assessments
            ) == (0,)
        assert await _epoch(postgres_target) == 1

    asyncio.run(scenario())
