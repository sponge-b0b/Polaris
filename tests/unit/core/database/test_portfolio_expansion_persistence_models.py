from __future__ import annotations

from typing import cast

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.portfolio import PortfolioAllocationSnapshotModel
from core.database.models.portfolio import PortfolioEquityHistoryPointModel
from core.database.models.portfolio import PortfolioExposureSnapshotModel
from core.database.models.portfolio import PortfolioPositionHistoryModel
from core.database.models.portfolio import PortfolioPositionLatestModel
from core.database.models.portfolio import PortfolioRiskSnapshotModel


def test_portfolio_expansion_models_are_imported_into_base_metadata() -> None:
    assert "portfolio_equity_history_points" in Base.metadata.tables
    assert "portfolio_positions_history" in Base.metadata.tables
    assert "portfolio_positions_latest" in Base.metadata.tables
    assert "portfolio_exposure_snapshots" in Base.metadata.tables
    assert "portfolio_risk_snapshots" in Base.metadata.tables
    assert "portfolio_allocation_snapshots" in Base.metadata.tables


def test_portfolio_equity_history_model_uses_normalized_natural_key() -> None:
    table = PortfolioEquityHistoryPointModel.__table__
    columns = table.c

    assert _primary_key_names(table) == {"portfolio_equity_history_point_id"}
    assert isinstance(columns.observed_at.type, DateTime)
    assert columns.observed_at.type.timezone is True
    assert columns.equity.nullable is False
    assert columns.profit_loss.nullable is False
    assert columns.profit_loss_pct.nullable is True
    assert columns.base_value.nullable is True
    assert isinstance(columns.cashflow_payload.type, JSONB)
    assert "uq_portfolio_equity_history_natural_key" in _unique_constraint_names(table)


def test_portfolio_position_history_model_persists_position_facts() -> None:
    columns = PortfolioPositionHistoryModel.__table__.c
    primary_keys = _primary_key_names(PortfolioPositionHistoryModel.__table__)
    foreign_keys = _foreign_key_targets(columns.snapshot_id)

    assert primary_keys == {"position_history_id"}
    assert columns.account_id.nullable is False
    assert columns.symbol.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.snapshot_id.nullable is True
    assert columns.quantity.nullable is False
    assert columns.market_value.nullable is False
    assert columns.cost_basis.nullable is True
    assert columns.exposure_weight.nullable is True
    assert columns.sector.nullable is True
    assert columns.theme.nullable is True
    assert columns.beta.nullable is True
    assert columns.risk_weight.nullable is True
    assert foreign_keys == {"portfolio_state_history.snapshot_id"}


def test_portfolio_position_latest_model_supports_account_symbol_upsert() -> None:
    columns = PortfolioPositionLatestModel.__table__.c
    primary_keys = _primary_key_names(PortfolioPositionLatestModel.__table__)
    unique_constraints = _unique_constraint_names(
        PortfolioPositionLatestModel.__table__
    )

    assert primary_keys == {"position_latest_id"}
    assert columns.account_id.nullable is False
    assert columns.symbol.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.quantity.nullable is False
    assert columns.market_value.nullable is False
    assert "uq_portfolio_positions_latest_account_symbol" in unique_constraints


def test_portfolio_position_models_include_canonical_position_output_columns() -> None:
    float_columns = {
        "qty_available",
        "entry_price",
        "current_price",
        "lastday_price",
        "change_today",
        "signed_market_value",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "unrealized_intraday_pnl",
        "unrealized_intraday_pnl_pct",
        "exposure_weight",
        "beta",
        "swap_rate",
        "avg_entry_swap_rate",
    }
    string_columns = {
        "side",
        "asset_id",
        "exchange",
        "asset_class",
        "sector",
    }

    for model in (PortfolioPositionHistoryModel, PortfolioPositionLatestModel):
        columns = model.__table__.c

        assert "weight" not in columns
        assert isinstance(columns.asset_marginable.type, Boolean)
        assert columns.asset_marginable.nullable is True

        for column_name in float_columns:
            assert isinstance(columns[column_name].type, Float)
            assert columns[column_name].nullable is True

        for column_name in string_columns:
            assert isinstance(columns[column_name].type, String)
            assert columns[column_name].nullable is True


def test_portfolio_exposure_snapshot_model_persists_exposure_dimensions() -> None:
    columns = PortfolioExposureSnapshotModel.__table__.c
    primary_keys = _primary_key_names(PortfolioExposureSnapshotModel.__table__)

    assert primary_keys == {"exposure_snapshot_id"}
    assert columns.account_id.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.snapshot_id.nullable is True
    assert columns.exposure_type.nullable is False
    assert columns.exposure_name.nullable is False
    assert columns.exposure_value.nullable is False
    assert columns.weight.nullable is True
    assert columns.beta.nullable is True
    assert columns.risk_weight.nullable is True


def test_portfolio_risk_snapshot_model_aligns_with_v1_state_risk_fields() -> None:
    columns = PortfolioRiskSnapshotModel.__table__.c
    primary_keys = _primary_key_names(PortfolioRiskSnapshotModel.__table__)

    assert primary_keys == {"risk_snapshot_id"}
    assert columns.account_id.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.snapshot_id.nullable is True
    assert columns.portfolio_value.nullable is True
    assert columns.cash.nullable is True
    assert columns.account_health.nullable is True
    assert columns.risk_score.nullable is True
    assert columns.risk_level.nullable is True
    assert columns.drawdown_risk.nullable is True
    assert columns.volatility_risk.nullable is True
    assert columns.concentration_risk.nullable is True
    assert columns.liquidity_risk.nullable is True
    assert columns.cash_ratio.nullable is True
    assert columns.equity_retention_ratio.nullable is True


