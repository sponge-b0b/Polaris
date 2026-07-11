from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.portfolio_state import PortfolioStateHistoryModel
from core.storage.persistence.repositories.postgres_portfolio_state_repository import (
    PostgresPortfolioStateRepository,
)
from core.storage.persistence.serializers.portfolio_state_serializer import (
    PortfolioStateSerializer,
)
from domain.portfolio.models.portfolio_state import PortfolioState


class FakeScalarResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(self, rows: Sequence[object] | None = None) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(self) -> object | None:
        if not self._rows:
            return None
        return self._rows[0]

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.added: list[Any] = []
        self.executed: list[Any] = []
        self.commits = 0

    def add(
        self,
        model: Any,
    ) -> None:
        self.added.append(model)

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)
        return self.result

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.asyncio
async def test_persist_snapshot_upserts_all_v2_latest_fields() -> None:
    state = _portfolio_state()
    session = FakeAsyncSession()
    repository = PostgresPortfolioStateRepository(
        cast(AsyncSession, session),
    )

    await repository.persist_snapshot(state)

    assert len(session.added) == 1
    assert isinstance(session.added[0], PortfolioStateHistoryModel)
    assert len(session.executed) == 1
    assert session.commits == 1

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )
    update_segment = compiled.split("DO UPDATE SET", maxsplit=1)[1]

    expected_sql_names = {field.name for field in fields(PortfolioState)} | {
        "cash_pct",
        "risk_signals_payload",
    }
    expected_sql_names.discard("cash_ratio")
    expected_sql_names.discard("risk_signals")

    for field_name in expected_sql_names:
        assert field_name in compiled
        if field_name != "account_id":
            assert field_name in update_segment

    assert "sector_exposure" in update_segment
    assert "asset_class_exposure" in update_segment
    assert "risk_signals_payload" in update_segment
    assert "shorting_enabled" in update_segment
    assert "updated_at = now()" in update_segment


@pytest.mark.asyncio
async def test_get_latest_preserves_v2_fields_and_json_exposures() -> None:
    state = _portfolio_state()
    latest_model = PortfolioStateSerializer.to_latest_model(state)
    repository = PostgresPortfolioStateRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([latest_model]))),
    )

    restored = await repository.get_latest("account-1")

    assert restored is not None
    assert restored == state
    assert restored.sector_exposure == {
        "technology": 0.423456789,
        "healthcare": 0.176543211,
    }
    assert restored.asset_class_exposure == {
        "us_equity": 0.812345678,
        "cash": 0.15306122448979592,
    }
    assert restored.risk_signals["margin"]["score"] == 0.1666677777


@pytest.mark.asyncio
async def test_get_history_preserves_v2_fields_and_json_exposures() -> None:
    state = _portfolio_state()
    history_model = PortfolioStateSerializer.to_history_model(state)
    repository = PostgresPortfolioStateRepository(
        cast(AsyncSession, FakeAsyncSession(FakeExecuteResult([history_model]))),
    )

    restored = await repository.get_history(
        account_id="account-1",
        start=state.timestamp,
        end=state.timestamp,
    )

    assert restored == [state]
    assert restored[0].sector_exposure["technology"] == 0.423456789
    assert restored[0].asset_class_exposure["us_equity"] == 0.812345678
    assert restored[0].risk_signals["drawdown"]["score"] == 0.0666688888


def _portfolio_state() -> PortfolioState:
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
