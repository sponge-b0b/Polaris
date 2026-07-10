from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestArtifactRecord,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestFillRecord,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestMetricRecord,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestPersistenceBundle,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestPersistenceResult,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestPortfolioSnapshotRecord,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestRunRecord,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestScenarioRecord,
)
from core.storage.persistence.backtesting.backtest_persistence_models import (
    BacktestStepRecord,
)


class BacktestPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated backtest persistence.
    """

    async def persist_backtest_bundle(
        self,
        bundle: BacktestPersistenceBundle,
    ) -> BacktestPersistenceResult: ...

    async def get_scenario(
        self,
        scenario_id: str,
    ) -> BacktestScenarioRecord | None: ...

    async def get_run(
        self,
        backtest_run_id: str,
    ) -> BacktestRunRecord | None: ...

    async def get_bundle(
        self,
        backtest_run_id: str,
    ) -> BacktestPersistenceBundle | None: ...

    async def list_runs(
        self,
        *,
        scenario_id: str | None = None,
        workflow_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> Sequence[BacktestRunRecord]: ...

    async def list_steps(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestStepRecord]: ...

    async def list_portfolio_snapshots(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestPortfolioSnapshotRecord]: ...

    async def list_fills(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestFillRecord]: ...

    async def list_metrics(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestMetricRecord]: ...

    async def list_artifacts(
        self,
        backtest_run_id: str,
    ) -> Sequence[BacktestArtifactRecord]: ...
