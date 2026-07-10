from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.portfolio import PortfolioAllocationSnapshotModel
from core.database.models.portfolio import PortfolioEquityHistoryPointModel
from core.database.models.portfolio import PortfolioExposureSnapshotModel
from core.database.models.portfolio import PortfolioPositionHistoryModel
from core.database.models.portfolio import PortfolioPositionLatestModel
from core.database.models.portfolio import PortfolioRiskSnapshotModel
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.portfolio import PortfolioAllocationSnapshotRecord
from core.storage.persistence.portfolio import PortfolioEquityHistoryPointRecord
from core.storage.persistence.portfolio import PortfolioExposureSnapshotRecord
from core.storage.persistence.portfolio import PortfolioPositionHistoryRecord
from core.storage.persistence.portfolio import PortfolioPositionLatestRecord
from core.storage.persistence.portfolio import PortfolioRiskSnapshotRecord


class PortfolioPersistenceSerializer:
    """
    Serializer between typed portfolio expansion records and SQLAlchemy models.

    JSON dictionaries are introduced only at this database persistence boundary.
    Portfolio/application layers should use typed portfolio records internally
    and serialize when crossing into Postgres, telemetry, replay, or checkpoint
    boundaries.
    """

    @staticmethod
    def equity_history_point_values(
        record: PortfolioEquityHistoryPointRecord,
    ) -> dict[str, Any]:
        return {
            "portfolio_equity_history_point_id": (
                record.portfolio_equity_history_point_id
            ),
            "account_id": record.account_id,
            "source": record.source,
            "timeframe": record.timeframe,
            "observed_at": record.observed_at,
            "equity": record.equity,
            "profit_loss": record.profit_loss,
            "profit_loss_pct": record.profit_loss_pct,
            "base_value": record.base_value,
            "cashflow_payload": dict(record.cashflow_payload),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
        }

    @staticmethod
    def position_history_values(
        record: PortfolioPositionHistoryRecord,
    ) -> dict[str, Any]:
        return {
            "position_history_id": record.position_history_id,
            "account_id": record.account_id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "snapshot_id": record.snapshot_id,
            "quantity": record.quantity,
            "market_value": record.market_value,
            "cost_basis": record.cost_basis,
            "weight": record.weight,
            "sector": record.sector,
            "theme": record.theme,
            "beta": record.beta,
            "risk_weight": record.risk_weight,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def position_latest_values(
        record: PortfolioPositionLatestRecord,
    ) -> dict[str, Any]:
        return {
            "position_latest_id": record.position_latest_id,
            "account_id": record.account_id,
            "symbol": record.symbol,
            "timestamp": record.timestamp,
            "snapshot_id": record.snapshot_id,
            "quantity": record.quantity,
            "market_value": record.market_value,
            "cost_basis": record.cost_basis,
            "weight": record.weight,
            "sector": record.sector,
            "theme": record.theme,
            "beta": record.beta,
            "risk_weight": record.risk_weight,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def exposure_snapshot_values(
        record: PortfolioExposureSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "exposure_snapshot_id": record.exposure_snapshot_id,
            "account_id": record.account_id,
            "timestamp": record.timestamp,
            "snapshot_id": record.snapshot_id,
            "exposure_type": record.exposure_type,
            "exposure_name": record.exposure_name,
            "exposure_value": record.exposure_value,
            "weight": record.weight,
            "beta": record.beta,
            "risk_weight": record.risk_weight,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def risk_snapshot_values(
        record: PortfolioRiskSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "risk_snapshot_id": record.risk_snapshot_id,
            "account_id": record.account_id,
            "timestamp": record.timestamp,
            "snapshot_id": record.snapshot_id,
            "portfolio_value": record.portfolio_value,
            "cash": record.cash,
            "account_health": record.account_health,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "drawdown_risk": record.drawdown_risk,
            "volatility_risk": record.volatility_risk,
            "concentration_risk": record.concentration_risk,
            "liquidity_risk": record.liquidity_risk,
            "beta": record.beta,
            "cash_ratio": record.cash_ratio,
            "equity_retention_ratio": record.equity_retention_ratio,
            "risk_signals": dict(record.risk_signals),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def allocation_snapshot_values(
        record: PortfolioAllocationSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "allocation_snapshot_id": record.allocation_snapshot_id,
            "account_id": record.account_id,
            "timestamp": record.timestamp,
            "snapshot_id": record.snapshot_id,
            "allocation_type": record.allocation_type,
            "allocation_name": record.allocation_name,
            "current_weight": record.current_weight,
            "target_weight": record.target_weight,
            "drift": record.drift,
            "market_value": record.market_value,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def equity_history_point_from_model(
        model: PortfolioEquityHistoryPointModel,
    ) -> PortfolioEquityHistoryPointRecord:
        return PortfolioEquityHistoryPointRecord(
            portfolio_equity_history_point_id=(model.portfolio_equity_history_point_id),
            account_id=model.account_id,
            source=model.source,
            timeframe=model.timeframe,
            observed_at=model.observed_at,
            equity=model.equity,
            profit_loss=model.profit_loss,
            profit_loss_pct=model.profit_loss_pct,
            base_value=model.base_value,
            cashflow_payload=cast(JsonObject, model.cashflow_payload),
            lineage=_lineage_from_model(model),
        )

    @staticmethod
    def position_history_from_model(
        model: PortfolioPositionHistoryModel,
    ) -> PortfolioPositionHistoryRecord:
        return PortfolioPositionHistoryRecord(
            position_history_id=model.position_history_id,
            account_id=model.account_id,
            symbol=model.symbol,
            timestamp=model.timestamp,
            snapshot_id=model.snapshot_id,
            quantity=model.quantity,
            market_value=model.market_value,
            cost_basis=model.cost_basis,
            weight=model.weight,
            sector=model.sector,
            theme=model.theme,
            beta=model.beta,
            risk_weight=model.risk_weight,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def position_latest_from_model(
        model: PortfolioPositionLatestModel,
    ) -> PortfolioPositionLatestRecord:
        return PortfolioPositionLatestRecord(
            position_latest_id=model.position_latest_id,
            account_id=model.account_id,
            symbol=model.symbol,
            timestamp=model.timestamp,
            snapshot_id=model.snapshot_id,
            quantity=model.quantity,
            market_value=model.market_value,
            cost_basis=model.cost_basis,
            weight=model.weight,
            sector=model.sector,
            theme=model.theme,
            beta=model.beta,
            risk_weight=model.risk_weight,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def exposure_snapshot_from_model(
        model: PortfolioExposureSnapshotModel,
    ) -> PortfolioExposureSnapshotRecord:
        return PortfolioExposureSnapshotRecord(
            exposure_snapshot_id=model.exposure_snapshot_id,
            account_id=model.account_id,
            timestamp=model.timestamp,
            snapshot_id=model.snapshot_id,
            exposure_type=model.exposure_type,
            exposure_name=model.exposure_name,
            exposure_value=model.exposure_value,
            weight=model.weight,
            beta=model.beta,
            risk_weight=model.risk_weight,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def risk_snapshot_from_model(
        model: PortfolioRiskSnapshotModel,
    ) -> PortfolioRiskSnapshotRecord:
        return PortfolioRiskSnapshotRecord(
            risk_snapshot_id=model.risk_snapshot_id,
            account_id=model.account_id,
            timestamp=model.timestamp,
            snapshot_id=model.snapshot_id,
            portfolio_value=model.portfolio_value,
            cash=model.cash,
            account_health=model.account_health,
            risk_score=model.risk_score,
            risk_level=model.risk_level,
            drawdown_risk=model.drawdown_risk,
            volatility_risk=model.volatility_risk,
            concentration_risk=model.concentration_risk,
            liquidity_risk=model.liquidity_risk,
            beta=model.beta,
            cash_ratio=model.cash_ratio,
            equity_retention_ratio=model.equity_retention_ratio,
            risk_signals=cast(JsonObject, model.risk_signals),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def allocation_snapshot_from_model(
        model: PortfolioAllocationSnapshotModel,
    ) -> PortfolioAllocationSnapshotRecord:
        return PortfolioAllocationSnapshotRecord(
            allocation_snapshot_id=model.allocation_snapshot_id,
            account_id=model.account_id,
            timestamp=model.timestamp,
            snapshot_id=model.snapshot_id,
            allocation_type=model.allocation_type,
            allocation_name=model.allocation_name,
            current_weight=model.current_weight,
            target_weight=model.target_weight,
            drift=model.drift,
            market_value=model.market_value,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(
    model: Any,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
