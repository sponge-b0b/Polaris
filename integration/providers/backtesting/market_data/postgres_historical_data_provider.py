from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import TypeVar

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.storage.persistence.market import (
    MarketContextSnapshotRecord,
    MarketOhlcvRecord,
    MarketPersistenceRepository,
)
from core.storage.persistence.repositories.postgres_market_persistence_repository import (  # noqa: E501
    PostgresMarketPersistenceRepository,
)
from domain.market.models import SP500Data
from integration.providers.market_data.market_data_provider import MarketDataProvider

MissingDataPolicy = str
RepositoryContextFactory = Callable[
    [],
    AbstractAsyncContextManager[MarketPersistenceRepository],
]
RecordT = TypeVar("RecordT")


@dataclass(
    frozen=True,
    slots=True,
)
class PostgresHistoricalDataProviderConfig:
    """
    Configuration for PostgreSQL-backed historical backtest market data.
    """

    source: str | None = None
    sp500_universe: str = "sp500"
    missing_data_policy: MissingDataPolicy = "fail_fast"

    def __post_init__(
        self,
    ) -> None:
        if self.missing_data_policy not in {"fail_fast", "forward_fill"}:
            raise ValueError(
                "missing_data_policy must be one of: fail_fast, forward_fill."
            )
        if not self.sp500_universe.strip():
            raise ValueError("sp500_universe is required.")


class MissingHistoricalMarketDataError(RuntimeError):
    """
    Raised when curated PostgreSQL market data cannot satisfy a request.
    """


