from __future__ import annotations

from typing import Any, cast

import pytest

from application.services.base import ServiceResult, ServiceRunner
from application.services.macro.macro_result import MacroAnalysisResult
from application.services.macro.macro_service import MacroService
from core.llm.llm_service import LLMService
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from intelligence.analysts.fundamental.fundamental_agent import FundamentalAgent


class _MacroRunner:
    async def run(
        self,
        *,
        service: object,
        request: object,
    ) -> ServiceResult[MacroAnalysisResult]:
        return ServiceResult.ok(
            request_id=str(getattr(request, "request_id", "request-1")),
            request_name="MacroAnalysisRequest",
            result=MacroAnalysisResult(
                macro_data=None,
                inflation_analysis={"inflation_regime": "disinflationary"},
                fed_analysis={"fed_stance": "dovish"},
                liquidity_analysis={"liquidity_regime": "high_liquidity"},
                yield_curve_analysis={"curve_regime": "normal_curve"},
                economic_regime={
                    "economic_regime": "risk_on_expansion",
                    "market_bias": "bullish_bias",
                },
                inflation_regime="disinflationary",
                fed_stance="dovish",
                liquidity_regime="high_liquidity",
                yield_curve_regime="normal_curve",
            ),
        )


class _LLM:
    def chat(self, **kwargs: Any) -> str:
        return "Constructive macro conditions."


class _FailingLLM:
    def chat(self, **kwargs: Any) -> str:
        raise RuntimeError("model unavailable")


class _Telemetry:
    def __init__(self) -> None:
        self.degraded: list[dict[str, Any]] = []

    async def emit_agent_signal(self, **kwargs: Any) -> None:
        return None

    async def emit_agent_degraded(self, **kwargs: Any) -> None:
        self.degraded.append(kwargs)


@pytest.mark.asyncio
async def test_fundamental_agent_uses_canonical_macro_result_fields() -> None:
    agent = FundamentalAgent(
        llm_service=cast(LLMService, _LLM()),
        macro_service=cast(MacroService, object()),
        service_runner=cast(ServiceRunner[Any, Any], _MacroRunner()),
        intelligence_telemetry=cast(IntelligenceTelemetry, _Telemetry()),
    )

    output = await agent._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="execution-1",
        )
    )

    assert output.success is True
    assert output.outputs["regime"] == "risk_on_expansion"
    assert output.outputs["directional_score"] == 1.0
    assert output.outputs["confidence"] == pytest.approx(0.85)
    assert output.outputs["signals"] == [
        "fed:dovish",
        "liquidity:high_liquidity",
        "inflation:disinflationary",
    ]


@pytest.mark.asyncio
async def test_fundamental_agent_emits_degraded_telemetry_for_llm_fallback() -> None:
    telemetry = _Telemetry()
    agent = FundamentalAgent(
        llm_service=cast(LLMService, _FailingLLM()),
        macro_service=cast(MacroService, object()),
        service_runner=cast(ServiceRunner[Any, Any], _MacroRunner()),
        intelligence_telemetry=cast(IntelligenceTelemetry, telemetry),
    )

    output = await agent._execute(
        RuntimeContext(
            runtime_id="runtime-1",
            workflow_id="morning_report",
            execution_id="execution-1",
        )
    )

    assert output.success is True
    assert "LLM fallback activated" in output.outputs["llm_response"]
    assert len(telemetry.degraded) == 1
    assert telemetry.degraded[0]["agent_name"] == "fundamental_agent"
    assert telemetry.degraded[0]["reason"] == "llm_inference_failure"
    assert isinstance(telemetry.degraded[0]["error"], RuntimeError)
