from __future__ import annotations

from copy import deepcopy
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from typing import Any
from typing import cast

import pytest

from application.reports import MorningReportAssembler
from application.services.backtesting.backtest_request import BacktestScenario
from application.services.backtesting.backtest_result import BacktestMetrics
from application.services.backtesting.backtest_result import BacktestPortfolioSnapshot
from application.services.backtesting.backtest_result import BacktestResult
from application.services.backtesting.backtest_result import BacktestStepResult
from application.services.base import ServiceRunner
from application.services.market_events.market_events_service import MarketEventsService
from core.runtime.state.runtime_context import RuntimeContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)
from core.telemetry.emitters.intelligence_telemetry import IntelligenceTelemetry
from core.telemetry.observability import ObservabilityManager
from intelligence.portfolio.management.portfolio_manager_agent import (
    PortfolioManagerAgent,
)
from intelligence.strategy.synthesis.strategy_synthesis_agent import (
    StrategySynthesisAgent,
)


NO_BREADTH: dict[str, object] = {"has_breadth_data": False}


@pytest.mark.asyncio
async def test_current_strategy_synthesis_ignores_perspective_agent_outputs() -> None:
    agent = _strategy_agent()
    baseline_context = _strategy_context(
        bull_weight=0.70,
        bear_weight=0.10,
        sideways_weight=0.20,
    )
    mutated_context = baseline_context.model_copy(
        update={
            "node_outputs": {
                **baseline_context.node_outputs,
                "bull_agent": _perspective_output(
                    directional_score=-1.0,
                    confidence=0.01,
                    regime="hard_bearish_override",
                ),
                "bear_agent": _perspective_output(
                    directional_score=1.0,
                    confidence=0.99,
                    regime="hard_bullish_override",
                ),
                "sideways_agent": _perspective_output(
                    directional_score=0.0,
                    confidence=1.0,
                    regime="high_conviction_sideways_override",
                ),
            }
        }
    )

    baseline = await agent._execute(baseline_context)
    mutated = await agent._execute(mutated_context)

    assert mutated.outputs == baseline.outputs
    assert mutated.execution_metadata == baseline.execution_metadata
    assert baseline.outputs["regime"] == "strong_risk_on"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "scenario_name",
        "bull_weight",
        "bear_weight",
        "sideways_weight",
        "expected_directional_score",
        "expected_confidence",
        "expected_regime",
    ),
    (
        (
            "bullish",
            0.70,
            0.10,
            0.20,
            0.5885423108318698,
            0.773845697182576,
            "strong_risk_on",
        ),
        (
            "bearish",
            0.10,
            0.70,
            0.20,
            -0.6044445520346655,
            0.7803824832360986,
            "strong_risk_off",
        ),
        (
            "sideways",
            0.20,
            0.20,
            0.60,
            -0.007112788503411238,
            0.4394280737407461,
            "neutral",
        ),
    ),
)
async def test_current_strategy_synthesis_deterministic_fixture_shape(
    scenario_name: str,
    bull_weight: float,
    bear_weight: float,
    sideways_weight: float,
    expected_directional_score: float,
    expected_confidence: float,
    expected_regime: str,
) -> None:
    del scenario_name
    output = await _strategy_agent()._execute(
        _strategy_context(
            bull_weight=bull_weight,
            bear_weight=bear_weight,
            sideways_weight=sideways_weight,
        )
    )

    assert set(output.outputs) == {
        "directional_score",
        "confidence",
        "regime",
        "signals",
        "risks",
        "recommendations",
        "features",
    }
    assert set(output.outputs["features"]) == {
        "symbol",
        "bull_weight",
        "bear_weight",
        "sideways_weight",
        "allocation_vector",
        "net_bias",
        "uncertainty",
        "execution_readiness",
        "signal_quality",
        "posture",
        "composite_risk",
        "risk_pressure",
        "portfolio_scale_factor",
        "portfolio_status",
        "technical_regime",
        "market_events",
        "market_event_constituents",
        "event_lookahead_days",
        "event_pressure",
        "event_bias",
        "event_volatility",
        "event_uncertainty_modifier",
        "event_execution_readiness_modifier",
        "event_signal_quality_modifier",
        "breadth_context",
        "breadth_confirmation_score",
        "breadth_risk_pressure",
        "breadth_uncertainty_modifier",
        "breadth_execution_readiness_modifier",
        "breadth_signal_quality_modifier",
        "breadth_risk_flags",
    }
    assert output.outputs["directional_score"] == pytest.approx(
        expected_directional_score
    )
    assert output.outputs["confidence"] == pytest.approx(expected_confidence)
    assert output.outputs["regime"] == expected_regime
    assert output.outputs["features"]["symbol"] == "SPY"
    assert output.outputs["features"]["market_event_constituents"] == [
        "AAPL",
        "MSFT",
    ]


