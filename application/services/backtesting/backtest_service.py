from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from collections.abc import Mapping

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timezone
from typing import Any
from typing import Protocol
from uuid import uuid4

from application.services.backtesting.backtest_request import BacktestRunRequest
from application.services.backtesting.backtest_request import BacktestScenario
from application.services.backtesting.backtest_request import (
    BacktestWorkflowStepRequest,
)
from application.services.backtesting.backtest_metrics import compute_backtest_metrics
from application.services.backtesting.backtest_reporting import build_backtest_artifacts
from application.services.backtesting.backtest_result import BacktestResult
from application.services.backtesting.backtest_result import BacktestStepResult
from application.services.backtesting.backtest_verification import (
    verify_backtest_outcomes,
)
from application.services.backtesting.simulated_portfolio_ledger import (
    BacktestPortfolioLedger,
)
from application.services.base import ServiceRequest
from application.services.base import ServiceResult
from application.services.base.application_service import ApplicationService
from application.services.base.application_service import ValidatingApplicationService


def _system_clock() -> datetime:
    return datetime.now(timezone.utc)


def _new_backtest_run_id() -> str:
    return f"backtest-{uuid4().hex}"


class BacktestWorkflowFacade(Protocol):
    """
    Minimal WorkflowFacade contract required by backtesting orchestration.
    """

    async def run_workflow(
        self,
        workflow_name: str,
        execution_id: str | None = None,
        mode: str = "live",
        workflow_inputs: Mapping[str, Any] | None = None,
        simulation_time: datetime | None = None,
        archive_on_completion: bool = True,
        checkpoint_on_completion: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Any: ...


class BacktestApplicationService(
    ApplicationService[BacktestRunRequest, BacktestResult],
    ValidatingApplicationService[BacktestRunRequest],
):
    """
    Canonical application boundary for platform backtesting.

    Backtest execution is runtime-native: each simulation timestamp delegates to
    WorkflowFacade.run_workflow with mode="backtest" and simulation_time set.
    """

    service_name = "backtest_application_service"

    def __init__(
        self,
        workflow_facade: BacktestWorkflowFacade | None = None,
        clock: Callable[[], datetime] = _system_clock,
        run_id_factory: Callable[[], str] = _new_backtest_run_id,
    ) -> None:
        self.workflow_facade = workflow_facade
        self.clock = clock
        self.run_id_factory = run_id_factory

    async def run(
        self,
        request: ServiceRequest[BacktestRunRequest],
    ) -> ServiceResult[BacktestResult]:
        result = await self._execute(
            request.payload,
        )

        return ServiceResult.ok(
            request_id=request.request_id,
            request_name=request.request_name,
            result=result,
            metadata={
                "service_name": self.service_name,
                "provider_profile": request.payload.scenario.provider_profile,
                "mode": "backtest",
                "status": result.status,
            },
        )

    async def validate_request(
        self,
        request: ServiceRequest[BacktestRunRequest],
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not isinstance(request.payload, BacktestRunRequest):
            errors.append(
                f"Unsupported service request: {request.request_name}",
            )
            return tuple(errors)

        errors.extend(
            request.payload.validate(),
        )

        return tuple(errors)

    async def _execute(
        self,
        request: BacktestRunRequest,
    ) -> BacktestResult:
        backtest_run_id = self.run_id_factory()

        if self.workflow_facade is None:
            return BacktestResult.validated(
                backtest_run_id=backtest_run_id,
                scenario=request.scenario,
                timestamp=_utc_timestamp(self.clock()),
            )

        return await self._execute_runtime_backtest(
            backtest_run_id=backtest_run_id,
            request=request,
        )

    async def _execute_runtime_backtest(
        self,
        *,
        backtest_run_id: str,
        request: BacktestRunRequest,
    ) -> BacktestResult:
        if self.workflow_facade is None:
            raise RuntimeError("WorkflowFacade is required for backtest execution.")

        started_at = _utc_timestamp(self.clock())
        steps: list[BacktestStepResult] = []
        success = True
        portfolio_ledger = BacktestPortfolioLedger(
            request.scenario,
        )

        for step_index, simulation_time in enumerate(
            _simulation_timeline(request.scenario),
        ):
            step_request = BacktestWorkflowStepRequest(
                backtest_run_id=backtest_run_id,
                scenario=request.scenario,
                step_index=step_index,
                simulation_time=simulation_time,
                persist_results=request.persist_results,
                checkpoint_workflow_runs=request.checkpoint_workflow_runs,
            )
            workflow_result = await self._run_workflow_step(step_request)
            step_result = _step_result_from_workflow_result(
                scenario=request.scenario,
                simulation_time=simulation_time,
                workflow_result=workflow_result,
                portfolio_ledger=portfolio_ledger,
            )
            steps.append(step_result)
            success = success and step_result.success

        completed_at = _utc_timestamp(self.clock())
        step_results = tuple(steps)
        metrics = compute_backtest_metrics(
            scenario=request.scenario,
            steps=step_results,
        )
        verifications = verify_backtest_outcomes(
            scenario=request.scenario,
            steps=step_results,
            metrics=metrics,
        )
        success = success and all(verification.passed for verification in verifications)
        status = "succeeded" if success else "failed"
        artifacts = build_backtest_artifacts(
            backtest_run_id=backtest_run_id,
            scenario=request.scenario,
            success=success,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            steps=step_results,
            metrics=metrics,
            verifications=verifications,
        )
        return BacktestResult(
            backtest_run_id=backtest_run_id,
            scenario=request.scenario,
            success=success,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            steps=step_results,
            metrics=metrics,
            artifacts=artifacts,
            verifications=verifications,
            metadata={
                "execution_phase": "metrics_and_reports",
                "step_count": len(step_results),
                "simulated_fill_count": sum(
                    len(step.simulated_fills) for step in step_results
                ),
                "artifact_formats": tuple(artifacts),
                "verification_count": len(verifications),
                "verification_failure_count": sum(
                    not verification.passed for verification in verifications
                ),
            },
        )

    async def _run_workflow_step(
        self,
        request: BacktestWorkflowStepRequest,
    ) -> Any:
        if self.workflow_facade is None:
            raise RuntimeError("WorkflowFacade is required for backtest execution.")
        return await self.workflow_facade.run_workflow(
            workflow_name=request.workflow_name,
            execution_id=request.execution_id,
            mode="backtest",
            workflow_inputs=request.workflow_inputs(),
            simulation_time=request.simulation_time,
            archive_on_completion=request.persist_results,
            checkpoint_on_completion=request.checkpoint_workflow_runs,
            metadata=request.metadata(),
        )


def _utc_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Backtest clock must return a timezone-aware datetime.")
    return value.astimezone(timezone.utc)


def _simulation_timeline(
    scenario: BacktestScenario,
) -> tuple[datetime, ...]:
    return tuple(
        datetime.combine(
            current_date,
            time.min,
            tzinfo=timezone.utc,
        )
        for current_date in _date_range(
            scenario.start_date,
            scenario.end_date,
        )
    )


def _date_range(
    start_date: date,
    end_date: date,
) -> tuple[date, ...]:
    days = (end_date - start_date).days
    return tuple(
        date.fromordinal(start_date.toordinal() + offset) for offset in range(days + 1)
    )


def _step_result_from_workflow_result(
    *,
    scenario: BacktestScenario,
    simulation_time: datetime,
    workflow_result: Any,
    portfolio_ledger: BacktestPortfolioLedger,
) -> BacktestStepResult:
    execution_result = workflow_result.execution_result
    final_context = execution_result.final_context
    runtime_node_outputs = dict(final_context.node_outputs)
    portfolio_snapshot, simulated_fills = portfolio_ledger.apply_workflow_outputs(
        timestamp=simulation_time,
        scenario=scenario,
        node_outputs=runtime_node_outputs,
    )
    node_outputs = _deterministic_node_outputs(runtime_node_outputs)

    return BacktestStepResult(
        timestamp=simulation_time,
        workflow_run_id=str(workflow_result.execution_id),
        success=bool(workflow_result.success),
        node_outputs=node_outputs,
        portfolio_snapshot=portfolio_snapshot,
        simulated_fills=simulated_fills,
    )


def _deterministic_node_outputs(
    node_outputs: Mapping[str, object],
) -> dict[str, object]:
    """Project runtime outputs without volatile execution timing metadata."""

    deterministic: dict[str, object] = {}
    for node_name in sorted(node_outputs, key=str):
        node_output = node_outputs[node_name]
        if not isinstance(node_output, Mapping):
            deterministic[str(node_name)] = deepcopy(node_output)
            continue
        deterministic[str(node_name)] = {
            str(key): deepcopy(value)
            for key, value in node_output.items()
            if key != "execution_metadata"
        }
    return deterministic
