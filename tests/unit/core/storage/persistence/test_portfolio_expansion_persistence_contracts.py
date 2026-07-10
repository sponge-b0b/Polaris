from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.portfolio import PortfolioAllocationSnapshotRecord
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceBundle
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceResult
from core.storage.persistence.portfolio import PortfolioEquityHistoryPointRecord
from core.storage.persistence.portfolio import PortfolioExposureSnapshotRecord
from core.storage.persistence.portfolio import PortfolioPositionHistoryRecord
from core.storage.persistence.portfolio import PortfolioPositionLatestRecord
from core.storage.persistence.portfolio import PortfolioRiskSnapshotRecord
from core.storage.persistence.portfolio import new_portfolio_allocation_snapshot_id
from core.storage.persistence.portfolio import new_portfolio_equity_history_point_id
from core.storage.persistence.portfolio import new_portfolio_exposure_snapshot_id
from core.storage.persistence.portfolio import new_portfolio_position_history_id
from core.storage.persistence.portfolio import new_portfolio_position_latest_id
from core.storage.persistence.portfolio import new_portfolio_risk_snapshot_id


def test_equity_history_record_is_normalized_immutable_and_stable() -> None:
    observed_at = _timestamp()
    record = PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=new_portfolio_equity_history_point_id(
            account_id=" acct-1 ",
            source=" alpaca ",
            timeframe=" 1D ",
            observed_at=observed_at,
        ),
        account_id=" acct-1 ",
        source=" alpaca ",
        timeframe=" 1D ",
        observed_at=observed_at,
        equity=100_000.123456789,
        profit_loss=-125.987654321,
        profit_loss_pct=-0.00125987654321,
        base_value=100_126.11111111,
        cashflow_payload={"deposit": 250.125},
    )

    assert record.account_id == "acct-1"
    assert record.source == "alpaca"
    assert record.timeframe == "1D"
    assert record.equity == 100_000.123456789
    assert record.profit_loss == -125.987654321
    assert record.portfolio_equity_history_point_id == (
        "portfolio_equity_history_point:acct-1:alpaca:1D:2026-05-30T14:00:00+00:00"
    )
    with pytest.raises(FrozenInstanceError):
        record.equity = 0.0  # type: ignore[misc]


