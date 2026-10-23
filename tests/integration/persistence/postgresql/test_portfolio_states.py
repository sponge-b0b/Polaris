from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError

from polaris.application.portfolio import PortfolioStateConflict
from polaris.domain.portfolio import (
    FinancialInstrumentId,
    PortfolioId,
    PortfolioSource,
    PortfolioState,
    PortfolioStateId,
)
from polaris.infrastructure.persistence.postgresql import PostgresPortfolioStateStore
from polaris.infrastructure.persistence.postgresql.schema import portfolio_states

from .conftest import PostgresTestTarget, postgres_store


def _state(portfolio_id: PortfolioId, *, as_of: datetime) -> PortfolioState:
    return PortfolioState(
        state_id=PortfolioStateId(uuid4()),
        portfolio_id=portfolio_id,
        as_of=as_of,
        source=PortfolioSource("custodian", f"snapshot-{as_of.isoformat()}", as_of),
        currency="USD",
        capital_basis=Decimal("123456.789123"),
        cash=Decimal("20000.000001"),
        instrument_id=FinancialInstrumentId(uuid4()),
        position_quantity=Decimal("100.125"),
        position_value=Decimal("80000.000001"),
        exposure_value=Decimal("81000.000001"),
        allocation_fraction=Decimal("0.6480001"),
        interpretation_basis=(
            "attributable custodian facts, no broker authority transfer"
        ),
        uncertainty="Source valuation may omit unsettled cash",
    )


def test_actual_state_history_survives_restart_and_later_source_change(
    postgres_target: PostgresTestTarget,
) -> None:
    async def scenario() -> None:
        portfolio_id = PortfolioId(uuid4())
        first = _state(portfolio_id, as_of=datetime(2026, 10, 17, tzinfo=UTC))
        async with postgres_store(postgres_target, PostgresPortfolioStateStore) as (
            _,
            store,
        ):
            committed = await store.append(first)
            assert committed.state == first
            assert committed.known_at >= first.source.observed_at
            with pytest.raises(PortfolioStateConflict):
                await store.append(replace(first, cash=Decimal("0")))

        async with postgres_store(postgres_target, PostgresPortfolioStateStore) as (
            engine,
            restarted,
        ):
            second = _state(
                portfolio_id,
                as_of=datetime(2026, 10, 18, tzinfo=UTC),
            )
            later = await restarted.append(second)
            assert await restarted.get(first.state_id) == committed
            history = await restarted.history(
                portfolio_id,
                effective_at=second.as_of,
                known_at=later.known_at + timedelta(seconds=1),
            )
            assert tuple(item.state.state_id for item in history) == (
                first.state_id,
                second.state_id,
            )
            assert history[0].state.cash == Decimal("20000.000001")
            assert history[0].state.uncertainty == (
                "Source valuation may omit unsettled cash"
            )
            assert await restarted.history(
                portfolio_id,
                effective_at=first.as_of,
                known_at=committed.known_at,
            ) == (committed,)
            with pytest.raises(ValueError, match="timezone-aware"):
                await restarted.history(
                    portfolio_id,
                    effective_at=first.as_of.replace(tzinfo=None),
                    known_at=committed.known_at,
                )
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        update(portfolio_states)
                        .where(portfolio_states.c.state_id == first.state_id.value)
                        .values(cash=Decimal("0"))
                    )
            with pytest.raises(DBAPIError):
                async with engine.begin() as connection:
                    await connection.execute(
                        delete(portfolio_states).where(
                            portfolio_states.c.state_id == first.state_id.value
                        )
                    )

    asyncio.run(scenario())
