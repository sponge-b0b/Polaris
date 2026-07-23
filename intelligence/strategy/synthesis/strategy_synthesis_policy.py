from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.services.market_events.market_events_result import MarketEventsResult
from core.utils.utils import _clamp
from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.hypothesis import StrategyHypothesis
from intelligence.strategy.synthesis.contracts import (
    StrategyHypothesisEvaluation,
    StrategySynthesisDecision,
    StrategySynthesisDegradedReason,
    StrategySynthesisSelectionStatus,
    normalize_strategy_hypothesis_evaluations,
)


@dataclass(
    frozen=True,
    slots=True,
)
class StrategyMarketEvents:
    symbol: str
    market_pressure_score: float
    volatility_pressure: float
    volatility_forecast: str
    regime_bias: str
    service_result: MarketEventsResult | None = None
    event_error: str | None = None

    @classmethod
    def from_service_result(
        cls,
        result: MarketEventsResult,
    ) -> StrategyMarketEvents:
        return cls(
            symbol=result.symbol,
            market_pressure_score=result.market_pressure_score,
            volatility_pressure=result.volatility_pressure,
            volatility_forecast=result.volatility_forecast,
            regime_bias=result.regime_bias,
            service_result=result,
        )

    @classmethod
    def neutral(
        cls,
        *,
        symbol: str,
        error: str,
    ) -> StrategyMarketEvents:
        return cls(
            symbol=symbol,
            market_pressure_score=0.0,
            volatility_pressure=0.0,
            volatility_forecast="unknown",
            regime_bias="neutral",
            event_error=error,
        )

    def to_dict(self) -> dict[str, Any]:
        if self.service_result is not None:
            return self.service_result.to_dict()
        return {
            "symbol": self.symbol,
            "market_pressure_score": self.market_pressure_score,
            "volatility_pressure": self.volatility_pressure,
            "volatility_forecast": self.volatility_forecast,
            "regime_bias": self.regime_bias,
            "event_error": self.event_error,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class StrategySynthesisInputs:
    symbol: str
    event_lookahead_days: int
    horizon: str
    bull_weight: float
    bear_weight: float
    sideways_weight: float
    bull_hypothesis: StrategyHypothesis
    bear_hypothesis: StrategyHypothesis
    sideways_hypothesis: StrategyHypothesis
    adjusted_risk_pressure: float
    composite_risk: float
    portfolio_scale_factor: float
    portfolio_status: str
    technical_regime: str
    breadth_context: TechnicalBreadthContext
    symbol_constituents: frozenset[str]


@dataclass(
    frozen=True,
    slots=True,
)
class _RuntimeStrategySynthesisOutput:
    directional_score: float
    confidence: float
    regime: str
    uncertainty: float
    signals: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    features: dict[str, Any]

    def to_runtime_outputs(self) -> dict[str, Any]:
        return {
            "directional_score": self.directional_score,
            "confidence": self.confidence,
            "regime": self.regime,
            "signals": list(self.signals),
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "features": self.features,
        }


def synthesize_strategy(
    inputs: StrategySynthesisInputs,
    market_events: StrategyMarketEvents,
) -> _RuntimeStrategySynthesisOutput:
    perspective_weights = normalize_weights(
        inputs.bull_weight,
        inputs.bear_weight,
        inputs.sideways_weight,
    )
    evaluations = normalize_strategy_hypothesis_evaluations(
        (
            evaluate_strategy_hypothesis(
                inputs.bull_hypothesis,
                perspective_weight=perspective_weights[0],
            ),
            evaluate_strategy_hypothesis(
                inputs.bear_hypothesis,
                perspective_weight=perspective_weights[1],
            ),
            evaluate_strategy_hypothesis(
                inputs.sideways_hypothesis,
                perspective_weight=perspective_weights[2],
            ),
        )
    )
    bull_weight, bear_weight, sideways_weight = synthesis_weights(evaluations)
    event_pressure = _clamp(
        market_events.market_pressure_score,
        lower=0.0,
        upper=1.0,
    )
    event_bias = market_events.regime_bias
    event_volatility = _clamp(
        market_events.volatility_pressure,
        lower=0.0,
        upper=1.0,
    )
    bull_weight, bear_weight, sideways_weight = apply_event_weighting(
        bull_weight=bull_weight,
        bear_weight=bear_weight,
        sideways_weight=sideways_weight,
        event_pressure=event_pressure,
        event_bias=event_bias,
        event_volatility=event_volatility,
    )
    bull_weight, bear_weight, sideways_weight = normalize_weights(
        bull_weight,
        bear_weight,
        sideways_weight,
    )

    risk_multiplier = _clamp(
        1.0 - (inputs.adjusted_risk_pressure * 0.50),
        lower=0.0,
        upper=1.0,
    )
    bull_weight *= risk_multiplier
    bear_weight *= 1.0 - (inputs.adjusted_risk_pressure * 0.15)
    sideways_weight *= 1.0 + inputs.adjusted_risk_pressure
    bull_weight, bear_weight, sideways_weight = normalize_weights(
        bull_weight,
        bear_weight,
        sideways_weight,
    )

    net_bias = _clamp(bull_weight - bear_weight, lower=-1.0, upper=1.0)
    posture = classify_posture(
        net_bias=net_bias,
        sideways_weight=sideways_weight,
        event_pressure=event_pressure,
    )
    event_uncertainty_modifier = event_uncertainty(
        event_pressure=event_pressure,
        event_volatility=event_volatility,
    )
    breadth_uncertainty_modifier = breadth_uncertainty(inputs.breadth_context)
    synthesis_disagreement = hypothesis_synthesis_disagreement(evaluations)
    uncertainty = _clamp(
        calculate_uncertainty(
            net_bias=net_bias,
            sideways_weight=sideways_weight,
            risk_pressure=inputs.adjusted_risk_pressure,
            event_pressure=event_pressure,
            event_volatility=event_volatility,
        )
        + breadth_uncertainty_modifier
        + event_uncertainty_modifier
        + (synthesis_disagreement * 0.15),
        lower=0.0,
        upper=1.0,
    )
    confidence = _clamp(
        (1.0 - uncertainty) * inputs.portfolio_scale_factor,
        lower=0.0,
        upper=1.0,
    )

    breadth_readiness_modifier = breadth_execution_readiness(inputs.breadth_context)
    event_readiness_modifier = event_execution_readiness(
        event_pressure=event_pressure,
        event_bias=event_bias,
    )
    execution_readiness = _clamp(
        abs(net_bias) * confidence * inputs.portfolio_scale_factor
        + breadth_readiness_modifier
        + event_readiness_modifier,
        lower=0.0,
        upper=1.0,
    )

    breadth_quality_modifier = breadth_signal_quality(inputs.breadth_context)
    event_quality_modifier = event_signal_quality(
        event_pressure=event_pressure,
        event_volatility=event_volatility,
    )
    signal_quality = _clamp(
        (abs(net_bias) * 0.45)
        + (confidence * 0.25)
        + ((1.0 - inputs.composite_risk) * 0.20)
        + ((1.0 - event_pressure) * 0.10)
        + breadth_quality_modifier
        + event_quality_modifier,
        lower=0.0,
        upper=1.0,
    )

    selected_hypothesis = selected_strategy_hypothesis(
        evaluations=evaluations,
        inputs=inputs,
    )
    degraded_reasons = synthesis_degraded_reasons(
        evaluations=evaluations,
        confidence=confidence,
        market_events=market_events,
        inputs=inputs,
    )
    thesis = synthesis_thesis(
        selected_hypothesis=selected_hypothesis,
        degraded_reasons=degraded_reasons,
    )

    hypothesis_signals = synthesis_hypothesis_signals(evaluations, selected_hypothesis)
    signals = deduplicate(
        [
            posture,
            *hypothesis_signals,
            f"bull_weight:{bull_weight}",
            f"bear_weight:{bear_weight}",
            f"sideways_weight:{sideways_weight}",
            f"net_bias:{net_bias}",
            f"risk_pressure:{inputs.adjusted_risk_pressure}",
            f"event_pressure:{event_pressure}",
            f"event_bias:{event_bias}",
            f"event_volatility:{event_volatility}",
            f"technical_regime:{inputs.technical_regime}",
            f"portfolio_status:{inputs.portfolio_status}",
            *event_context_signals(market_events),
            *event_signals(
                event_pressure=event_pressure,
                event_bias=event_bias,
                event_volatility=event_volatility,
            ),
            *breadth_signals(inputs.breadth_context),
        ]
    )
    risks = base_risks(
        adjusted_risk_pressure=inputs.adjusted_risk_pressure,
        sideways_weight=sideways_weight,
        confidence=confidence,
        net_bias=net_bias,
        portfolio_status=inputs.portfolio_status,
    )
    risks = deduplicate(
        [
            *risks,
            *hypothesis_risks(selected_hypothesis, degraded_reasons),
            *event_context_risks(market_events),
            *event_risks(
                event_pressure=event_pressure,
                event_bias=event_bias,
                event_volatility=event_volatility,
            ),
            *breadth_risks(inputs.breadth_context),
        ]
    )
    recommendations = deduplicate(
        [
            *posture_recommendations(posture, confidence),
            *hypothesis_recommendations(selected_hypothesis, degraded_reasons),
            *event_recommendations(
                event_pressure=event_pressure,
                event_bias=event_bias,
                event_volatility=event_volatility,
            ),
            *breadth_recommendations(inputs.breadth_context),
        ]
    )

    decision = StrategySynthesisDecision.from_evaluations(
        evaluations=evaluations,
        directional_score=net_bias,
        confidence=confidence,
        regime=posture,
        uncertainty=uncertainty,
        thesis=thesis,
        signals=tuple(signals),
        risks=tuple(risks),
        recommendations=tuple(recommendations),
        degraded_reasons=tuple(degraded_reasons),
    )

    return _RuntimeStrategySynthesisOutput(
        directional_score=net_bias,
        confidence=confidence,
        regime=posture,
        uncertainty=uncertainty,
        signals=decision.signals,
        risks=decision.risks,
        recommendations=decision.recommendations,
        features={
            "symbol": inputs.symbol,
            "bull_weight": bull_weight,
            "bear_weight": bear_weight,
            "sideways_weight": sideways_weight,
            "allocation_vector": {
                "bull": bull_weight * inputs.portfolio_scale_factor,
                "bear": bear_weight * inputs.portfolio_scale_factor,
                "sideways": sideways_weight * inputs.portfolio_scale_factor,
            },
            "net_bias": net_bias,
            "uncertainty": uncertainty,
            "execution_readiness": execution_readiness,
            "signal_quality": signal_quality,
            "posture": posture,
            "composite_risk": inputs.composite_risk,
            "risk_pressure": inputs.adjusted_risk_pressure,
            "portfolio_scale_factor": inputs.portfolio_scale_factor,
            "portfolio_status": inputs.portfolio_status,
            "technical_regime": inputs.technical_regime,
            "market_events": market_events.to_dict(),
            "market_event_constituents": sorted(inputs.symbol_constituents),
            "event_lookahead_days": inputs.event_lookahead_days,
            "event_pressure": event_pressure,
            "event_bias": event_bias,
            "event_volatility": event_volatility,
            "event_uncertainty_modifier": event_uncertainty_modifier,
            "event_execution_readiness_modifier": event_readiness_modifier,
            "event_signal_quality_modifier": event_quality_modifier,
            "breadth_context": inputs.breadth_context.to_dict(),
            "breadth_confirmation_score": inputs.breadth_context.confirmation_score,
            "breadth_risk_pressure": inputs.breadth_context.risk_pressure,
            "breadth_uncertainty_modifier": breadth_uncertainty_modifier,
            "breadth_execution_readiness_modifier": breadth_readiness_modifier,
            "breadth_signal_quality_modifier": breadth_quality_modifier,
            "breadth_risk_flags": list(inputs.breadth_context.risk_flags()),
            "strategy_synthesis_decision": decision.to_dict(),
            "strategy_hypothesis_evaluations": [
                evaluation.to_dict() for evaluation in decision.evaluations
            ],
            "hypothesis_candidate_scores": {
                evaluation.perspective.value: evaluation.candidate_score
                for evaluation in decision.evaluations
            },
            "hypothesis_synthesis_weights": {
                evaluation.perspective.value: evaluation.synthesis_weight
                for evaluation in decision.evaluations
            },
            "hypothesis_synthesis_disagreement": synthesis_disagreement,
            "selected_hypothesis": (
                None if selected_hypothesis is None else selected_hypothesis.to_dict()
            ),
            "selected_perspective": (
                None
                if decision.selected_perspective is None
                else decision.selected_perspective.value
            ),
            "selection_status": decision.selection_status.value,
            "degraded_reasons": [reason.value for reason in decision.degraded_reasons],
            "thesis": decision.thesis,
        },
    )


def evaluate_strategy_hypothesis(
    hypothesis: StrategyHypothesis,
    *,
    perspective_weight: float,
) -> StrategyHypothesisEvaluation:
    """Evaluate one hypothesis with the canonical pure candidate-score formula."""

    normalized_weight = _clamp(perspective_weight, lower=0.0, upper=1.0)
    contradiction_burden = hypothesis_contradiction_burden(hypothesis)
    assumption_support = hypothesis_assumption_support(hypothesis)
    candidate_score = 0.0
    if not hypothesis.invalidated:
        candidate_score = _clamp(
            normalized_weight
            * hypothesis.hypothesis_strength
            * hypothesis.confidence
            * assumption_support
            * (1.0 - contradiction_burden),
            lower=0.0,
            upper=1.0,
        )

    return StrategyHypothesisEvaluation(
        perspective=hypothesis.perspective,
        perspective_weight=normalized_weight,
        contradiction_burden=contradiction_burden,
        assumption_support=assumption_support,
        invalidated=hypothesis.invalidated,
        candidate_score=candidate_score,
        synthesis_weight=0.0,
        rank=0,
        selection_status=StrategySynthesisSelectionStatus.CANDIDATE,
        degraded_reasons=(
            (StrategySynthesisDegradedReason.DATA_QUALITY_DEGRADED,)
            if hypothesis.data_quality_flags
            else ()
        ),
    )


def hypothesis_contradiction_burden(hypothesis: StrategyHypothesis) -> float:
    if not hypothesis.contradicting_evidence:
        return 0.0
    total = sum(
        evidence.strength * evidence.reliability
        for evidence in hypothesis.contradicting_evidence
    )
    return _clamp(
        total / len(hypothesis.contradicting_evidence),
        lower=0.0,
        upper=1.0,
    )


def hypothesis_assumption_support(hypothesis: StrategyHypothesis) -> float:
    if not hypothesis.key_assumptions:
        return 1.0
    total = sum(assumption.confidence for assumption in hypothesis.key_assumptions)
    return _clamp(total / len(hypothesis.key_assumptions), lower=0.0, upper=1.0)


def synthesis_weights(
    evaluations: tuple[StrategyHypothesisEvaluation, ...],
) -> tuple[float, float, float]:
    by_perspective = {evaluation.perspective: evaluation for evaluation in evaluations}
    bull = by_perspective[StrategyPerspective.BULL].synthesis_weight
    bear = by_perspective[StrategyPerspective.BEAR].synthesis_weight
    sideways = by_perspective[StrategyPerspective.SIDEWAYS].synthesis_weight
    if bull + bear + sideways <= 0.0:
        return 0.0, 0.0, 1.0
    return bull, bear, sideways


def hypothesis_synthesis_disagreement(
    evaluations: tuple[StrategyHypothesisEvaluation, ...],
) -> float:
    valid_synthesis_weights = tuple(
        evaluation.synthesis_weight
        for evaluation in evaluations
        if not evaluation.invalidated
    )
    if not valid_synthesis_weights:
        return 1.0
    return _clamp(1.0 - max(valid_synthesis_weights), lower=0.0, upper=1.0)


def selected_strategy_hypothesis(
    *,
    evaluations: tuple[StrategyHypothesisEvaluation, ...],
    inputs: StrategySynthesisInputs,
) -> StrategyHypothesis | None:
    selected = tuple(
        evaluation
        for evaluation in evaluations
        if evaluation.selection_status is StrategySynthesisSelectionStatus.SELECTED
    )
    if len(selected) != 1:
        return None
    return hypothesis_by_perspective(inputs)[selected[0].perspective]


def hypothesis_by_perspective(
    inputs: StrategySynthesisInputs,
) -> dict[StrategyPerspective, StrategyHypothesis]:
    return {
        StrategyPerspective.BULL: inputs.bull_hypothesis,
        StrategyPerspective.BEAR: inputs.bear_hypothesis,
        StrategyPerspective.SIDEWAYS: inputs.sideways_hypothesis,
    }


def synthesis_degraded_reasons(
    *,
    evaluations: tuple[StrategyHypothesisEvaluation, ...],
    confidence: float,
    market_events: StrategyMarketEvents,
    inputs: StrategySynthesisInputs,
) -> list[StrategySynthesisDegradedReason]:
    reasons: list[StrategySynthesisDegradedReason] = []
    if all(evaluation.invalidated for evaluation in evaluations):
        reasons.append(StrategySynthesisDegradedReason.ALL_HYPOTHESES_INVALIDATED)
    if any(
        evaluation.selection_status is StrategySynthesisSelectionStatus.TIED
        for evaluation in evaluations
    ):
        reasons.append(StrategySynthesisDegradedReason.TIED_CANDIDATES)
    if confidence <= 0.35:
        reasons.append(StrategySynthesisDegradedReason.LOW_CONFIDENCE)
    if market_events.event_error:
        reasons.append(StrategySynthesisDegradedReason.DATA_QUALITY_DEGRADED)
    if any(
        hypothesis.data_quality_flags
        for hypothesis in hypothesis_by_perspective(inputs).values()
    ):
        reasons.append(StrategySynthesisDegradedReason.DATA_QUALITY_DEGRADED)
    return list(dict.fromkeys(reasons))


def synthesis_thesis(
    *,
    selected_hypothesis: StrategyHypothesis | None,
    degraded_reasons: list[StrategySynthesisDegradedReason],
) -> str:
    if selected_hypothesis is None:
        if degraded_reasons:
            reasons = ", ".join(reason.value for reason in degraded_reasons)
            return f"Strategy synthesis is degraded because {reasons}."
        return "Strategy synthesis did not identify a dominant hypothesis."
    if degraded_reasons:
        reasons = ", ".join(reason.value for reason in degraded_reasons)
        return f"{selected_hypothesis.thesis} Synthesis is degraded by {reasons}."
    return selected_hypothesis.thesis


def synthesis_hypothesis_signals(
    evaluations: tuple[StrategyHypothesisEvaluation, ...],
    selected_hypothesis: StrategyHypothesis | None,
) -> list[str]:
    signals = [
        f"{evaluation.perspective.value}_candidate_score:{evaluation.candidate_score}"
        for evaluation in evaluations
    ]
    if selected_hypothesis is not None:
        signals.append(
            f"selected_strategy_hypothesis:{selected_hypothesis.perspective.value}"
        )
    if any(
        evaluation.selection_status is StrategySynthesisSelectionStatus.TIED
        for evaluation in evaluations
    ):
        signals.append("strategy_hypothesis_tie")
    if all(evaluation.invalidated for evaluation in evaluations):
        signals.append("all_strategy_hypotheses_invalidated")
    return signals


def hypothesis_risks(
    selected_hypothesis: StrategyHypothesis | None,
    degraded_reasons: list[StrategySynthesisDegradedReason],
) -> list[str]:
    risks: list[str] = []
    if selected_hypothesis is not None:
        risks.extend(selected_hypothesis.risks)
    if StrategySynthesisDegradedReason.TIED_CANDIDATES in degraded_reasons:
        risks.append("tied_strategy_hypotheses")
    if StrategySynthesisDegradedReason.ALL_HYPOTHESES_INVALIDATED in degraded_reasons:
        risks.append("no_valid_strategy_hypothesis")
    if StrategySynthesisDegradedReason.LOW_CONFIDENCE in degraded_reasons:
        risks.append("low_hypothesis_synthesis_confidence")
    return risks


def hypothesis_recommendations(
    selected_hypothesis: StrategyHypothesis | None,
    degraded_reasons: list[StrategySynthesisDegradedReason],
) -> list[str]:
    recommendations: list[str] = []
    if selected_hypothesis is not None:
        recommendations.extend(selected_hypothesis.recommendations)
    if degraded_reasons:
        recommendations.append("require_human_review_of_strategy_hypotheses")
    return recommendations


def normalize_weights(
    bull: float,
    bear: float,
    sideways: float,
) -> tuple[float, float, float]:
    bull = max(0.0, bull)
    bear = max(0.0, bear)
    sideways = max(0.0, sideways)
    total = bull + bear + sideways
    if total <= 0:
        return 0.33, 0.33, 0.34
    return bull / total, bear / total, sideways / total


def apply_event_weighting(
    *,
    bull_weight: float,
    bear_weight: float,
    sideways_weight: float,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> tuple[float, float, float]:
    if event_pressure >= 0.70:
        bull_weight *= 0.85
        bear_weight *= 0.85
        # Preserve the established two-stage high-pressure uncertainty penalty.
        sideways_weight *= 1.20
        sideways_weight *= 1.20
    elif event_pressure <= 0.30:
        bull_weight *= 1.05
        bear_weight *= 1.05
        sideways_weight *= 0.95

    if event_volatility >= 0.70:
        bull_weight *= 0.90
        bear_weight *= 0.95
        sideways_weight *= 1.15
    if event_bias == "risk_off":
        bull_weight *= 0.80
        bear_weight *= 1.15
        sideways_weight *= 1.05
    elif event_bias == "risk_on":
        bull_weight *= 1.10
        bear_weight *= 0.90
    return bull_weight, bear_weight, sideways_weight


def classify_posture(
    *,
    net_bias: float,
    sideways_weight: float,
    event_pressure: float,
) -> str:
    if event_pressure >= 0.85 or sideways_weight >= 0.55:
        return "neutral"
    if net_bias >= 0.45:
        return "strong_risk_on"
    if net_bias >= 0.20:
        return "risk_on"
    if net_bias <= -0.45:
        return "strong_risk_off"
    if net_bias <= -0.20:
        return "risk_off"
    return "neutral"


def calculate_uncertainty(
    *,
    net_bias: float,
    sideways_weight: float,
    risk_pressure: float,
    event_pressure: float,
    event_volatility: float,
) -> float:
    return _clamp(
        (sideways_weight * 0.40)
        + ((1.0 - abs(net_bias)) * 0.30)
        + (risk_pressure * 0.20)
        + (event_pressure * 0.07)
        + (event_volatility * 0.03),
        lower=0.0,
        upper=1.0,
    )


def event_uncertainty(*, event_pressure: float, event_volatility: float) -> float:
    return _clamp(
        (event_pressure * 0.08) + (event_volatility * 0.05),
        lower=0.0,
        upper=0.15,
    )


def event_execution_readiness(*, event_pressure: float, event_bias: str) -> float:
    modifier = 0.0
    if event_pressure >= 0.70:
        modifier -= 0.08
    if event_bias == "risk_off":
        modifier -= 0.04
    elif event_bias == "risk_on" and event_pressure <= 0.50:
        modifier += 0.03
    return _clamp(modifier, lower=-0.12, upper=0.04)


def event_signal_quality(
    *,
    event_pressure: float,
    event_volatility: float,
) -> float:
    modifier = 0.0
    if event_pressure >= 0.70:
        modifier -= 0.05
    if event_volatility >= 0.70:
        modifier -= 0.04
    if event_pressure <= 0.25 and event_volatility <= 0.35:
        modifier += 0.03
    return _clamp(modifier, lower=-0.10, upper=0.03)


def breadth_uncertainty(context: TechnicalBreadthContext) -> float:
    if not context.has_breadth_data:
        return 0.0
    modifier = 0.0
    if context.is_weak:
        modifier += 0.08
    if context.price_ad_divergence:
        modifier += 0.05
    if context.participation_score <= -0.25:
        modifier += 0.03
    if context.leadership_score <= -0.25:
        modifier += 0.02
    if context.is_strong:
        modifier -= min(0.06, context.confirmation_score * 0.08)
    return _clamp(modifier, lower=-0.06, upper=0.16)


def breadth_execution_readiness(context: TechnicalBreadthContext) -> float:
    if not context.has_breadth_data:
        return 0.0
    modifier = 0.0
    if context.is_weak:
        modifier -= 0.08
    if context.price_ad_divergence:
        modifier -= 0.05
    if context.risk_pressure >= 0.65:
        modifier -= 0.03
    if context.is_strong:
        modifier += min(0.06, context.confirmation_score * 0.08)
    return _clamp(modifier, lower=-0.16, upper=0.06)


def breadth_signal_quality(context: TechnicalBreadthContext) -> float:
    if not context.has_breadth_data:
        return 0.0
    modifier = 0.0
    if context.is_weak:
        modifier -= 0.05
    if context.price_ad_divergence:
        modifier -= 0.03
    if context.is_strong:
        modifier += min(0.05, context.confirmation_score * 0.07)
    return _clamp(modifier, lower=-0.08, upper=0.05)


def event_context_signals(events: StrategyMarketEvents) -> list[str]:
    return ["market_event_context_unavailable"] if events.event_error else []


def event_context_risks(events: StrategyMarketEvents) -> list[str]:
    return ["market_event_context_unavailable"] if events.event_error else []


def event_signals(
    *,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> list[str]:
    signals: list[str] = []
    if event_pressure >= 0.70:
        signals.append("high_event_pressure_conditions")
    if event_pressure <= 0.30:
        signals.append("low_event_pressure_conditions")
    if event_bias in {"risk_on", "risk_off"}:
        signals.append(f"event_bias:{event_bias}")
    if event_volatility >= 0.70:
        signals.append("event_volatility_pressure_elevated")
    return signals


def event_risks(
    *,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> list[str]:
    risks: list[str] = []
    if event_pressure >= 0.70:
        risks.append("high_event_pressure")
    if event_bias == "risk_off":
        risks.append("event_regime_risk_off")
    if event_volatility >= 0.70:
        risks.append("event_volatility_risk")
    return risks


def event_recommendations(
    *,
    event_pressure: float,
    event_bias: str,
    event_volatility: float,
) -> list[str]:
    recommendations: list[str] = []
    if event_pressure >= 0.70:
        recommendations.extend(
            [
                "reduce_conviction_until_event_risk_clears",
                "avoid_oversized_positions_into_event_window",
            ]
        )
    if event_bias == "risk_off":
        recommendations.append("respect_event_driven_risk_off_bias")
    if event_volatility >= 0.70:
        recommendations.append("expect_volatility_around_event_window")
    return recommendations


def breadth_signals(context: TechnicalBreadthContext) -> list[str]:
    if not context.has_breadth_data:
        return []
    signals = [f"breadth:{context.breadth_regime}"]
    if context.is_strong:
        signals.append("breadth_confirms_strategy_synthesis")
    if context.is_weak:
        signals.append("weak_breadth_lowers_execution_readiness")
    if context.price_ad_divergence:
        signals.append("breadth_divergence_increases_synthesis_uncertainty")
    return signals


def breadth_risks(context: TechnicalBreadthContext) -> list[str]:
    if not context.has_breadth_data:
        return []
    risks = list(context.risk_flags())
    if context.is_weak:
        risks.append("breadth_confirmation_risk")
    if context.price_ad_divergence:
        risks.append("breadth_divergence_risk")
    return risks


def breadth_recommendations(context: TechnicalBreadthContext) -> list[str]:
    if not context.has_breadth_data:
        return []
    if context.is_strong:
        return ["breadth_supports_strategy_conviction"]
    if context.is_weak or context.price_ad_divergence:
        return [
            "require_breadth_confirmation_before_aggressive_allocation",
            "reduce_execution_urgency_until_breadth_improves",
        ]
    return []


def base_risks(
    *,
    adjusted_risk_pressure: float,
    sideways_weight: float,
    confidence: float,
    net_bias: float,
    portfolio_status: str,
) -> list[str]:
    risks: list[str] = []
    if adjusted_risk_pressure >= 0.70:
        risks.append("high_risk_environment")
    if sideways_weight >= 0.50:
        risks.append("high_regime_uncertainty")
    if confidence <= 0.35:
        risks.append("low_synthesis_confidence")
    if abs(net_bias) <= 0.15:
        risks.append("weak_directional_edge")
    if portfolio_status == "rejected":
        risks.append("portfolio_execution_restricted")
    return risks


def posture_recommendations(posture: str, confidence: float) -> list[str]:
    if posture.startswith("strong_risk_on"):
        recommendations = [
            "allow_aggressive_trend_exposure",
            "favor_breakout_continuation",
        ]
    elif posture == "risk_on":
        recommendations = ["favor_long_exposure", "allow_trend_following"]
    elif posture.startswith("strong_risk_off"):
        recommendations = ["preserve_capital", "reduce_beta_exposure"]
    elif posture == "risk_off":
        recommendations = ["reduce_net_exposure", "favor_defensive_positioning"]
    else:
        recommendations = [
            "reduce_aggressive_positioning",
            "favor_market_neutrality",
        ]
    if confidence <= 0.40:
        recommendations.append("decrease_position_size")
    return recommendations


def deduplicate(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
