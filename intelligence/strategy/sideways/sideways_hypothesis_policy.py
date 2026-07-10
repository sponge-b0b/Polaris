from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.context import StrategyEvidenceInputStatus
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.evidence import StrategyAssumption
from intelligence.strategy.hypothesis.evidence import StrategyEvidenceItem
from intelligence.strategy.hypothesis.evidence import StrategyInvalidationCondition
from intelligence.strategy.hypothesis.evidence import StrategyInvalidationOperator
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis


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

    sentiment_score = _numeric_value(evidence, "sentiment.directional_score")
    sentiment_confidence = _reliability(evidence, "sentiment.directional_score")
    stability = _numeric_value(evidence, "sentiment.stability", default=0.5)
    divergence = _numeric_value(evidence, "sentiment.divergence")
    momentum = _numeric_value(evidence, "sentiment.momentum")

    technical_score = _numeric_value(evidence, "technical.directional_score")
    technical_confidence = _reliability(evidence, "technical.directional_score")
    technical_regime = _string_value(evidence, "technical.regime", default="neutral")
    trend_strength = _numeric_value(evidence, "technical.trend_strength")
    volatility_score = _numeric_value(evidence, "technical.volatility_score")
    volatility_regime = _volatility_regime(volatility_score)
    breadth_context = _breadth_context_from_evidence(evidence)

    fundamental_directional = _numeric_value(
        evidence,
        "fundamental.directional_score",
    )
    news_directional = _numeric_value(evidence, "news.directional_score")
    risk_pressure = _numeric_value(evidence, "risk.pressure")

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
    score = _clamp_01(score + breadth_score_modifier)

    confidence = _clamp_01(
        (sentiment_confidence * 0.40)
        + (technical_confidence * 0.60)
        + breadth_confidence_modifier
    )

    signals = _deduplicate(
        (
            "range_bound_bias",
            "mean_reversion_candidate",
        )
        + (("weak_trend_structure",) if trend_strength < 0.30 else ())
        + (("compressed_volatility",) if volatility_regime == "low_volatility" else ())
        + (("low_directional_conviction",) if directional_compression > 0.70 else ())
        + _breadth_signals(breadth_context)
    )

    risks = _deduplicate(
        (
            "breakout_risk",
            "false_mean_reversion_signals",
        )
        + (("volatility_expansion_risk",) if volatility_score > 0.75 else ())
        + (("trend_acceleration_risk",) if abs(momentum) > 0.70 else ())
        + _breadth_risks(breadth_context)
    )

    recommendations = _deduplicate(
        (
            "prefer_range_strategies",
            "avoid_aggressive_directional_exposure",
            "favor_mean_reversion_entries",
        )
        + (("reduce_position_size",) if volatility_score > 0.70 else ())
        + (("prepare_for_breakout_transition",) if trend_strength > 0.60 else ())
        + _breadth_recommendations(breadth_context)
    )

    supporting_evidence = _evidence_for_perspective(
        evidence_context,
        support=True,
    )
    contradicting_evidence = _sideways_contradicting_evidence(evidence_context)
    data_quality_flags = _data_quality_flags(evidence_context)
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
        data_quality_flags=data_quality_flags,
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


