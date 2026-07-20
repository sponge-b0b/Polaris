from __future__ import annotations

from math import isclose
from typing import Any, cast

import pytest

from application.services.base import ServiceRunner
from application.services.market_events.market_events_service import MarketEventsService
from config.strategy_model_config import StrategyModelConfig
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from intelligence.strategy.bear.bear_agent import BearAgent
from intelligence.strategy.bear.bear_hypothesis_policy import build_bear_hypothesis
from intelligence.strategy.bull.bull_agent import BullAgent
from intelligence.strategy.bull.bull_hypothesis_policy import build_bull_hypothesis
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)
from intelligence.strategy.sideways.sideways_agent import SidewaysAgent
from intelligence.strategy.sideways.sideways_hypothesis_policy import (
    build_sideways_hypothesis,
)
from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)
from intelligence.strategy.synthesis.strategy_synthesis_policy import (
    evaluate_strategy_hypothesis,
)


@pytest.mark.asyncio
async def test_perspective_agents_publish_reasoning_alias_metadata() -> None:
    config = StrategyModelConfig(
        perspective_reasoning_model="test-reasoning-alias",
        synthesis_model="test-synthesis-alias",
    )
    context = _perspective_runtime_context(_evidence_context())

    for agent, perspective in (
        (BullAgent(strategy_model_config=config), StrategyPerspective.BULL),
        (BearAgent(strategy_model_config=config), StrategyPerspective.BEAR),
        (SidewaysAgent(strategy_model_config=config), StrategyPerspective.SIDEWAYS),
    ):
        output = await agent._execute(context)

        assert (
            output.execution_metadata["strategy_model_role"] == "perspective_reasoning"
        )
        assert (
            output.execution_metadata["strategy_model_alias"] == "test-reasoning-alias"
        )
        assert output.execution_metadata["strategy_perspective"] == perspective.value
        assert output.execution_metadata["calculation_authority"] == "code"
        assert output.execution_metadata["llm_output_authority"] == "explanation_only"

        hypothesis = StrategyHypothesis.from_dict(
            cast(dict[str, object], output.outputs["strategy_hypothesis"])
        )
        assert hypothesis.perspective is perspective
        assert hypothesis.thesis
        assert hypothesis.supporting_evidence or hypothesis.contradicting_evidence
        assert hypothesis.key_assumptions
        assert hypothesis.invalidation_conditions


