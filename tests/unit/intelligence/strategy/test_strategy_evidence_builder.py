from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any, cast

from application.services.base import ServiceRequest, ServiceResult, ServiceRunner
from application.services.market_events.market_events_request import MarketEventsRequest
from application.services.market_events.market_events_result import MarketEventsResult
from application.services.market_events.market_events_service import MarketEventsService
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import STRATEGY_EVIDENCE_CONTEXT_OUTPUT_CONTRACT
from intelligence.strategy.hypothesis import StrategyEvidenceInputStatus
from intelligence.strategy.hypothesis.evidence_builder import StrategyEvidenceBuilder


class _CapturingServiceRunner:
    def __init__(
        self,
        *,
        result: MarketEventsResult | None = None,
        error: BaseException | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.requests: list[ServiceRequest[MarketEventsRequest]] = []

    async def run(
        self,
        *,
        service: object,
        request: ServiceRequest[MarketEventsRequest],
    ) -> ServiceResult[MarketEventsResult]:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.result is None:
            return ServiceResult.failed(
                request_id=request.request_id,
                request_name=request.request_name,
                error="missing result",
            )
        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=self.result,
        )


class _FakeTelemetry:
    def __init__(self) -> None:
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

    def signal_named(self, signal_name: str) -> dict[str, Any]:
        for signal in self.signals:
            if signal["signal_name"] == signal_name:
                return signal
        raise AssertionError(f"No signal named {signal_name} was emitted.")


def _builder(
    runner: _CapturingServiceRunner,
    *,
    telemetry: _FakeTelemetry | None = None,
) -> StrategyEvidenceBuilder:
    return StrategyEvidenceBuilder(
        events_service=cast(MarketEventsService, object()),
        service_runner=cast(ServiceRunner[Any, Any], runner),
        intelligence_telemetry=cast(
            IntelligenceTelemetry,
            telemetry or _FakeTelemetry(),
        ),
    )


def test_strategy_evidence_builder_returns_shared_evidence_context() -> None:
    runner = _CapturingServiceRunner(result=_market_events_result())
    builder = _builder(runner)

    output = _run_builder(builder, _runtime_context())

    evidence_context = cast(
        dict[str, object], output.outputs["strategy_evidence_context"]
    )
    assert output.success is True
    assert output.output_contract == STRATEGY_EVIDENCE_CONTEXT_OUTPUT_CONTRACT
    assert (
        output.outputs["evidence_fingerprint"]
        == evidence_context["evidence_fingerprint"]
    )
    assert output.outputs["market_events_status"] == "available"
    assert output.outputs["missing_required_inputs"] is False
    assert output.outputs["degraded_required_inputs"] is False

    input_quality = {
        cast(str, item["input_name"]): cast(str, item["status"])
        for item in cast(list[dict[str, object]], evidence_context["input_quality"])
    }
    optional_ids = {
        cast(str, item["evidence_id"])
        for item in cast(list[dict[str, object]], evidence_context["optional_evidence"])
    }
    assert input_quality["market_events"] == StrategyEvidenceInputStatus.AVAILABLE.value
    assert "market_events.pressure" in optional_ids
    assert "market_events.bias" in optional_ids
    assert "market_events.volatility" in optional_ids

    captured_request = runner.requests[0].payload
    assert captured_request.symbol == "SPY"
    assert captured_request.lookahead_days == 7
    assert captured_request.horizon == "1month"
    assert captured_request.symbol_constituents == frozenset({"AAPL", "MSFT"})


def test_strategy_evidence_builder_degrades_optional_market_events() -> None:
    runner = _CapturingServiceRunner(error=RuntimeError("market events unavailable"))
    telemetry = _FakeTelemetry()
    builder = _builder(runner, telemetry=telemetry)

    output = _run_builder(builder, _runtime_context())

    evidence_context = cast(
        dict[str, object], output.outputs["strategy_evidence_context"]
    )
    input_quality = {
        cast(str, item["input_name"]): item
        for item in cast(list[dict[str, object]], evidence_context["input_quality"])
    }
    market_events_quality = cast(dict[str, object], input_quality["market_events"])

    assert output.success is True
    assert output.outputs["market_events_status"] == "degraded"
    assert market_events_quality["status"] == StrategyEvidenceInputStatus.DEGRADED.value
    assert market_events_quality["required"] is False
    assert market_events_quality["reason"] == (
        "market_events output did not contain strategy evidence fields."
    )

    signal = telemetry.signal_named("strategy_evidence_context.degraded")
    assert signal["agent_name"] == "strategy_evidence_builder"
    assert signal["confidence"] == 0.25
    assert signal["payload"]["symbol"] == "SPY"
    assert signal["payload"]["market_events_status"] == "degraded"
    assert signal["payload"]["missing_required_inputs"] is False
    assert signal["payload"]["degraded_required_inputs"] is False
    assert signal["payload"]["required_evidence_count"] > 0
    assert signal["payload"]["optional_evidence_count"] >= 0
    degraded_input_quality = {
        item["input_name"]: item for item in signal["payload"]["input_quality"]
    }
    assert degraded_input_quality["market_events"] == market_events_quality
    assert signal["context"].workflow_id == "morning_report"
    assert signal["context"].execution_id == "execution-1"
    assert signal["context"].runtime_id == "runtime-1"
    assert signal["context"].node_name == "strategy_evidence_builder"
    assert signal["context"].attributes == {
        "runtime_mode": "live",
        "telemetry_reason": "evidence_context_degraded",
    }


