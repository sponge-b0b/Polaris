from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast

import httpx

from config.settings import Settings


@dataclass(
    frozen=True,
    slots=True,
)
class FredSeriesObservation:
    """Typed outcome for one requested FRED series."""

    series_id: str
    value: float | None
    error_type: str | None = None
    error_message: str | None = None

    @property
    def failed(self) -> bool:
        return self.error_type is not None


class FredMacroClient:
    """Vendor-specific FRED HTTP client."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(
        self,
        settings: Settings,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = settings.FRED_API_KEY
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("Missing FRED_API_KEY environment variable.")

    async def get_latest_observations(
        self,
        series_ids: tuple[str, ...],
    ) -> tuple[FredSeriesObservation, ...]:
        """Fetch the latest requested observations concurrently over one HTTP client."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            results = await asyncio.gather(
                *(
                    self._get_latest_observation(
                        client=client,
                        series_id=series_id,
                    )
                    for series_id in series_ids
                ),
                return_exceptions=True,
            )

        observations: list[FredSeriesObservation] = []
        for series_id, result in zip(series_ids, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                if not isinstance(result, Exception):
                    raise result
                observations.append(
                    FredSeriesObservation(
                        series_id=series_id,
                        value=None,
                        error_type=type(result).__name__,
                        error_message=self._safe_error_message(result),
                    )
                )
                continue
            observations.append(result)

        return tuple(observations)

    async def get_economic_data(
        self,
        series_id: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Fetch raw historical FRED data at the vendor boundary."""

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.BASE_URL,
                params=self._request_params(
                    series_id=series_id,
                    limit=limit or 100,
                ),
            )

        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    async def _get_latest_observation(
        self,
        client: httpx.AsyncClient,
        series_id: str,
    ) -> FredSeriesObservation:
        response = await client.get(
            self.BASE_URL,
            params=self._request_params(
                series_id=series_id,
                limit=1,
            ),
        )
        response.raise_for_status()
        data = cast(dict[str, Any], response.json())
        observations = data.get("observations", [])

        if not isinstance(observations, list) or not observations:
            return FredSeriesObservation(
                series_id=series_id,
                value=None,
            )

        latest = observations[0]
        if not isinstance(latest, dict):
            raise ValueError("FRED observation payload must be an object.")

        value = latest.get("value")
        if value in (".", None):
            return FredSeriesObservation(
                series_id=series_id,
                value=None,
            )

        return FredSeriesObservation(
            series_id=series_id,
            value=float(value),
        )

    def _request_params(
        self,
        *,
        series_id: str,
        limit: int,
    ) -> dict[str, str | int]:
        return {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }

    @staticmethod
    def _safe_error_message(error: Exception) -> str:
        if isinstance(error, httpx.HTTPStatusError):
            return f"FRED returned HTTP {error.response.status_code}."
        return f"FRED request failed with {type(error).__name__}."
