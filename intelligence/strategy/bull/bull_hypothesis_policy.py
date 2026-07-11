from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.policy_support import (
    breadth_context_from_evidence,
)
from intelligence.strategy.hypothesis.policy_support import clamp_01
from intelligence.strategy.hypothesis.policy_support import data_quality_flags
from intelligence.strategy.hypothesis.policy_support import deduplicate_values
from intelligence.strategy.hypothesis.policy_support import evidence_for_perspective
from intelligence.strategy.hypothesis.policy_support import evidence_reliability
from intelligence.strategy.hypothesis.policy_support import numeric_evidence_value
from intelligence.strategy.hypothesis.policy_support import string_evidence_value
from intelligence.strategy.hypothesis.breadth import BreadthMessageRule
from intelligence.strategy.hypothesis.breadth import breadth_messages
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.evidence import StrategyAssumption
from intelligence.strategy.hypothesis.evidence import StrategyEvidenceItem
from intelligence.strategy.hypothesis.evidence import StrategyInvalidationCondition
from intelligence.strategy.hypothesis.evidence import StrategyInvalidationOperator
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis


_BULL_BREADTH_SIGNAL_RULES = (
    BreadthMessageRule(
        lambda context: context.is_strong,
        "bullish_breadth_confirmation",
    ),
    BreadthMessageRule(
        lambda context: context.is_weak,
        "weak_breadth_not_confirming_bullish_setup",
    ),
)
_BULL_BREADTH_RISK_RULES = (
    BreadthMessageRule(
        lambda context: context.is_weak,
        "breadth_not_confirming_bullish_setup",
    ),
    BreadthMessageRule(
        lambda context: context.leadership_score <= -0.25,
        "narrow_leadership_risk",
    ),
    BreadthMessageRule(
        lambda context: context.price_ad_divergence,
        "price_ad_divergence_risk",
    ),
)
_BULL_BREADTH_RECOMMENDATION_RULES = (
    BreadthMessageRule(
        lambda context: context.is_weak,
        "wait_for_breadth_confirmation",
    ),
    BreadthMessageRule(
        lambda context: context.price_ad_divergence,
        "avoid_aggressive_long_exposure_until_divergence_resolves",
    ),
    BreadthMessageRule(
        lambda context: context.is_strong,
        "breadth_confirms_bullish_setup",
    ),
)


@dataclass(frozen=True, slots=True)
class BullHypothesisDecision:
    hypothesis: StrategyHypothesis
    signals: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    features: Mapping[str, object]

    def to_runtime_outputs(self) -> dict[str, object]:
        return {
            "directional_score": self.hypothesis.directional_bias,
            "confidence": self.hypothesis.confidence,
            "regime": "bull_strategy",
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "strategy_hypothesis": self.hypothesis.to_dict(),
            "features": dict(self.features),
        }


