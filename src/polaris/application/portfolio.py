"""Inward-owned durable actual Portfolio State capability."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from polaris.domain.portfolio import (
    PortfolioId,
    PortfolioState,
    PortfolioStateId,
    RecordedPortfolioState,
)


class PortfolioStateConflict(Exception):
    """The State identity already denotes a different durable fact."""


class PortfolioStateStoreFailure(Exception):
    """The durable State operation did not complete."""


class PortfolioStateStore(Protocol):
    async def append(self, state: PortfolioState) -> RecordedPortfolioState:
        """Persist a new actual State with a trusted knowledge timestamp."""

    async def get(self, state_id: PortfolioStateId) -> RecordedPortfolioState | None:
        """Read the exact immutable State selected by a material judgment."""

    async def history(
        self,
        portfolio_id: PortfolioId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> tuple[RecordedPortfolioState, ...]:
        """Return all States observable at (effective_at, known_at).

        The caller chooses an exact State root; row order does not establish
        source authority or silently resolve conflicting observations.
        """
