from __future__ import annotations

from typing import Any
from typing import cast

import pytest

from application.services.base import ServiceRunner
from application.services.market_events.market_events_service import (
    MarketEventsService,
)
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.observability import ObservabilityManager
from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)


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

    # Golden characterization: preserve the established synthesis contract while
    # policy calculations move out of the runtime node.
    assert weak.outputs["directional_score"] == pytest.approx(0.33615284368929665)
    assert weak.outputs["confidence"] == pytest.approx(0.5180648651306893)
    assert weak.outputs["regime"] == "risk_on"
    assert weak.outputs["features"]["uncertainty"] == pytest.approx(0.4819351348693107)
    assert weak.outputs["features"]["execution_readiness"] == pytest.approx(
        0.014148977629193149
    )
    assert weak.outputs["features"]["signal_quality"] == pytest.approx(
        0.49078499594285585
    )
    assert weak.outputs["recommendations"] == [
        "favor_long_exposure",
        "allow_trend_following",
        "require_breadth_confirmation_before_aggressive_allocation",
        "reduce_execution_urgency_until_breadth_improves",
    ]
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
    assert output.execution_metadata["reason"] == "missing_adaptive_weighting_engine"

    signal = telemetry.signal_named(
        "strategy_synthesis.fallback_output",
    )
    assert signal["agent_name"] == "strategy_synthesis_agent"
    assert signal["confidence"] == 0.25
    assert signal["payload"] == {
        "reason": "missing_adaptive_weighting_engine",
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

    def signal_named(
        self,
        signal_name: str,
    ) -> dict[str, Any]:
        for signal in self.signals:
            if signal["signal_name"] == signal_name:
                return signal

        raise AssertionError(f"No signal named {signal_name} was emitted.")


def _agent(
    *,
    provider: _NoEventsProvider | None = None,
    telemetry: _FakeTelemetry | None = None,
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
            "adaptive_weighting_engine": {
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
        },
    )
