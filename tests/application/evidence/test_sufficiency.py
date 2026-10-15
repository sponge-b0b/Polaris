from __future__ import annotations

import asyncio
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.evidence.requirements import (
    ContestedEvidenceRequirementAuthority,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    UnavailableEvidenceRequirementAuthority,
)
from polaris.application.evidence.sufficiency import (
    EvidenceSufficiencyAssessmentResult,
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyBasisConflict,
    EvidenceSufficiencyCommit,
    EvidenceSufficiencyCommitted,
    EvidenceSufficiencyContestedAuthority,
    EvidenceSufficiencyHistoryConflict,
    EvidenceSufficiencyInvalidAuthority,
    EvidenceSufficiencyInvalidHistory,
    EvidenceSufficiencyMissingAuthority,
    EvidenceSufficiencyReceipt,
    EvidenceSufficiencyService,
    EvidenceSufficiencyStaleBasis,
    EvidenceSufficiencyUnavailableAuthority,
    RecordEvidenceSufficiencyAssessmentCommand,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import OperationId
from polaris.domain.evidence.observations import (
    EvidenceSufficiencyAssessmentId,
    EvidenceSupportVersion,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAuthorityGuard,
    EvidenceRequirementDisposition,
    EvidenceSufficiencyBasisGuards,
    EvidenceSufficiencyResult,
)
from tests.configuration_support import (
    SECOND_VERSION_ID,
    requirement_key,
    requirement_version,
)
from tests.sufficiency_support import (
    ASSESSMENT_EFFECTIVE_AT,
    ASSESSMENT_KNOWN_AT,
    interpreted_binding,
)

OPERATION_ID = UUID("00000000-0000-4000-8000-000000000801")
ASSESSMENT_ID = UUID("00000000-0000-4000-8000-000000000802")
ACTOR_ID = UUID("00000000-0000-4000-8000-000000000803")
RECORDED_AT = datetime(2026, 9, 29, 14, 4, tzinfo=UTC)


def _basis() -> EvidenceSufficiencyBasis:
    interpretation = interpreted_binding()
    version = requirement_version()
    return EvidenceSufficiencyBasis(
        requirement_version=version,
        interpretations=(interpretation,),
        support_version=EvidenceSupportVersion(1),
        guards=EvidenceSufficiencyBasisGuards(
            EvidenceBindingUniverseGuard(
                frozenset({interpretation.binding.binding_id})
            ),
            EvidenceCorrectionUniverseGuard(frozenset()),
            EvidenceRequirementAuthorityGuard(frozenset({version.version_id})),
        ),
    )


def _command(
    operation_id: UUID = OPERATION_ID,
) -> RecordEvidenceSufficiencyAssessmentCommand:
    return RecordEvidenceSufficiencyAssessmentCommand(
        operation_id=OperationId(operation_id),
        applicability_key=requirement_key(),
        attribution=KnownActorAttribution(ActorId(ACTOR_ID)),
        effective_at=ASSESSMENT_EFFECTIVE_AT,
        known_at=ASSESSMENT_KNOWN_AT,
    )


class _Store:
    def __init__(self, resolution=None) -> None:
        self.resolution = resolution or _basis()
        self.receipt = None
        self.commit: EvidenceSufficiencyCommit | None = None
        self.basis_reads = 0

    async def get_sufficiency_receipt(self, operation_id):
        del operation_id
        return self.receipt

    async def load_sufficiency_basis(
        self,
        applicability_key,
        *,
        effective_at,
        known_at,
    ):
        del applicability_key, effective_at, known_at
        self.basis_reads += 1
        return self.resolution

    async def commit_sufficiency(self, commit):
        self.commit = commit
        # duplicate-code: the fake store locally models the port result so service
        # tests do not depend on PostgreSQL adapter construction behavior.
        # arid: disable
        result = EvidenceSufficiencyAssessmentResult(
            commit.assessment.assessment_id,
            commit.assessment.result,
        )
        receipt = EvidenceSufficiencyReceipt(
            commit.operation_id,
            commit.request,
            result,
        )
        # arid: enable
        self.receipt = receipt
        return EvidenceSufficiencyCommitted(receipt)

    async def load_sufficiency_assessment(self, assessment_id):
        del assessment_id
        return self.commit.assessment if self.commit is not None else None


def _assess(store: _Store, command=None):
    return asyncio.run(
        EvidenceSufficiencyService(
            store=store,
            now=lambda: RECORDED_AT,
            new_uuid=lambda: ASSESSMENT_ID,
        ).assess(command or _command())
    )


def test_command_has_no_caller_authored_disposition_or_support_subset() -> None:
    actual = {
        field.name for field in fields(RecordEvidenceSufficiencyAssessmentCommand)
    }
    assert actual == {
        "operation_id",
        "applicability_key",
        "attribution",
        "effective_at",
        "known_at",
        "reassesses_assessment_id",
    }


def test_service_derives_complete_proof_before_commit() -> None:
    store = _Store()

    result = _assess(store)

    assert result == EvidenceSufficiencyAssessmentResult(
        EvidenceSufficiencyAssessmentId(ASSESSMENT_ID),
        EvidenceSufficiencyResult.SUFFICIENT,
    )
    assert store.commit is not None
    assessment = store.commit.assessment
    assert assessment.requirement_assessments[0].disposition is (
        EvidenceRequirementDisposition.SATISFIED
    )
    assert assessment.contributing_binding_ids == frozenset(
        {store.resolution.interpretations[0].binding.binding_id}
    )
    assert assessment.support_version == EvidenceSupportVersion(1)
    assert assessment.known_at == ASSESSMENT_KNOWN_AT


def test_exact_retry_reuses_identity_without_reloading_mutable_basis() -> None:
    store = _Store()
    first = _assess(store)
    assert store.receipt is not None

    second = _assess(store)

    assert second.assessment_id == first.assessment_id
    assert second.replayed
    assert store.basis_reads == 1


@pytest.mark.parametrize(
    ("resolution", "expected"),
    # duplicate-code: sufficiency authority mapping is proved independently from
    # freshness mapping; sharing cases could conceal a missing outcome in either API.
    # arid: disable
    [
        (MissingEvidenceRequirementAuthority(), EvidenceSufficiencyMissingAuthority),
        (
            UnavailableEvidenceRequirementAuthority("offline"),
            EvidenceSufficiencyUnavailableAuthority,
        ),
        (
            ContestedEvidenceRequirementAuthority(
                frozenset(
                    {
                        requirement_version().version_id,
                        requirement_version(SECOND_VERSION_ID).version_id,
                    }
                )
            ),
            EvidenceSufficiencyContestedAuthority,
        ),
        (
            InvalidEvidenceRequirementAuthority("broken ancestry"),
            EvidenceSufficiencyInvalidAuthority,
        ),
    ],
    # arid: enable
)
def test_authority_failures_remain_typed_and_append_nothing(
    resolution,
    expected,
) -> None:
    store = _Store(resolution)

    result = _assess(store)

    assert isinstance(result, expected)
    assert store.commit is None


def test_future_knowledge_cutoff_is_invalid_and_append_free() -> None:
    store = _Store()
    command = replace(_command(), known_at=RECORDED_AT + timedelta(microseconds=1))

    result = _assess(store, command)

    assert isinstance(result, EvidenceSufficiencyInvalidAuthority)
    assert store.basis_reads == 0
    assert store.commit is None


def test_stale_commit_basis_is_a_typed_fail_closed_application_error() -> None:
    class _StaleStore(_Store):
        async def commit_sufficiency(self, commit):
            self.commit = commit
            return EvidenceSufficiencyStaleBasis("support changed")

    with pytest.raises(EvidenceSufficiencyBasisConflict, match="support changed"):
        _assess(_StaleStore())


@pytest.mark.parametrize("failure_at", ["initial", "commit"])
def test_invalid_evidence_history_is_distinct_from_authority_and_stale_basis(
    failure_at: str,
) -> None:
    class _InvalidHistoryStore(_Store):
        async def load_sufficiency_basis(self, *args, **kwargs):
            if failure_at == "initial":
                return EvidenceSufficiencyInvalidHistory("late observation")
            return await super().load_sufficiency_basis(*args, **kwargs)

        async def commit_sufficiency(self, commit):
            self.commit = commit
            return EvidenceSufficiencyInvalidHistory("late observation")

    store = _InvalidHistoryStore()

    with pytest.raises(EvidenceSufficiencyHistoryConflict, match="late observation"):
        _assess(store)

    if failure_at == "initial":
        assert store.commit is None


def test_basis_rejects_incomplete_absence_guard() -> None:
    basis = _basis()

    with pytest.raises(ValueError, match="complete universe"):
        replace(
            basis,
            guards=replace(
                basis.guards,
                bindings=EvidenceBindingUniverseGuard(frozenset()),
            ),
        )
