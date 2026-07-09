from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping

from application.services.backtesting.backtest_request import BacktestInitialPosition
from application.services.backtesting.backtest_request import BacktestScenario
from application.services.backtesting.backtest_result import BacktestFill
from application.services.backtesting.backtest_result import BacktestPortfolioSnapshot


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestLedgerPosition:
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_price: Decimal
    realized_pnl: Decimal = Decimal("0")

    @classmethod
    def from_initial_position(
        cls,
        position: BacktestInitialPosition,
    ) -> BacktestLedgerPosition:
        return cls(
            symbol=position.symbol,
            quantity=position.quantity,
            average_price=position.average_price,
            current_price=position.average_price,
        )

    @property
    def market_value(
        self,
    ) -> Decimal:
        return abs(self.quantity) * self.current_price

    @property
    def signed_market_value(
        self,
    ) -> Decimal:
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(
        self,
    ) -> Decimal:
        if self.quantity < Decimal("0"):
            return (self.average_price - self.current_price) * abs(self.quantity)

        return (self.current_price - self.average_price) * self.quantity

    def to_snapshot_payload(
        self,
    ) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "average_price": str(self.average_price),
            "current_price": str(self.current_price),
            "market_value": str(self.market_value),
            "signed_market_value": str(self.signed_market_value),
            "unrealized_pnl": str(self.unrealized_pnl),
            "realized_pnl": str(self.realized_pnl),
            "side": _position_side(self.quantity),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class SimulatedTradeInstruction:
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    reason: str | None = None


