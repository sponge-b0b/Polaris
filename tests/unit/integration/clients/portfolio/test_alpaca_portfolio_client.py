from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

import pytest

from integration.clients.portfolio.alpaca_portfolio_client import (
    AlpacaPortfolioClient,
)


def _client_without_init() -> AlpacaPortfolioClient:
    return object.__new__(AlpacaPortfolioClient)


def _async_method(
    value: Any,
) -> Awaitable[Any]:
    async def method() -> Any:
        return value

    return method()


@pytest.mark.asyncio
async def test_get_full_portfolio_snapshot_resolves_async_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client_without_init()

    async def get_account() -> dict[str, Any]:
        return {"id": "acct-1", "equity": "100000"}

    async def get_positions() -> list[dict[str, Any]]:
        return [{"symbol": "SPY", "qty": "1"}]

    async def get_portfolio_history() -> dict[str, Any]:
        return {"profit_loss": [100.0]}

    monkeypatch.setattr(client, "get_account", get_account)
    monkeypatch.setattr(client, "get_positions", get_positions)
    monkeypatch.setattr(client, "get_portfolio_history", get_portfolio_history)

    snapshot = await client.get_full_portfolio_snapshot()

    assert snapshot == {
        "account": {"id": "acct-1", "equity": "100000"},
        "positions": [{"symbol": "SPY", "qty": "1"}],
        "portfolio": {"profit_loss": [100.0]},
    }
    assert not hasattr(snapshot["account"], "__await__")
    assert not hasattr(snapshot["positions"], "__await__")
    assert not hasattr(snapshot["portfolio"], "__await__")