@pytest.mark.asyncio
async def test_current_portfolio_manager_runtime_output_shape() -> None:
    output = await PortfolioManagerAgent()._execute(_portfolio_context())

    assert set(output.outputs) == {
        "directional_score",
        "confidence",
        "regime",
        "signals",
        "risks",
        "recommendations",
        "features",
    }
    assert set(output.outputs["features"]) == {
        "target_allocation",
        "drift",
        "total_drift",
        "execution_status",
        "scale_factor",
        "portfolio_regime",
        "composite_risk",
        "risk_pressure",
        "stability_score",
        "risk_regime",
        "portfolio_heat",
        "risk_intensity",
        "margin_utilization_ratio",
        "account_restricted",
    }
    assert output.outputs["features"]["target_allocation"] == {
        "bull": 0.60,
        "bear": 0.15,
        "sideways": 0.25,
    }
    assert output.outputs["regime"] == "offensive"
    assert output.outputs["features"]["execution_status"] == "restricted"


def test_current_morning_report_action_plan_shape() -> None:
    document = MorningReportAssembler().assemble(_report_workflow_result())

    assert document.recommended_action_plan.title == "Recommended Action Plan"
    assert [metric.label for metric in document.recommended_action_plan.metrics] == [
        "Strategy Posture",
        "Portfolio Status",
        "Trade-Package Direction",
        "Execution Guard",
        "Capital Scale Factor",
        "Position Size Hint",
        "Trade Quality",
        "Execution Readiness",
    ]
    assert "decision support only" in document.recommended_action_plan.summary
    assert document.recommended_action_plan.recommendations


def test_current_backtest_result_serialization_shape() -> None:
    timestamp = datetime(2026, 7, 9, 14, 30, tzinfo=timezone.utc)
    result = BacktestResult(
        backtest_run_id="backtest-structured-hypothesis-baseline",
        scenario=BacktestScenario(
            scenario_id="structured-hypothesis-baseline",
            name="Structured Hypothesis Baseline",
            workflow_name="morning_report",
            start_date=date(2026, 7, 9),
            end_date=date(2026, 7, 9),
            symbols=("SPY",),
            benchmark_symbol="SPY",
            initial_cash=Decimal("100000"),
        ),
        success=True,
        started_at=timestamp,
        completed_at=timestamp,
        steps=(
            BacktestStepResult(
                timestamp=timestamp,
                workflow_run_id="workflow-run-1",
                success=True,
                node_outputs={
                    "strategy_synthesis_agent": {
                        "outputs": _strategy_runtime_output(),
                    }
                },
                portfolio_snapshot=BacktestPortfolioSnapshot(
                    timestamp=timestamp,
                    cash=Decimal("75000"),
                    equity=Decimal("100000"),
                    market_value=Decimal("25000"),
                    positions={"SPY": {"quantity": "50"}},
                ),
            ),
        ),
        metrics=BacktestMetrics(
            total_return=Decimal("0.05"),
            max_drawdown=Decimal("0.02"),
        ),
    )

    serialized = result.to_dict()

    assert set(serialized) == {
        "backtest_run_id",
        "scenario",
        "success",
        "started_at",
        "completed_at",
        "status",
        "steps",
        "metrics",
        "artifacts",
        "verifications",
        "metadata",
    }
    steps = cast(list[dict[str, object]], serialized["steps"])
    first_step = steps[0]
    metrics = cast(dict[str, object], serialized["metrics"])
    node_outputs = cast(dict[str, object], first_step["node_outputs"])
    strategy_node = cast(dict[str, object], node_outputs["strategy_synthesis_agent"])
    strategy_outputs = cast(dict[str, object], strategy_node["outputs"])

    assert set(first_step) == {
        "timestamp",
        "workflow_run_id",
        "success",
        "node_outputs",
        "portfolio_snapshot",
        "simulated_fills",
    }
    assert metrics["total_return"] == "0.05"
    assert strategy_outputs["regime"] == "strong_risk_on"


