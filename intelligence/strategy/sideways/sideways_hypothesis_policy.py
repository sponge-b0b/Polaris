from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.strategy.hypothesis.breadth import (
    BreadthMessageRule,
    breadth_messages,
)
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.evidence import (
    StrategyAssumption,
    StrategyEvidenceItem,
    StrategyInvalidationCondition,
    StrategyInvalidationOperator,
)
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.hypothesis.policy_support import (
    breadth_context_from_evidence,
    clamp_01,
    data_quality_flags,
    deduplicate_values,
    evidence_for_perspective,
    evidence_reliability,
    numeric_evidence_value,
    string_evidence_value,
)

_SIDEWAYS_BREADTH_SIGNAL_RULES = (
    BreadthMessageRule(
        lambda context: abs(context.confirmation_score) <= 0.15,
        "mixed_breadth_structure",
    ),
    BreadthMessageRule(
        lambda context: context.is_weak,
        "narrow_or_weak_breadth_supports_sideways_case",
    ),
    BreadthMessageRule(
        lambda context: context.price_ad_divergence,
        "breadth_divergence_supports_sideways_case",
    ),
)
_SIDEWAYS_BREADTH_RISK_RULES = (
    BreadthMessageRule(
        lambda context: context.is_weak,
        "breadth_uncertainty_risk",
    ),
    BreadthMessageRule(
        lambda context: context.participation_score <= -0.25,
        "participation_breakdown_risk",
    ),
)
_SIDEWAYS_BREADTH_RECOMMENDATION_RULES = (
    BreadthMessageRule(
        lambda context: (
            context.is_weak
            or context.price_ad_divergence
            or abs(context.confirmation_score) <= 0.15
        ),
        "wait_for_breadth_resolution",
    ),
    BreadthMessageRule(
        lambda context: context.is_strong,
        "avoid_fading_strong_breadth_without_price_confirmation",
    ),
)


@dataclass(frozen=True, slots=True)
class SidewaysHypothesisDecision:
    hypothesis: StrategyHypothesis
    signals: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    features: Mapping[str, object]

    def to_runtime_outputs(self) -> dict[str, object]:
        return {
            "directional_score": self.hypothesis.directional_bias,
            "confidence": self.hypothesis.confidence,
            "regime": "sideways_strategy",
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "strategy_hypothesis": self.hypothesis.to_dict(),
            "features": dict(self.features),
        }


def build_sideways_hypothesis(
    evidence_context: StrategyEvidenceContext,
) -> SidewaysHypothesisDecision:
    evidence = evidence_context.evidence_by_id()

    sentiment_score = numeric_evidence_value(evidence, "sentiment.directional_score")
    sentiment_confidence = evidence_reliability(evidence, "sentiment.directional_score")
    stability = numeric_evidence_value(evidence, "sentiment.stability", default=0.5)
    divergence = numeric_evidence_value(evidence, "sentiment.divergence")
    momentum = numeric_evidence_value(evidence, "sentiment.momentum")

    technical_score = numeric_evidence_value(evidence, "technical.directional_score")
    technical_confidence = evidence_reliability(evidence, "technical.directional_score")
    technical_regime = string_evidence_value(
        evidence, "technical.regime", default="neutral"
    )
    trend_strength = numeric_evidence_value(evidence, "technical.trend_strength")
    volatility_score = numeric_evidence_value(evidence, "technical.volatility_score")
    volatility_regime = _volatility_regime(volatility_score)
    breadth_context = breadth_context_from_evidence(evidence)

    fundamental_directional = numeric_evidence_value(
        evidence,
        "fundamental.directional_score",
    )
    news_directional = numeric_evidence_value(evidence, "news.directional_score")
    risk_pressure = numeric_evidence_value(evidence, "risk.pressure")

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

    range_condition = (
        (1.0 - trend_strength) * 0.50
        + directional_compression * 0.30
        + stability * 0.20
    )
    volatility_stability = 1.0 - min(1.0, volatility_score)
    momentum_neutrality = 1.0 - min(1.0, abs(momentum))
    divergence_bonus = min(1.0, abs(divergence))
    risk_normalization = 1.0 - min(1.0, risk_pressure)

    score = (
        (range_condition * 0.35)
        + (volatility_stability * 0.20)
        + (momentum_neutrality * 0.20)
        + (divergence_bonus * 0.10)
        + (risk_normalization * 0.15)
    )

    if technical_regime in {"neutral", "sideways", "range_bound"}:
        score += 0.10

    if volatility_regime in {"low_volatility", "normal"}:
        score += 0.05

    if trend_strength > 0.75:
        score -= 0.20

    if abs(sentiment_score) > 0.75:
        score -= 0.10

    if abs(technical_score) > 0.75:
        score -= 0.15

    breadth_score_modifier = _breadth_score_modifier(breadth_context)
    breadth_confidence_modifier = _breadth_confidence_modifier(breadth_context)
    score = clamp_01(score + breadth_score_modifier)

    confidence = clamp_01(
        (sentiment_confidence * 0.40)
        + (technical_confidence * 0.60)
        + breadth_confidence_modifier
    )

    signals = deduplicate_values(
        (
            "range_bound_bias",
            "mean_reversion_candidate",
        )
        + (("weak_trend_structure",) if trend_strength < 0.30 else ())
        + (("compressed_volatility",) if volatility_regime == "low_volatility" else ())
        + (("low_directional_conviction",) if directional_compression > 0.70 else ())
        + _breadth_signals(breadth_context)
    )

    risks = deduplicate_values(
        (
            "breakout_risk",
            "false_mean_reversion_signals",
        )
        + (("volatility_expansion_risk",) if volatility_score > 0.75 else ())
        + (("trend_acceleration_risk",) if abs(momentum) > 0.70 else ())
        + _breadth_risks(breadth_context)
    )

    recommendations = deduplicate_values(
        (
            "prefer_range_strategies",
            "avoid_aggressive_directional_exposure",
            "favor_mean_reversion_entries",
        )
        + (("reduce_position_size",) if volatility_score > 0.70 else ())
        + (("prepare_for_breakout_transition",) if trend_strength > 0.60 else ())
        + _breadth_recommendations(breadth_context)
    )

    supporting_evidence = evidence_for_perspective(
        evidence_context,
        StrategyPerspective.SIDEWAYS,
        support=True,
    )
    contradicting_evidence = _sideways_contradicting_evidence(evidence_context)
    quality_flags = data_quality_flags(evidence_context)
    assumptions = _sideways_assumptions(score, confidence, supporting_evidence)
    invalidations = _sideways_invalidations(
        trend_strength=trend_strength,
        volatility_score=volatility_score,
        sentiment_score=sentiment_score,
        technical_score=technical_score,
    )
    thesis = _sideways_thesis(score, confidence, invalidations)

    hypothesis = StrategyHypothesis(
        perspective=StrategyPerspective.SIDEWAYS,
        thesis=thesis,
        directional_bias=0.0,
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
        "sideways_score": score,
        "directional_compression": directional_compression,
        "range_condition": range_condition,
        "volatility_stability": volatility_stability,
        "momentum_neutrality": momentum_neutrality,
        "risk_normalization": risk_normalization,
        "sentiment_score": sentiment_score,
        "stability": stability,
        "divergence": divergence,
        "divergence_data": {"avg_divergence": divergence},
        "momentum": momentum,
        "technical_score": technical_score,
        "technical_regime": technical_regime,
        "trend_strength": trend_strength,
        "volatility_score": volatility_score,
        "volatility_regime": volatility_regime,
        "breadth_context": breadth_context.to_dict(),
        "breadth_confirmation_score": breadth_context.confirmation_score,
        "breadth_risk_pressure": breadth_context.risk_pressure,
        "breadth_score_modifier": breadth_score_modifier,
        "breadth_confidence_modifier": breadth_confidence_modifier,
        "breadth_risk_flags": list(breadth_context.risk_flags()),
        "fundamental_directional": fundamental_directional,
        "news_directional": news_directional,
        "risk_pressure": risk_pressure,
        "evidence_fingerprint": hypothesis.evidence_fingerprint,
        "hypothesis_strength": hypothesis.hypothesis_strength,
        "supporting_evidence_count": len(hypothesis.supporting_evidence),
        "contradicting_evidence_count": len(hypothesis.contradicting_evidence),
        "invalidated": hypothesis.invalidated,
    }

    return SidewaysHypothesisDecision(
        hypothesis=hypothesis,
        signals=signals,
        risks=risks,
        recommendations=recommendations,
        features=features,
    )


def _sideways_contradicting_evidence(
    evidence_context: StrategyEvidenceContext,
) -> tuple[StrategyEvidenceItem, ...]:
    return tuple(
        item
        for item in evidence_context.all_evidence
        if _is_directional_breakout_evidence(item)
    )


