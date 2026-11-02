from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from polaris.application.evidence.context_versions import (
    ContextNoBasis,
    ContextNoBasisReason,
    ResolvedContextSelection,
)
from polaris.application.evidence.owner_meaning import (
    CanonicalContextMeaning,
    OwnerCauseVerdict,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningResolver,
    OwnerMeaningWitness,
)
from polaris.application.governance_context import (
    GovernanceContextMeaningReader,
    GovernanceContextOwner,
    GovernanceOwnerReadUnavailable,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.decisions import (
    HumanInvestmentDecisionEffect,
    InvestmentDecisionId,
)
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextSelectionRole,
    InvestmentAuthorityRegimeId,
)
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    HumanInvestmentDecisionRef,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
)
from polaris.domain.governance_authority import (
    InvestmentAuthorityPower,
    InvestmentAuthorityRegime,
)
from polaris.domain.governance_judgment_history import HumanDecisionTargetHistory
from polaris.domain.governance_regime_history import (
    AuthorityRegimeCorrectionDraft,
    AuthorityRegimeHistory,
    AuthorityRegimeStatus,
    InvalidAuthorityRegimeHistory,
)
from polaris.domain.human_investment_decision import HumanInvestmentDecision
from polaris.domain.investment_intelligence import EconomicDisposition
from polaris.domain.portfolio import PortfolioId

AT = datetime(2026, 11, 1, 12, tzinfo=UTC)


class _RegimeStore:
    def __init__(self, history: AuthorityRegimeHistory) -> None:
        self.history = history

    async def load(
        self, root: InvestmentAuthorityRegimeId
    ) -> AuthorityRegimeHistory | None:
        return self.history if self.history.root.regime_id == root else None


class _TargetStore:
    def __init__(self, history: HumanDecisionTargetHistory) -> None:
        self.history = history

    async def load(
        self, root: HumanInvestmentDecisionRef
    ) -> HumanDecisionTargetHistory | None:
        return (
            self.history if self.history.root_assertion.decision_ref == root else None
        )


def _setup() -> tuple[
    BasisScopeKey, _RegimeStore, _TargetStore, InvestmentAuthorityRegime
]:
    decision_id = InvestmentDecisionId(uuid4())
    actor_id = ActorId(uuid4())
    portfolio_id = PortfolioId(uuid4())
    regime = InvestmentAuthorityRegime(
        InvestmentAuthorityRegimeId(uuid4()),
        actor_id,
        portfolio_id,
        InvestmentAuthorityPower.HUMAN_INVESTMENT_DECISION,
        AT - timedelta(days=1),
        None,
    )
    decision = HumanInvestmentDecision(
        HumanInvestmentDecisionRef(uuid4()),
        decision_id,
        portfolio_id,
        KnownActorAttribution(actor_id),
        AT,
        EconomicDisposition.HOLD,
        HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        regime.regime_id,
    )
    key = BasisScopeKey(
        decision_id,
        decision.decision_ref,
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )
    return (
        key,
        _RegimeStore(AuthorityRegimeHistory.form(regime, AT)),
        _TargetStore(HumanDecisionTargetHistory.form(decision, AT)),
        regime,
    )


def test_authority_context_revision_and_exact_selection_guard() -> None:
    async def scenario() -> None:
        key, regimes, targets, regime = _setup()
        owner = GovernanceContextOwner(regimes, targets)
        initial = await owner.read_at(
            # duplicate-code: Initial authority selection is a separate proof from
            # absence and unavailable authority; keep its query explicit.
            # arid: disable
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=AT,
        )
        # arid: enable
        assert isinstance(initial, ResolvedContextSelection)
        assert initial.facts[0].reference.revision.value == 1
        assert initial.guard.selected == frozenset({regime.regime_id})
        assert initial.guard.universe.target_revision is not None
        # duplicate-code: Revision and wrong-scope tests construct independent
        # corrective owner acts.
        # arid: disable
        correction = AuthorityRegimeCorrectionDraft(
            uuid4(),
            regime.regime_id,
            KnownActorAttribution(regime.actor_id),
            # arid: enable
            "verified provenance",
            AT,
            AuthorityRegimeStatus.DETERMINATE,
            regime,
        )
        later = AT + timedelta(seconds=1)
        regimes.history = regimes.history.append(correction.at_boundary(later))
        updated = await owner.read_at(
            # duplicate-code: Revision and wrong-scope tests independently query the
            # owner at their chosen cutoffs.
            # arid: disable
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=later,
            known_at=later,
        )
        # arid: enable
        assert isinstance(updated, ResolvedContextSelection)
        assert updated.facts[0].reference.revision.value == 2
        assert updated.guard == initial.guard
        assert updated.facts[0].reference != initial.facts[0].reference

    asyncio.run(scenario())


def test_wrong_scope_and_contested_authority_fail_closed() -> None:
    async def scenario() -> None:
        key, regimes, targets, regime = _setup()
        owner = GovernanceContextOwner(regimes, targets)
        later = AT + timedelta(seconds=1)
        correction = AuthorityRegimeCorrectionDraft(
            uuid4(),
            regime.regime_id,
            KnownActorAttribution(regime.actor_id),
            "scope removed",
            AT,
            AuthorityRegimeStatus.DETERMINATE,
            replace(regime, portfolio_id=PortfolioId(uuid4())),
        )
        regimes.history = regimes.history.append(correction.at_boundary(later))
        result = await owner.read_at(
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=later,
            known_at=later,
        )
        assert isinstance(result, ContextNoBasis)
        assert result.reason is ContextNoBasisReason.MISSING_REQUIRED
        contested = AuthorityRegimeCorrectionDraft(
            uuid4(),
            regime.regime_id,
            KnownActorAttribution(regime.actor_id),
            "contested power",
            AT,
            AuthorityRegimeStatus.CONTESTED,
            None,
        )
        regimes.history = regimes.history.append(
            contested.at_boundary(later + timedelta(seconds=1))
        )
        result = await owner.read_at(
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=later + timedelta(seconds=1),
            known_at=later + timedelta(seconds=1),
        )
        assert isinstance(result, ContextNoBasis)
        assert result.reason is ContextNoBasisReason.CONTESTED

    asyncio.run(scenario())


