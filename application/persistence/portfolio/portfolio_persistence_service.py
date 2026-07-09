from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import require_non_empty_identifier
from core.storage.persistence.portfolio import PortfolioAllocationSnapshotRecord
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceBundle
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceRepository
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceResult
from core.storage.persistence.portfolio import PortfolioEquityHistoryPointRecord
from core.storage.persistence.portfolio import PortfolioExposureSnapshotRecord
from core.storage.persistence.portfolio import PortfolioPositionHistoryRecord
from core.storage.persistence.portfolio import PortfolioPositionLatestRecord
from core.storage.persistence.portfolio import PortfolioRiskSnapshotRecord
from core.storage.persistence.query import PersistenceListResult
from core.storage.persistence.portfolio.portfolio_state_repository import (
    PortfolioStateRepository,
)
from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result
from domain.portfolio.models.portfolio_state import PortfolioState


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioEquityHistoryPersistenceFilters:
    """Typed filters for normalized portfolio equity history."""

    account_id: str
    source: str | None = None
    timeframe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(self.account_id, "account_id"),
        )
        for attribute in ("source", "timeframe"):
            object.__setattr__(
                self,
                attribute,
                clean_optional_identifier(getattr(self, attribute), attribute),
            )
        _require_ordered_time_window(self.start, self.end)


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioPositionHistoryPersistenceFilters:
    """
    Typed application-layer filters for position history retrieval.
    """

    account_id: str
    symbol: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(
                self.symbol,
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioLatestPositionPersistenceFilters:
    """
    Typed application-layer filters for latest position retrieval.
    """

    account_id: str
    symbol: str | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "symbol",
            _clean_optional_symbol(
                self.symbol,
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioExposureSnapshotPersistenceFilters:
    """
    Typed application-layer filters for exposure snapshot retrieval.
    """

    account_id: str
    exposure_type: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "exposure_type",
            clean_optional_identifier(
                self.exposure_type,
                "exposure_type",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioRiskSnapshotPersistenceFilters:
    """
    Typed application-layer filters for risk snapshot retrieval.
    """

    account_id: str
    risk_level: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "risk_level",
            clean_optional_identifier(
                self.risk_level,
                "risk_level",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioAllocationSnapshotPersistenceFilters:
    """
    Typed application-layer filters for allocation snapshot retrieval.
    """

    account_id: str
    allocation_type: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "account_id",
            require_non_empty_identifier(
                self.account_id,
                "account_id",
            ),
        )
        object.__setattr__(
            self,
            "allocation_type",
            clean_optional_identifier(
                self.allocation_type,
                "allocation_type",
            ),
        )
        _require_ordered_time_window(
            self.start,
            self.end,
        )


class PortfolioPersistenceService:
    """
    Application service for curated portfolio persistence.

    The existing V1 PortfolioState repository remains intact for account-level
    state snapshots. The expansion repository adds explicit curated position,
    exposure, risk, and allocation persistence around those snapshots without
    automatic workflow capture.
    """

    def __init__(
        self,
        expansion_repository: PortfolioExpansionPersistenceRepository,
        state_repository: PortfolioStateRepository | None = None,
    ) -> None:
        self._expansion_repository = expansion_repository
        self._state_repository = state_repository

    async def persist_state_snapshot(
        self,
        state: PortfolioState,
    ) -> None:
        repository = self._require_state_repository()
        await repository.persist_snapshot(
            state,
        )

    async def get_latest_state(
        self,
        account_id: str,
    ) -> PortfolioState | None:
        repository = self._require_state_repository()
        return await repository.get_latest(
            require_non_empty_identifier(
                account_id,
                "account_id",
            ),
        )

    async def get_state_history(
        self,
        *,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> Sequence[PortfolioState]:
        _require_ordered_time_window(
            start,
            end,
        )
        repository = self._require_state_repository()
        return await repository.get_history(
            require_non_empty_identifier(
                account_id,
                "account_id",
            ),
            start,
            end,
        )

    async def persist_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult:
        return await self._expansion_repository.persist_portfolio_expansion_bundle(
            bundle,
        )

    async def persist_expansion_records(
        self,
        *,
        equity_history_points: Sequence[PortfolioEquityHistoryPointRecord] = (),
        position_history: Sequence[PortfolioPositionHistoryRecord] = (),
        position_latest: Sequence[PortfolioPositionLatestRecord] = (),
        exposure_snapshots: Sequence[PortfolioExposureSnapshotRecord] = (),
        risk_snapshots: Sequence[PortfolioRiskSnapshotRecord] = (),
        allocation_snapshots: Sequence[PortfolioAllocationSnapshotRecord] = (),
    ) -> PortfolioExpansionPersistenceResult:
        return await self.persist_expansion_bundle(
            PortfolioExpansionPersistenceBundle(
                equity_history_points=tuple(equity_history_points),
                position_history=tuple(
                    position_history,
                ),
                position_latest=tuple(
                    position_latest,
                ),
                exposure_snapshots=tuple(
                    exposure_snapshots,
                ),
                risk_snapshots=tuple(
                    risk_snapshots,
                ),
                allocation_snapshots=tuple(
                    allocation_snapshots,
                ),
            )
        )

    async def list_equity_history_points(
        self,
        filters: PortfolioEquityHistoryPersistenceFilters,
    ) -> Sequence[PortfolioEquityHistoryPointRecord]:
        result = await self.list_equity_history_points_result(filters)
        return result.records

    async def list_equity_history_points_result(
        self,
        filters: PortfolioEquityHistoryPersistenceFilters,
    ) -> PersistenceListResult[PortfolioEquityHistoryPointRecord]:
        records = await self._expansion_repository.list_equity_history_points(
            account_id=filters.account_id,
            source=filters.source,
            timeframe=filters.timeframe,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="portfolio_equity_history_point",
            account_id=filters.account_id,
            source=filters.source,
            start=filters.start,
            end=filters.end,
            metadata={"timeframe": filters.timeframe},
        )
        return build_list_result(records, query=query)

    async def list_position_history(
        self,
        filters: PortfolioPositionHistoryPersistenceFilters,
    ) -> Sequence[PortfolioPositionHistoryRecord]:
        result = await self.list_position_history_result(
            filters,
        )
        return result.records

    async def list_position_history_result(
        self,
        filters: PortfolioPositionHistoryPersistenceFilters,
    ) -> PersistenceListResult[PortfolioPositionHistoryRecord]:
        records = await self._expansion_repository.list_position_history(
            account_id=filters.account_id,
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="portfolio_position_history",
            account_id=filters.account_id,
            symbol=filters.symbol,
            start=filters.start,
            end=filters.end,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_latest_positions(
        self,
        filters: PortfolioLatestPositionPersistenceFilters,
    ) -> Sequence[PortfolioPositionLatestRecord]:
        result = await self.list_latest_positions_result(
            filters,
        )
        return result.records

    async def list_latest_positions_result(
        self,
        filters: PortfolioLatestPositionPersistenceFilters,
    ) -> PersistenceListResult[PortfolioPositionLatestRecord]:
        records = await self._expansion_repository.list_latest_positions(
            account_id=filters.account_id,
            symbol=filters.symbol,
        )
        query = build_common_query(
            record_type="portfolio_position_latest",
            account_id=filters.account_id,
            symbol=filters.symbol,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_exposure_snapshots(
        self,
        filters: PortfolioExposureSnapshotPersistenceFilters,
    ) -> Sequence[PortfolioExposureSnapshotRecord]:
        result = await self.list_exposure_snapshots_result(
            filters,
        )
        return result.records

    async def list_exposure_snapshots_result(
        self,
        filters: PortfolioExposureSnapshotPersistenceFilters,
    ) -> PersistenceListResult[PortfolioExposureSnapshotRecord]:
        records = await self._expansion_repository.list_exposure_snapshots(
            account_id=filters.account_id,
            exposure_type=filters.exposure_type,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="portfolio_exposure_snapshot",
            account_id=filters.account_id,
            start=filters.start,
            end=filters.end,
            metadata={
                "exposure_type": filters.exposure_type,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_risk_snapshots(
        self,
        filters: PortfolioRiskSnapshotPersistenceFilters,
    ) -> Sequence[PortfolioRiskSnapshotRecord]:
        result = await self.list_risk_snapshots_result(
            filters,
        )
        return result.records

    async def list_risk_snapshots_result(
        self,
        filters: PortfolioRiskSnapshotPersistenceFilters,
    ) -> PersistenceListResult[PortfolioRiskSnapshotRecord]:
        records = await self._expansion_repository.list_risk_snapshots(
            account_id=filters.account_id,
            risk_level=filters.risk_level,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="portfolio_risk_snapshot",
            account_id=filters.account_id,
            start=filters.start,
            end=filters.end,
            metadata={
                "risk_level": filters.risk_level,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_allocation_snapshots(
        self,
        filters: PortfolioAllocationSnapshotPersistenceFilters,
    ) -> Sequence[PortfolioAllocationSnapshotRecord]:
        result = await self.list_allocation_snapshots_result(
            filters,
        )
        return result.records

    async def list_allocation_snapshots_result(
        self,
        filters: PortfolioAllocationSnapshotPersistenceFilters,
    ) -> PersistenceListResult[PortfolioAllocationSnapshotRecord]:
        records = await self._expansion_repository.list_allocation_snapshots(
            account_id=filters.account_id,
            allocation_type=filters.allocation_type,
            start=filters.start,
            end=filters.end,
        )
        query = build_common_query(
            record_type="portfolio_allocation_snapshot",
            account_id=filters.account_id,
            start=filters.start,
            end=filters.end,
            metadata={
                "allocation_type": filters.allocation_type,
            },
        )
        return build_list_result(
            records,
            query=query,
        )

    def _require_state_repository(
        self,
    ) -> PortfolioStateRepository:
        if self._state_repository is None:
            raise RuntimeError(
                "PortfolioStateRepository is required for V1 portfolio state "
                "snapshot operations."
            )

        return self._state_repository


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