class BacktestPortfolioLedger:
    """
    Deterministic simulated portfolio ledger for analytical backtests only.

    The ledger consumes runtime node outputs after a workflow step completes and
    simulates fills outside the runtime. It never calls broker clients and never
    mutates runtime nodes.
    """

    def __init__(
        self,
        scenario: BacktestScenario,
    ) -> None:
        self.cash = scenario.initial_cash
        self.positions: dict[str, BacktestLedgerPosition] = {
            position.symbol: BacktestLedgerPosition.from_initial_position(
                position,
            )
            for position in scenario.initial_positions
        }

    def apply_workflow_outputs(
        self,
        *,
        timestamp: datetime,
        scenario: BacktestScenario,
        node_outputs: Mapping[str, object],
    ) -> tuple[BacktestPortfolioSnapshot, tuple[BacktestFill, ...]]:
        self._mark_to_market(
            timestamp=timestamp,
            scenario=scenario,
            node_outputs=node_outputs,
        )
        instruction = _trade_instruction_from_node_outputs(
            timestamp=timestamp,
            scenario=scenario,
            node_outputs=node_outputs,
            portfolio_equity=self._equity(),
        )
        if instruction is None:
            return self.snapshot(
                timestamp=timestamp,
            ), ()

        fill = self._apply_instruction(
            timestamp=timestamp,
            instruction=instruction,
        )
        return self.snapshot(
            timestamp=timestamp,
        ), (fill,)

    def snapshot(
        self,
        *,
        timestamp: datetime,
    ) -> BacktestPortfolioSnapshot:
        market_value = sum(
            (position.market_value for position in self.positions.values()),
            Decimal("0"),
        )
        return BacktestPortfolioSnapshot(
            timestamp=timestamp,
            cash=self.cash,
            equity=self._equity(),
            market_value=market_value,
            positions={
                symbol: position.to_snapshot_payload()
                for symbol, position in self.positions.items()
            },
        )

    def _apply_instruction(
        self,
        *,
        timestamp: datetime,
        instruction: SimulatedTradeInstruction,
    ) -> BacktestFill:
        if instruction.reason is not None:
            return _rejected_fill(
                timestamp=timestamp,
                instruction=instruction,
                reason=instruction.reason,
            )

        if instruction.quantity <= Decimal("0"):
            return _rejected_fill(
                timestamp=timestamp,
                instruction=instruction,
                reason="quantity_must_be_positive",
            )

        if instruction.price <= Decimal("0"):
            return _rejected_fill(
                timestamp=timestamp,
                instruction=instruction,
                reason="price_must_be_positive",
            )

        if instruction.side == "buy":
            return self._buy(
                timestamp=timestamp,
                instruction=instruction,
            )

        if instruction.side == "sell":
            return self._sell(
                timestamp=timestamp,
                instruction=instruction,
            )

        return _rejected_fill(
            timestamp=timestamp,
            instruction=instruction,
            reason=f"unsupported_side:{instruction.side}",
        )

    def _buy(
        self,
        *,
        timestamp: datetime,
        instruction: SimulatedTradeInstruction,
    ) -> BacktestFill:
        cost = instruction.quantity * instruction.price
        if cost > self.cash:
            return _rejected_fill(
                timestamp=timestamp,
                instruction=instruction,
                reason="insufficient_cash",
            )

        existing = self.positions.get(
            instruction.symbol,
        )
        realized_pnl = Decimal("0")
        if existing is None:
            updated = BacktestLedgerPosition(
                symbol=instruction.symbol,
                quantity=instruction.quantity,
                average_price=instruction.price,
                current_price=instruction.price,
            )
        else:
            updated, realized_pnl = _increase_position(
                existing=existing,
                quantity_delta=instruction.quantity,
                price=instruction.price,
            )

        self.cash -= cost
        self.positions[instruction.symbol] = updated
        return _filled_fill(
            timestamp=timestamp,
            instruction=instruction,
            realized_pnl=realized_pnl,
        )

    def _sell(
        self,
        *,
        timestamp: datetime,
        instruction: SimulatedTradeInstruction,
    ) -> BacktestFill:
        proceeds = instruction.quantity * instruction.price
        existing = self.positions.get(
            instruction.symbol,
        )
        realized_pnl = Decimal("0")
        if existing is None:
            updated = BacktestLedgerPosition(
                symbol=instruction.symbol,
                quantity=-instruction.quantity,
                average_price=instruction.price,
                current_price=instruction.price,
            )
        else:
            updated, realized_pnl = _increase_position(
                existing=existing,
                quantity_delta=-instruction.quantity,
                price=instruction.price,
            )

        self.cash += proceeds
        self.positions[instruction.symbol] = updated
        return _filled_fill(
            timestamp=timestamp,
            instruction=instruction,
            realized_pnl=realized_pnl,
        )

    def _mark_to_market(
        self,
        *,
        timestamp: datetime,
        scenario: BacktestScenario,
        node_outputs: Mapping[str, object],
    ) -> None:
        for symbol, position in tuple(self.positions.items()):
            price = _price_for_symbol(
                symbol=symbol,
                timestamp=timestamp,
                scenario=scenario,
                node_outputs=node_outputs,
            )
            if price is None:
                continue
            self.positions[symbol] = BacktestLedgerPosition(
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                current_price=price,
                realized_pnl=position.realized_pnl,
            )

    def _equity(
        self,
    ) -> Decimal:
        return self.cash + sum(
            (position.signed_market_value for position in self.positions.values()),
            Decimal("0"),
        )


def _increase_position(
    *,
    existing: BacktestLedgerPosition,
    quantity_delta: Decimal,
    price: Decimal,
) -> tuple[BacktestLedgerPosition, Decimal]:
    existing_quantity = existing.quantity
    new_quantity = existing_quantity + quantity_delta
    realized_pnl = Decimal("0")

    if new_quantity == Decimal("0"):
        closed_quantity = abs(quantity_delta)
        realized_pnl = _realized_pnl_for_close(
            existing=existing,
            closed_quantity=closed_quantity,
            price=price,
        )
        return BacktestLedgerPosition(
            symbol=existing.symbol,
            quantity=Decimal("0"),
            average_price=price,
            current_price=price,
            realized_pnl=existing.realized_pnl + realized_pnl,
        ), realized_pnl

    if _same_direction(
        existing_quantity,
        quantity_delta,
    ):
        average_price = _weighted_average_price(
            existing_quantity=existing_quantity,
            existing_average=existing.average_price,
            quantity_delta=quantity_delta,
            price=price,
        )
    elif _same_direction(
        new_quantity,
        existing_quantity,
    ):
        closed_quantity = abs(quantity_delta)
        realized_pnl = _realized_pnl_for_close(
            existing=existing,
            closed_quantity=closed_quantity,
            price=price,
        )
        average_price = existing.average_price
    else:
        closed_quantity = abs(existing_quantity)
        realized_pnl = _realized_pnl_for_close(
            existing=existing,
            closed_quantity=closed_quantity,
            price=price,
        )
        average_price = price

    return BacktestLedgerPosition(
        symbol=existing.symbol,
        quantity=new_quantity,
        average_price=average_price,
        current_price=price,
        realized_pnl=existing.realized_pnl + realized_pnl,
    ), realized_pnl


