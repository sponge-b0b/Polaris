from __future__ import annotations

import pytest

from core.runtime.state.runtime_context import RuntimeContext
from domain.authority import RiskTier
from intelligence.portfolio.management.portfolio_manager_agent import (
    PortfolioManagerAgent,
)
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.synthesis.contracts import (
    StrategyHypothesisEvaluation,
    StrategySynthesisDecision,
    StrategySynthesisDegradedReason,
    StrategySynthesisSelectionStatus,
)


@pytest.mark.asyncio
async def test_portfolio_manager_rejects_restricted_account_state() -> None:
    output = await PortfolioManagerAgent()._execute(
        _runtime_context(
            decision=_decision_payload(
                selected_perspective=StrategyPerspective.BULL,
                directional_score=0.25,
                confidence=0.80,
                regime="risk_on",
                synthesis_weights={
                    StrategyPerspective.BULL: 0.50,
                    StrategyPerspective.BEAR: 0.20,
                    StrategyPerspective.SIDEWAYS: 0.30,
                },
            ),
            portfolio_risk_features={
                "portfolio_heat": 0.20,
                "risk_intensity": 0.25,
                "margin_utilization_ratio": 0.15,
                "trading_blocked": True,
                "account_blocked": False,
                "trade_suspended_by_user": False,
            },
        )
    )

    features = output.outputs["features"]
    assert features["execution_status"] == "rejected"
    assert features["scale_factor"] == 0.0
    assert features["account_restricted"] is True
    assert features["composite_risk"] == 1.0
    assert features["synthesis_execution_blocked"] is False
    assert "account_restricted" in output.outputs["risks"]
    assert "respect_account_restrictions" in output.outputs["recommendations"]


@pytest.mark.asyncio
async def test_portfolio_manager_uses_selected_decision_not_legacy_weights() -> None:
    output = await PortfolioManagerAgent()._execute(
        _runtime_context(
            decision=_decision_payload(
                selected_perspective=StrategyPerspective.SIDEWAYS,
                directional_score=0.0,
                confidence=0.86,
                regime="sideways",
                synthesis_weights={
                    StrategyPerspective.BULL: 0.05,
                    StrategyPerspective.BEAR: 0.10,
                    StrategyPerspective.SIDEWAYS: 0.85,
                },
            ),
            legacy_features={
                "bull_weight": 0.95,
                "bear_weight": 0.03,
                "sideways_weight": 0.02,
            },
            legacy_directional_score=0.95,
            legacy_regime="risk_on",
        )
    )

    features = output.outputs["features"]
    assert output.outputs["directional_score"] == 0.0
    assert output.outputs["regime"] == "balanced"
    assert features["target_allocation"] == {
        "bull": 0.05,
        "bear": 0.10,
        "sideways": 0.85,
    }
    assert features["hypothesis_synthesis_weights"] == features["target_allocation"]
    assert features["selected_perspective"] == "sideways"
    assert features["selection_status"] == "selected"
    assert features["synthesis_execution_blocked"] is False


@pytest.mark.asyncio
async def test_portfolio_manager_rejects_degraded_synthesis_decision() -> None:
    output = await PortfolioManagerAgent()._execute(
        _runtime_context(
            decision=_decision_payload(
                selected_perspective=None,
                selection_status=StrategySynthesisSelectionStatus.DEGRADED,
                degraded_reasons=(StrategySynthesisDegradedReason.TIED_CANDIDATES,),
                directional_score=0.0,
                confidence=0.42,
                regime="neutral",
                synthesis_weights={
                    StrategyPerspective.BULL: 0.34,
                    StrategyPerspective.BEAR: 0.33,
                    StrategyPerspective.SIDEWAYS: 0.33,
                },
            )
        )
    )

    features = output.outputs["features"]
    assert output.outputs["directional_score"] == 0.0
    assert features["execution_status"] == "rejected"
    assert features["scale_factor"] == 0.0
    assert features["selected_perspective"] is None
    assert features["selection_status"] == "degraded"
    assert features["synthesis_degraded_reasons"] == ["tied_candidates"]
    assert features["synthesis_execution_blocked"] is True
    assert "synthesis_unresolved" in output.outputs["risks"]
    assert (
        "resolve_strategy_synthesis_before_execution"
        in output.outputs["recommendations"]
    )


