from __future__ import annotations

from collections import Counter
from dataclasses import fields
from datetime import datetime
from datetime import timezone
import ast

from sqlalchemy import Boolean
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB

from core.database.models.portfolio_state import PortfolioStateHistoryModel
from core.database.models.portfolio_state import PortfolioStateLatestModel
from core.storage.persistence.serializers.portfolio_state_serializer import (
    PortfolioStateSerializer,
)
from domain.portfolio.models.portfolio_state import PortfolioState


def build_portfolio_state() -> PortfolioState:
    return PortfolioState(
        snapshot_id="snapshot-1",
        account_id="account-1",
        timestamp=datetime(2026, 5, 30, tzinfo=timezone.utc),
        schema_version=2,
        equity=100_000.123456,
        peak_equity=105_000.234567,
        portfolio_value=98_000.345678,
        cash=15_000.456789,
        buying_power=20_000.567891,
        last_equity=99_000.678912,
        cash_ratio=0.15306122448979592,
        buying_power_ratio=0.20408163265306123,
        realized_pnl=1_250.789123,
        realized_pnl_pct=0.01250789123,
        unrealized_pnl=-500.891234,
        unrealized_pnl_pct=-0.00500891234,
        unrealized_intraday_pnl=125.912345,
        unrealized_intraday_pnl_pct=0.00125912345,
        pnl_total=750.123456,
        pnl_total_pct=0.00750123456,
        drawdown_absolute=7_000.234567,
        drawdown_percent=0.0666688888,
        capital_base=100_000.0,
        equity_retention_ratio=0.98000345678,
        long_market_value=80_000.111111,
        short_market_value=-12_000.222222,
        gross_market_value=92_000.333333,
        net_market_value=68_000.444444,
        gross_exposure=0.93877891234,
        net_exposure=0.69388123456,
        long_exposure=0.81632888888,
        short_exposure=0.12244777777,
        leverage=0.93877999999,
        largest_position_pct=0.21456789123,
        concentration_score=0.36567891234,
        diversification_score=0.73456789123,
        beta_exposure=1.087654321,
        beta_risk=0.187654321,
        portfolio_heat=0.276543219,
        risk_intensity=0.323456789,
        initial_margin=10_000.111111,
        maintenance_margin=8_000.222222,
        last_maintenance_margin=7_500.333333,
        margin_utilization_ratio=0.1666677777,
        initial_margin_ratio=0.10204012345,
        daytrade_count=2,
        pattern_day_trader=True,
        trading_blocked=False,
        transfers_blocked=True,
        account_blocked=False,
        trade_suspended_by_user=True,
        shorting_enabled=True,
        position_count=7,
        portfolio_regime="risk_on",
        directional_bias="bullish",
        account_health="healthy",
        sector_exposure={
            "technology": 0.423456789,
            "healthcare": 0.176543211,
        },
        asset_class_exposure={
            "us_equity": 0.812345678,
            "cash": 0.15306122448979592,
        },
        risk_signals={
            "drawdown": {"severity": "contained", "score": 0.0666688888},
            "margin": {"severity": "normal", "score": 0.1666677777},
        },
    )


def test_portfolio_state_models_use_postgres_jsonb() -> None:
    for model in (PortfolioStateHistoryModel, PortfolioStateLatestModel):
        columns = model.__table__.c

        assert isinstance(columns.risk_signals_payload.type, JSONB)
        assert isinstance(columns.portfolio_state_payload.type, JSONB)
        assert isinstance(columns.equity_state_payload.type, JSONB)
        assert isinstance(columns.sector_exposure.type, JSONB)
        assert isinstance(columns.asset_class_exposure.type, JSONB)


def test_portfolio_state_models_mirror_v2_domain_columns() -> None:
    expected_columns = {
        _canonical_database_column_name(field_name)
        for field_name in PortfolioState.__dataclass_fields__
    }

    for model in (PortfolioStateHistoryModel, PortfolioStateLatestModel):
        columns = set(model.__table__.c.keys())

        assert expected_columns <= columns


