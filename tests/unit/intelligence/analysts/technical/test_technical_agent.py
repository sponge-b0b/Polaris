from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Any
from typing import cast

import pytest

from application.services.base import ServiceRunner
from application.services.base import ServiceResult
from application.services.technical.technical_analysis_service import (
    TechnicalAnalysisService,
)
from application.services.technical.technical_result import TechnicalAnalysisResult
from core.llm.llm_service import LLMService
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.tracing.trace_context import TraceContext
from application.observability import AiObservationType
from intelligence.analysts.technical.technical_agent import TechnicalAgent
from tests.helpers.recording_ai_observability import RecordingAiObservabilityProjector


@pytest.mark.asyncio
async def test_technical_agent_preserves_expanded_breadth_outputs() -> None:
    llm_service = _FakeLLMService()
    service_runner = _FakeServiceRunner(
        _analysis_payload(),
    )
    telemetry = _FakeTelemetry()
    agent = TechnicalAgent(
        llm_service=cast(
            LLMService,
            llm_service,
        ),
        technical_service=cast(
            TechnicalAnalysisService,
            object(),
        ),
        service_runner=cast(
            ServiceRunner[Any, Any],
            service_runner,
        ),
        intelligence_telemetry=cast(
            IntelligenceTelemetry,
            telemetry,
        ),
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        trace_context=TraceContext(
            trace_id="trace-1",
            span_id="technical-node-span-1",
            parent_span_id="workflow-span-1",
            correlation_id="correlation-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="technical_agent",
            attributes={
                "trace_scope": "runtime_node",
            },
        ),
        created_at=datetime(2026, 7, 10, 13, 30, tzinfo=UTC),
        workflow_inputs={
            "symbol": "SPY",
            "days": 365,
        },
    )

    output = await agent._execute(
        context,
    )

    assert output.success is True
    assert output.outputs["observed_at"] == "2026-07-10T13:30:00+00:00"
    assert output.outputs["market_universe"] == "sp500"
    features = output.outputs["features"]
    assert features["breadth"]["breadth_regime"] == "weak_breadth"
    assert features["market_context"]["advances_count"] == 180
    assert features["breadth_state"]["price_ad_divergence"] is True
    assert "breadth:weak_breadth" in output.outputs["signals"]
    assert "price_ad_divergence" in output.outputs["risks"]
    assert "weak_market_breadth" in output.outputs["risks"]
    assert "validate_breakout_with_participation" in output.outputs["recommendations"]

    assert len(service_runner.requests) == 1
    request = service_runner.requests[0]
    telemetry_context = request.telemetry_context
    assert telemetry_context is not None
    assert telemetry_context.workflow_id == "morning_report"
    assert telemetry_context.execution_id == "exec-1"
    assert telemetry_context.runtime_id == "runtime-1"
    assert telemetry_context.node_name == "technical_agent"
    assert telemetry_context.correlation_id == "correlation-1"
    assert telemetry_context.trace_id == "trace-1"
    assert telemetry_context.span_id == "technical-node-span-1"
    assert telemetry_context.parent_span_id == "workflow-span-1"
    assert telemetry_context.tags == (
        "runtime",
        "intelligence",
    )
    assert telemetry_context.attributes == {
        "trace_scope": "runtime_node",
        "runtime_mode": "live",
    }

    assert len(telemetry.signals) == 1
    signal_context = cast(
        TelemetryContext,
        telemetry.signals[0]["context"],
    )
    assert signal_context.trace_id == "trace-1"
    assert signal_context.span_id == "technical-node-span-1"
    assert signal_context.parent_span_id == "workflow-span-1"


@pytest.mark.asyncio
async def test_technical_agent_llm_context_includes_sp500_breadth() -> None:
    llm_service = _FakeLLMService()
    service_runner = _FakeServiceRunner(
        _analysis_payload(),
    )
    telemetry = _FakeTelemetry()
    agent = TechnicalAgent(
        llm_service=cast(
            LLMService,
            llm_service,
        ),
        technical_service=cast(
            TechnicalAnalysisService,
            object(),
        ),
        service_runner=cast(
            ServiceRunner[Any, Any],
            service_runner,
        ),
        intelligence_telemetry=cast(
            IntelligenceTelemetry,
            telemetry,
        ),
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        workflow_inputs={
            "symbol": "SPY",
        },
    )

    await agent._execute(
        context,
    )

    llm_context = llm_service.last_message
    assert "MARKET BREADTH ENGINE" in llm_context
    assert "S&P 500 MARKET CONTEXT" in llm_context
    assert "McClellan Oscillator" in llm_context
    assert "Price / A-D Divergence" in llm_context