def test_morning_report_wires_strategy_evidence_builder_before_strategy_agents() -> (
    None
):
    nodes = _workflow_node_definitions()

    assert nodes["strategy_evidence_builder"]["node_type"] == "StrategyEvidenceBuilder"
    assert nodes["strategy_evidence_builder"]["dependencies"] == (
        "portfolio_state_builder",
        "fundamental_agent",
        "technical_agent",
        "news_agent",
        "sentiment_agent",
        "risk_aggregator_agent",
    )

    concurrent_strategy_nodes = (
        "strategy_perspective_weighting_engine",
        "bull_agent",
        "bear_agent",
        "sideways_agent",
    )
    for node_name in concurrent_strategy_nodes:
        assert nodes[node_name]["dependencies"] == ("strategy_evidence_builder",)


def test_morning_report_wires_strategy_synthesis_after_all_hypotheses() -> None:
    nodes = _workflow_node_definitions()

    assert nodes["strategy_synthesis_agent"]["dependencies"] == (
        "strategy_perspective_weighting_engine",
        "bull_agent",
        "bear_agent",
        "sideways_agent",
        "risk_aggregator_agent",
        "portfolio_state_builder",
        "technical_agent",
    )
    for upstream_name in (
        "strategy_perspective_weighting_engine",
        "bull_agent",
        "bear_agent",
        "sideways_agent",
    ):
        dependencies = cast(
            tuple[str, ...], nodes["strategy_synthesis_agent"]["dependencies"]
        )
        assert upstream_name in dependencies


def test_morning_report_keeps_portfolio_and_execution_after_synthesis() -> None:
    nodes = _workflow_node_definitions()

    assert nodes["portfolio_manager_agent"]["dependencies"] == (
        "portfolio_state_builder",
        "strategy_synthesis_agent",
        "risk_aggregator_agent",
    )
    assert nodes["trade_packager"]["dependencies"] == ("portfolio_manager_agent",)
    assert nodes["execution_risk_guard"]["dependencies"] == (
        "trade_packager",
        "risk_aggregator_agent",
    )


def _workflow_node_definitions() -> dict[str, dict[str, object]]:
    source = Path("workflows/definitions/reports/morning_report.py").read_text()
    tree = ast.parse(source)
    nodes: dict[str, dict[str, object]] = {}
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        if (
            not isinstance(call.func, ast.Name)
            or call.func.id != "WorkflowNodeDefinition"
        ):
            continue
        keywords = {keyword.arg: keyword.value for keyword in call.keywords}
        name = _literal_string(keywords.get("name"))
        node_type = _name_value(keywords.get("node_type"))
        dependencies = _string_tuple(keywords.get("dependencies"))
        if name is not None and node_type is not None:
            nodes[name] = {
                "node_type": node_type,
                "dependencies": dependencies,
            }
    return nodes


def _literal_string(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _name_value(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _string_tuple(node: ast.expr | None) -> tuple[str, ...]:
    if not isinstance(node, ast.Tuple):
        return ()
    return tuple(
        value.value
        for value in node.elts
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    )


def _run_builder(
    builder: StrategyEvidenceBuilder,
    context: RuntimeContext,
) -> RuntimeNodeOutput:
    return asyncio.run(builder._execute(context))


def _runtime_context() -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-1",
        workflow_id="morning_report",
        execution_id="execution-1",
        workflow_inputs={
            "symbol": "SPY",
            "event_lookahead_days": 7,
            "horizon": "1month",
        },
        node_outputs={
            "sentiment_agent": {
                "outputs": {
                    "directional_score": 0.25,
                    "confidence": 0.73,
                    "features": {
                        "momentum": 0.31,
                        "stability": 0.62,
                        "divergence": {"avg_divergence": 0.08},
                    },
                }
            },
            "technical_agent": {
                "outputs": {
                    "directional_score": 0.42,
                    "confidence": 0.81,
                    "features": {
                        "market_context": {"top_50_constituents": ["AAPL", "MSFT"]},
                        "regime": {"regime": "bullish"},
                        "trend": {"trend_strength": 0.55},
                        "volatility": {
                            "volatility_score": 0.22,
                            "volatility_regime": "normal",
                        },
                        "breadth_state": {
                            "has_breadth_data": False,
                        },
                    },
                }
            },
            "fundamental_agent": {
                "outputs": {"directional_score": 0.15, "confidence": 0.67}
            },
            "news_agent": {"outputs": {"directional_score": -0.05, "confidence": 0.58}},
            "risk_aggregator_agent": {
                "outputs": {
                    "confidence": 0.72,
                    "features": {"risk_pressure": 0.24, "composite_risk": 0.30},
                }
            },
            "portfolio_state_builder": {
                "outputs": {
                    "confidence": 0.90,
                    "features": {
                        "scale_factor": 0.88,
                        "status": "approved",
                        "risk_features": {"portfolio_heat": 0.33},
                    },
                }
            },
        },
    )


def _market_events_result() -> MarketEventsResult:
    return MarketEventsResult(
        symbol="SPY",
        market_pressure_score=0.20,
        volatility_pressure=0.30,
        volatility_forecast="normal",
        regime_bias="bullish",
        events=({"event_id": "fed", "impact": "medium"},),
        high_impact_events=(),
        event_count=1,
        high_impact_count=0,
        risk_projection={"risk_level": "moderate"},
    )
