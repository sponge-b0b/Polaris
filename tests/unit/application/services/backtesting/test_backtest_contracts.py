from __future__ import annotations

from collections.abc import Mapping

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any
from typing import cast

import pytest

from application.services.backtesting import BacktestApplicationService
from application.services.backtesting import BacktestExpectedOutcome
from application.services.backtesting import BacktestInitialPosition
from application.services.backtesting import BacktestRunRequest
from application.services.backtesting import BacktestScenario
from application.services.backtesting import backtest_scenario_from_mapping
from application.services.backtesting import load_backtest_scenario
from application.services.base import ServiceRequest


def test_backtest_scenario_validates_and_serializes_deterministic_expectations() -> (
    None
):
    scenario = BacktestScenario(
        scenario_id="deterministic-risk-check",
        name="Deterministic risk check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 5),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000.00"),
        initial_positions=(
            BacktestInitialPosition(
                symbol="SPY",
                quantity=Decimal("10"),
                average_price=Decimal("500.25"),
            ),
        ),
        expected_outcomes=(
            BacktestExpectedOutcome(
                target="technical.regime.directional_technical_score",
                expectation_type="approx",
                expected="0.75",
                tolerance=Decimal("0.0001"),
            ),
        ),
    )

    assert scenario.validate() == ()

    payload = scenario.to_dict()
    assert payload["initial_cash"] == "100000.00"
    assert payload["expected_outcomes"] == [
        {
            "target": "technical.regime.directional_technical_score",
            "expectation_type": "approx",
            "expected": "0.75",
            "tolerance": "0.0001",
        }
    ]


def test_backtest_scenario_rejects_invalid_date_range() -> None:
    scenario = BacktestScenario(
        scenario_id="invalid-range",
        name="Invalid range",
        workflow_name="morning_report",
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
    )

    assert "start_date must be on or before end_date." in scenario.validate()


def test_scenario_loader_builds_typed_contract_from_boundary_mapping() -> None:
    scenario = backtest_scenario_from_mapping(
        {
            "scenario_id": "loader-check",
            "name": "Loader check",
            "workflow_name": "morning_report",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "symbols": ["SPY", "QQQ"],
            "benchmark_symbol": "SPY",
            "initial_cash": "250000.50",
            "provider_profile": "backtest_synthetic",
            "initial_positions": [
                {
                    "symbol": "QQQ",
                    "quantity": "3.5",
                    "average_price": "400",
                }
            ],
            "expected_outcomes": [
                {
                    "target": "risk.aggregate_risk_score",
                    "expectation_type": "max",
                    "expected": "0.35",
                }
            ],
        }
    )

    assert scenario.scenario_id == "loader-check"
    assert scenario.start_date == date(2026, 1, 1)
    assert scenario.symbols == ("SPY", "QQQ")
    assert scenario.initial_cash == Decimal("250000.50")
    assert scenario.initial_positions[0].quantity == Decimal("3.5")
    assert scenario.expected_outcomes[0].target == "risk.aggregate_risk_score"


def test_load_backtest_scenario_supports_yaml_boundary_file(tmp_path) -> None:
    scenario_file = tmp_path / "scenario.yaml"
    scenario_file.write_text(
        """
scenario_id: yaml-check
name: YAML check
workflow_name: morning_report
start_date: '2026-01-01'
end_date: '2026-01-02'
symbols:
  - SPY
benchmark_symbol: SPY
initial_cash: '100000'
""".strip(),
        encoding="utf-8",
    )

    scenario = load_backtest_scenario(
        scenario_file,
    )

    assert scenario.scenario_id == "yaml-check"
    assert scenario.initial_cash == Decimal("100000")


@pytest.mark.asyncio
async def test_backtest_application_service_prepares_validated_result() -> None:
    service = BacktestApplicationService()
    scenario = BacktestScenario(
        scenario_id="service-check",
        name="Service check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
    )
    request = ServiceRequest(
        payload=BacktestRunRequest(
            scenario=scenario,
        ),
    )

    validation_errors = await service.validate_request(
        request,
    )
    result = await service.run(
        request,
    )

    assert validation_errors == ()
    assert result.success is True
    assert result.result is not None
    assert result.result.status == "validated"
    assert result.result.scenario == scenario
    assert result.result.steps == ()
    assert result.metadata["mode"] == "backtest"


class FakeWorkflowFacade:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        from types import SimpleNamespace

        if simulation_time is None or workflow_inputs is None:
            raise AssertionError("simulation_time and workflow_inputs are required")

        self.calls.append(
            {
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "mode": mode,
                "workflow_inputs": workflow_inputs,
                "simulation_time": simulation_time,
                "archive_on_completion": archive_on_completion,
                "checkpoint_on_completion": checkpoint_on_completion,
                "metadata": metadata,
            }
        )
        return SimpleNamespace(
            success=True,
            execution_id=f"workflow-{len(self.calls)}",
            execution_result=SimpleNamespace(
                final_context=SimpleNamespace(
                    node_outputs={
                        "deterministic_node": {
                            "success": True,
                            "simulation_time": simulation_time.isoformat(),
                            "runtime_mode": mode,
                            "step_index": workflow_inputs["backtest"]["step_index"],
                        }
                    }
                )
            ),
        )


