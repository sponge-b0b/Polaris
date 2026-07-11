from __future__ import annotations

from collections.abc import Mapping

from intelligence.analysts.technical.technical_breadth_context import (
    TechnicalBreadthContext,
)
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.context import StrategyEvidenceInputStatus
from intelligence.strategy.hypothesis.contracts import StrategyPerspective
from intelligence.strategy.hypothesis.evidence import StrategyEvidenceItem


def evidence_for_perspective(
    evidence_context: StrategyEvidenceContext,
    perspective: StrategyPerspective,
    *,
    support: bool,
) -> tuple[StrategyEvidenceItem, ...]:
    return tuple(
        item
        for item in evidence_context.all_evidence
        if perspective in (item.supports if support else item.contradicts)
    )


def data_quality_flags(
    evidence_context: StrategyEvidenceContext,
) -> tuple[str, ...]:
    flags = [
        f"{quality.input_name}:{quality.status.value}"
        for quality in evidence_context.input_quality
        if quality.status is not StrategyEvidenceInputStatus.AVAILABLE
    ]
    return tuple(flags)


def breadth_context_from_evidence(
    evidence: Mapping[str, StrategyEvidenceItem],
) -> TechnicalBreadthContext:
    if "technical.breadth.confirmation_score" not in evidence:
        return TechnicalBreadthContext.unavailable()

    confirmation_score = numeric_evidence_value(
        evidence, "technical.breadth.confirmation_score"
    )
    risk_pressure = numeric_evidence_value(evidence, "technical.breadth.risk_pressure")
    participation_score = numeric_evidence_value(
        evidence, "technical.breadth.participation_score"
    )
    leadership_score = numeric_evidence_value(
        evidence, "technical.breadth.leadership_score"
    )
    return TechnicalBreadthContext(
        has_breadth_data=True,
        breadth_regime=breadth_regime(confirmation_score),
        risk_regime=risk_regime(risk_pressure),
        breadth_score=confirmation_score,
        breadth_risk_score=risk_pressure,
        participation_score=participation_score,
        leadership_score=leadership_score,
    )


def breadth_regime(confirmation_score: float) -> str:
    if confirmation_score >= 0.25:
        return "strong_breadth"
    if confirmation_score <= -0.25:
        return "weak_breadth"
    return "neutral_breadth"


def risk_regime(risk_pressure: float) -> str:
    if risk_pressure >= 0.65:
        return "elevated"
    if risk_pressure <= 0.40:
        return "stable"
    return "neutral"


def numeric_evidence_value(
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


def string_evidence_value(
    evidence: Mapping[str, StrategyEvidenceItem],
    evidence_id: str,
    *,
    default: str,
) -> str:
    item = evidence.get(evidence_id)
    if item is None or not isinstance(item.observed_value, str):
        return default
    return item.observed_value


def evidence_reliability(
    evidence: Mapping[str, StrategyEvidenceItem],
    evidence_id: str,
    *,
    default: float = 0.0,
) -> float:
    item = evidence.get(evidence_id)
    if item is None:
        return default
    return item.reliability


def deduplicate_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