def test_equity_history_record_normalizes_observation_time_to_utc() -> None:
    observed_at = datetime(
        2026,
        5,
        30,
        8,
        tzinfo=timezone(-timedelta(hours=6)),
    )
    record = PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=new_portfolio_equity_history_point_id(
            account_id="acct-1",
            source="alpaca",
            timeframe="1D",
            observed_at=observed_at,
        ),
        account_id="acct-1",
        source="alpaca",
        timeframe="1D",
        observed_at=observed_at,
        equity=100_000.0,
        profit_loss=0.0,
    )

    assert record.observed_at == _timestamp()
    assert record.portfolio_equity_history_point_id.endswith(
        "2026-05-30T14:00:00+00:00"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account_id", " "),
        ("source", " "),
        ("timeframe", " "),
        ("equity", -1.0),
        ("base_value", -1.0),
    ],
)
def test_equity_history_record_validates_fields(
    field: str,
    value: object,
) -> None:
    values: dict[str, object] = {
        "portfolio_equity_history_point_id": "history-point-1",
        "account_id": "acct-1",
        "source": "alpaca",
        "timeframe": "1D",
        "observed_at": _timestamp(),
        "equity": 100_000.0,
        "profit_loss": 125.0,
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        PortfolioEquityHistoryPointRecord(**values)  # type: ignore[arg-type]


def test_position_history_record_is_typed_normalized_and_immutable() -> None:
    record = _position_history()

    assert record.position_history_id == "position-history-1"
    assert record.account_id == "acct-1"
    assert record.symbol == "SPY"
    assert record.snapshot_id == "snapshot-1"
    assert record.quantity == 10.0
    assert record.market_value == 5300.0
    assert record.cost_basis == 5000.0
    assert record.weight == 0.42
    assert record.sector == "ETF"
    assert record.theme == "core"
    assert record.beta == 1.0
    assert record.risk_weight == 0.35
    assert record.lineage.execution_id == "exec-1"
    assert record.metadata == {"source": "unit-test"}

    with pytest.raises(FrozenInstanceError):
        record.symbol = "QQQ"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"position_history_id": " "}, "position_history_id"),
        ({"account_id": ""}, "account_id"),
        ({"symbol": " "}, "symbol"),
        ({"quantity": -1.0}, "quantity"),
        ({"market_value": -1.0}, "market_value"),
        ({"cost_basis": -1.0}, "cost_basis"),
        ({"weight": 1.2}, "weight"),
        ({"risk_weight": -0.1}, "risk_weight"),
    ],
)
def test_position_history_record_validates_required_fields_and_ratios(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "position_history_id": "position-history-1",
        "account_id": "acct-1",
        "symbol": "SPY",
        "timestamp": _timestamp(),
        "quantity": 10.0,
        "market_value": 5300.0,
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        PortfolioPositionHistoryRecord(**values)  # type: ignore[arg-type]


def test_position_latest_record_uses_stable_account_symbol_contract() -> None:
    record = PortfolioPositionLatestRecord(
        position_latest_id="portfolio_position_latest:acct-1:SPY",
        account_id=" acct-1 ",
        symbol=" spy ",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=5300.0,
        cost_basis=5000.0,
        weight=0.42,
        risk_weight=0.35,
    )

    assert record.position_latest_id == "portfolio_position_latest:acct-1:SPY"
    assert record.account_id == "acct-1"
    assert record.symbol == "SPY"


def test_exposure_snapshot_allows_signed_exposure_values() -> None:
    record = PortfolioExposureSnapshotRecord(
        exposure_snapshot_id="exposure-1",
        account_id=" acct-1 ",
        snapshot_id=" snapshot-1 ",
        timestamp=_timestamp(),
        exposure_type="sector",
        exposure_name="Technology",
        exposure_value=-0.15,
        weight=0.35,
        beta=1.2,
        risk_weight=0.4,
    )

    assert record.account_id == "acct-1"
    assert record.snapshot_id == "snapshot-1"
    assert record.exposure_value == -0.15

    with pytest.raises(ValueError, match="exposure_name"):
        PortfolioExposureSnapshotRecord(
            exposure_snapshot_id="exposure-1",
            account_id="acct-1",
            timestamp=_timestamp(),
            exposure_type="sector",
            exposure_name=" ",
            exposure_value=0.2,
        )


def test_risk_snapshot_aligns_with_v1_portfolio_state_risk_fields() -> None:
    record = PortfolioRiskSnapshotRecord(
        risk_snapshot_id="risk-1",
        account_id=" acct-1 ",
        snapshot_id=" snapshot-1 ",
        timestamp=_timestamp(),
        portfolio_value=100000.0,
        cash=12000.0,
        account_health=" healthy ",
        risk_score=0.31,
        risk_level=" moderate ",
        drawdown_risk=0.2,
        volatility_risk=0.4,
        concentration_risk=0.35,
        liquidity_risk=0.1,
        beta=1.05,
        cash_ratio=0.12,
        equity_retention_ratio=0.98,
        risk_signals={"capital_preservation": "ok"},
    )

    assert record.account_id == "acct-1"
    assert record.snapshot_id == "snapshot-1"
    assert record.account_health == "healthy"
    assert record.risk_level == "moderate"
    assert record.risk_signals == {"capital_preservation": "ok"}

    with pytest.raises(ValueError, match="risk_score"):
        PortfolioRiskSnapshotRecord(
            risk_snapshot_id="risk-1",
            account_id="acct-1",
            timestamp=_timestamp(),
            risk_score=1.1,
        )


def test_allocation_snapshot_captures_current_target_and_drift() -> None:
    record = PortfolioAllocationSnapshotRecord(
        allocation_snapshot_id="allocation-1",
        account_id=" acct-1 ",
        snapshot_id=" snapshot-1 ",
        timestamp=_timestamp(),
        allocation_type="sector",
        allocation_name="Technology",
        current_weight=0.35,
        target_weight=0.3,
        drift=0.05,
        market_value=35000.0,
    )

    assert record.account_id == "acct-1"
    assert record.snapshot_id == "snapshot-1"
    assert record.current_weight == 0.35
    assert record.target_weight == 0.3
    assert record.drift == 0.05

    with pytest.raises(ValueError, match="current_weight"):
        PortfolioAllocationSnapshotRecord(
            allocation_snapshot_id="allocation-1",
            account_id="acct-1",
            timestamp=_timestamp(),
            allocation_type="sector",
            allocation_name="Technology",
            current_weight=1.2,
        )


def test_portfolio_expansion_bundle_groups_atomic_payload() -> None:
    position = _position_history()
    bundle = PortfolioExpansionPersistenceBundle(
        equity_history_points=(
            PortfolioEquityHistoryPointRecord(
                portfolio_equity_history_point_id="history-point-1",
                account_id="acct-1",
                source="alpaca",
                timeframe="1D",
                observed_at=_timestamp(),
                equity=100_000.0,
                profit_loss=125.0,
            ),
        ),
        position_history=(position,),
        position_latest=(
            PortfolioPositionLatestRecord(
                position_latest_id="portfolio_position_latest:acct-1:SPY",
                account_id="acct-1",
                symbol="SPY",
                timestamp=_timestamp(),
                quantity=10.0,
                market_value=5300.0,
            ),
        ),
        exposure_snapshots=(
            PortfolioExposureSnapshotRecord(
                exposure_snapshot_id="exposure-1",
                account_id="acct-1",
                timestamp=_timestamp(),
                exposure_type="sector",
                exposure_name="Technology",
                exposure_value=0.35,
            ),
        ),
        risk_snapshots=(
            PortfolioRiskSnapshotRecord(
                risk_snapshot_id="risk-1",
                account_id="acct-1",
                timestamp=_timestamp(),
                risk_score=0.3,
            ),
        ),
        allocation_snapshots=(
            PortfolioAllocationSnapshotRecord(
                allocation_snapshot_id="allocation-1",
                account_id="acct-1",
                timestamp=_timestamp(),
                allocation_type="sector",
                allocation_name="Technology",
                current_weight=0.35,
            ),
        ),
    )

    assert len(bundle.equity_history_points) == 1
    assert bundle.position_history == (position,)
    assert len(bundle.position_latest) == 1
    assert len(bundle.exposure_snapshots) == 1
    assert len(bundle.risk_snapshots) == 1
    assert len(bundle.allocation_snapshots) == 1


def test_portfolio_expansion_persistence_result_validates_state() -> None:
    success = PortfolioExpansionPersistenceResult.succeeded(
        account_id="acct-1",
        records_persisted=5,
    )
    failure = PortfolioExpansionPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 5
    assert success.account_id == "acct-1"
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="account_id"):
        PortfolioExpansionPersistenceResult(success=True)

    with pytest.raises(ValueError, match="error"):
        PortfolioExpansionPersistenceResult.failed(" ")

    with pytest.raises(ValueError, match="successful"):
        PortfolioExpansionPersistenceResult(
            success=True,
            account_id="acct-1",
            error="unexpected",
        )


