from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from config.settings import Settings

logger = logging.getLogger(__name__)


class FredEventsClient:
    """FRED release-calendar client for forward-looking macro events."""

    BASE_URL = "https://api.stlouisfed.org/fred/release/dates"
    SERIES_TO_RELEASE_ID = {
        "CPI": 10,
        "PPI": 40,
        "GDP": 53,
        "UNEMPLOYMENT": 50,
        "RETAIL_SALES": 27,
        "INDUSTRIAL_PRODUCTION": 30,
    }

    def __init__(self, settings: Settings, timeout: int = 10) -> None:
        self.api_key = settings.FRED_API_KEY
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("Missing FRED_API_KEY environment variable.")

    async def get_economic_events(
        self,
        days_ahead: int = 14,
    ) -> list[dict[str, Any]]:
        series_names = tuple(self.SERIES_TO_RELEASE_ID)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            results = await asyncio.gather(
                *(
                    self._get_release_dates(release_id=release_id, client=client)
                    for release_id in self.SERIES_TO_RELEASE_ID.values()
                ),
                return_exceptions=True,
            )

        events: list[dict[str, Any]] = []
        failed_sources: list[str] = []
        for series_name, release_id, result in zip(
            series_names,
            self.SERIES_TO_RELEASE_ID.values(),
            results,
        ):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                failed_sources.append(series_name)
                logger.warning(
                    "FRED release source failed",
                    extra={
                        "series_name": series_name,
                        "release_id": release_id,
                        "error_type": type(result).__name__,
                    },
                    exc_info=(type(result), result, result.__traceback__),
                )
                continue
            events.extend(
                self._fetch_events(
                    release_id=release_id,
                    days_ahead=days_ahead,
                    series_name=series_name,
                    release_dates=result,
                )
            )

        if len(failed_sources) == len(series_names):
            raise RuntimeError("All FRED release sources failed.")
        return self._normalize(events)

    async def _get_release_dates(
        self,
        release_id: int,
        client: httpx.AsyncClient,
    ) -> list[dict[str, Any]]:
        response = await client.get(
            self.BASE_URL,
            params={
                "release_id": release_id,
                "api_key": self.api_key,
                "file_type": "json",
            },
        )
        response.raise_for_status()
        release_dates = response.json().get("release_dates", [])
        return [item for item in release_dates if isinstance(item, dict)]

    def _fetch_events(
        self,
        release_id: int,
        days_ahead: int,
        series_name: str,
        release_dates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        events: list[dict[str, Any]] = []
        for item in release_dates:
            date_str = item.get("date")
            if not isinstance(date_str, str) or not date_str:
                continue
            try:
                event_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            if event_time < now or (event_time - now).days > days_ahead:
                continue
            events.append(
                {
                    "series": series_name,
                    "release_id": release_id,
                    "timestamp": event_time.isoformat(),
                }
            )
        return events

    def _normalize(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for event in events:
            series = str(event.get("series", "unknown"))
            if series in ("CPI", "GDP", "UNEMPLOYMENT"):
                impact = 0.95
            elif series in ("RETAIL_SALES", "PPI"):
                impact = 0.80
            else:
                impact = 0.65
            normalized.append(
                {
                    "name": f"{series} Release",
                    "event_type": "macro",
                    "subtype": "fred_release",
                    "timestamp": event.get("timestamp"),
                    "symbol": "SPY",
                    "impact": impact,
                    "direction_bias": "neutral",
                    "release_id": event.get("release_id"),
                    "source": "fred_events",
                }
            )
        return normalized
