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

    sentiment_score = _numeric_value(evidence, "sentiment.directional_score")
    sentiment_confidence = _reliability(evidence, "sentiment.directional_score")
    bullish_sentiment = max(0.0, sentiment_score)
    momentum = _numeric_value(evidence, "sentiment.momentum")
    stability = _numeric_value(evidence, "sentiment.stability")
    divergence = _numeric_value(evidence, "sentiment.divergence")

    technical_score = _numeric_value(evidence, "technical.directional_score")
    technical_confidence = _reliability(evidence, "technical.directional_score")
    technical_bullishness = max(0.0, technical_score)
    technical_regime = _string_value(evidence, "technical.regime", default="neutral")
    trend_strength = _numeric_value(evidence, "technical.trend_strength")
    volatility_score = _numeric_value(evidence, "technical.volatility_score")
    breadth_context = _breadth_context_from_evidence(evidence)

    fundamental_bullishness = max(
        0.0,
        _numeric_value(evidence, "fundamental.directional_score"),
    )
    news_bullishness = max(0.0, _numeric_value(evidence, "news.directional_score"))
    risk_pressure = _numeric_value(evidence, "risk.pressure")

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

    risks = _deduplicate(
        (
            "bull_trap_risk",
            "overextension_risk",
        )
        + (("high_volatility_breakdown_risk",) if volatility_score > 0.70 else ())
        + (("macro_risk_pressure",) if risk_pressure > 0.70 else ())
        + _breadth_risks(breadth_context)
    )

    recommendations = _deduplicate(
        (
            "scale_into_strength",
            "avoid_chasing_extended_moves",
        )
        + (("reduce_position_size",) if volatility_score > 0.70 else ())
        + (("tighten_risk_controls",) if risk_pressure > 0.60 else ())
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
        data_quality_flags=data_quality_flags,
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


def _evidence_for_perspective(
    evidence_context: StrategyEvidenceContext,
    *,
    support: bool,
) -> tuple[StrategyEvidenceItem, ...]:
    perspective = StrategyPerspective.BULL
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
            confidence=_clamp_01(confidence),
            evidence_ids=evidence_ids,
        ),
        StrategyAssumption(
            assumption_id="bull.strength_requires_follow_through",
            perspective=StrategyPerspective.BULL,
            description="Bullish strength assumes trend and sentiment follow-through do not fail.",
            confidence=_clamp_01(score),
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
    if not breadth_context.has_breadth_data:
        return ()

    signals = [f"breadth:{breadth_context.breadth_regime}"]
    if breadth_context.is_strong:
        signals.append("bullish_breadth_confirmation")
    if breadth_context.is_weak:
        signals.append("weak_breadth_not_confirming_bullish_setup")
    return tuple(signals)


def _breadth_risks(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    risks: list[str] = []
    if breadth_context.is_weak:
        risks.append("breadth_not_confirming_bullish_setup")
    if breadth_context.leadership_score <= -0.25:
        risks.append("narrow_leadership_risk")
    if breadth_context.price_ad_divergence:
        risks.append("price_ad_divergence_risk")
    return tuple(risks)


def _breadth_recommendations(
    breadth_context: TechnicalBreadthContext,
) -> tuple[str, ...]:
    if not breadth_context.has_breadth_data:
        return ()

    recommendations: list[str] = []
    if breadth_context.is_weak:
        recommendations.append("wait_for_breadth_confirmation")
    if breadth_context.price_ad_divergence:
        recommendations.append(
            "avoid_aggressive_long_exposure_until_divergence_resolves"
        )
    if breadth_context.is_strong:
        recommendations.append("breadth_confirms_bullish_setup")
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
