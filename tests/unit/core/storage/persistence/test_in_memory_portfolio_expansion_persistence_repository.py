from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

from core.storage.persistence.portfolio import (
    InMemoryPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.portfolio import PortfolioExpansionPersistenceBundle
from core.storage.persistence.portfolio import PortfolioEquityHistoryPointRecord
from core.storage.persistence.portfolio import PortfolioPositionLatestRecord


_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_in_memory_portfolio_expansion_repository_is_deterministic() -> None:
    repository = InMemoryPortfolioExpansionPersistenceRepository()
    later = _BASE_TIME + timedelta(days=1)

    first_result = await repository.persist_portfolio_expansion_bundle(
        PortfolioExpansionPersistenceBundle(
            equity_history_points=(
                _equity_point("equity-later", later, 101_000.0),
                _equity_point("equity-first", _BASE_TIME, 100_000.0),
            ),
            position_latest=(_latest_position("latest-first", _BASE_TIME, 10.0),),
        )
    )
    await repository.persist_portfolio_expansion_bundle(
        PortfolioExpansionPersistenceBundle(
            equity_history_points=(
                _equity_point("equity-duplicate", _BASE_TIME, 999_999.0),
            ),
            position_latest=(_latest_position("latest-second", later, 12.0),),
        )
    )

    equity_history = await repository.list_equity_history_points(
        account_id="acct-1",
        source="simulated",
        timeframe="1D",
    )
    latest_positions = await repository.list_latest_positions(
        account_id="acct-1",
        symbol="spy",
    )

    assert first_result.success is True
    assert first_result.records_persisted == 3
    assert [point.portfolio_equity_history_point_id for point in equity_history] == [
        "equity-first",
        "equity-later",
    ]
    assert [point.equity for point in equity_history] == [100_000.0, 101_000.0]
    assert len(latest_positions) == 1
    assert latest_positions[0].position_latest_id == "latest-second"
    assert latest_positions[0].quantity == 12.0


def _equity_point(
    record_id: str,
    observed_at: datetime,
    equity: float,
) -> PortfolioEquityHistoryPointRecord:
    return PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=record_id,
        account_id="acct-1",
        source="simulated",
        timeframe="1D",
        observed_at=observed_at,
        equity=equity,
        profit_loss=equity - 100_000.0,
    )


def _latest_position(
    record_id: str,
    timestamp: datetime,
    quantity: float,
) -> PortfolioPositionLatestRecord:
    return PortfolioPositionLatestRecord(
        position_latest_id=record_id,
        account_id="acct-1",
        symbol="SPY",
        timestamp=timestamp,
        quantity=quantity,
        market_value=quantity * 500.0,
    )
