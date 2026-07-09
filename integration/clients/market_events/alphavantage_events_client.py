from __future__ import annotations

import csv
import io
import httpx
from datetime import datetime
from collections.abc import Set
from typing import Optional, Any, Dict, List
from config.settings import Settings


DEFAULT_EARNINGS_SYMBOLS = frozenset(
    {
        "AAPL",
        "AMZN",
        "GOOG",
        "GOOGL",
        "META",
        "MSFT",
        "NVDA",
        "TSLA",
    }
)


class AlphaVantageEarningsClient:
    """
    Alpha Vantage earnings calendar client.

    Docs:
    https://www.alphavantage.co/documentation/#earnings-calendar

    Endpoint returns CSV data.
    """

    BASE_URL = "https://www.alphavantage.co/query"

    VALID_HORIZONS = {
        "3month",
        "6month",
        "12month",
    }

    def __init__(
        self,
        settings: Settings,
        timeout: int = 30,
    ) -> None:

        self.api_key = settings.ALPHAVANTAGE_API_KEY
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("Missing ALPHAVANTAGE_API_KEY environment variable.")

    async def get_earnings_calendar(
        self,
        horizon: str = "3month",
        symbols: Set[str] | None = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch upcoming earnings calendar events.

        Args:
            horizon:
                One of:
                - 3month
                - 6month
                - 12month

            symbols:
                Optional symbol filter.

        Returns:
            List of normalized earnings event mappings.
        """

        if horizon not in self.VALID_HORIZONS:
            raise ValueError(
                f"Invalid horizon '{horizon}'. Expected one of {self.VALID_HORIZONS}"
            )

        params = {
            "function": "EARNINGS_CALENDAR",
            "horizon": horizon,
            "apikey": self.api_key,
        }

        if client is not None:
            response = await client.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.timeout,
                )

        response.raise_for_status()
        csv_text = response.text.strip()

        if not csv_text:
            return []

        return self._parse_csv(
            csv_text=csv_text,
            symbols=DEFAULT_EARNINGS_SYMBOLS if symbols is None else symbols,
        )

    def _parse_csv(
        self,
        csv_text: str,
        symbols: Set[str] | None = None,
    ) -> List[Dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(csv_text))

        events: List[Dict[str, Any]] = []

        symbol_filter = {s.upper() for s in symbols} if symbols else None

        for row in reader:
            symbol = row.get("symbol", "").upper()

            if symbol_filter and symbol not in symbol_filter:
                continue

            events.append(
                {
                    "symbol": symbol,
                    "company": row.get("name", "").strip(),
                    "report_date": self._parse_date(row.get("reportDate")),
                    "fiscal_date_ending": self._parse_optional_date(
                        row.get("fiscalDateEnding")
                    ),
                    "estimate": self._parse_optional_float(row.get("estimate")),
                    "currency": row.get("currency"),
                }
            )

        return events

    @staticmethod
    def _parse_date(value: str | None) -> datetime:
        if not value:
            raise ValueError("Missing required report date")

        return datetime.strptime(value, "%Y-%m-%d")

    @staticmethod
    def _parse_optional_date(
        value: str | None,
    ) -> datetime | None:
        if not value:
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _parse_optional_float(
        value: str | None,
    ) -> float | None:
        if value in (None, "", "None"):
            return None

        try:
            return float(value)
        except ValueError:
            return None
