from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal

import pytest

from application.persistence.backtesting import BacktestPersistenceService
from application.persistence.backtesting import BacktestRunPersistenceFilters
from application.services.backtesting import BacktestFill
from application.services.backtesting import BacktestMetrics
from application.services.backtesting import BacktestPortfolioSnapshot
from application.services.backtesting import BacktestResult
from application.services.backtesting import BacktestScenario
from application.services.backtesting import BacktestStepResult
from core.storage.persistence.backtesting import BacktestArtifactRecord
from core.storage.persistence.backtesting import BacktestFillRecord
from core.storage.persistence.backtesting import BacktestMetricRecord
from core.storage.persistence.backtesting import BacktestPersistenceBundle
from core.storage.persistence.backtesting import BacktestPersistenceResult
from core.storage.persistence.backtesting import BacktestPortfolioSnapshotRecord
from core.storage.persistence.backtesting import BacktestRunRecord
from core.storage.persistence.backtesting import BacktestScenarioRecord
from core.storage.persistence.backtesting import BacktestStepRecord


class FakeBacktestRepository:
    def __init__(
        self,
        bundle: BacktestPersistenceBundle | None = None,
    ) -> None:
        self.bundle = bundle
        self.persisted_bundle: BacktestPersistenceBundle | None = None
        self.run_filters: dict[str, object] | None = None

    async def persist_backtest_bundle(
        self,
        bundle: BacktestPersistenceBundle,
    ) -> BacktestPersistenceResult:
        self.persisted_bundle = bundle
        return BacktestPersistenceResult.succeeded(
            backtest_run_id=bundle.run.backtest_run_id,
            records_persisted=(
                2
                + len(bundle.steps)
                + len(bundle.portfolio_snapshots)
                + len(bundle.fills)
                + len(bundle.metrics)
                + len(bundle.artifacts)
            ),
        )

    async def get_scenario(
        self,
        scenario_id: str,
    ) -> BacktestScenarioRecord | None:
        if self.bundle is None or self.bundle.scenario.scenario_id != scenario_id:
            return None
        return self.bundle.scenario

    async def get_run(
        self,
        backtest_run_id: str,
    ) -> BacktestRunRecord | None:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return None
        return self.bundle.run

    async def get_bundle(
        self,
        backtest_run_id: str,
    ) -> BacktestPersistenceBundle | None:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return None
        return self.bundle

    async def list_runs(
        self,
        *,
        scenario_id: str | None = None,
        workflow_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> Sequence[BacktestRunRecord]:
        self.run_filters = {
            "scenario_id": scenario_id,
            "workflow_name": workflow_name,
            "status": status,
            "limit": limit,
        }
        if self.bundle is None:
            return ()
        return (self.bundle.run,)

    async def list_steps(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestStepRecord]:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return ()
        return self.bundle.steps

    async def list_portfolio_snapshots(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestPortfolioSnapshotRecord]:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return ()
        return self.bundle.portfolio_snapshots

    async def list_fills(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestFillRecord]:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return ()
        return self.bundle.fills

    async def list_metrics(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestMetricRecord]:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return ()
        return self.bundle.metrics

    async def list_artifacts(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestArtifactRecord]:
        if self.bundle is None or self.bundle.run.backtest_run_id != backtest_run_id:
            return ()
        return self.bundle.artifacts


@pytest.mark.asyncio
async def test_backtest_persistence_service_maps_result_to_curated_records() -> None:
    repository = FakeBacktestRepository()
    service = BacktestPersistenceService(repository)

    result = await service.persist_result(_backtest_result())

    assert result.success is True
    assert repository.persisted_bundle is not None
    bundle = repository.persisted_bundle
    assert bundle.scenario.scenario_id == "scenario-1"
    assert bundle.run.backtest_run_id == "backtest-1"
    assert bundle.run.metrics["total_return"] == "0.10"
    assert bundle.steps[0].workflow_run_id == "workflow-run-1"
    assert bundle.steps[0].node_output_keys == ("technical_agent",)
    assert bundle.steps[0].summary == {
        "node_output_count": 1,
        "simulated_fill_count": 1,
    }
    assert bundle.portfolio_snapshots[0].cash == Decimal("99000")
    assert bundle.fills[0].realized_pnl == Decimal("5")
    assert bundle.metrics[0].metric_name == "total_return"
    assert bundle.metrics[0].recorded_at == _timestamp()
    assert bundle.artifacts[0].artifact_format == "console"
    assert bundle.artifacts[0].generated_at == _timestamp()


@pytest.mark.asyncio
async def test_backtest_persistence_service_rehydrates_existing_bundle() -> None:
    bundle = _bundle()
    service = BacktestPersistenceService(FakeBacktestRepository(bundle=bundle))

    retrieved = await service.get_bundle("backtest-1")

    assert retrieved == bundle
    assert await service.list_steps("backtest-1") == bundle.steps
    assert await service.list_fills("backtest-1") == bundle.fills
    assert await service.list_metrics("backtest-1") == bundle.metrics
    assert await service.list_artifacts("backtest-1") == bundle.artifacts


@pytest.mark.asyncio
async def test_backtest_persistence_service_uses_typed_run_filters() -> None:
    repository = FakeBacktestRepository(bundle=_bundle())
    service = BacktestPersistenceService(repository)

    runs = await service.list_runs(
        BacktestRunPersistenceFilters(
            scenario_id=" scenario-1 ",
            workflow_name=" morning_report ",
            status=" succeeded ",
            limit=10,
        )
    )

    assert len(runs) == 1
    assert repository.run_filters == {
        "scenario_id": "scenario-1",
        "workflow_name": "morning_report",
        "status": "succeeded",
        "limit": 10,
    }


def _timestamp() -> datetime:
    return datetime(2026, 6, 14, 14, tzinfo=timezone.utc)


def _scenario() -> BacktestScenario:
    return BacktestScenario(
        scenario_id="scenario-1",
        name="Deterministic Scenario",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
        parameters={"benchmark_return": Decimal("0.05")},
    )


def _backtest_result() -> BacktestResult:
    timestamp = _timestamp()
    return BacktestResult(
        backtest_run_id="backtest-1",
        scenario=_scenario(),
        success=True,
        started_at=timestamp,
        completed_at=timestamp,
        status="succeeded",
        steps=(
            BacktestStepResult(
                timestamp=timestamp,
                workflow_run_id="workflow-run-1",
                success=True,
                node_outputs={"technical_agent": {"score": "bullish"}},
                portfolio_snapshot=BacktestPortfolioSnapshot(
                    timestamp=timestamp,
                    cash=Decimal("99000"),
                    equity=Decimal("101000"),
                    market_value=Decimal("2000"),
                    positions={"SPY": {"quantity": "10"}},
                ),
                simulated_fills=(
                    BacktestFill(
                        timestamp=timestamp,
                        symbol="SPY",
                        side="buy",
                        quantity=Decimal("10"),
                        price=Decimal("100"),
                        status="filled",
                        realized_pnl=Decimal("5"),
                    ),
                ),
            ),
        ),
        metrics=BacktestMetrics(
            total_return=Decimal("0.10"),
            benchmark_relative_return=Decimal("0.05"),
        ),
        artifacts={
            "console": "Backtest summary",
            "markdown": "# Backtest summary\n",
        },
        metadata={"step_count": 1},
    )


def _bundle() -> BacktestPersistenceBundle:
    result = _backtest_result()
    from application.persistence.backtesting import (
        backtest_result_to_persistence_bundle,
    )

    return backtest_result_to_persistence_bundle(result)
