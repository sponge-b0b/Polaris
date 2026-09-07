from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import cast

import pytest

from polaris.domain.investment_decisions import (
    ActorAttribution,
    BusinessBasis,
    BusinessReference,
    DecisionContinuity,
    DecisionInitiated,
    DecisionNeedAlreadyGrounded,
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    FactMetadata,
    IndependentChoiceRequiresNewDecision,
    InvalidDecisionHistory,
    InvalidDecisionIdentity,
    InvalidDecisionScope,
    InvestmentDecision,
    InvestmentDecisionId,
    OperationId,
    PortfolioRef,
    ScopeCompleteness,
    TechnicalProvenance,
    TechnicalReference,
    TriggerProvenance,
    find_reconciliation_requirements,
    initiate_decision,
    refine_scope,
    refine_subject,
)


def _metadata(sequence: int, *, workflow: str = "workflow-1") -> FactMetadata:
    moment = datetime(2026, 9, 6, 12, sequence, tzinfo=UTC)
    return FactMetadata(
        effective_at=moment,
        recorded_at=moment,
        recorded_sequence=sequence,
        operation_id=OperationId(f"operation-{sequence}"),
        actor=ActorAttribution("polaris", "polaris"),
        trigger=TriggerProvenance("attention", "attention-1"),
        technical=TechnicalProvenance(
            (
                TechnicalReference("workflow", workflow),
                TechnicalReference("model", "model-1"),
            )
        ),
        business_basis=BusinessBasis("decision-need", "need-1"),
        business_reference=BusinessReference("observation", "observation-1"),
    )


def _decision(
    *,
    decision: str = "decision-1",
    need: str = "need-1",
    sequence: int = 0,
) -> InvestmentDecision:
    return initiate_decision(
        decision_id=InvestmentDecisionId(decision),
        need_id=DecisionNeedId(need),
        subject=DecisionSubject("Evaluate whether to establish SPY exposure"),
        scope=DecisionScope.unresolved(),
        metadata=_metadata(sequence),
    )


def test_initiation_allows_unresolved_scope_without_portfolios() -> None:
    decision = _decision()

    assert decision.scope == DecisionScope((), ScopeCompleteness.UNRESOLVED)
    assert decision.decision_id == InvestmentDecisionId("decision-1")
    assert decision.need_id == DecisionNeedId("need-1")


def test_initiation_preserves_confirmed_partial_scope() -> None:
    portfolio = PortfolioRef("portfolio-a")
    scope = DecisionScope.unresolved(portfolio)

    decision = initiate_decision(
        decision_id=InvestmentDecisionId("decision-1"),
        need_id=DecisionNeedId("need-1"),
        subject=DecisionSubject("Evaluate SPY exposure"),
        scope=scope,
        metadata=_metadata(0),
    )

    assert decision.scope == scope
    assert decision.scope.portfolios == (portfolio,)
    assert decision.scope.completeness is ScopeCompleteness.UNRESOLVED


def test_established_scope_requires_at_least_one_real_portfolio() -> None:
    with pytest.raises(InvalidDecisionScope, match="at least one Portfolio"):
        DecisionScope.established()

    portfolio = PortfolioRef("portfolio-a")
    assert DecisionScope.established(portfolio).portfolios == (portfolio,)


def test_scope_rejects_duplicate_portfolio_references() -> None:
    portfolio = PortfolioRef("portfolio-a")

    with pytest.raises(InvalidDecisionScope, match="duplicate"):
        DecisionScope.unresolved(portfolio, portfolio)


def test_scope_and_history_require_immutable_collections() -> None:
    portfolio = PortfolioRef("portfolio-a")
    with pytest.raises(InvalidDecisionScope, match="immutable tuple"):
        DecisionScope(
            cast(tuple[PortfolioRef, ...], [portfolio]),
            ScopeCompleteness.UNRESOLVED,
        )

    original = _decision()
    with pytest.raises(InvalidDecisionHistory, match="immutable tuple"):
        InvestmentDecision(cast(tuple, list(original.facts)))


def test_need_reuse_returns_explicit_semantic_failure() -> None:
    existing = InvestmentDecisionId("existing-decision")

    with pytest.raises(DecisionNeedAlreadyGrounded) as error:
        initiate_decision(
            decision_id=InvestmentDecisionId("new-decision"),
            need_id=DecisionNeedId("need-1"),
            subject=DecisionSubject("Evaluate SPY exposure"),
            scope=DecisionScope.unresolved(),
            metadata=_metadata(0),
            existing_decision_for_need=existing,
        )

    assert error.value.existing_decision_id == existing


def test_subject_refinement_preserves_identity_for_same_choice() -> None:
    original = _decision()

    refined = refine_subject(
        original,
        subject=DecisionSubject("Evaluate whether to increase SPY exposure"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        metadata=_metadata(1),
    )

    assert refined.decision_id == original.decision_id
    assert refined.need_id == original.need_id
    assert refined.subject.meaning == "Evaluate whether to increase SPY exposure"
    assert len(refined.facts) == 2
    assert len(original.facts) == 1


def test_scope_refinement_preserves_identity_for_same_choice() -> None:
    original = _decision()
    portfolio = PortfolioRef("portfolio-a")

    refined = refine_scope(
        original,
        scope=DecisionScope.established(portfolio),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        metadata=_metadata(1),
    )

    assert refined.decision_id == original.decision_id
    assert refined.scope == DecisionScope.established(portfolio)
    assert original.scope == DecisionScope.unresolved()


@pytest.mark.parametrize("operation", ["subject", "scope"])
def test_independent_choice_requires_a_new_decision(operation: str) -> None:
    original = _decision()

    with pytest.raises(IndependentChoiceRequiresNewDecision):
        if operation == "subject":
            refine_subject(
                original,
                subject=DecisionSubject("Independent portfolio choice"),
                continuity=DecisionContinuity.INDEPENDENT_CHOICE,
                metadata=_metadata(1),
            )
        else:
            refine_scope(
                original,
                scope=DecisionScope.unresolved(PortfolioRef("portfolio-b")),
                continuity=DecisionContinuity.INDEPENDENT_CHOICE,
                metadata=_metadata(1),
            )


def test_fact_metadata_keeps_provenance_and_business_references_separate() -> None:
    metadata = _metadata(0)

    assert metadata.actor == ActorAttribution("polaris", "polaris")
    assert metadata.trigger == TriggerProvenance("attention", "attention-1")
    assert metadata.technical.references[0] == TechnicalReference(
        "workflow", "workflow-1"
    )
    assert metadata.business_basis == BusinessBasis("decision-need", "need-1")
    assert metadata.business_reference == BusinessReference(
        "observation", "observation-1"
    )


def test_technical_reference_cannot_substitute_for_decision_identity() -> None:
    with pytest.raises(InvalidDecisionIdentity, match="InvestmentDecisionId"):
        initiate_decision(
            decision_id=cast(
                InvestmentDecisionId,
                TechnicalReference("workflow", "workflow-1"),
            ),
            need_id=DecisionNeedId("need-1"),
            subject=DecisionSubject("Evaluate SPY exposure"),
            scope=DecisionScope.unresolved(),
            metadata=_metadata(0),
        )


def test_fact_construction_rejects_technical_decision_identity() -> None:
    with pytest.raises(InvalidDecisionIdentity, match="InvestmentDecisionId"):
        DecisionInitiated(
            decision_id=cast(
                InvestmentDecisionId,
                TechnicalReference("workflow", "workflow-1"),
            ),
            need_id=DecisionNeedId("need-1"),
            subject=DecisionSubject("Evaluate SPY exposure"),
            scope=DecisionScope.unresolved(),
            metadata=_metadata(0),
        )


def test_technical_provenance_does_not_determine_decision_identity() -> None:
    original = initiate_decision(
        decision_id=InvestmentDecisionId("decision-1"),
        need_id=DecisionNeedId("need-1"),
        subject=DecisionSubject("Evaluate SPY exposure"),
        scope=DecisionScope.unresolved(),
        metadata=_metadata(0, workflow="workflow-a"),
    )

    refined = refine_subject(
        original,
        subject=DecisionSubject("Refined SPY exposure choice"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        metadata=_metadata(1, workflow="workflow-b"),
    )

    assert refined.decision_id == original.decision_id
    assert original.facts[0].metadata.technical != refined.facts[1].metadata.technical


def test_current_state_is_derived_from_immutable_facts() -> None:
    original = _decision()
    refined = refine_subject(
        original,
        subject=DecisionSubject("Refined subject"),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        metadata=_metadata(1),
    )

    assert refined.subject == DecisionSubject("Refined subject")
    initiation = refined.facts[0]
    assert isinstance(initiation, DecisionInitiated)
    assert initiation.subject == original.subject
    attribute = "subject"
    with pytest.raises(FrozenInstanceError):
        setattr(initiation, attribute, DecisionSubject("mutated"))


def test_history_requires_strict_recorded_sequence() -> None:
    original = _decision(sequence=1)

    with pytest.raises(InvalidDecisionHistory, match="strictly increasing"):
        refine_subject(
            original,
            subject=DecisionSubject("Refined subject"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            metadata=_metadata(1),
        )


def test_historical_duplicates_are_preserved_and_require_reconciliation() -> None:
    first = _decision(decision="decision-a", need="need-shared")
    second = _decision(decision="decision-b", need="need-shared")
    unrelated = _decision(decision="decision-c", need="need-other")

    conflicts = find_reconciliation_requirements((first, second, unrelated))

    assert len(conflicts) == 1
    assert conflicts[0].need_id == DecisionNeedId("need-shared")
    assert conflicts[0].decision_ids == (
        InvestmentDecisionId("decision-a"),
        InvestmentDecisionId("decision-b"),
    )
    assert first.decision_id == InvestmentDecisionId("decision-a")
    assert second.decision_id == InvestmentDecisionId("decision-b")
