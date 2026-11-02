"""Governance-owned authority context for an exact R3 Evidence basis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from polaris.application.evidence.context_versions import (
    ContextContribution,
    ContextNoBasis,
    ContextNoBasisReason,
    ResolvedContextSelection,
    SelectedContextFact,
)
from polaris.application.evidence.owner_meaning import (
    CanonicalContextAbsence,
    CanonicalContextMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningCause,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
    context_no_basis_meaning_reason,
)
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextSelectionGuard,
    ContextSelectionRole,
    InvestmentAuthorityRegimeId,
)
from polaris.domain.evidence.judgments import HumanInvestmentDecisionRef
from polaris.domain.governance_authority import (
    InvestmentAuthorityCheck,
    InvestmentAuthorityPower,
    check_investment_authority,
)
from polaris.domain.governance_judgment_history import (
    HumanDecisionTargetHistory,
    HumanDecisionTargetNeedsReevaluation,
    HumanDecisionTargetNotKnown,
    HumanDecisionTargetSelection,
    HumanDecisionTargetStatus,
    InvalidHumanDecisionTargetHistory,
)
from polaris.domain.governance_regime_history import (
    AuthorityRegimeHistory,
    AuthorityRegimeNeedsReevaluation,
    AuthorityRegimeSelection,
    AuthorityRegimeStatus,
    InvalidAuthorityRegimeHistory,
)
from polaris.domain.human_investment_decision import HumanInvestmentDecision

AUTHORITY_ROLE = ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME


class GovernanceOwnerReadUnavailable(RuntimeError):
    """The Governance owner cannot attest its target or regime history."""


class GovernanceHistoryReader(Protocol):
    async def load(
        self, root: InvestmentAuthorityRegimeId
    ) -> AuthorityRegimeHistory | None: ...


class HumanDecisionHistoryReader(Protocol):
    async def load(
        self, root: HumanInvestmentDecisionRef
    ) -> HumanDecisionTargetHistory | None: ...


@dataclass(frozen=True, slots=True)
class AuthoritySelectionRelationship:
    key: BasisScopeKey
    role: ContextSelectionRole
    selected_root: InvestmentAuthorityRegimeId
    target_revision: object


@dataclass(frozen=True, slots=True)
class AuthoritySelectionUniverse:
    key: BasisScopeKey
    role: ContextSelectionRole
    target_revision: object | None
    regime_id: InvestmentAuthorityRegimeId | None


@dataclass(frozen=True, slots=True)
class AuthorityContextProvenance:
    root_known_at: datetime
    correction_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class AuthorityContextAbsence:
    """The exact non-Human-Decision target has no R3 authority-regime role."""

    target: object


class GovernanceContextOwner:
    """Resolve only the Governance authority role from complete owner history."""

    def __init__(
        self,
        regimes: GovernanceHistoryReader,
        targets: HumanDecisionHistoryReader,
    ) -> None:
        self._regimes = regimes
        self._targets = targets

    async def read_at(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ResolvedContextSelection[object, object, object, object] | ContextNoBasis:
        if type(key) is not BasisScopeKey or role is not AUTHORITY_ROLE:
            raise TypeError(
                "Governance context requires the authority role and typed key"
            )
        _aware(effective_at)
        _aware(known_at)

        def no_basis(reason: ContextNoBasisReason, detail: str) -> ContextNoBasis:
            return ContextNoBasis(key, role, effective_at, known_at, reason, detail)

        if type(key.target) is not HumanInvestmentDecisionRef:
            guard = _guard(key, None, None)
            return ResolvedContextSelection(
                key, role, effective_at, known_at, (), guard
            )
        try:
            target_selection = await _target_at(
                self._targets, key, effective_at, known_at
            )
            if isinstance(target_selection, ContextNoBasis):
                return target_selection
            assertion = target_selection.assertion
            assert assertion is not None
            regime_id = assertion.authority_regime_id
            resolved = await _authority_at(
                self._regimes, key, assertion, effective_at, known_at
            )
            if isinstance(resolved, ContextNoBasis):
                return resolved
            history, selection = resolved
            regime = selection.regime
            assert regime is not None
            guard = _guard(key, target_selection.version, regime_id)
            fact = SelectedContextFact(
                selection.reference,
                regime,
                (history.root.regime_id, *selection.support),
                assertion.made_at,
                AuthorityContextProvenance(history.root_known_at, selection.support),
                frozenset(
                    {
                        ContextContribution.APPLICABILITY,
                        ContextContribution.SUPPORT,
                        ContextContribution.PROVENANCE,
                    }
                ),
            )
            return ResolvedContextSelection(
                key, role, effective_at, known_at, (fact,), guard
            )
        except (
            HumanDecisionTargetNotKnown,
            AuthorityRegimeNeedsReevaluation,
            HumanDecisionTargetNeedsReevaluation,
        ):
            return no_basis(
                ContextNoBasisReason.INCOMPLETE_MEMBERSHIP,
                "owner meaning requires reevaluation",
            )
        except (
            InvalidHumanDecisionTargetHistory,
            InvalidAuthorityRegimeHistory,
            ValueError,
        ):
            return no_basis(
                ContextNoBasisReason.INVALID_HISTORY,
                "Governance owner history is invalid",
            )
        except GovernanceOwnerReadUnavailable as error:
            return no_basis(ContextNoBasisReason.UNAVAILABLE_AUTHORITY, str(error))


async def _target_at(
    targets: HumanDecisionHistoryReader,
    key: BasisScopeKey,
    effective_at: datetime,
    known_at: datetime,
) -> HumanDecisionTargetSelection | ContextNoBasis:
    def no_basis(reason: ContextNoBasisReason, detail: str) -> ContextNoBasis:
        return ContextNoBasis(
            key, AUTHORITY_ROLE, effective_at, known_at, reason, detail
        )

    assert isinstance(key.target, HumanInvestmentDecisionRef)
    target = await targets.load(key.target)
    if target is None:
        return no_basis(
            ContextNoBasisReason.MISSING_REQUIRED, "Human Decision target is missing"
        )
    selection = target.select(effective_at, known_at)
    if selection.status is HumanDecisionTargetStatus.CONTESTED:
        return no_basis(
            ContextNoBasisReason.CONTESTED, "Human Decision target is contested"
        )
    assertion = selection.assertion
    if assertion is None:
        return no_basis(
            ContextNoBasisReason.MISSING_REQUIRED,
            "Human Decision target is not determinate",
        )
    if assertion.investment_decision_id != key.decision_id:
        return no_basis(
            ContextNoBasisReason.INVALID_HISTORY,
            "Human Decision belongs to another Decision",
        )
    return selection


async def _authority_at(
    regimes: GovernanceHistoryReader,
    key: BasisScopeKey,
    assertion: HumanInvestmentDecision,
    effective_at: datetime,
    known_at: datetime,
) -> tuple[AuthorityRegimeHistory, AuthorityRegimeSelection] | ContextNoBasis:
    def no_basis(reason: ContextNoBasisReason, detail: str) -> ContextNoBasis:
        return ContextNoBasis(
            key, AUTHORITY_ROLE, effective_at, known_at, reason, detail
        )

    history = await regimes.load(assertion.authority_regime_id)
    if history is None:
        return no_basis(
            ContextNoBasisReason.MISSING_REQUIRED,
            "selected authority regime is missing",
        )
    selection = history.select(assertion.made_at, known_at)
    if selection is None or selection.status is AuthorityRegimeStatus.WITHDRAWN:
        return no_basis(
            ContextNoBasisReason.MISSING_REQUIRED, "authority is absent at the act time"
        )
    if selection.status is AuthorityRegimeStatus.CONTESTED:
        return no_basis(ContextNoBasisReason.CONTESTED, "authority is contested")
    regime = selection.regime
    if (
        regime is None
        or check_investment_authority(
            regime,
            assertion.actor,
            assertion.portfolio_id,
            InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
            assertion.made_at,
        )
        is not InvestmentAuthorityCheck.ESTABLISHED
    ):
        return no_basis(
            ContextNoBasisReason.MISSING_REQUIRED,
            "authority power or scope is unestablished",
        )
    return history, selection


def _guard(
    key: BasisScopeKey,
    target_revision: object | None,
    regime_id: InvestmentAuthorityRegimeId | None,
) -> ContextSelectionGuard:
    selected = frozenset() if regime_id is None else frozenset({regime_id})
    relationships = (
        frozenset()
        if regime_id is None
        else frozenset(
            {
                AuthoritySelectionRelationship(
                    key, AUTHORITY_ROLE, regime_id, target_revision
                )
            }
        )
    )
    return ContextSelectionGuard(
        key,
        AUTHORITY_ROLE,
        selected,
        relationships,
        AuthoritySelectionUniverse(key, AUTHORITY_ROLE, target_revision, regime_id),
    )


class GovernanceContextMeaningReader:
    """Attest and replay Governance's typed authority selection at `(T,K)`."""

    def __init__(
        self,
        regimes: GovernanceHistoryReader,
        targets: HumanDecisionHistoryReader,
    ) -> None:
        self._regimes = regimes
        self._targets = targets
        self._owner = GovernanceContextOwner(regimes, targets)

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> OwnerMeaningWitness | OwnerMeaningNoBasis:
        if (
            type(subject) not in (CanonicalContextMeaning, CanonicalContextAbsence)
            or subject.role is not AUTHORITY_ROLE
        ):
            raise TypeError("Governance meaning requires authority context subject")
        _aware(read_at)

        def no_basis(
            reason: OwnerMeaningNoBasisReason, detail: str
        ) -> OwnerMeaningNoBasis:
            return OwnerMeaningNoBasis(
                key, subject, effective_at, known_at, read_at, reason, detail
            )

        selection = await self._owner.read_at(
            key, AUTHORITY_ROLE, effective_at=effective_at, known_at=known_at
        )
        if isinstance(selection, ContextNoBasis):
            return no_basis(
                context_no_basis_meaning_reason(selection.reason), selection.detail
            )
        if selection.guard != subject.selection:
            return no_basis(
                OwnerMeaningNoBasisReason.INVALID_HISTORY,
                "authority selection guard differs",
            )
        if isinstance(subject, CanonicalContextMeaning):
            fact = next(
                (
                    item
                    for item in selection.facts
                    if item.reference == subject.reference
                ),
                # duplicate-code: Governance and Portfolio meaning readers have
                # independent owner facts; keep each missing-fact proof local.
                # arid: disable
                None,
            )
            if fact is None:
                return no_basis(
                    OwnerMeaningNoBasisReason.MISSING,
                    # arid: enable
                    "authority context reference is absent",
                )
            regime_id = subject.reference.root
            try:
                history = await self._regimes.load(regime_id)
            except GovernanceOwnerReadUnavailable as error:
                return no_basis(OwnerMeaningNoBasisReason.UNAVAILABLE, str(error))
            if history is None:
                return no_basis(
                    OwnerMeaningNoBasisReason.MISSING,
                    "authority history disappeared during meaning read",
                )
            meaning: object = fact.fact
            provenance: object = fact.provenance
            fact_ancestry: tuple[OwnerHistoryRecord[object], ...] = (
                OwnerHistoryRecord[object](
                    history.root, history.root.effective_from, history.root_known_at
                ),
            )
            correction_ancestry: tuple[OwnerHistoryRecord[object], ...] = tuple(
                OwnerHistoryRecord[object](item, item.effective_at, item.known_at)
                for item in history.corrections
                if item.known_at <= known_at
            )
        else:
            if selection.facts:
                return no_basis(
                    OwnerMeaningNoBasisReason.INVALID_HISTORY,
                    "authority absence contradicts selected fact",
                )
            meaning = AuthorityContextAbsence(key.target)
            provenance = selection.guard.universe
            fact_ancestry = ()
            correction_ancestry = ()
        # duplicate-code: Governance witness construction attests its own authority
        # cause; sharing with Decision would couple distinct owner proofs.
        # arid: disable
        return OwnerMeaningWitness(
            key,
            subject,
            effective_at,
            known_at,
            read_at,
            # arid: enable
            meaning,
            provenance,
            OwnerMeaningCause(
                fact_ancestry,
                correction_ancestry,
                (selection.guard,),
                True,
            ),
        )

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        _aware(validation_at)
        if type(witness) is not OwnerMeaningWitness or validation_at < witness.read_at:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        # duplicate-code: Governance replays its own authority history; sharing
        # verification with other owners would couple independent causes.
        # arid: disable
        reconstructed = await self.read_at(
            witness.key,
            witness.subject,
            effective_at=witness.effective_at,
            known_at=witness.known_at,
            read_at=witness.read_at,
        )
        if isinstance(reconstructed, OwnerMeaningNoBasis):
            return reconstructed.reason
        return (
            OwnerCauseVerdict.VALID
            if reconstructed == witness
            else OwnerMeaningNoBasisReason.INVALID_HISTORY
        )
        # arid: enable


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Governance context time must be timezone-aware")
