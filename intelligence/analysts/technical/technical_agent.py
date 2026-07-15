from __future__ import annotations

from time import perf_counter
from typing import Any, Dict

from application.observability import AiObservationStatus
from application.observability import static_prompt_hash
from core.llm.llm_service import LLMService

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput

from core.utils.utils import _safe_float

from intelligence.prompts.system.technical_agent_prompt import (
    TECHNICAL_AGENT_SYSTEM_PROMPT,
)

from intelligence.observability import IntelligenceAiObservabilityProjectorPort
from intelligence.observability import IntelligenceAiObservabilityRecorder
from intelligence.observability import llm_model_name
from intelligence.observability import record_intelligence_generation_observation
from intelligence.telemetry import telemetry_context_from_runtime

from application.services.technical.technical_analysis_service import (
    TechnicalAnalysisService,
)
from application.services.base import ServiceRequest
from application.services.base import ServiceRunner
from application.services.technical.technical_request import (
    TechnicalAnalysisRequest,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from domain.workflow_outputs import (
    TECHNICAL_ANALYSIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


TECHNICAL_AGENT_SYSTEM_PROMPT_HASH = static_prompt_hash(TECHNICAL_AGENT_SYSTEM_PROMPT)


class TechnicalAgent(RuntimeNode):
    """
    Polaris Technical Analysis Agent

    PURPOSE:
    --------
    - consume calibrated TechnicalService outputs
    - preserve deterministic regime calculations
    - enrich with LLM interpretation layer
    - output canonical RuntimeNodeOutput

    IMPORTANT:
    ----------
    TechnicalService is the SOURCE OF TRUTH.

    This agent MUST NOT:
    - recompute calibrated regime
    - override service regime logic
    - generate conflicting directional scores

    This agent MAY:
    - derive secondary descriptive states
    - generate narrative interpretation
    - expose synthesis-ready features
    """

    node_name = "technical_agent"
    node_type = "technical_analysis"

    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self,
        llm_service: LLMService,
        technical_service: TechnicalAnalysisService,
        service_runner: ServiceRunner[Any, Any],
        intelligence_telemetry: IntelligenceTelemetry,
        ai_observability_projector: IntelligenceAiObservabilityProjectorPort
        | None = None,
    ) -> None:

        self.llm_service = llm_service
        self.technical_service = technical_service
        self.service_runner = service_runner
        self.intelligence_telemetry = intelligence_telemetry
        self.ai_observability = IntelligenceAiObservabilityRecorder(
            ai_observability_projector
        )

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        # ========================================================
        # INPUTS
        # ========================================================

        symbol = context.workflow_inputs.get(
            "symbol",
            "SPY",
        )

        days = context.workflow_inputs.get(
            "days",
            365,
        )

        # ========================================================
        # TECHNICAL SERVICE
        # ========================================================

        technical_result = await self.service_runner.run(
            service=self.technical_service,
            request=ServiceRequest(
                payload=TechnicalAnalysisRequest(
                    symbol=str(symbol),
                    days=int(days),
                ),
                telemetry_context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
            ),
        )
        technical_result.raise_if_failed()

        if technical_result.result is None:
            raise RuntimeError("Technical service returned no result data.")

        tech_snapshot = technical_result.result

        # ========================================================
        # CORE SNAPSHOTS
        # ========================================================

        snapshot = tech_snapshot.snapshot
        trend = tech_snapshot.trend
        volatility = tech_snapshot.volatility
        breadth = tech_snapshot.breadth
        market_context = tech_snapshot.market_context
        raw_regime = tech_snapshot.raw_regime
        regime = tech_snapshot.regime

        breadth_state = self._build_breadth_state(
            breadth=breadth,
            market_context=market_context,
        )

        # ========================================================
        # SERVICE IS SOURCE OF TRUTH
        # ========================================================

        directional_score = float(
            regime.get(
                "directional_technical_score",
                0.0,
            )
        )

        confidence = float(
            regime.get(
                "confidence",
                0.5,
            )
        )

        trend_direction = str(
            trend.get(
                "primary_trend",
                regime.get(
                    "regime",
                    "neutral",
                ),
            )
        )

        # ========================================================
        # SECONDARY DERIVED STATES
        # ========================================================

        rsi = float(
            snapshot.get(
                "rsi_14",
                50.0,
            )
        )

        momentum_state = self._determine_rsi_state(rsi)

        macd_state = self._determine_macd_state(
            float(
                snapshot.get(
                    "macd",
                    0.0,
                )
            ),
            float(
                snapshot.get(
                    "macd_signal",
                    0.0,
                )
            ),
        )

        # ========================================================
        # EXECUTION READINESS
        # ========================================================

        execution_readiness = self._calculate_execution_readiness(
            regime=regime,
            volatility=volatility,
        )

        # ========================================================
        # SIGNAL QUALITY
        # ========================================================

        signal_quality = self._calculate_signal_quality(
            regime=regime,
            trend=trend,
            volatility=volatility,
        )

        # ========================================================
        # LLM CONTEXT
        # ========================================================

        llm_context = self.build_llm_context(
            symbol=symbol,
            snapshot=snapshot,
            trend=trend,
            volatility=volatility,
            breadth=breadth,
            market_context=market_context,
            raw_regime=raw_regime,
            regime=regime,
        )

        # ========================================================
        # LLM INFERENCE
        # ========================================================

        llm_started_at = perf_counter()
        llm_status = AiObservationStatus.SUCCESS
        try:
            llm_response = await self.llm_service.chat(
                system_prompt=(TECHNICAL_AGENT_SYSTEM_PROMPT),
                response_format="json",
                messages=[
                    {
                        "role": "user",
                        "content": llm_context,
                    }
                ],
            )
        except Exception as error:
            llm_status = AiObservationStatus.FAILED
            await self.intelligence_telemetry.emit_agent_degraded(
                agent_name=self.node_name,
                reason="llm_inference_failure",
                error=error,
                context=telemetry_context_from_runtime(
                    context,
                    node_name=self.node_name,
                ),
            )
            llm_response = {
                "error": "llm_inference_failure",
                "message": str(error),
            }

        # ========================================================
        # FAILSAFE
        # ========================================================

        if not isinstance(llm_response, dict) or "error" in llm_response:
            llm_status = AiObservationStatus.DEGRADED
            llm_response = {
                "outlook": trend_direction,
                "summary": ("Technical analysis fallback mode."),
                "signals": ["llm_inference_failure"],
                "risks": ["llm_inference_failure"],
                "recommendations": ["validate_llm_service"],
                "key_points": [],
                "support_levels": [],
                "resistance_levels": [],
            }

        await record_intelligence_generation_observation(
            self.ai_observability,
            context=context,
            node_name=self.node_name,
            component_name="technical_llm_reasoning",
            status=llm_status,
            latency_seconds=perf_counter() - llm_started_at,
            model_name=llm_model_name(self.llm_service),
            provider_name="LLMService",
            prompt_name="technical_agent_system_prompt",
            prompt_version="static-v1",
            prompt_hash=TECHNICAL_AGENT_SYSTEM_PROMPT_HASH,
            input_shape=(
                f"context_characters={len(llm_context)};"
                f"breadth_fields={len(breadth)};"
                f"market_context_fields={len(market_context)}"
            ),
            output_shape=f"response_keys={len(llm_response)}",
            metadata={
                "symbol": str(symbol),
                "regime": str(regime.get("regime", "neutral")),
                "confidence": confidence,
                "fallback": llm_status is not AiObservationStatus.SUCCESS,
            },
        )

        # ========================================================
        # SIGNALS
        # ========================================================

        signals = [
            f"trend:{trend_direction}",
            f"momentum:{momentum_state}",
            f"macd:{macd_state}",
            f"confidence:{confidence}",
            f"directional_score:{directional_score}",
        ]

        signals.extend(
            self._breadth_signal_tags(
                breadth_state,
            )
        )

        signals.extend(
            llm_response.get(
                "signals",
                [],
            )
        )

        # ========================================================
        # RISKS
        # ========================================================

        risks = list(
            llm_response.get(
                "risks",
                [],
            )
        )

        if confidence < 0.40:
            risks.append("low_technical_confidence")

        if volatility.get("volatility_regime") == "high_volatility":
            risks.append("high_volatility_environment")

        risks.extend(
            self._breadth_risk_flags(
                breadth_state,
            )
        )

        # ========================================================
        # RECOMMENDATIONS
        # ========================================================

        recommendations = list(
            llm_response.get(
                "recommendations",
                [],
            )
        )

        if execution_readiness < 0.40:
            recommendations.append("reduce_position_size")

        recommendations.extend(
            self._breadth_recommendations(
                breadth_state,
            )
        )

        # ========================================================
        # BUILD RESULT
        # ========================================================

        observed_at = context.simulation_time or context.created_at

        result = dict(
            observed_at=observed_at.isoformat(),
            market_universe="sp500",
            directional_score=directional_score,
            confidence=confidence,
            regime=regime.get(
                "regime",
                "neutral",
            ),
            signals=list(
                dict.fromkeys(
                    signals,
                )
            ),
            risks=list(
                dict.fromkeys(
                    risks,
                )
            ),
            recommendations=list(
                dict.fromkeys(
                    recommendations,
                )
            ),
            features={
                # ====================================================
                # CORE SERVICE OUTPUTS
                # ====================================================
                "symbol": symbol,
                "technical_score": directional_score,
                "snapshot": snapshot,
                "trend": trend,
                "volatility": volatility,
                "breadth": breadth,
                "breadth_state": breadth_state,
                "market_context": market_context,
                "raw_regime": raw_regime,
                "regime": {
                    **regime,
                    # synthesis-critical fields
                    "execution_readiness": execution_readiness,
                    "signal_quality": signal_quality,
                },
                # ====================================================
                # SECONDARY INTERPRETATION
                # ====================================================
                "technical_state": {
                    "trend_direction": trend_direction,
                    "momentum_state": momentum_state,
                    "macd_state": macd_state,
                },
                # ====================================================
                # LLM INTERPRETATION
                # ====================================================
                "outlook": llm_response.get(
                    "outlook",
                    trend_direction,
                ),
                "summary": llm_response.get(
                    "summary",
                    "",
                ),
                "key_points": llm_response.get(
                    "key_points",
                    [],
                ),
                "support_levels": llm_response.get(
                    "support_levels",
                    [],
                ),
                "resistance_levels": llm_response.get(
                    "resistance_levels",
                    [],
                ),
            },
            llm_response=llm_response,
        )

        await self.intelligence_telemetry.emit_agent_signal(
            agent_name=self.node_name,
            signal_name="technical.analysis_signal",
            confidence=confidence,
            context=telemetry_context_from_runtime(
                context,
                node_name=self.node_name,
            ),
            payload={
                "directional_score": directional_score,
                "regime": result["regime"],
                "symbol": symbol,
            },
        )

        # ========================================================
        # RETURN NODE OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": confidence,
                **(
                    {
                        "source": "TechnicalService",
                        "symbol": symbol,
                        "quality_status": "normal",
                    }
                ),
            },
            output_contract=TECHNICAL_ANALYSIS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )

    # ============================================================
    # RSI STATE
    # ============================================================

    def _determine_rsi_state(
        self,
        rsi: float,
    ) -> str:

        if rsi >= 75:
            return "extreme_bullish"

        if rsi >= 60:
            return "bullish_momentum"

        if rsi <= 25:
            return "extreme_bearish"

        if rsi <= 40:
            return "bearish_momentum"

        return "neutral"

    # ============================================================
    # MACD STATE
    # ============================================================

    def _determine_macd_state(
        self,
        macd: float,
        signal: float,
    ) -> str:

        if macd > signal:
            return "bullish"

        if macd < signal:
            return "bearish"

        return "neutral"

    # ============================================================
    # EXECUTION READINESS
    # ============================================================

    def _calculate_execution_readiness(
        self,
        regime: Dict[str, Any],
        volatility: Dict[str, Any],
    ) -> float:

        confidence = float(
            regime.get(
                "confidence",
                0.5,
            )
        )

        directional_score = abs(
            float(
                regime.get(
                    "directional_technical_score",
                    0.0,
                )
            )
        )

        vol_score = float(
            volatility.get(
                "volatility_score",
                0.5,
            )
        )

        readiness = directional_score * 0.45 + confidence * 0.35 + vol_score * 0.20

        return max(
            0.0,
            min(1.0, readiness),
        )

    # ============================================================
    # SIGNAL QUALITY
    # ============================================================

    def _calculate_signal_quality(
        self,
        regime: Dict[str, Any],
        trend: Dict[str, Any],
        volatility: Dict[str, Any],
    ) -> float:

        confidence = float(
            regime.get(
                "confidence",
                0.5,
            )
        )

        trend_strength = float(
            trend.get(
                "trend_strength",
                0.5,
            )
        )

        vol_score = float(
            volatility.get(
                "volatility_score",
                0.5,
            )
        )

        quality = confidence * 0.40 + trend_strength * 0.40 + vol_score * 0.20

        return max(
            0.0,
            min(1.0, quality),
        )

    # ============================================================
    # BREADTH STATE
    # ============================================================

    def _build_breadth_state(
        self,
        *,
        breadth: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> Dict[str, Any]:

        has_breadth = bool(
            breadth.get(
                "has_breadth_data",
                market_context.get(
                    "has_breadth",
                    False,
                ),
            )
        )

        return {
            "has_breadth_data": has_breadth,
            "breadth_regime": breadth.get(
                "breadth_regime",
                "unavailable" if not has_breadth else "neutral",
            ),
            "risk_regime": breadth.get(
                "risk_regime",
                "unknown",
            ),
            "strategy_environment": breadth.get(
                "strategy_environment",
                {},
            ),
            "breadth_score": _safe_float(
                breadth.get(
                    "breadth_score",
                )
            ),
            "breadth_risk_score": _safe_float(
                breadth.get(
                    "breadth_risk_score",
                    0.5,
                ),
                default=0.5,
            ),
            "participation_score": _safe_float(
                breadth.get(
                    "participation_score",
                )
            ),
            "leadership_score": _safe_float(
                breadth.get(
                    "leadership_score",
                )
            ),
            "mcclellan_score": _safe_float(
                breadth.get(
                    "mcclellan_score",
                )
            ),
            "divergence_score": _safe_float(
                breadth.get(
                    "divergence_score",
                )
            ),
            "price_ad_divergence": bool(
                breadth.get(
                    "price_ad_divergence",
                    market_context.get(
                        "price_ad_divergence",
                        False,
                    ),
                )
            ),
            "breadth_percent": _safe_float(
                breadth.get(
                    "breadth_percent",
                    market_context.get(
                        "breadth_percent",
                    ),
                )
            ),
            "pct_above_50dma": _safe_float(
                breadth.get(
                    "pct_above_50dma",
                    market_context.get(
                        "pct_above_50dma",
                    ),
                )
            ),
            "pct_above_200dma": _safe_float(
                breadth.get(
                    "pct_above_200dma",
                    market_context.get(
                        "pct_above_200dma",
                    ),
                )
            ),
            "new_high_low_diff": _safe_float(
                breadth.get(
                    "new_high_low_diff",
                    market_context.get(
                        "new_high_low_diff",
                    ),
                )
            ),
            "mcclellan_oscillator": _safe_float(
                breadth.get(
                    "mcclellan_oscillator",
                    market_context.get(
                        "mcclellan_oscillator",
                    ),
                )
            ),
        }

    def _breadth_signal_tags(
        self,
        breadth_state: Dict[str, Any],
    ) -> list[str]:

        if not breadth_state.get(
            "has_breadth_data",
        ):
            return [
                "breadth:unavailable",
            ]

        return [
            f"breadth:{breadth_state.get('breadth_regime', 'neutral')}",
            f"breadth_score:{_safe_float(breadth_state.get('breadth_score'))}",
            f"participation:{_safe_float(breadth_state.get('participation_score'))}",
            f"mcclellan:{_safe_float(breadth_state.get('mcclellan_score'))}",
            f"price_ad_divergence:{str(bool(breadth_state.get('price_ad_divergence'))).lower()}",
        ]

    def _breadth_risk_flags(
        self,
        breadth_state: Dict[str, Any],
    ) -> list[str]:

        if not breadth_state.get(
            "has_breadth_data",
        ):
            return []

        flags: list[str] = []

        breadth_score = _safe_float(
            breadth_state.get(
                "breadth_score",
            )
        )
        breadth_risk_score = _safe_float(
            breadth_state.get(
                "breadth_risk_score",
                0.5,
            ),
            default=0.5,
        )
        participation_score = _safe_float(
            breadth_state.get(
                "participation_score",
            )
        )
        leadership_score = _safe_float(
            breadth_state.get(
                "leadership_score",
            )
        )

        if breadth_score <= -0.35:
            flags.append(
                "weak_market_breadth",
            )

        if breadth_risk_score >= 0.65:
            flags.append(
                "elevated_breadth_risk",
            )

        if bool(
            breadth_state.get(
                "price_ad_divergence",
            )
        ):
            flags.append(
                "price_ad_divergence",
            )

        if participation_score < -0.25 or leadership_score < -0.25:
            flags.append(
                "narrow_market_leadership",
            )

        return flags

    def _breadth_recommendations(
        self,
        breadth_state: Dict[str, Any],
    ) -> list[str]:

        if not breadth_state.get(
            "has_breadth_data",
        ):
            return []

        recommendations: list[str] = []
        breadth_score = _safe_float(
            breadth_state.get(
                "breadth_score",
            )
        )
        breadth_risk_score = _safe_float(
            breadth_state.get(
                "breadth_risk_score",
                0.5,
            ),
            default=0.5,
        )

        if bool(
            breadth_state.get(
                "price_ad_divergence",
            )
        ):
            recommendations.append(
                "validate_breakout_with_participation",
            )

        if breadth_score < 0.0:
            recommendations.append(
                "wait_for_breadth_confirmation",
            )

        if breadth_risk_score >= 0.65:
            recommendations.append(
                "reduce_risk_until_breadth_improves",
            )

        return recommendations

    # ============================================================
    # LLM CONTEXT
    # ============================================================

    def build_llm_context(
        self,
        symbol: str,
        snapshot: Dict[str, Any],
        trend: Dict[str, Any],
        volatility: Dict[str, Any],
        breadth: Dict[str, Any],
        market_context: Dict[str, Any],
        raw_regime: Dict[str, Any],
        regime: Dict[str, Any],
    ) -> str:

        return f"""
TECHNICAL SYSTEM STATE
======================

Ticker:
{symbol}

PRICE SNAPSHOT
======================

Close:
{snapshot.get("close")}

EMA 8:
{snapshot.get("ema_8")}

EMA 21:
{snapshot.get("ema_21")}

EMA 50:
{snapshot.get("ema_50")}

EMA 200:
{snapshot.get("ema_200")}

RSI 14:
{snapshot.get("rsi_14")}

MACD:
{snapshot.get("macd")}

MACD SIGNAL:
{snapshot.get("macd_signal")}

MACD HISTOGRAM:
{snapshot.get("macd_histogram")}

ATR 14:
{snapshot.get("atr_14")}

TREND ENGINE
======================

{trend}

VOLATILITY ENGINE
======================

{volatility}

MARKET BREADTH ENGINE
======================

{breadth}

S&P 500 MARKET CONTEXT
======================

Advance / Decline Line:
{market_context.get("ad_line")}

Advance / Decline Ratio:
{market_context.get("ad_ratio")}

Breadth Percent:
{market_context.get("breadth_percent")}

Percent Above 50DMA:
{market_context.get("pct_above_50dma")}

Percent Above 200DMA:
{market_context.get("pct_above_200dma")}

New Highs:
{market_context.get("new_highs")}

New Lows:
{market_context.get("new_lows")}

McClellan Oscillator:
{market_context.get("mcclellan_oscillator")}

McClellan Summation Index:
{market_context.get("mcclellan_summation_index")}

Price / A-D Divergence:
{market_context.get("price_ad_divergence")}

RAW REGIME
======================

{raw_regime}

CALIBRATED REGIME
======================

{regime}

TASK
======================

Analyze the current technical structure for SPY.

Focus on:
- trend strength
- momentum confirmation
- volatility conditions
- S&P 500 breadth participation and leadership
- advance / decline confirmation
- price versus advance-decline divergence
- McClellan oscillator confirmation
- market structure quality
- breakout vs exhaustion behavior
- directional conviction
- execution quality

Evaluate:
- EMA alignment
- RSI behavior
- MACD confirmation
- volatility regime
- structural persistence

Do NOT:
- generate trade orders
- guarantee outcomes
- use emotional language
- provide certainty statements

Return structured JSON only.
"""
