from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.persistence.portfolio import (
    PortfolioAllocationSnapshotPersistenceFilters,
    PortfolioEquityHistoryPersistenceFilters,
    PortfolioExposureSnapshotPersistenceFilters,
    PortfolioLatestPositionPersistenceFilters,
    PortfolioPersistenceService,
    PortfolioPositionHistoryPersistenceFilters,
    PortfolioRiskSnapshotPersistenceFilters,
)
from core.storage.persistence.portfolio import (
    PortfolioAllocationSnapshotRecord,
    PortfolioEquityHistoryPointRecord,
    PortfolioExpansionPersistenceBundle,
    PortfolioExpansionPersistenceResult,
    PortfolioExposureSnapshotRecord,
    PortfolioPositionHistoryRecord,
    PortfolioPositionLatestRecord,
    PortfolioRiskSnapshotRecord,
)
from domain.portfolio.models.portfolio_state import PortfolioState


class FakePortfolioExpansionRepository:
    def __init__(
        self,
        *,
        equity_history_points: Sequence[PortfolioEquityHistoryPointRecord] = (),
        position_history: Sequence[PortfolioPositionHistoryRecord] = (),
        position_latest: Sequence[PortfolioPositionLatestRecord] = (),
        exposure_snapshots: Sequence[PortfolioExposureSnapshotRecord] = (),
        risk_snapshots: Sequence[PortfolioRiskSnapshotRecord] = (),
        allocation_snapshots: Sequence[PortfolioAllocationSnapshotRecord] = (),
    ) -> None:
        self.bundle: PortfolioExpansionPersistenceBundle | None = None
        self.equity_history_points = tuple(equity_history_points)
        self.position_history = tuple(position_history)
        self.position_latest = tuple(position_latest)
        self.exposure_snapshots = tuple(exposure_snapshots)
        self.risk_snapshots = tuple(risk_snapshots)
        self.allocation_snapshots = tuple(allocation_snapshots)
        self.equity_history_filters: dict[str, str | datetime | None] | None = None
        self.position_history_filters: (
            dict[
                str,
                str | datetime | None,
            ]
            | None
        ) = None
        self.latest_position_filters: dict[str, str | None] | None = None
        self.exposure_filters: dict[str, str | datetime | None] | None = None
        self.risk_filters: dict[str, str | datetime | None] | None = None
        self.allocation_filters: dict[str, str | datetime | None] | None = None

    async def persist_portfolio_expansion_bundle(
        self,
        bundle: PortfolioExpansionPersistenceBundle,
    ) -> PortfolioExpansionPersistenceResult:
        self.bundle = bundle
        return PortfolioExpansionPersistenceResult.succeeded(
            account_id=_account_id(),
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
        self.equity_history_filters = {
            "account_id": account_id,
            "source": source,
            "timeframe": timeframe,
            "start": start,
            "end": end,
        }
        return self.equity_history_points

    async def list_position_history(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioPositionHistoryRecord]:
        self.position_history_filters = {
            "account_id": account_id,
            "symbol": symbol,
            "start": start,
            "end": end,
        }
        return self.position_history

    async def list_latest_positions(
        self,
        *,
        account_id: str,
        symbol: str | None = None,
    ) -> Sequence[PortfolioPositionLatestRecord]:
        self.latest_position_filters = {
            "account_id": account_id,
            "symbol": symbol,
        }
        return self.position_latest

    async def list_exposure_snapshots(
        self,
        *,
        account_id: str,
        exposure_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioExposureSnapshotRecord]:
        self.exposure_filters = {
            "account_id": account_id,
            "exposure_type": exposure_type,
            "start": start,
            "end": end,
        }
        return self.exposure_snapshots

    async def list_risk_snapshots(
        self,
        *,
        account_id: str,
        risk_level: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioRiskSnapshotRecord]:
        self.risk_filters = {
            "account_id": account_id,
            "risk_level": risk_level,
            "start": start,
            "end": end,
        }
        return self.risk_snapshots

    async def list_allocation_snapshots(
        self,
        *,
        account_id: str,
        allocation_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[PortfolioAllocationSnapshotRecord]:
        self.allocation_filters = {
            "account_id": account_id,
            "allocation_type": allocation_type,
            "start": start,
            "end": end,
        }
        return self.allocation_snapshots


class FakePortfolioStateRepository:
    def __init__(
        self,
        latest_state: PortfolioState | None = None,
        history: Sequence[PortfolioState] = (),
    ) -> None:
        self.persisted_state: PortfolioState | None = None
        self.latest_state = latest_state
        self.history = tuple(history)
        self.latest_account_id: str | None = None
        self.history_request: tuple[str, datetime, datetime] | None = None

    async def persist_snapshot(
        self,
        state: PortfolioState,
    ) -> None:
        self.persisted_state = state

    async def get_latest(
        self,
        account_id: str,
    ) -> PortfolioState | None:
        self.latest_account_id = account_id
        return self.latest_state

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]:
        self.history_request = (
            account_id,
            start,
            end,
        )
        return list(self.history)


@pytest.mark.asyncio
async def test_portfolio_persistence_service_persists_existing_expansion_bundle() -> (
    None
):
    repository = FakePortfolioExpansionRepository()
    service = PortfolioPersistenceService(repository)
    bundle = PortfolioExpansionPersistenceBundle(
        equity_history_points=(_equity_history_point(),),
        position_history=(_position_history(),),
        position_latest=(_position_latest(),),
        exposure_snapshots=(_exposure_snapshot(),),
        risk_snapshots=(_risk_snapshot(),),
        allocation_snapshots=(_allocation_snapshot(),),
    )

    result = await service.persist_expansion_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 6
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_portfolio_persistence_service_builds_typed_expansion_bundle() -> None:
    repository = FakePortfolioExpansionRepository()
    service = PortfolioPersistenceService(repository)

    result = await service.persist_expansion_records(
        equity_history_points=(_equity_history_point(),),
        position_history=(_position_history(),),
        position_latest=(_position_latest(),),
        exposure_snapshots=(_exposure_snapshot(),),
        risk_snapshots=(_risk_snapshot(),),
        allocation_snapshots=(_allocation_snapshot(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.equity_history_points[0].timeframe == "1D"
    assert repository.bundle.position_history[0].symbol == "AAPL"
    assert repository.bundle.position_latest[0].position_latest_id == "latest-1"
    assert repository.bundle.exposure_snapshots[0].exposure_type == "sector"
    assert repository.bundle.risk_snapshots[0].risk_level == "moderate"
    assert repository.bundle.allocation_snapshots[0].allocation_type == "asset_class"


@pytest.mark.asyncio
async def test_portfolio_persistence_service_uses_typed_expansion_filters() -> None:
    repository = FakePortfolioExpansionRepository(
        equity_history_points=(_equity_history_point(),),
        position_history=(_position_history(),),
        position_latest=(_position_latest(),),
        exposure_snapshots=(_exposure_snapshot(),),
        risk_snapshots=(_risk_snapshot(),),
        allocation_snapshots=(_allocation_snapshot(),),
    )
    service = PortfolioPersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)

    equity_history = await service.list_equity_history_points(
        PortfolioEquityHistoryPersistenceFilters(
            account_id=" acct-1 ",
            source="alpaca",
            timeframe="1D",
            start=start,
            end=end,
        )
    )
    position_history = await service.list_position_history(
        PortfolioPositionHistoryPersistenceFilters(
            account_id=" acct-1 ",
            symbol="aapl",
            start=start,
            end=end,
        )
    )
    latest_positions = await service.list_latest_positions(
        PortfolioLatestPositionPersistenceFilters(
            account_id="acct-1",
            symbol="aapl",
        )
    )
    exposure_snapshots = await service.list_exposure_snapshots(
        PortfolioExposureSnapshotPersistenceFilters(
            account_id="acct-1",
            exposure_type="sector",
            start=start,
            end=end,
        )
    )
    risk_snapshots = await service.list_risk_snapshots(
        PortfolioRiskSnapshotPersistenceFilters(
            account_id="acct-1",
            risk_level="moderate",
            start=start,
            end=end,
        )
    )
    allocation_snapshots = await service.list_allocation_snapshots(
        PortfolioAllocationSnapshotPersistenceFilters(
            account_id="acct-1",
            allocation_type="asset_class",
            start=start,
            end=end,
        )
    )

    assert len(equity_history) == 1
    assert len(position_history) == 1
    assert len(latest_positions) == 1
    assert len(exposure_snapshots) == 1
    assert len(risk_snapshots) == 1
    assert len(allocation_snapshots) == 1
    assert repository.equity_history_filters == {
        "account_id": "acct-1",
        "source": "alpaca",
        "timeframe": "1D",
        "start": start,
        "end": end,
    }
    assert repository.position_history_filters == {
        "account_id": "acct-1",
        "symbol": "AAPL",
        "start": start,
        "end": end,
    }
    assert repository.latest_position_filters == {
        "account_id": "acct-1",
        "symbol": "AAPL",
    }
    assert repository.exposure_filters == {
        "account_id": "acct-1",
        "exposure_type": "sector",
        "start": start,
        "end": end,
    }
    assert repository.risk_filters == {
        "account_id": "acct-1",
        "risk_level": "moderate",
        "start": start,
        "end": end,
    }
    assert repository.allocation_filters == {
        "account_id": "acct-1",
        "allocation_type": "asset_class",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_portfolio_persistence_service_preserves_v2_state_repository() -> None:
    state = _portfolio_state()
    expansion_repository = FakePortfolioExpansionRepository()
    state_repository = FakePortfolioStateRepository(
        latest_state=state,
        history=(state,),
    )
    service = PortfolioPersistenceService(
        expansion_repository,
        state_repository,
    )
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)

    await service.persist_state_snapshot(state)
    latest_state = await service.get_latest_state(" acct-1 ")
    history = await service.get_state_history(
        account_id="acct-1",
        start=start,
        end=end,
    )

    assert state_repository.persisted_state == state
    assert latest_state == state
    assert tuple(history) == (state,)
    assert latest_state is not None
    assert latest_state.schema_version == 2
    assert latest_state.buying_power_ratio == 0.20408163265306123
    assert latest_state.unrealized_intraday_pnl_pct == 0.00125912345
    assert latest_state.margin_utilization_ratio == 0.1666677777
    assert latest_state.shorting_enabled is True
    assert latest_state.trade_suspended_by_user is True
    assert latest_state.sector_exposure == {
        "technology": 0.423456789,
        "healthcare": 0.176543211,
    }
    assert latest_state.asset_class_exposure == {
        "us_equity": 0.812345678,
        "cash": 0.15306122448979592,
    }
    assert latest_state.risk_signals["margin"]["score"] == 0.1666677777
    assert state_repository.latest_account_id == "acct-1"
    assert state_repository.history_request == (
        "acct-1",
        start,
        end,
    )


@pytest.mark.asyncio
async def test_portfolio_persistence_service_requires_state_repository_for_state_methods() -> (  # noqa: E501
    None
):
    service = PortfolioPersistenceService(FakePortfolioExpansionRepository())

    with pytest.raises(RuntimeError, match="PortfolioStateRepository is required"):
        await service.get_latest_state("acct-1")


@pytest.mark.parametrize(
    "filters",
    [
        PortfolioEquityHistoryPersistenceFilters,
        PortfolioPositionHistoryPersistenceFilters,
        PortfolioExposureSnapshotPersistenceFilters,
        PortfolioRiskSnapshotPersistenceFilters,
        PortfolioAllocationSnapshotPersistenceFilters,
    ],
)
def test_portfolio_time_window_filters_require_ordered_bounds(
    filters: type[
        PortfolioEquityHistoryPersistenceFilters
        | PortfolioPositionHistoryPersistenceFilters
        | PortfolioExposureSnapshotPersistenceFilters
        | PortfolioRiskSnapshotPersistenceFilters
        | PortfolioAllocationSnapshotPersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            account_id="acct-1",
            start=start,
            end=end,
        )


def _equity_history_point() -> PortfolioEquityHistoryPointRecord:
    return PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=(
            "portfolio_equity_history_point:acct-1:alpaca:1D:2026-05-31T13:00:00+00:00"
        ),
        account_id=_account_id(),
        source="alpaca",
        timeframe="1D",
        observed_at=_timestamp(),
        equity=10_000.123456789,
        profit_loss=125.987654321,
        profit_loss_pct=0.01275892345,
        base_value=9_874.135802468,
        cashflow_payload={"deposit": 100.25},
    )


def _position_history() -> PortfolioPositionHistoryRecord:
    return PortfolioPositionHistoryRecord(
        position_history_id="history-1",
        account_id=_account_id(),
        symbol="aapl",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=1_900.0,
        cost_basis=1_500.0,
        weight=0.19,
        sector="technology",
        theme="ai",
        beta=1.2,
        risk_weight=0.25,
    )


def _position_latest() -> PortfolioPositionLatestRecord:
    return PortfolioPositionLatestRecord(
        position_latest_id="latest-1",
        account_id=_account_id(),
        symbol="AAPL",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=1_900.0,
        cost_basis=1_500.0,
        weight=0.19,
        sector="technology",
        theme="ai",
        beta=1.2,
        risk_weight=0.25,
    )


def _exposure_snapshot() -> PortfolioExposureSnapshotRecord:
    return PortfolioExposureSnapshotRecord(
        exposure_snapshot_id="exposure-1",
        account_id=_account_id(),
        timestamp=_timestamp(),
        exposure_type="sector",
        exposure_name="technology",
        exposure_value=1_900.0,
        weight=0.19,
        beta=1.2,
        risk_weight=0.25,
    )


def _risk_snapshot() -> PortfolioRiskSnapshotRecord:
    return PortfolioRiskSnapshotRecord(
        risk_snapshot_id="risk-1",
        account_id=_account_id(),
        timestamp=_timestamp(),
        portfolio_value=10_000.0,
        cash=1_000.0,
        account_health="healthy",
        risk_score=0.35,
        risk_level="moderate",
        drawdown_risk=0.2,
        volatility_risk=0.3,
        concentration_risk=0.4,
        liquidity_risk=0.1,
        beta=1.1,
        cash_ratio=0.1,
        equity_retention_ratio=0.9,
    )


def _allocation_snapshot() -> PortfolioAllocationSnapshotRecord:
    return PortfolioAllocationSnapshotRecord(
        allocation_snapshot_id="allocation-1",
        account_id=_account_id(),
        timestamp=_timestamp(),
        allocation_type="asset_class",
        allocation_name="equity",
        current_weight=0.9,
        target_weight=0.85,
        drift=0.05,
        market_value=9_000.0,
    )


def _portfolio_state() -> PortfolioState:
    return PortfolioState(
        snapshot_id="snapshot-1",
        account_id=_account_id(),
        timestamp=_timestamp(),
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


def _account_id() -> str:
    return "acct-1"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
