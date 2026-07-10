from __future__ import annotations

from datetime import datetime
from typing import Protocol

from domain.portfolio.models.portfolio_state import (
    PortfolioState,
)


class PortfolioStateRepository(Protocol):
    async def persist_snapshot(
        self,
        state: PortfolioState,
    ) -> None: ...

    async def get_latest(
        self,
        account_id: str,
    ) -> PortfolioState | None: ...

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]: ...