def _trade_instruction_from_node_outputs(
    *,
    timestamp: datetime,
    scenario: BacktestScenario,
    node_outputs: Mapping[str, object],
    portfolio_equity: Decimal,
) -> SimulatedTradeInstruction | None:
    trade_intent = _trade_intent_from_outputs(
        node_outputs,
    )
    if trade_intent is None:
        return None

    symbol = str(
        trade_intent.get(
            "symbol",
            scenario.symbols[0],
        )
    ).upper()
    direction = str(
        trade_intent.get(
            "direction",
            "flat",
        )
    ).lower()
    if direction == "flat":
        return None

    price = _price_for_symbol(
        symbol=symbol,
        timestamp=timestamp,
        scenario=scenario,
        node_outputs=node_outputs,
    )
    if price is None:
        price = _decimal_from_object(
            trade_intent.get(
                "price",
            )
        )
    if price is None:
        return SimulatedTradeInstruction(
            symbol=symbol,
            side=_side_from_direction(
                direction,
            ),
            quantity=Decimal("0"),
            price=Decimal("0"),
            reason="missing_simulated_price",
        )

    position_size = _adjusted_position_size(
        node_outputs=node_outputs,
        trade_intent=trade_intent,
    )
    if position_size <= Decimal("0"):
        return SimulatedTradeInstruction(
            symbol=symbol,
            side=_side_from_direction(
                direction,
            ),
            quantity=Decimal("0"),
            price=price,
            reason="execution_guard_blocked_trade",
        )

    notional = portfolio_equity * position_size
    quantity = notional / price
    return SimulatedTradeInstruction(
        symbol=symbol,
        side=_side_from_direction(
            direction,
        ),
        quantity=quantity,
        price=price,
    )


def _trade_intent_from_outputs(
    node_outputs: Mapping[str, object],
) -> Mapping[str, object] | None:
    trade_packager = _mapping_value(
        node_outputs,
        "trade_packager",
    )
    outputs = _mapping_value(
        trade_packager,
        "outputs",
    )
    features = _mapping_value(
        outputs,
        "features",
    )
    trade_intent = _mapping_value(
        features,
        "trade_intent",
    )
    return trade_intent or None


def _adjusted_position_size(
    *,
    node_outputs: Mapping[str, object],
    trade_intent: Mapping[str, object],
) -> Decimal:
    execution_guard = _execution_guard_from_outputs(
        node_outputs,
    )
    if execution_guard is not None:
        mode = str(
            execution_guard.get(
                "mode",
                "normal",
            )
        )
        if mode == "blocked":
            return Decimal("0")
        adjusted_position_size = _decimal_from_object(
            execution_guard.get(
                "adjusted_position_size",
            )
        )
        if adjusted_position_size is not None:
            return adjusted_position_size

    position_sizing_hint = _decimal_from_object(
        trade_intent.get(
            "position_sizing_hint",
        )
    )
    return position_sizing_hint or Decimal("0")


def _execution_guard_from_outputs(
    node_outputs: Mapping[str, object],
) -> Mapping[str, object] | None:
    for node_name in (
        "execution_risk_guard",
        "risk_guard",
    ):
        guard_node = _mapping_value(
            node_outputs,
            node_name,
        )
        outputs = _mapping_value(
            guard_node,
            "outputs",
        )
        features = _mapping_value(
            outputs,
            "features",
        )
        execution_guard = _mapping_value(
            features,
            "execution_guard",
        )
        if execution_guard is not None:
            return execution_guard

    return None


def _price_for_symbol(
    *,
    symbol: str,
    timestamp: datetime,
    scenario: BacktestScenario,
    node_outputs: Mapping[str, object],
) -> Decimal | None:
    parameter_price = _price_from_scenario_parameters(
        symbol=symbol,
        timestamp=timestamp,
        scenario=scenario,
    )
    if parameter_price is not None:
        return parameter_price

    return _price_from_technical_output(
        symbol=symbol,
        node_outputs=node_outputs,
    )