def _is_directional_breakout_evidence(item: StrategyEvidenceItem) -> bool:
    if isinstance(item.observed_value, bool) or not isinstance(
        item.observed_value,
        (int, float),
    ):
        return False
    numeric = abs(float(item.observed_value))
    if item.evidence_id in {
        "sentiment.directional_score",
        "technical.directional_score",
        "fundamental.directional_score",
        "news.directional_score",
    }:
        return numeric >= 0.50
    if item.evidence_id == "technical.trend_strength":
        return numeric >= 0.70
    if item.evidence_id == "technical.volatility_score":
        return numeric >= 0.75
    return False


def _sideways_assumptions(
    score: float,
    confidence: float,
    supporting_evidence: tuple[StrategyEvidenceItem, ...],
) -> tuple[StrategyAssumption, ...]:
    evidence_ids = tuple(item.evidence_id for item in supporting_evidence[:5])
    return (
        StrategyAssumption(
            assumption_id="sideways.range_requires_contained_directionality",
            perspective=StrategyPerspective.SIDEWAYS,
            description=(
                "Sideways posture requires directional evidence to remain contained."
            ),
            confidence=clamp_01(confidence),
            evidence_ids=evidence_ids,
        ),
        StrategyAssumption(
            assumption_id="sideways.mean_reversion_requires_stable_volatility",
            perspective=StrategyPerspective.SIDEWAYS,
            description=(
                "Sideways strength assumes volatility does not expand into breakout "
                "conditions."
            ),
            confidence=clamp_01(score),
            evidence_ids=evidence_ids,
        ),
    )


def _sideways_invalidations(
    *,
    trend_strength: float,
    volatility_score: float,
    sentiment_score: float,
    technical_score: float,
) -> tuple[StrategyInvalidationCondition, ...]:
    return (
        StrategyInvalidationCondition(
            condition_id="sideways.trend_breakout",
            perspective=StrategyPerspective.SIDEWAYS,
            description=(
                "Sideways case is invalidated by strong trend breakout pressure."
            ),
            observed_value=trend_strength,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.75,
            evidence_id="technical.trend_strength",
        ),
        StrategyInvalidationCondition(
            condition_id="sideways.volatility_expansion",
            perspective=StrategyPerspective.SIDEWAYS,
            description="Sideways case is invalidated by volatility expansion.",
            observed_value=volatility_score,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.75,
            evidence_id="technical.volatility_score",
        ),
        StrategyInvalidationCondition(
            condition_id="sideways.sentiment_directional_breakout",
            perspective=StrategyPerspective.SIDEWAYS,
            description=(
                "Sideways case is invalidated by extreme sentiment directionality."
            ),
            observed_value=abs(sentiment_score),
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.75,
            evidence_id="sentiment.directional_score",
        ),
        StrategyInvalidationCondition(
            condition_id="sideways.technical_directional_breakout",
            perspective=StrategyPerspective.SIDEWAYS,
            description=(
                "Sideways case is invalidated by extreme technical directionality."
            ),
            observed_value=abs(technical_score),
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.75,
            evidence_id="technical.directional_score",
        ),
    )


def _sideways_thesis(
    score: float,
    confidence: float,
    invalidations: tuple[StrategyInvalidationCondition, ...],
) -> str:
    if any(condition.is_invalidated() for condition in invalidations):
        return "Sideways hypothesis is currently invalidated by breakout conditions."
    if score >= 0.65 and confidence >= 0.60:
        return "Sideways hypothesis is supported by contained directional evidence."
    if score >= 0.35:
        return "Sideways hypothesis is plausible but requires range confirmation."
    return "Sideways hypothesis is weak because range evidence is limited."


def _volatility_regime(volatility_score: float) -> str:
    if volatility_score <= 0.25:
        return "low_volatility"
    if volatility_score >= 0.75:
        return "high_volatility"
    return "normal"


def _breadth_score_modifier(
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
    return min(0.14, modifier)


def _breadth_confidence_modifier(
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
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    return breadth_messages(
        breadth_context,
        _SIDEWAYS_BREADTH_SIGNAL_RULES,
        include_regime=True,
    )


def _breadth_risks(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    return breadth_messages(breadth_context, _SIDEWAYS_BREADTH_RISK_RULES)


def _breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    return breadth_messages(breadth_context, _SIDEWAYS_BREADTH_RECOMMENDATION_RULES)
