from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.backtesting import (
    BacktestArtifactModel,
    BacktestFillModel,
    BacktestMetricModel,
    BacktestPortfolioSnapshotModel,
    BacktestRunModel,
    BacktestScenarioModel,
    BacktestStepModel,
)
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestFillRecord,
    BacktestMetricRecord,
    BacktestPersistenceBundle,
    BacktestPersistenceRepository,
    BacktestPersistenceResult,
    BacktestPortfolioSnapshotRecord,
    BacktestRunRecord,
    BacktestScenarioRecord,
    BacktestStepRecord,
)
from core.storage.persistence.serializers.backtest_persistence_serializer import (
    BacktestPersistenceSerializer,
)


class PostgresBacktestPersistenceRepository(BacktestPersistenceRepository):
    """
    PostgreSQL adapter for durable curated backtest persistence.

    This repository stores scenario/run summaries, workflow-run links, portfolio
    snapshots, simulated fills, queryable metrics, and report artifacts. It does
    not duplicate raw runtime node outputs; those remain in runtime persistence.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_backtest_bundle(
        self,
        bundle: BacktestPersistenceBundle,
    ) -> BacktestPersistenceResult:
        try:
            await self._session.execute(_upsert_scenario_statement(bundle.scenario))
            await self._session.execute(_upsert_run_statement(bundle.run))
            for step in bundle.steps:
                await self._session.execute(_upsert_step_statement(step))
            for snapshot in bundle.portfolio_snapshots:
                await self._session.execute(_upsert_snapshot_statement(snapshot))
            for fill in bundle.fills:
                await self._session.execute(_upsert_fill_statement(fill))
            for metric in bundle.metrics:
                await self._session.execute(_upsert_metric_statement(metric))
            for artifact in bundle.artifacts:
                await self._session.execute(_upsert_artifact_statement(artifact))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            return BacktestPersistenceResult.failed(str(exc))

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
        stmt = select(BacktestScenarioModel).where(
            BacktestScenarioModel.scenario_id == scenario_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return BacktestPersistenceSerializer.scenario_from_model(model)

    async def get_run(
        self,
        backtest_run_id: str,
    ) -> BacktestRunRecord | None:
        stmt = select(BacktestRunModel).where(
            BacktestRunModel.backtest_run_id == backtest_run_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return BacktestPersistenceSerializer.run_from_model(model)

    async def get_bundle(
        self,
        backtest_run_id: str,
    ) -> BacktestPersistenceBundle | None:
        run = await self.get_run(backtest_run_id)
        if run is None:
            return None
        scenario = await self.get_scenario(run.scenario_id)
        if scenario is None:
            return None

        return BacktestPersistenceBundle(
            scenario=scenario,
            run=run,
            steps=tuple(await self.list_steps(backtest_run_id)),
            portfolio_snapshots=tuple(
                await self.list_portfolio_snapshots(backtest_run_id)
            ),
            fills=tuple(await self.list_fills(backtest_run_id)),
            metrics=tuple(await self.list_metrics(backtest_run_id)),
            artifacts=tuple(await self.list_artifacts(backtest_run_id)),
        )

    async def list_runs(
        self,
        *,
        scenario_id: str | None = None,
        workflow_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> Sequence[BacktestRunRecord]:
        stmt = select(BacktestRunModel)
        if scenario_id is not None:
            stmt = stmt.where(BacktestRunModel.scenario_id == scenario_id)
        if workflow_name is not None:
            stmt = stmt.where(BacktestRunModel.workflow_name == workflow_name)
        if status is not None:
            stmt = stmt.where(BacktestRunModel.status == status)
        stmt = stmt.order_by(BacktestRunModel.started_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return tuple(
            BacktestPersistenceSerializer.run_from_model(model)
            for model in result.scalars().all()
        )

    async def list_steps(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestStepRecord]:
        stmt = (
            select(BacktestStepModel)
            .where(BacktestStepModel.backtest_run_id == backtest_run_id)
            .order_by(BacktestStepModel.step_index)
        )
        result = await self._session.execute(stmt)
        return tuple(
            BacktestPersistenceSerializer.step_from_model(model)
            for model in result.scalars().all()
        )

    async def list_portfolio_snapshots(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestPortfolioSnapshotRecord]:
        stmt = (
            select(BacktestPortfolioSnapshotModel)
            .where(BacktestPortfolioSnapshotModel.backtest_run_id == backtest_run_id)
            .order_by(BacktestPortfolioSnapshotModel.timestamp)
        )
        result = await self._session.execute(stmt)
        return tuple(
            BacktestPersistenceSerializer.portfolio_snapshot_from_model(model)
            for model in result.scalars().all()
        )

    async def list_fills(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestFillRecord]:
        stmt = (
            select(BacktestFillModel)
            .where(BacktestFillModel.backtest_run_id == backtest_run_id)
            .order_by(BacktestFillModel.timestamp, BacktestFillModel.fill_id)
        )
        result = await self._session.execute(stmt)
        return tuple(
            BacktestPersistenceSerializer.fill_from_model(model)
            for model in result.scalars().all()
        )

    async def list_metrics(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestMetricRecord]:
        stmt = (
            select(BacktestMetricModel)
            .where(BacktestMetricModel.backtest_run_id == backtest_run_id)
            .order_by(BacktestMetricModel.metric_name)
        )
        result = await self._session.execute(stmt)
        return tuple(
            BacktestPersistenceSerializer.metric_from_model(model)
            for model in result.scalars().all()
        )

    async def list_artifacts(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestArtifactRecord]:
        stmt = (
            select(BacktestArtifactModel)
            .where(BacktestArtifactModel.backtest_run_id == backtest_run_id)
            .order_by(BacktestArtifactModel.artifact_format)
        )
        result = await self._session.execute(stmt)
        return tuple(
            BacktestPersistenceSerializer.artifact_from_model(model)
            for model in result.scalars().all()
        )


def _upsert_scenario_statement(
    record: BacktestScenarioRecord,
) -> Any:
    values = BacktestPersistenceSerializer.scenario_values(record)
    stmt = insert(BacktestScenarioModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["scenario_id"],
        set_={
            "name": excluded.name,
            "workflow_name": excluded.workflow_name,
            "start_date": excluded.start_date,
            "end_date": excluded.end_date,
            "symbols": excluded.symbols,
            "benchmark_symbol": excluded.benchmark_symbol,
            "initial_cash": excluded.initial_cash,
            "provider_profile": excluded.provider_profile,
            "initial_positions": excluded.initial_positions,
            "parameters": excluded.parameters,
            "expected_outcomes": excluded.expected_outcomes,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_run_statement(
    record: BacktestRunRecord,
) -> Any:
    values = BacktestPersistenceSerializer.run_values(record)
    stmt = insert(BacktestRunModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["backtest_run_id"],
        set_={
            "scenario_id": excluded.scenario_id,
            "workflow_name": excluded.workflow_name,
            "status": excluded.status,
            "success": excluded.success,
            "started_at": excluded.started_at,
            "completed_at": excluded.completed_at,
            "metrics": excluded.metrics,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_step_statement(
    record: BacktestStepRecord,
) -> Any:
    values = BacktestPersistenceSerializer.step_values(record)
    stmt = insert(BacktestStepModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["step_id"],
        set_={
            "backtest_run_id": excluded.backtest_run_id,
            "step_index": excluded.step_index,
            "timestamp": excluded.timestamp,
            "workflow_run_id": excluded.workflow_run_id,
            "success": excluded.success,
            "node_output_keys": excluded.node_output_keys,
            "summary": excluded.summary,
            "updated_at": func.now(),
        },
    )


def _upsert_snapshot_statement(
    record: BacktestPortfolioSnapshotRecord,
) -> Any:
    values = BacktestPersistenceSerializer.portfolio_snapshot_values(record)
    stmt = insert(BacktestPortfolioSnapshotModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["snapshot_id"],
        set_={
            "backtest_run_id": excluded.backtest_run_id,
            "step_id": excluded.step_id,
            "timestamp": excluded.timestamp,
            "cash": excluded.cash,
            "equity": excluded.equity,
            "market_value": excluded.market_value,
            "positions": excluded.positions,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_fill_statement(
    record: BacktestFillRecord,
) -> Any:
    values = BacktestPersistenceSerializer.fill_values(record)
    stmt = insert(BacktestFillModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["fill_id"],
        set_={
            "backtest_run_id": excluded.backtest_run_id,
            "step_id": excluded.step_id,
            "timestamp": excluded.timestamp,
            "symbol": excluded.symbol,
            "side": excluded.side,
            "quantity": excluded.quantity,
            "price": excluded.price,
            "status": excluded.status,
            "reason": excluded.reason,
            "realized_pnl": excluded.realized_pnl,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_metric_statement(
    record: BacktestMetricRecord,
) -> Any:
    values = BacktestPersistenceSerializer.metric_values(record)
    stmt = insert(BacktestMetricModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["metric_id"],
        set_={
            "backtest_run_id": excluded.backtest_run_id,
            "metric_name": excluded.metric_name,
            "metric_value": excluded.metric_value,
            "recorded_at": excluded.recorded_at,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )


def _upsert_artifact_statement(
    record: BacktestArtifactRecord,
) -> Any:
    values = BacktestPersistenceSerializer.artifact_values(record)
    stmt = insert(BacktestArtifactModel).values(**values)
    excluded = stmt.excluded
    return stmt.on_conflict_do_update(
        index_elements=["artifact_id"],
        set_={
            "backtest_run_id": excluded.backtest_run_id,
            "artifact_format": excluded.artifact_format,
            "content": excluded.content,
            "mime_type": excluded.mime_type,
            "generated_at": excluded.generated_at,
            "metadata": excluded.metadata,
            "updated_at": func.now(),
        },
    )