def _price_from_scenario_parameters(
    *,
    symbol: str,
    timestamp: datetime,
    scenario: BacktestScenario,
) -> Decimal | None:
    prices = scenario.parameters.get(
        "prices",
    )
    if not isinstance(prices, Mapping):
        return None

    symbol_prices = (
        prices.get(
            symbol,
        )
        or prices.get(
            symbol.upper(),
        )
        or prices.get(
            symbol.lower(),
        )
    )
    if isinstance(symbol_prices, Mapping):
        return _decimal_from_object(
            symbol_prices.get(
                timestamp.date().isoformat(),
            )
        )

    return _decimal_from_object(
        symbol_prices,
    )


def _price_from_technical_output(
    *,
    symbol: str,
    node_outputs: Mapping[str, object],
) -> Decimal | None:
    technical_agent = _mapping_value(
        node_outputs,
        "technical_agent",
    )
    outputs = _mapping_value(
        technical_agent,
        "outputs",
    )
    features = _mapping_value(
        outputs,
        "features",
    )
    if features is None:
        return None

    output_symbol = str(
        features.get(
            "symbol",
            symbol,
        )
    ).upper()
    if output_symbol != symbol.upper():
        return None

    snapshot = _mapping_value(
        features,
        "snapshot",
    )
    if snapshot is None:
        return None

    for key in (
        "close",
        "price",
        "adj_close",
    ):
        price = _decimal_from_object(
            snapshot.get(
                key,
            )
        )
        if price is not None:
            return price

    return None


def _mapping_value(
    mapping: Mapping[str, object] | None,
    key: str,
) -> Mapping[str, object] | None:
    if mapping is None:
        return None

    value = mapping.get(
        key,
    )
    if isinstance(value, Mapping):
        return value

    return None


def _decimal_from_object(
    value: object,
) -> Decimal | None:
    if value is None:
        return None

    try:
        return Decimal(
            str(value),
        )
    except (InvalidOperation, ValueError):
        return None


def _side_from_direction(
    direction: str,
) -> str:
    if direction == "long":
        return "buy"

    if direction == "short":
        return "sell"

    return direction


def _same_direction(
    first: Decimal,
    second: Decimal,
) -> bool:
    return (first >= Decimal("0") and second >= Decimal("0")) or (
        first <= Decimal("0") and second <= Decimal("0")
    )


def _weighted_average_price(
    *,
    existing_quantity: Decimal,
    existing_average: Decimal,
    quantity_delta: Decimal,
    price: Decimal,
) -> Decimal:
    total_quantity = abs(existing_quantity) + abs(quantity_delta)
    if total_quantity == Decimal("0"):
        return price

    return (
        (abs(existing_quantity) * existing_average) + (abs(quantity_delta) * price)
    ) / total_quantity


def _realized_pnl_for_close(
    *,
    existing: BacktestLedgerPosition,
    closed_quantity: Decimal,
    price: Decimal,
) -> Decimal:
    if existing.quantity < Decimal("0"):
        return (existing.average_price - price) * closed_quantity

    return (price - existing.average_price) * closed_quantity


def _filled_fill(
    *,
    timestamp: datetime,
    instruction: SimulatedTradeInstruction,
    realized_pnl: Decimal,
) -> BacktestFill:
    return BacktestFill(
        timestamp=timestamp,
        symbol=instruction.symbol,
        side=instruction.side,
        quantity=instruction.quantity,
        price=instruction.price,
        status="filled",
        reason=f"realized_pnl:{realized_pnl}",
        realized_pnl=realized_pnl,
    )


def _rejected_fill(
    *,
    timestamp: datetime,
    instruction: SimulatedTradeInstruction,
    reason: str,
) -> BacktestFill:
    return BacktestFill(
        timestamp=timestamp,
        symbol=instruction.symbol,
        side=instruction.side,
        quantity=instruction.quantity,
        price=instruction.price,
        status="rejected",
        reason=reason,
    )


def _position_side(
    quantity: Decimal,
) -> str:
    if quantity > Decimal("0"):
        return "long"

    if quantity < Decimal("0"):
        return "short"

    return "flat"
