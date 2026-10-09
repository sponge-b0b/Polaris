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
    EvidenceObservationService,
    EvidencePersistenceUnavailable,
    EvidenceRequirementResolver,
    EvidenceRequirementVersionAppended,
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyService,
    RecordEvidenceBindingCorrectionCommand,
    RecordEvidenceObservationCorrectionCommand,
    RecordEvidenceSufficiencyAssessmentCommand,
)
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceBindingId,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    EvidenceObservation,
    EvidenceObservationId,
    EvidenceObservationMaterial,
)
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceRole,
)
from polaris.domain.evidence.freshness import EvidenceFreshnessResult
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretationState,
    EvidenceRequirementDisposition,
    evaluate_evidence_sufficiency,
)
from polaris.infrastructure.persistence.postgresql import (
    PostgresEvidenceBindingStore,
    PostgresEvidenceCorrectionStore,
    PostgresEvidenceRequirementStore,
    PostgresEvidenceStore,
    PostgresEvidenceSufficiencyStore,
)
from polaris.infrastructure.persistence.postgresql.schema import (
    evidence_binding_corrections,
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
BINDING_CORRECTION_ID = UUID("00000000-0000-4000-8000-000000000a31")
BINDING_OPERATION_ID = UUID("00000000-0000-4000-8000-000000000a32")


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


async def _load_binding_only(target: PostgresTestTarget) -> EvidenceBinding:
    async with postgres_store(target, PostgresEvidenceBindingStore) as (_, store):
        binding = await store.load_binding(EvidenceBindingId(BINDING_ID))
    assert binding is not None
    return binding


def _binding_revision_command(
    binding: EvidenceBinding,
    replacement: EvidenceBinding,
    basis: str,
) -> RecordEvidenceBindingCorrectionCommand:
    return RecordEvidenceBindingCorrectionCommand(
        OperationId(BINDING_OPERATION_ID),
        binding.binding_id,
        binding.binding_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis(basis),
        CORRECTION_RECORDED_AT - timedelta(minutes=1),
        replacement,
    )


async def _load_current_basis(target: PostgresTestTarget) -> EvidenceSufficiencyBasis:
    async with postgres_store(target, PostgresEvidenceSufficiencyStore) as (_, store):
        basis = await store.load_sufficiency_basis(
            requirement_key(),
            effective_at=CORRECTION_RECORDED_AT,
            known_at=CORRECTION_RECORDED_AT,
        )
    assert isinstance(basis, EvidenceSufficiencyBasis)
    return basis


async def _seed_future_binding(target: PostgresTestTarget) -> EvidenceBinding:
    await _seed_observation(target)
    async with postgres_store(target, PostgresEvidenceRequirementStore) as (
        _,
        requirement_store,
    ):
        outcome = await requirement_store.append_requirement_version(
            requirement_version()
        )
        assert isinstance(outcome, EvidenceRequirementVersionAppended)
    async with postgres_store(target, PostgresEvidenceBindingStore) as (
        engine,
        binding_store,
    ):
        await binding_service(
            binding_store,
            BINDING_ID,
            requirements=EvidenceRequirementResolver(
                PostgresEvidenceRequirementStore(engine)
            ),
        ).record(
            replace(
                binding_command(),
                effective_at=CORRECTION_RECORDED_AT + timedelta(minutes=1),
            )
        )
        binding = await binding_store.load_binding(EvidenceBindingId(BINDING_ID))
    assert binding is not None
    assert binding.effective_at > CORRECTION_RECORDED_AT
    return binding


def test_binding_revision_round_trip_replay_and_fixed_endpoints(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        binding = await _load_binding_only(postgres_target)
        replacement = replace(
            binding,
            role=EvidenceRole.QUALIFYING,
            availability=EvidenceAvailability.UNKNOWN,
            materially_used=False,
            freshness=replace(
                binding.freshness,
                result=EvidenceFreshnessResult.STALE,
            ),
        )
        command = _binding_revision_command(
            binding, replacement, "reviewed role and availability"
        )
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            service = _correction_service(store, BINDING_CORRECTION_ID)
            result = await service.record(command)
            replay = await service.record(command)
            assert replay.replayed
            assert replay.correction_id == result.correction_id
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            engine,
            restarted,
        ):
            cutoff = CORRECTION_RECORDED_AT + timedelta(minutes=1)
            current = await _correction_service(restarted).inspect_binding(
                binding.binding_id, effective_at=cutoff, known_at=cutoff
            )
            historical = await _correction_service(restarted).inspect_binding(
                binding.binding_id,
                effective_at=cutoff,
                known_at=CORRECTION_RECORDED_AT - timedelta(seconds=1),
            )
            assert current.assertions == frozenset({replacement})
            assert historical.assertions == frozenset({binding})
            assert current.fact_support == frozenset(
                {binding.binding_id, result.correction_id}
            )
            counts = await postgres_row_counts(engine, evidence_binding_corrections)
            assert counts == (1,)
            with pytest.raises(
                EvidenceCorrectionHistoryConflict, match="cannot change"
            ):
                await _correction_service(
                    restarted, UUID("00000000-0000-4000-8000-000000000a33")
                ).record(
                    replace(
                        command,
                        operation_id=OperationId(
                            UUID("00000000-0000-4000-8000-000000000a34")
                        ),
                        replacement=replace(
                            replacement,
                            observation_id=EvidenceObservationId(SECOND_OBSERVATION_ID),
                        ),
                    )
                )
            assert await postgres_row_counts(engine, evidence_binding_corrections) == (
                1,
            )
            restored_id = UUID("00000000-0000-4000-8000-000000000a35")
            await _correction_service(restarted, restored_id).record(
                RecordEvidenceBindingCorrectionCommand(
                    OperationId(UUID("00000000-0000-4000-8000-000000000a36")),
                    binding.binding_id,
                    result.correction_id,
                    EvidenceCorrectionEffect.RETRACT,
                    UnknownActorAttribution(),
                    EvidenceCorrectionBasis("withdraw role correction"),
                    CORRECTION_RECORDED_AT,
                )
            )
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            restarted_again,
        ):
            restored = await _correction_service(restarted_again).inspect_binding(
                binding.binding_id,
                effective_at=cutoff,
                known_at=cutoff,
            )
        assert restored.assertions == frozenset({binding})
        assert restored.fact_support == frozenset(
            {
                binding.binding_id,
                result.correction_id,
                EvidenceCorrectionId(restored_id),
            }
        )

    asyncio.run(scenario())


