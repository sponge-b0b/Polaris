from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PortfolioProvider(Protocol):
    """
    Canonical portfolio provider interface.

    ALL portfolio providers MUST implement this interface.
    """

    @property
    def source(self) -> str: ...

    async def get_account(self) -> dict[str, Any]: ...

    async def get_positions(self) -> list[dict[str, Any]]: ...

    async def get_portfolio_history(
        self,
        *,
        period: str = "1A",
        timeframe: str = "1D",
    ) -> dict[str, Any]: ...
