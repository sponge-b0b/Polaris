from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from domain.workflow_outputs import (
    STRATEGY_PERSPECTIVE_WEIGHTS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)
from intelligence.strategy.hypothesis.context import StrategyEvidenceContext
from intelligence.strategy.hypothesis.contracts import validate_confidence
from intelligence.strategy.hypothesis.runtime import (
    strategy_evidence_context_from_node_outputs,
)


@dataclass(frozen=True, slots=True)
class StrategyPerspectiveWeights:
    """Deterministic perspective weights derived from the shared strategy evidence."""

    bull_weight: float
    bear_weight: float
    sideways_weight: float
    confidence: float
    evidence_fingerprint: str
    features: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "bull_weight", _validate_weight(self.bull_weight))
        object.__setattr__(self, "bear_weight", _validate_weight(self.bear_weight))
        object.__setattr__(
            self, "sideways_weight", _validate_weight(self.sideways_weight)
        )
        object.__setattr__(self, "confidence", validate_confidence(self.confidence))
        if not self.evidence_fingerprint.strip():
            raise ValueError("evidence_fingerprint must not be empty.")
        total = self.bull_weight + self.bear_weight + self.sideways_weight
        if abs(total - 1.0) > 1e-12:
            raise ValueError("strategy perspective weights must sum to 1.0.")

    def to_dict(self) -> dict[str, object]:
        return {
            "bull_weight": self.bull_weight,
            "bear_weight": self.bear_weight,
            "sideways_weight": self.sideways_weight,
            "confidence": self.confidence,
            "evidence_fingerprint": self.evidence_fingerprint,
            "features": dict(self.features),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        features = payload.get("features")
        return cls(
            bull_weight=_required_float(payload.get("bull_weight"), "bull_weight"),
            bear_weight=_required_float(payload.get("bear_weight"), "bear_weight"),
            sideways_weight=_required_float(
                payload.get("sideways_weight"),
                "sideways_weight",
            ),
            confidence=_required_float(payload.get("confidence"), "confidence"),
            evidence_fingerprint=str(payload.get("evidence_fingerprint", "")),
            features=dict(features) if isinstance(features, Mapping) else {},
        )


class StrategyPerspectiveWeightingEngine(RuntimeNode):
    """
    Compute deterministic strategy-perspective weights from StrategyEvidenceContext.
    """

    node_name = "strategy_perspective_weighting_engine"
    node_type = "strategy_perspective_weighting_engine"

    async def _execute(self, context: RuntimeContext) -> RuntimeNodeOutput:
        evidence_context = strategy_evidence_context_from_node_outputs(
            context.node_outputs,
            consumer_name="StrategyPerspectiveWeightingEngine",
        )
        perspective_weights = calculate_strategy_perspective_weights(evidence_context)
        features = dict(perspective_weights.features)
        features.update(
            {
                "bull_weight": perspective_weights.bull_weight,
                "bear_weight": perspective_weights.bear_weight,
                "sideways_weight": perspective_weights.sideways_weight,
                "evidence_fingerprint": perspective_weights.evidence_fingerprint,
            }
        )

        return RuntimeNodeOutput.success_output(
            outputs={
                "directional_score": 0.0,
                "confidence": perspective_weights.confidence,
                "regime": "strategy_perspective_weighting",
                "signals": [
                    "strategy_perspective_weights_computed",
                    "shared_evidence_context_applied",
                ],
                "risks": list(_perspective_weight_risks(features)),
                "recommendations": [
                    "use perspective weights only as pre-hypothesis perspective inputs",
                    "do not interpret perspective weights as final strategy selection",
                ],
                "strategy_perspective_weights": perspective_weights.to_dict(),
                "features": features,
            },
            execution_metadata={
                "node_name": self.node_name,
                "node_type": self.node_type,
                "confidence": perspective_weights.confidence,
                "evidence_fingerprint": perspective_weights.evidence_fingerprint,
            },
            output_contract=STRATEGY_PERSPECTIVE_WEIGHTS_OUTPUT_CONTRACT,
            output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        )


def calculate_strategy_perspective_weights(
    evidence_context: StrategyEvidenceContext,
) -> StrategyPerspectiveWeights:
    """
    Calculate normalized bull/bear/sideways perspective weights from shared evidence.
    """

    evidence = evidence_context.evidence_by_id()
    sentiment_directional = _numeric_value(evidence, "sentiment.directional_score")
    technical_directional = _numeric_value(evidence, "technical.directional_score")
    fundamental_directional = _numeric_value(evidence, "fundamental.directional_score")
    news_directional = _numeric_value(evidence, "news.directional_score")
    macro_directional = _numeric_value(evidence, "macro.directional_score")
    market_event_pressure = _numeric_value(evidence, "market_events.pressure")
    breadth_confirmation = _numeric_value(
        evidence,
        "technical.breadth.confirmation_score",
    )
    risk_pressure = _clamp_01(_numeric_value(evidence, "risk.pressure"))
    trend_strength = _clamp_01(_numeric_value(evidence, "technical.trend_strength"))
    volatility_score = _clamp_01(_numeric_value(evidence, "technical.volatility_score"))

    directional_input = _weighted_average(
        (
            (technical_directional, 0.35),
            (sentiment_directional, 0.25),
            (fundamental_directional, 0.15),
            (news_directional, 0.10),
            (macro_directional, 0.10),
            (market_event_pressure, 0.05),
        )
    )
    confidence = _weighted_average(
        (
            (_reliability(evidence, "technical.directional_score"), 0.35),
            (_reliability(evidence, "sentiment.directional_score"), 0.25),
            (_reliability(evidence, "fundamental.directional_score"), 0.15),
            (_reliability(evidence, "news.directional_score"), 0.10),
            (_reliability(evidence, "macro.directional_score"), 0.10),
            (_reliability(evidence, "market_events.pressure"), 0.05),
        ),
        default=0.0,
    )

    directional_conviction = min(1.0, abs(directional_input))
    contained_directionality = 1.0 - directional_conviction

    bull_raw = (
        1.0
        + max(0.0, directional_input) * 0.85
        + max(0.0, breadth_confirmation) * 0.20
        + max(0.0, macro_directional) * 0.10
        + max(0.0, market_event_pressure) * 0.10
    )
    bear_raw = (
        1.0
        + max(0.0, -directional_input) * 0.85
        + max(0.0, -breadth_confirmation) * 0.20
        + risk_pressure * 0.30
        + volatility_score * 0.15
        + max(0.0, -macro_directional) * 0.10
        + max(0.0, -market_event_pressure) * 0.10
    )
    sideways_raw = (
        1.0
        + contained_directionality * 0.50
        + (1.0 - trend_strength) * 0.25
        + (1.0 - volatility_score) * 0.15
        + (1.0 - risk_pressure) * 0.10
    )

    risk_dampener = 1.0 - risk_pressure * 0.20
    bull_raw *= risk_dampener
    sideways_raw *= 1.0 - min(0.35, trend_strength * directional_conviction * 0.35)

    bull_weight, bear_weight, sideways_weight = _normalize_weights(
        bull_raw,
        bear_raw,
        sideways_raw,
    )
    features = {
        "directional_input": directional_input,
        "confidence_input": confidence,
        "sentiment_directional": sentiment_directional,
        "technical_directional": technical_directional,
        "fundamental_directional": fundamental_directional,
        "news_directional": news_directional,
        "macro_directional": macro_directional,
        "market_event_pressure": market_event_pressure,
        "breadth_confirmation_score": breadth_confirmation,
        "risk_pressure": risk_pressure,
        "trend_strength": trend_strength,
        "volatility_score": volatility_score,
        "directional_conviction": directional_conviction,
        "contained_directionality": contained_directionality,
        "raw_weights": {
            "bull": bull_raw,
            "bear": bear_raw,
            "sideways": sideways_raw,
        },
        "weights_sum": bull_weight + bear_weight + sideways_weight,
    }
    return StrategyPerspectiveWeights(
        bull_weight=bull_weight,
        bear_weight=bear_weight,
        sideways_weight=sideways_weight,
        confidence=confidence,
        evidence_fingerprint=evidence_context.evidence_fingerprint(),
        features=features,
    )


def _perspective_weight_risks(features: Mapping[str, object]) -> tuple[str, ...]:
    risks = ["pre_hypothesis_perspective_weights_only"]
    risk_pressure = features.get("risk_pressure", 0.0)
    volatility_score = features.get("volatility_score", 0.0)
    if isinstance(risk_pressure, (int, float)) and not isinstance(risk_pressure, bool):
        if risk_pressure > 0.65:
            risks.append("elevated_risk_pressure_affects_perspective_weights")
    if isinstance(volatility_score, (int, float)) and not isinstance(
        volatility_score,
        bool,
    ):
        if volatility_score > 0.75:
            risks.append("elevated_volatility_affects_perspective_weights")
    return tuple(risks)


def _numeric_value(
    evidence: Mapping[str, object],
    evidence_id: str,
    *,
    default: float = 0.0,
) -> float:
    item = evidence.get(evidence_id)
    observed_value = getattr(item, "observed_value", None)
    if isinstance(observed_value, bool):
        return default
    if isinstance(observed_value, (int, float)):
        return float(observed_value)
    return default


def _reliability(
    evidence: Mapping[str, object],
    evidence_id: str,
    *,
    default: float = 0.0,
) -> float:
    item = evidence.get(evidence_id)
    reliability = getattr(item, "reliability", None)
    if isinstance(reliability, bool):
        return default
    if isinstance(reliability, (int, float)):
        return float(reliability)
    return default


def _weighted_average(
    weighted_values: tuple[tuple[float, float], ...],
    *,
    default: float = 0.0,
) -> float:
    total_weight = sum(weight for _, weight in weighted_values if weight > 0.0)
    if total_weight == 0.0:
        return default
    return sum(value * weight for value, weight in weighted_values) / total_weight


def _normalize_weights(
    bull: float,
    bear: float,
    sideways: float,
) -> tuple[float, float, float]:
    raw_bull = max(0.0, bull)
    raw_bear = max(0.0, bear)
    raw_sideways = max(0.0, sideways)
    total = raw_bull + raw_bear + raw_sideways
    if total == 0.0:
        return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    bull_weight = raw_bull / total
    bear_weight = raw_bear / total
    sideways_weight = 1.0 - bull_weight - bear_weight
    return (bull_weight, bear_weight, sideways_weight)


def _validate_weight(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("strategy perspective weight must be numeric.")
    numeric = float(value)
    if numeric < 0.0 or numeric > 1.0:
        raise ValueError("strategy perspective weight must be between 0.0 and 1.0.")
    return numeric


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _required_float(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError(f"{field_name} must be numeric.")
    return float(value)