def _evidence_for_perspective(
    evidence_context: StrategyEvidenceContext,
    *,
    support: bool,
) -> tuple[StrategyEvidenceItem, ...]:
    perspective = StrategyPerspective.SIDEWAYS
    return tuple(
        item
        for item in evidence_context.all_evidence
        if perspective in (item.supports if support else item.contradicts)
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


def _data_quality_flags(
    evidence_context: StrategyEvidenceContext,
) -> tuple[str, ...]:
    flags = [
        f"{quality.input_name}:{quality.status.value}"
        for quality in evidence_context.input_quality
        if quality.status is not StrategyEvidenceInputStatus.AVAILABLE
    ]
    return tuple(flags)


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
            description="Sideways posture requires directional evidence to remain contained.",
            confidence=_clamp_01(confidence),
            evidence_ids=evidence_ids,
        ),
        StrategyAssumption(
            assumption_id="sideways.mean_reversion_requires_stable_volatility",
            perspective=StrategyPerspective.SIDEWAYS,
            description="Sideways strength assumes volatility does not expand into breakout conditions.",
            confidence=_clamp_01(score),
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
            description="Sideways case is invalidated by strong trend breakout pressure.",
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
            description="Sideways case is invalidated by extreme sentiment directionality.",
            observed_value=abs(sentiment_score),
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.75,
            evidence_id="sentiment.directional_score",
        ),
        StrategyInvalidationCondition(
            condition_id="sideways.technical_directional_breakout",
            perspective=StrategyPerspective.SIDEWAYS,
            description="Sideways case is invalidated by extreme technical directionality.",
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


def _breadth_context_from_evidence(
    evidence: Mapping[str, StrategyEvidenceItem],
) -> TechnicalBreadthContext:
    if "technical.breadth.confirmation_score" not in evidence:
        return TechnicalBreadthContext.unavailable()

    confirmation_score = _numeric_value(
        evidence, "technical.breadth.confirmation_score"
    )
    risk_pressure = _numeric_value(evidence, "technical.breadth.risk_pressure")
    participation_score = _numeric_value(
        evidence, "technical.breadth.participation_score"
    )
    leadership_score = _numeric_value(evidence, "technical.breadth.leadership_score")
    return TechnicalBreadthContext(
        has_breadth_data=True,
        breadth_regime=_breadth_regime(confirmation_score),
        risk_regime=_risk_regime(risk_pressure),
        breadth_score=confirmation_score,
        breadth_risk_score=risk_pressure,
        participation_score=participation_score,
        leadership_score=leadership_score,
    )


def _breadth_regime(confirmation_score: float) -> str:
    if confirmation_score >= 0.25:
        return "strong_breadth"
    if confirmation_score <= -0.25:
        return "weak_breadth"
    return "neutral_breadth"


def _risk_regime(risk_pressure: float) -> str:
    if risk_pressure >= 0.65:
        return "elevated"
    if risk_pressure <= 0.40:
        return "stable"
    return "neutral"


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
    if not breadth_context.has_breadth_data:
        return ()

    signals = [f"breadth:{breadth_context.breadth_regime}"]
    if abs(breadth_context.confirmation_score) <= 0.15:
        signals.append("mixed_breadth_structure")
    if breadth_context.is_weak:
        signals.append("narrow_or_weak_breadth_supports_sideways_case")
    if breadth_context.price_ad_divergence:
        signals.append("breadth_divergence_supports_sideways_case")
    return tuple(signals)


def _breadth_risks(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    risks: list[str] = []
    if breadth_context.is_weak:
        risks.append("breadth_uncertainty_risk")
    if breadth_context.participation_score <= -0.25:
        risks.append("participation_breakdown_risk")
    return tuple(risks)


def _breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    recommendations: list[str] = []
    if (
        breadth_context.is_weak
        or breadth_context.price_ad_divergence
        or abs(breadth_context.confirmation_score) <= 0.15
    ):
        recommendations.append("wait_for_breadth_resolution")
    if breadth_context.is_strong:
        recommendations.append("avoid_fading_strong_breadth_without_price_confirmation")
    return tuple(recommendations)


def _numeric_value(
    evidence: Mapping[str, StrategyEvidenceItem],
    evidence_id: str,
    *,
    default: float = 0.0,
) -> float:
    item = evidence.get(evidence_id)
    if item is None or isinstance(item.observed_value, bool):
        return default
    if isinstance(item.observed_value, (int, float)):
        return float(item.observed_value)
    return default


def _string_value(
    evidence: Mapping[str, StrategyEvidenceItem],
    evidence_id: str,
    *,
    default: str,
) -> str:
    item = evidence.get(evidence_id)
    if item is None or not isinstance(item.observed_value, str):
        return default
    return item.observed_value


def _reliability(
    evidence: Mapping[str, StrategyEvidenceItem],
    evidence_id: str,
    *,
    default: float = 0.0,
) -> float:
    item = evidence.get(evidence_id)
    if item is None:
        return default
    return item.reliability


def _deduplicate(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
