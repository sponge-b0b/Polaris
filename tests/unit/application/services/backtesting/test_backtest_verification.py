from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from application.persistence.backtesting import backtest_result_to_persistence_bundle
from application.services.backtesting import BacktestApplicationService
from application.services.backtesting import BacktestExpectedOutcome
from application.services.backtesting import BacktestRunRequest
from application.services.backtesting import BacktestScenario
from application.services.base import ServiceRequest


_FIXED_TIME = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


class DeterministicGoldenWorkflowFacade:
    def __init__(self) -> None:
        self.call_count = 0

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
        if simulation_time is None:
            raise AssertionError("simulation_time is required")
        if execution_id is None:
            raise AssertionError("execution_id is required")
        if workflow_inputs is None:
            raise AssertionError("workflow_inputs are required")
        assert workflow_inputs["symbol"] == "SPY"
        assert workflow_inputs["days"] == 120
        self.call_count += 1
        node_outputs = _golden_node_outputs()
        for output in node_outputs.values():
            output["execution_metadata"] = {
                "duration_seconds": self.call_count,
            }
        return SimpleNamespace(
            success=True,
            execution_id=execution_id,
            execution_result=SimpleNamespace(
                final_context=SimpleNamespace(
                    node_outputs=node_outputs,
                )
            ),
        )


@pytest.mark.asyncio
async def test_golden_backtest_verifies_full_decision_chain_and_is_repeatable() -> None:
    scenario = _golden_scenario()
    service = BacktestApplicationService(
        workflow_facade=DeterministicGoldenWorkflowFacade(),
        clock=lambda: _FIXED_TIME,
        run_id_factory=lambda: "backtest-golden",
    )
    request = ServiceRequest(
        payload=BacktestRunRequest(
            scenario=scenario,
            persist_results=False,
            checkpoint_workflow_runs=False,
        )
    )

    first = await service.run(request)
    second = await service.run(request)

    assert first.result is not None
    assert second.result is not None
    assert first.result.success is True
    assert first.result.status == "succeeded"
    assert len(first.result.verifications) == len(scenario.expected_outcomes)
    assert all(verification.passed for verification in first.result.verifications)
    assert first.result.steps[0].workflow_run_id == "backtest-golden-step-000000"
    technical_output = first.result.steps[0].node_outputs["technical_agent"]
    assert isinstance(technical_output, dict)
    assert "execution_metadata" not in technical_output
    assert first.result.to_dict() == second.result.to_dict()
    assert backtest_result_to_persistence_bundle(
        first.result
    ) == backtest_result_to_persistence_bundle(second.result)
    assert "Verified Expectations: 9 / 9" in first.result.artifacts["console"]
    assert "## Deterministic Verification" in first.result.artifacts["markdown"]
    assert '"passed": true' in first.result.artifacts["json"]


@pytest.mark.asyncio
async def test_failed_expected_outcome_fails_run_with_attributable_evidence() -> None:
    scenario = _golden_scenario(
        expected_outcomes=(
            BacktestExpectedOutcome(
                target="risk.composite_risk",
                expectation_type="max",
                expected="0.20",
            ),
        )
    )
    service = BacktestApplicationService(
        workflow_facade=DeterministicGoldenWorkflowFacade(),
        clock=lambda: _FIXED_TIME,
        run_id_factory=lambda: "backtest-failed-verification",
    )

    response = await service.run(
        ServiceRequest(
            payload=BacktestRunRequest(
                scenario=scenario,
                persist_results=False,
                checkpoint_workflow_runs=False,
            )
        )
    )

    assert response.result is not None
    assert response.result.success is False
    assert response.result.status == "failed"
    assert response.result.verifications[0].passed is False
    assert response.result.verifications[0].actual == Decimal("0.25")
    assert response.result.metadata["verification_failure_count"] == 1


@pytest.mark.asyncio
async def test_injected_backtest_clock_must_be_timezone_aware() -> None:
    service = BacktestApplicationService(
        clock=lambda: datetime(2026, 1, 1),
        run_id_factory=lambda: "backtest-naive-clock",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        await service.run(
            ServiceRequest(
                payload=BacktestRunRequest(
                    scenario=_golden_scenario(expected_outcomes=()),
                )
            )
        )


def _golden_scenario(
    *,
    expected_outcomes: tuple[BacktestExpectedOutcome, ...] | None = None,
) -> BacktestScenario:
    return BacktestScenario(
        scenario_id="full-chain-golden",
        name="Full decision chain golden scenario",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("1000"),
        parameters={"days": 120},
        expected_outcomes=expected_outcomes
        if expected_outcomes is not None
        else (
            BacktestExpectedOutcome(
                target="technical.snapshot.rsi_14",
                expectation_type="equals",
                expected="62.5",
            ),
            BacktestExpectedOutcome(
                target="breadth.breadth_percent",
                expectation_type="approx",
                expected="0.20",
                tolerance=Decimal("0.000001"),
            ),
            BacktestExpectedOutcome(
                target="technical.regime.directional_technical_score",
                expectation_type="min",
                expected="0.60",
            ),
            BacktestExpectedOutcome(
                target="portfolio.equity",
                expectation_type="equals",
                expected="1000",
            ),
            BacktestExpectedOutcome(
                target="portfolio_state.total_equity",
                expectation_type="equals",
                expected="1000",
            ),
            BacktestExpectedOutcome(
                target="risk.composite_risk",
                expectation_type="between",
                expected=("0.24", "0.26"),
            ),
            BacktestExpectedOutcome(
                target="strategy.directional_score",
                expectation_type="equals",
                expected="0.45",
            ),
            BacktestExpectedOutcome(
                target="trade.position_sizing_hint",
                expectation_type="equals",
                expected="0.20",
            ),
            BacktestExpectedOutcome(
                target="execution_risk.adjusted_position_size",
                expectation_type="max",
                expected="0.20",
            ),
        ),
    )


def _golden_node_outputs() -> dict[str, dict[str, object]]:
    return {
        "technical_agent": {
            "outputs": {
                "features": {
                    "symbol": "SPY",
                    "snapshot": {"close": "100", "rsi_14": "62.5"},
                    "breadth_state": {"breadth_percent": "0.20"},
                    "regime": {"directional_technical_score": "0.60"},
                }
            }
        },
        "portfolio_state_builder": {
            "outputs": {
                "features": {
                    "total_equity": "1000",
                    "cash": "1000",
                    "gross_exposure": "0",
                }
            }
        },
        "risk_aggregator_agent": {
            "outputs": {
                "features": {
                    "composite_risk": Decimal("0.25"),
                    "risk_pressure": Decimal("0.20"),
                }
            }
        },
        "strategy_synthesis_agent": {
            "outputs": {
                "directional_score": Decimal("0.45"),
                "confidence": Decimal("0.80"),
                "regime": "bullish",
            }
        },
        "trade_packager": {
            "outputs": {
                "features": {
                    "trade_intent": {
                        "symbol": "SPY",
                        "direction": "long",
                        "position_sizing_hint": Decimal("0.20"),
                    }
                }
            }
        },
        "execution_risk_guard": {
            "outputs": {
                "features": {
                    "execution_guard": {
                        "mode": "normal",
                        "adjusted_position_size": Decimal("0.20"),
                    }
                }
            }
        },
    }
