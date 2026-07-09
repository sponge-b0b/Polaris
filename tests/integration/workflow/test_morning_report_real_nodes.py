from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal

import pytest

from application.services.backtesting import BacktestApplicationService
from application.services.backtesting import BacktestExpectedOutcome
from application.services.backtesting import BacktestRunRequest
from application.services.backtesting import BacktestScenario
from application.services.base import ServiceRequest
from interfaces.cli.bootstrap.container import cli_runtime_scope


_FIXED_BACKTEST_TIME = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
_PROVIDER_ENV = {
    "PROVIDER_PROFILE": "backtest_synthetic",
    "MACRO_PROVIDER": "backtest_macro_provider",
    "MARKET_DATA_PROVIDER": "backtest_data_provider",
    "MARKET_EVENTS_PROVIDER": "backtest_events_provider",
    "NEWS_PROVIDER": "backtest_news_provider",
    "PORTFOLIO_PROVIDER": "backtest_portfolio_provider",
    "SENTIMENT_PROVIDER": "backtest_sentiment_provider",
}


@pytest.mark.asyncio
async def test_morning_report_runs_real_intelligence_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_synthetic_providers(monkeypatch)

    async with cli_runtime_scope() as scope:
        result = await scope.runtime.facade.run_workflow(
            workflow_name="morning_report",
            workflow_inputs={
                "symbol": "SPY",
                "days": 120,
            },
            archive_on_completion=False,
        )

    assert result.success is True

    node_outputs = result.execution_result.final_context.node_outputs

    expected_nodes = {
        "portfolio_state_builder",
        "fundamental_agent",
        "technical_agent",
        "news_agent",
        "sentiment_agent",
        "drawdown_risk_agent",
        "exposure_risk_agent",
        "volatility_risk_agent",
        "risk_signal_builder",
        "risk_aggregator_agent",
        "attribution_engine",
        "adaptive_weighting_engine",
        "bull_agent",
        "bear_agent",
        "sideways_agent",
        "strategy_synthesis_agent",
        "portfolio_manager_agent",
        "trade_packager",
        "execution_risk_guard",
    }

    assert set(node_outputs) == expected_nodes

    for node_name in expected_nodes:
        output = node_outputs[node_name]
        assert output["success"] is True, node_name
        assert output["outputs"], node_name
        assert output["execution_metadata"]["node_name"] == node_name

    assert "features" in node_outputs["technical_agent"]["outputs"]
    assert "features" in node_outputs["risk_aggregator_agent"]["outputs"]
    assert "features" in node_outputs["execution_risk_guard"]["outputs"]

    technical_features = node_outputs["technical_agent"]["outputs"]["features"]
    technical_breadth = technical_features["breadth_state"]
    market_context = technical_features["market_context"]

    assert len(market_context["top_50_constituents"]) == 50
    assert technical_breadth["has_breadth_data"] is True
    assert "breadth_score" in technical_breadth
    assert "breadth_risk_score" in technical_breadth
    assert "breadth_regime" in technical_breadth

    downstream_breadth_nodes = (
        "volatility_risk_agent",
        "risk_aggregator_agent",
        "bull_agent",
        "bear_agent",
        "sideways_agent",
        "strategy_synthesis_agent",
        "trade_packager",
        "execution_risk_guard",
    )

    for node_name in downstream_breadth_nodes:
        features = node_outputs[node_name]["outputs"]["features"]
        breadth_context = features["breadth_context"]

        assert breadth_context["has_breadth_data"] is True, node_name
        assert (
            breadth_context["breadth_regime"] == technical_breadth["breadth_regime"]
        ), node_name
        assert breadth_context["risk_regime"] == technical_breadth["risk_regime"], (
            node_name
        )
        assert breadth_context["breadth_score"] == technical_breadth["breadth_score"], (
            node_name
        )
        assert "confirmation_score" in breadth_context, node_name
        assert "risk_pressure" in breadth_context, node_name
        assert features["breadth_confirmation_score"] == pytest.approx(
            breadth_context["confirmation_score"],
            abs=1e-4,
        ), node_name
        assert features["breadth_risk_pressure"] == pytest.approx(
            breadth_context["risk_pressure"],
            abs=1e-4,
        ), node_name
        assert isinstance(features["breadth_risk_flags"], list), node_name

    strategy_features = node_outputs["strategy_synthesis_agent"]["outputs"]["features"]

    assert "market_events" in strategy_features
    assert "event_pressure" in strategy_features
    assert strategy_features["event_lookahead_days"] == 10
    assert len(strategy_features["market_event_constituents"]) == 50
    assert "event_error" not in strategy_features["market_events"]

    trade_features = node_outputs["trade_packager"]["outputs"]["features"]
    assert "breadth_entry_bias_modifier" in trade_features
    assert "breadth_position_size_multiplier" in trade_features


