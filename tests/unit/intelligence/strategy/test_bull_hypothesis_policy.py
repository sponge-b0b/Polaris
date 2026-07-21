from __future__ import annotations

import pytest

from config.strategy_model_config import StrategyModelConfig
from core.runtime.state.runtime_context import RuntimeContext
from domain.workflow_outputs import (
    STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.bull.bull_agent import BullAgent
from intelligence.strategy.bull.bull_hypothesis_policy import build_bull_hypothesis
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.normalization import (
    normalize_strategy_evidence_context,
)


@pytest.mark.asyncio
async def test_bull_agent_produces_complete_structured_hypothesis() -> None:
    evidence_context = _evidence_context(risk_pressure=0.20)
    agent = BullAgent(strategy_model_config=StrategyModelConfig())

    output = await agent._execute(_runtime_context(evidence_context))

    hypothesis = output.outputs["strategy_hypothesis"]
    assert isinstance(hypothesis, dict)
    assert hypothesis["perspective"] == "bull"
    assert hypothesis["evidence_fingerprint"] == evidence_context.evidence_fingerprint()
    assert hypothesis["directional_bias"] == output.outputs["directional_score"]
    assert hypothesis["hypothesis_strength"] == output.outputs["directional_score"]
    assert hypothesis["confidence"] == output.outputs["confidence"]
    assert hypothesis["supporting_evidence"]
    assert hypothesis["key_assumptions"]
    assert hypothesis["invalidation_conditions"]
    assert output.output_contract == STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT
    assert output.output_schema_version == WORKFLOW_OUTPUT_SCHEMA_VERSION_V1
    assert output.execution_metadata["evidence_fingerprint"] == (
        evidence_context.evidence_fingerprint()
    )

    supporting_ids = {item["evidence_id"] for item in hypothesis["supporting_evidence"]}
    assert "sentiment.directional_score" in supporting_ids
    assert "technical.directional_score" in supporting_ids


@pytest.mark.asyncio
async def test_bull_agent_requires_strategy_evidence_builder_output() -> None:
    agent = BullAgent(strategy_model_config=StrategyModelConfig())
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={"sentiment_agent": {}, "technical_agent": {}},
    )

    with pytest.raises(ValueError, match="strategy_evidence_builder"):
        await agent._execute(context)


def test_bull_policy_is_deterministic_across_serialized_replay() -> None:
    evidence_context = _evidence_context(risk_pressure=0.20)
    replay_context = StrategyEvidenceContext.from_dict(evidence_context.to_dict())

    first = build_bull_hypothesis(evidence_context)
    second = build_bull_hypothesis(replay_context)

    assert first.hypothesis.to_canonical_json() == second.hypothesis.to_canonical_json()
    assert first.to_runtime_outputs() == second.to_runtime_outputs()


def test_bull_policy_expresses_opposing_evidence_and_hard_invalidations() -> None:
    evidence_context = _evidence_context(risk_pressure=0.90, volatility_score=0.92)

    decision = build_bull_hypothesis(evidence_context)
    hypothesis = decision.hypothesis

    contradicting_ids = {item.evidence_id for item in hypothesis.contradicting_evidence}
    invalidated_ids = {
        condition.condition_id
        for condition in hypothesis.invalidation_conditions
        if condition.is_invalidated()
    }
    assert "risk.pressure" in contradicting_ids
    assert "bull.risk_pressure_spike" in invalidated_ids
    assert "bull.volatility_shock" in invalidated_ids
    assert hypothesis.invalidated is True
    assert decision.features["invalidated"] is True


def test_bull_policy_surfaces_missing_optional_inputs_as_data_quality_flags() -> None:
    evidence_context = _evidence_context(risk_pressure=0.20, include_optional=False)

    decision = build_bull_hypothesis(evidence_context)

    assert "fundamental_agent:missing" in decision.hypothesis.data_quality_flags
    assert "news_agent:missing" in decision.hypothesis.data_quality_flags
    assert "portfolio_state_builder:missing" in decision.hypothesis.data_quality_flags


def _runtime_context(evidence_context: StrategyEvidenceContext) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "strategy_evidence_builder": {
                "outputs": {
                    "strategy_evidence_context": evidence_context.to_dict(),
                    "evidence_fingerprint": evidence_context.evidence_fingerprint(),
                }
            }
        },
    )


def _evidence_context(
    *,
    risk_pressure: float,
    volatility_score: float = 0.30,
    include_optional: bool = True,
) -> StrategyEvidenceContext:
    node_outputs: dict[str, object] = {
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
    }
    if include_optional:
        node_outputs.update(
            {
                "fundamental_agent": {
                    "outputs": {"directional_score": 0.42, "confidence": 0.58}
                },
                "news_agent": {
                    "outputs": {"directional_score": 0.35, "confidence": 0.55}
                },
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
            }
        )
    return normalize_strategy_evidence_context(
        node_outputs,
        symbol="SPY",
        as_of="2026-07-10T14:30:00Z",
    )
