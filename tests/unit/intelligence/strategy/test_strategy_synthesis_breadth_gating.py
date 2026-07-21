from __future__ import annotations

from typing import Any, cast

import pytest

from application.observability import AiObservationType
from application.services.base import ServiceRunner
from application.services.market_events.market_events_service import (
    MarketEventsService,
)
from config.strategy_model_config import StrategyModelConfig
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing.trace_context import TraceContext
from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)
from tests.helpers.recording_ai_observability import RecordingAiObservabilityProjector

WEAK_BREADTH: dict[str, object] = {
    "has_breadth_data": True,
    "breadth_regime": "weak_breadth",
    "risk_regime": "elevated",
    "breadth_score": -0.52,
    "breadth_risk_score": 0.76,
    "participation_score": -0.41,
    "leadership_score": -0.38,
    "mcclellan_score": -0.45,
    "price_ad_divergence": True,
}

STRONG_BREADTH: dict[str, object] = {
    "has_breadth_data": True,
    "breadth_regime": "strong_breadth",
    "risk_regime": "stable",
    "breadth_score": 0.64,
    "breadth_risk_score": 0.24,
    "participation_score": 0.36,
    "leadership_score": 0.22,
    "mcclellan_score": 0.18,
    "price_ad_divergence": False,
}

MISSING_BREADTH: dict[str, object] = {
    "has_breadth_data": False,
}


@pytest.mark.asyncio
async def test_strategy_synthesis_weak_breadth_lowers_execution_readiness() -> None:
    agent = _agent()

    baseline = await agent._execute(
        _context(
            breadth_state=MISSING_BREADTH,
        )
    )
    weak = await agent._execute(
        _context(
            breadth_state=WEAK_BREADTH,
        )
    )

    assert (
        weak.outputs["features"]["uncertainty"]
        > baseline.outputs["features"]["uncertainty"]
    )
    assert (
        weak.outputs["features"]["execution_readiness"]
        < baseline.outputs["features"]["execution_readiness"]
    )
    assert (
        weak.outputs["features"]["signal_quality"]
        < baseline.outputs["features"]["signal_quality"]
    )
    assert weak.outputs["features"]["breadth_uncertainty_modifier"] > 0.0
    assert weak.outputs["features"]["breadth_execution_readiness_modifier"] < 0.0
    assert "weak_breadth_lowers_execution_readiness" in weak.outputs["signals"]
    assert "breadth_divergence_risk" in weak.outputs["risks"]
    assert (
        "require_breadth_confirmation_before_aggressive_allocation"
        in weak.outputs["recommendations"]
    )

    assert weak.outputs["features"]["selection_status"] in {"selected", "degraded"}
    assert weak.outputs["features"]["selected_perspective"] == "bull"
    assert weak.outputs["features"]["strategy_hypothesis_evaluations"]
    assert (
        weak.outputs["features"]["hypothesis_synthesis_weights"]["bull"]
        > (weak.outputs["features"]["hypothesis_synthesis_weights"]["bear"])
    )
    assert weak.outputs["directional_score"] != round(
        weak.outputs["directional_score"],
        4,
    )


@pytest.mark.asyncio
async def test_strategy_synthesis_strong_breadth_improves_readiness() -> None:
    agent = _agent()

    baseline = await agent._execute(
        _context(
            breadth_state=MISSING_BREADTH,
        )
    )
    strong = await agent._execute(
        _context(
            breadth_state=STRONG_BREADTH,
        )
    )

    assert (
        strong.outputs["features"]["uncertainty"]
        < baseline.outputs["features"]["uncertainty"]
    )
    assert (
        strong.outputs["features"]["execution_readiness"]
        > baseline.outputs["features"]["execution_readiness"]
    )
    assert (
        strong.outputs["features"]["signal_quality"]
        > baseline.outputs["features"]["signal_quality"]
    )
    assert strong.outputs["features"]["breadth_uncertainty_modifier"] < 0.0
    assert strong.outputs["features"]["breadth_execution_readiness_modifier"] > 0.0
    assert "breadth_confirms_strategy_synthesis" in strong.outputs["signals"]
    assert "breadth_supports_strategy_conviction" in strong.outputs["recommendations"]


