from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

from application.services.backtesting.backtest_request import (
    BacktestExpectedOutcome,
    BacktestScenario,
)
from application.services.backtesting.backtest_result import (
    BacktestMetrics,
    BacktestOutcomeVerification,
    BacktestStepResult,
)

_NODE_ALIASES = {
    "technical": "technical_agent",
    "risk": "risk_aggregator_agent",
    "strategy": "strategy_synthesis_agent",
    "portfolio_state": "portfolio_state_builder",
}


def verify_backtest_outcomes(
    *,
    scenario: BacktestScenario,
    steps: tuple[BacktestStepResult, ...],
    metrics: BacktestMetrics,
) -> tuple[BacktestOutcomeVerification, ...]:
    """Evaluate declared scenario expectations against deterministic run results."""

    if not scenario.expected_outcomes:
        return ()

    payload = _verification_payload(
        steps=steps,
        metrics=metrics,
    )
    return tuple(
        _verify_outcome(
            outcome,
            payload=payload,
        )
        for outcome in scenario.expected_outcomes
    )


def _verification_payload(  # noqa: C901
    *,
    steps: tuple[BacktestStepResult, ...],
    metrics: BacktestMetrics,
) -> dict[str, object]:
    final_step = steps[-1] if steps else None
    final_node_outputs = dict(final_step.node_outputs) if final_step is not None else {}
    payload: dict[str, object] = {
        "metrics": _metrics_payload(metrics),
        "steps": tuple(_step_payload(step) for step in steps),
        "node_outputs": final_node_outputs,
    }

    if final_step is not None:
        snapshot = final_step.portfolio_snapshot
        payload["portfolio"] = {
            "timestamp": snapshot.timestamp,
            "cash": snapshot.cash,
            "equity": snapshot.equity,
            "market_value": snapshot.market_value,
            "positions": snapshot.positions,
        }

    for alias, node_name in _NODE_ALIASES.items():
        node_payload = _node_payload(final_node_outputs.get(node_name))
        if node_payload is not None:
            payload[alias] = node_payload

    technical = payload.get("technical")
    if isinstance(technical, Mapping):
        breadth = technical.get("breadth_state", technical.get("breadth"))
        if breadth is not None:
            payload["breadth"] = breadth

    trade = _node_payload(final_node_outputs.get("trade_packager"))
    if trade is not None:
        features = trade.get("features")
        if isinstance(features, Mapping) and "trade_intent" in features:
            payload["trade"] = features["trade_intent"]
            payload["trade_recommendation"] = features["trade_intent"]
        else:
            payload["trade"] = trade
            payload["trade_recommendation"] = trade

    execution = _node_payload(final_node_outputs.get("execution_risk_guard"))
    if execution is not None:
        features = execution.get("features")
        if isinstance(features, Mapping) and "execution_guard" in features:
            payload["execution_risk"] = features["execution_guard"]
        else:
            payload["execution_risk"] = execution

    for node_name, node_output in final_node_outputs.items():
        node_payload = _node_payload(node_output)
        if node_payload is not None:
            payload.setdefault(str(node_name), node_payload)

    return payload


def _metrics_payload(metrics: BacktestMetrics) -> dict[str, Decimal]:
    return {
        "total_return": metrics.total_return,
        "annualized_return": metrics.annualized_return,
        "volatility": metrics.volatility,
        "max_drawdown": metrics.max_drawdown,
        "sharpe_ratio": metrics.sharpe_ratio,
        "sortino_ratio": metrics.sortino_ratio,
        "win_rate": metrics.win_rate,
        "profit_factor": metrics.profit_factor,
        "exposure": metrics.exposure,
        "turnover": metrics.turnover,
        "benchmark_relative_return": metrics.benchmark_relative_return,
    }


def _step_payload(step: BacktestStepResult) -> dict[str, object]:
    return {
        "timestamp": step.timestamp,
        "workflow_run_id": step.workflow_run_id,
        "success": step.success,
        "node_outputs": step.node_outputs,
        "portfolio": {
            "timestamp": step.portfolio_snapshot.timestamp,
            "cash": step.portfolio_snapshot.cash,
            "equity": step.portfolio_snapshot.equity,
            "market_value": step.portfolio_snapshot.market_value,
            "positions": step.portfolio_snapshot.positions,
        },
        "simulated_fills": step.simulated_fills,
    }


def _node_payload(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None

    outputs = value.get("outputs", value)
    if not isinstance(outputs, Mapping):
        return None

    features = outputs.get("features")
    if isinstance(features, Mapping):
        return {
            **dict(outputs),
            **dict(features),
        }
    return dict(outputs)


def _verify_outcome(
    outcome: BacktestExpectedOutcome,
    *,
    payload: Mapping[str, object],
) -> BacktestOutcomeVerification:
    try:
        actual = _resolve_target(
            payload,
            outcome.target,
        )
        passed = _matches_expectation(
            actual=actual,
            outcome=outcome,
        )
        detail = None if passed else "actual value did not satisfy expectation"
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        actual = None
        passed = False
        detail = str(exc)

    return BacktestOutcomeVerification(
        target=outcome.target,
        expectation_type=outcome.expectation_type,
        expected=outcome.expected,
        actual=actual,
        tolerance=outcome.tolerance,
        passed=passed,
        detail=detail,
    )


def _resolve_target(
    payload: Mapping[str, object],
    target: str,
) -> object:
    current: object = payload
    for segment in target.split("."):
        if isinstance(current, Mapping):
            if segment not in current:
                raise KeyError(f"target segment not found: {segment}")
            current = current[segment]
            continue
        if isinstance(current, Sequence) and not isinstance(
            current,
            (str, bytes, bytearray),
        ):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError) as exc:
                raise IndexError(f"invalid sequence target segment: {segment}") from exc
            continue
        raise TypeError(f"target segment is not traversable: {segment}")
    return current


def _matches_expectation(  # noqa: C901
    *,
    actual: object,
    outcome: BacktestExpectedOutcome,
) -> bool:
    expectation_type = outcome.expectation_type
    expected = outcome.expected

    if expectation_type == "equals":
        numeric = _numeric_pair(actual, expected)
        return numeric[0] == numeric[1] if numeric is not None else actual == expected

    if expectation_type == "contains":
        if isinstance(actual, Mapping):
            return expected in actual
        if isinstance(actual, Sequence):
            return expected in actual
        raise TypeError("contains expectation requires a mapping or sequence")

    if expectation_type == "between":
        if not isinstance(expected, Sequence) or isinstance(
            expected,
            (str, bytes, bytearray),
        ):
            raise TypeError("between expectation requires a two-value sequence")
        if len(expected) != 2:
            raise ValueError("between expectation requires exactly two values")
        actual_value = _decimal(actual)
        lower = _decimal(expected[0])
        upper = _decimal(expected[1])
        return lower <= actual_value <= upper

    actual_value = _decimal(actual)
    expected_value = _decimal(expected)
    if expectation_type == "approx":
        if outcome.tolerance is None:
            raise ValueError("approx expectation requires tolerance")
        return abs(actual_value - expected_value) <= outcome.tolerance
    if expectation_type == "min":
        return actual_value >= expected_value
    if expectation_type == "max":
        return actual_value <= expected_value

    raise ValueError(f"unsupported expectation type: {expectation_type}")


def _numeric_pair(
    left: object,
    right: object,
) -> tuple[Decimal, Decimal] | None:
    try:
        return _decimal(left), _decimal(right)
    except (TypeError, ValueError):
        return None


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float, str)):
        raise TypeError(f"numeric expectation received non-numeric value: {value!r}")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc
