from __future__ import annotations

import asyncio
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.application.evidence import (
    EvidenceCorrectionAuthorityConflict,
    EvidenceCorrectionAuthorityKind,
    EvidenceCorrectionBasisConflict,
    EvidenceCorrectionCommit,
    EvidenceCorrectionCommitted,
    EvidenceCorrectionHistoryConflict,
    EvidenceCorrectionReceipt,
    EvidenceCorrectionResult,
    EvidenceCorrectionService,
    EvidenceIdempotencyConflict,
    RecordEvidenceAssessmentCorrectionCommand,
)
from polaris.application.evidence.requirements import (
    ContestedEvidenceRequirementAuthority,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    UnavailableEvidenceRequirementAuthority,
)
from polaris.application.evidence.sufficiency import (
    EvidenceSufficiencyBasis,
    EvidenceSufficiencyInvalidHistory,
)
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.decisions import OperationId
from polaris.domain.evidence import (
    EvidenceAssessmentCorrection,
    EvidenceAssessmentCorrectionHistory,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
)
from polaris.domain.evidence.observations import EvidenceSupportVersion
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAuthorityGuard,
    EvidenceSufficiencyBasisGuards,
    EvidenceSufficiencyResult,
)
from tests.configuration_support import requirement_version
from tests.sufficiency_support import derived_assessment, interpreted_binding

NOW = datetime(2026, 9, 29, 14, 5, tzinfo=UTC)
CORRECTION_UUID = UUID("50000000-0000-4000-8000-000000000001")
OPERATION_UUID = UUID("50000000-0000-4000-8000-000000000002")


def _basis(
    *, maximum_age: timedelta = timedelta(minutes=10)
) -> EvidenceSufficiencyBasis:
    version = requirement_version(maximum_age=maximum_age)
    interpreted = interpreted_binding()
    return EvidenceSufficiencyBasis(
        version,
        (interpreted,),
        EvidenceSupportVersion(1),
        EvidenceSufficiencyBasisGuards(
            EvidenceBindingUniverseGuard(frozenset({interpreted.binding.binding_id})),
            EvidenceCorrectionUniverseGuard(frozenset()),
            EvidenceRequirementAuthorityGuard(frozenset({version.version_id})),
        ),
    )


class _Store:
    def __init__(self, *, maximum_age: timedelta = timedelta(minutes=10)) -> None:
        self.basis = _basis(maximum_age=maximum_age)
        self.root = derived_assessment(version=self.basis.requirement_version)
        self.receipt: EvidenceCorrectionReceipt | None = None
        self.commit: EvidenceCorrectionCommit | None = None

    async def get_correction_receipt(self, operation_id):
        return (
            self.receipt
            if self.receipt and self.receipt.operation_id == operation_id
            else None
        )

    async def load_assessment_history(self, root_id):
        return (
            EvidenceAssessmentCorrectionHistory(self.root, ())
            if root_id == self.root.assessment_id
            else None
        )

    async def load_sufficiency_basis(self, key, *, effective_at, known_at):
        del key, effective_at, known_at
        return self.basis

    async def commit_correction(self, commit):
        self.commit = commit
        self.receipt = EvidenceCorrectionReceipt(
            commit.operation_id,
            commit.request,
            EvidenceCorrectionResult(commit.correction.correction_id),
        )
        return EvidenceCorrectionCommitted(self.receipt)


def _command(
    store: _Store, *, basis: str = "assessment record correction"
) -> RecordEvidenceAssessmentCorrectionCommand:
    return RecordEvidenceAssessmentCorrectionCommand(
        operation_id=OperationId(OPERATION_UUID),
        root_id=store.root.assessment_id,
        target=store.root.assessment_id,
        effect=EvidenceCorrectionEffect.REVISE,
        attribution=UnknownActorAttribution(),
        basis=EvidenceCorrectionBasis(basis),
        effective_at=store.root.effective_at,
    )


def _record(store: _Store, command: RecordEvidenceAssessmentCorrectionCommand):
    return asyncio.run(
        EvidenceCorrectionService(
            store=store,
            now=lambda: NOW,
            new_uuid=lambda: CORRECTION_UUID,
        ).record(command)
    )


def test_assessment_correction_command_cannot_submit_proof_or_support_subset() -> None:
    assert {
        field.name for field in fields(RecordEvidenceAssessmentCorrectionCommand)
    } == {
        "operation_id",
        "root_id",
        "target",
        "effect",
        "attribution",
        "basis",
        "effective_at",
    }


def test_application_derives_assessment_replacement_and_exact_replay() -> None:
    store = _Store()
    command = _command(store)

    result = _record(store, command)

    assert result == EvidenceCorrectionResult(EvidenceCorrectionId(CORRECTION_UUID))
    assert store.commit is not None
    assert type(store.commit.correction) is EvidenceAssessmentCorrection
    assert store.commit.correction.replacement == store.root
    assert store.commit.assessment_basis == store.basis
    assert store.commit.assessment_commit_basis == store.basis
    assert _record(store, command).replayed is True
    with pytest.raises(EvidenceIdempotencyConflict):
        _record(store, _command(store, basis="different correction"))


def test_revision_repairs_misrecorded_disposition_from_complete_universe() -> None:
    store = _Store()
    store.root = derived_assessment(
        interpretations=(), version=store.basis.requirement_version
    )
    assert store.root.result is EvidenceSufficiencyResult.INSUFFICIENT

    _record(store, _command(store))

    assert store.commit is not None
    replacement = store.commit.correction.replacement
    assert replacement is not None
    assert replacement.result is EvidenceSufficiencyResult.SUFFICIENT
    assert replacement.requirement_assessments != store.root.requirement_assessments
    assert replacement.basis_guards == store.basis.guards


def test_time_only_freshness_change_rejects_assessment_correction() -> None:
    store = _Store(maximum_age=timedelta(minutes=2))

    with pytest.raises(EvidenceCorrectionBasisConflict):
        _record(store, _command(store))

    assert store.commit is None


def test_preparation_rejects_correction_before_root_is_recorded() -> None:
    store = _Store()
    store.root = replace(store.root, recorded_at=NOW + timedelta(seconds=1))

    with pytest.raises(EvidenceCorrectionHistoryConflict):
        _record(store, _command(store))

    assert store.commit is None


@pytest.mark.parametrize(
    ("resolution", "kind"),
    [
        (
            MissingEvidenceRequirementAuthority(),
            EvidenceCorrectionAuthorityKind.MISSING,
        ),
        (
            UnavailableEvidenceRequirementAuthority("owner unavailable"),
            EvidenceCorrectionAuthorityKind.UNAVAILABLE,
        ),
        (
            ContestedEvidenceRequirementAuthority(frozenset()),
            EvidenceCorrectionAuthorityKind.CONTESTED,
        ),
        (
            InvalidEvidenceRequirementAuthority("incomplete requirement history"),
            EvidenceCorrectionAuthorityKind.INVALID,
        ),
    ],
)
def test_requirement_authority_failure_is_typed_and_appends_nothing(
    resolution, kind
) -> None:
    store = _Store()
    store.basis = resolution

    with pytest.raises(EvidenceCorrectionAuthorityConflict) as error:
        _record(store, _command(store))

    assert error.value.kind is kind
    assert store.commit is None


def test_invalid_interpreted_history_appends_nothing() -> None:
    store = _Store()
    store.basis = EvidenceSufficiencyInvalidHistory("incomplete binding ancestry")

    with pytest.raises(EvidenceCorrectionHistoryConflict):
        _record(store, _command(store))

    assert store.commit is None
