from __future__ import annotations

from datetime import datetime

from polaris.domain.decisions import InvestmentDecisionId

from .contracts import (
    DecisionCommandReadUnavailable,
    DecisionMemoryReader,
    PersistenceUnavailable,
)


async def read_continuity_candidates(
    reader: DecisionMemoryReader,
    known_at: datetime,
) -> frozenset[InvestmentDecisionId]:
    try:
        return frozenset(
            await reader.find_unresolved_continuity_candidates(known_at=known_at)
        )
    except DecisionCommandReadUnavailable as error:
        raise PersistenceUnavailable(str(error)) from error
