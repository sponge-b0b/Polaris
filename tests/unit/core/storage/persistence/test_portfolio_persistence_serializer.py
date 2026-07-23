from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.portfolio import (
    PortfolioAllocationSnapshotModel,
    PortfolioEquityHistoryPointModel,
    PortfolioExposureSnapshotModel,
    PortfolioPositionHistoryModel,
    PortfolioPositionLatestModel,
    PortfolioRiskSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.portfolio import (
    PortfolioAllocationSnapshotRecord,
    PortfolioEquityHistoryPointRecord,
    PortfolioExposureSnapshotRecord,
    PortfolioPositionHistoryRecord,
    PortfolioPositionLatestRecord,
    PortfolioRiskSnapshotRecord,
)
from core.storage.persistence.serializers.portfolio_persistence_serializer import (
    PortfolioPersistenceSerializer,
)


def test_portfolio_serializer_round_trips_equity_history_point() -> None:
    record = _equity_history_point()
    values = PortfolioPersistenceSerializer.equity_history_point_values(record)
    model = PortfolioEquityHistoryPointModel(**values)

    restored = PortfolioPersistenceSerializer.equity_history_point_from_model(model)

    assert values["equity"] == 100_000.123456789
    assert values["cashflow_payload"] == {"deposit": 250.125}
    assert restored == record
    assert restored.lineage.execution_id == "exec-1"


def test_portfolio_serializer_flattens_position_history_record() -> None:
    record = _position_history()

    values = PortfolioPersistenceSerializer.position_history_values(record)

    assert values["position_history_id"] == "position-history-1"
    assert values["account_id"] == "acct-1"
    assert values["symbol"] == "SPY"
    assert values["snapshot_id"] == "snapshot-1"
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"source": "unit-test"}


def test_portfolio_serializer_round_trips_position_records() -> None:
    history_model = PortfolioPositionHistoryModel(
        **PortfolioPersistenceSerializer.position_history_values(_position_history())
    )
    latest_model = PortfolioPositionLatestModel(
        **PortfolioPersistenceSerializer.position_latest_values(_position_latest())
    )

    history = PortfolioPersistenceSerializer.position_history_from_model(
        history_model,
    )
    latest = PortfolioPersistenceSerializer.position_latest_from_model(
        latest_model,
    )

    assert history.position_history_id == "position-history-1"
    assert history.symbol == "SPY"
    assert history.lineage.node_name == "portfolio_state"
    assert history.metadata == {"source": "unit-test"}
    assert latest.position_latest_id == "portfolio_position_latest:acct-1:SPY"
    assert latest.weight == 0.42


def test_portfolio_serializer_round_trips_snapshot_records() -> None:
    exposure_model = PortfolioExposureSnapshotModel(
        **PortfolioPersistenceSerializer.exposure_snapshot_values(_exposure())
    )
    risk_model = PortfolioRiskSnapshotModel(
        **PortfolioPersistenceSerializer.risk_snapshot_values(_risk())
    )
    allocation_model = PortfolioAllocationSnapshotModel(
        **PortfolioPersistenceSerializer.allocation_snapshot_values(_allocation())
    )

    exposure = PortfolioPersistenceSerializer.exposure_snapshot_from_model(
        exposure_model,
    )
    risk = PortfolioPersistenceSerializer.risk_snapshot_from_model(
        risk_model,
    )
    allocation = PortfolioPersistenceSerializer.allocation_snapshot_from_model(
        allocation_model,
    )

    assert exposure.exposure_snapshot_id == "exposure-1"
    assert exposure.exposure_type == "sector"
    assert exposure.exposure_value == -0.15
    assert risk.risk_snapshot_id == "risk-1"
    assert risk.risk_signals == {"capital_preservation": "ok"}
    assert risk.account_health == "healthy"
    assert allocation.allocation_snapshot_id == "allocation-1"
    assert allocation.current_weight == 0.35
    assert allocation.target_weight == 0.3


def _equity_history_point() -> PortfolioEquityHistoryPointRecord:
    return PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=(
            "portfolio_equity_history_point:acct-1:alpaca:1D:2026-05-31T13:00:00+00:00"
        ),
        account_id="acct-1",
        source="alpaca",
        timeframe="1D",
        observed_at=_timestamp(),
        equity=100_000.123456789,
        profit_loss=1_250.987654321,
        profit_loss_pct=0.01250987654321,
        base_value=98_749.135802468,
        cashflow_payload={"deposit": 250.125},
        lineage=_lineage(),
    )


def _position_history() -> PortfolioPositionHistoryRecord:
    return PortfolioPositionHistoryRecord(
        position_history_id="position-history-1",
        account_id="acct-1",
        symbol="spy",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=5300.0,
        cost_basis=5000.0,
        weight=0.42,
        sector="ETF",
        theme="core",
        beta=1.0,
        risk_weight=0.35,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _position_latest() -> PortfolioPositionLatestRecord:
    return PortfolioPositionLatestRecord(
        position_latest_id="portfolio_position_latest:acct-1:SPY",
        account_id="acct-1",
        symbol="spy",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=5300.0,
        cost_basis=5000.0,
        weight=0.42,
        sector="ETF",
        theme="core",
        beta=1.0,
        risk_weight=0.35,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _exposure() -> PortfolioExposureSnapshotRecord:
    return PortfolioExposureSnapshotRecord(
        exposure_snapshot_id="exposure-1",
        account_id="acct-1",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        exposure_type="sector",
        exposure_name="Technology",
        exposure_value=-0.15,
        weight=0.35,
        beta=1.2,
        risk_weight=0.4,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _risk() -> PortfolioRiskSnapshotRecord:
    return PortfolioRiskSnapshotRecord(
        risk_snapshot_id="risk-1",
        account_id="acct-1",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        portfolio_value=100000.0,
        cash=12000.0,
        account_health="healthy",
        risk_score=0.31,
        risk_level="moderate",
        drawdown_risk=0.2,
        volatility_risk=0.4,
        concentration_risk=0.35,
        liquidity_risk=0.1,
        beta=1.05,
        cash_ratio=0.12,
        equity_retention_ratio=0.98,
        risk_signals={"capital_preservation": "ok"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _allocation() -> PortfolioAllocationSnapshotRecord:
    return PortfolioAllocationSnapshotRecord(
        allocation_snapshot_id="allocation-1",
        account_id="acct-1",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        allocation_type="sector",
        allocation_name="Technology",
        current_weight=0.35,
        target_weight=0.3,
        drift=0.05,
        market_value=35000.0,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="portfolio_state",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=UTC)