def test_portfolio_state_models_use_v2_sqlalchemy_types() -> None:
    float_columns = {
        "equity",
        "peak_equity",
        "portfolio_value",
        "cash",
        "buying_power",
        "last_equity",
        "cash_pct",
        "buying_power_ratio",
        "realized_pnl",
        "realized_pnl_pct",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "unrealized_intraday_pnl",
        "unrealized_intraday_pnl_pct",
        "pnl_total",
        "pnl_total_pct",
        "drawdown_absolute",
        "drawdown_percent",
        "capital_base",
        "equity_retention_ratio",
        "long_market_value",
        "short_market_value",
        "gross_market_value",
        "net_market_value",
        "gross_exposure",
        "net_exposure",
        "long_exposure",
        "short_exposure",
        "leverage",
        "largest_position_pct",
        "concentration_score",
        "diversification_score",
        "beta_exposure",
        "beta_risk",
        "portfolio_heat",
        "risk_intensity",
        "initial_margin",
        "maintenance_margin",
        "last_maintenance_margin",
        "margin_utilization_ratio",
        "initial_margin_ratio",
        "regt_buying_power",
        "daytrading_buying_power",
        "non_marginable_buying_power",
        "options_buying_power",
        "multiplier",
        "accrued_fees",
        "pending_transfer_in",
        "pending_transfer_out",
    }
    integer_columns = {
        "schema_version",
        "daytrade_count",
        "position_count",
        "options_approved_level",
        "options_trading_level",
    }
    boolean_columns = {
        "pattern_day_trader",
        "trading_blocked",
        "transfers_blocked",
        "account_blocked",
        "trade_suspended_by_user",
        "shorting_enabled",
    }
    string_columns = {
        "snapshot_id",
        "account_id",
        "workflow_name",
        "execution_id",
        "portfolio_regime",
        "directional_bias",
        "account_health",
        "account_number",
        "status",
        "currency",
    }

    for model in (PortfolioStateHistoryModel, PortfolioStateLatestModel):
        columns = model.__table__.c

        for column_name in float_columns:
            assert isinstance(columns[column_name].type, Float)

        for column_name in integer_columns:
            assert isinstance(columns[column_name].type, Integer)

        for column_name in boolean_columns:
            assert isinstance(columns[column_name].type, Boolean)

        for column_name in string_columns:
            assert isinstance(columns[column_name].type, String)


def test_portfolio_state_models_use_canonical_database_column_names() -> None:
    for model in (PortfolioStateHistoryModel, PortfolioStateLatestModel):
        columns = model.__table__.c

        assert "cash_pct" in columns
        assert "cash_ratio" not in columns
        assert "risk_signals_payload" in columns
        assert "risk_signals" not in columns

        for column_name in (
            "account_number",
            "status",
            "currency",
            "regt_buying_power",
            "daytrading_buying_power",
            "non_marginable_buying_power",
            "options_buying_power",
            "multiplier",
            "accrued_fees",
            "pending_transfer_in",
            "pending_transfer_out",
            "options_approved_level",
            "options_trading_level",
            "portfolio_state_payload",
            "equity_state_payload",
        ):
            assert column_name in columns
            assert columns[column_name].nullable is True or column_name.endswith(
                "_payload"
            )


def test_portfolio_state_models_keep_account_health_nullable() -> None:
    assert PortfolioStateHistoryModel.__table__.c.account_health.nullable is True
    assert PortfolioStateLatestModel.__table__.c.account_health.nullable is True


def test_portfolio_state_models_do_not_define_duplicate_mapped_columns() -> None:
    source = ast.parse(
        open(
            "core/database/models/portfolio_state.py",
            encoding="utf-8",
        ).read(),
        filename="core/database/models/portfolio_state.py",
    )
    target_classes = {
        "PortfolioStateHistoryModel",
        "PortfolioStateLatestModel",
    }

    for node in source.body:
        if not isinstance(node, ast.ClassDef) or node.name not in target_classes:
            continue

        assignments = [
            statement.target.id
            for statement in node.body
            if isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
        ]
        duplicate_names = {
            name for name, count in Counter(assignments).items() if count > 1
        }

        assert duplicate_names == set()


def test_portfolio_state_models_include_lineage_and_timestamps() -> None:
    history_columns = PortfolioStateHistoryModel.__table__.c
    latest_columns = PortfolioStateLatestModel.__table__.c

    for columns in (history_columns, latest_columns):
        assert "workflow_name" in columns
        assert "execution_id" in columns
        assert columns.workflow_name.nullable is True
        assert columns.execution_id.nullable is True
        assert columns.created_at.server_default is not None
        assert columns.updated_at.server_default is not None


def test_portfolio_state_serializer_preserves_all_v2_domain_fields() -> None:
    state = build_portfolio_state()

    history_model = PortfolioStateSerializer.to_history_model(state)
    latest_model = PortfolioStateSerializer.to_latest_model(state)
    restored_state = PortfolioStateSerializer.from_latest_model(latest_model)

    for field in fields(PortfolioState):
        assert getattr(history_model, field.name) == getattr(state, field.name)
        assert getattr(latest_model, field.name) == getattr(state, field.name)

    assert restored_state == state


def test_portfolio_state_serializer_hydrates_legacy_nullable_fields() -> None:
    state = build_portfolio_state()
    latest_model = PortfolioStateSerializer.to_latest_model(state)
    latest_model.account_health = None
    latest_model.portfolio_regime = None
    latest_model.directional_bias = None
    latest_model.risk_signals = None
    latest_model.sector_exposure = None
    latest_model.asset_class_exposure = None

    restored_state = PortfolioStateSerializer.from_latest_model(latest_model)

    assert restored_state.account_health == "unknown"
    assert restored_state.portfolio_regime == "unknown"
    assert restored_state.directional_bias == "neutral"
    assert restored_state.risk_signals == {}
    assert restored_state.sector_exposure == {}
    assert restored_state.asset_class_exposure == {}


def _canonical_database_column_name(
    domain_field_name: str,
) -> str:
    return {
        "cash_ratio": "cash_pct",
        "risk_signals": "risk_signals_payload",
    }.get(domain_field_name, domain_field_name)
