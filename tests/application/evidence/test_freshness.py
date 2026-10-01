from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from polaris.application.evidence import (
    ContestedEvidenceRequirementAuthority,
    EvidenceRequirementResolver,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
    UnavailableEvidenceRequirementAuthority,
    evaluate_binding_freshness,
)
from polaris.domain.evidence.freshness import (
    EvidenceFreshnessApplicable,
    EvidenceFreshnessBasisReference,
    EvidenceFreshnessContestedAuthority,
    EvidenceFreshnessInvalidAuthority,
    EvidenceFreshnessMissingAuthority,
    EvidenceFreshnessNotApplicable,
    EvidenceFreshnessResult,
    EvidenceFreshnessUnavailableAuthority,
)
from polaris.domain.evidence.judgments import EvidenceUse
from tests.configuration_support import (
    EFFECTIVE_AT,
    RECORDED_AT,
    ROOT_VERSION_ID,
    SECOND_VERSION_ID,
    THIRD_VERSION_ID,
    RequirementResolutionStub,
    corrected_requirement_version,
    requirement_assignment,
    requirement_key,
    requirement_version,
)


class _Store:
    def __init__(self, versions) -> None:
        self.versions = tuple(versions)

    async def load_requirement_versions(self):
        return self.versions

    async def append_requirement_version(self, version):
        raise AssertionError("not used by freshness tests")


def _basis(as_of_at=EFFECTIVE_AT) -> EvidenceFreshnessBasisReference:
    return EvidenceFreshnessBasisReference(
        "observation:market-price:SPY",
        as_of_at,
        requirement_key(),
    )


def _evaluate_with_resolver(
    resolver,
    basis: EvidenceFreshnessBasisReference,
    *,
    effective_at=EFFECTIVE_AT,
    known_at=RECORDED_AT,
):
    return asyncio.run(
        evaluate_binding_freshness(
            resolver,
            basis,
            effective_at=effective_at,
            known_at=known_at,
        )
    )


def _evaluate(result, *, basis_at=None):
    return _evaluate_with_resolver(
        RequirementResolutionStub(result),
        _basis(basis_at or EFFECTIVE_AT),
    )


def _evaluate_historical_pair(
    resolver,
    *,
    after_known_at,
    after_effective_at=EFFECTIVE_AT,
):
    basis = _basis()
    before = _evaluate_with_resolver(
        resolver,
        basis,
        effective_at=EFFECTIVE_AT,
        known_at=RECORDED_AT,
    )
    after = _evaluate_with_resolver(
        resolver,
        basis,
        effective_at=after_effective_at,
        known_at=after_known_at,
    )
    return before, after


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (timedelta(), EvidenceFreshnessResult.FRESH),
        (timedelta(minutes=2), EvidenceFreshnessResult.FRESH),
        (timedelta(minutes=2, microseconds=1), EvidenceFreshnessResult.STALE),
    ],
)
def test_resolved_freshness_uses_exact_maximum_age_boundary(age, expected) -> None:
    outcome = _evaluate(
        ResolvedEvidenceRequirementVersion(requirement_version()),
        basis_at=EFFECTIVE_AT - age,
    )

    assert isinstance(outcome, EvidenceFreshnessApplicable)
    assert outcome.result is expected
    assert outcome.authority.version_id.value == ROOT_VERSION_ID


def test_future_basis_is_indeterminate_instead_of_becoming_fresh() -> None:
    outcome = _evaluate(
        ResolvedEvidenceRequirementVersion(requirement_version()),
        basis_at=EFFECTIVE_AT + timedelta(microseconds=1),
    )

    assert isinstance(outcome, EvidenceFreshnessApplicable)
    assert outcome.result is EvidenceFreshnessResult.INDETERMINATE


def test_resolved_version_without_freshness_records_negative_witness() -> None:
    version = replace(requirement_version(), requirements=())

    outcome = _evaluate(ResolvedEvidenceRequirementVersion(version))

    assert isinstance(outcome, EvidenceFreshnessNotApplicable)
    assert outcome.witness.set_id == version.set_id
    assert outcome.witness.version_id == version.version_id


@pytest.mark.parametrize(
    ("resolution", "expected_type"),
    [
        (MissingEvidenceRequirementAuthority(), EvidenceFreshnessMissingAuthority),
        (
            UnavailableEvidenceRequirementAuthority("configuration unavailable"),
            EvidenceFreshnessUnavailableAuthority,
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
            EvidenceFreshnessContestedAuthority,
        ),
    ],
)
def test_unresolved_requirement_authority_is_indeterminate(
    resolution,
    expected_type,
) -> None:
    outcome = _evaluate(resolution)

    assert isinstance(outcome, expected_type)
    assert outcome.result is EvidenceFreshnessResult.INDETERMINATE


def test_invalid_requirement_history_remains_invalid_not_absent() -> None:
    outcome = _evaluate(InvalidEvidenceRequirementAuthority("broken ancestry"))

    assert outcome == EvidenceFreshnessInvalidAuthority(
        _basis(),
        "broken ancestry",
    )


def test_contradictory_positive_resolution_fails_closed() -> None:
    wrong_assignment = replace(
        requirement_assignment(),
        evidence_use=EvidenceUse.CURRENT_SUPPORT_CHECK,
    )
    version = requirement_version(assignment=wrong_assignment)

    outcome = _evaluate(ResolvedEvidenceRequirementVersion(version))

    assert isinstance(outcome, EvidenceFreshnessInvalidAuthority)
    assert "contradicts" in outcome.reason


def test_requirement_resolution_obeys_historical_knowledge_boundary() -> None:
    root = requirement_version()
    corrected = corrected_requirement_version()
    resolver = EvidenceRequirementResolver(_Store((root, corrected)))
    before, after = _evaluate_historical_pair(
        resolver,
        after_known_at=corrected.recorded_at,
    )

    assert isinstance(before, EvidenceFreshnessApplicable)
    assert isinstance(after, EvidenceFreshnessApplicable)
    assert before.authority.version_id == root.version_id
    assert after.authority.version_id == corrected.version_id


def test_later_invalid_history_does_not_contaminate_earlier_boundary() -> None:
    root = requirement_version()
    later_orphan = requirement_version(
        THIRD_VERSION_ID,
        recorded_at=RECORDED_AT + timedelta(days=1),
        predecessor_id=SECOND_VERSION_ID,
    )
    resolver = EvidenceRequirementResolver(_Store((root, later_orphan)))
    before, after = _evaluate_historical_pair(
        resolver,
        after_effective_at=RECORDED_AT + timedelta(days=2),
        after_known_at=later_orphan.recorded_at,
    )

    assert isinstance(before, EvidenceFreshnessApplicable)
    assert isinstance(after, EvidenceFreshnessInvalidAuthority)
