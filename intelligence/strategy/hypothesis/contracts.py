from __future__ import annotations

from enum import Enum
from math import isfinite
from typing import TypeAlias


class StrategyPerspective(str, Enum):
    """Canonical independent strategy hypothesis perspectives."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"


StrategyJsonScalar: TypeAlias = str | int | float | bool | None
DirectionalBias: TypeAlias = float
HypothesisStrength: TypeAlias = float
Confidence: TypeAlias = float
EvidenceStrength: TypeAlias = float
EvidenceReliability: TypeAlias = float


def parse_strategy_perspective(
    value: StrategyPerspective | str,
) -> StrategyPerspective:
    """Normalize and validate a strategy perspective value."""

    if isinstance(value, StrategyPerspective):
        return value

    normalized = value.strip().lower()
    try:
        return StrategyPerspective(normalized)
    except ValueError as exc:
        supported = ", ".join(perspective.value for perspective in StrategyPerspective)
        raise ValueError(f"strategy perspective must be one of: {supported}.") from exc


def validate_directional_bias(
    value: float,
    *,
    field_name: str = "directional_bias",
) -> DirectionalBias:
    return _validate_float_range(
        value,
        field_name=field_name,
        lower=-1.0,
        upper=1.0,
    )


def validate_hypothesis_strength(
    value: float,
    *,
    field_name: str = "hypothesis_strength",
) -> HypothesisStrength:
    return _validate_unit_interval(value, field_name=field_name)


def validate_confidence(
    value: float,
    *,
    field_name: str = "confidence",
) -> Confidence:
    return _validate_unit_interval(value, field_name=field_name)


def validate_evidence_strength(
    value: float,
    *,
    field_name: str = "evidence_strength",
) -> EvidenceStrength:
    return _validate_unit_interval(value, field_name=field_name)


def validate_reliability(
    value: float,
    *,
    field_name: str = "reliability",
) -> EvidenceReliability:
    return _validate_unit_interval(value, field_name=field_name)


def validate_strategy_json_scalar(
    value: object,
    *,
    field_name: str = "value",
) -> StrategyJsonScalar:
    """Validate JSON-compatible scalar evidence values.

    Strategy evidence may carry scalar observed values or scalar invalidation
    thresholds. Containers must be modeled structurally instead of hidden inside
    generic dictionaries or lists.
    """

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{field_name} must be finite.")
        return value
    raise TypeError(
        f"{field_name} must be a JSON-compatible scalar: str, int, float, bool, or None."
    )


def _validate_unit_interval(
    value: float,
    *,
    field_name: str,
) -> float:
    return _validate_float_range(
        value,
        field_name=field_name,
        lower=0.0,
        upper=1.0,
    )


def _validate_float_range(
    value: float,
    *,
    field_name: str,
    lower: float,
    upper: float,
) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not boolean.")

    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{field_name} must be finite.")
    if numeric < lower or numeric > upper:
        raise ValueError(f"{field_name} must be between {lower} and {upper}.")
    return numeric
