from __future__ import annotations

from datetime import datetime

from domain.portfolio.models.portfolio_state import PortfolioState


class InMemoryPortfolioStateRepository:
    """Invocation-local portfolio snapshots for synchronous runtime composition."""

    def __init__(self) -> None:
        self._states: dict[str, list[PortfolioState]] = {}

    async def persist_snapshot(self, state: PortfolioState) -> None:
        self._states.setdefault(state.account_id, []).append(state)

    async def get_latest(self, account_id: str) -> PortfolioState | None:
        states = self._states.get(account_id, [])
        return states[-1] if states else None

    async def get_history(
        self,
        account_id: str,
        start: datetime,
        end: datetime,
    ) -> list[PortfolioState]:
        return [
            state
            for state in self._states.get(account_id, [])
            if start <= state.timestamp <= end
        ]
