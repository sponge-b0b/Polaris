from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Literal
from typing import Mapping


OutputFormat = Literal["console", "json", "markdown"]
BacktestExpectationType = Literal[
    "equals",
    "approx",
    "min",
    "max",
    "between",
    "contains",
]

_ALLOWED_MISSING_DATA_POLICIES = frozenset({"fail_fast", "forward_fill"})


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestInitialPosition:
    """
    Starting position for a deterministic backtest scenario.
    """

    symbol: str
    quantity: Decimal
    average_price: Decimal

    def validate(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not self.symbol.strip():
            errors.append("initial position symbol is required.")

        if self.quantity < Decimal("0"):
            errors.append("initial position quantity cannot be negative.")

        if self.average_price <= Decimal("0"):
            errors.append("initial position average_price must be greater than zero.")

        return tuple(errors)

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "quantity": str(self.quantity),
            "average_price": str(self.average_price),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestExpectedOutcome:
    """
    Deterministic assertion for verifying workflow outputs, risk assessments,
    or recommendation calculations against known input data.
    """

    target: str
    expectation_type: BacktestExpectationType
    expected: object
    tolerance: Decimal | None = None

    def validate(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not self.target.strip():
            errors.append("expected outcome target is required.")

        if self.expectation_type == "approx" and self.tolerance is None:
            errors.append("approx expected outcomes require tolerance.")

        if self.tolerance is not None and self.tolerance < Decimal("0"):
            errors.append("expected outcome tolerance cannot be negative.")

        return tuple(errors)

    def to_dict(
        self,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "target": self.target,
            "expectation_type": self.expectation_type,
            "expected": deepcopy(self.expected),
        }

        if self.tolerance is not None:
            payload["tolerance"] = str(self.tolerance)

        return payload


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestScenario:
    """
    Runtime-agnostic backtest scenario definition.
    """

    scenario_id: str
    name: str
    workflow_name: str
    start_date: date
    end_date: date
    symbols: tuple[str, ...]
    benchmark_symbol: str
    initial_cash: Decimal
    provider_profile: str = "backtest_synthetic"
    initial_positions: tuple[BacktestInitialPosition, ...] = ()
    parameters: Mapping[str, object] = field(default_factory=dict)
    expected_outcomes: tuple[BacktestExpectedOutcome, ...] = ()

    def validate(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not self.scenario_id.strip():
            errors.append("scenario_id is required.")

        if not self.name.strip():
            errors.append("name is required.")

        if not self.workflow_name.strip():
            errors.append("workflow_name is required.")

        if self.start_date > self.end_date:
            errors.append("start_date must be on or before end_date.")

        if not self.symbols:
            errors.append("at least one symbol is required.")

        if any(not symbol.strip() for symbol in self.symbols):
            errors.append("symbols cannot contain blank values.")

        if not self.benchmark_symbol.strip():
            errors.append("benchmark_symbol is required.")

        if self.initial_cash < Decimal("0"):
            errors.append("initial_cash cannot be negative.")

        if not self.provider_profile.strip():
            errors.append("provider_profile is required.")

        missing_data_policy = self.parameters.get(
            "missing_data_policy",
        )
        if (
            missing_data_policy is not None
            and missing_data_policy not in _ALLOWED_MISSING_DATA_POLICIES
        ):
            supported_policies = ", ".join(
                sorted(_ALLOWED_MISSING_DATA_POLICIES),
            )
            errors.append(
                f"parameters.missing_data_policy must be one of: {supported_policies}."
            )

        for position in self.initial_positions:
            errors.extend(position.validate())

        for expected_outcome in self.expected_outcomes:
            errors.extend(expected_outcome.validate())

        return tuple(errors)

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "workflow_name": self.workflow_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "symbols": list(self.symbols),
            "benchmark_symbol": self.benchmark_symbol,
            "initial_cash": str(self.initial_cash),
            "provider_profile": self.provider_profile,
            "initial_positions": [
                position.to_dict() for position in self.initial_positions
            ],
            "parameters": deepcopy(dict(self.parameters)),
            "expected_outcomes": [
                expected_outcome.to_dict()
                for expected_outcome in self.expected_outcomes
            ],
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestRunRequest:
    """
    Application-service payload for preparing or executing a backtest run.
    """

    scenario: BacktestScenario
    persist_results: bool = True
    checkpoint_workflow_runs: bool = True
    output_format: OutputFormat = "console"

    def validate(
        self,
    ) -> tuple[str, ...]:
        return self.scenario.validate()

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "scenario": self.scenario.to_dict(),
            "persist_results": self.persist_results,
            "checkpoint_workflow_runs": self.checkpoint_workflow_runs,
            "output_format": self.output_format,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestWorkflowStepRequest:
    """Immutable invocation contract for one runtime-native backtest step."""

    backtest_run_id: str
    scenario: BacktestScenario
    step_index: int
    simulation_time: datetime
    persist_results: bool
    checkpoint_workflow_runs: bool

    @property
    def workflow_name(self) -> str:
        return self.scenario.workflow_name

    @property
    def execution_id(self) -> str:
        return f"{self.backtest_run_id}-step-{self.step_index:06d}"

    def workflow_inputs(self) -> dict[str, object]:
        workflow_inputs = deepcopy(dict(self.scenario.parameters))
        workflow_inputs.update(
            {
                "symbol": self.scenario.symbols[0],
                "symbols": list(self.scenario.symbols),
                "benchmark_symbol": self.scenario.benchmark_symbol,
                "backtest": {
                    "backtest_run_id": self.backtest_run_id,
                    "scenario_id": self.scenario.scenario_id,
                    "provider_profile": self.scenario.provider_profile,
                    "symbols": list(self.scenario.symbols),
                    "benchmark_symbol": self.scenario.benchmark_symbol,
                    "parameters": deepcopy(dict(self.scenario.parameters)),
                    "expected_outcomes": [
                        expected_outcome.to_dict()
                        for expected_outcome in self.scenario.expected_outcomes
                    ],
                    "step_index": self.step_index,
                    "simulation_time": self.simulation_time.isoformat(),
                },
            }
        )
        return workflow_inputs

    def metadata(self) -> dict[str, object]:
        return {
            "backtest_run_id": self.backtest_run_id,
            "scenario_id": self.scenario.scenario_id,
            "provider_profile": self.scenario.provider_profile,
            "step_index": self.step_index,
            "simulation_time": self.simulation_time.isoformat(),
        }
