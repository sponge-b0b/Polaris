"""Closed owner-issued R3 canonical context references and selection scopes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable
from uuid import UUID

from polaris.domain.decisions.facts import DecisionVersion, InvestmentDecisionId

from .judgment_versions import (
    TargetJudgmentVersionRef,
    is_target_judgment_version_ref,
)
from .judgments import EvidenceJudgmentRef, EvidenceScope, EvidenceUse


@dataclass(frozen=True, slots=True)
class _ContextId:
    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise TypeError(f"{type(self).__name__}.value must be UUID")
        if self.value.version != 4:
            raise ValueError(f"{type(self).__name__}.value must be UUIDv4")


@dataclass(frozen=True, slots=True)
class _ContextRevision:
    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 1:
            raise ValueError(f"{type(self).__name__}.value must be positive")


@dataclass(frozen=True, slots=True)
class DecisionAlternativeId(_ContextId):
    """Investment Intelligence-owned Decision Alternative root."""


@dataclass(frozen=True, slots=True)
class DecisionAlternativeRevision(_ContextRevision):
    """Owner epoch for one Decision Alternative root."""


@dataclass(frozen=True, slots=True)
class PortfolioBoundaryId(_ContextId):
    """Portfolio & Risk-owned boundary root."""


@dataclass(frozen=True, slots=True)
class PortfolioBoundaryRevision(_ContextRevision):
    """Owner epoch for one Portfolio Boundary root."""


@dataclass(frozen=True, slots=True)
class PortfolioStateId(_ContextId):
    """One attributable actual Portfolio State, including its as-of basis."""


@dataclass(frozen=True, slots=True)
class PortfolioStateRevision(_ContextRevision):
    """Owner epoch for one actual Portfolio State root."""


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioStateId(_ContextId):
    """Portfolio & Risk-owned projected state root."""


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioStateRevision(_ContextRevision):
    """Owner epoch for one projected state root."""


@dataclass(frozen=True, slots=True)
class InvestmentMandateId(_ContextId):
    """Mandate root including applicable Objective and Principle meaning."""


@dataclass(frozen=True, slots=True)
class InvestmentMandateRevision(_ContextRevision):
    """Epoch of complete Mandate membership, content and applicability."""


@dataclass(frozen=True, slots=True)
class InvestmentStrategyId(_ContextId):
    """Portfolio & Risk-owned Strategy root."""


@dataclass(frozen=True, slots=True)
class InvestmentStrategyRevision(_ContextRevision):
    """Owner epoch for one Strategy root."""


@dataclass(frozen=True, slots=True)
class InvestmentAuthorityRegimeId(_ContextId):
    """Governance & Authority-owned power/scope regime root."""


@dataclass(frozen=True, slots=True)
class InvestmentAuthorityRegimeRevision(_ContextRevision):
    """Owner epoch for one authority regime root."""


@dataclass(frozen=True, slots=True)
class OutcomeId(_ContextId):
    """Learning-owned attributable Outcome root."""


@dataclass(frozen=True, slots=True)
class OutcomeRevision(_ContextRevision):
    """Owner epoch for one Outcome root."""


def _pair(
    root: object, root_type: type[object], revision: object, revision_type: type[object]
) -> None:
    if type(root) is not root_type:
        raise TypeError(f"root must be {root_type.__name__}")
    if type(revision) is not revision_type:
        raise TypeError(f"revision must be {revision_type.__name__}")


@dataclass(frozen=True, slots=True)
class DecisionContextVersionRef:
    root: InvestmentDecisionId
    revision: DecisionVersion

    def __post_init__(self) -> None:
        _pair(self.root, InvestmentDecisionId, self.revision, DecisionVersion)


@dataclass(frozen=True, slots=True)
class OtherJudgmentContextVersionRef:
    version: TargetJudgmentVersionRef

    def __post_init__(self) -> None:
        if not is_target_judgment_version_ref(self.version):
            raise TypeError("version must be TargetJudgmentVersionRef")


@dataclass(frozen=True, slots=True)
class DecisionAlternativeVersionRef:
    root: DecisionAlternativeId
    revision: DecisionAlternativeRevision

    def __post_init__(self) -> None:
        _pair(
            self.root, DecisionAlternativeId, self.revision, DecisionAlternativeRevision
        )


@dataclass(frozen=True, slots=True)
class PortfolioBoundaryVersionRef:
    root: PortfolioBoundaryId
    revision: PortfolioBoundaryRevision

    def __post_init__(self) -> None:
        _pair(self.root, PortfolioBoundaryId, self.revision, PortfolioBoundaryRevision)


@dataclass(frozen=True, slots=True)
class PortfolioStateVersionRef:
    root: PortfolioStateId
    revision: PortfolioStateRevision

    def __post_init__(self) -> None:
        _pair(self.root, PortfolioStateId, self.revision, PortfolioStateRevision)


@dataclass(frozen=True, slots=True)
class ProjectedPortfolioStateVersionRef:
    root: ProjectedPortfolioStateId
    revision: ProjectedPortfolioStateRevision

    def __post_init__(self) -> None:
        _pair(
            self.root,
            ProjectedPortfolioStateId,
            self.revision,
            ProjectedPortfolioStateRevision,
        )


@dataclass(frozen=True, slots=True)
class InvestmentMandateVersionRef:
    root: InvestmentMandateId
    revision: InvestmentMandateRevision

    def __post_init__(self) -> None:
        _pair(self.root, InvestmentMandateId, self.revision, InvestmentMandateRevision)


@dataclass(frozen=True, slots=True)
class InvestmentStrategyVersionRef:
    root: InvestmentStrategyId
    revision: InvestmentStrategyRevision

    def __post_init__(self) -> None:
        _pair(
            self.root, InvestmentStrategyId, self.revision, InvestmentStrategyRevision
        )


@dataclass(frozen=True, slots=True)
class InvestmentAuthorityRegimeVersionRef:
    root: InvestmentAuthorityRegimeId
    revision: InvestmentAuthorityRegimeRevision

    def __post_init__(self) -> None:
        _pair(
            self.root,
            InvestmentAuthorityRegimeId,
            self.revision,
            InvestmentAuthorityRegimeRevision,
        )


@dataclass(frozen=True, slots=True)
class OutcomeVersionRef:
    root: OutcomeId
    revision: OutcomeRevision

    def __post_init__(self) -> None:
        _pair(self.root, OutcomeId, self.revision, OutcomeRevision)


type CanonicalContextVersionRef = (
    DecisionContextVersionRef
    | OtherJudgmentContextVersionRef
    | DecisionAlternativeVersionRef
    | PortfolioBoundaryVersionRef
    | PortfolioStateVersionRef
    | ProjectedPortfolioStateVersionRef
    | InvestmentMandateVersionRef
    | InvestmentStrategyVersionRef
    | InvestmentAuthorityRegimeVersionRef
    | OutcomeVersionRef
)

type ContextRootRef = (
    InvestmentDecisionId
    | EvidenceJudgmentRef
    | DecisionAlternativeId
    | PortfolioBoundaryId
    | PortfolioStateId
    | ProjectedPortfolioStateId
    | InvestmentMandateId
    | InvestmentStrategyId
    | InvestmentAuthorityRegimeId
    | OutcomeId
)


class ContextSelectionRole(StrEnum):
    USED_PRIOR_DECISION = "used_prior_decision"
    OTHER_ADMITTED_JUDGMENT = "other_admitted_judgment"
    SELECTED_ALTERNATIVE = "selected_alternative"
    PORTFOLIO_BOUNDARY = "portfolio_boundary"
    ACTUAL_PORTFOLIO_STATE = "actual_portfolio_state"
    PROJECTED_PORTFOLIO_STATE = "projected_portfolio_state"
    INVESTMENT_MANDATE = "investment_mandate"
    INVESTMENT_STRATEGY = "investment_strategy"
    INVESTMENT_AUTHORITY_REGIME = "investment_authority_regime"
    OUTCOME = "outcome"


_REF_BY_ROLE: dict[ContextSelectionRole, tuple[type[object], type[object]]] = {
    ContextSelectionRole.USED_PRIOR_DECISION: (
        DecisionContextVersionRef,
        InvestmentDecisionId,
    ),
    ContextSelectionRole.OTHER_ADMITTED_JUDGMENT: (
        OtherJudgmentContextVersionRef,
        object,
    ),
    ContextSelectionRole.SELECTED_ALTERNATIVE: (
        DecisionAlternativeVersionRef,
        DecisionAlternativeId,
    ),
    ContextSelectionRole.PORTFOLIO_BOUNDARY: (
        PortfolioBoundaryVersionRef,
        PortfolioBoundaryId,
    ),
    ContextSelectionRole.ACTUAL_PORTFOLIO_STATE: (
        PortfolioStateVersionRef,
        PortfolioStateId,
    ),
    ContextSelectionRole.PROJECTED_PORTFOLIO_STATE: (
        ProjectedPortfolioStateVersionRef,
        ProjectedPortfolioStateId,
    ),
    ContextSelectionRole.INVESTMENT_MANDATE: (
        InvestmentMandateVersionRef,
        InvestmentMandateId,
    ),
    ContextSelectionRole.INVESTMENT_STRATEGY: (
        InvestmentStrategyVersionRef,
        InvestmentStrategyId,
    ),
    ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME: (
        InvestmentAuthorityRegimeVersionRef,
        InvestmentAuthorityRegimeId,
    ),
    ContextSelectionRole.OUTCOME: (OutcomeVersionRef, OutcomeId),
}


@dataclass(frozen=True, slots=True)
class BasisScopeKey:
    decision_id: InvestmentDecisionId
    target: EvidenceJudgmentRef
    scope: EvidenceScope
    use: EvidenceUse

    def __post_init__(self) -> None:
        from .judgments import evidence_scope_kind, is_evidence_judgment_ref

        if type(self.decision_id) is not InvestmentDecisionId:
            raise TypeError("decision_id must be InvestmentDecisionId")
        if not is_evidence_judgment_ref(self.target):
            raise TypeError("target must be EvidenceJudgmentRef")
        evidence_scope_kind(self.scope)
        if type(self.use) is not EvidenceUse:
            raise TypeError("use must be EvidenceUse")


@runtime_checkable
class ContextSelectionRelationship(Protocol):
    """Owner's immutable typed value identifying an exact selection relationship.

    Concrete owners retain their own relationship coordinates and lineage in the
    witness value. Application compares those values; no global relationship ID,
    kind/id pair, token, or Evidence-owned relationship fact is introduced.
    """

    @property
    def key(self) -> BasisScopeKey: ...

    @property
    def role(self) -> ContextSelectionRole: ...

    @property
    def selected_root(self) -> ContextRootRef: ...


@runtime_checkable
class ContextSelectionUniverseWitness(Protocol):
    """Owner's immutable typed value for the complete scoped selection universe.

    This value protects the selection and absence relationship even when the
    owner attests to no selected roots. Its concrete owner type retains exact
    relationship coordinates and lineage rather than a global Evidence token.
    """

    @property
    def key(self) -> BasisScopeKey: ...

    @property
    def role(self) -> ContextSelectionRole: ...


@dataclass(frozen=True, slots=True)
class ContextSelectionGuard:
    """Owner-attested complete selected set, including an empty set, for a role/key.

    Exact equality at a later T=K protects the selected relationship and its
    absence of additional current members. Replacement breaks equality even if
    the old root's revision is unchanged.
    """

    key: BasisScopeKey
    role: ContextSelectionRole
    selected: frozenset[ContextRootRef]
    relationships: frozenset[ContextSelectionRelationship]
    universe: ContextSelectionUniverseWitness

    def __post_init__(self) -> None:
        _validate_selection_scope(self.key, self.role)
        if type(self.selected) is not frozenset:
            raise TypeError("selected must be a frozenset")
        if type(self.relationships) is not frozenset:
            raise TypeError("relationships must be a frozenset")
        _validate_selection_universe(self.universe, self.key, self.role)
        _, expected_root = _REF_BY_ROLE[self.role]
        if self.role is ContextSelectionRole.OTHER_ADMITTED_JUDGMENT:
            from .judgments import is_evidence_judgment_ref

            if any(not is_evidence_judgment_ref(root) for root in self.selected):
                raise TypeError("selected roots must be EvidenceJudgmentRef")
            if self.key.target in self.selected:
                raise ValueError("exact Evidence target is not other judgment context")
        elif any(type(root) is not expected_root for root in self.selected):
            raise TypeError(f"selected roots must be {expected_root.__name__}")
        if (
            self.role is ContextSelectionRole.USED_PRIOR_DECISION
            and self.key.decision_id in self.selected
        ):
            raise ValueError("governing Decision is not used-prior context")
        if any(
            not isinstance(witness, ContextSelectionRelationship)
            or witness.key != self.key
            or witness.role != self.role
            or witness.selected_root not in self.selected
            for witness in self.relationships
        ):
            raise ValueError(
                "relationship witnesses must match exact key, role and root"
            )
        if frozenset(w.selected_root for w in self.relationships) != self.selected:
            raise ValueError("every selected root requires a relationship witness")


def _validate_selection_universe(
    universe: object, key: BasisScopeKey, role: ContextSelectionRole
) -> None:
    if (
        not isinstance(universe, ContextSelectionUniverseWitness)
        or universe.key != key
        or universe.role != role
    ):
        raise ValueError("selection universe must match exact key and role")


def context_root(reference: CanonicalContextVersionRef) -> ContextRootRef:
    """Return the owner-typed root without discarding the positive revision."""
    if isinstance(reference, OtherJudgmentContextVersionRef):
        return reference.version.root
    if is_canonical_context_version_ref(reference):
        return reference.root
    raise TypeError("reference must be CanonicalContextVersionRef")


def is_canonical_context_version_ref(value: object) -> bool:
    return any(type(value) is pair[0] for pair in _REF_BY_ROLE.values())


def _validate_selection_scope(key: object, role: object) -> None:
    if type(key) is not BasisScopeKey:
        raise TypeError("key must be BasisScopeKey")
    if type(role) is not ContextSelectionRole:
        raise TypeError("role must be ContextSelectionRole")