@pytest.mark.asyncio
async def test_strategy_synthesis_missing_breadth_is_neutral() -> None:
    agent = _agent()

    output = await agent._execute(
        _context(
            breadth_state=MISSING_BREADTH,
        )
    )

    features = output.outputs["features"]

    assert features["breadth_context"]["has_breadth_data"] is False
    assert features["breadth_uncertainty_modifier"] == 0.0
    assert features["breadth_execution_readiness_modifier"] == 0.0
    assert features["breadth_signal_quality_modifier"] == 0.0
    assert features["breadth_risk_flags"] == []
    assert not any(
        signal.startswith("breadth:") for signal in output.outputs["signals"]
    )


@pytest.mark.asyncio
async def test_strategy_synthesis_uses_market_context_constituents() -> None:
    provider = _NoEventsProvider()
    agent = _agent(
        provider=provider,
    )

    output = await agent._execute(
        _context(
            breadth_state=MISSING_BREADTH,
            top_50_constituents=[
                "aapl",
                " msft ",
                "NVDA",
            ],
        )
    )

    assert provider.earnings_symbols == {
        "AAPL",
        "MSFT",
        "NVDA",
    }
    assert output.outputs["features"]["market_event_constituents"] == [
        "AAPL",
        "MSFT",
        "NVDA",
    ]
    assert output.outputs["features"]["event_lookahead_days"] == 10


@pytest.mark.asyncio
async def test_strategy_synthesis_uses_neutral_events_on_service_failure() -> None:
    telemetry = _FakeTelemetry()
    agent = _agent(
        provider=_FailingEventsProvider(),
        telemetry=telemetry,
    )

    output = await agent._execute(
        _context(
            breadth_state=MISSING_BREADTH,
        )
    )

    features = output.outputs["features"]

    assert output.success is True
    assert features["market_events"]["regime_bias"] == "neutral"
    assert features["market_events"]["event_error"]
    assert "market_event_context_unavailable" in output.outputs["signals"]
    assert "market_event_context_unavailable" in output.outputs["risks"]

    signal = telemetry.signal_named(
        "strategy_synthesis.degraded_data_quality",
    )
    assert signal["agent_name"] == "strategy_synthesis_agent"
    assert signal["confidence"] == 0.0
    assert signal["payload"]["symbol"] == "SPY"
    assert signal["payload"]["reason"] == "events unavailable"
    assert signal["context"].workflow_id == "morning_report"
    assert signal["context"].execution_id == "exec-1"
    assert signal["context"].runtime_id == "runtime-1"
    assert signal["context"].node_name == "strategy_synthesis_agent"
    assert signal["context"].attributes == {
        "runtime_mode": "live",
        "telemetry_reason": "degraded_data_quality",
    }


@pytest.mark.asyncio
async def test_strategy_synthesis_emits_fallback_telemetry_for_missing_upstream() -> (
    None
):
    telemetry = _FakeTelemetry()
    agent = _agent(
        telemetry=telemetry,
    )
    context = _context(
        breadth_state=MISSING_BREADTH,
    ).model_copy(
        update={
            "node_outputs": {},
        },
    )

    output = await agent._execute(
        context,
    )

    assert output.success is True
    assert output.execution_metadata["fallback"] is True
    assert (
        output.execution_metadata["reason"]
        == "missing_strategy_perspective_weighting_engine"
    )
    features = output.outputs["features"]
    assert features["selection_status"] == "degraded"
    assert features["selected_perspective"] is None
    assert (
        features["fallback_reason"] == "missing_strategy_perspective_weighting_engine"
    )
    assert features["hypothesis_synthesis_disagreement"] == 1.0
    assert [
        evaluation["perspective"]
        for evaluation in features["strategy_hypothesis_evaluations"]
    ] == ["bull", "bear", "sideways"]
    assert all(
        evaluation["selection_status"] == "invalidated"
        for evaluation in features["strategy_hypothesis_evaluations"]
    )
    assert "synthesis_input_unavailable" in features["degraded_reasons"]
    assert "missing_perspective_weight" in features["degraded_reasons"]
    assert "all_hypotheses_invalidated" in features["degraded_reasons"]
    assert (
        features["strategy_synthesis_decision"]["selection_status"]
        == features["selection_status"]
    )

    signal = telemetry.signal_named(
        "strategy_synthesis.fallback_output",
    )
    assert signal["agent_name"] == "strategy_synthesis_agent"
    assert signal["confidence"] == 0.25
    assert signal["payload"] == {
        "reason": "missing_strategy_perspective_weighting_engine",
        "fallback": True,
    }
    assert signal["context"].workflow_id == "morning_report"
    assert signal["context"].execution_id == "exec-1"
    assert signal["context"].runtime_id == "runtime-1"
    assert signal["context"].node_name == "strategy_synthesis_agent"
    assert signal["context"].attributes == {
        "runtime_mode": "live",
        "telemetry_reason": "fallback_output",
    }


