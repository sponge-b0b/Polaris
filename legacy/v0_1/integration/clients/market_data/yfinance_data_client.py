from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any, overload

import httpx
import numpy as np
import pandas as pd
from pandas import DataFrame

from core.telemetry.context import get_active_telemetry_context
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.market.models import SP500Data

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class YFinanceClientOptions:
    """Bounded transport options for Yahoo Finance requests."""

    timeout_seconds: float = 10.0
    max_concurrency: int = 25
    max_connections: int = 50
    max_keepalive_connections: int = 25
    retry_attempts: int = 2


@dataclass(frozen=True, slots=True)
class _HistoryQuery:
    symbol: str
    interval: str
    days: int | None = None
    start_date: date | None = None
    end_date: date | None = None

    def params(self) -> dict[str, str | int]:
        params: dict[str, str | int] = {"interval": self.interval}
        if self.start_date is not None or self.end_date is not None:
            if self.start_date is not None:
                params["period1"] = _utc_epoch(self.start_date)
            if self.end_date is not None:
                params["period2"] = _utc_epoch(self.end_date)
            return params

        params["range"] = f"{self.days or 365}d"
        return params


@dataclass(frozen=True, slots=True)
class _PriceFrames:
    close: DataFrame
    high: DataFrame
    low: DataFrame


@dataclass(frozen=True, slots=True)
class _BreadthCounts:
    advances: pd.Series
    declines: pd.Series
    unchanged: pd.Series
    active: pd.Series


