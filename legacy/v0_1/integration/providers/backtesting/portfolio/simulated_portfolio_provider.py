from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from integration.providers.portfolio.portfolio_provider import (
    PortfolioProvider,
)


@dataclass
class SimPosition:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    side: str  # long / short

    def market_value(self) -> float:
        return abs(self.quantity * self.current_price)

    def signed_value(self) -> float:
        value = self.market_value()
        return value if self.side == "long" else -value

    def cost_basis(self) -> float:
        return abs(self.quantity * self.entry_price)

    def unrealized_pl(self) -> float:
        if self.side == "short":
            return self.cost_basis() - self.market_value()

        return self.market_value() - self.cost_basis()

    def unrealized_plpc(self) -> float:
        cost_basis = self.cost_basis()

        if cost_basis <= 0.0:
            return 0.0

        return self.unrealized_pl() / cost_basis


class SimulatedPortfolioProvider(PortfolioProvider):
    """
    Deterministic Backtest Portfolio Provider

    ============================================================
    PURPOSE
    ============================================================
    Acts as a broker replacement for backtesting.

    Provides:
    - positions
    - account state
    - deterministic execution of signals

    This is the ONLY stateful component in backtesting.
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
    ):
        self.initial_capital = float(initial_capital)

        self.cash: float = float(initial_capital)
        self.equity: float = float(initial_capital)
        self.last_equity: float = float(initial_capital)

        self.positions: dict[str, SimPosition] = {}

        self.realized_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0

        self._history_step: int = 0
        self._history_timestamps: list[int] = []
        self._history_equity: list[float] = []
        self._history_profit_loss: list[float] = []
        self._history_profit_loss_pct: list[float | None] = []
        self._record_portfolio_history()

    @property
    def source(self) -> str:
        return "simulated"

    # ============================================================
    # MARKET UPDATE (CRITICAL)
    # ============================================================

    def update_market(self, symbol: str, price: float):
        """
        Updates mark-to-market pricing.
        """

        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = price

        self._recalculate_equity()

        return self  # pipeline compatibility

    # ============================================================
    # EXECUTION INTERFACE (USED BY BACKTEST ENGINE)
    # ============================================================

    def apply_signal(
        self,
        symbol: str,
        side: str,
        price: float,
        capital_allocation: float,
    ):
        """
        Deterministic fill simulation.
        """

        side = side.lower()

        if capital_allocation <= 0:
            return

        quantity = capital_allocation / price

        if symbol in self.positions:
            # simple position overwrite model (deterministic)
            existing = self.positions[symbol]

            if existing.side == side:
                # scale in
                existing.quantity += quantity
                existing.entry_price = (existing.entry_price + price) / 2
                existing.current_price = price

            else:
                # flip position
                self.realized_pnl += existing.market_value() * 0.01
                self.positions[symbol] = SimPosition(
                    symbol=symbol,
                    quantity=quantity,
                    entry_price=price,
                    current_price=price,
                    side=side,
                )

        else:
            self.positions[symbol] = SimPosition(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                current_price=price,
                side=side,
            )

        self.cash -= capital_allocation

        self._recalculate_equity()

    # ============================================================
    # ACCOUNT API (LIVE COMPATIBLE)
    # ============================================================

    async def get_account(self) -> dict[str, Any]:
        return {
            "id": "simulated-account",
            "account_number": "SIMULATED",
            "status": "ACTIVE",
            "currency": "USD",
            "equity": self.equity,
            "last_equity": self.last_equity,
            "cash": self.cash,
            "buying_power": self.cash,
            "regt_buying_power": self.cash,
            "daytrading_buying_power": self.cash,
            "non_marginable_buying_power": self.cash,
            "options_buying_power": 0.0,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "portfolio_value": self.equity,
            "long_market_value": self._long_market_value(),
            "short_market_value": self._short_market_value(),
            "initial_margin": 0.0,
            "maintenance_margin": 0.0,
            "last_maintenance_margin": 0.0,
            "multiplier": 1.0,
            "accrued_fees": 0.0,
            "pending_transfer_in": 0.0,
            "pending_transfer_out": 0.0,
            "daytrade_count": 0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "transfers_blocked": False,
            "account_blocked": False,
            "trade_suspended_by_user": False,
            "shorting_enabled": True,
            "options_approved_level": 0,
            "options_trading_level": 0,
        }

    # ============================================================
    # POSITIONS API (LIVE COMPATIBLE)
    # ============================================================

    async def get_positions(self) -> list[dict[str, Any]]:
        return [
            {
                "symbol": p.symbol,
                "asset_id": f"sim-{p.symbol.lower()}",
                "exchange": "SIM",
                "asset_class": "equity",
                "asset_marginable": True,
                "sector": "simulated",
                "beta": 1.0,
                "qty": p.quantity,
                "quantity": p.quantity,
                "qty_available": p.quantity,
                "avg_entry_price": p.entry_price,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "lastday_price": p.current_price,
                "change_today": 0.0,
                "market_value": p.market_value(),
                "cost_basis": p.cost_basis(),
                "unrealized_pl": p.unrealized_pl(),
                "unrealized_plpc": p.unrealized_plpc(),
                "unrealized_intraday_pl": 0.0,
                "unrealized_intraday_plpc": 0.0,
                "side": p.side,
            }
            for p in self.positions.values()
        ]

    # ============================================================
    # PORTFOLIO HISTORY
    # ============================================================

    async def get_portfolio_history(
        self,
        *,
        period: str = "1A",
        timeframe: str = "1D",
    ) -> dict[str, Any]:
        return {
            "timestamp": list(self._history_timestamps),
            "equity": list(self._history_equity),
            "profit_loss": list(self._history_profit_loss),
            "profit_loss_pct": list(self._history_profit_loss_pct),
            "base_value": self.initial_capital,
            "timeframe": timeframe,
            "cashflow": {},
        }

    # ============================================================
    # INTERNAL EQUITY ENGINE
    # ============================================================

    def _record_portfolio_history(self) -> None:
        profit_loss = self.equity - self.initial_capital
        profit_loss_pct = (
            profit_loss / self.initial_capital if self.initial_capital > 0.0 else None
        )

        self._history_timestamps.append(self._history_step)
        self._history_equity.append(self.equity)
        self._history_profit_loss.append(profit_loss)
        self._history_profit_loss_pct.append(profit_loss_pct)
        self._history_step += 1

    def _recalculate_equity(self):
        self.last_equity = self.equity

        self.unrealized_pnl = sum(
            position.unrealized_pl() for position in self.positions.values()
        )

        self.equity = self.cash + sum(p.signed_value() for p in self.positions.values())

        self._record_portfolio_history()

    def _long_market_value(self) -> float:
        return sum(
            position.market_value()
            for position in self.positions.values()
            if position.side == "long"
        )

    def _short_market_value(self) -> float:
        return -sum(
            position.market_value()
            for position in self.positions.values()
            if position.side == "short"
        )
