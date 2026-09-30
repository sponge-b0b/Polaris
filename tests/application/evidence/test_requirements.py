from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

from polaris.application.evidence import (
    ContestedEvidenceRequirementAuthority,
    EvidenceRequirementReadUnavailable,
    EvidenceRequirementResolver,
    InvalidEvidenceRequirementAuthority,
    MissingEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
    UnavailableEvidenceRequirementAuthority,
    resolve_requirement_version,
)
from polaris.domain.configuration import EvidenceRequirementPredecessorEffect
from polaris.domain.evidence import EvidenceUse
from tests.configuration_support import (
    EFFECTIVE_AT,
    RECORDED_AT,
    ROOT_VERSION_ID,
    SECOND_VERSION_ID,
    THIRD_VERSION_ID,
    requirement_assignment,
    requirement_key,
    requirement_version,
)


class _RequirementStore:
    def __init__(self, versions=(), *, unavailable: bool = False) -> None:
        self.versions = tuple(versions)
        self.unavailable = unavailable

    async def load_requirement_versions(self):
        if self.unavailable:
            raise EvidenceRequirementReadUnavailable("configuration unavailable")
        return self.versions

    async def append_requirement_version(self, version):
        raise AssertionError("not used by resolver tests")


def test_resolution_obeys_effective_and_known_boundaries() -> None:
    root = requirement_version()
    key = requirement_key()

    for effective_at, known_at in (
        (EFFECTIVE_AT - timedelta(seconds=1), RECORDED_AT),
        (EFFECTIVE_AT, RECORDED_AT - timedelta(seconds=1)),
    ):
        assert isinstance(
            resolve_requirement_version(
                (root,),
                key,
                effective_at=effective_at,
                known_at=known_at,
            ),
            MissingEvidenceRequirementAuthority,
        )
    result = resolve_requirement_version(
        (root,),
        key,
        effective_at=EFFECTIVE_AT,
        known_at=RECORDED_AT,
    )
    assert result == ResolvedEvidenceRequirementVersion(root)


def test_known_correction_replaces_ancestry_without_recency_selection() -> None:
    root = requirement_version()
    corrected = requirement_version(
        SECOND_VERSION_ID,
        effective_at=EFFECTIVE_AT - timedelta(days=1),
        recorded_at=RECORDED_AT + timedelta(hours=1),
        predecessor_id=ROOT_VERSION_ID,
    )
    before_known = resolve_requirement_version(
        (root, corrected),
        requirement_key(),
        effective_at=RECORDED_AT + timedelta(hours=2),
        known_at=RECORDED_AT,
    )
    after_known = resolve_requirement_version(
        (corrected, root),
        requirement_key(),
        effective_at=RECORDED_AT + timedelta(hours=2),
        known_at=corrected.recorded_at,
    )

    assert before_known == ResolvedEvidenceRequirementVersion(root)
    assert after_known == ResolvedEvidenceRequirementVersion(corrected)


def test_history_recorded_after_known_boundary_cannot_rewrite_earlier_result() -> None:
    root = requirement_version()
    later_orphan = requirement_version(
        SECOND_VERSION_ID,
        recorded_at=RECORDED_AT + timedelta(days=1),
        predecessor_id=THIRD_VERSION_ID,
    )

    before_known = resolve_requirement_version(
        (root, later_orphan),
        requirement_key(),
        effective_at=RECORDED_AT + timedelta(days=2),
        known_at=RECORDED_AT,
    )
    after_known = resolve_requirement_version(
        (root, later_orphan),
        requirement_key(),
        effective_at=RECORDED_AT + timedelta(days=2),
        known_at=later_orphan.recorded_at,
    )

    assert before_known == ResolvedEvidenceRequirementVersion(root)
    assert isinstance(after_known, InvalidEvidenceRequirementAuthority)


def test_incomparable_applicable_versions_are_contested() -> None:
    root = requirement_version()
    left = requirement_version(
        SECOND_VERSION_ID,
        recorded_at=RECORDED_AT + timedelta(minutes=1),
        predecessor_id=ROOT_VERSION_ID,
    )
    right = requirement_version(
        THIRD_VERSION_ID,
        recorded_at=RECORDED_AT + timedelta(minutes=2),
        predecessor_id=ROOT_VERSION_ID,
    )
    result = resolve_requirement_version(
        (root, right, left),
        requirement_key(),
        effective_at=RECORDED_AT + timedelta(hours=1),
        known_at=RECORDED_AT + timedelta(hours=1),
    )

    assert result == ContestedEvidenceRequirementAuthority(
        frozenset({left.version_id, right.version_id})
    )


def test_zero_match_is_missing_and_bad_ancestry_is_invalid() -> None:
    root = requirement_version()
    no_match = replace(
        requirement_key(),
        evidence_use=EvidenceUse.CURRENT_SUPPORT_CHECK,
    )
    missing = resolve_requirement_version(
        (root,),
        no_match,
        effective_at=RECORDED_AT,
        known_at=RECORDED_AT,
    )
    invalid = resolve_requirement_version(
        (
            requirement_version(
                SECOND_VERSION_ID,
                predecessor_id=ROOT_VERSION_ID,
            ),
        ),
        requirement_key(),
        effective_at=RECORDED_AT,
        known_at=RECORDED_AT,
    )

    assert isinstance(missing, MissingEvidenceRequirementAuthority)
    assert isinstance(invalid, InvalidEvidenceRequirementAuthority)


def test_supersession_is_not_effective_before_its_prospective_boundary() -> None:
    root = requirement_version()
    successor = requirement_version(
        SECOND_VERSION_ID,
        effective_at=RECORDED_AT + timedelta(hours=2),
        recorded_at=RECORDED_AT + timedelta(hours=1),
        predecessor_id=ROOT_VERSION_ID,
        effect=EvidenceRequirementPredecessorEffect.SUPERSEDES,
    )
    result = resolve_requirement_version(
        (root, successor),
        requirement_key(),
        effective_at=RECORDED_AT + timedelta(hours=1, minutes=30),
        known_at=RECORDED_AT + timedelta(hours=3),
    )

    assert result == ResolvedEvidenceRequirementVersion(root)


def test_resolver_preserves_unavailable_authority_as_distinct_outcome() -> None:
    resolver = EvidenceRequirementResolver(_RequirementStore(unavailable=True))

    result = asyncio.run(
        resolver.resolve(
            requirement_key(),
            effective_at=RECORDED_AT,
            known_at=RECORDED_AT,
        )
    )

    assert result == UnavailableEvidenceRequirementAuthority(
        "configuration unavailable"
    )


def test_family_wide_assignment_matches_exact_target_without_rule_graph() -> None:
    assignment = replace(
        requirement_assignment(),
        target=replace(requirement_assignment().target, target=None),
    )
    version = requirement_version(assignment=assignment)

    result = resolve_requirement_version(
        (version,),
        requirement_key(),
        effective_at=RECORDED_AT,
        known_at=RECORDED_AT,
    )

    assert result == ResolvedEvidenceRequirementVersion(version)