@pytest.mark.asyncio
async def test_portfolio_manager_classifies_allocation_intent_runtime_output() -> None:
    output = await PortfolioManagerAgent()._execute(
        _runtime_context(
            decision=_decision_payload(
                selected_perspective=StrategyPerspective.BULL,
                directional_score=0.25,
                confidence=0.80,
                regime="risk_on",
                synthesis_weights={
                    StrategyPerspective.BULL: 0.50,
                    StrategyPerspective.BEAR: 0.20,
                    StrategyPerspective.SIDEWAYS: 0.30,
                },
            )
        )
    )

    authority_metadata = output.execution_metadata["risk_authority"]
    assert authority_metadata["risk_tier"] == RiskTier.VIGILANT.value
    assert authority_metadata["authority_effect"] == ("deterministic_platform_decision")
    assert authority_metadata["intended_sink"] == "durable_domain_record"
    assert authority_metadata["capital_relevant"] is True
    assert authority_metadata["durable_authority"] is True


def _runtime_context(
    *,
    decision: dict[str, object],
    legacy_features: dict[str, object] | None = None,
    legacy_directional_score: float = 0.25,
    legacy_regime: str = "risk_on",
    portfolio_risk_features: dict[str, object] | None = None,
) -> RuntimeContext:
    synthesis_features: dict[str, object] = {
        "strategy_synthesis_decision": decision,
    }
    if legacy_features is not None:
        synthesis_features.update(legacy_features)
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "strategy_synthesis_agent": {
                "outputs": {
                    "directional_score": legacy_directional_score,
                    "confidence": 0.80,
                    "regime": legacy_regime,
                    "features": synthesis_features,
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "features": {
                        "composite_risk": 0.20,
                        "risk_pressure": 0.20,
                        "stability_score": 0.90,
                        "risk_regime": "stable",
                    }
                }
            },
            "portfolio_state_builder": {
                "outputs": {
                    "features": {
                        "risk_features": portfolio_risk_features
                        or {
                            "portfolio_heat": 0.20,
                            "risk_intensity": 0.25,
                            "margin_utilization_ratio": 0.15,
                            "trading_blocked": False,
                            "account_blocked": False,
                            "trade_suspended_by_user": False,
                        }
                    }
                }
            },
        },
    )


def _decision_payload(
    *,
    selected_perspective: StrategyPerspective | None,
    directional_score: float,
    confidence: float,
    regime: str,
    synthesis_weights: dict[StrategyPerspective, float],
    selection_status: StrategySynthesisSelectionStatus = (
        StrategySynthesisSelectionStatus.SELECTED
    ),
    degraded_reasons: tuple[StrategySynthesisDegradedReason, ...] = (),
) -> dict[str, object]:
    evaluations = tuple(
        _evaluation(
            perspective=perspective,
            synthesis_weight=synthesis_weights[perspective],
            rank=rank,
            selected_perspective=selected_perspective,
            decision_status=selection_status,
            degraded_reasons=degraded_reasons,
        )
        for rank, perspective in enumerate(
            (
                StrategyPerspective.BULL,
                StrategyPerspective.BEAR,
                StrategyPerspective.SIDEWAYS,
            ),
            start=1,
        )
    )
    return StrategySynthesisDecision(
        selected_perspective=selected_perspective,
        selection_status=selection_status,
        directional_score=directional_score,
        confidence=confidence,
        regime=regime,
        uncertainty=1.0 - confidence,
        evaluations=evaluations,
        degraded_reasons=degraded_reasons,
        thesis="Portfolio-manager test synthesis decision.",
        signals=("test_signal",),
        risks=(),
        recommendations=("test_recommendation",),
    ).to_dict()


def _evaluation(
    *,
    perspective: StrategyPerspective,
    synthesis_weight: float,
    rank: int,
    selected_perspective: StrategyPerspective | None,
    decision_status: StrategySynthesisSelectionStatus,
    degraded_reasons: tuple[StrategySynthesisDegradedReason, ...],
) -> StrategyHypothesisEvaluation:
    invalidated = decision_status is StrategySynthesisSelectionStatus.DEGRADED
    if invalidated:
        evaluation_status = StrategySynthesisSelectionStatus.DEGRADED
    elif perspective is selected_perspective:
        evaluation_status = StrategySynthesisSelectionStatus.SELECTED
    else:
        evaluation_status = StrategySynthesisSelectionStatus.REJECTED
    return StrategyHypothesisEvaluation(
        perspective=perspective,
        perspective_weight=synthesis_weight,
        contradiction_burden=0.0,
        assumption_support=1.0,
        invalidated=invalidated,
        candidate_score=synthesis_weight,
        synthesis_weight=synthesis_weight,
        rank=rank,
        selection_status=evaluation_status,
        degraded_reasons=degraded_reasons if invalidated else (),
    )
