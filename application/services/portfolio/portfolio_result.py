from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.storage.persistence.portfolio import PortfolioEquityHistoryPointRecord
from domain.portfolio.models.portfolio_state import PortfolioState


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioAnalysisResult:
    """Typed result for portfolio analysis orchestration."""

    portfolio_state: dict[str, Any]
    positions_state: dict[str, Any]
    equity_state: dict[str, Any]
    canonical_portfolio_state: PortfolioState | None = None
    positions: tuple[dict[str, Any], ...] = ()
    exposures: dict[str, Any] | None = None
    risk_metrics: dict[str, Any] | None = None
    allocation_data: dict[str, Any] | None = None
    current_equity: float = 0.0
    equity_history_points: tuple[PortfolioEquityHistoryPointRecord, ...] = ()
    peak_equity: float = 0.0
    drawdown_absolute: float = 0.0
    drawdown_percent: float = 0.0
    provider_source: str = ""
    history_period: str = ""
    history_timeframe: str = ""

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "portfolio_state": deepcopy(self.portfolio_state),
            "positions_state": deepcopy(self.positions_state),
            "equity_state": deepcopy(self.equity_state),
            "canonical_portfolio_state": _serialize_value(
                self.canonical_portfolio_state,
            ),
            "positions": _serialize_value(self.positions),
            "exposures": deepcopy(self.exposures or {}),
            "risk_metrics": deepcopy(self.risk_metrics or {}),
            "allocation_data": deepcopy(self.allocation_data or {}),
            "current_equity": self.current_equity,
            "equity_history_points": _serialize_value(self.equity_history_points),
            "peak_equity": self.peak_equity,
            "drawdown_absolute": self.drawdown_absolute,
            "drawdown_percent": self.drawdown_percent,
            "provider_source": self.provider_source,
            "history_period": self.history_period,
            "history_timeframe": self.history_timeframe,
        }


def _serialize_value(
    value: Any,
) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, PortfolioState):
        return _serialize_value(asdict(value))

    if isinstance(value, PortfolioEquityHistoryPointRecord):
        return _serialize_value(asdict(value))

    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}

    if isinstance(value, tuple | list):
        return [_serialize_value(item) for item in value]

    if hasattr(value, "as_dict"):
        return _serialize_value(value.as_dict())

    return deepcopy(value)
