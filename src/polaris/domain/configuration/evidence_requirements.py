from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentFamily,
    EvidenceJudgmentRef,
    EvidenceScope,
    EvidenceScopeKind,
    EvidenceUse,
    evidence_judgment_family,
    evidence_scope_kind,
    is_evidence_judgment_ref,
)
from polaris.domain.evidence.observations import EvidenceSubjectReference
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId


class InvalidEvidenceRequirement(ValueError):
    pass


class InvalidEvidenceRequirementHistory(InvalidEvidenceRequirement):
    pass


def _uuid4(value: object, field: str) -> None:
    if type(value) is not UUID or value.version != 4:
        raise InvalidEvidenceRequirement(f"{field} must be UUIDv4")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidEvidenceRequirement(f"{field} must be a non-empty string")
    return value.strip()


# duplicate-code: Configuration owns this domain validation and failure type;
# sharing it across bounded contexts would couple independent domain semantics.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise InvalidEvidenceRequirement(f"{field} must be timezone-aware")


# arid: enable


@dataclass(frozen=True, slots=True)
class EvidenceRequirementSetId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceRequirementSetId.value")


@dataclass(frozen=True, slots=True)
class EvidenceRequirementSetVersionId:
    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceRequirementSetVersionId.value")


@dataclass(frozen=True, slots=True)
class EvidenceRequirementId:
    """Dependent identity meaningful only with its requirement-set identity."""

    value: UUID

    def __post_init__(self) -> None:
        _uuid4(self.value, "EvidenceRequirementId.value")


