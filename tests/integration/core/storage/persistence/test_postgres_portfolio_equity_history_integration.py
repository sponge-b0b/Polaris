from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database.models.portfolio import PortfolioEquityHistoryPointModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.portfolio import (
    PortfolioEquityHistoryPointRecord,
    PortfolioExpansionPersistenceBundle,
    new_portfolio_equity_history_point_id,
)
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (  # noqa: E501 - canonical module path
    PostgresPortfolioExpansionPersistenceRepository,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "POLARIS_TEST_DATABASE_URL is required for portfolio persistence integration "
        "tests."
    ),
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    yield session_factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_portfolio_equity_history_is_idempotent_and_queryable(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    account_id = f"portfolio-equity-integration-{uuid4().hex}"
    observed_at = datetime(2026, 6, 30, 14, tzinfo=UTC)
    record = PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=new_portfolio_equity_history_point_id(
            account_id=account_id,
            source="alpaca",
            timeframe="1D",
            observed_at=observed_at,
        ),
        account_id=account_id,
        source="alpaca",
        timeframe="1D",
        observed_at=observed_at,
        equity=100_000.123456789,
        profit_loss=1_250.987654321,
        profit_loss_pct=0.01250987654321,
        base_value=98_749.135802468,
        cashflow_payload={"deposit": 250.125},
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="integration-exec-1",
            runtime_id="integration-runtime-1",
            node_name="portfolio_state",
        ),
    )
    bundle = PortfolioExpansionPersistenceBundle(equity_history_points=(record,))

    try:
        async with postgres_session_factory() as session:
            repository = PostgresPortfolioExpansionPersistenceRepository(session)
            first = await repository.persist_portfolio_expansion_bundle(bundle)
            duplicate = await repository.persist_portfolio_expansion_bundle(bundle)

        async with postgres_session_factory() as session:
            records = await PostgresPortfolioExpansionPersistenceRepository(
                session
            ).list_equity_history_points(
                account_id=account_id,
                source="alpaca",
                timeframe="1D",
                start=observed_at,
                end=observed_at,
            )

        assert first.success is True
        assert duplicate.success is True
        assert len(records) == 1
        assert records[0] == record
        assert records[0].equity == 100_000.123456789
    finally:
        async with postgres_session_factory() as session:
            await session.execute(
                delete(PortfolioEquityHistoryPointModel).where(
                    PortfolioEquityHistoryPointModel.account_id == account_id,
                )
            )
            await session.commit()