@pytest.mark.asyncio
async def test_backtest_application_service_executes_each_step_through_workflow_facade() -> (
    None
):
    workflow_facade = FakeWorkflowFacade()
    service = BacktestApplicationService(
        workflow_facade=workflow_facade,
    )
    scenario = BacktestScenario(
        scenario_id="runtime-native-check",
        name="Runtime native check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
        initial_positions=(
            BacktestInitialPosition(
                symbol="SPY",
                quantity=Decimal("2"),
                average_price=Decimal("500"),
            ),
        ),
    )
    request = ServiceRequest(
        payload=BacktestRunRequest(
            scenario=scenario,
            persist_results=False,
            checkpoint_workflow_runs=False,
        ),
    )

    result = await service.run(
        request,
    )

    assert result.success is True
    assert result.result is not None
    assert result.result.status == "succeeded"
    assert result.result.success is True
    assert len(result.result.steps) == 3
    assert len(workflow_facade.calls) == 3

    first_call = workflow_facade.calls[0]
    assert first_call["workflow_name"] == "morning_report"
    assert first_call["mode"] == "backtest"
    assert first_call["archive_on_completion"] is False
    assert first_call["checkpoint_on_completion"] is False
    assert first_call["simulation_time"].isoformat() == "2026-01-01T00:00:00+00:00"
    assert first_call["mode"] == "backtest"
    assert first_call["workflow_inputs"]["backtest"]["step_index"] == 0
    assert first_call["workflow_inputs"]["backtest"]["scenario_id"] == (
        "runtime-native-check"
    )

    first_step = result.result.steps[0]
    assert first_step.workflow_run_id == "workflow-1"
    deterministic_node = cast(
        dict[str, object], first_step.node_outputs["deterministic_node"]
    )
    assert deterministic_node["runtime_mode"] == "backtest"
    assert first_step.portfolio_snapshot.cash == Decimal("100000")
    assert first_step.portfolio_snapshot.market_value == Decimal("1000")
    assert first_step.portfolio_snapshot.equity == Decimal("101000")


class FakeTradeWorkflowFacade:
    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        from types import SimpleNamespace

        if simulation_time is None:
            raise AssertionError("simulation_time is required")

        return SimpleNamespace(
            success=True,
            execution_id="workflow-trade-1",
            execution_result=SimpleNamespace(
                final_context=SimpleNamespace(
                    node_outputs={
                        "technical_agent": {
                            "outputs": {
                                "features": {
                                    "symbol": "SPY",
                                    "snapshot": {
                                        "close": "100",
                                    },
                                }
                            }
                        },
                        "trade_packager": {
                            "outputs": {
                                "features": {
                                    "trade_intent": {
                                        "symbol": "SPY",
                                        "direction": "long",
                                        "position_sizing_hint": "0.5",
                                    }
                                }
                            }
                        },
                        "execution_risk_guard": {
                            "outputs": {
                                "features": {
                                    "execution_guard": {
                                        "mode": "normal",
                                        "adjusted_position_size": "0.5",
                                    }
                                }
                            }
                        },
                    }
                )
            ),
        )


@pytest.mark.asyncio
async def test_backtest_application_service_simulates_fills_from_workflow_outputs() -> (
    None
):
    service = BacktestApplicationService(
        workflow_facade=FakeTradeWorkflowFacade(),
    )
    scenario = BacktestScenario(
        scenario_id="fill-engine-check",
        name="Fill engine check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("1000"),
    )
    request = ServiceRequest(
        payload=BacktestRunRequest(
            scenario=scenario,
            persist_results=False,
            checkpoint_workflow_runs=False,
        ),
    )

    result = await service.run(
        request,
    )

    assert result.success is True
    assert result.result is not None
    assert result.result.metadata["simulated_fill_count"] == 1
    step = result.result.steps[0]
    assert step.simulated_fills[0].status == "filled"
    assert step.simulated_fills[0].side == "buy"
    assert step.simulated_fills[0].quantity == Decimal("5.0")
    assert step.portfolio_snapshot.cash == Decimal("500.0")
    assert step.portfolio_snapshot.equity == Decimal("1000.0")
    assert result.result.metrics.total_return == Decimal("0")
    assert set(result.result.artifacts) == {"console", "markdown", "json"}
    assert result.result.metadata["artifact_formats"] == ("console", "markdown", "json")


def test_backtest_scenario_rejects_invalid_missing_data_policy() -> None:
    scenario = BacktestScenario(
        scenario_id="missing-data-policy-check",
        name="Missing data policy check",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
        parameters={"missing_data_policy": "silent_fill"},
    )

    assert (
        "parameters.missing_data_policy must be one of: fail_fast, forward_fill."
        in scenario.validate()
    )
