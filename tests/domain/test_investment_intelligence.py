from __future__ import annotations

import asyncio
from dataclasses import fields, replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from polaris.application.investment_intelligence import InvestmentIntelligenceService
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.configuration.evidence_requirements import InvestmentHorizon
from polaris.domain.decisions import DecisionVersion, InvestmentDecisionId, OperationId
from polaris.domain.evidence import EvidenceBindingId
from polaris.domain.evidence.judgments import (
    InvestmentHypothesisRef,
    InvestmentViewRef,
    MeaningfulChallengeResultRef,
)
from polaris.domain.investment_intelligence import (
    ChallengeDisposition,
    DecisionAlternative,
    DecisionAlternativeId,
    EconomicDisposition,
    InvalidInvestmentJudgment,
    InvestmentHypothesis,
    InvestmentView,
    MeaningfulChallengeResult,
    R3InvestmentSlice,
    require_minimum_alternatives,
)
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId
from polaris.infrastructure.persistence.postgresql.investment_intelligence import (
    _alternative_payload,
    _challenge_payload,
    _hypothesis_payload,
    _view_payload,
)

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _actor() -> KnownActorAttribution:
    return KnownActorAttribution(ActorId(uuid4()))


def _view() -> InvestmentView:
    return InvestmentView(
        InvestmentViewRef(uuid4()),
        InvestmentDecisionId(uuid4()),
        R3InvestmentSlice(
            PortfolioId(uuid4()),
            FinancialInstrumentId(uuid4()),
            InvestmentHorizon("three months"),
        ),
        "SPY exposure may warrant an increase",
        _actor(),
        NOW,
        (EvidenceBindingId(uuid4()),),
        ("liquidity remains adequate",),
        "market path is uncertain",
        "cash retention may be preferable",
        ("drawdown exceeds the stated threshold",),
        ("trend signal from observed market data",),
    )


def _challenge(view: InvestmentView) -> MeaningfulChallengeResult:
    return MeaningfulChallengeResult(
        MeaningfulChallengeResultRef(uuid4()),
        view.view_id,
        view.decision_id,
        _actor(),
        NOW,
        "The same trend may be a short-lived rebound",
        (EvidenceBindingId(uuid4()),),
        "The liquidity assumption may fail",
        ChallengeDisposition.QUALIFIED,
        "Conflicting observations leave the view conditional",
    )


def test_material_view_and_hypothesis_keep_typed_judgment_identity() -> None:
    view = _view()
    hypothesis = InvestmentHypothesis(
        InvestmentHypothesisRef(uuid4()),
        view.decision_id,
        "Liquidity supports increasing exposure",
        view.view_id,
        _actor(),
        NOW,
    )
    assert hypothesis.material_to == view.view_id
    assert view.slice.horizon.value == "three months"
    assert view.material_evidence
    with pytest.raises(InvalidInvestmentJudgment):
        InvestmentHypothesis(
            InvestmentHypothesisRef(uuid4()),
            view.decision_id,
            "transient thought",
            None,
            _actor(),
            NOW,  # type: ignore[arg-type]
        )


def test_boolean_only_challenge_cannot_be_durable() -> None:
    view = _view()
    challenge = _challenge(view)
    assert challenge.disposition is ChallengeDisposition.QUALIFIED
    with pytest.raises(InvalidInvestmentJudgment):
        replace(challenge, strongest_competing_interpretation="")
    with pytest.raises(InvalidInvestmentJudgment):
        replace(challenge, disposition=True)  # type: ignore[arg-type]


def test_first_slice_material_comparison_requires_three_choices() -> None:
    decision_id = InvestmentDecisionId(uuid4())
    instrument_id = FinancialInstrumentId(uuid4())
    alternatives = tuple(
        DecisionAlternative(
            DecisionAlternativeId(uuid4()),
            decision_id,
            instrument_id,
            InvestmentHorizon("three months"),
            disposition,
            f"Compare {disposition.value} exposure",
            _actor(),
            NOW,
        )
        for disposition in EconomicDisposition
    )
    require_minimum_alternatives(alternatives)
    with pytest.raises(InvalidInvestmentJudgment):
        require_minimum_alternatives(alternatives[:2])


def test_model_and_workflow_data_have_no_business_judgment_authority() -> None:
    view = _view()
    challenge = _challenge(view)
    hypothesis = InvestmentHypothesis(
        InvestmentHypothesisRef(uuid4()),
        view.decision_id,
        "material hypothesis",
        view.view_id,
        _actor(),
        NOW,
    )
    alternative = DecisionAlternative(
        DecisionAlternativeId(uuid4()),
        view.decision_id,
        view.slice.instrument_id,
        view.slice.horizon,
        EconomicDisposition.HOLD,
        "deliberate no action",
        _actor(),
        NOW,
    )
    canonical_fields = {
        field.name
        for judgment in (
            InvestmentHypothesis,
            InvestmentView,
            MeaningfulChallengeResult,
            DecisionAlternative,
        )
        for field in fields(judgment)
    }
    persisted_keys = (
        _view_payload(view)
        | _challenge_payload(challenge)
        | _hypothesis_payload(hypothesis)
        | _alternative_payload(alternative)
    ).keys()
    for name in (*canonical_fields, *persisted_keys):
        assert not any(
            token in name
            for token in (
                "provider",
                "workflow",
                "model",
                "adapter",
                "query",
                "trace",
            )
        )

    class UnusedStore:
        async def record_challenge(self, *_args: object) -> None:
            raise AssertionError("untrusted draft reached persistence")

    service = InvestmentIntelligenceService(UnusedStore())  # type: ignore[arg-type]
    with pytest.raises(InvalidInvestmentJudgment):
        asyncio.run(
            service.record_challenge(
                OperationId(uuid4()),
                {"challenged": True},  # type: ignore[arg-type]
                DecisionVersion(1),
            )
        )