class YFinanceDataClient:
    """Yahoo Finance REST client with bounded concurrent breadth retrieval."""

    _PROVIDER_NAME = "YahooFinance"
    _CONSTITUENTS_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/json,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(
        self,
        options: YFinanceClientOptions | None = None,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._options = options or YFinanceClientOptions()
        self._telemetry = telemetry
        if self._options.max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1.")
        if self._options.retry_attempts < 1:
            raise ValueError("retry_attempts must be at least 1.")

    @overload
    async def get_symbol_data(
        self,
        symbol: str,
        interval: str,
        *,
        days: int,
        client: httpx.AsyncClient | None = None,
    ) -> pd.DataFrame: ...

    @overload
    async def get_symbol_data(
        self,
        symbol: str,
        interval: str,
        *,
        start_date: date,
        end_date: date | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> pd.DataFrame: ...

    async def get_symbol_data(
        self,
        symbol: str,
        interval: str,
        *,
        days: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> pd.DataFrame:
        query = _HistoryQuery(
            symbol=symbol,
            interval=interval,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )
        if client is not None:
            return await self._fetch_symbol_history(query=query, client=client)

        async with self._new_client() as owned_client:
            return await self._fetch_symbol_history(query=query, client=owned_client)

    async def get_sp500_data(
        self,
        interval: str,
        days: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> SP500Data:
        query_template = _HistoryQuery(
            symbol="",
            interval=interval,
            days=days,
            start_date=start_date,
            end_date=end_date,
        )

        async with self._new_client() as client:
            crumb, symbols = await asyncio.gather(
                self._fetch_crumb(client),
                self._fetch_constituents(client),
            )
            semaphore = asyncio.Semaphore(self._options.max_concurrency)
            symbol_results, summary_results = await asyncio.gather(
                self._fetch_symbol_batch(
                    symbols=symbols,
                    query_template=query_template,
                    client=client,
                    semaphore=semaphore,
                ),
                self._fetch_summary_batch(
                    symbols=symbols,
                    crumb=crumb,
                    client=client,
                    semaphore=semaphore,
                ),
            )

        market_data = self._build_market_data(symbol_results, symbols)
        market_caps = dict(summary_results)
        if market_data.empty:
            raise RuntimeError("No S&P 500 symbol data returned from yfinance.")
        if not market_caps:
            raise RuntimeError("No S&P 500 summary data returned from yfinance.")

        analytics = self._build_breadth_analytics(
            market_data=market_data,
            market_caps=market_caps,
            symbols=symbols,
        )
        return SP500Data(
            analytics=analytics,
            top_50_constituents=self._rank_top_constituents(market_caps),
            market_caps=market_caps,
        )

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=self._options.max_keepalive_connections,
                max_connections=self._options.max_connections,
            ),
            follow_redirects=True,
            timeout=self._options.timeout_seconds,
        )

    async def _fetch_crumb(self, client: httpx.AsyncClient) -> str:
        await self._request(
            client=client,
            url="https://fc.yahoo.com/",
            operation="fetch_cookie",
            raise_for_status=False,
        )
        response = await self._request(
            client=client,
            url="https://query1.finance.yahoo.com/v1/test/getcrumb",
            operation="fetch_crumb",
        )
        crumb = response.text.strip()
        if not crumb:
            raise RuntimeError("Yahoo Finance returned an empty session crumb.")
        return crumb

    async def _fetch_constituents(self, client: httpx.AsyncClient) -> list[str]:
        response = await self._request(
            client=client,
            url=self._CONSTITUENTS_URL,
            operation="fetch_constituents",
        )
        tables = await asyncio.to_thread(pd.read_html, response.text)
        if not tables or "Symbol" not in tables[0].columns:
            raise RuntimeError("S&P 500 constituent table did not contain Symbol data.")

        raw_symbols = tables[0]["Symbol"].dropna().astype(str).tolist()
        symbols = [self._normalize_symbol(symbol) for symbol in raw_symbols]
        if not symbols:
            raise RuntimeError("No S&P 500 constituents were returned.")
        return symbols

    async def _fetch_symbol_batch(
        self,
        *,
        symbols: list[str],
        query_template: _HistoryQuery,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ) -> list[DataFrame]:
        results = await asyncio.gather(
            *(
                self._fetch_symbol_history(
                    query=_HistoryQuery(
                        symbol=symbol,
                        interval=query_template.interval,
                        days=query_template.days,
                        start_date=query_template.start_date,
                        end_date=query_template.end_date,
                    ),
                    client=client,
                    semaphore=semaphore,
                )
                for symbol in symbols
            ),
            return_exceptions=True,
        )
        return [
            self._coerce_symbol_result(symbol=symbol, result=result)
            for symbol, result in zip(symbols, results, strict=False)
        ]

    async def _fetch_summary_batch(
        self,
        *,
        symbols: list[str],
        crumb: str,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ) -> list[tuple[str, float]]:
        results = await asyncio.gather(
            *(
                self._fetch_summary_data(
                    symbol=symbol,
                    crumb=crumb,
                    client=client,
                    semaphore=semaphore,
                )
                for symbol in symbols
            ),
            return_exceptions=True,
        )
        return [
            self._coerce_summary_result(symbol=symbol, result=result)
            for symbol, result in zip(symbols, results, strict=False)
        ]

    async def _fetch_symbol_history(
        self,
        *,
        query: _HistoryQuery,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore | None = None,
    ) -> pd.DataFrame:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{query.symbol}"
        try:
            response = await self._request(
                client=client,
                url=url,
                operation="fetch_symbol_history",
                params=query.params(),
                semaphore=semaphore,
            )
        except httpx.HTTPStatusError:
            logger.warning(
                "Yahoo Finance symbol history request failed",
                extra={"symbol": query.symbol},
                exc_info=True,
            )
            return pd.DataFrame()

        raw_data = response.json()
        result = raw_data.get("chart", {}).get("result")
        if not result:
            return pd.DataFrame()

        chart_data = result[0]
        timestamps = chart_data.get("timestamp", [])
        quotes = chart_data.get("indicators", {}).get("quote", [])
        if not timestamps or not quotes:
            return pd.DataFrame()

        indicators = quotes[0]
        row_count = len(timestamps)
        frame = pd.DataFrame(
            {
                "Open": _normalized_values(indicators.get("open"), row_count),
                "High": _normalized_values(indicators.get("high"), row_count),
                "Low": _normalized_values(indicators.get("low"), row_count),
                "Close": _normalized_values(indicators.get("close"), row_count),
                "Volume": _normalized_values(indicators.get("volume"), row_count),
            }
        )
        frame["Volume"] = frame["Volume"].fillna(0).astype("int64")

        datetime_index = pd.to_datetime(timestamps, unit="s", utc=True)
        timezone_name = chart_data.get("meta", {}).get("exchangeTimezoneName", "UTC")
        try:
            datetime_index = datetime_index.tz_convert(timezone_name)
        except (TypeError, ValueError, KeyError):
            logger.warning(
                "Yahoo Finance returned an invalid exchange timezone",
                extra={"symbol": query.symbol, "timezone": timezone_name},
            )

        frame.index = datetime_index
        frame.index.name = "Date"
        return frame

    async def _fetch_summary_data(
        self,
        *,
        symbol: str,
        crumb: str,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ) -> tuple[str, float]:
        response = await self._request(
            client=client,
            url=f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}",
            operation="fetch_summary_data",
            params={
                "modules": ["summaryDetail"],
                "corsDomain": "finance.yahoo.com",
                "formatted": "false",
                "symbol": symbol,
                "region": "US",
                "lang": "en-US",
                "crumb": crumb,
            },
            semaphore=semaphore,
        )
        data = response.json()
        market_cap = data["quoteSummary"]["result"][0]["summaryDetail"]["marketCap"]
        return symbol, float(market_cap or 0.0)

    async def _request(
        self,
        *,
        client: httpx.AsyncClient,
        url: str,
        operation: str,
        params: Mapping[str, str | int | float | bool | None | Sequence[str]]
        | None = None,
        semaphore: asyncio.Semaphore | None = None,
        raise_for_status: bool = True,
    ) -> httpx.Response:
        for attempt in range(self._options.retry_attempts):
            try:
                if semaphore is None:
                    response = await client.get(
                        url,
                        params=params,
                        headers=self._HEADERS,
                    )
                else:
                    async with semaphore:
                        response = await client.get(
                            url,
                            params=params,
                            headers=self._HEADERS,
                        )

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt + 1 < self._options.retry_attempts:
                        await self._schedule_retry(
                            operation=operation,
                            attempt_index=attempt,
                            status_code=response.status_code,
                        )
                        continue
                if raise_for_status:
                    response.raise_for_status()
                return response
            except httpx.TransportError as exc:
                if attempt + 1 >= self._options.retry_attempts:
                    raise
                await self._schedule_retry(
                    operation=operation,
                    attempt_index=attempt,
                    error_type=type(exc).__name__,
                )

        raise RuntimeError("Yahoo Finance request retry loop exited unexpectedly.")

    async def _schedule_retry(
        self,
        *,
        operation: str,
        attempt_index: int,
        status_code: int | None = None,
        error_type: str | None = None,
    ) -> None:
        backoff_seconds = 0.25 * (2**attempt_index)
        if self._telemetry is not None:
            await self._telemetry.emit_client_retry_scheduled(
                provider_name=self._PROVIDER_NAME,
                client_name=self.__class__.__name__,
                operation=operation,
                attempt=attempt_index + 1,
                next_attempt=attempt_index + 2,
                maximum_attempts=self._options.retry_attempts,
                backoff_seconds=backoff_seconds,
                status_code=status_code,
                error_type=error_type,
                context=get_active_telemetry_context(),
            )
        await asyncio.sleep(backoff_seconds)

    def _coerce_symbol_result(
        self,
        *,
        symbol: str,
        result: DataFrame | BaseException,
    ) -> DataFrame:
        if isinstance(result, asyncio.CancelledError):
            raise result
        if isinstance(result, BaseException):
            logger.warning(
                "Yahoo Finance symbol fetch failed",
                extra={"symbol": symbol, "error_type": type(result).__name__},
                exc_info=(type(result), result, result.__traceback__),
            )
            return pd.DataFrame()
        return result

    def _coerce_summary_result(
        self,
        *,
        symbol: str,
        result: tuple[str, float] | BaseException,
    ) -> tuple[str, float]:
        if isinstance(result, asyncio.CancelledError):
            raise result
        if isinstance(result, BaseException):
            logger.warning(
                "Yahoo Finance market-cap fetch failed",
                extra={"symbol": symbol, "error_type": type(result).__name__},
                exc_info=(type(result), result, result.__traceback__),
            )
            return symbol, 0.0
        return result

    def _build_breadth_analytics(
        self,
        *,
        market_data: DataFrame,
        market_caps: dict[str, float],
        symbols: list[str],
    ) -> DataFrame:
        prices = self._extract_price_frames(
            market_data=market_data,
            symbols=symbols,
        )
        counts = self._calculate_breadth_counts(prices.close)
        pct_above_50dma, pct_above_200dma = self._calculate_moving_average_breadth(
            prices.close
        )
        new_highs, new_lows = self._calculate_high_low_counts(prices)

        analytics = pd.DataFrame(
            {
                "market_cap_index": self._build_market_cap_index(
                    close_prices=prices.close,
                    market_caps=market_caps,
                ),
                "advances_count": counts.advances,
                "declines_count": counts.declines,
                "unchanged_count": counts.unchanged,
                "active_count": counts.active,
                "pct_above_50dma": pct_above_50dma,
                "pct_above_200dma": pct_above_200dma,
                "new_highs": new_highs,
                "new_lows": new_lows,
            },
            index=prices.close.index,
        ).iloc[1:]
        analytics["net_breadth"] = (
            analytics["advances_count"] - analytics["declines_count"]
        )
        analytics["breadth_percent"] = np.where(
            analytics["active_count"] > 0,
            analytics["advances_count"] / analytics["active_count"],
            0.0,
        )
        analytics["ad_line"] = analytics["net_breadth"].fillna(0.0).cumsum()
        analytics["ad_ratio"] = np.where(
            analytics["declines_count"] > 0,
            analytics["advances_count"] / analytics["declines_count"],
            np.nan,
        )
        return analytics

    def _extract_price_frames(
        self,
        *,
        market_data: DataFrame,
        symbols: list[str],
    ) -> _PriceFrames:
        available_symbols = set(market_data.columns.get_level_values(0))
        close_prices = self._select_price_field(
            market_data=market_data,
            symbols=symbols,
            available_symbols=available_symbols,
            field="Close",
        ).dropna(how="all")
        if close_prices.empty:
            raise RuntimeError("No usable S&P 500 close prices were returned.")

        return _PriceFrames(
            close=close_prices,
            high=self._select_price_field(
                market_data=market_data,
                symbols=symbols,
                available_symbols=available_symbols,
                field="High",
            ).reindex(close_prices.index),
            low=self._select_price_field(
                market_data=market_data,
                symbols=symbols,
                available_symbols=available_symbols,
                field="Low",
            ).reindex(close_prices.index),
        )

    @staticmethod
    def _select_price_field(
        *,
        market_data: DataFrame,
        symbols: list[str],
        available_symbols: set[str],
        field: str,
    ) -> DataFrame:
        return pd.DataFrame(
            {
                symbol: market_data[symbol][field]
                for symbol in symbols
                if symbol in available_symbols and field in market_data[symbol].columns
            }
        )

    @staticmethod
    def _build_market_cap_index(
        *,
        close_prices: DataFrame,
        market_caps: dict[str, float],
    ) -> pd.Series:
        caps = pd.Series(market_caps, dtype="float64").reindex(close_prices.columns)
        valid_caps = caps.fillna(0.0)
        cap_weights = (
            valid_caps / valid_caps.sum()
            if valid_caps.sum() > 0
            else pd.Series(1.0 / len(close_prices.columns), index=close_prices.columns)
        )
        weighted_returns = (
            close_prices.pct_change(fill_method=None)
            .mul(cap_weights, axis=1)
            .sum(axis=1, min_count=1)
        )
        return 100.0 * (1.0 + weighted_returns.fillna(0.0)).cumprod()

    @staticmethod
    def _calculate_breadth_counts(close_prices: DataFrame) -> _BreadthCounts:
        daily_changes = close_prices.diff()
        advances = (daily_changes > 0).sum(axis=1)
        declines = (daily_changes < 0).sum(axis=1)
        unchanged = daily_changes.notna().sum(axis=1) - advances - declines
        return _BreadthCounts(
            advances=advances,
            declines=declines,
            unchanged=unchanged,
            active=advances + declines,
        )

    @staticmethod
    def _calculate_moving_average_breadth(
        close_prices: DataFrame,
    ) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
        dma_50 = close_prices.rolling(window=50, min_periods=20).mean()
        dma_200 = close_prices.rolling(window=200, min_periods=50).mean()
        valid_50dma_count = dma_50.notna().sum(axis=1)
        valid_200dma_count = dma_200.notna().sum(axis=1)
        return (
            np.where(
                valid_50dma_count > 0,
                (close_prices > dma_50).sum(axis=1) / valid_50dma_count,
                np.nan,
            ),
            np.where(
                valid_200dma_count > 0,
                (close_prices > dma_200).sum(axis=1) / valid_200dma_count,
                np.nan,
            ),
        )

    @staticmethod
    def _calculate_high_low_counts(
        prices: _PriceFrames,
    ) -> tuple[pd.Series, pd.Series]:
        rolling_highs = prices.high.rolling(window=252, min_periods=60).max()
        rolling_lows = prices.low.rolling(window=252, min_periods=60).min()
        return (
            (prices.close >= rolling_highs).sum(axis=1),
            (prices.close <= rolling_lows).sum(axis=1),
        )

    def _build_market_data(
        self,
        results: list[DataFrame],
        symbols: list[str],
    ) -> DataFrame:
        valid_results = [
            (symbol, result)
            for symbol, result in zip(symbols, results, strict=False)
            if isinstance(result, pd.DataFrame) and not result.empty
        ]
        if not valid_results:
            return pd.DataFrame()

        market_data = pd.concat(
            [result for _, result in valid_results],
            axis=1,
            keys=[symbol for symbol, _ in valid_results],
            names=["Symbol", "Price"],
        )
        market_data.index = pd.to_datetime(market_data.index)
        market_data.index.name = "Date"
        return market_data.sort_index()

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        return symbol.replace(".", "-")

    @staticmethod
    def _rank_top_constituents(market_caps: dict[str, float]) -> list[str]:
        return [
            symbol
            for symbol, _ in sorted(
                market_caps.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:50]
        ]


def _utc_epoch(value: date) -> int:
    return int(datetime.combine(value, time.min, tzinfo=UTC).timestamp())


def _normalized_values(value: object, row_count: int) -> list[object | None]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return [None] * row_count
    values = list(value[:row_count])
    return values + [None] * (row_count - len(values))