def build_bull_hypothesis(
    evidence_context: StrategyEvidenceContext,
) -> BullHypothesisDecision:
    evidence = evidence_context.evidence_by_id()

    sentiment_score = numeric_evidence_value(evidence, "sentiment.directional_score")
    sentiment_confidence = evidence_reliability(evidence, "sentiment.directional_score")
    bullish_sentiment = max(0.0, sentiment_score)
    momentum = numeric_evidence_value(evidence, "sentiment.momentum")
    stability = numeric_evidence_value(evidence, "sentiment.stability")
    divergence = numeric_evidence_value(evidence, "sentiment.divergence")

    technical_score = numeric_evidence_value(evidence, "technical.directional_score")
    technical_confidence = evidence_reliability(evidence, "technical.directional_score")
    technical_bullishness = max(0.0, technical_score)
    technical_regime = string_evidence_value(
        evidence, "technical.regime", default="neutral"
    )
    trend_strength = numeric_evidence_value(evidence, "technical.trend_strength")
    volatility_score = numeric_evidence_value(evidence, "technical.volatility_score")
    breadth_context = breadth_context_from_evidence(evidence)

    fundamental_bullishness = max(
        0.0,
        numeric_evidence_value(evidence, "fundamental.directional_score"),
    )
    news_bullishness = max(
        0.0, numeric_evidence_value(evidence, "news.directional_score")
    )
    risk_pressure = numeric_evidence_value(evidence, "risk.pressure")

    score = (
        (bullish_sentiment * 0.30)
        + (technical_bullishness * 0.35)
        + (fundamental_bullishness * 0.15)
        + (news_bullishness * 0.10)
        + (stability * 0.05)
        - (risk_pressure * 0.05)
    )

    if technical_regime in {"bullish", "strong_bullish"}:
        score += 0.10
    if momentum > 0:
        score += momentum * 0.05
    if divergence > 0:
        score += divergence * 0.05

    score += trend_strength * 0.05

    if volatility_score > 0.70:
        score -= volatility_score * 0.10

    breadth_score_modifier = _breadth_score_modifier(breadth_context)
    breadth_confidence_modifier = _breadth_confidence_modifier(breadth_context)
    score = clamp_01(score + breadth_score_modifier)

    confidence = clamp_01(
        (sentiment_confidence * 0.40)
        + (technical_confidence * 0.60)
        + breadth_confidence_modifier
    )

    signals = deduplicate_values(
        tuple(
            signal
            for signal, enabled in (
                ("bullish_sentiment", bullish_sentiment > 0.50),
                ("bullish_technical_structure", technical_bullishness > 0.50),
                ("positive_momentum", momentum > 0),
                (
                    "bullish_regime",
                    technical_regime in {"bullish", "strong_bullish"},
                ),
            )
            if enabled
        )
        + _breadth_signals(breadth_context)
    )

    risks = deduplicate_values(
        (
            "bull_trap_risk",
            "overextension_risk",
        )
        + (("high_volatility_breakdown_risk",) if volatility_score > 0.70 else ())
        + (("macro_risk_pressure",) if risk_pressure > 0.70 else ())
        + _breadth_risks(breadth_context)
    )

    recommendations = deduplicate_values(
        (
            "scale_into_strength",
            "avoid_chasing_extended_moves",
        )
        + (("reduce_position_size",) if volatility_score > 0.70 else ())
        + (("tighten_risk_controls",) if risk_pressure > 0.60 else ())
        + _breadth_recommendations(breadth_context)
    )

    supporting_evidence = evidence_for_perspective(
        evidence_context,
        StrategyPerspective.BULL,
        support=True,
    )
    contradicting_evidence = evidence_for_perspective(
        evidence_context,
        StrategyPerspective.BULL,
        support=False,
    )
    quality_flags = data_quality_flags(evidence_context)
    assumptions = _bull_assumptions(score, confidence, supporting_evidence)
    invalidations = _bull_invalidations(
        sentiment_score=sentiment_score,
        technical_score=technical_score,
        volatility_score=volatility_score,
        risk_pressure=risk_pressure,
    )
    thesis = _bull_thesis(score, confidence, invalidations)

    hypothesis = StrategyHypothesis(
        perspective=StrategyPerspective.BULL,
        thesis=thesis,
        directional_bias=score,
        hypothesis_strength=score,
        confidence=confidence,
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
        key_assumptions=assumptions,
        invalidation_conditions=invalidations,
        risks=risks,
        recommendations=recommendations,
        data_quality_flags=quality_flags,
        evidence_fingerprint=evidence_context.evidence_fingerprint(),
    )

    features: dict[str, object] = {
        "bull_score": score,
        "sentiment_score": sentiment_score,
        "bullish_sentiment": bullish_sentiment,
        "momentum": momentum,
        "stability": stability,
        "divergence": divergence,
        "divergence_data": {"avg_divergence": divergence},
        "technical_score": technical_score,
        "technical_bullishness": technical_bullishness,
        "technical_regime": technical_regime,
        "trend_strength": trend_strength,
        "volatility_score": volatility_score,
        "breadth_context": breadth_context.to_dict(),
        "breadth_confirmation_score": breadth_context.confirmation_score,
        "breadth_risk_pressure": breadth_context.risk_pressure,
        "breadth_score_modifier": breadth_score_modifier,
        "breadth_confidence_modifier": breadth_confidence_modifier,
        "breadth_risk_flags": list(breadth_context.risk_flags()),
        "fundamental_bullishness": fundamental_bullishness,
        "news_bullishness": news_bullishness,
        "risk_pressure": risk_pressure,
        "evidence_fingerprint": hypothesis.evidence_fingerprint,
        "hypothesis_strength": hypothesis.hypothesis_strength,
        "supporting_evidence_count": len(hypothesis.supporting_evidence),
        "contradicting_evidence_count": len(hypothesis.contradicting_evidence),
        "invalidated": hypothesis.invalidated,
    }

    return BullHypothesisDecision(
        hypothesis=hypothesis,
        signals=signals,
        risks=risks,
        recommendations=recommendations,
        features=features,
    )


def _bull_assumptions(
    score: float,
    confidence: float,
    supporting_evidence: tuple[StrategyEvidenceItem, ...],
) -> tuple[StrategyAssumption, ...]:
    evidence_ids = tuple(item.evidence_id for item in supporting_evidence[:5])
    return (
        StrategyAssumption(
            assumption_id="bull.continuation_requires_positive_evidence",
            perspective=StrategyPerspective.BULL,
            description="Bullish posture requires positive evidence to remain persistent.",
            confidence=clamp_01(confidence),
            evidence_ids=evidence_ids,
        ),
        StrategyAssumption(
            assumption_id="bull.strength_requires_follow_through",
            perspective=StrategyPerspective.BULL,
            description="Bullish strength assumes trend and sentiment follow-through do not fail.",
            confidence=clamp_01(score),
            evidence_ids=evidence_ids,
        ),
    )


def _bull_invalidations(
    *,
    sentiment_score: float,
    technical_score: float,
    volatility_score: float,
    risk_pressure: float,
) -> tuple[StrategyInvalidationCondition, ...]:
    return (
        StrategyInvalidationCondition(
            condition_id="bull.sentiment_breakdown",
            perspective=StrategyPerspective.BULL,
            description="Bull case is invalidated if sentiment turns materially bearish.",
            observed_value=sentiment_score,
            operator=StrategyInvalidationOperator.LESS_THAN,
            threshold=-0.25,
            evidence_id="sentiment.directional_score",
        ),
        StrategyInvalidationCondition(
            condition_id="bull.technical_breakdown",
            perspective=StrategyPerspective.BULL,
            description="Bull case is invalidated if technical structure turns bearish.",
            observed_value=technical_score,
            operator=StrategyInvalidationOperator.LESS_THAN,
            threshold=-0.25,
            evidence_id="technical.directional_score",
        ),
        StrategyInvalidationCondition(
            condition_id="bull.volatility_shock",
            perspective=StrategyPerspective.BULL,
            description="Bull case is invalidated by extreme volatility pressure.",
            observed_value=volatility_score,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.85,
            evidence_id="technical.volatility_score",
        ),
        StrategyInvalidationCondition(
            condition_id="bull.risk_pressure_spike",
            perspective=StrategyPerspective.BULL,
            description="Bull case is invalidated by extreme aggregate risk pressure.",
            observed_value=risk_pressure,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.80,
            evidence_id="risk.pressure",
        ),
    )


def _bull_thesis(
    score: float,
    confidence: float,
    invalidations: tuple[StrategyInvalidationCondition, ...],
) -> str:
    if any(condition.is_invalidated() for condition in invalidations):
        return "Bull hypothesis is currently invalidated by hard risk conditions."
    if score >= 0.65 and confidence >= 0.60:
        return "Bull hypothesis is supported by aligned positive evidence."
    if score >= 0.35:
        return "Bull hypothesis is plausible but requires further confirmation."
    return "Bull hypothesis is weak because positive evidence is limited."


def _breadth_score_modifier(
    breadth_context: TechnicalBreadthContext,
) -> float:
    if not breadth_context.has_breadth_data:
        return 0.0
    if breadth_context.is_strong:
        return 0.08

    modifier = min(0.0, breadth_context.confirmation_score) * 0.08
    if breadth_context.is_weak:
        modifier -= 0.08
    if breadth_context.price_ad_divergence:
        modifier -= 0.04
    if breadth_context.participation_score <= -0.25:
        modifier -= 0.03
    if breadth_context.leadership_score <= -0.25:
        modifier -= 0.03
    return max(-0.18, modifier)


def _breadth_confidence_modifier(
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
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    return breadth_messages(
        breadth_context,
        _BULL_BREADTH_SIGNAL_RULES,
        include_regime=True,
    )


def _breadth_risks(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    return breadth_messages(breadth_context, _BULL_BREADTH_RISK_RULES)


def _breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    return breadth_messages(breadth_context, _BULL_BREADTH_RECOMMENDATION_RULES)