@dataclass(frozen=True, slots=True)
class InvestmentHorizon:
    """Explicit ex-ante horizon without manufacturing a single time shape."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _text(self.value, "InvestmentHorizon.value"))


class EvidenceRequirementPredecessorEffect(StrEnum):
    CORRECTS = "corrects"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True, slots=True)
class EvidenceRequirementTargetAssignment:
    """Family-wide or owner-specific target applicability assignment."""

    family: EvidenceJudgmentFamily
    target: EvidenceJudgmentRef | None = None

    def __post_init__(self) -> None:
        if type(self.family) is not EvidenceJudgmentFamily:
            raise TypeError("family must be EvidenceJudgmentFamily")
        if self.target is not None:
            if not is_evidence_judgment_ref(self.target):
                raise TypeError("target must be an EvidenceJudgmentRef or None")
            if evidence_judgment_family(self.target) is not self.family:
                raise InvalidEvidenceRequirement(
                    "target family must match the owner-specific target identity"
                )


@dataclass(frozen=True, slots=True)
class EvidenceRequirementScopeAssignment:
    kind: EvidenceScopeKind
    claim_id: ClaimId | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not EvidenceScopeKind:
            raise TypeError("kind must be EvidenceScopeKind")
        if self.claim_id is not None and type(self.claim_id) is not ClaimId:
            raise TypeError("claim_id must be ClaimId or None")
        if self.kind is EvidenceScopeKind.JUDGMENT_WIDE and self.claim_id is not None:
            raise InvalidEvidenceRequirement(
                "judgment-wide applicability cannot identify a claim"
            )


@dataclass(frozen=True, slots=True)
class EvidenceRequirementApplicabilityKey:
    # duplicate-code: keys and assignments intentionally expose the same typed
    # coordinates but enforce different exactness rules; inheritance would hide them.
    # arid: disable
    target: EvidenceJudgmentRef
    scope: EvidenceScope
    evidence_use: EvidenceUse
    subject: EvidenceSubjectReference | None = None
    portfolio_id: PortfolioId | None = None
    instrument_id: FinancialInstrumentId | None = None
    investment_horizon: InvestmentHorizon | None = None
    # arid: enable

    def __post_init__(self) -> None:
        _validate_coordinates(self)


@dataclass(frozen=True, slots=True)
class EvidenceRequirementApplicabilityAssignment:
    # duplicate-code: assignment coordinates remain explicit because their
    # family-wide matching semantics may evolve independently from exact keys.
    # arid: disable
    target: EvidenceRequirementTargetAssignment
    scope: EvidenceRequirementScopeAssignment
    evidence_use: EvidenceUse
    subject: EvidenceSubjectReference | None = None
    portfolio_id: PortfolioId | None = None
    instrument_id: FinancialInstrumentId | None = None
    investment_horizon: InvestmentHorizon | None = None
    # arid: enable

    def __post_init__(self) -> None:
        _validate_coordinates(self)
        if self.scope.claim_id is not None and self.target.target is None:
            raise InvalidEvidenceRequirement(
                "claim-specific assignment requires an exact target"
            )

    def matches(self, key: EvidenceRequirementApplicabilityKey) -> bool:
        return all(
            assignment is None or assignment == actual
            for assignment, actual in (
                (self.target.target, key.target),
                (
                    self.scope.claim_id,
                    (
                        key.scope.claim_id
                        if type(key.scope) is ClaimSpecificEvidenceScope
                        else None
                    ),
                ),
                (self.subject, key.subject),
                (self.portfolio_id, key.portfolio_id),
                (self.instrument_id, key.instrument_id),
                (self.investment_horizon, key.investment_horizon),
            )
        ) and (
            self.target.family is evidence_judgment_family(key.target)
            and self.scope.kind is evidence_scope_kind(key.scope)
            and self.evidence_use is key.evidence_use
        )


def _validate_coordinates(
    value: EvidenceRequirementApplicabilityAssignment
    | EvidenceRequirementApplicabilityKey,
) -> None:
    if isinstance(value, EvidenceRequirementApplicabilityAssignment):
        if type(value.target) is not EvidenceRequirementTargetAssignment:
            raise TypeError("target must be EvidenceRequirementTargetAssignment")
        if type(value.scope) is not EvidenceRequirementScopeAssignment:
            raise TypeError("scope must be EvidenceRequirementScopeAssignment")
    else:
        if not is_evidence_judgment_ref(value.target):
            raise TypeError("target must be an EvidenceJudgmentRef")
        evidence_scope_kind(value.scope)
    if type(value.evidence_use) is not EvidenceUse:
        raise TypeError("evidence_use must be EvidenceUse")
    optional_types = (
        (value.subject, EvidenceSubjectReference, "subject"),
        (value.portfolio_id, PortfolioId, "portfolio_id"),
        (value.instrument_id, FinancialInstrumentId, "instrument_id"),
        (value.investment_horizon, InvestmentHorizon, "investment_horizon"),
    )
    for coordinate, expected, field in optional_types:
        if coordinate is not None and type(coordinate) is not expected:
            raise TypeError(f"{field} must be {expected.__name__} or None")


@dataclass(frozen=True, slots=True)
class FreshnessRequirementDefinition:
    requirement_id: EvidenceRequirementId
    maximum_age: timedelta

    def __post_init__(self) -> None:
        if type(self.requirement_id) is not EvidenceRequirementId:
            raise TypeError("requirement_id must be EvidenceRequirementId")
        if (
            not isinstance(self.maximum_age, timedelta)
            or self.maximum_age <= timedelta()
        ):
            raise InvalidEvidenceRequirement("maximum_age must be positive")

    @property
    def semantic_predicate(self) -> tuple[str, int]:
        return (
            "freshness",
            self.maximum_age // timedelta(microseconds=1),
        )


@dataclass(frozen=True, slots=True)
class SufficiencyRequirementDefinition:
    requirement_id: EvidenceRequirementId
    predicate: str

    def __post_init__(self) -> None:
        if type(self.requirement_id) is not EvidenceRequirementId:
            raise TypeError("requirement_id must be EvidenceRequirementId")
        object.__setattr__(
            self,
            "predicate",
            _text(self.predicate, "SufficiencyRequirementDefinition.predicate"),
        )

    @property
    def semantic_predicate(self) -> tuple[str, str]:
        return ("sufficiency", self.predicate)


type EvidenceRequirementDefinition = (
    FreshnessRequirementDefinition | SufficiencyRequirementDefinition
)


@dataclass(frozen=True, slots=True)
class ConfigurationAuthority:
    authority_identity: str
    source_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "authority_identity",
            _text(self.authority_identity, "ConfigurationAuthority.authority_identity"),
        )
        object.__setattr__(
            self,
            "source_reference",
            _text(self.source_reference, "ConfigurationAuthority.source_reference"),
        )


@dataclass(frozen=True, slots=True)
class EvidenceRequirementPredecessor:
    version_id: EvidenceRequirementSetVersionId
    effect: EvidenceRequirementPredecessorEffect

    def __post_init__(self) -> None:
        if type(self.version_id) is not EvidenceRequirementSetVersionId:
            raise TypeError("version_id must be EvidenceRequirementSetVersionId")
        if type(self.effect) is not EvidenceRequirementPredecessorEffect:
            raise TypeError("effect must be EvidenceRequirementPredecessorEffect")


@dataclass(frozen=True, slots=True)
class EvidenceRequirementSetVersion:
    set_id: EvidenceRequirementSetId
    version_id: EvidenceRequirementSetVersionId
    authority: ConfigurationAuthority
    effective_at: datetime
    recorded_at: datetime
    applicability: EvidenceRequirementApplicabilityAssignment
    requirements: tuple[EvidenceRequirementDefinition, ...]
    predecessor: EvidenceRequirementPredecessor | None = None

    def __post_init__(self) -> None:
        if type(self.set_id) is not EvidenceRequirementSetId:
            raise TypeError("set_id must be EvidenceRequirementSetId")
        if type(self.version_id) is not EvidenceRequirementSetVersionId:
            raise TypeError("version_id must be EvidenceRequirementSetVersionId")
        if type(self.authority) is not ConfigurationAuthority:
            raise TypeError("authority must be ConfigurationAuthority")
        if type(self.applicability) is not EvidenceRequirementApplicabilityAssignment:
            raise TypeError(
                "applicability must be EvidenceRequirementApplicabilityAssignment"
            )
        _aware(self.effective_at, "EvidenceRequirementSetVersion.effective_at")
        _aware(self.recorded_at, "EvidenceRequirementSetVersion.recorded_at")
        if not isinstance(self.requirements, tuple) or any(
            type(requirement)
            not in (FreshnessRequirementDefinition, SufficiencyRequirementDefinition)
            for requirement in self.requirements
        ):
            raise TypeError("requirements must be a tuple of requirement definitions")
        ids = [requirement.requirement_id for requirement in self.requirements]
        if len(ids) != len(set(ids)):
            raise InvalidEvidenceRequirement(
                "a complete version cannot repeat a requirement identity"
            )
        freshness_count = sum(
            isinstance(requirement, FreshnessRequirementDefinition)
            for requirement in self.requirements
        )
        if freshness_count > 1:
            raise InvalidEvidenceRequirement(
                "one applicability assignment cannot define multiple "
                "freshness requirements"
            )
        if (
            self.predecessor is not None
            and type(self.predecessor) is not EvidenceRequirementPredecessor
        ):
            raise TypeError(
                "predecessor must be EvidenceRequirementPredecessor or None"
            )
        if (
            self.predecessor is not None
            and self.predecessor.version_id == self.version_id
        ):
            raise InvalidEvidenceRequirement("a version cannot precede itself")


def validate_requirement_history(
    versions: tuple[EvidenceRequirementSetVersion, ...],
) -> None:
    by_id = _index_versions(versions)
    _validate_predecessors(versions, by_id)
    _validate_requirement_identity(versions)
    _validate_roots(versions)
    _validate_acyclic(versions, by_id)


def _index_versions(
    versions: tuple[EvidenceRequirementSetVersion, ...],
) -> dict[EvidenceRequirementSetVersionId, EvidenceRequirementSetVersion]:
    by_id: dict[EvidenceRequirementSetVersionId, EvidenceRequirementSetVersion] = {}
    for version in versions:
        if version.version_id in by_id:
            raise InvalidEvidenceRequirementHistory(
                "duplicate requirement version identity"
            )
        by_id[version.version_id] = version
    return by_id


def _validate_predecessors(
    versions: tuple[EvidenceRequirementSetVersion, ...],
    by_id: dict[EvidenceRequirementSetVersionId, EvidenceRequirementSetVersion],
) -> None:
    for version in versions:
        predecessor = version.predecessor
        if predecessor is None:
            continue
        prior = by_id.get(predecessor.version_id)
        if prior is None:
            raise InvalidEvidenceRequirementHistory("missing predecessor version")
        if prior.set_id != version.set_id:
            raise InvalidEvidenceRequirementHistory("cross-set predecessor version")
        if version.recorded_at < prior.recorded_at:
            raise InvalidEvidenceRequirementHistory(
                "requirement history recording time regressed"
            )
        if (
            predecessor.effect is EvidenceRequirementPredecessorEffect.CORRECTS
            and version.authority.authority_identity
            != prior.authority.authority_identity
        ):
            raise InvalidEvidenceRequirementHistory(
                "CORRECTS must retain configuration authority"
            )
        if (
            predecessor.effect is EvidenceRequirementPredecessorEffect.SUPERSEDES
            and version.effective_at < version.recorded_at
        ):
            raise InvalidEvidenceRequirementHistory(
                "SUPERSEDES must be prospective at recording time"
            )


def _validate_requirement_identity(
    versions: tuple[EvidenceRequirementSetVersion, ...],
) -> None:
    predicates: dict[
        tuple[EvidenceRequirementSetId, EvidenceRequirementId], tuple[str, object]
    ] = {}
    for version in versions:
        for requirement in version.requirements:
            key = (version.set_id, requirement.requirement_id)
            predicate = requirement.semantic_predicate
            prior_predicate = predicates.setdefault(key, predicate)
            if prior_predicate != predicate:
                raise InvalidEvidenceRequirementHistory(
                    "requirement identity changed semantic predicate"
                )


def _validate_roots(
    versions: tuple[EvidenceRequirementSetVersion, ...],
) -> None:
    roots: dict[EvidenceRequirementSetId, int] = {}
    for version in versions:
        if version.predecessor is None:
            roots[version.set_id] = roots.get(version.set_id, 0) + 1
    if any(count != 1 for count in roots.values()) or set(roots) != {
        version.set_id for version in versions
    }:
        raise InvalidEvidenceRequirementHistory(
            "each requirement set must have exactly one root version"
        )


def _validate_acyclic(
    versions: tuple[EvidenceRequirementSetVersion, ...],
    by_id: dict[EvidenceRequirementSetVersionId, EvidenceRequirementSetVersion],
) -> None:
    for version in versions:
        seen: set[EvidenceRequirementSetVersionId] = set()
        current = version
        while current.predecessor is not None:
            if current.version_id in seen:
                raise InvalidEvidenceRequirementHistory("cyclic requirement history")
            seen.add(current.version_id)
            current = by_id[current.predecessor.version_id]