def test_portfolio_allocation_snapshot_model_persists_allocation_drift() -> None:
    columns = PortfolioAllocationSnapshotModel.__table__.c
    primary_keys = _primary_key_names(PortfolioAllocationSnapshotModel.__table__)

    assert primary_keys == {"allocation_snapshot_id"}
    assert columns.account_id.nullable is False
    assert columns.timestamp.nullable is False
    assert columns.snapshot_id.nullable is True
    assert columns.allocation_type.nullable is False
    assert columns.allocation_name.nullable is False
    assert columns.current_weight.nullable is False
    assert columns.target_weight.nullable is True
    assert columns.drift.nullable is True
    assert columns.market_value.nullable is True


def test_portfolio_expansion_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(PortfolioPositionHistoryModel.__table__.c.metadata.type, JSONB)
    assert isinstance(
        PortfolioPositionHistoryModel.__table__.c.position_payload.type,
        JSONB,
    )
    assert isinstance(
        PortfolioPositionHistoryModel.__table__.c.position_risk_payload.type,
        JSONB,
    )
    assert isinstance(PortfolioPositionLatestModel.__table__.c.metadata.type, JSONB)
    assert isinstance(
        PortfolioPositionLatestModel.__table__.c.position_payload.type,
        JSONB,
    )
    assert isinstance(
        PortfolioPositionLatestModel.__table__.c.position_risk_payload.type,
        JSONB,
    )
    assert isinstance(PortfolioExposureSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(PortfolioRiskSnapshotModel.__table__.c.risk_signals.type, JSONB)
    assert isinstance(PortfolioRiskSnapshotModel.__table__.c.metadata.type, JSONB)
    assert isinstance(PortfolioAllocationSnapshotModel.__table__.c.metadata.type, JSONB)


def test_portfolio_expansion_models_include_lineage_and_row_timestamps() -> None:
    for table in (
        PortfolioEquityHistoryPointModel.__table__,
        PortfolioPositionHistoryModel.__table__,
        PortfolioPositionLatestModel.__table__,
        PortfolioExposureSnapshotModel.__table__,
        PortfolioRiskSnapshotModel.__table__,
        PortfolioAllocationSnapshotModel.__table__,
    ):
        columns = table.c

        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.runtime_id.nullable is True
        assert columns.node_name.nullable is True
        assert columns.row_created_at.server_default is not None
        assert columns.row_updated_at.server_default is not None


def test_portfolio_expansion_models_index_core_query_paths() -> None:
    equity_history_indexes = _index_names(PortfolioEquityHistoryPointModel.__table__)
    history_indexes = _index_names(PortfolioPositionHistoryModel.__table__)
    latest_indexes = _index_names(PortfolioPositionLatestModel.__table__)
    exposure_indexes = _index_names(PortfolioExposureSnapshotModel.__table__)
    risk_indexes = _index_names(PortfolioRiskSnapshotModel.__table__)
    allocation_indexes = _index_names(PortfolioAllocationSnapshotModel.__table__)

    assert "idx_portfolio_equity_history_account_observed_at" in equity_history_indexes
    assert "idx_portfolio_equity_history_workflow_execution" in equity_history_indexes
    assert "idx_portfolio_positions_history_account_timestamp" in history_indexes
    assert "idx_portfolio_positions_history_symbol_timestamp" in history_indexes
    assert "idx_portfolio_positions_history_workflow_execution" in history_indexes
    assert "idx_portfolio_positions_latest_account_symbol" in latest_indexes
    assert "idx_portfolio_positions_latest_workflow_execution" in latest_indexes
    assert "idx_portfolio_exposure_snapshots_account_timestamp" in exposure_indexes
    assert "idx_portfolio_exposure_snapshots_type_name" in exposure_indexes
    assert "idx_portfolio_exposure_snapshots_workflow_execution" in exposure_indexes
    assert "idx_portfolio_risk_snapshots_account_timestamp" in risk_indexes
    assert "idx_portfolio_risk_snapshots_risk_level_timestamp" in risk_indexes
    assert "idx_portfolio_risk_snapshots_workflow_execution" in risk_indexes
    assert "idx_portfolio_allocation_snapshots_account_timestamp" in allocation_indexes
    assert "idx_portfolio_allocation_snapshots_type_name" in allocation_indexes
    assert "idx_portfolio_allocation_snapshots_workflow_execution" in allocation_indexes


def _primary_key_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {column.name for column in sqlalchemy_table.primary_key}


def _foreign_key_targets(column: object) -> set[str]:
    sqlalchemy_column = cast(object, column)
    return {
        foreign_key.target_fullname
        for foreign_key in sqlalchemy_column.foreign_keys  # type: ignore[attr-defined]
    }


def _unique_constraint_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    names: set[str] = set()
    for constraint in sqlalchemy_table.constraints:
        if not isinstance(constraint, UniqueConstraint):
            continue
        if isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def _index_names(table: object) -> set[str]:
    sqlalchemy_table = cast(Table, table)
    return {index.name for index in sqlalchemy_table.indexes if index.name is not None}