class _NoEventsProvider:
    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return []

    async def get_fed_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        return []

    async def get_earnings_events(
        self,
        horizon: str = "3month",
        symbols: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        return []


class _FakeTelemetry:
    async def emit_agent_signal(
        self,
        **kwargs: object,
    ) -> None:
        return None


def _strategy_agent() -> StrategySynthesisAgent:
    return StrategySynthesisAgent(
        events_service=MarketEventsService(events_provider=_NoEventsProvider()),
        service_runner=ServiceRunner(
            telemetry=ApplicationServiceTelemetry(
                observability_manager=ObservabilityManager()
            )
        ),
        intelligence_telemetry=cast(IntelligenceTelemetry, _FakeTelemetry()),
    )


def _strategy_context(
    *,
    bull_weight: float,
    bear_weight: float,
    sideways_weight: float,
) -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-structured-baseline",
        workflow_id="morning_report",
        execution_id="exec-structured-baseline",
        workflow_inputs={"symbol": "SPY"},
        node_outputs={
            "adaptive_weighting_engine": {
                "outputs": {
                    "features": {
                        "bull_weight": bull_weight,
                        "bear_weight": bear_weight,
                        "sideways_weight": sideways_weight,
                    }
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "features": {
                        "risk_pressure": 0.10,
                        "adjusted_risk_pressure": 0.10,
                        "composite_risk": 0.10,
                    }
                }
            },
            "portfolio_state_builder": {
                "outputs": {
                    "features": {
                        "scale_factor": 1.0,
                        "status": "approved",
                    }
                }
            },
            "technical_agent": {
                "outputs": {
                    "features": {
                        "regime": {"regime": "neutral"},
                        "breadth_state": NO_BREADTH,
                        "market_context": {
                            "top_50_constituents": ["AAPL", "MSFT"],
                        },
                    }
                }
            },
        },
    )


def _portfolio_context() -> RuntimeContext:
    return RuntimeContext(
        runtime_id="runtime-structured-baseline",
        workflow_id="morning_report",
        execution_id="exec-structured-baseline",
        node_outputs={
            "strategy_synthesis_agent": {
                "outputs": {
                    "directional_score": 0.45,
                    "confidence": 0.72,
                    "regime": "risk_on",
                    "features": {
                        "bull_weight": 0.60,
                        "bear_weight": 0.15,
                        "sideways_weight": 0.25,
                    },
                }
            },
            "risk_aggregator_agent": {
                "outputs": {
                    "features": {
                        "composite_risk": 0.30,
                        "risk_pressure": 0.35,
                        "stability_score": 0.65,
                        "risk_regime": "moderate",
                    }
                }
            },
            "portfolio_state_builder": {
                "outputs": {
                    "features": {
                        "risk_features": {
                            "portfolio_heat": 0.20,
                            "risk_intensity": 0.25,
                            "margin_utilization_ratio": 0.10,
                            "trading_blocked": False,
                            "account_blocked": False,
                            "trade_suspended_by_user": False,
                        }
                    }
                }
            },
        },
    )


def _perspective_output(
    *,
    directional_score: float,
    confidence: float,
    regime: str,
) -> dict[str, object]:
    return {
        "outputs": {
            "directional_score": directional_score,
            "confidence": confidence,
            "regime": regime,
            "signals": [f"{regime}_signal"],
            "risks": [f"{regime}_risk"],
            "recommendations": [f"{regime}_recommendation"],
            "features": {
                "score": directional_score,
                "force_marker": regime,
            },
        }
    }


def _strategy_runtime_output() -> dict[str, object]:
    output = cast(
        dict[str, object],
        deepcopy(
            {
                "directional_score": 0.5885423108318698,
                "confidence": 0.773845697182576,
                "regime": "strong_risk_on",
                "signals": ["strong_risk_on"],
                "risks": [],
                "recommendations": ["allow_aggressive_trend_exposure"],
                "features": {
                    "posture": "strong_risk_on",
                    "execution_readiness": 0.45544093484713266,
                },
            }
        ),
    )
    return output


def _report_workflow_result() -> dict[str, object]:
    return {
        "workflow_name": "morning_report",
        "execution_id": "exec-structured-baseline",
        "success": True,
        "status": "succeeded",
        "summary": {
            "symbol": "SPY",
            "completed_at": "2026-07-09T14:30:00Z",
        },
        "payload": {
            "workflow_inputs": {"symbol": "SPY"},
            "node_outputs": {
                "strategy_synthesis_agent": {
                    "success": True,
                    "outputs": {
                        "confidence": 0.73,
                        "regime": "risk_on",
                        "features": {
                            "posture": "risk_on",
                            "execution_readiness": 0.69,
                            "portfolio_scale_factor": 0.6,
                        },
                        "recommendations": ["add_exposure_selectively"],
                    },
                },
                "portfolio_manager_agent": {
                    "success": True,
                    "outputs": {
                        "regime": "ready_for_review",
                        "features": {
                            "execution_status": "ready_for_review",
                            "scale_factor": 0.6,
                        },
                        "recommendations": ["rebalance_toward_quality"],
                    },
                },
                "trade_packager": {
                    "success": True,
                    "outputs": {
                        "regime": "long_bias",
                        "features": {
                            "trade_intent": {
                                "direction": "long_bias",
                                "position_sizing_hint": 0.35,
                                "trade_quality_score": 0.72,
                            }
                        },
                        "recommendations": ["stage_entries"],
                    },
                },
                "execution_risk_guard": {
                    "success": True,
                    "outputs": {
                        "features": {
                            "execution_guard": {
                                "mode": "review",
                                "adjusted_position_size": 0.3,
                            }
                        },
                        "recommendations": ["confirm_liquidity_before_action"],
                    },
                },
            },
        },
    }
