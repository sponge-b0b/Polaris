from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from polaris.domain.configuration import (
    EvidenceNoSufficiencyRequirementsWitness,
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementId,
    EvidenceRequirementNotApplicableWitness,
    EvidenceRequirementSetVersion,
    EvidenceRequirementSetVersionId,
    InvalidEvidenceRequirementHistory,
    validate_requirement_history,
)


class EvidenceRequirementReadUnavailable(Exception):
    """Technology-neutral requirement-authority read failure."""


@dataclass(frozen=True, slots=True)
class EvidenceRequirementVersionAppended:
    version: EvidenceRequirementSetVersion


@dataclass(frozen=True, slots=True)
class EvidenceRequirementVersionConflict:
    version_id: EvidenceRequirementSetVersionId


@dataclass(frozen=True, slots=True)
class EvidenceRequirementHistoryRejected:
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceRequirementStoreUnavailable:
    reason: str


type EvidenceRequirementAppendOutcome = (
    EvidenceRequirementVersionAppended
    | EvidenceRequirementVersionConflict
    | EvidenceRequirementHistoryRejected
    | EvidenceRequirementStoreUnavailable
)


class EvidenceRequirementStore(Protocol):
    async def load_requirement_versions(
        self,
    ) -> tuple[EvidenceRequirementSetVersion, ...]: ...

    async def append_requirement_version(
        self,
        version: EvidenceRequirementSetVersion,
    ) -> EvidenceRequirementAppendOutcome: ...


@dataclass(frozen=True, slots=True)
class ResolvedEvidenceRequirementVersion:
    version: EvidenceRequirementSetVersion


@dataclass(frozen=True, slots=True)
class MissingEvidenceRequirementAuthority:
    pass


@dataclass(frozen=True, slots=True)
class ContestedEvidenceRequirementAuthority:
    version_ids: frozenset[EvidenceRequirementSetVersionId]


@dataclass(frozen=True, slots=True)
class InvalidEvidenceRequirementAuthority:
    reason: str


@dataclass(frozen=True, slots=True)
class UnavailableEvidenceRequirementAuthority:
    reason: str


type EvidenceRequirementResolution = (
    ResolvedEvidenceRequirementVersion
    | MissingEvidenceRequirementAuthority
    | ContestedEvidenceRequirementAuthority
    | InvalidEvidenceRequirementAuthority
    | UnavailableEvidenceRequirementAuthority
)


def requirement_not_applicable_witness(
    resolution: EvidenceRequirementResolution,
    requirement_id: EvidenceRequirementId,
    applicability_key: EvidenceRequirementApplicabilityKey,
) -> EvidenceRequirementNotApplicableWitness | None:
    if not isinstance(resolution, ResolvedEvidenceRequirementVersion):
        return None
    return resolution.version.not_applicable_witness(
        requirement_id,
        applicability_key,
    )


def no_sufficiency_requirements_witness(
    resolution: EvidenceRequirementResolution,
    applicability_key: EvidenceRequirementApplicabilityKey,
) -> EvidenceNoSufficiencyRequirementsWitness | None:
    if not isinstance(resolution, ResolvedEvidenceRequirementVersion):
        return None
    return resolution.version.no_sufficiency_requirements_witness(applicability_key)


class EvidenceRequirementVersionResolver(Protocol):
    async def resolve(
        self,
        key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceRequirementResolution: ...


class EvidenceRequirementResolver:
    def __init__(self, store: EvidenceRequirementStore) -> None:
        self._store = store

    async def resolve(
        self,
        key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceRequirementResolution:
        _aware(effective_at, "effective_at")
        _aware(known_at, "known_at")
        try:
            versions = await self._store.load_requirement_versions()
        except EvidenceRequirementReadUnavailable as error:
            return UnavailableEvidenceRequirementAuthority(str(error))
        return resolve_requirement_version(
            versions,
            key,
            effective_at=effective_at,
            known_at=known_at,
        )


def resolve_requirement_version(
    versions: tuple[EvidenceRequirementSetVersion, ...],
    key: EvidenceRequirementApplicabilityKey,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> EvidenceRequirementResolution:
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")
    known_versions = tuple(
        version for version in versions if version.recorded_at <= known_at
    )
    try:
        validate_requirement_history(known_versions)
    except InvalidEvidenceRequirementHistory as error:
        return InvalidEvidenceRequirementAuthority(str(error))

    active = {
        version.version_id: version
        for version in known_versions
        if version.effective_at <= effective_at
    }
    shadowed = {
        ancestor
        for version in active.values()
        for ancestor in _active_ancestors(version, active)
    }
    matches = tuple(
        version
        for version_id, version in active.items()
        if version_id not in shadowed and version.applicability.matches(key)
    )
    if not matches:
        return MissingEvidenceRequirementAuthority()
    if len(matches) > 1:
        return ContestedEvidenceRequirementAuthority(
            frozenset(version.version_id for version in matches)
        )
    return ResolvedEvidenceRequirementVersion(matches[0])


def _active_ancestors(
    version: EvidenceRequirementSetVersion,
    active: dict[EvidenceRequirementSetVersionId, EvidenceRequirementSetVersion],
) -> set[EvidenceRequirementSetVersionId]:
    ancestors: set[EvidenceRequirementSetVersionId] = set()
    predecessor = version.predecessor
    while predecessor is not None and predecessor.version_id in active:
        ancestors.add(predecessor.version_id)
        predecessor = active[predecessor.version_id].predecessor
    return ancestors


# duplicate-code: application resolution owns its boundary failure semantics;
# sharing a domain validator would couple application and domain error contracts.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
