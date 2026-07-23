from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.backtesting import BacktestRunModel, BacktestStepModel
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestFillRecord,
    BacktestMetricRecord,
    BacktestPersistenceBundle,
    BacktestPortfolioSnapshotRecord,
    BacktestRunRecord,
    BacktestScenarioRecord,
    BacktestStepRecord,
)
from core.storage.persistence.repositories.postgres_backtest_persistence_repository import (  # noqa: E501
    PostgresBacktestPersistenceRepository,
)


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
    ) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None
        return self._rows[0]

    def scalars(
        self,
    ) -> FakeExecuteResult:
        return self

    def all(
        self,
    ) -> Sequence[object]:
        return tuple(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)
        if self.error is not None:
            raise self.error
        return self.result

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_backtest_bundle_uses_idempotent_upserts() -> None:
    session = FakeAsyncSession()
    repository = PostgresBacktestPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_backtest_bundle(_bundle())

    compiled = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.executed
    ]
    assert result.success is True
    assert result.records_persisted == 8
    assert session.commits == 1
    assert len(session.executed) == 8
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert "scenario_id" in compiled[0]
    assert "backtest_run_id" in compiled[1]
    assert "step_id" in compiled[2]
    assert "snapshot_id" in compiled[3]
    assert "fill_id" in compiled[4]
    assert "metric_id" in compiled[5]
    assert "artifact_id" in compiled[7]


@pytest.mark.asyncio
async def test_persist_backtest_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresBacktestPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_backtest_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_run_round_trips_model_to_record() -> None:
    model = BacktestRunModel(
        backtest_run_id="backtest-1",
        scenario_id="scenario-1",
        workflow_name="morning_report",
        status="succeeded",
        success=True,
        started_at=_timestamp(),
        completed_at=_timestamp(),
        metrics_payload={"total_return": "0.10"},
        metadata_payload={"step_count": 1},
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresBacktestPersistenceRepository(cast(AsyncSession, session))

    record = await repository.get_run("backtest-1")

    assert record is not None
    assert record.backtest_run_id == "backtest-1"
    assert record.metrics == {"total_return": "0.10"}


@pytest.mark.asyncio
async def test_list_steps_round_trips_models_to_records() -> None:
    model = BacktestStepModel(
        step_id="backtest-1:step:0",
        backtest_run_id="backtest-1",
        step_index=0,
        timestamp=_timestamp(),
        workflow_run_id="workflow-run-1",
        success=True,
        node_output_keys=["technical_agent"],
        summary_payload={"node_output_count": 1},
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresBacktestPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_steps("backtest-1")

    assert len(records) == 1
    assert records[0].workflow_run_id == "workflow-run-1"
    assert records[0].node_output_keys == ("technical_agent",)


def _timestamp() -> datetime:
    return datetime(2026, 6, 14, 14, tzinfo=UTC)


def _scenario() -> BacktestScenarioRecord:
    return BacktestScenarioRecord(
        scenario_id="scenario-1",
        name="Deterministic Scenario",
        workflow_name="morning_report",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 2),
        symbols=("SPY",),
        benchmark_symbol="SPY",
        initial_cash=Decimal("100000"),
        provider_profile="backtest_synthetic",
    )


def _run() -> BacktestRunRecord:
    return BacktestRunRecord(
        backtest_run_id="backtest-1",
        scenario_id="scenario-1",
        workflow_name="morning_report",
        status="succeeded",
        success=True,
        started_at=_timestamp(),
        completed_at=_timestamp(),
        metrics={"total_return": "0.10"},
    )


def _step() -> BacktestStepRecord:
    return BacktestStepRecord(
        step_id="backtest-1:step:0",
        backtest_run_id="backtest-1",
        step_index=0,
        timestamp=_timestamp(),
        workflow_run_id="workflow-run-1",
        success=True,
        node_output_keys=("technical_agent",),
    )


def _snapshot() -> BacktestPortfolioSnapshotRecord:
    return BacktestPortfolioSnapshotRecord(
        snapshot_id="backtest-1:step:0:snapshot",
        backtest_run_id="backtest-1",
        step_id="backtest-1:step:0",
        timestamp=_timestamp(),
        cash=Decimal("99000"),
        equity=Decimal("101000"),
        market_value=Decimal("2000"),
        positions={"SPY": {"quantity": "10"}},
    )


def _fill() -> BacktestFillRecord:
    return BacktestFillRecord(
        fill_id="backtest-1:step:0:fill:0",
        backtest_run_id="backtest-1",
        step_id="backtest-1:step:0",
        timestamp=_timestamp(),
        symbol="SPY",
        side="buy",
        quantity=Decimal("10"),
        price=Decimal("100"),
        status="filled",
        realized_pnl=Decimal("5"),
    )


def _metrics() -> tuple[BacktestMetricRecord, ...]:
    return (
        BacktestMetricRecord(
            metric_id="backtest-1:metric:total_return",
            backtest_run_id="backtest-1",
            metric_name="total_return",
            metric_value=Decimal("0.10"),
            recorded_at=_timestamp(),
        ),
        BacktestMetricRecord(
            metric_id="backtest-1:metric:sharpe_ratio",
            backtest_run_id="backtest-1",
            metric_name="sharpe_ratio",
            metric_value=Decimal("1.5"),
            recorded_at=_timestamp(),
        ),
    )


def _artifact() -> BacktestArtifactRecord:
    return BacktestArtifactRecord(
        artifact_id="backtest-1:artifact:markdown",
        backtest_run_id="backtest-1",
        artifact_format="markdown",
        content="# Backtest\n",
        mime_type="text/markdown",
        generated_at=_timestamp(),
    )


def _bundle() -> BacktestPersistenceBundle:
    return BacktestPersistenceBundle(
        scenario=_scenario(),
        run=_run(),
        steps=(_step(),),
        portfolio_snapshots=(_snapshot(),),
        fills=(_fill(),),
        metrics=_metrics(),
        artifacts=(_artifact(),),
    )
