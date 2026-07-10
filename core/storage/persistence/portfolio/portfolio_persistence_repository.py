from __future__ import annotations

from datetime import datetime
from typing import Protocol
from typing import Sequence

from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioAllocationSnapshotRecord,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioExpansionPersistenceBundle,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioExpansionPersistenceResult,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioEquityHistoryPointRecord,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioExposureSnapshotRecord,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioPositionHistoryRecord,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioPositionLatestRecord,
)
from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioRiskSnapshotRecord,
)


class PortfolioExpansionPersistenceRepository(Protocol):
    """
    Async repository contract for durable curated portfolio expansion records.

    Position history and snapshot records are append-only canonical facts.
    Latest position records are upserted for fast account/symbol lookups.
    Future RAG/vector ingestion should read from these curated records rather
    than raw workflow node payloads.
    """

    async def persist_portfolio_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult: ...

    async def list_equity_history_points(
        self,
        *,
        account_id: str,
        source: str | None = None,
        timeframe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioEquityHistoryPointRecord]: ...

    async def list_position_history(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioPositionHistoryRecord]: ...

    async def list_latest_positions(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
    ) -> Sequence[PortfolioPositionLatestRecord]: ...

    async def list_exposure_snapshots(
        self,
        *,
        account_id: str,
        exposure_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioExposureSnapshotRecord]: ...

    async def list_risk_snapshots(
        self,
        *,
        account_id: str,
        risk_level: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioRiskSnapshotRecord]: ...

    async def list_allocation_snapshots(
        self,
        *,
        account_id: str,
        allocation_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioAllocationSnapshotRecord]: ...
