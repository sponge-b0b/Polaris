from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from json import dumps
from typing import Self

from intelligence.strategy.hypothesis.contracts import (
    Confidence,
    EvidenceReliability,
    EvidenceStrength,
    StrategyJsonScalar,
    StrategyPerspective,
    parse_strategy_perspective,
    validate_confidence,
    validate_evidence_strength,
    validate_reliability,
    validate_strategy_json_scalar,
)
from intelligence.strategy.hypothesis.serialization import require_serialized_list


class StrategyInvalidationOperator(StrEnum):
    """Supported deterministic invalidation comparison operators."""

    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "neq"


@dataclass(frozen=True, slots=True)
class StrategyEvidenceItem:
    """Attributable scalar observation used by a strategy hypothesis."""

    evidence_id: str
    source: str
    name: str
    observed_value: StrategyJsonScalar
    strength: EvidenceStrength
    reliability: EvidenceReliability
    supports: tuple[StrategyPerspective, ...] = ()
    contradicts: tuple[StrategyPerspective, ...] = ()
    explanation: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "evidence_id", _validate_non_empty(self.evidence_id, "evidence_id")
        )
        object.__setattr__(self, "source", _validate_non_empty(self.source, "source"))
        object.__setattr__(self, "name", _validate_non_empty(self.name, "name"))
        object.__setattr__(
            self,
            "observed_value",
            validate_strategy_json_scalar(
                self.observed_value, field_name="observed_value"
            ),
        )
        object.__setattr__(self, "strength", validate_evidence_strength(self.strength))
        object.__setattr__(self, "reliability", validate_reliability(self.reliability))
        object.__setattr__(
            self, "supports", _parse_perspectives(self.supports, "supports")
        )
        object.__setattr__(
            self, "contradicts", _parse_perspectives(self.contradicts, "contradicts")
        )
        if self.explanation is not None:
            object.__setattr__(
                self,
                "explanation",
                _validate_non_empty(self.explanation, "explanation"),
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "name": self.name,
            "observed_value": self.observed_value,
            "strength": self.strength,
            "reliability": self.reliability,
            "supports": [perspective.value for perspective in self.supports],
            "contradicts": [perspective.value for perspective in self.contradicts],
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            evidence_id=_required_string(payload, "evidence_id"),
            source=_required_string(payload, "source"),
            name=_required_string(payload, "name"),
            observed_value=_required_scalar(payload, "observed_value"),
            strength=_required_float(payload, "strength"),
            reliability=_required_float(payload, "reliability"),
            supports=_required_perspective_tuple(payload, "supports"),
            contradicts=_required_perspective_tuple(payload, "contradicts"),
            explanation=_optional_string(payload, "explanation"),
        )

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class StrategyAssumption:
    """Explicit assumption that a perspective requires to remain valid."""

    assumption_id: str
    perspective: StrategyPerspective
    description: str
    confidence: Confidence
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "assumption_id",
            _validate_non_empty(self.assumption_id, "assumption_id"),
        )
        object.__setattr__(
            self, "perspective", parse_strategy_perspective(self.perspective)
        )
        object.__setattr__(
            self, "description", _validate_non_empty(self.description, "description")
        )
        object.__setattr__(self, "confidence", validate_confidence(self.confidence))
        object.__setattr__(
            self,
            "evidence_ids",
            _validate_string_tuple(self.evidence_ids, "evidence_ids"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "assumption_id": self.assumption_id,
            "perspective": self.perspective.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            assumption_id=_required_string(payload, "assumption_id"),
            perspective=parse_strategy_perspective(
                _required_string(payload, "perspective")
            ),
            description=_required_string(payload, "description"),
            confidence=_required_float(payload, "confidence"),
            evidence_ids=_required_string_tuple(payload, "evidence_ids"),
        )

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True, slots=True)
class StrategyInvalidationCondition:
    """Deterministic scalar condition that invalidates a hypothesis."""

    condition_id: str
    perspective: StrategyPerspective
    description: str
    observed_value: StrategyJsonScalar
    operator: StrategyInvalidationOperator
    threshold: StrategyJsonScalar
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "condition_id", _validate_non_empty(self.condition_id, "condition_id")
        )
        object.__setattr__(
            self, "perspective", parse_strategy_perspective(self.perspective)
        )
        object.__setattr__(
            self, "description", _validate_non_empty(self.description, "description")
        )
        object.__setattr__(
            self,
            "observed_value",
            validate_strategy_json_scalar(
                self.observed_value, field_name="observed_value"
            ),
        )
        object.__setattr__(self, "operator", _parse_operator(self.operator))
        object.__setattr__(
            self,
            "threshold",
            validate_strategy_json_scalar(self.threshold, field_name="threshold"),
        )
        if self.evidence_id is not None:
            object.__setattr__(
                self,
                "evidence_id",
                _validate_non_empty(self.evidence_id, "evidence_id"),
            )
        evaluate_invalidation_operator(
            observed_value=self.observed_value,
            operator=self.operator,
            threshold=self.threshold,
        )

    def is_invalidated(self) -> bool:
        return evaluate_invalidation_operator(
            observed_value=self.observed_value,
            operator=self.operator,
            threshold=self.threshold,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "condition_id": self.condition_id,
            "perspective": self.perspective.value,
            "description": self.description,
            "observed_value": self.observed_value,
            "operator": self.operator.value,
            "threshold": self.threshold,
            "evidence_id": self.evidence_id,
            "invalidated": self.is_invalidated(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> Self:
        return cls(
            condition_id=_required_string(payload, "condition_id"),
            perspective=parse_strategy_perspective(
                _required_string(payload, "perspective")
            ),
            description=_required_string(payload, "description"),
            observed_value=_required_scalar(payload, "observed_value"),
            operator=_parse_operator(_required_string(payload, "operator")),
            threshold=_required_scalar(payload, "threshold"),
            evidence_id=_optional_string(payload, "evidence_id"),
        )

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_dict())


def evaluate_invalidation_operator(
    *,
    observed_value: StrategyJsonScalar,
    operator: StrategyInvalidationOperator,
    threshold: StrategyJsonScalar,
) -> bool:
    """Evaluate a deterministic invalidation operator against scalar values."""

    parsed_operator = _parse_operator(operator)
    if parsed_operator is StrategyInvalidationOperator.EQUAL:
        return observed_value == threshold
    if parsed_operator is StrategyInvalidationOperator.NOT_EQUAL:
        return observed_value != threshold

    observed_numeric = _numeric_scalar(observed_value, "observed_value")
    threshold_numeric = _numeric_scalar(threshold, "threshold")
    if parsed_operator is StrategyInvalidationOperator.GREATER_THAN:
        return observed_numeric > threshold_numeric
    if parsed_operator is StrategyInvalidationOperator.GREATER_THAN_OR_EQUAL:
        return observed_numeric >= threshold_numeric
    if parsed_operator is StrategyInvalidationOperator.LESS_THAN:
        return observed_numeric < threshold_numeric
    if parsed_operator is StrategyInvalidationOperator.LESS_THAN_OR_EQUAL:
        return observed_numeric <= threshold_numeric
    raise ValueError(f"unsupported invalidation operator: {parsed_operator.value}")


def _canonical_json(payload: dict[str, object]) -> str:
    return dumps(payload, sort_keys=True, separators=(",", ":"))


def _parse_operator(
    value: StrategyInvalidationOperator | str,
) -> StrategyInvalidationOperator:
    if isinstance(value, StrategyInvalidationOperator):
        return value
    try:
        return StrategyInvalidationOperator(value.strip().lower())
    except ValueError as exc:
        supported = ", ".join(
            operator.value for operator in StrategyInvalidationOperator
        )
        raise ValueError(f"invalidation operator must be one of: {supported}.") from exc


def _parse_perspectives(
    values: tuple[StrategyPerspective, ...] | tuple[str, ...],
    field_name: str,
) -> tuple[StrategyPerspective, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple.")
    return tuple(parse_strategy_perspective(value) for value in values)


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


def _numeric_scalar(value: StrategyJsonScalar, field_name: str) -> float:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        raise TypeError(f"{field_name} must be numeric for this invalidation operator.")
    return float(value)


def _required_string(payload: dict[str, object], field_name: str) -> str:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")
    return value


def _optional_string(payload: dict[str, object], field_name: str) -> str | None:
    value = payload.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string when provided.")
    return value


def _required_scalar(payload: dict[str, object], field_name: str) -> StrategyJsonScalar:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    return validate_strategy_json_scalar(payload[field_name], field_name=field_name)


def _required_float(payload: dict[str, object], field_name: str) -> float:
    if field_name not in payload:
        raise KeyError(f"missing required field: {field_name}")
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")
    return float(value)


def _required_string_tuple(
    payload: dict[str, object], field_name: str
) -> tuple[str, ...]:
    value = require_serialized_list(payload, field_name)
    return tuple(
        _validate_non_empty(_list_string(item, field_name), field_name)
        for item in value
    )


def _required_perspective_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[StrategyPerspective, ...]:
    value = require_serialized_list(payload, field_name)
    return tuple(
        parse_strategy_perspective(_list_string(item, field_name)) for item in value
    )


def _list_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} entries must be strings.")
    return value
