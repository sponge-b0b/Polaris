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


class BearAgent(RuntimeNode):
    """
    Polaris Bear Agent

    ============================================================
    PURPOSE
    ============================================================
    - synthesize bearish trade conditions
    - evaluate downside opportunity quality
    - combine multi-domain intelligence
    - produce normalized bear strategy score

    ============================================================
    REQUIRED INPUTS
    ============================================================
    context.node_outputs["sentiment_agent"]
    context.node_outputs["technical_agent"]

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
    - no execution logic
    - no portfolio mutation
    """

    node_name = "bear_agent"
    node_type = "bear_strategy"

    # ============================================================
    # EXECUTE
    # ============================================================

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:

        node_outputs = context.node_outputs

        # ========================================================
        # REQUIRED AGENTS
        # ========================================================

        sentiment_output = node_outputs.get("sentiment_agent")

        technical_output = node_outputs.get("technical_agent")

        if sentiment_output is None:
            raise ValueError("BearAgent requires 'sentiment_agent' in node_outputs.")

        if technical_output is None:
            raise ValueError("BearAgent requires 'technical_agent' in node_outputs.")

        # ========================================================
        # OPTIONAL AGENTS
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

        bearish_sentiment = abs(min(0.0, sentiment_score))

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

        regime = technical_features.get(
            "regime",
            {},
        )

        trend = technical_features.get(
            "trend",
            {},
        )

        volatility = technical_features.get(
            "volatility",
            {},
        )

        technical_bearishness = abs(min(0.0, technical_score))

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

        technical_regime = str(
            regime.get(
                "regime",
                "neutral",
            )
        )

        breadth_context = extract_technical_breadth_context(
            technical_output,
        )

        # ========================================================
        # FUNDAMENTAL
        # ========================================================

        fundamental_bearishness = 0.0

        if fundamental_output is not None:
            fundamental_result = fundamental_output.get("outputs", {})

            fundamental_score = float(fundamental_result.get("directional_score", 0.0))

            fundamental_bearishness = abs(min(0.0, fundamental_score))

        # ========================================================
        # NEWS
        # ========================================================

        news_bearishness = 0.0

        if news_output is not None:
            news_result = news_output.get("outputs", {})

            news_score = float(news_result.get("directional_score", 0.0))

            news_bearishness = abs(min(0.0, news_score))

        # ========================================================
        # RISK CONTEXT
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
        # CORE BEAR SCORE
        # ========================================================

        score = (
            (bearish_sentiment * 0.30)
            + (technical_bearishness * 0.35)
            + (fundamental_bearishness * 0.15)
            + (news_bearishness * 0.10)
            + (risk_pressure * 0.10)
        )

        # ========================================================
        # TECHNICAL CONFIRMATION
        # ========================================================

        if technical_regime in [
            "bearish",
            "strong_bearish",
        ]:
            score += 0.10

        # ========================================================
        # VOLATILITY EXPANSION
        # ========================================================

        score += volatility_score * 0.05

        # ========================================================
        # DIVERGENCE BONUS
        # ========================================================

        if divergence < 0:
            score += abs(divergence) * 0.10

        # ========================================================
        # MOMENTUM CONFIRMATION
        # ========================================================

        if momentum < 0:
            score += abs(momentum) * 0.05

        # ========================================================
        # TREND CONFIRMATION
        # ========================================================

        score += trend_strength * 0.05

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

        signals = []

        if bearish_sentiment > 0.50:
            signals.append("bearish_sentiment")

        if technical_bearishness > 0.50:
            signals.append("bearish_technical_structure")

        if risk_pressure > 0.50:
            signals.append("elevated_risk_environment")

        if volatility_score > 0.60:
            signals.append("volatility_expansion")

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
            "short_squeeze_risk",
            "macro_reversal_risk",
        ]

        if technical_regime == "bullish":
            risks.append("counter_trend_short_risk")

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
            "prefer downside confirmation",
            "avoid illiquid shorts",
        ]

        if volatility_score > 0.70:
            recommendations.append("reduce_position_size")

        if risk_pressure > 0.70:
            recommendations.append("tighten_risk_controls")

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
            directional_score=-score,
            confidence=confidence,
            regime="bear_strategy",
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features={
                # ================================================
                # FINAL SCORE
                # ================================================
                "bear_score": score,
                # ================================================
                # SENTIMENT
                # ================================================
                "sentiment_score": sentiment_score,
                "bearish_sentiment": bearish_sentiment,
                "momentum": momentum,
                "divergence": divergence,
                "divergence_data": divergence_data,
                # ================================================
                # TECHNICAL
                # ================================================
                "technical_score": technical_score,
                "technical_bearishness": technical_bearishness,
                "technical_regime": technical_regime,
                "trend_strength": trend_strength,
                "volatility_score": volatility_score,
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
                "fundamental_bearishness": fundamental_bearishness,
                "news_bearishness": news_bearishness,
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
            return -0.10

        modifier = (
            max(
                0.0,
                -breadth_context.confirmation_score,
            )
            * 0.08
        )

        if breadth_context.is_weak:
            modifier += 0.08

        if breadth_context.price_ad_divergence:
            modifier += 0.04

        if breadth_context.participation_score <= -0.25:
            modifier += 0.03

        if breadth_context.leadership_score <= -0.25:
            modifier += 0.03

        return min(
            0.18,
            modifier,
        )

    def _breadth_confidence_modifier(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> float:
        if not breadth_context.has_breadth_data:
            return 0.0

        if breadth_context.is_strong:
            return -0.06

        if breadth_context.is_weak:
            return 0.06

        return (
            max(
                0.0,
                -breadth_context.confirmation_score,
            )
            * 0.03
        )

    def _breadth_signals(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        signals = [
            f"breadth:{breadth_context.breadth_regime}",
        ]

        if breadth_context.is_weak:
            signals.append(
                "bearish_breadth_confirmation",
            )

        if breadth_context.price_ad_divergence:
            signals.append(
                "breadth_divergence_supports_bear_case",
            )

        return signals

    def _breadth_risks(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        risks: list[str] = []

        if breadth_context.is_strong:
            risks.append(
                "strong_breadth_countertrend_risk",
            )

        return risks

    def _breadth_recommendations(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        recommendations: list[str] = []

        if breadth_context.is_weak:
            recommendations.append(
                "breadth_confirms_defensive_bias",
            )

        if breadth_context.is_strong:
            recommendations.append(
                "reduce_bearish_conviction_until_breadth_weakens",
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
