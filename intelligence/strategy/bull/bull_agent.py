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


class BullAgent(RuntimeNode):
    """
    Polaris Bull Agent

    ============================================================
    PURPOSE
    ============================================================
    - synthesize bullish trade conditions
    - evaluate upside opportunity quality
    - combine multi-domain intelligence
    - produce normalized bull strategy score

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

    node_name = "bull_agent"
    node_type = "bull_strategy"

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
            raise ValueError("BullAgent requires 'sentiment_agent' in node_outputs.")

        if technical_output is None:
            raise ValueError("BullAgent requires 'technical_agent' in node_outputs.")

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

        bullish_sentiment = max(
            0.0,
            sentiment_score,
        )

        momentum = float(
            sentiment_features.get(
                "momentum",
                0.0,
            )
        )

        stability = float(
            sentiment_features.get(
                "stability",
                0.0,
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

        technical_bullishness = max(
            0.0,
            technical_score,
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

        fundamental_bullishness = 0.0

        if fundamental_output is not None:
            fundamental_result = fundamental_output.get("outputs", {})

            fundamental_score = float(fundamental_result.get("directional_score", 0.0))

            fundamental_bullishness = max(
                0.0,
                fundamental_score,
            )

        # ========================================================
        # NEWS
        # ========================================================

        news_bullishness = 0.0

        if news_output is not None:
            news_result = news_output.get("outputs", {})

            news_score = float(news_result.get("directional_score", 0.0))

            news_bullishness = max(
                0.0,
                news_score,
            )

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
        # CORE BULL SCORE
        # ========================================================

        score = (
            (bullish_sentiment * 0.30)
            + (technical_bullishness * 0.35)
            + (fundamental_bullishness * 0.15)
            + (news_bullishness * 0.10)
            + (stability * 0.05)
            - (risk_pressure * 0.05)
        )

        # ========================================================
        # REGIME CONFIRMATION
        # ========================================================

        if technical_regime in [
            "bullish",
            "strong_bullish",
        ]:
            score += 0.10

        # ========================================================
        # MOMENTUM CONFIRMATION
        # ========================================================

        if momentum > 0:
            score += momentum * 0.05

        # ========================================================
        # POSITIVE DIVERGENCE BONUS
        # ========================================================

        if divergence > 0:
            score += divergence * 0.05

        # ========================================================
        # TREND CONFIRMATION
        # ========================================================

        score += trend_strength * 0.05

        # ========================================================
        # VOLATILITY PENALTY
        # ========================================================

        if volatility_score > 0.70:
            score -= volatility_score * 0.10

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

        if bullish_sentiment > 0.50:
            signals.append("bullish_sentiment")

        if technical_bullishness > 0.50:
            signals.append("bullish_technical_structure")

        if momentum > 0:
            signals.append("positive_momentum")

        if technical_regime in [
            "bullish",
            "strong_bullish",
        ]:
            signals.append("bullish_regime")

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
            "bull_trap_risk",
            "overextension_risk",
        ]

        if volatility_score > 0.70:
            risks.append("high_volatility_breakdown_risk")

        if risk_pressure > 0.70:
            risks.append("macro_risk_pressure")

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
            "scale_into_strength",
            "avoid_chasing_extended_moves",
        ]

        if volatility_score > 0.70:
            recommendations.append("reduce_position_size")

        if risk_pressure > 0.60:
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
            directional_score=score,
            confidence=confidence,
            regime="bull_strategy",
            signals=signals,
            risks=risks,
            recommendations=recommendations,
            features={
                # ================================================
                # FINAL SCORE
                # ================================================
                "bull_score": score,
                # ================================================
                # SENTIMENT
                # ================================================
                "sentiment_score": sentiment_score,
                "bullish_sentiment": bullish_sentiment,
                "momentum": momentum,
                "stability": stability,
                "divergence": divergence,
                "divergence_data": divergence_data,
                # ================================================
                # TECHNICAL
                # ================================================
                "technical_score": technical_score,
                "technical_bullishness": technical_bullishness,
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
                "fundamental_bullishness": fundamental_bullishness,
                "news_bullishness": news_bullishness,
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
            return 0.08

        modifier = (
            min(
                0.0,
                breadth_context.confirmation_score,
            )
            * 0.08
        )

        if breadth_context.is_weak:
            modifier -= 0.08

        if breadth_context.price_ad_divergence:
            modifier -= 0.04

        if breadth_context.participation_score <= -0.25:
            modifier -= 0.03

        if breadth_context.leadership_score <= -0.25:
            modifier -= 0.03

        return max(
            -0.18,
            modifier,
        )

    def _breadth_confidence_modifier(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> float:
        if not breadth_context.has_breadth_data:
            return 0.0

        if breadth_context.is_strong:
            return 0.05

        if breadth_context.is_weak:
            return -0.08

        return breadth_context.confirmation_score * 0.03

    def _breadth_signals(
        self,
        breadth_context: TechnicalBreadthContext,
    ) -> list[str]:
        if not breadth_context.has_breadth_data:
            return []

        signals = [
            f"breadth:{breadth_context.breadth_regime}",
        ]

        if breadth_context.is_strong:
            signals.append(
                "bullish_breadth_confirmation",
            )

        if breadth_context.is_weak:
            signals.append(
                "weak_breadth_not_confirming_bullish_setup",
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
                "breadth_not_confirming_bullish_setup",
            )

        if breadth_context.leadership_score <= -0.25:
            risks.append(
                "narrow_leadership_risk",
            )

        if breadth_context.price_ad_divergence:
            risks.append(
                "price_ad_divergence_risk",
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
                "wait_for_breadth_confirmation",
            )

        if breadth_context.price_ad_divergence:
            recommendations.append(
                "avoid_aggressive_long_exposure_until_divergence_resolves",
            )

        if breadth_context.is_strong:
            recommendations.append(
                "breadth_confirms_bullish_setup",
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