@pytest.mark.asyncio
async def test_runtime_native_backtest_verifies_real_synthetic_decision_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_synthetic_providers(monkeypatch)
    scenario = _real_golden_scenario()

    async with cli_runtime_scope() as scope:
        service = BacktestApplicationService(
            workflow_facade=scope.runtime.facade,
            clock=lambda: _FIXED_BACKTEST_TIME,
            run_id_factory=lambda: "backtest-real-golden",
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
    result = response.result
    assert result.success is True, [
        verification.to_dict()
        for verification in result.verifications
        if not verification.passed
    ]
    assert result.started_at == _FIXED_BACKTEST_TIME
    assert result.completed_at == _FIXED_BACKTEST_TIME
    assert result.steps[0].timestamp == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert result.steps[0].workflow_run_id == "backtest-real-golden-step-000000"
    assert tuple(result.steps[0].node_outputs) == (
        "adaptive_weighting_engine",
        "attribution_engine",
        "bear_agent",
        "bull_agent",
        "drawdown_risk_agent",
        "execution_risk_guard",
        "exposure_risk_agent",
        "fundamental_agent",
        "news_agent",
        "portfolio_manager_agent",
        "portfolio_state_builder",
        "risk_aggregator_agent",
        "risk_signal_builder",
        "sentiment_agent",
        "sideways_agent",
        "strategy_synthesis_agent",
        "technical_agent",
        "trade_packager",
        "volatility_risk_agent",
    )
    assert all(verification.passed for verification in result.verifications)
    assert result.metadata["verification_count"] == len(scenario.expected_outcomes)
    assert result.metadata["verification_failure_count"] == 0
    technical_output = result.steps[0].node_outputs["technical_agent"]
    assert isinstance(technical_output, dict)
    assert "execution_metadata" not in technical_output
    assert '"passed": true' in result.artifacts["json"]


def _configure_synthetic_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _PROVIDER_ENV.items():
        monkeypatch.setenv(name, value)


def _real_golden_scenario() -> BacktestScenario:
    return BacktestScenario(
        scenario_id="real-synthetic-decision-chain",
        name="Real synthetic decision-chain verification",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
        parameters={"days": 120},
        expected_outcomes=(
            BacktestExpectedOutcome(
                target="technical.snapshot.rsi_14",
                expectation_type="approx",
                expected="97.43217587049374",
                tolerance=Decimal("0.000000000001"),
            ),
            BacktestExpectedOutcome(
                target="breadth.breadth_score",
                expectation_type="approx",
                expected="-0.6177259443575474",
                tolerance=Decimal("0.000000000001"),
            ),
            BacktestExpectedOutcome(
                target="technical.regime.directional_technical_score",
                expectation_type="approx",
                expected="0.3232220334217033",
                tolerance=Decimal("0.000000000001"),
            ),
            BacktestExpectedOutcome(
                target="technical.regime.regime",
                expectation_type="equals",
                expected="bullish",
            ),
            BacktestExpectedOutcome(
                target="portfolio.equity",
                expectation_type="equals",
                expected="100000",
            ),
            BacktestExpectedOutcome(
                target="portfolio_state.portfolio_state.equity",
                expectation_type="equals",
                expected="100000",
            ),
            BacktestExpectedOutcome(
                target="risk.adjusted_composite_risk",
                expectation_type="approx",
                expected="0.1431672",
                tolerance=Decimal("0.000000000001"),
            ),
            BacktestExpectedOutcome(
                target="strategy.directional_score",
                expectation_type="approx",
                expected="-0.015557159122692982",
                tolerance=Decimal("0.000000000001"),
            ),
            BacktestExpectedOutcome(
                target="strategy.posture",
                expectation_type="equals",
                expected="neutral",
            ),
            BacktestExpectedOutcome(
                target="trade.direction",
                expectation_type="equals",
                expected="flat",
            ),
            BacktestExpectedOutcome(
                target="trade.position_sizing_hint",
                expectation_type="approx",
                expected="0.22920277399999997",
                tolerance=Decimal("0.000000000001"),
            ),
            BacktestExpectedOutcome(
                target="execution_risk.mode",
                expectation_type="equals",
                expected="normal",
            ),
            BacktestExpectedOutcome(
                target="execution_risk.adjusted_position_size",
                expectation_type="approx",
                expected="0.22920277399999997",
                tolerance=Decimal("0.000000000001"),
            ),
        ),
    )