@pytest.mark.asyncio
async def test_strategy_synthesis_alias_preserves_code_owned_scores() -> None:
    config = StrategyModelConfig(
        perspective_reasoning_model="test-reasoning-alias",
        synthesis_model="test-synthesis-alias",
    )
    agent = StrategySynthesisAgent(
        events_service=MarketEventsService(events_provider=_NoEventsProvider()),
        service_runner=ServiceRunner(
            telemetry=ApplicationServiceTelemetry(
                observability_manager=ObservabilityManager()
            )
        ),
        intelligence_telemetry=cast(IntelligenceTelemetry, _FakeTelemetry()),
        strategy_model_config=config,
    )
    context = _synthesis_runtime_context(_evidence_context())

    output = await agent._execute(context)

    assert output.execution_metadata["strategy_model_role"] == "strategy_synthesis"
    assert output.execution_metadata["strategy_model_alias"] == "test-synthesis-alias"
    assert output.execution_metadata["calculation_authority"] == "code"
    assert output.execution_metadata["llm_output_authority"] == "explanation_only"

    hypotheses = {
        perspective: StrategyHypothesis.from_dict(
            cast(
                dict[str, object],
                context.node_outputs[f"{perspective.value}_agent"]["outputs"][
                    "strategy_hypothesis"
                ],
            )
        )
        for perspective in StrategyPerspective
    }
    features = cast(dict[str, object], output.outputs["features"])
    evaluations = cast(
        list[dict[str, object]],
        features["strategy_hypothesis_evaluations"],
    )
    candidate_scores = cast(
        dict[str, float],
        features["hypothesis_candidate_scores"],
    )
    selected_hypothesis = cast(
        dict[str, object],
        features["selected_hypothesis"],
    )
    assert str(features["thesis"]).startswith(str(selected_hypothesis["thesis"]))

    for evaluation in evaluations:
        perspective = StrategyPerspective(cast(str, evaluation["perspective"]))
        expected = evaluate_strategy_hypothesis(
            hypotheses[perspective],
            perspective_weight=cast(float, evaluation["perspective_weight"]),
        )
        actual_candidate_score = cast(float, evaluation["candidate_score"])
        assert isclose(
            actual_candidate_score,
            expected.candidate_score,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        assert isclose(
            candidate_scores[perspective.value],
            expected.candidate_score,
            rel_tol=0.0,
            abs_tol=1e-12,
        )


def test_invalidated_hypothesis_candidate_score_is_always_zero() -> None:
    evidence_context = _evidence_context(risk_pressure=0.95, volatility_score=0.95)
    hypothesis = build_bull_hypothesis(evidence_context).hypothesis

    evaluation = evaluate_strategy_hypothesis(hypothesis, perspective_weight=1.0)

    assert hypothesis.invalidated is True
    assert evaluation.candidate_score == 0.0
    assert evaluation.invalidated is True


class _NoEventsProvider:
    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return []

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return []

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        return []


class _FakeTelemetry:
    async def emit_agent_signal(
        self,
        **kwargs: object,
    ) -> None:
        return None


def _perspective_runtime_context(
    evidence_context: StrategyEvidenceContext,
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        workflow_inputs={"symbol": "SPY"},
        node_outputs={
            "strategy_evidence_builder": {
                "outputs": {
                    "strategy_evidence_context": evidence_context.to_dict(),
                    "evidence_fingerprint": evidence_context.evidence_fingerprint(),
                }
            }
        },
    )


def _synthesis_runtime_context(
    evidence_context: StrategyEvidenceContext,
) -> RuntimeContext:
    bull = build_bull_hypothesis(evidence_context).to_runtime_outputs()
    bear = build_bear_hypothesis(evidence_context).to_runtime_outputs()
    sideways = build_sideways_hypothesis(evidence_context).to_runtime_outputs()
    return RuntimeContext(
        runtime_id="runtime-strategy-alias",
        workflow_id="morning_report",
        execution_id="exec-strategy-alias",
        workflow_inputs={"symbol": "SPY"},
        node_outputs={
            "strategy_perspective_weighting_engine": {
                "outputs": {
                    "features": {
                        "bull_weight": 0.50,
                        "bear_weight": 0.20,
                        "sideways_weight": 0.30,
                    }
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "features": {
                        "risk_pressure": 0.10,
                        "adjusted_risk_pressure": 0.10,
                        "composite_risk": 0.10,
                    }
                }
            },
            "portfolio_state_builder": {
                "outputs": {
                    "features": {
                        "scale_factor": 1.0,
                        "status": "approved",
                    }
                }
            },
            "technical_agent": {
                "outputs": {
                    "features": {
                        "regime": {"regime": "bullish"},
                        "breadth_state": {
                            "has_breadth_data": True,
                            "breadth_regime": "strong_breadth",
                            "risk_regime": "stable",
                            "breadth_score": 0.50,
                            "breadth_risk_score": 0.20,
                            "participation_score": 0.40,
                            "leadership_score": 0.35,
                        },
                        "market_context": {
                            "top_50_constituents": ["AAPL", "MSFT"],
                        },
                    }
                }
            },
            "bull_agent": {"outputs": bull},
            "bear_agent": {"outputs": bear},
            "sideways_agent": {"outputs": sideways},
        },
    )


def _evidence_context(
    *,
    risk_pressure: float = 0.20,
    volatility_score: float = 0.30,
) -> StrategyEvidenceContext:
    return normalize_strategy_evidence_context(
        {
            "sentiment_agent": {
                "outputs": {
                    "directional_score": 0.62,
                    "confidence": 0.70,
                    "features": {
                        "momentum": 0.20,
                        "stability": 0.55,
                        "divergence": {"avg_divergence": 0.05},
                    },
                }
            },
            "technical_agent": {
                "outputs": {
                    "directional_score": 0.68,
                    "confidence": 0.72,
                    "features": {
                        "regime": {"regime": "bullish"},
                        "trend": {"trend_strength": 0.45},
                        "volatility": {
                            "volatility_score": volatility_score,
                            "volatility_regime": "normal",
                        },
                        "breadth_state": {
                            "has_breadth_data": True,
                            "breadth_regime": "strong_breadth",
                            "risk_regime": "stable",
                            "breadth_score": 0.48,
                            "breadth_risk_score": 0.20,
                            "participation_score": 0.35,
                            "leadership_score": 0.28,
                        },
                    },
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "confidence": 0.65,
                    "features": {
                        "risk_pressure": risk_pressure,
                        "composite_risk": risk_pressure,
                    },
                }
            },
            "fundamental_agent": {
                "outputs": {"directional_score": 0.42, "confidence": 0.58}
            },
            "news_agent": {"outputs": {"directional_score": 0.35, "confidence": 0.55}},
            "portfolio_state_builder": {
                "outputs": {
                    "confidence": 0.50,
                    "features": {
                        "scale_factor": 0.80,
                        "status": "risk_on",
                        "risk_features": {"portfolio_heat": 0.30},
                    },
                }
            },
            "market_events": {
                "outputs": {
                    "confidence": 0.60,
                    "features": {
                        "event_pressure": 0.20,
                        "event_bias": "risk_on",
                        "event_volatility": 0.25,
                    },
                }
            },
        },
        symbol="SPY",
        as_of="2026-07-10T14:30:00Z",
    )