@pytest.mark.asyncio
async def test_strategy_synthesis_missing_hypothesis_degrades_to_neutral() -> None:
    telemetry = _FakeTelemetry()
    agent = _agent(telemetry=telemetry)
    source_context = _context(breadth_state=MISSING_BREADTH)
    node_outputs = dict(source_context.node_outputs)
    node_outputs.pop("bear_agent")

    output = await agent._execute(
        source_context.model_copy(update={"node_outputs": node_outputs})
    )

    features = output.outputs["features"]

    assert output.success is True
    assert output.outputs["directional_score"] == 0.0
    assert output.outputs["confidence"] == 0.25
    assert output.outputs["regime"] == "neutral"
    assert output.execution_metadata["fallback"] is True
    assert output.execution_metadata["reason"] == "missing_bear_agent"
    assert features["fallback_reason"] == "missing_bear_agent"
    assert features["selection_status"] == "degraded"
    assert features["selected_perspective"] is None
    assert [
        evaluation["perspective"]
        for evaluation in features["strategy_hypothesis_evaluations"]
    ] == ["bull", "bear", "sideways"]
    assert all(
        evaluation["selection_status"] == "invalidated"
        for evaluation in features["strategy_hypothesis_evaluations"]
    )
    assert "missing_hypothesis" in features["degraded_reasons"]
    assert "synthesis_input_unavailable" in features["degraded_reasons"]
    assert "all_hypotheses_invalidated" in features["degraded_reasons"]
    assert (
        features["strategy_synthesis_decision"]["evaluations"]
        == features["strategy_hypothesis_evaluations"]
    )

    signal = telemetry.signal_named("strategy_synthesis.fallback_output")
    assert signal["payload"] == {"reason": "missing_bear_agent", "fallback": True}

    missing = telemetry.signal_named("strategy_synthesis.missing_mandatory_hypothesis")
    assert missing["payload"] == {
        "symbol": "SPY",
        "reason": "missing_bear_agent",
        "fallback": True,
        "degraded_reasons": [
            "all_hypotheses_invalidated",
            "missing_hypothesis",
            "synthesis_input_unavailable",
        ],
    }
    degraded = telemetry.signal_named("strategy_synthesis.degraded_neutral")
    assert degraded["payload"]["symbol"] == "SPY"
    assert degraded["payload"]["fallback"] is True
    assert degraded["payload"]["selection_status"] == "degraded"
    completed = telemetry.signal_named("strategy_synthesis.completed")
    assert completed["payload"]["fallback"] is True
    assert completed["payload"]["latency_seconds"] >= 0.0
    assert len(telemetry.signals_named("strategy_synthesis.degraded_neutral")) == 1


@pytest.mark.asyncio
async def test_strategy_synthesis_emits_low_confidence_telemetry() -> None:
    telemetry = _FakeTelemetry()
    agent = _agent(
        telemetry=telemetry,
    )

    output = await agent._execute(
        _context(
            breadth_state=MISSING_BREADTH,
            portfolio_scale_factor=0.2,
        )
    )

    assert output.success is True
    assert output.execution_metadata["confidence"] <= 0.4

    signal = telemetry.signal_named(
        "strategy_synthesis.low_confidence",
    )
    assert signal["agent_name"] == "strategy_synthesis_agent"
    assert signal["confidence"] <= 0.4
    assert signal["payload"]["symbol"] == "SPY"
    assert signal["payload"]["confidence"] <= 0.4
    assert signal["context"].attributes == {
        "runtime_mode": "live",
        "telemetry_reason": "low_confidence",
    }


