from __future__ import annotations

import asyncio

from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest

from config.settings import Settings
from integration.clients.macro import fred_macro_client as fred_module
from integration.clients.macro.fred_macro_client import FredMacroClient


def _settings() -> Settings:
    return cast(Settings, SimpleNamespace(FRED_API_KEY="test-secret"))


@pytest.mark.asyncio
async def test_latest_observations_share_one_client_and_run_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    series_ids = ("CPIAUCSL", "FEDFUNDS", "VIXCLS")
    values = {
        "CPIAUCSL": "3.2",
        "FEDFUNDS": "5.0",
        "VIXCLS": "18.0",
    }
    started = 0
    all_started = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal started
        started += 1
        if started == len(series_ids):
            all_started.set()
        await all_started.wait()
        series_id = request.url.params["series_id"]
        return httpx.Response(
            200,
            json={"observations": [{"value": values[series_id]}]},
        )

    real_async_client = httpx.AsyncClient
    construction_count = 0

    def build_client(**kwargs: Any) -> httpx.AsyncClient:
        nonlocal construction_count
        construction_count += 1
        return real_async_client(
            transport=httpx.MockTransport(handler),
            **kwargs,
        )

    monkeypatch.setattr(fred_module.httpx, "AsyncClient", build_client)

    observations = await asyncio.wait_for(
        FredMacroClient(settings=_settings()).get_latest_observations(series_ids),
        timeout=1.0,
    )

    assert construction_count == 1
    assert started == len(series_ids)
    assert tuple(item.series_id for item in observations) == series_ids
    assert tuple(item.value for item in observations) == (3.2, 5.0, 18.0)
    assert all(not item.failed for item in observations)


@pytest.mark.asyncio
async def test_latest_observations_isolates_failures_without_leaking_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        series_id = request.url.params["series_id"]
        if series_id == "FAILED":
            return httpx.Response(503, json={"error": "unavailable"})
        value = "." if series_id == "MISSING" else "4.25"
        return httpx.Response(200, json={"observations": [{"value": value}]})

    real_async_client = httpx.AsyncClient

    def build_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_async_client(
            transport=httpx.MockTransport(handler),
            **kwargs,
        )

    monkeypatch.setattr(fred_module.httpx, "AsyncClient", build_client)

    observations = await FredMacroClient(settings=_settings()).get_latest_observations(
        ("DGS10", "MISSING", "FAILED")
    )

    assert observations[0].value == 4.25
    assert observations[1].value is None
    assert observations[1].failed is False
    assert observations[2].value is None
    assert observations[2].error_type == "HTTPStatusError"
    assert observations[2].error_message == "FRED returned HTTP 503."
    assert "test-secret" not in str(observations[2])


@pytest.mark.asyncio
async def test_latest_observations_propagates_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FredMacroClient(settings=_settings())

    async def cancelled_request(**kwargs: Any) -> object:
        raise asyncio.CancelledError

    monkeypatch.setattr(client, "_get_latest_observation", cancelled_request)

    with pytest.raises(asyncio.CancelledError):
        await client.get_latest_observations(("CPIAUCSL",))
