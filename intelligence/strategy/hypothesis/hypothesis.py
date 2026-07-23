from __future__ import annotations

from dataclasses import dataclass
from json import dumps
from typing import Self

from intelligence.strategy.hypothesis.contracts import (
    Confidence,
    DirectionalBias,
    HypothesisStrength,
    StrategyPerspective,
    parse_strategy_perspective,
    validate_confidence,
    validate_directional_bias,
    validate_hypothesis_strength,
)
from intelligence.strategy.hypothesis.evidence import (
    StrategyAssumption,
    StrategyEvidenceItem,
    StrategyInvalidationCondition,
)
from intelligence.strategy.hypothesis.serialization import require_serialized_list


@dataclass(frozen=True, slots=True)
class StrategyHypothesis:
    """Complete typed hypothesis produced by one strategy perspective."""

    perspective: StrategyPerspective
    thesis: str
    directional_bias: DirectionalBias
    hypothesis_strength: HypothesisStrength
    confidence: Confidence
    supporting_evidence: tuple[StrategyEvidenceItem, ...]
    contradicting_evidence: tuple[StrategyEvidenceItem, ...]
    key_assumptions: tuple[StrategyAssumption, ...]
    invalidation_conditions: tuple[StrategyInvalidationCondition, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    data_quality_flags: tuple[str, ...]
    evidence_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "perspective",
            parse_strategy_perspective(self.perspective),
        )
        object.__setattr__(self, "thesis", _validate_non_empty(self.thesis, "thesis"))
        object.__setattr__(
            self,
            "directional_bias",
            validate_directional_bias(self.directional_bias),
        )
        object.__setattr__(
            self,
            "hypothesis_strength",
            validate_hypothesis_strength(self.hypothesis_strength),
        )
        object.__setattr__(self, "confidence", validate_confidence(self.confidence))
        object.__setattr__(
            self,
            "supporting_evidence",
            _validate_evidence_tuple(self.supporting_evidence, "supporting_evidence"),
        )
        object.__setattr__(
            self,
            "contradicting_evidence",
            _validate_evidence_tuple(
                self.contradicting_evidence,
                "contradicting_evidence",
            ),
        )
        object.__setattr__(
            self,
            "key_assumptions",
            _validate_assumption_tuple(self.key_assumptions),
        )
        object.__setattr__(
            self,
            "invalidation_conditions",
            _validate_invalidation_tuple(self.invalidation_conditions),
        )
        object.__setattr__(self, "risks", _validate_string_tuple(self.risks, "risks"))
        object.__setattr__(
            self,
            "recommendations",
            _validate_string_tuple(self.recommendations, "recommendations"),
        )
        object.__setattr__(
            self,
            "data_quality_flags",
            _validate_string_tuple(self.data_quality_flags, "data_quality_flags"),
        )
        object.__setattr__(
            self,
            "evidence_fingerprint",
            _validate_non_empty(self.evidence_fingerprint, "evidence_fingerprint"),
        )

    @property
    def invalidated(self) -> bool:
        return any(
            condition.is_invalidated() for condition in self.invalidation_conditions
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "perspective": self.perspective.value,
            "thesis": self.thesis,
            "directional_bias": self.directional_bias,
            "hypothesis_strength": self.hypothesis_strength,
            "confidence": self.confidence,
            "supporting_evidence": [
                item.to_dict() for item in self.supporting_evidence
            ],
            "contradicting_evidence": [
                item.to_dict() for item in self.contradicting_evidence
            ],
            "key_assumptions": [item.to_dict() for item in self.key_assumptions],
            "invalidation_conditions": [
                item.to_dict() for item in self.invalidation_conditions
            ],
            "risks": list(self.risks),
            "recommendations": list(self.recommendations),
            "data_quality_flags": list(self.data_quality_flags),
            "evidence_fingerprint": self.evidence_fingerprint,
            "invalidated": self.invalidated,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            perspective=parse_strategy_perspective(
                _required_string(payload, "perspective")
            ),
            thesis=_required_string(payload, "thesis"),
            directional_bias=_required_float(payload, "directional_bias"),
            hypothesis_strength=_required_float(payload, "hypothesis_strength"),
            confidence=_required_float(payload, "confidence"),
            supporting_evidence=_required_evidence_tuple(
                payload,
                "supporting_evidence",
            ),
            contradicting_evidence=_required_evidence_tuple(
                payload,
                "contradicting_evidence",
            ),
            key_assumptions=_required_assumption_tuple(payload, "key_assumptions"),
            invalidation_conditions=_required_invalidation_tuple(
                payload,
                "invalidation_conditions",
            ),
            risks=_required_string_tuple(payload, "risks"),
            recommendations=_required_string_tuple(payload, "recommendations"),
            data_quality_flags=_required_string_tuple(payload, "data_quality_flags"),
            evidence_fingerprint=_required_string(payload, "evidence_fingerprint"),
        )

    def to_canonical_json(self) -> str:
        return dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _validate_non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def _validate_string_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple.")
    return tuple(_validate_non_empty(value, field_name) for value in values)


def _validate_evidence_tuple(
    values: tuple[StrategyEvidenceItem, ...],
    field_name: str,
) -> tuple[StrategyEvidenceItem, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple.")
    for value in values:
        if not isinstance(value, StrategyEvidenceItem):
            raise TypeError(
                f"{field_name} entries must be StrategyEvidenceItem instances."
            )
    return values


def _validate_assumption_tuple(
    values: tuple[StrategyAssumption, ...],
) -> tuple[StrategyAssumption, ...]:
    if not isinstance(values, tuple):
        raise TypeError("key_assumptions must be a tuple.")
    for value in values:
        if not isinstance(value, StrategyAssumption):
            raise TypeError(
                "key_assumptions entries must be StrategyAssumption instances."
            )
    return values


def _validate_invalidation_tuple(
    values: tuple[StrategyInvalidationCondition, ...],
) -> tuple[StrategyInvalidationCondition, ...]:
    if not isinstance(values, tuple):
        raise TypeError("invalidation_conditions must be a tuple.")
    for value in values:
        if not isinstance(value, StrategyInvalidationCondition):
            raise TypeError(
                "invalidation_conditions entries must be "
                "StrategyInvalidationCondition instances."
            )
    return values


def _required_string(payload: dict[str, object], field_name: str) -> str:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    return value


def _required_float(payload: dict[str, object], field_name: str) -> float:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")
    return float(value)


def _required_string_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[str, ...]:
    value = require_serialized_list(payload, field_name)
    return tuple(_list_string(item, field_name) for item in value)


def _required_evidence_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyEvidenceItem, ...]:
    value = _required_list(payload, field_name)
    return tuple(StrategyEvidenceItem.from_dict(item) for item in value)


def _required_assumption_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyAssumption, ...]:
    value = _required_list(payload, field_name)
    return tuple(StrategyAssumption.from_dict(item) for item in value)


def _required_invalidation_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyInvalidationCondition, ...]:
    value = _required_list(payload, field_name)
    return tuple(StrategyInvalidationCondition.from_dict(item) for item in value)


def _required_list(
    payload: dict[str, object],
    field_name: str,
) -> list[dict[str, object]]:
    value = require_serialized_list(payload, field_name)
    return [_list_mapping(item, field_name) for item in value]


def _list_mapping(value: object, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} entries must be dictionaries.")
    return {str(key): mapped_value for key, mapped_value in value.items()}


def _list_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} entries must be strings.")
    return _validate_non_empty(value, field_name)