@pytest.mark.asyncio
async def test_strategy_synthesis_emits_completion_and_disagreement_with_trace() -> (
    None
):
    telemetry = _FakeTelemetry()
    agent = _agent(telemetry=telemetry)
    source_context = _context(breadth_state=MISSING_BREADTH)
    node_outputs = dict(source_context.node_outputs)
    node_outputs["strategy_perspective_weighting_engine"] = {
        "outputs": {
            "features": {
                "bull_weight": 0.33,
                "bear_weight": 0.33,
                "sideways_weight": 0.34,
            }
        }
    }
    for node_name in ("bull_agent", "bear_agent", "sideways_agent"):
        hypothesis = cast(
            dict[str, object],
            cast(
                dict[str, object],
                cast(dict[str, object], node_outputs[node_name])["outputs"],
            )["strategy_hypothesis"],
        )
        hypothesis["hypothesis_strength"] = 0.60
        hypothesis["confidence"] = 0.60

    context = source_context.model_copy(
        update={
            "node_outputs": node_outputs,
            "trace_context": TraceContext(
                trace_id="trace-1",
                span_id="span-1",
                parent_span_id="parent-1",
                correlation_id="corr-1",
                workflow_id="morning_report",
                execution_id="exec-1",
                runtime_id="runtime-1",
                node_name="strategy_synthesis_agent",
                attributes={"tenant": "unit-test"},
            ),
        }
    )

    output = await agent._execute(context)

    assert output.success is True
    completed = telemetry.signal_named("strategy_synthesis.completed")
    assert completed["payload"]["symbol"] == "SPY"
    assert completed["payload"]["latency_seconds"] >= 0.0
    assert completed["payload"]["fallback"] is False
    assert completed["context"].trace_id == "trace-1"
    assert completed["context"].span_id == "span-1"
    assert completed["context"].parent_span_id == "parent-1"
    assert completed["context"].correlation_id == "corr-1"
    assert completed["context"].attributes == {
        "tenant": "unit-test",
        "runtime_mode": "live",
        "telemetry_reason": "synthesis_completed",
    }
    assert len(telemetry.signals_named("strategy_synthesis.completed")) == 1

    disagreement = telemetry.signal_named(
        "strategy_synthesis.high_hypothesis_disagreement"
    )
    assert (
        disagreement["payload"]["hypothesis_synthesis_disagreement"]
        >= disagreement["payload"]["threshold"]
    )
    assert disagreement["context"].trace_id == "trace-1"
    assert (
        len(telemetry.signals_named("strategy_synthesis.high_hypothesis_disagreement"))
        == 1
    )


@pytest.mark.asyncio
async def test_strategy_synthesis_emits_hypothesis_invalidation_once() -> None:
    telemetry = _FakeTelemetry()
    agent = _agent(telemetry=telemetry)
    source_context = _context(breadth_state=MISSING_BREADTH)
    node_outputs = dict(source_context.node_outputs)
    bull_output = cast(dict[str, object], node_outputs["bull_agent"])
    bull_outputs = cast(dict[str, object], bull_output["outputs"])
    bull_hypothesis = cast(dict[str, object], bull_outputs["strategy_hypothesis"])
    bull_hypothesis["invalidation_conditions"] = [
        {
            "condition_id": "bull-invalidated",
            "perspective": "bull",
            "description": "Fixture condition invalidates the bull hypothesis.",
            "observed_value": 1.0,
            "operator": "gte",
            "threshold": 0.5,
            "evidence_id": None,
        }
    ]

    output = await agent._execute(
        source_context.model_copy(update={"node_outputs": node_outputs})
    )

    assert output.success is True
    signal = telemetry.signal_named("strategy_synthesis.hypothesis_invalidated")
    assert signal["payload"]["symbol"] == "SPY"
    assert signal["payload"]["invalidated_perspectives"] == ["bull"]
    assert signal["payload"]["invalidation_count"] == 1
    assert signal["context"].attributes == {
        "runtime_mode": "live",
        "telemetry_reason": "hypothesis_invalidated",
    }
    assert (
        len(telemetry.signals_named("strategy_synthesis.hypothesis_invalidated")) == 1
    )


class _NoEventsProvider:
    def __init__(self) -> None:
        self.earnings_symbols: set[str] | None = None

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
        self.earnings_symbols = symbols
        return []


class _FailingEventsProvider(_NoEventsProvider):
    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("events unavailable")