def test_nonhuman_target_has_typed_absence_and_owner_meaning_proof() -> None:
    async def scenario() -> None:
        key, regimes, targets, _ = _setup()
        key = BasisScopeKey(
            key.decision_id,
            InvestmentViewRef(uuid4()),
            JudgmentWideEvidenceScope(),
            EvidenceUse.JUDGMENT_BASIS,
        )
        owner = GovernanceContextOwner(regimes, targets)
        selection = await owner.read_at(
            # duplicate-code: Typed absence and meaning-witness proof must remain
            # explicit independently of unavailable-read falsification.
            # arid: disable
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=AT,
        )
        assert isinstance(selection, ResolvedContextSelection)
        assert not selection.facts and not selection.guard.selected

        human_key, regimes, targets, _ = _setup()
        selection = await GovernanceContextOwner(regimes, targets).read_at(
            human_key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=AT,
        )
        assert isinstance(selection, ResolvedContextSelection)
        subject = CanonicalContextMeaning(
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            selection.facts[0].reference,
            selection.guard,
        )
        # arid: enable
        resolver = OwnerMeaningResolver(
            GovernanceContextMeaningReader(regimes, targets)
        )
        witness = await resolver.read_current(human_key, subject, at=AT)
        assert isinstance(witness, OwnerMeaningWitness)
        assert await resolver.verify(witness, validation_at=AT) == witness
        assert (
            await GovernanceContextMeaningReader(regimes, targets).verify_cause(
                witness, validation_at=AT
            )
            is OwnerCauseVerdict.VALID
        )

    asyncio.run(scenario())


def test_authority_owner_read_unavailable_fails_closed() -> None:
    class UnavailableRegimes(_RegimeStore):
        async def load(
            self, root: InvestmentAuthorityRegimeId
        ) -> AuthorityRegimeHistory | None:
            raise GovernanceOwnerReadUnavailable("history temporarily unavailable")

    async def scenario() -> None:
        key, regimes, targets, _ = _setup()
        unavailable = UnavailableRegimes(regimes.history)
        result = await GovernanceContextOwner(unavailable, targets).read_at(
            # duplicate-code: Unavailable-read falsification separately constructs the
            # subject whose second owner read fails.
            # arid: disable
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=AT,
        )
        assert isinstance(result, ContextNoBasis)
        assert result.reason is ContextNoBasisReason.UNAVAILABLE_AUTHORITY

        selection = await GovernanceContextOwner(regimes, targets).read_at(
            key,
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            effective_at=AT,
            known_at=AT,
        )
        assert isinstance(selection, ResolvedContextSelection)
        subject = CanonicalContextMeaning(
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            selection.facts[0].reference,
            selection.guard,
        )
        # arid: enable

        class FailingSecondRead(_RegimeStore):
            def __init__(self, history: AuthorityRegimeHistory) -> None:
                super().__init__(history)
                self.calls = 0

            async def load(
                self, root: InvestmentAuthorityRegimeId
            ) -> AuthorityRegimeHistory | None:
                self.calls += 1
                if self.calls == 2:
                    raise GovernanceOwnerReadUnavailable("history read failed")
                return await super().load(root)

        result = await GovernanceContextMeaningReader(
            FailingSecondRead(regimes.history), targets
        ).read_at(key, subject, effective_at=AT, known_at=AT, read_at=AT)
        assert isinstance(result, OwnerMeaningNoBasis)
        assert result.reason is OwnerMeaningNoBasisReason.UNAVAILABLE

    asyncio.run(scenario())


def test_missing_invalid_and_wrong_time_authority_fail_closed() -> None:
    class InvalidRegimes(_RegimeStore):
        async def load(
            self, root: InvestmentAuthorityRegimeId
        ) -> AuthorityRegimeHistory | None:
            raise InvalidAuthorityRegimeHistory("broken owner ancestry")

    async def scenario() -> None:
        key, regimes, targets, regime = _setup()
        role = ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME
        missing = await GovernanceContextOwner(
            _RegimeStore(
                AuthorityRegimeHistory.form(
                    replace(regime, regime_id=InvestmentAuthorityRegimeId(uuid4())), AT
                )
            ),
            targets,
        ).read_at(key, role, effective_at=AT, known_at=AT)
        assert isinstance(missing, ContextNoBasis)
        assert missing.reason is ContextNoBasisReason.MISSING_REQUIRED

        invalid = await GovernanceContextOwner(
            InvalidRegimes(regimes.history), targets
        ).read_at(key, role, effective_at=AT, known_at=AT)
        assert isinstance(invalid, ContextNoBasis)
        assert invalid.reason is ContextNoBasisReason.INVALID_HISTORY

        regimes.history = AuthorityRegimeHistory.form(
            replace(regime, effective_from=AT + timedelta(seconds=1)), AT
        )
        wrong_time = await GovernanceContextOwner(regimes, targets).read_at(
            key, role, effective_at=AT, known_at=AT
        )
        assert isinstance(wrong_time, ContextNoBasis)
        assert wrong_time.reason is ContextNoBasisReason.MISSING_REQUIRED

    asyncio.run(scenario())