def test_binding_revision_reaches_current_sufficiency_basis(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        binding = await _load_binding_only(postgres_target)
        # duplicate-code: the role-change and backdated-time scenarios each own
        # independent persistence lifetimes to falsify different basis errors.
        # arid: disable
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(
                _binding_revision_command(
                    binding,
                    replace(binding, role=EvidenceRole.QUALIFYING),
                    "role review",
                )
            )
        # arid: enable
        basis = await _load_current_basis(postgres_target)
        assert basis.interpretations[0].binding.role is EvidenceRole.QUALIFYING
        assert basis.support_version.value == 2
        assert basis.guards.corrections.correction_ids == frozenset(
            {EvidenceCorrectionId(BINDING_CORRECTION_ID)}
        )

    asyncio.run(scenario())


def test_backdated_binding_revision_enters_sufficiency_universe(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        binding = await _seed_future_binding(postgres_target)
        replacement = replace(
            binding,
            effective_at=CORRECTION_RECORDED_AT - timedelta(minutes=2),
        )
        # duplicate-code: the backdated correction must commit through its own
        # store lifetime before the exact historical basis is reloaded.
        # arid: disable
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(
                replace(
                    _binding_revision_command(binding, replacement, "correct time"),
                    effective_at=replacement.effective_at,
                )
            )
        # arid: enable
        basis = await _load_current_basis(postgres_target)
        assert len(basis.interpretations) == 1
        assert basis.interpretations[0].binding == replacement
        assert basis.support_version.value == 1
        assert basis.guards.corrections.correction_ids == frozenset(
            {EvidenceCorrectionId(BINDING_CORRECTION_ID)}
        )
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(
                store, UUID("00000000-0000-4000-8000-000000000a37")
            ).record(
                RecordEvidenceBindingCorrectionCommand(
                    OperationId(UUID("00000000-0000-4000-8000-000000000a38")),
                    binding.binding_id,
                    EvidenceCorrectionId(BINDING_CORRECTION_ID),
                    EvidenceCorrectionEffect.RETRACT,
                    UnknownActorAttribution(),
                    EvidenceCorrectionBasis("restore future root"),
                    CORRECTION_RECORDED_AT - timedelta(minutes=1),
                )
            )
        restored_basis = await _load_current_basis(postgres_target)
        assert restored_basis.interpretations == ()
        assert restored_basis.support_version.value == 2

    asyncio.run(scenario())


def test_future_only_binding_revision_does_not_advance_current_support(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        binding = await _seed_future_binding(postgres_target)
        # duplicate-code: this correction must remain future-effective, while
        # adjacent correction proofs intentionally change current support.
        # arid: disable
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(
                _binding_revision_command(
                    binding,
                    replace(binding, role=EvidenceRole.QUALIFYING),
                    "future role review",
                )
            )
        # arid: enable
        basis = await _load_current_basis(postgres_target)
        assert basis.interpretations == ()
        assert basis.support_version.value == 0

    asyncio.run(scenario())


@pytest.mark.parametrize("change", ["correction", "succession"])
def test_observation_change_advances_support_after_backdated_binding_revision(
    postgres_target: PostgresTestTarget,
    change: str,
) -> None:
    async def scenario() -> None:
        # duplicate-code: this setup proves observation effects after a
        # backdated binding; the standalone restoration test owns its branch.
        # arid: disable
        binding = await _seed_future_binding(postgres_target)
        replacement = replace(
            binding,
            effective_at=CORRECTION_RECORDED_AT - timedelta(minutes=2),
        )
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(
                replace(
                    _binding_revision_command(binding, replacement, "correct time"),
                    effective_at=replacement.effective_at,
                )
            )
        # arid: enable
        assert (await _load_current_basis(postgres_target)).support_version.value == 1

        cutoff = CORRECTION_RECORDED_AT
        if change == "correction":
            observation = await _load_observation_only(postgres_target)
            async with postgres_store(
                postgres_target, PostgresEvidenceCorrectionStore
            ) as (_, store):
                await _correction_service(store, OBSERVATION_CORRECTION_ID).record(
                    _observation_correction_command(
                        observation,
                        basis="publisher withdrew observation",
                    )
                )
        else:
            cutoff += timedelta(minutes=1)
            key = requirement_key()
            assert key.subject is not None
            async with postgres_store(postgres_target, PostgresEvidenceStore) as (
                _,
                store,
            ):
                await EvidenceObservationService(
                    store=store,
                    now=lambda: cutoff,
                    new_uuid=lambda: SECOND_OBSERVATION_ID,
                ).record(
                    replace(
                        evidence_command(
                            SECOND_OPERATION_ID,
                            supersedes=EvidenceObservationId(OBSERVATION_ID),
                        ),
                        subject=key.subject,
                    )
                )
        async with postgres_store(
            postgres_target, PostgresEvidenceSufficiencyStore
        ) as (_, store):
            basis = await store.load_sufficiency_basis(
                requirement_key(), effective_at=cutoff, known_at=cutoff
            )
        assert isinstance(basis, EvidenceSufficiencyBasis)
        assert basis.support_version.value == 2

    asyncio.run(scenario())


@pytest.mark.parametrize("mode", ["contested", "withdrawn"])
def test_backdated_binding_branches_enter_sufficiency_universe(
    postgres_target: PostgresTestTarget,
    mode: str,
) -> None:
    async def scenario() -> None:
        binding = await _seed_future_binding(postgres_target)
        backdated_at = CORRECTION_RECORDED_AT - timedelta(minutes=2)
        first = RecordEvidenceBindingCorrectionCommand(
            OperationId(BINDING_OPERATION_ID),
            binding.binding_id,
            binding.binding_id,
            (
                EvidenceCorrectionEffect.RETRACT
                if mode == "withdrawn"
                else EvidenceCorrectionEffect.REVISE
            ),
            UnknownActorAttribution(),
            EvidenceCorrectionBasis("backdated binding review"),
            backdated_at,
            (
                None
                if mode == "withdrawn"
                else replace(binding, effective_at=backdated_at)
            ),
        )
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(first)
            if mode == "contested":
                await _correction_service(store, RETRACTION_ID).record(
                    replace(
                        first,
                        operation_id=OperationId(RETRACTION_OPERATION_ID),
                        replacement=replace(
                            binding,
                            effective_at=backdated_at,
                            role=EvidenceRole.CONFLICTING,
                        ),
                    )
                )
        basis = await _load_current_basis(postgres_target)
        assert len(basis.interpretations) == 1
        interpretation = basis.interpretations[0]
        expected_state = (
            EvidenceBindingInterpretationState.WITHDRAWN
            if mode == "withdrawn"
            else EvidenceBindingInterpretationState.CONTESTED
        )
        assert interpretation.state is expected_state
        assert len(interpretation.surviving_bindings or ()) == (
            0 if mode == "withdrawn" else 2
        )
        assert basis.support_version.value == (1 if mode == "withdrawn" else 2)
        expected_ids = {EvidenceCorrectionId(BINDING_CORRECTION_ID)}
        if mode == "contested":
            expected_ids.add(EvidenceCorrectionId(RETRACTION_ID))
        assert basis.guards.corrections.correction_ids == expected_ids
        assert basis.requirement_version is not None
        assessment = evaluate_evidence_sufficiency(
            basis.requirement_version,
            requirement_key(),
            basis.interpretations,
            effective_at=CORRECTION_RECORDED_AT,
            known_at=CORRECTION_RECORDED_AT,
        )
        assert assessment.requirement_assessments[0].disposition is (
            EvidenceRequirementDisposition.MISSING
            if mode == "withdrawn"
            else EvidenceRequirementDisposition.CONTESTED
        )

    asyncio.run(scenario())


def test_contested_binding_proof_preserves_each_sibling_across_restart(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        # duplicate-code: this proof keeps its own binding seed and evaluation
        # independent from the temporal membership tests it guards.
        # arid: disable
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        binding = await _load_binding_only(postgres_target)
        # arid: enable
        first = replace(
            binding,
            effective_at=CORRECTION_RECORDED_AT - timedelta(minutes=1),
            freshness=replace(
                binding.freshness,
                basis=replace(
                    binding.freshness.basis,
                    as_of_at=CORRECTION_RECORDED_AT - timedelta(minutes=1),
                ),
            ),
        )
        second = replace(
            binding,
            effective_at=first.effective_at,
            availability=EvidenceAvailability.UNAVAILABLE,
            materially_used=False,
        )
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            _,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(
                replace(
                    _binding_revision_command(binding, first, "available branch"),
                    effective_at=first.effective_at,
                )
            )
            await _correction_service(store, RETRACTION_ID).record(
                replace(
                    _binding_revision_command(binding, second, "unavailable branch"),
                    operation_id=OperationId(RETRACTION_OPERATION_ID),
                    effective_at=second.effective_at,
                )
            )
        basis = await _load_current_basis(postgres_target)
        assert (
            basis.interpretations[0].state
            is EvidenceBindingInterpretationState.CONTESTED
        )
        assert basis.requirement_version is not None
        # duplicate-code: direct disposition and branch-proof assertions remain
        # independent witnesses over the same exact current-basis call.
        # arid: disable
        evaluation = evaluate_evidence_sufficiency(
            basis.requirement_version,
            requirement_key(),
            basis.interpretations,
            effective_at=CORRECTION_RECORDED_AT,
            known_at=CORRECTION_RECORDED_AT,
        )
        # arid: enable
        proof = evaluation.requirement_assessments[0].binding_proofs[0]
        assert {
            (
                assertion.binding.availability,
                assertion.binding.materially_used,
                assertion.freshness.result,
            )
            for assertion in proof.assertion_proofs
        } == {
            (EvidenceAvailability.AVAILABLE, True, EvidenceFreshnessResult.FRESH),
            (EvidenceAvailability.UNAVAILABLE, False, EvidenceFreshnessResult.STALE),
        }
        assert {
            EvidenceCorrectionId(BINDING_CORRECTION_ID),
            EvidenceCorrectionId(RETRACTION_ID),
        } <= proof.fact_support
        # duplicate-code: the fresh and restarted stores are distinct durability
        # boundaries; collapsing their contexts would hide the restart falsifier.
        # arid: disable
        async with postgres_store(
            postgres_target, PostgresEvidenceSufficiencyStore
        ) as (
            _,
            store,
        ):
            result = await EvidenceSufficiencyService(
                store=store,
                now=lambda: CORRECTION_RECORDED_AT + timedelta(minutes=1),
                new_uuid=lambda: UUID("00000000-0000-4000-8000-000000000a39"),
            ).assess(
                RecordEvidenceSufficiencyAssessmentCommand(
                    OperationId(UUID("00000000-0000-4000-8000-000000000a3a")),
                    requirement_key(),
                    UnknownActorAttribution(),
                    CORRECTION_RECORDED_AT,
                    CORRECTION_RECORDED_AT,
                )
            )
        async with postgres_store(
            postgres_target, PostgresEvidenceSufficiencyStore
        ) as (
            _,
            restarted,
        ):
            saved = await restarted.load_sufficiency_assessment(result.assessment_id)
        # arid: enable
        assert saved is not None
        assert saved.requirement_assessments[0].binding_proofs[0] == proof

    asyncio.run(scenario())


def test_binding_correction_rollback_and_immutability(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        await _seed_observation(postgres_target)
        await _seed_binding(postgres_target)
        root_id = EvidenceBindingId(BINDING_ID)
        command = RecordEvidenceBindingCorrectionCommand(
            OperationId(BINDING_OPERATION_ID),
            root_id,
            root_id,
            EvidenceCorrectionEffect.RETRACT,
            UnknownActorAttribution(),
            EvidenceCorrectionBasis("withdraw binding"),
            CORRECTION_RECORDED_AT - timedelta(minutes=1),
        )
        async with postgres_store(postgres_target, _FailAfterCorrectionStore) as (
            engine,
            failing,
        ):
            with pytest.raises(EvidencePersistenceUnavailable):
                await _correction_service(failing, BINDING_CORRECTION_ID).record(
                    command
                )
            assert await postgres_row_counts(
                engine,
                evidence_correction_identities,
                evidence_binding_corrections,
                evidence_correction_command_receipts,
            ) == (0, 0, 0)
        async with postgres_store(postgres_target, PostgresEvidenceCorrectionStore) as (
            engine,
            store,
        ):
            await _correction_service(store, BINDING_CORRECTION_ID).record(command)
            async with engine.begin() as connection:
                with pytest.raises(SQLAlchemyError):
                    await connection.execute(
                        update(evidence_binding_corrections).values(
                            basis_reference="rewritten"
                        )
                    )

    asyncio.run(scenario())


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
        "load_binding_history",
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
        basis = await _load_current_basis(postgres_target)
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
