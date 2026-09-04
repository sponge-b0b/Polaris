from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from application.persistence.backtesting.backtest_result_persistence_mapper import (
    backtest_result_to_persistence_bundle,
)
from application.persistence.query_result_helpers import (
    build_common_query,
    build_list_result,
)
from application.services.backtesting import BacktestResult
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
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.query import PersistenceCommonQuery, PersistenceListResult


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestRunPersistenceFilters:
    """
    Typed application-layer filters for backtest run retrieval.
    """

    scenario_id: str | None = None
    workflow_name: str | None = None
    status: str | None = None
    limit: int = 100

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "scenario_id",
            clean_optional_identifier(self.scenario_id, "scenario_id"),
        )
        object.__setattr__(
            self,
            "workflow_name",
            clean_optional_identifier(self.workflow_name, "workflow_name"),
        )
        object.__setattr__(
            self,
            "status",
            clean_optional_identifier(self.status, "status"),
        )
        if self.limit <= 0:
            raise ValueError("limit must be positive.")


class BacktestPersistenceService:
    """
    Application service for curated backtest persistence.
    """

    def __init__(
        self,
        repository: BacktestPersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_result(
        self,
        result: BacktestResult,
    ) -> BacktestPersistenceResult:
        return await self.persist_bundle(
            backtest_result_to_persistence_bundle(result),
        )

    async def persist_bundle(
        self,
        bundle: BacktestPersistenceBundle,
    ) -> BacktestPersistenceResult:
        return await self._repository.persist_backtest_bundle(bundle)

    async def get_scenario(
        self,
        scenario_id: str,
    ) -> BacktestScenarioRecord | None:
        return await self._repository.get_scenario(scenario_id)

    async def get_run(
        self,
        backtest_run_id: str,
    ) -> BacktestRunRecord | None:
        return await self._repository.get_run(backtest_run_id)

    async def get_bundle(
        self,
        backtest_run_id: str,
    ) -> BacktestPersistenceBundle | None:
        return await self._repository.get_bundle(backtest_run_id)

    async def list_runs(
        self,
        filters: BacktestRunPersistenceFilters | None = None,
    ) -> Sequence[BacktestRunRecord]:
        result = await self.list_runs_result(
            filters,
        )
        return result.records

    async def list_runs_result(
        self,
        filters: BacktestRunPersistenceFilters | None = None,
    ) -> PersistenceListResult[BacktestRunRecord]:
        active_filters = filters or BacktestRunPersistenceFilters()
        records = await self._repository.list_runs(
            scenario_id=active_filters.scenario_id,
            workflow_name=active_filters.workflow_name,
            status=active_filters.status,
            limit=active_filters.limit,
        )
        query = build_common_query(
            record_type="backtest_run",
            workflow_name=active_filters.workflow_name,
            metadata={
                "scenario_id": active_filters.scenario_id,
                "status": active_filters.status,
                "limit": active_filters.limit,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_steps(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestStepRecord]:
        result = await self.list_steps_result(
            backtest_run_id,
        )
        return result.records

    async def list_steps_result(
        self,
        backtest_run_id: str,
    ) -> PersistenceListResult[BacktestStepRecord]:
        records = await self._repository.list_steps(backtest_run_id)
        query = _build_backtest_child_query(
            record_type="backtest_step",
            backtest_run_id=backtest_run_id,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_portfolio_snapshots(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestPortfolioSnapshotRecord]:
        result = await self.list_portfolio_snapshots_result(
            backtest_run_id,
        )
        return result.records

    async def list_portfolio_snapshots_result(
        self,
        backtest_run_id: str,
    ) -> PersistenceListResult[BacktestPortfolioSnapshotRecord]:
        records = await self._repository.list_portfolio_snapshots(backtest_run_id)
        query = _build_backtest_child_query(
            record_type="backtest_portfolio_snapshot",
            backtest_run_id=backtest_run_id,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_fills(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestFillRecord]:
        result = await self.list_fills_result(
            backtest_run_id,
        )
        return result.records

    async def list_fills_result(
        self,
        backtest_run_id: str,
    ) -> PersistenceListResult[BacktestFillRecord]:
        records = await self._repository.list_fills(backtest_run_id)
        query = _build_backtest_child_query(
            record_type="backtest_fill",
            backtest_run_id=backtest_run_id,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_metrics(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestMetricRecord]:
        result = await self.list_metrics_result(
            backtest_run_id,
        )
        return result.records

    async def list_metrics_result(
        self,
        backtest_run_id: str,
    ) -> PersistenceListResult[BacktestMetricRecord]:
        records = await self._repository.list_metrics(backtest_run_id)
        query = _build_backtest_child_query(
            record_type="backtest_metric",
            backtest_run_id=backtest_run_id,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_artifacts(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestArtifactRecord]:
        result = await self.list_artifacts_result(
            backtest_run_id,
        )
        return result.records

    async def list_artifacts_result(
        self,
        backtest_run_id: str,
    ) -> PersistenceListResult[BacktestArtifactRecord]:
        records = await self._repository.list_artifacts(backtest_run_id)
        query = _build_backtest_child_query(
            record_type="backtest_artifact",
            backtest_run_id=backtest_run_id,
        )
        return build_list_result(
            records,
            query=query,
        )


def _build_backtest_child_query(
    *,
    record_type: str,
    backtest_run_id: str,
) -> PersistenceCommonQuery:
    return build_common_query(
        record_type=record_type,
        metadata={
            "backtest_run_id": backtest_run_id,
        },
    )
