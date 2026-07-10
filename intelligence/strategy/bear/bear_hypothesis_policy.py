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
class BearHypothesisDecision:
    hypothesis: StrategyHypothesis
    signals: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    features: Mapping[str, object]

    def to_runtime_outputs(self) -> dict[str, object]:
        return {
            "directional_score": self.hypothesis.directional_bias,
            "confidence": self.hypothesis.confidence,
            "regime": "bear_strategy",
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "strategy_hypothesis": self.hypothesis.to_dict(),
            "features": dict(self.features),
        }


def build_bear_hypothesis(
    evidence_context: StrategyEvidenceContext,
) -> BearHypothesisDecision:
    evidence = evidence_context.evidence_by_id()

    sentiment_score = _numeric_value(evidence, "sentiment.directional_score")
    sentiment_confidence = _reliability(evidence, "sentiment.directional_score")
    bearish_sentiment = abs(min(0.0, sentiment_score))
    divergence = _numeric_value(evidence, "sentiment.divergence")
    momentum = _numeric_value(evidence, "sentiment.momentum")

    technical_score = _numeric_value(evidence, "technical.directional_score")
    technical_confidence = _reliability(evidence, "technical.directional_score")
    technical_bearishness = abs(min(0.0, technical_score))
    technical_regime = _string_value(evidence, "technical.regime", default="neutral")
    trend_strength = _numeric_value(evidence, "technical.trend_strength")
    volatility_score = _numeric_value(evidence, "technical.volatility_score")
    breadth_context = _breadth_context_from_evidence(evidence)

    fundamental_bearishness = abs(
        min(0.0, _numeric_value(evidence, "fundamental.directional_score"))
    )
    news_bearishness = abs(min(0.0, _numeric_value(evidence, "news.directional_score")))
    risk_pressure = _numeric_value(evidence, "risk.pressure")

    score = (
        (bearish_sentiment * 0.30)
        + (technical_bearishness * 0.35)
        + (fundamental_bearishness * 0.15)
        + (news_bearishness * 0.10)
        + (risk_pressure * 0.10)
    )

    if technical_regime in {"bearish", "strong_bearish"}:
        score += 0.10

    score += volatility_score * 0.05

    if divergence < 0:
        score += abs(divergence) * 0.10

    if momentum < 0:
        score += abs(momentum) * 0.05

    score += trend_strength * 0.05

    breadth_score_modifier = _breadth_score_modifier(breadth_context)
    breadth_confidence_modifier = _breadth_confidence_modifier(breadth_context)
    score = _clamp_01(score + breadth_score_modifier)

    confidence = _clamp_01(
        (sentiment_confidence * 0.40)
        + (technical_confidence * 0.60)
        + breadth_confidence_modifier
    )

    signals = _deduplicate(
        tuple(
            signal
            for signal, enabled in (
                ("bearish_sentiment", bearish_sentiment > 0.50),
                ("bearish_technical_structure", technical_bearishness > 0.50),
                ("elevated_risk_environment", risk_pressure > 0.50),
                ("volatility_expansion", volatility_score > 0.60),
            )
            if enabled
        )
        + _breadth_signals(breadth_context)
    )

    risks = _deduplicate(
        (
            "short_squeeze_risk",
            "macro_reversal_risk",
        )
        + (("counter_trend_short_risk",) if technical_regime == "bullish" else ())
        + _breadth_risks(breadth_context)
    )

    recommendations = _deduplicate(
        (
            "prefer downside confirmation",
            "avoid illiquid shorts",
        )
        + (("reduce_position_size",) if volatility_score > 0.70 else ())
        + (("tighten_risk_controls",) if risk_pressure > 0.70 else ())
        + _breadth_recommendations(breadth_context)
    )

    supporting_evidence = _evidence_for_perspective(
        evidence_context,
        support=True,
    )
    contradicting_evidence = _evidence_for_perspective(
        evidence_context,
        support=False,
    )
    data_quality_flags = _data_quality_flags(evidence_context)
    assumptions = _bear_assumptions(score, confidence, supporting_evidence)
    invalidations = _bear_invalidations(
        sentiment_score=sentiment_score,
        technical_score=technical_score,
        breadth_confirmation_score=breadth_context.confirmation_score,
        risk_pressure=risk_pressure,
    )
    thesis = _bear_thesis(score, confidence, invalidations)

    hypothesis = StrategyHypothesis(
        perspective=StrategyPerspective.BEAR,
        thesis=thesis,
        directional_bias=-score,
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
        "bear_score": score,
        "sentiment_score": sentiment_score,
        "bearish_sentiment": bearish_sentiment,
        "momentum": momentum,
        "divergence": divergence,
        "divergence_data": {"avg_divergence": divergence},
        "technical_score": technical_score,
        "technical_bearishness": technical_bearishness,
        "technical_regime": technical_regime,
        "trend_strength": trend_strength,
        "volatility_score": volatility_score,
        "breadth_context": breadth_context.to_dict(),
        "breadth_confirmation_score": breadth_context.confirmation_score,
        "breadth_risk_pressure": breadth_context.risk_pressure,
        "breadth_score_modifier": breadth_score_modifier,
        "breadth_confidence_modifier": breadth_confidence_modifier,
        "breadth_risk_flags": list(breadth_context.risk_flags()),
        "fundamental_bearishness": fundamental_bearishness,
        "news_bearishness": news_bearishness,
        "risk_pressure": risk_pressure,
        "evidence_fingerprint": hypothesis.evidence_fingerprint,
        "hypothesis_strength": hypothesis.hypothesis_strength,
        "supporting_evidence_count": len(hypothesis.supporting_evidence),
        "contradicting_evidence_count": len(hypothesis.contradicting_evidence),
        "invalidated": hypothesis.invalidated,
    }

    return BearHypothesisDecision(
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
    perspective = StrategyPerspective.BEAR
    return tuple(
        item
        for item in evidence_context.all_evidence
        if perspective in (item.supports if support else item.contradicts)
    )


def _data_quality_flags(
    evidence_context: StrategyEvidenceContext,
) -> tuple[str, ...]:
    flags = [
        f"{quality.input_name}:{quality.status.value}"
        for quality in evidence_context.input_quality
        if quality.status is not StrategyEvidenceInputStatus.AVAILABLE
    ]
    return tuple(flags)


def _bear_assumptions(
    score: float,
    confidence: float,
    supporting_evidence: tuple[StrategyEvidenceItem, ...],
) -> tuple[StrategyAssumption, ...]:
    evidence_ids = tuple(item.evidence_id for item in supporting_evidence[:5])
    return (
        StrategyAssumption(
            assumption_id="bear.downside_requires_negative_evidence",
            perspective=StrategyPerspective.BEAR,
            description="Bearish posture requires negative evidence to remain persistent.",
            confidence=_clamp_01(confidence),
            evidence_ids=evidence_ids,
        ),
        StrategyAssumption(
            assumption_id="bear.strength_requires_risk_or_trend_pressure",
            perspective=StrategyPerspective.BEAR,
            description="Bearish strength assumes risk pressure or trend pressure does not unwind.",
            confidence=_clamp_01(score),
            evidence_ids=evidence_ids,
        ),
    )


def _bear_invalidations(
    *,
    sentiment_score: float,
    technical_score: float,
    breadth_confirmation_score: float,
    risk_pressure: float,
) -> tuple[StrategyInvalidationCondition, ...]:
    return (
        StrategyInvalidationCondition(
            condition_id="bear.sentiment_reversal",
            perspective=StrategyPerspective.BEAR,
            description="Bear case is invalidated if sentiment turns materially bullish.",
            observed_value=sentiment_score,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.25,
            evidence_id="sentiment.directional_score",
        ),
        StrategyInvalidationCondition(
            condition_id="bear.technical_reversal",
            perspective=StrategyPerspective.BEAR,
            description="Bear case is invalidated if technical structure turns bullish.",
            observed_value=technical_score,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.25,
            evidence_id="technical.directional_score",
        ),
        StrategyInvalidationCondition(
            condition_id="bear.breadth_reacceleration",
            perspective=StrategyPerspective.BEAR,
            description="Bear case is invalidated if market breadth strongly reaccelerates.",
            observed_value=breadth_confirmation_score,
            operator=StrategyInvalidationOperator.GREATER_THAN,
            threshold=0.45,
            evidence_id="technical.breadth.confirmation_score",
        ),
        StrategyInvalidationCondition(
            condition_id="bear.risk_pressure_collapse",
            perspective=StrategyPerspective.BEAR,
            description="Bear case is invalidated if aggregate risk pressure collapses.",
            observed_value=risk_pressure,
            operator=StrategyInvalidationOperator.LESS_THAN,
            threshold=0.15,
            evidence_id="risk.pressure",
        ),
    )


def _bear_thesis(
    score: float,
    confidence: float,
    invalidations: tuple[StrategyInvalidationCondition, ...],
) -> str:
    if any(condition.is_invalidated() for condition in invalidations):
        return "Bear hypothesis is currently invalidated by hard reversal conditions."
    if score >= 0.65 and confidence >= 0.60:
        return "Bear hypothesis is supported by aligned downside evidence."
    if score >= 0.35:
        return "Bear hypothesis is plausible but requires downside confirmation."
    return "Bear hypothesis is weak because downside evidence is limited."


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


def _breadth_score_modifier(
    breadth_context: TechnicalBreadthContext,
) -> float:
    if not breadth_context.has_breadth_data:
        return 0.0
    if breadth_context.is_strong:
        return -0.10

    modifier = max(0.0, -breadth_context.confirmation_score) * 0.08
    if breadth_context.is_weak:
        modifier += 0.08
    if breadth_context.price_ad_divergence:
        modifier += 0.04
    if breadth_context.participation_score <= -0.25:
        modifier += 0.03
    if breadth_context.leadership_score <= -0.25:
        modifier += 0.03
    return min(0.18, modifier)


def _breadth_confidence_modifier(
    breadth_context: TechnicalBreadthContext,
) -> float:
    if not breadth_context.has_breadth_data:
        return 0.0
    if breadth_context.is_strong:
        return -0.06
    if breadth_context.is_weak:
        return 0.06
    return max(0.0, -breadth_context.confirmation_score) * 0.03


def _breadth_signals(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    signals = [f"breadth:{breadth_context.breadth_regime}"]
    if breadth_context.is_weak:
        signals.append("bearish_breadth_confirmation")
    if breadth_context.price_ad_divergence:
        signals.append("breadth_divergence_supports_bear_case")
    return tuple(signals)


def _breadth_risks(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    risks: list[str] = []
    if breadth_context.is_strong:
        risks.append("strong_breadth_countertrend_risk")
    return tuple(risks)


def _breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    recommendations: list[str] = []
    if breadth_context.is_weak:
        recommendations.append("breadth_confirms_defensive_bias")
    if breadth_context.is_strong:
        recommendations.append("reduce_bearish_conviction_until_breadth_weakens")
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
