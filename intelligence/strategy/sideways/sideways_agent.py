from __future__ import annotations


from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.analysts.technical.technical_breadth_context import (
    extract_technical_breadth_context,
)


class SidewaysAgent(RuntimeNode):
    """
    Polaris Sideways Agent

    ============================================================
    PURPOSE
    ============================================================
    - identify range-bound market conditions
    - detect low directional conviction
    - evaluate mean-reversion environments
    - synthesize multi-domain neutrality signals

    ============================================================
    REQUIRED INPUTS
    ============================================================
    context.node_outputs["sentiment_agent"]
    context.node_outputs["technical_agent"]

    ============================================================
    OPTIONAL INPUTS
    ============================================================
    context.node_outputs["fundamental_agent"]
    context.node_outputs["news_agent"]
    context.node_outputs["risk_aggregator_agent"]

    ============================================================
    DESIGN PRINCIPLES
    ============================================================
    - deterministic
    - bounded outputs
    - regime-aware
    - execution agnostic
    """

    node_name = "sideways_agent"
    node_type = "sideways_strategy"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        node_outputs = context.node_outputs

        # ========================================================
        # REQUIRED INPUTS
        # ========================================================

        sentiment_output = node_outputs.get("sentiment_agent")

        technical_output = node_outputs.get("technical_agent")

        if sentiment_output is None:
            raise ValueError(
                "SidewaysAgent requires 'sentiment_agent' in node_outputs."
            )

        if technical_output is None:
            raise ValueError(
                "SidewaysAgent requires 'technical_agent' in node_outputs."
            )

        # ========================================================
        # OPTIONAL INPUTS
        # ========================================================

        fundamental_output = node_outputs.get("fundamental_agent")

        news_output = node_outputs.get("news_agent")

        risk_output = node_outputs.get("risk_aggregator_agent")

        # ========================================================
        # SENTIMENT
        # ========================================================

        sentiment_result = sentiment_output.get("outputs", {})

        sentiment_score = float(sentiment_result.get("directional_score", 0.0))

        sentiment_confidence = float(sentiment_result.get("confidence", 0.0))

        sentiment_features = sentiment_result.get("features", {}) or {}

        stability = float(
            sentiment_features.get(
                "stability",
                0.5,
            )
        )

        divergence_data = sentiment_features.get(
            "divergence",
            {},
        )

        divergence = float(
            divergence_data.get(
                "avg_divergence",
                0.0,
            )
        )

        momentum = float(
            sentiment_features.get(
                "momentum",
                0.0,
            )
        )

        # ========================================================
        # TECHNICAL
        # ========================================================

        technical_result = technical_output.get("outputs", {})

        technical_score = float(technical_result.get("directional_score", 0.0))

        technical_confidence = float(technical_result.get("confidence", 0.0))

        technical_features = technical_result.get("features", {}) or {}

        trend = technical_features.get(
            "trend",
            {},
        )

        regime = technical_features.get(
            "regime",
            {},
        )

        volatility = technical_features.get(
            "volatility",
            {},
        )

        technical_regime = str(
            regime.get(
                "regime",
                "neutral",
            )
        )

        trend_strength = float(
            trend.get(
                "trend_strength",
                0.0,
            )
        )

        volatility_score = float(
            volatility.get(
                "volatility_score",
                0.0,
            )
        )

        volatility_regime = str(
            volatility.get(
                "volatility_regime",
                "normal",
            )
        )

        breadth_context = extract_technical_breadth_context(
            technical_output,
        )

        # ========================================================
        # FUNDAMENTAL
        # ========================================================

        fundamental_directional = 0.0

        if fundamental_output is not None:
            fundamental_result = fundamental_output.get("outputs", {})

            fundamental_directional = float(
                fundamental_result.get("directional_score", 0.0)
            )

        # ========================================================
        # NEWS
        # ========================================================

        news_directional = 0.0

        if news_output is not None:
            news_result = news_output.get("outputs", {})

            news_directional = float(news_result.get("directional_score", 0.0))

        # ========================================================
        # RISK
        # ========================================================

        risk_pressure = 0.0

        if risk_output is not None:
            risk_result = risk_output.get("outputs", {})

            risk_features = risk_result.get("features", {}) or {}

            risk_pressure = float(
                risk_features.get(
                    "risk_pressure",
                    0.0,
                )
            )

        # ========================================================
        # DIRECTIONAL COMPRESSION
        # ========================================================

        directional_compression = 1.0 - min(
            1.0,
            (
                abs(sentiment_score)
                + abs(technical_score)
                + abs(fundamental_directional)
                + abs(news_directional)
            )
            / 4.0,
        )

        # ========================================================
        # RANGE CONDITIONS
        # ========================================================

        range_condition = (
            (1.0 - trend_strength) * 0.50
            + directional_compression * 0.30
            + stability * 0.20
        )

        # ========================================================
        # VOLATILITY ADJUSTMENT
        # ========================================================

        volatility_stability = 1.0 - min(1.0, volatility_score)

        # ========================================================
        # MOMENTUM DAMPENING
        # ========================================================

        momentum_neutrality = 1.0 - min(1.0, abs(momentum))

        # ========================================================
        # DIVERGENCE BONUS
        # ========================================================

        divergence_bonus = min(
            1.0,
            abs(divergence),
        )

        # ========================================================
        # RISK NORMALIZATION
        # ========================================================

        risk_normalization = 1.0 - min(1.0, risk_pressure)

        # ========================================================
        # COMPOSITE SIDEWAYS SCORE
        # ========================================================

        score = (
            (range_condition * 0.35)
            + (volatility_stability * 0.20)
            + (momentum_neutrality * 0.20)
            + (divergence_bonus * 0.10)
            + (risk_normalization * 0.15)
        )

        # ========================================================
        # REGIME ADJUSTMENTS
        # ========================================================

        if technical_regime in [
            "neutral",
            "sideways",
            "range_bound",
        ]:
            score += 0.10

        if volatility_regime in [
            "low_volatility",
            "normal",
        ]:
            score += 0.05

        # ========================================================
        # STRONG TREND PENALTY
        # ========================================================

        if trend_strength > 0.75:
            score -= 0.20

        # ========================================================
        # EXTREME DIRECTIONAL PENALTY
        # ========================================================

        if abs(sentiment_score) > 0.75:
            score -= 0.10

        if abs(technical_score) > 0.75:
            score -= 0.15

        score += self._breadth_score_modifier(
            breadth_context,
        )

        score = self._clamp_01(score)

        # ========================================================
        # CONFIDENCE
        # ========================================================

        confidence = (sentiment_confidence * 0.40) + (technical_confidence * 0.60)

        confidence = self._clamp_01(
            confidence
            + self._breadth_confidence_modifier(
                breadth_context,
            )
        )

        # ========================================================
        # SIGNALS
        # ========================================================

        signals = [
            "range_bound_bias",
            "mean_reversion_candidate",
        ]

        if trend_strength < 0.30:
            signals.append("weak_trend_structure")

        if volatility_regime == "low_volatility":
            signals.append("compressed_volatility")

        if directional_compression > 0.70:
            signals.append("low_directional_conviction")

        signals = self._deduplicate(
            signals
            + self._breadth_signals(
                breadth_context,
            )
        )

        # ========================================================
        # RISKS
        # ========================================================

        risks = [
            "breakout_risk",
            "false_mean_reversion_signals",
        ]

        if volatility_score > 0.75:
            risks.append("volatility_expansion_risk")

        if abs(momentum) > 0.70:
            risks.append("trend_acceleration_risk")

        risks = self._deduplicate(
            risks
            + self._breadth_risks(
                breadth_context,
            )
        )

        # ========================================================
        # RECOMMENDATIONS
        # ========================================================

        recommendations = [
            "prefer_range_strategies",
            "avoid_aggressive_directional_exposure",
            "favor_mean_reversion_entries",
        ]

        if volatility_score > 0.70:
            recommendations.append("reduce_position_size")

        if trend_strength > 0.60:
            recommendations.append("prepare_for_breakout_transition")

        recommendations = self._deduplicate(
            recommendations
            + self._breadth_recommendations(
                breadth_context,
            )
        )

        # ========================================================
        # RESULT
        # ========================================================

        runtime_result = dict(
            directional_score=score,
            confidence=confidence,
            regime="sideways_strategy",
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features={
                # ================================================
                # FINAL SCORE
                # ================================================
                "sideways_score": score,
                # ================================================
                # CORE CONDITIONS
                # ================================================
                "directional_compression": directional_compression,
                "range_condition": range_condition,
                "volatility_stability": volatility_stability,
                "momentum_neutrality": momentum_neutrality,
                "risk_normalization": risk_normalization,
                # ================================================
                # SENTIMENT
                # ================================================
                "sentiment_score": sentiment_score,
                "stability": stability,
                "divergence": divergence,
                "divergence_data": divergence_data,
                "momentum": momentum,
                # ================================================
                # TECHNICAL
                # ================================================
                "technical_score": technical_score,
                "technical_regime": technical_regime,
                "trend_strength": trend_strength,
                "volatility_score": volatility_score,
                "volatility_regime": volatility_regime,
                # ================================================
                # BREADTH
                # ================================================
                "breadth_context": breadth_context.to_dict(),
                "breadth_confirmation_score": breadth_context.confirmation_score,
                "breadth_risk_pressure": breadth_context.risk_pressure,
                "breadth_score_modifier": self._breadth_score_modifier(
                    breadth_context,
                ),
                "breadth_confidence_modifier": self._breadth_confidence_modifier(
                    breadth_context,
                ),
                "breadth_risk_flags": list(
                    breadth_context.risk_flags(),
                ),
                # ================================================
                # FUNDAMENTAL + NEWS
                # ================================================
                "fundamental_directional": fundamental_directional,
                "news_directional": news_directional,
                # ================================================
                # RISK
                # ================================================
                "risk_pressure": risk_pressure,
            },
        )

        # ========================================================
        # OUTPUT
        # ========================================================

        return RuntimeNodeOutput.success_output(
            outputs=runtime_result,
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": (confidence),
                **({}),
            },
        )

    # ============================================================
    # BREADTH CONTEXT
    # ============================================================

    def _breadth_score_modifier(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> float:
        if not breadth_context.has_breadth_data:
            return 0.0

        if breadth_context.is_strong:
            return -0.06

        modifier = 0.0

        if abs(breadth_context.confirmation_score) <= 0.15:
            modifier += 0.06

        if breadth_context.is_weak:
            modifier += 0.05

        if breadth_context.participation_score <= -0.25:
            modifier += 0.03

        if breadth_context.leadership_score <= -0.25:
            modifier += 0.03

        if breadth_context.price_ad_divergence:
            modifier += 0.05

        return min(
            0.14,
            modifier,
        )

    def _breadth_confidence_modifier(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> float:
        if not breadth_context.has_breadth_data:
            return 0.0

        if breadth_context.is_strong:
            return -0.03

        if (
            breadth_context.is_weak
            or breadth_context.price_ad_divergence
            or abs(breadth_context.confirmation_score) <= 0.15
        ):
            return 0.04

        return 0.0

    def _breadth_signals(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        signals = [
            f"breadth:{breadth_context.breadth_regime}",
        ]

        if abs(breadth_context.confirmation_score) <= 0.15:
            signals.append(
                "mixed_breadth_structure",
            )

        if breadth_context.is_weak:
            signals.append(
                "narrow_or_weak_breadth_supports_sideways_case",
            )

        if breadth_context.price_ad_divergence:
            signals.append(
                "breadth_divergence_supports_sideways_case",
            )

        return signals

    def _breadth_risks(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        risks: list[str] = []

        if breadth_context.is_weak:
            risks.append(
                "breadth_uncertainty_risk",
            )

        if breadth_context.participation_score <= -0.25:
            risks.append(
                "participation_breakdown_risk",
            )

        return risks

    def _breadth_recommendations(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        recommendations: list[str] = []

        if (
            breadth_context.is_weak
            or breadth_context.price_ad_divergence
            or abs(breadth_context.confirmation_score) <= 0.15
        ):
            recommendations.append(
                "wait_for_breadth_resolution",
            )

        if breadth_context.is_strong:
            recommendations.append(
                "avoid_fading_strong_breadth_without_price_confirmation",
            )

        return recommendations

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
    # CLAMP
    # ============================================================

    def _clamp_01(
        self,
        value: float,
    ) -> float:

        return max(
            0.0,
            min(1.0, float(value)),
        )
