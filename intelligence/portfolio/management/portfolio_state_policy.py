from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from application.services.portfolio.portfolio_result import PortfolioAnalysisResult

_EQUITY_FIELD_DEFAULTS: tuple[tuple[str, object], ...] = (
    ("equity", 0.0),
    ("portfolio_value", 0.0),
    ("cash", 0.0),
    ("buying_power", 0.0),
    ("regt_buying_power", 0.0),
    ("daytrading_buying_power", 0.0),
    ("non_marginable_buying_power", 0.0),
    ("options_buying_power", 0.0),
    ("realized_pnl", 0.0),
    ("unrealized_pnl", 0.0),
    ("pnl_total", 0.0),
    ("last_equity", 0.0),
    ("peak_equity", 0.0),
    ("capital_base", 0.0),
    ("equity_retention_ratio", 0.0),
    ("cash_ratio", 0.0),
    ("buying_power_ratio", 0.0),
    ("long_market_value", 0.0),
    ("short_market_value", 0.0),
    ("gross_market_value", 0.0),
    ("net_market_value", 0.0),
    ("long_exposure_ratio", 0.0),
    ("short_exposure_ratio", 0.0),
    ("gross_exposure_ratio", 0.0),
    ("net_exposure_ratio", 0.0),
    ("initial_margin", 0.0),
    ("maintenance_margin", 0.0),
    ("last_maintenance_margin", 0.0),
    ("margin_utilization_ratio", 0.0),
    ("initial_margin_ratio", 0.0),
    ("multiplier", 0.0),
    ("accrued_fees", 0.0),
    ("pending_transfer_in", 0.0),
    ("pending_transfer_out", 0.0),
    ("daytrade_count", 0),
    ("pattern_day_trader", False),
    ("trading_blocked", False),
    ("transfers_blocked", False),
    ("account_blocked", False),
    ("trade_suspended_by_user", False),
    ("shorting_enabled", False),
    ("options_approved_level", 0),
    ("options_trading_level", 0),
    ("account_health", "unknown"),
    ("risk_signals", ()),
)


@dataclass(
    frozen=True,
    slots=True,
)
class PortfolioStateDecision:
    """Deterministic portfolio-state normalization result."""

    portfolio_state: dict[str, Any]
    equity_state: dict[str, Any]
    positions_state: dict[str, Any]
    risk_features: dict[str, Any]
    position_count: int
    drawdown_percent: float

    def to_runtime_outputs(self) -> dict[str, Any]:
        risks: list[str] = []

        if float(self.portfolio_state.get("concentration_score", 0.0)) >= 0.45:
            risks.append("capital_concentration_risk")

        if float(self.portfolio_state.get("cash_pct", 0.0)) <= 0.10:
            risks.append("liquidity_risk")

        if self.drawdown_percent >= 0.10:
            risks.append("deep_drawdown_risk")

        return {
            "directional_score": 0.0,
            "confidence": 1.0,
            "regime": self.portfolio_state.get("portfolio_regime", "unknown"),
            "signals": [
                "portfolio_normalized",
                "canonical_portfolio_state",
            ],
            "risks": risks,
            "recommendations": [
                "use canonical portfolio state only",
                "do not recompute exposure downstream",
                "consume normalized risk features",
            ],
            "features": {
                "portfolio_state": self.portfolio_state,
                "equity_state": self.equity_state,
                "positions_state": self.positions_state,
                "risk_features": self.risk_features,
            },
        }


def build_portfolio_state_decision(
    portfolio: PortfolioAnalysisResult,
) -> PortfolioStateDecision:
    """Normalize one typed service result without runtime or telemetry concerns."""

    portfolio_state = dict(portfolio.portfolio_state)
    positions_state = dict(portfolio.positions_state)
    equity_state = dict(portfolio.equity_state)

    positions = list(positions_state.get("positions", []))
    position_count = int(positions_state.get("position_count", len(positions)))
    drawdown_absolute = float(equity_state.get("drawdown_absolute", 0.0))
    drawdown_percent = float(equity_state.get("drawdown_percent", 0.0))

    normalized_positions_state = {
        **positions_state,
        "positions": positions,
        "position_count": position_count,
    }
    normalized_equity_state = {
        key: equity_state.get(key, default) for key, default in _EQUITY_FIELD_DEFAULTS
    }
    normalized_equity_state["risk_signals"] = list(equity_state.get("risk_signals", []))
    normalized_equity_state["drawdown_absolute"] = drawdown_absolute
    normalized_equity_state["drawdown_percent"] = drawdown_percent

    cash_ratio = equity_state.get(
        "cash_ratio",
        portfolio_state.get("cash_pct", 0.0),
    )
    margin_utilization_ratio = equity_state.get(
        "margin_utilization_ratio",
        0.0,
    )
    risk_features = {
        "capital_utilization": portfolio_state.get("gross_exposure", 0.0),
        "net_exposure": portfolio_state.get("net_exposure", 0.0),
        "risk_intensity": portfolio_state.get("risk_intensity", 0.0),
        "concentration": portfolio_state.get("concentration_score", 0.0),
        "leverage": portfolio_state.get("leverage", 0.0),
        "cash_buffer": cash_ratio,
        "portfolio_stress": drawdown_percent,
        "position_density": min(1.0, len(positions) / 10.0),
        "beta_exposure": portfolio_state.get("beta_exposure", 0.0),
        "beta_risk": portfolio_state.get("beta_risk", 0.0),
        "portfolio_heat": portfolio_state.get("portfolio_heat", 0.0),
        "largest_position_pct": portfolio_state.get("largest_position_pct", 0.0),
        "diversification_score": portfolio_state.get(
            "diversification_score",
            0.0,
        ),
        "cash_ratio": equity_state.get("cash_ratio", 0.0),
        "buying_power_ratio": equity_state.get("buying_power_ratio", 0.0),
        "margin_utilization": margin_utilization_ratio,
        "margin_utilization_ratio": margin_utilization_ratio,
        "initial_margin_ratio": equity_state.get("initial_margin_ratio", 0.0),
        "maintenance_margin": equity_state.get("maintenance_margin", 0.0),
        "last_maintenance_margin": equity_state.get(
            "last_maintenance_margin",
            0.0,
        ),
        "account_health": equity_state.get("account_health", "unknown"),
        "trading_blocked": equity_state.get("trading_blocked", False),
        "transfers_blocked": equity_state.get("transfers_blocked", False),
        "account_blocked": equity_state.get("account_blocked", False),
        "trade_suspended_by_user": equity_state.get(
            "trade_suspended_by_user",
            False,
        ),
        "pattern_day_trader": equity_state.get("pattern_day_trader", False),
        "shorting_enabled": equity_state.get("shorting_enabled", False),
    }

    return PortfolioStateDecision(
        portfolio_state=portfolio_state,
        equity_state=normalized_equity_state,
        positions_state=normalized_positions_state,
        risk_features=risk_features,
        position_count=position_count,
        drawdown_percent=drawdown_percent,
    )
