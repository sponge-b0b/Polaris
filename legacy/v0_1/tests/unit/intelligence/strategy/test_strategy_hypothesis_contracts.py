from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from intelligence.strategy.hypothesis import (
    StrategyPerspective,
    parse_strategy_perspective,
    validate_confidence,
    validate_directional_bias,
    validate_evidence_strength,
    validate_hypothesis_strength,
    validate_reliability,
    validate_strategy_json_scalar,
)

UnitValidator = Callable[[float], float]


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("bull", StrategyPerspective.BULL),
        (" BEAR ", StrategyPerspective.BEAR),
        ("sideways", StrategyPerspective.SIDEWAYS),
        (StrategyPerspective.BULL, StrategyPerspective.BULL),
    ),
)
def test_parse_strategy_perspective_accepts_canonical_values(
    raw: StrategyPerspective | str,
    expected: StrategyPerspective,
) -> None:
    assert parse_strategy_perspective(raw) is expected


@pytest.mark.parametrize("raw", ("", "neutral", "risk_on", "bullish"))
def test_parse_strategy_perspective_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError, match="strategy perspective"):
        parse_strategy_perspective(raw)


@pytest.mark.parametrize("value", (-1.0, -0.25, 0.0, 0.75, 1.0))
def test_directional_bias_accepts_negative_to_positive_unit_range(
    value: float,
) -> None:
    assert validate_directional_bias(value) == value


@pytest.mark.parametrize("value", (-1.000001, 1.000001, math.inf, -math.inf, math.nan))
def test_directional_bias_rejects_out_of_range_or_nonfinite_values(
    value: float,
) -> None:
    with pytest.raises(ValueError):
        validate_directional_bias(value)


@pytest.mark.parametrize(
    "validator",
    (
        validate_hypothesis_strength,
        validate_confidence,
        validate_evidence_strength,
        validate_reliability,
    ),
)
def test_unit_interval_strategy_scalars_accept_zero_to_one(
    validator: UnitValidator,
) -> None:
    assert validator(0.0) == 0.0
    assert validator(0.5) == 0.5
    assert validator(1.0) == 1.0


@pytest.mark.parametrize("value", (-0.000001, 1.000001, math.inf, math.nan))
@pytest.mark.parametrize(
    "validator",
    (
        validate_hypothesis_strength,
        validate_confidence,
        validate_evidence_strength,
        validate_reliability,
    ),
)
def test_unit_interval_strategy_scalars_reject_invalid_values(
    validator: UnitValidator,
    value: float,
) -> None:
    with pytest.raises(ValueError):
        validator(value)


@pytest.mark.parametrize(
    "value",
    (
        "headline",
        42,
        3.14,
        True,
        False,
        None,
    ),
)
def test_strategy_json_scalar_accepts_json_scalar_values(value: object) -> None:
    assert validate_strategy_json_scalar(value) == value


@pytest.mark.parametrize(
    "value",
    (
        {"nested": "mapping"},
        ["list"],
        ("tuple",),
        math.inf,
        math.nan,
    ),
)
def test_strategy_json_scalar_rejects_containers_and_nonfinite_numbers(
    value: object,
) -> None:
    expected_error = ValueError if isinstance(value, float) else TypeError
    with pytest.raises(expected_error):
        validate_strategy_json_scalar(value)


@pytest.mark.parametrize(
    "validator",
    (
        validate_directional_bias,
        validate_hypothesis_strength,
        validate_confidence,
        validate_evidence_strength,
        validate_reliability,
    ),
)
def test_numeric_strategy_scalar_validators_reject_boolean_values(
    validator: UnitValidator,
) -> None:
    with pytest.raises(TypeError):
        validator(True)
