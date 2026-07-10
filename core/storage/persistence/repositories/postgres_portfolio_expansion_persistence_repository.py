from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.portfolio import PortfolioAllocationSnapshotModel
from core.database.models.portfolio import PortfolioEquityHistoryPointModel
from core.database.models.portfolio import PortfolioExposureSnapshotModel
from core.database.models.portfolio import PortfolioPositionHistoryModel
from core.database.models.portfolio import PortfolioPositionLatestModel
from core.database.models.portfolio import PortfolioRiskSnapshotModel
from core.storage.persistence.portfolio import PortfolioAllocationSnapshotRecord
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceBundle
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceResult
from core.storage.persistence.portfolio import PortfolioEquityHistoryPointRecord
from core.storage.persistence.portfolio import PortfolioExposureSnapshotRecord
from core.storage.persistence.portfolio import PortfolioPositionHistoryRecord
from core.storage.persistence.portfolio import PortfolioPositionLatestRecord
from core.storage.persistence.portfolio import PortfolioRiskSnapshotRecord
from core.storage.persistence.portfolio.portfolio_persistence_repository import (
    PortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.serializers.portfolio_persistence_serializer import (
    PortfolioPersistenceSerializer,
)


class PostgresPortfolioExpansionPersistenceRepository(
    PortfolioExpansionPersistenceRepository,
):
    """
    PostgreSQL adapter for durable curated portfolio expansion persistence.

    Position latest records are upserted by the account/symbol natural key.
    Position history and exposure/risk/allocation snapshots are insert-only
    append records, preserving historical observations without mutation.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_portfolio_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult:
        try:
            for equity_history_point in bundle.equity_history_points:
                await self._session.execute(
                    _insert_equity_history_point_statement(equity_history_point)
                )
            for history_record in bundle.position_history:
                await self._session.execute(
                    _insert_position_history_statement(
                        history_record,
                    )
                )
            for latest_record in bundle.position_latest:
                await self._session.execute(
                    _upsert_position_latest_statement(
                        latest_record,
                    )
                )
            for exposure_record in bundle.exposure_snapshots:
                await self._session.execute(
                    _insert_exposure_snapshot_statement(
                        exposure_record,
                    )
                )
            for risk_record in bundle.risk_snapshots:
                await self._session.execute(
                    _insert_risk_snapshot_statement(
                        risk_record,
                    )
                )
            for allocation_record in bundle.allocation_snapshots:
                await self._session.execute(
                    _insert_allocation_snapshot_statement(
                        allocation_record,
                    )
                )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return PortfolioExpansionPersistenceResult.failed(
                str(exc),
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
        stmt = select(PortfolioEquityHistoryPointModel).where(
            PortfolioEquityHistoryPointModel.account_id == account_id,
        )
        if source is not None:
            stmt = stmt.where(PortfolioEquityHistoryPointModel.source == source)
        if timeframe is not None:
            stmt = stmt.where(PortfolioEquityHistoryPointModel.timeframe == timeframe)
        if start is not None:
            stmt = stmt.where(PortfolioEquityHistoryPointModel.observed_at >= start)
        if end is not None:
            stmt = stmt.where(PortfolioEquityHistoryPointModel.observed_at <= end)
        stmt = stmt.order_by(
            PortfolioEquityHistoryPointModel.observed_at,
            PortfolioEquityHistoryPointModel.portfolio_equity_history_point_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            PortfolioPersistenceSerializer.equity_history_point_from_model(model)
            for model in result.scalars().all()
        )

    async def list_position_history(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioPositionHistoryRecord]:
        stmt = select(PortfolioPositionHistoryModel).where(
            PortfolioPositionHistoryModel.account_id == account_id,
        )
        if symbol is not None:
            stmt = stmt.where(
                PortfolioPositionHistoryModel.symbol == symbol.upper(),
            )
        if start is not None:
            stmt = stmt.where(
                PortfolioPositionHistoryModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                PortfolioPositionHistoryModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            PortfolioPositionHistoryModel.timestamp,
            PortfolioPositionHistoryModel.symbol,
            PortfolioPositionHistoryModel.position_history_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PortfolioPersistenceSerializer.position_history_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_latest_positions(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
    ) -> Sequence[PortfolioPositionLatestRecord]:
        stmt = select(PortfolioPositionLatestModel).where(
            PortfolioPositionLatestModel.account_id == account_id,
        )
        if symbol is not None:
            stmt = stmt.where(
                PortfolioPositionLatestModel.symbol == symbol.upper(),
            )
        stmt = stmt.order_by(
            PortfolioPositionLatestModel.symbol,
            PortfolioPositionLatestModel.position_latest_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PortfolioPersistenceSerializer.position_latest_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_exposure_snapshots(
        self,
        *,
        account_id: str,
        exposure_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioExposureSnapshotRecord]:
        stmt = select(PortfolioExposureSnapshotModel).where(
            PortfolioExposureSnapshotModel.account_id == account_id,
        )
        if exposure_type is not None:
            stmt = stmt.where(
                PortfolioExposureSnapshotModel.exposure_type == exposure_type,
            )
        if start is not None:
            stmt = stmt.where(
                PortfolioExposureSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                PortfolioExposureSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            PortfolioExposureSnapshotModel.timestamp,
            PortfolioExposureSnapshotModel.exposure_type,
            PortfolioExposureSnapshotModel.exposure_name,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PortfolioPersistenceSerializer.exposure_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_risk_snapshots(
        self,
        *,
        account_id: str,
        risk_level: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioRiskSnapshotRecord]:
        stmt = select(PortfolioRiskSnapshotModel).where(
            PortfolioRiskSnapshotModel.account_id == account_id,
        )
        if risk_level is not None:
            stmt = stmt.where(
                PortfolioRiskSnapshotModel.risk_level == risk_level,
            )
        if start is not None:
            stmt = stmt.where(
                PortfolioRiskSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                PortfolioRiskSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            PortfolioRiskSnapshotModel.timestamp,
            PortfolioRiskSnapshotModel.risk_snapshot_id,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PortfolioPersistenceSerializer.risk_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_allocation_snapshots(
        self,
        *,
        account_id: str,
        allocation_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioAllocationSnapshotRecord]:
        stmt = select(PortfolioAllocationSnapshotModel).where(
            PortfolioAllocationSnapshotModel.account_id == account_id,
        )
        if allocation_type is not None:
            stmt = stmt.where(
                PortfolioAllocationSnapshotModel.allocation_type == allocation_type,
            )
        if start is not None:
            stmt = stmt.where(
                PortfolioAllocationSnapshotModel.timestamp >= start,
            )
        if end is not None:
            stmt = stmt.where(
                PortfolioAllocationSnapshotModel.timestamp <= end,
            )
        stmt = stmt.order_by(
            PortfolioAllocationSnapshotModel.timestamp,
            PortfolioAllocationSnapshotModel.allocation_type,
            PortfolioAllocationSnapshotModel.allocation_name,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PortfolioPersistenceSerializer.allocation_snapshot_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _insert_equity_history_point_statement(
    record: PortfolioEquityHistoryPointRecord,
) -> Any:
    values = PortfolioPersistenceSerializer.equity_history_point_values(record)
    return (
        insert(PortfolioEquityHistoryPointModel)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=["account_id", "source", "timeframe", "observed_at"],
        )
    )


def _insert_position_history_statement(
    record: PortfolioPositionHistoryRecord,
) -> Any:
    return insert(PortfolioPositionHistoryModel).values(
        **PortfolioPersistenceSerializer.position_history_values(record)
    )


def _upsert_position_latest_statement(
    record: PortfolioPositionLatestRecord,
) -> Any:
    values = PortfolioPersistenceSerializer.position_latest_values(record)
    stmt = insert(PortfolioPositionLatestModel).values(**values)
    excluded = stmt.excluded

    return stmt.on_conflict_do_update(
        index_elements=["account_id", "symbol"],
        set_={
            "position_latest_id": excluded.position_latest_id,
            "timestamp": excluded.timestamp,
            "snapshot_id": excluded.snapshot_id,
            "quantity": excluded.quantity,
            "market_value": excluded.market_value,
            "cost_basis": excluded.cost_basis,
            "exposure_weight": excluded.exposure_weight,
            "sector": excluded.sector,
            "theme": excluded.theme,
            "beta": excluded.beta,
            "risk_weight": excluded.risk_weight,
            "workflow_name": excluded.workflow_name,
            "execution_id": excluded.execution_id,
            "runtime_id": excluded.runtime_id,
            "node_name": excluded.node_name,
            "metadata": excluded.metadata,
            "row_updated_at": func.now(),
        },
    )


def _insert_exposure_snapshot_statement(
    record: PortfolioExposureSnapshotRecord,
) -> Any:
    return insert(PortfolioExposureSnapshotModel).values(
        **PortfolioPersistenceSerializer.exposure_snapshot_values(record)
    )


def _insert_risk_snapshot_statement(
    record: PortfolioRiskSnapshotRecord,
) -> Any:
    return insert(PortfolioRiskSnapshotModel).values(
        **PortfolioPersistenceSerializer.risk_snapshot_values(record)
    )


def _insert_allocation_snapshot_statement(
    record: PortfolioAllocationSnapshotRecord,
) -> Any:
    return insert(PortfolioAllocationSnapshotModel).values(
        **PortfolioPersistenceSerializer.allocation_snapshot_values(record)
    )


def _bundle_account_id(
    bundle: PortfolioExpansionPersistenceBundle,
) -> str:
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
