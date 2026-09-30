from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest

from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityAssignment,
    EvidenceRequirementId,
    EvidenceRequirementPredecessor,
    EvidenceRequirementPredecessorEffect,
    EvidenceRequirementScopeAssignment,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
    EvidenceRequirementTargetAssignment,
    FreshnessRequirementDefinition,
    InvalidEvidenceRequirement,
    InvalidEvidenceRequirementHistory,
    SufficiencyRequirementDefinition,
    validate_requirement_history,
)
from polaris.domain.evidence import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentFamily,
    EvidenceScopeKind,
    EvidenceUse,
    InvestmentViewRef,
)
from tests.configuration_support import (
    CLAIM_ID,
    ROOT_VERSION_ID,
    SECOND_VERSION_ID,
    THIRD_VERSION_ID,
    requirement_assignment,
    requirement_key,
    requirement_version,
)


@pytest.mark.parametrize(
    "identity_type",
    [
        EvidenceRequirementSetId,
        EvidenceRequirementSetVersionId,
        EvidenceRequirementId,
    ],
)
def test_requirement_identities_are_distinct_uuid4_types(
    identity_type: type[object],
) -> None:
    with pytest.raises(InvalidEvidenceRequirement):
        identity_type(UUID("00000000-0000-1000-8000-000000000001"))  # type: ignore[call-arg]


def test_complete_version_preserves_authority_applicability_and_definitions() -> None:
    version = requirement_version()
    key = requirement_key()

    assert version.authority.authority_identity == "Polaris product configuration"
    assert version.applicability.matches(key)
    assert version.applicability.portfolio_id == key.portfolio_id
    assert version.applicability.instrument_id == key.instrument_id
    assert version.applicability.investment_horizon == key.investment_horizon
    assert isinstance(version.requirements[0], FreshnessRequirementDefinition)
    assert isinstance(version.requirements[1], SufficiencyRequirementDefinition)


def test_claim_assignment_requires_exact_target_and_typed_scope() -> None:
    with pytest.raises(InvalidEvidenceRequirement):
        EvidenceRequirementApplicabilityAssignment(
            target=EvidenceRequirementTargetAssignment(
                EvidenceJudgmentFamily.INVESTMENT_VIEW
            ),
            scope=EvidenceRequirementScopeAssignment(
                EvidenceScopeKind.CLAIM_SPECIFIC,
                ClaimId(CLAIM_ID),
            ),
            evidence_use=EvidenceUse.JUDGMENT_BASIS,
        )

    with pytest.raises(InvalidEvidenceRequirement):
        EvidenceRequirementScopeAssignment(
            EvidenceScopeKind.JUDGMENT_WIDE,
            ClaimId(CLAIM_ID),
        )


def test_exact_claim_scope_requires_typed_claim_id() -> None:
    with pytest.raises(TypeError, match="ClaimId"):
        ClaimSpecificEvidenceScope(None)  # type: ignore[arg-type]


def test_exact_target_must_match_its_owner_specific_family() -> None:
    with pytest.raises(InvalidEvidenceRequirement, match="family"):
        EvidenceRequirementTargetAssignment(
            EvidenceJudgmentFamily.INVESTMENT_RECOMMENDATION,
            InvestmentViewRef(ROOT_VERSION_ID),
        )


def test_applicability_requires_every_assigned_coordinate_to_match() -> None:
    assignment = requirement_assignment()
    key = requirement_key()

    assert assignment.matches(key)
    assert not assignment.matches(
        replace(
            key,
            evidence_use=EvidenceUse.CURRENT_SUPPORT_CHECK,
        )
    )


def test_history_accepts_one_acyclic_correction_or_supersession_predecessor() -> None:
    root = requirement_version()
    correction = requirement_version(
        SECOND_VERSION_ID,
        predecessor_id=ROOT_VERSION_ID,
    )
    supersession = requirement_version(
        THIRD_VERSION_ID,
        effective_at=correction.recorded_at + timedelta(minutes=2),
        recorded_at=correction.recorded_at + timedelta(minutes=1),
        predecessor_id=SECOND_VERSION_ID,
        effect=EvidenceRequirementPredecessorEffect.SUPERSEDES,
    )

    validate_requirement_history((root, correction, supersession))


def test_history_rejects_missing_cross_set_and_cyclic_ancestry() -> None:
    missing = requirement_version(
        SECOND_VERSION_ID,
        predecessor_id=ROOT_VERSION_ID,
    )
    with pytest.raises(InvalidEvidenceRequirementHistory, match="missing"):
        validate_requirement_history((missing,))

    other_set = UUID("00000000-0000-4000-8000-00000000020b")
    cross_set = requirement_version(
        SECOND_VERSION_ID,
        set_id=other_set,
        predecessor_id=ROOT_VERSION_ID,
    )
    with pytest.raises(InvalidEvidenceRequirementHistory, match="cross-set"):
        validate_requirement_history((requirement_version(), cross_set))

    first = replace(
        requirement_version(),
        predecessor=EvidenceRequirementPredecessor(
            EvidenceRequirementSetVersionId(SECOND_VERSION_ID),
            EvidenceRequirementPredecessorEffect.CORRECTS,
        ),
    )
    second = requirement_version(
        SECOND_VERSION_ID,
        predecessor_id=ROOT_VERSION_ID,
    )
    with pytest.raises(InvalidEvidenceRequirementHistory, match="root|cyclic"):
        validate_requirement_history((first, second))


def test_requirement_identity_cannot_survive_changed_predicate_meaning() -> None:
    root = requirement_version()
    changed = requirement_version(
        SECOND_VERSION_ID,
        predecessor_id=ROOT_VERSION_ID,
        maximum_age=timedelta(minutes=5),
    )

    with pytest.raises(InvalidEvidenceRequirementHistory, match="semantic predicate"):
        validate_requirement_history((root, changed))


def test_empty_complete_version_represents_explicit_no_requirements() -> None:
    version = replace(requirement_version(), requirements=())

    validate_requirement_history((version,))
    assert version.requirements == ()


def test_one_assignment_cannot_define_multiple_freshness_requirements() -> None:
    version = requirement_version()
    duplicate = FreshnessRequirementDefinition(
        EvidenceRequirementId(UUID("00000000-0000-4000-8000-00000000020c")),
        timedelta(minutes=5),
    )

    with pytest.raises(InvalidEvidenceRequirement, match="multiple freshness"):
        replace(version, requirements=(*version.requirements, duplicate))


def test_correction_cannot_transfer_configuration_authority() -> None:
    root = requirement_version()
    correction = replace(
        requirement_version(
            SECOND_VERSION_ID,
            predecessor_id=ROOT_VERSION_ID,
        ),
        authority=replace(
            root.authority,
            authority_identity="another configuration authority",
        ),
    )

    with pytest.raises(InvalidEvidenceRequirementHistory, match="retain"):
        validate_requirement_history((root, correction))


def test_requirement_production_contract_does_not_hardcode_spy() -> None:
    paths = (
        Path("src/polaris/domain/configuration/evidence_requirements.py"),
        Path("src/polaris/domain/evidence/judgments.py"),
        Path("src/polaris/application/evidence/requirements.py"),
        Path("src/polaris/infrastructure/persistence/postgresql/requirement_codec.py"),
        Path("src/polaris/infrastructure/persistence/postgresql/requirement_store.py"),
    )

    assert all("SPY" not in path.read_text(encoding="utf-8") for path in paths)
