import asyncio
import pandas as pd

from datetime import datetime, timedelta, timezone, date
from massive import RESTClient
from massive.rest.models.aggs import Agg
from typing import Iterable, cast, overload, Optional

from config.settings import Settings


class MassiveDataClient:
    """
    Massive REST client.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self.api_key = settings.MASSIVE_API_KEY

        if not self.api_key:
            raise ValueError("Missing MASSIVE_API_KEY environment variable.")

        self.client = RESTClient(api_key=self.api_key)

    # ============================================================
    # SYMBOL DATA
    # ============================================================

    @overload
    async def get_symbol_data(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        *,
        days: int,
    ) -> pd.DataFrame: ...

    @overload
    async def get_symbol_data(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        *,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame: ...

    async def get_symbol_data(
        self,
        symbol: str,
        multiplier: int,
        timespan: str,
        *,
        days: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:

        from_date = date.today()
        to_date = date.today()

        if start_date is None and end_date is None:
            from_date = to_date - timedelta(days=days or 365)
        elif start_date is None:
            to_date = end_date
            from_date = to_date - timedelta(days=days or 365)
        elif end_date is None:
            from_date = start_date
        else:
            from_date = start_date
            to_date = end_date

        aggs = cast(
            Iterable[Agg],
            await asyncio.to_thread(
                self.client.list_aggs,
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=str(from_date),
                to=str(to_date),
                adjusted=True,
                sort="asc",
                limit=50000,
            ),
        )

        rows = []
        for agg in aggs:
            if agg.timestamp is None:
                continue

            timestamp = datetime.fromtimestamp(
                int(agg.timestamp) / 1000,
                tz=timezone.utc,
            )

            rows.append(
                {
                    "datetime": timestamp,
                    "open": agg.open,
                    "high": agg.high,
                    "low": agg.low,
                    "close": agg.close,
                    "volume": agg.volume,
                    "vwap": getattr(agg, "vwap", None),
                    "transactions": getattr(
                        agg,
                        "transactions",
                        None,
                    ),
                }
            )

        return pd.DataFrame(rows)
