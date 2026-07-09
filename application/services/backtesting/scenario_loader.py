from __future__ import annotations

import importlib
import json

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Mapping
from typing import cast

from application.services.backtesting.backtest_request import (
    BacktestExpectedOutcome,
)
from application.services.backtesting.backtest_request import BacktestExpectationType
from application.services.backtesting.backtest_request import (
    BacktestInitialPosition,
)
from application.services.backtesting.backtest_request import BacktestScenario


def load_backtest_scenario(
    path: str | Path,
) -> BacktestScenario:
    """
    Load a backtest scenario from a JSON or YAML boundary document.
    """

    scenario_path = Path(path)
    payload = _load_mapping(
        scenario_path,
    )
    return backtest_scenario_from_mapping(
        payload,
    )


def backtest_scenario_from_mapping(
    payload: Mapping[str, object],
) -> BacktestScenario:
    """
    Convert an untrusted boundary mapping into a typed scenario object.
    """

    initial_positions = tuple(
        _initial_position_from_mapping(position)
        for position in _mapping_sequence(payload.get("initial_positions", ()))
    )
    expected_outcomes = tuple(
        _expected_outcome_from_mapping(expected_outcome)
        for expected_outcome in _mapping_sequence(payload.get("expected_outcomes", ()))
    )

    scenario = BacktestScenario(
        scenario_id=str(payload.get("scenario_id", "")),
        name=str(payload.get("name", "")),
        workflow_name=str(payload.get("workflow_name", "")),
        start_date=_parse_date(payload.get("start_date")),
        end_date=_parse_date(payload.get("end_date")),
        symbols=tuple(
            str(symbol) for symbol in _object_sequence(payload.get("symbols", ()))
        ),
        benchmark_symbol=str(payload.get("benchmark_symbol", "")),
        initial_cash=_parse_decimal(payload.get("initial_cash", "0")),
        provider_profile=str(payload.get("provider_profile", "backtest_synthetic")),
        initial_positions=initial_positions,
        parameters=_object_mapping(payload.get("parameters", {})),
        expected_outcomes=expected_outcomes,
    )

    errors = scenario.validate()
    if errors:
        raise ValueError(
            "Invalid backtest scenario: " + "; ".join(errors),
        )

    return scenario


def _load_mapping(
    path: Path,
) -> Mapping[str, object]:
    if path.suffix.lower() == ".json":
        raw_payload = json.loads(
            path.read_text(encoding="utf-8"),
        )
    elif path.suffix.lower() in {".yaml", ".yml"}:
        yaml_loader = importlib.import_module("yaml")
        raw_payload = yaml_loader.safe_load(
            path.read_text(encoding="utf-8"),
        )
    else:
        raise ValueError(
            f"Unsupported backtest scenario file type: {path.suffix}",
        )

    if not isinstance(raw_payload, Mapping):
        raise ValueError("Backtest scenario file must contain a mapping.")

    return raw_payload


def _initial_position_from_mapping(
    payload: Mapping[str, object],
) -> BacktestInitialPosition:
    return BacktestInitialPosition(
        symbol=str(payload.get("symbol", "")),
        quantity=_parse_decimal(payload.get("quantity", "0")),
        average_price=_parse_decimal(payload.get("average_price", "0")),
    )


def _expected_outcome_from_mapping(
    payload: Mapping[str, object],
) -> BacktestExpectedOutcome:
    tolerance_value = payload.get("tolerance")
    tolerance = None if tolerance_value is None else _parse_decimal(tolerance_value)
    expectation_type_value = str(payload.get("expectation_type", "equals"))
    allowed_expectation_types = {
        "equals",
        "approx",
        "min",
        "max",
        "between",
        "contains",
    }
    if expectation_type_value not in allowed_expectation_types:
        raise ValueError(
            f"Unsupported backtest expectation type: {expectation_type_value}",
        )

    return BacktestExpectedOutcome(
        target=str(payload.get("target", "")),
        expectation_type=cast(BacktestExpectationType, expectation_type_value),
        expected=payload.get("expected"),
        tolerance=tolerance,
    )


def _object_sequence(
    value: object,
) -> tuple[object, ...]:
    if value is None:
        return ()

    if not isinstance(value, list | tuple):
        raise ValueError("Expected a sequence.")

    return tuple(value)


def _mapping_sequence(
    value: object,
) -> tuple[Mapping[str, object], ...]:
    if value is None:
        return ()

    if not isinstance(value, list | tuple):
        raise ValueError("Expected a sequence of mappings.")

    mappings: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("Expected a sequence of mappings.")
        mappings.append(item)

    return tuple(mappings)


def _object_mapping(
    value: object,
) -> Mapping[str, object]:
    if value is None:
        return {}

    if not isinstance(value, Mapping):
        raise ValueError("Expected a mapping.")

    return value


def _parse_date(
    value: object,
) -> date:
    if isinstance(value, date):
        return value

    if isinstance(value, str):
        return date.fromisoformat(value)

    raise ValueError("Expected ISO date value.")


def _parse_decimal(
    value: object,
) -> Decimal:
    return Decimal(str(value))
