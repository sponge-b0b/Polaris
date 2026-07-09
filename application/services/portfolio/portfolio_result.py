from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioAnalysisResult:
    """Typed result for portfolio analysis orchestration."""

    portfolio_state: dict[str, Any]
    positions_state: dict[str, Any]
    equity_state: dict[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "portfolio_state": deepcopy(self.portfolio_state),
            "positions_state": deepcopy(self.positions_state),
            "equity_state": deepcopy(self.equity_state),
        }
