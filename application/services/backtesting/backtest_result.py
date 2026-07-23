from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from application.services.backtesting.backtest_request import (
    BacktestExpectationType,
    BacktestScenario,
)


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestPortfolioSnapshot:
    """
    Portfolio state captured at a deterministic backtest timestamp.
    """

    timestamp: datetime
    cash: Decimal
    equity: Decimal
    market_value: Decimal
    positions: Mapping[str, object] = field(default_factory=dict)

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "cash": str(self.cash),
            "equity": str(self.equity),
            "market_value": str(self.market_value),
            "positions": deepcopy(dict(self.positions)),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestFill:
    """
    Simulated fill record for analytical backtesting only.
    """

    timestamp: datetime
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    status: str
    reason: str | None = None
    realized_pnl: Decimal = Decimal("0")

    def to_dict(
        self,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "status": self.status,
            "realized_pnl": str(self.realized_pnl),
        }

        if self.reason is not None:
            payload["reason"] = self.reason

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestMetrics:
    """
    Canonical backtest metrics payload.
    """

    total_return: Decimal = Decimal("0")
    annualized_return: Decimal = Decimal("0")
    volatility: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    sharpe_ratio: Decimal = Decimal("0")
    sortino_ratio: Decimal = Decimal("0")
    win_rate: Decimal = Decimal("0")
    profit_factor: Decimal = Decimal("0")
    exposure: Decimal = Decimal("0")
    turnover: Decimal = Decimal("0")
    benchmark_relative_return: Decimal = Decimal("0")

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "total_return": str(self.total_return),
            "annualized_return": str(self.annualized_return),
            "volatility": str(self.volatility),
            "max_drawdown": str(self.max_drawdown),
            "sharpe_ratio": str(self.sharpe_ratio),
            "sortino_ratio": str(self.sortino_ratio),
            "win_rate": str(self.win_rate),
            "profit_factor": str(self.profit_factor),
            "exposure": str(self.exposure),
            "turnover": str(self.turnover),
            "benchmark_relative_return": str(self.benchmark_relative_return),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestStepResult:
    """
    Result of one workflow execution at one deterministic simulation timestamp.
    """

    timestamp: datetime
    workflow_run_id: str
    success: bool
    node_outputs: Mapping[str, object]
    portfolio_snapshot: BacktestPortfolioSnapshot
    simulated_fills: tuple[BacktestFill, ...] = ()

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "workflow_run_id": self.workflow_run_id,
            "success": self.success,
            "node_outputs": deepcopy(dict(self.node_outputs)),
            "portfolio_snapshot": self.portfolio_snapshot.to_dict(),
            "simulated_fills": [fill.to_dict() for fill in self.simulated_fills],
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestOutcomeVerification:
    """Result of one deterministic scenario expectation."""

    target: str
    expectation_type: BacktestExpectationType
    expected: object
    actual: object
    passed: bool
    tolerance: Decimal | None = None
    detail: str | None = None

    def to_dict(
        self,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "target": self.target,
            "expectation_type": self.expectation_type,
            "expected": _boundary_value(self.expected),
            "actual": _boundary_value(self.actual),
            "passed": self.passed,
        }
        if self.tolerance is not None:
            payload["tolerance"] = str(self.tolerance)
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestResult:
    """
    Backtest application-service result.
    """

    backtest_run_id: str
    scenario: BacktestScenario
    success: bool
    started_at: datetime
    completed_at: datetime
    status: str = "validated"
    steps: tuple[BacktestStepResult, ...] = ()
    metrics: BacktestMetrics = field(default_factory=BacktestMetrics)
    artifacts: Mapping[str, str] = field(default_factory=dict)
    verifications: tuple[BacktestOutcomeVerification, ...] = ()
    metadata: Mapping[str, object] = field(default_factory=dict)

    @classmethod
    def validated(
        cls,
        *,
        backtest_run_id: str,
        scenario: BacktestScenario,
        timestamp: datetime | None = None,
    ) -> BacktestResult:
        now = timestamp or datetime.now(UTC)
        return cls(
            backtest_run_id=backtest_run_id,
            scenario=scenario,
            success=True,
            started_at=now,
            completed_at=now,
            status="validated",
            metadata={
                "execution_phase": "boundary_and_contracts",
            },
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "backtest_run_id": self.backtest_run_id,
            "scenario": self.scenario.to_dict(),
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "metrics": self.metrics.to_dict(),
            "artifacts": dict(self.artifacts),
            "verifications": [
                verification.to_dict() for verification in self.verifications
            ],
            "metadata": deepcopy(dict(self.metadata)),
        }


def _boundary_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _boundary_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_boundary_value(item) for item in value]
    if isinstance(value, list):
        return [_boundary_value(item) for item in value]
    return deepcopy(value)