class PostgresMarketRepositoryContext(
    AbstractAsyncContextManager[MarketPersistenceRepository]
):
    """
    Async context wrapper that exposes the canonical market repository protocol.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(
        self,
    ) -> MarketPersistenceRepository:
        self._session = self._session_factory()
        return PostgresMarketPersistenceRepository(
            self._session,
        )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None


def postgres_market_repository_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> RepositoryContextFactory:
    """
    Build a repository context factory for PostgreSQL-backed market history.
    """

    def create_context() -> AbstractAsyncContextManager[MarketPersistenceRepository]:
        return PostgresMarketRepositoryContext(
            session_factory,
        )

    return create_context


class PostgresHistoricalDataProvider(MarketDataProvider):
    """
    Backtest market data provider backed by curated PostgreSQL records.

    This provider is intentionally a normal MarketDataProvider implementation;
    runtime nodes and application services remain unaware of whether the data is
    synthetic, live, or persisted historical data.
    """

    def __init__(
        self,
        repository_factory: RepositoryContextFactory,
        config: PostgresHistoricalDataProviderConfig | None = None,
    ) -> None:
        self._repository_factory = repository_factory
        self._config = config or PostgresHistoricalDataProviderConfig()

    async def get_symbol_data(
        self,
        symbol: str,
        days: int,
    ) -> pd.DataFrame:
        records = await self._list_ohlcv(
            symbol=symbol,
            days=days,
        )
        return _ohlcv_records_to_frame(
            records=records,
            days=days,
            label=f"symbol={symbol.upper()}",
            policy=self._config.missing_data_policy,
        )

    async def get_vix_data(
        self,
        days: int,
    ) -> pd.DataFrame:
        records = await self._list_ohlcv(
            symbol="^VIX",
            days=days,
        )
        return _ohlcv_records_to_frame(
            records=records,
            days=days,
            label="symbol=^VIX",
            policy=self._config.missing_data_policy,
        )

    async def get_vvix_data(
        self,
        days: int,
    ) -> pd.DataFrame:
        records = await self._list_ohlcv(
            symbol="^VVIX",
            days=days,
        )
        return _ohlcv_records_to_frame(
            records=records,
            days=days,
            label="symbol=^VVIX",
            policy=self._config.missing_data_policy,
        )

    async def get_sp500_data(
        self,
        days: int,
    ) -> SP500Data:
        async with self._repository_factory() as repository:
            records = await repository.list_context_snapshots(
                universe=self._config.sp500_universe,
                source=self._config.source,
            )

        selected_records = _select_records(
            records=records,
            days=days,
            label=f"universe={self._config.sp500_universe}",
            record_type="S&P 500 context snapshots",
            policy=self._config.missing_data_policy,
        )
        analytics = _sp500_records_to_frame(
            selected_records,
        )
        if self._config.missing_data_policy == "forward_fill":
            analytics = _forward_fill_frame(
                analytics,
                days=days,
            )

        latest_record = selected_records[-1]
        return SP500Data(
            analytics=analytics,
            top_50_constituents=_top_50_constituents_from_record(latest_record),
            market_caps=_market_caps_from_record(latest_record),
        )

    async def _list_ohlcv(
        self,
        *,
        symbol: str,
        days: int,
    ) -> tuple[MarketOhlcvRecord, ...]:
        async with self._repository_factory() as repository:
            records = await repository.list_ohlcv(
                symbol=symbol,
                source=self._config.source,
            )

        return _select_records(
            records=records,
            days=days,
            label=f"symbol={symbol.upper()}",
            record_type="OHLCV rows",
            policy=self._config.missing_data_policy,
        )


def _select_records[RecordT](
    *,
    records: Sequence[RecordT],
    days: int,
    label: str,
    record_type: str,
    policy: MissingDataPolicy,
) -> tuple[RecordT, ...]:
    requested_days = max(
        int(days),
        1,
    )
    typed_records = tuple(records)
    available_count = len(typed_records)
    if available_count == 0:
        raise MissingHistoricalMarketDataError(
            _missing_data_message(
                label=label,
                record_type=record_type,
                requested_days=requested_days,
                available_count=available_count,
                policy=policy,
            )
        )
    if available_count < requested_days and policy == "fail_fast":
        raise MissingHistoricalMarketDataError(
            _missing_data_message(
                label=label,
                record_type=record_type,
                requested_days=requested_days,
                available_count=available_count,
                policy=policy,
            )
        )
    return typed_records[-requested_days:]


def _missing_data_message(
    *,
    label: str,
    record_type: str,
    requested_days: int,
    available_count: int,
    policy: MissingDataPolicy,
) -> str:
    return (
        "Missing curated PostgreSQL historical market data for "
        f"{label}: requested {requested_days} {record_type}, "
        f"found {available_count}; missing_data_policy={policy}."
    )


def _ohlcv_records_to_frame(
    *,
    records: tuple[MarketOhlcvRecord, ...],
    days: int,
    label: str,
    policy: MissingDataPolicy,
) -> pd.DataFrame:
    if not records:
        raise MissingHistoricalMarketDataError(
            _missing_data_message(
                label=label,
                record_type="OHLCV rows",
                requested_days=max(int(days), 1),
                available_count=0,
                policy=policy,
            )
        )

    frame = pd.DataFrame(
        {
            "open": [record.open_price for record in records],
            "high": [record.high_price for record in records],
            "low": [record.low_price for record in records],
            "close": [record.close_price for record in records],
            "volume": [record.volume for record in records],
            "adjusted_close": [record.adjusted_close for record in records],
        },
        index=pd.DatetimeIndex([record.timestamp for record in records]),
    ).sort_index()
    if frame["adjusted_close"].isna().all():
        frame = frame.drop(
            columns=["adjusted_close"],
        )
    if policy == "forward_fill":
        frame = _forward_fill_frame(
            frame,
            days=days,
        )
    return frame


def _sp500_records_to_frame(
    records: tuple[MarketContextSnapshotRecord, ...],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "market_cap_index": [record.market_cap_index for record in records],
            "advances_count": [record.advances_count for record in records],
            "declines_count": [record.declines_count for record in records],
            "unchanged_count": [record.unchanged_count for record in records],
            "active_count": [record.active_count for record in records],
            "pct_above_50dma": [record.pct_above_50dma for record in records],
            "pct_above_200dma": [record.pct_above_200dma for record in records],
            "new_highs": [record.new_highs for record in records],
            "new_lows": [record.new_lows for record in records],
            "net_breadth": [record.net_breadth for record in records],
            "breadth_percent": [record.breadth_percent for record in records],
            "ad_line": [record.ad_line for record in records],
            "ad_ratio": [record.ad_ratio for record in records],
        },
        index=pd.DatetimeIndex([record.timestamp for record in records]),
    ).sort_index()


def _forward_fill_frame(
    frame: pd.DataFrame,
    *,
    days: int,
) -> pd.DataFrame:
    if frame.empty:
        return frame

    requested_days = max(
        int(days),
        1,
    )
    end = pd.Timestamp(frame.index.max()).normalize()
    index = pd.date_range(
        end=end,
        periods=requested_days,
        freq="D",
    )
    return frame.reindex(index).ffill().bfill()


def _top_50_constituents_from_record(
    record: MarketContextSnapshotRecord,
) -> list[str]:
    payload = record.top_50_constituents_payload
    for key in ("symbols", "top_50_constituents", "constituents"):
        value = payload.get(key)
        if isinstance(value, list | tuple):
            return [str(symbol) for symbol in value]
    if payload:
        return [str(symbol) for symbol in payload]
    return []


def _market_caps_from_record(
    record: MarketContextSnapshotRecord,
) -> dict[str, float]:
    market_caps: dict[str, float] = {}
    for symbol, value in record.market_caps_payload.items():
        if isinstance(value, int | float):
            market_caps[str(symbol)] = float(value)
    return market_caps
