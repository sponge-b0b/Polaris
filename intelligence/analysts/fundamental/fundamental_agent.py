from __future__ import annotations

from typing import Any

from application.services.base import ServiceRequest
from application.services.base import ServiceRunner
from application.services.macro.macro_request import MacroAnalysisRequest
from application.services.macro.macro_result import MacroAnalysisResult
from application.services.macro.macro_service import MacroService
from core.llm.llm_service import LLMService
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import (
    MACRO_ANALYSIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.prompts.system.fundamental_agent_prompt import (
    FUNDAMENTAL_AGENT_SYSTEM_PROMPT,
)
from intelligence.telemetry import telemetry_context_from_runtime


class FundamentalAgent(RuntimeNode):
    """
    Polaris Fundamental Agent.

    Returns node-specific business data through RuntimeNodeOutput.outputs.
    """

    node_name = "fundamental_agent"
    node_type = "macro_fundamental"

    def __init__(
        self,
        llm_service: LLMService,
        macro_service: MacroService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
    ) -> None:
        self.llm_service = llm_service
        self.macro_service = macro_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        try:
            macro_result = await self.service_runner.run(
                service=self.macro_service,
                request=ServiceRequest(
                    payload=MacroAnalysisRequest(),
                    telemetry_context=telemetry_context_from_runtime(
                        context,
                        node_name=self.node_name,
                    ),
                ),
            )

            macro_result.raise_if_failed()

            if macro_result.result is None:
                raise RuntimeError("Macro service returned no result data.")

            macro_data = macro_result.result

            llm_context = self.build_llm_context(
                macro_data.to_dict(),
            )

            try:
                llm_response = self.llm_service.chat(
                    system_prompt=FUNDAMENTAL_AGENT_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": llm_context,
                        }
                    ],
                )
            except Exception as error:
                await self.intelligence_telemetry.emit_agent_degraded(
                    agent_name=self.node_name,
                    reason="llm_inference_failure",
                    error=error,
                    context=telemetry_context_from_runtime(
                        context,
                        node_name=self.node_name,
                    ),
                )
                llm_response = (
                    "Fundamental interpretation unavailable; "
                    f"LLM fallback activated: {error}"
                )

            llm_response = str(
                llm_response,
            )

            confidence = self._calculate_confidence(
                macro_data,
            )

            directional_score = self._derive_direction(
                macro_data,
            )

            regime = str(
                macro_data.economic_regime.get(
                    "economic_regime",
                    "neutral",
                )
            )

            signals = [
                f"fed:{macro_data.fed_stance}",
                f"liquidity:{macro_data.liquidity_regime}",
                f"inflation:{macro_data.inflation_regime}",
            ]

            risks = [
                "Fed policy uncertainty",
                "Liquidity regime shifts",
                "Inflation volatility risk",
            ]

            recommendations = [
                "Monitor macro regime shifts",
                "Track liquidity conditions",
                "Observe rate expectations sensitivity",
            ]

            macro_analysis = macro_data.to_dict()
            observed_at = context.simulation_time or context.created_at

            features = {
                "macro_state": macro_analysis,
                "fundamental_summary": {
                    "fed": macro_data.fed_analysis,
                    "inflation": macro_data.inflation_analysis,
                    "liquidity": macro_data.liquidity_analysis,
                    "yield_curve": macro_data.yield_curve_analysis,
                },
            }

            output_data = {
                "agent_name": self.node_name,
                "agent_type": self.node_type,
                "observed_at": observed_at.isoformat(),
                "macro_source": "MacroService",
                "macro_region": "US",
                "macro_analysis": macro_analysis,
                "directional_score": directional_score,
                "confidence": confidence,
                "regime": regime,
                "signals": signals,
                "risks": risks,
                "recommendations": recommendations,
                "features": features,
                "llm_response": llm_response,
            }

            await self.intelligence_telemetry.emit_agent_signal(
                agent_name=self.node_name,
                signal_name="fundamental.macro_signal",
                confidence=confidence,
                context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
                payload={
                    "directional_score": directional_score,
                    "regime": regime,
                },
            )

            return RuntimeNodeOutput.success_output(
                outputs=output_data,
                execution_metadata={
                    "agent_name": self.node_name,
                    "agent_type": self.node_type,
                    "regime": regime,
                    "confidence": confidence,
                    "quality_status": "normal",
                },
                output_contract=MACRO_ANALYSIS_OUTPUT_CONTRACT,
                output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
            )

        except Exception as error:
            return RuntimeNodeOutput.failure_output(
                errors=[
                    {
                        "message": str(error),
                        "error_type": type(error).__name__,
                        "agent_name": self.node_name,
                        "agent_type": self.node_type,
                    }
                ],
                execution_metadata={
                    "agent_name": self.node_name,
                    "agent_type": self.node_type,
                    "error_type": type(error).__name__,
                },
            )

    def _calculate_confidence(
        self,
        macro_data: MacroAnalysisResult,
    ) -> float:
        confidence = 0.5

        inflation = macro_data.inflation_regime.lower()
        liquidity = macro_data.liquidity_regime.lower()
        fed = macro_data.fed_stance.lower()

        if inflation == "disinflationary":
            confidence += 0.1
        elif inflation in {"high_inflation", "elevated_inflation"}:
            confidence -= 0.1

        if liquidity in {"high_liquidity", "moderate_liquidity"}:
            confidence += 0.15
        elif liquidity in {"tightening_liquidity", "liquidity_crunch"}:
            confidence -= 0.15

        if "dovish" in fed:
            confidence += 0.1
        elif "hawkish" in fed:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _derive_direction(
        self,
        macro_data: MacroAnalysisResult,
    ) -> float:
        score = 0.0

        liquidity = macro_data.liquidity_regime.lower()
        fed = macro_data.fed_stance.lower()
        inflation = macro_data.inflation_regime.lower()

        if liquidity in {"high_liquidity", "moderate_liquidity"}:
            score += 0.4

        if "dovish" in fed:
            score += 0.3

        if inflation == "disinflationary":
            score += 0.3

        if liquidity in {"tightening_liquidity", "liquidity_crunch"}:
            score -= 0.4

        if "hawkish" in fed:
            score -= 0.3

        return max(-1.0, min(1.0, score))

    def build_llm_context(
        self,
        macro_data: dict[str, Any],
    ) -> str:
        return f"""
MACRO ENVIRONMENT DATA
======================

{macro_data}

TASK
======================

Analyze macro conditions for SPY trading.

Focus:
- Fed policy direction
- liquidity conditions
- inflation pressure
- growth momentum
- risk regime interpretation
"""