class _FakeTelemetry:
    def __init__(
        self,
    ) -> None:
        self.signals: list[dict[str, Any]] = []

    async def emit_agent_signal(
        self,
        *,
        agent_name: str,
        signal_name: str,
        confidence: float | None,
        context: object | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.signals.append(
            {
                "agent_name": agent_name,
                "signal_name": signal_name,
                "confidence": confidence,
                "context": context,
                "attributes": dict(attributes or {}),
                "payload": dict(payload or {}),
            }
        )

    def signals_named(
        self,
        signal_name: str,
    ) -> list[dict[str, Any]]:
        return [
            signal for signal in self.signals if signal["signal_name"] == signal_name
        ]

    def signal_named(
        self,
        signal_name: str,
    ) -> dict[str, Any]:
        for signal in self.signals:
            if signal["signal_name"] == signal_name:
                return signal

        raise AssertionError(f"No signal named {signal_name} was emitted.")


@pytest.mark.asyncio
async def test_strategy_synthesis_records_ai_observability_projection() -> None:
    projector = RecordingAiObservabilityProjector()
    agent = _agent(
        projector=projector,
    )

    output = await agent._execute(
        _context(
            breadth_state=STRONG_BREADTH,
            top_50_constituents=["AAPL", "MSFT"],
        )
    )

    assert output.success is True
    assert len(projector.observations) == 1
    observation = projector.observations[0]
    assert (
        observation.observation_type
        is AiObservationType.INTELLIGENCE_STRATEGY_SYNTHESIS
    )
    assert observation.name == "strategy_synthesis"
    assert observation.correlation_ids.execution_id == "exec-1"
    assert observation.correlation_ids.node_name == "strategy_synthesis_agent"
    assert observation.prompt is None
    assert observation.response is None
    assert observation.metadata["symbol"] == "SPY"
    assert observation.metadata["evaluation_count"] == 3
    assert observation.metadata["fallback"] is False
    assert observation.metadata["selected_perspective"] in {
        "bull",
        "bear",
        "sideways",
        None,
    }


def _agent(
    *,
    provider: _NoEventsProvider | None = None,
    telemetry: _FakeTelemetry | None = None,
    projector: RecordingAiObservabilityProjector | None = None,
) -> StrategySynthesisAgent:
    return StrategySynthesisAgent(
        events_service=MarketEventsService(
            events_provider=provider or _NoEventsProvider(),
        ),
        service_runner=ServiceRunner(
            telemetry=ApplicationServiceTelemetry(
                observability_manager=ObservabilityManager()
            )
        ),
        intelligence_telemetry=cast(
            IntelligenceTelemetry,
            telemetry or _FakeTelemetry(),
        ),
        strategy_model_config=StrategyModelConfig(),
        ai_observability_projector=projector,
    )


def _context(
    *,
    breadth_state: dict[str, object],
    top_50_constituents: list[str] | None = None,
    portfolio_scale_factor: float = 1.0,
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        node_outputs={
            "strategy_perspective_weighting_engine": {
                "outputs": {
                    "features": {
                        "bull_weight": 0.55,
                        "bear_weight": 0.20,
                        "sideways_weight": 0.25,
                    }
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "features": {
                        "risk_pressure": 0.10,
                        "adjusted_risk_pressure": 0.10,
                        "composite_risk": 0.20,
                    }
                }
            },
            "portfolio_state_builder": {
                "outputs": {
                    "features": {
                        "scale_factor": portfolio_scale_factor,
                        "status": "approved",
                    }
                }
            },
            "technical_agent": {
                "outputs": {
                    "features": {
                        "regime": {
                            "regime": "neutral",
                        },
                        "breadth_state": breadth_state,
                        "market_context": {
                            "top_50_constituents": top_50_constituents,
                        },
                    }
                }
            },
            "bull_agent": _hypothesis_node(
                perspective="bull",
                directional_bias=0.70,
                hypothesis_strength=0.70,
                confidence=0.80,
                thesis="Bull hypothesis is strongest in the fixture.",
            ),
            "bear_agent": _hypothesis_node(
                perspective="bear",
                directional_bias=-0.35,
                hypothesis_strength=0.35,
                confidence=0.65,
                thesis="Bear hypothesis is weaker in the fixture.",
            ),
            "sideways_agent": _hypothesis_node(
                perspective="sideways",
                directional_bias=0.0,
                hypothesis_strength=0.40,
                confidence=0.70,
                thesis="Sideways hypothesis is plausible but not dominant.",
            ),
        },
    )


def _hypothesis_node(
    *,
    perspective: str,
    directional_bias: float,
    hypothesis_strength: float,
    confidence: float,
    thesis: str,
) -> dict[str, object]:
    return {
        "outputs": {
            "strategy_hypothesis": {
                "perspective": perspective,
                "thesis": thesis,
                "directional_bias": directional_bias,
                "hypothesis_strength": hypothesis_strength,
                "confidence": confidence,
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "key_assumptions": [],
                "invalidation_conditions": [],
                "risks": [],
                "recommendations": [],
                "data_quality_flags": [],
                "evidence_fingerprint": f"{perspective}-fixture",
            }
        }
    }