def test_portfolio_id_helpers_are_stable_when_execution_lineage_exists() -> None:
    timestamp = _timestamp()

    position_history_id = new_portfolio_position_history_id(
        account_id=" acct-1 ",
        symbol=" spy ",
        timestamp=timestamp,
        execution_id=" exec-1 ",
        position_key=" primary ",
    )
    position_latest_id = new_portfolio_position_latest_id(
        account_id=" acct-1 ",
        symbol=" spy ",
    )
    exposure_id = new_portfolio_exposure_snapshot_id(
        account_id="acct-1",
        exposure_type="sector",
        exposure_name="Technology",
        timestamp=timestamp,
        execution_id="exec-1",
    )
    risk_id = new_portfolio_risk_snapshot_id(
        account_id="acct-1",
        timestamp=timestamp,
        execution_id="exec-1",
        risk_key="primary",
    )
    allocation_id = new_portfolio_allocation_snapshot_id(
        account_id="acct-1",
        allocation_type="sector",
        allocation_name="Technology",
        timestamp=timestamp,
        execution_id="exec-1",
    )

    assert position_history_id == (
        "portfolio_position_history:exec-1:acct-1:SPY:2026-05-30T14:00:00+00:00:primary"
    )
    assert position_latest_id == "portfolio_position_latest:acct-1:SPY"
    assert exposure_id == (
        "portfolio_exposure_snapshot:exec-1:acct-1:"
        "2026-05-30T14:00:00+00:00:sector:Technology"
    )
    assert risk_id == (
        "portfolio_risk_snapshot:exec-1:acct-1:2026-05-30T14:00:00+00:00:primary"
    )
    assert allocation_id == (
        "portfolio_allocation_snapshot:exec-1:acct-1:"
        "2026-05-30T14:00:00+00:00:sector:Technology"
    )


def test_portfolio_append_id_helpers_avoid_accidental_duplicates_without_lineage() -> (
    None
):
    timestamp = _timestamp()

    position_history_ids = {
        new_portfolio_position_history_id(
            account_id="acct-1",
            symbol="spy",
            timestamp=timestamp,
        )
        for _ in range(2)
    }
    exposure_ids = {
        new_portfolio_exposure_snapshot_id(
            account_id="acct-1",
            exposure_type="sector",
            exposure_name="Technology",
            timestamp=timestamp,
        )
        for _ in range(2)
    }
    risk_ids = {
        new_portfolio_risk_snapshot_id(
            account_id="acct-1",
            timestamp=timestamp,
        )
        for _ in range(2)
    }
    allocation_ids = {
        new_portfolio_allocation_snapshot_id(
            account_id="acct-1",
            allocation_type="sector",
            allocation_name="Technology",
            timestamp=timestamp,
        )
        for _ in range(2)
    }

    assert len(position_history_ids) == 2
    assert len(exposure_ids) == 2
    assert len(risk_ids) == 2
    assert len(allocation_ids) == 2
    assert all(
        value.startswith("portfolio_position_history:acct-1:SPY:")
        for value in position_history_ids
    )
    assert all(
        value.startswith("portfolio_exposure_snapshot:") for value in exposure_ids
    )
    assert all(value.startswith("portfolio_risk_snapshot:") for value in risk_ids)
    assert all(
        value.startswith("portfolio_allocation_snapshot:") for value in allocation_ids
    )


def _position_history() -> PortfolioPositionHistoryRecord:
    return PortfolioPositionHistoryRecord(
        position_history_id="position-history-1",
        account_id=" acct-1 ",
        symbol=" spy ",
        snapshot_id=" snapshot-1 ",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=5300.0,
        cost_basis=5000.0,
        weight=0.42,
        sector=" ETF ",
        theme=" core ",
        beta=1.0,
        risk_weight=0.35,
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="portfolio_state",
        ),
        metadata={"source": "unit-test"},
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc)