@pytest.mark.asyncio
async def test_technical_agent_records_ai_observability_projection() -> None:
    projector = RecordingAiObservabilityProjector()
    agent = TechnicalAgent(
        llm_service=cast(
            LLMService,
            _FakeLLMService(),
        ),
        technical_service=cast(
            TechnicalAnalysisService,
            object(),
        ),
        service_runner=cast(
            ServiceRunner[Any, Any],
            _FakeServiceRunner(
                _analysis_payload(),
            ),
        ),
        intelligence_telemetry=cast(
            IntelligenceTelemetry,
            _FakeTelemetry(),
        ),
        ai_observability_projector=projector,
    )
    context = RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="exec-1",
        trace_context=TraceContext(
            trace_id="trace-1",
            span_id="technical-node-span-1",
            parent_span_id="workflow-span-1",
            correlation_id="correlation-1",
            workflow_id="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="technical_agent",
        ),
        workflow_inputs={
            "symbol": "SPY",
            "days": 365,
        },
    )

    output = await agent._execute(
        context,
    )

    assert output.success is True
    assert len(projector.observations) == 1
    observation = projector.observations[0]
    assert (
        observation.observation_type is AiObservationType.INTELLIGENCE_AGENT_REASONING
    )
    assert observation.name == "technical_llm_reasoning"
    assert observation.correlation_ids.execution_id == "exec-1"
    assert observation.correlation_ids.node_name == "technical_agent"
    assert observation.prompt is None
    assert observation.response is None
    assert observation.prompt_reference is not None
    assert observation.prompt_reference.prompt_name == "technical_agent_system_prompt"
    assert observation.prompt_reference.prompt_hash is not None
    assert observation.prompt_reference.source == "polaris.intelligence"
    assert observation.metadata["symbol"] == "SPY"
    assert observation.metadata["fallback"] is False


class _FakeLLMService:
    def __init__(
        self,
    ) -> None:
        self.last_message = ""

    async def chat(
        self,
        *,
        system_prompt: str,
        response_format: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        self.last_message = messages[0]["content"]
        return {
            "outlook": "cautious",
            "summary": "Breadth is weakening beneath price.",
            "signals": [
                "llm_breadth_warning",
            ],
            "risks": [],
            "recommendations": [],
            "key_points": [],
            "support_levels": [],
            "resistance_levels": [],
        }


class _FakeServiceRunner:
    def __init__(
        self,
        analysis: dict[str, Any],
    ) -> None:
        self.analysis = analysis
        self.requests: list[Any] = []

    async def run(
        self,
        *,
        service: object,
        request: object,
    ) -> ServiceResult[TechnicalAnalysisResult]:
        self.requests.append(
            request,
        )
        request_id = getattr(
            request,
            "request_id",
            "request-1",
        )
        return ServiceResult.ok(
            request_id=request_id,
            request_name="TechnicalAnalysisRequest",
            result=TechnicalAnalysisResult(
                symbol=str(self.analysis.get("symbol", "SPY")),
                technical_score=float(self.analysis.get("technical_score", 0.31)),
                snapshot=self.analysis["snapshot"],
                market_context=self.analysis["market_context"],
                micro_regime=self.analysis.get("micro_regime", {}),
                trend=self.analysis["trend"],
                volatility=self.analysis["volatility"],
                breadth=self.analysis["breadth"],
                raw_regime=self.analysis["raw_regime"],
                regime=self.analysis["regime"],
            ),
        )


class _FakeTelemetry:
    def __init__(
        self,
    ) -> None:
        self.signals: list[dict[str, Any]] = []
        self.degraded: list[dict[str, Any]] = []

    async def emit_agent_signal(
        self,
        *,
        agent_name: str,
        signal_name: str,
        confidence: float,
        context: object | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.signals.append(
            {
                "agent_name": agent_name,
                "signal_name": signal_name,
                "confidence": confidence,
                "context": context,
                "payload": dict(payload or {}),
            }
        )

    async def emit_agent_degraded(self, **kwargs: Any) -> None:
        self.degraded.append(kwargs)


def _analysis_payload() -> dict[str, Any]:
    return {
        "snapshot": {
            "close": 450.0,
            "ema_8": 448.0,
            "ema_21": 445.0,
            "ema_50": 440.0,
            "ema_200": 420.0,
            "rsi_14": 61.0,
            "macd": 1.2,
            "macd_signal": 1.0,
            "macd_histogram": 0.2,
            "atr_14": 4.5,
        },
        "trend": {
            "primary_trend": "uptrend",
            "trend_strength": 0.72,
        },
        "volatility": {
            "volatility_regime": "normal",
            "volatility_score": 0.44,
        },
        "market_context": {
            "has_breadth": True,
            "advances_count": 180,
            "declines_count": 310,
            "breadth_percent": 0.37,
            "pct_above_50dma": 0.42,
            "pct_above_200dma": 0.48,
            "new_highs": 8,
            "new_lows": 44,
            "mcclellan_oscillator": -32.5,
            "price_ad_divergence": 1.0,
        },
        "breadth": {
            "has_breadth_data": True,
            "breadth_regime": "weak_breadth",
            "risk_regime": "elevated",
            "breadth_score": -0.52,
            "breadth_risk_score": 0.76,
            "participation_score": -0.41,
            "leadership_score": -0.38,
            "mcclellan_score": -0.45,
            "divergence_score": -0.60,
            "price_ad_divergence": True,
            "breadth_percent": 0.37,
            "pct_above_50dma": 0.42,
            "pct_above_200dma": 0.48,
            "new_high_low_diff": -36,
            "mcclellan_oscillator": -32.5,
        },
        "raw_regime": {
            "inputs": {
                "breadth_regime": "weak_breadth",
                "price_ad_divergence": True,
            },
        },
        "regime": {
            "directional_technical_score": 0.31,
            "confidence": 0.58,
            "regime": "constructive",
            "calibration": {
                "breadth_score": -0.52,
                "breadth_risk_score": 0.76,
                "participation_score": -0.41,
            },
        },
    }
