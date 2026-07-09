from __future__ import annotations

from typing import Any

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.analysts.technical.technical_breadth_context import (
    extract_technical_breadth_context,
)

from integration.contracts.execution.trade_intent_contract import (
    TradeIntentContract,
)


class TradePackager(RuntimeNode):
    """
    Polaris Trade Packager

    PURPOSE:
    --------
    - Convert fused intelligence into execution-ready trade intent
    - Fuse sentiment + technical + risk layers
    - Produce deterministic execution payload
    - Remain execution-engine agnostic

    DOES NOT:
    ----------
    - execute trades
    - enforce portfolio rules
    - override risk guard decisions
    """

    node_name = "trade_packager"
    node_type = "trade_packager"

    LONG_THRESHOLD = 0.25
    SHORT_THRESHOLD = -0.25

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

        symbol = context.workflow_inputs.get("symbol", "SPY")

        sentiment_result: dict[str, Any] = context.node_outputs["sentiment_agent"].get(
            "outputs", {}
        )

        technical_result: dict[str, Any] = context.node_outputs["technical_agent"].get(
            "outputs", {}
        )

        risk_result: dict[str, Any] = context.node_outputs["risk_aggregator_agent"].get(
            "outputs", {}
        )

        # ========================================================
        # SENTIMENT
        # ========================================================

        sentiment_score = float(sentiment_result.get("directional_score", 0.0))

        sentiment_confidence = float(sentiment_result.get("confidence", 0.0))

        # ========================================================
        # TECHNICAL
        # ========================================================

        trend_score = float(technical_result.get("directional_score", 0.0))

        technical_confidence = float(technical_result.get("confidence", 0.0))

        technical_regime = str(technical_result.get("regime", "neutral"))

        breadth_context = extract_technical_breadth_context(
            context.node_outputs["technical_agent"],
        )

        # ========================================================
        # RISK
        # ========================================================

        risk_score = float(risk_result.get("directional_score", 0.0))

        risk_pressure = float(
            risk_result.get("features", {}).get(
                "risk_pressure",
                abs(risk_score),
            )
        )

        # ========================================================
        # CONFIDENCE FUSION
        # ========================================================

        confidence = (sentiment_confidence + technical_confidence) / 2.0

        confidence = self._clamp_01(confidence)

        # ========================================================
        # ENTRY BIAS
        # ========================================================

        raw_entry_bias = (
            (sentiment_score * 0.40) + (trend_score * 0.50) - (risk_pressure * 0.10)
        )

        breadth_entry_bias_modifier = self._breadth_entry_bias_modifier(
            raw_entry_bias=raw_entry_bias,
            breadth_context=breadth_context,
        )

        entry_bias = raw_entry_bias + breadth_entry_bias_modifier

        entry_bias = self._clamp(entry_bias)

        # ========================================================
        # DIRECTION
        # ========================================================

        direction = self._classify_direction(entry_bias)

        # ========================================================
        # RISK ALIGNMENT
        # ========================================================

        risk_alignment = 1.0 - abs(risk_score)

        risk_alignment = self._clamp_01(risk_alignment)

        # ========================================================
        # POSITION SIZE
        # ========================================================

        base_position_sizing_hint = self._compute_position_size(
            confidence=confidence,
            risk_score=risk_score,
        )

        breadth_position_size_multiplier = self._breadth_position_size_multiplier(
            raw_entry_bias=raw_entry_bias,
            direction=direction,
            breadth_context=breadth_context,
        )

        position_sizing_hint = self._clamp_01(
            base_position_sizing_hint * breadth_position_size_multiplier
        )

        # ========================================================
        # BRACKETS
        # ========================================================

        stop_distance, take_profit_distance = self._compute_brackets(
            risk_score=risk_score,
            trend_score=trend_score,
        )

        # ========================================================
        # QUALITY SCORE
        # ========================================================

        trade_quality_score = self._compute_quality(
            entry_bias=entry_bias,
            confidence=confidence,
            risk_alignment=risk_alignment,
        )

        # ========================================================
        # TRADE CONTRACT
        # ========================================================

        trade_intent = TradeIntentContract(
            symbol=symbol,
            direction=direction,
            entry_bias=entry_bias,
            position_sizing_hint=position_sizing_hint,
            stop_distance=stop_distance,
            take_profit_distance=take_profit_distance,
            trade_quality_score=trade_quality_score,
            confidence=confidence,
            reasoning={
                "sentiment_score": sentiment_score,
                "trend_score": trend_score,
                "risk_score": risk_score,
                "risk_pressure": risk_pressure,
                "technical_regime": technical_regime,
                "raw_entry_bias": raw_entry_bias,
                "breadth_context": breadth_context.to_dict(),
                "breadth_entry_bias_modifier": (breadth_entry_bias_modifier),
                "breadth_position_size_multiplier": (breadth_position_size_multiplier),
            },
        )

        # ========================================================
        # SIGNALS
        # ========================================================

        signals = [
            f"direction:{direction}",
            f"entry_bias:{round(entry_bias, 4)}",
            f"trend_score:{round(trend_score, 4)}",
            f"sentiment_score:{round(sentiment_score, 4)}",
            f"risk_pressure:{round(risk_pressure, 4)}",
        ]

        signals = self._deduplicate(
            [
                *signals,
                *self._breadth_signals(
                    raw_entry_bias=raw_entry_bias,
                    direction=direction,
                    breadth_context=breadth_context,
                ),
            ]
        )

        # ========================================================
        # RISKS
        # ========================================================

        risks = []

        if abs(risk_score) > 0.7:
            risks.append("elevated_risk_environment")

        if confidence < 0.4:
            risks.append("low_signal_confidence")

        if direction == "flat":
            risks.append("low_directional_conviction")

        risks = self._deduplicate(
            [
                *risks,
                *self._breadth_risks(
                    raw_entry_bias=raw_entry_bias,
                    direction=direction,
                    breadth_context=breadth_context,
                ),
            ]
        )

        # ========================================================
        # RECOMMENDATIONS
        # ========================================================

        recommendations = []

        if direction == "long":
            recommendations.append("favor_long_exposure")

        elif direction == "short":
            recommendations.append("favor_short_exposure")

        else:
            recommendations.append("reduce_directional_exposure")

        if abs(risk_score) > 0.6:
            recommendations.append("decrease_position_size")

        recommendations = self._deduplicate(
            [
                *recommendations,
                *self._breadth_recommendations(
                    raw_entry_bias=raw_entry_bias,
                    direction=direction,
                    breadth_context=breadth_context,
                ),
            ]
        )

        # ========================================================
        # RESULT
        # ========================================================

        result = dict(
            directional_score=entry_bias,
            confidence=confidence,
            regime=direction,
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features={
                "symbol": symbol,
                "trade_intent": {
                    "symbol": trade_intent.symbol,
                    "direction": trade_intent.direction,
                    "entry_bias": trade_intent.entry_bias,
                    "position_sizing_hint": (trade_intent.position_sizing_hint),
                    "stop_distance": (trade_intent.stop_distance),
                    "take_profit_distance": (trade_intent.take_profit_distance),
                    "trade_quality_score": (trade_intent.trade_quality_score),
                    "confidence": (trade_intent.confidence),
                    "reasoning": (trade_intent.reasoning),
                },
                "risk_alignment": risk_alignment,
                "trade_quality_score": (trade_quality_score),
                "position_sizing_hint": (position_sizing_hint),
                "base_position_sizing_hint": (base_position_sizing_hint),
                "breadth_position_size_multiplier": (breadth_position_size_multiplier),
                "technical_regime": (technical_regime),
                "breadth_context": (breadth_context.to_dict()),
                "breadth_confirmation_score": (breadth_context.confirmation_score),
                "breadth_risk_pressure": (breadth_context.risk_pressure),
                "breadth_entry_bias_modifier": (breadth_entry_bias_modifier),
                "breadth_risk_flags": list(
                    breadth_context.risk_flags(),
                ),
                "risk_score": risk_score,
                "risk_pressure": risk_pressure,
                "raw_entry_bias": raw_entry_bias,
                "trend_score": trend_score,
                "sentiment_score": sentiment_score,
                "stop_distance": stop_distance,
                "take_profit_distance": (take_profit_distance),
            },
        )

        # ========================================================
        # OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": (confidence),
                **(
                    {
                        "symbol": symbol,
                        "direction": direction,
                    }
                ),
            },
        )

    # ============================================================
    # HELPERS
    # ============================================================

    def _classify_direction(
        self,
        bias: float,
    ) -> str:

        if bias > self.LONG_THRESHOLD:
            return "long"

        if bias < self.SHORT_THRESHOLD:
            return "short"

        return "flat"

    # ============================================================

    def _compute_position_size(
        self,
        confidence: float,
        risk_score: float,
    ) -> float:

        base = confidence * (1.0 - abs(risk_score))

        return self._clamp_01(base)

    # ============================================================

    def _compute_brackets(
        self,
        risk_score: float,
        trend_score: float,
    ) -> tuple[float, float]:

        volatility_factor = 1.0 + abs(risk_score)

        stop = 1.0 * volatility_factor

        take_profit = (1.5 + abs(trend_score)) * volatility_factor

        return (
            round(stop, 4),
            round(take_profit, 4),
        )

    # ============================================================

    def _compute_quality(
        self,
        entry_bias: float,
        confidence: float,
        risk_alignment: float,
    ) -> float:

        score = (abs(entry_bias) * 0.4) + (confidence * 0.3) + (risk_alignment * 0.3)

        return self._clamp_01(score)

    # ============================================================

    def _breadth_entry_bias_modifier(
        self,
        *,
        raw_entry_bias: float,
        breadth_context: TechnicalBreadthContext,
    ) -> float:

        if not breadth_context.has_breadth_data:
            return 0.0

        modifier = 0.0

        if raw_entry_bias > 0.0:
            if breadth_context.is_weak:
                modifier -= 0.12
            if breadth_context.price_ad_divergence:
                modifier -= 0.05
            if breadth_context.is_strong:
                modifier += min(
                    0.04,
                    breadth_context.confirmation_score * 0.06,
                )

        if raw_entry_bias < 0.0:
            if breadth_context.is_strong:
                modifier += 0.12
            if breadth_context.is_weak:
                modifier -= min(
                    0.04,
                    abs(breadth_context.confirmation_score) * 0.05,
                )

        return self._clamp_range(
            modifier,
            minimum=-0.20,
            maximum=0.16,
        )

    # ============================================================

    def _breadth_position_size_multiplier(
        self,
        *,
        raw_entry_bias: float,
        direction: str,
        breadth_context: TechnicalBreadthContext,
    ) -> float:

        if not breadth_context.has_breadth_data:
            return 1.0

        multiplier = 1.0

        if raw_entry_bias > 0.0 and breadth_context.is_weak:
            multiplier -= 0.25

        if raw_entry_bias > 0.0 and breadth_context.price_ad_divergence:
            multiplier -= 0.10

        if raw_entry_bias < 0.0 and breadth_context.is_strong:
            multiplier -= 0.25

        if direction == "flat":
            multiplier = min(
                multiplier,
                0.50,
            )

        return self._clamp_range(
            multiplier,
            minimum=0.35,
            maximum=1.05,
        )

    # ============================================================

    def _breadth_signals(
        self,
        *,
        raw_entry_bias: float,
        direction: str,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:

        if not breadth_context.has_breadth_data:
            return []

        signals = [
            f"breadth:{breadth_context.breadth_regime}",
        ]

        if raw_entry_bias > 0.0 and breadth_context.is_weak:
            signals.append(
                "weak_breadth_dampens_long_trade_intent",
            )

        if raw_entry_bias < 0.0 and breadth_context.is_strong:
            signals.append(
                "strong_breadth_dampens_short_trade_intent",
            )

        if breadth_context.price_ad_divergence:
            signals.append(
                "breadth_divergence_reduces_trade_conviction",
            )

        if direction == "flat" and abs(raw_entry_bias) > 0.0:
            signals.append(
                "breadth_adjusted_trade_to_flat",
            )

        return signals

    # ============================================================

    def _breadth_risks(
        self,
        *,
        raw_entry_bias: float,
        direction: str,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:

        if not breadth_context.has_breadth_data:
            return []

        risks = list(
            breadth_context.risk_flags(),
        )

        if raw_entry_bias > 0.0 and breadth_context.is_weak:
            risks.append(
                "long_breadth_confirmation_failure",
            )

        if raw_entry_bias < 0.0 and breadth_context.is_strong:
            risks.append(
                "short_against_strong_breadth_risk",
            )

        if direction == "flat" and abs(raw_entry_bias) > 0.0:
            risks.append(
                "breadth_reduced_directional_intent",
            )

        return risks

    # ============================================================

    def _breadth_recommendations(
        self,
        *,
        raw_entry_bias: float,
        direction: str,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:

        if not breadth_context.has_breadth_data:
            return []

        recommendations: list[str] = []

        if raw_entry_bias > 0.0 and breadth_context.is_weak:
            recommendations.extend(
                [
                    "wait_for_breadth_confirmation_before_long_exposure",
                    "reduce_position_size_for_breadth_risk",
                ]
            )

        if raw_entry_bias < 0.0 and breadth_context.is_strong:
            recommendations.extend(
                [
                    "avoid_short_bias_against_strong_breadth",
                    "reduce_short_size_until_breadth_weakens",
                ]
            )

        if direction == "flat" and abs(raw_entry_bias) > 0.0:
            recommendations.append(
                "keep_trade_intent_on_watchlist_until_breadth_confirms",
            )

        return recommendations

    # ============================================================

    def _deduplicate(
        self,
        values: list[str],
    ) -> list[str]:

        return list(
            dict.fromkeys(
                values,
            )
        )

    # ============================================================

    def _clamp_range(
        self,
        value: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:

        return max(
            minimum,
            min(
                maximum,
                float(value),
            ),
        )

    # ============================================================

    def _clamp(
        self,
        value: float,
    ) -> float:

        return max(
            -1.0,
            min(1.0, float(value)),
        )

    # ============================================================

    def _clamp_01(
        self,
        value: float,
    ) -> float:

        return max(
            0.0,
            min(1.0, float(value)),
        )
