from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from core.storage.persistence.portfolio.portfolio_persistence_models import (
    PortfolioAllocationSnapshotRecord,
    PortfolioEquityHistoryPointRecord,
    PortfolioExpansionPersistenceBundle,
    PortfolioExpansionPersistenceResult,
    PortfolioExposureSnapshotRecord,
    PortfolioPositionHistoryRecord,
    PortfolioPositionLatestRecord,
    PortfolioRiskSnapshotRecord,
)


class InMemoryPortfolioExpansionPersistenceRepository:
    """Invocation-local portfolio records for deterministic runtime composition."""

    def __init__(self) -> None:
        self._equity_history: dict[
            tuple[str, str, str, datetime], PortfolioEquityHistoryPointRecord
        ] = {}
        self._position_history: dict[str, PortfolioPositionHistoryRecord] = {}
        self._position_latest: dict[tuple[str, str], PortfolioPositionLatestRecord] = {}
        self._exposure_snapshots: dict[str, PortfolioExposureSnapshotRecord] = {}
        self._risk_snapshots: dict[str, PortfolioRiskSnapshotRecord] = {}
        self._allocation_snapshots: dict[str, PortfolioAllocationSnapshotRecord] = {}

    async def persist_portfolio_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult:
        for equity_record in bundle.equity_history_points:
            key = (
                equity_record.account_id,
                equity_record.source,
                equity_record.timeframe,
                equity_record.observed_at,
            )
            self._equity_history.setdefault(key, equity_record)
        for history_record in bundle.position_history:
            self._position_history.setdefault(
                history_record.position_history_id, history_record
            )
        for latest_record in bundle.position_latest:
            self._position_latest[(latest_record.account_id, latest_record.symbol)] = (
                latest_record
            )
        for exposure_record in bundle.exposure_snapshots:
            self._exposure_snapshots.setdefault(
                exposure_record.exposure_snapshot_id, exposure_record
            )
        for risk_record in bundle.risk_snapshots:
            self._risk_snapshots.setdefault(risk_record.risk_snapshot_id, risk_record)
        for allocation_record in bundle.allocation_snapshots:
            self._allocation_snapshots.setdefault(
                allocation_record.allocation_snapshot_id, allocation_record
            )

        return PortfolioExpansionPersistenceResult.succeeded(
            account_id=_bundle_account_id(bundle),
            records_persisted=(
                len(bundle.equity_history_points)
                + len(bundle.position_history)
                + len(bundle.position_latest)
                + len(bundle.exposure_snapshots)
                + len(bundle.risk_snapshots)
                + len(bundle.allocation_snapshots)
            ),
        )

    async def list_equity_history_points(
        self,
        *,
        account_id: str,
        source: str | None = None,
        timeframe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioEquityHistoryPointRecord]:
        return tuple(
            sorted(
                (
                    record
                    for record in self._equity_history.values()
                    if record.account_id == account_id
                    and (source is None or record.source == source)
                    and (timeframe is None or record.timeframe == timeframe)
                    and (start is None or record.observed_at >= start)
                    and (end is None or record.observed_at <= end)
                ),
                key=lambda record: (
                    record.observed_at,
                    record.portfolio_equity_history_point_id,
                ),
            )
        )

    async def list_position_history(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioPositionHistoryRecord]:
        normalized_symbol = symbol.upper() if symbol is not None else None
        return tuple(
            sorted(
                (
                    record
                    for record in self._position_history.values()
                    if record.account_id == account_id
                    and (
                        normalized_symbol is None or record.symbol == normalized_symbol
                    )
                    and (start is None or record.timestamp >= start)
                    and (end is None or record.timestamp <= end)
                ),
                key=lambda record: (
                    record.timestamp,
                    record.symbol,
                    record.position_history_id,
                ),
            )
        )

    async def list_latest_positions(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
    ) -> Sequence[PortfolioPositionLatestRecord]:
        normalized_symbol = symbol.upper() if symbol is not None else None
        return tuple(
            sorted(
                (
                    record
                    for record in self._position_latest.values()
                    if record.account_id == account_id
                    and (
                        normalized_symbol is None or record.symbol == normalized_symbol
                    )
                ),
                key=lambda record: (
                    record.symbol,
                    record.position_latest_id,
                ),
            )
        )

    async def list_exposure_snapshots(
        self,
        *,
        account_id: str,
        exposure_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioExposureSnapshotRecord]:
        return tuple(
            sorted(
                (
                    record
                    for record in self._exposure_snapshots.values()
                    if record.account_id == account_id
                    and (exposure_type is None or record.exposure_type == exposure_type)
                    and (start is None or record.timestamp >= start)
                    and (end is None or record.timestamp <= end)
                ),
                key=lambda record: (
                    record.timestamp,
                    record.exposure_type,
                    record.exposure_name,
                ),
            )
        )

    async def list_risk_snapshots(
        self,
        *,
        account_id: str,
        risk_level: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioRiskSnapshotRecord]:
        return tuple(
            sorted(
                (
                    record
                    for record in self._risk_snapshots.values()
                    if record.account_id == account_id
                    and (risk_level is None or record.risk_level == risk_level)
                    and (start is None or record.timestamp >= start)
                    and (end is None or record.timestamp <= end)
                ),
                key=lambda record: (
                    record.timestamp,
                    record.risk_snapshot_id,
                ),
            )
        )

    async def list_allocation_snapshots(
        self,
        *,
        account_id: str,
        allocation_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioAllocationSnapshotRecord]:
        return tuple(
            sorted(
                (
                    record
                    for record in self._allocation_snapshots.values()
                    if record.account_id == account_id
                    and (
                        allocation_type is None
                        or record.allocation_type == allocation_type
                    )
                    and (start is None or record.timestamp >= start)
                    and (end is None or record.timestamp <= end)
                ),
                key=lambda record: (
                    record.timestamp,
                    record.allocation_type,
                    record.allocation_name,
                ),
            )
        )


def _bundle_account_id(bundle: PortfolioExpansionPersistenceBundle) -> str:
    for records in (
        bundle.equity_history_points,
        bundle.position_history,
        bundle.position_latest,
        bundle.exposure_snapshots,
        bundle.risk_snapshots,
        bundle.allocation_snapshots,
    ):
        if records:
            return records[0].account_id
    return "empty-portfolio-expansion-bundle"
