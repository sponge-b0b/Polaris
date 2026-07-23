from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from application.persistence.backtesting import (
    BacktestPersistenceService,
    BacktestRunPersistenceFilters,
)
from application.services.backtesting import (
    BacktestApplicationService,
    BacktestResult,
    BacktestRunRequest,
    load_backtest_scenario,
)
from application.services.base import ServiceRequest, ServiceRunner
from core.bootstrap.di_providers import application_request_scope
from core.storage.persistence.backtesting import (
    BacktestArtifactRecord,
    BacktestPersistenceBundle,
    BacktestPersistenceResult,
    BacktestRunRecord,
)
from interfaces.cli.bootstrap.container import cli_runtime_scope


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestRunCommandRequest:
    """
    CLI command request for runtime-native backtest execution.
    """

    scenario_path: Path
    output_format: str = "console"
    persist_results: bool = True
    checkpoint_workflow_runs: bool = True
    plugin_dirs: tuple[Path, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestListCommandRequest:
    """
    CLI command request for listing persisted backtest runs.
    """

    scenario_id: str | None = None
    workflow_name: str | None = None
    status: str | None = None
    limit: int = 20


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestShowCommandRequest:
    """
    CLI command request for retrieving one persisted backtest run.
    """

    backtest_run_id: str


@dataclass(
    frozen=True,
    slots=True,
)
class BacktestReportCommandRequest:
    """
    CLI command request for rendering one persisted backtest report artifact.
    """

    backtest_run_id: str
    output_format: str = "markdown"


class BacktestCommandService:
    """
    Thin CLI service that delegates execution to BacktestApplicationService.
    """

    async def run_backtest(
        self,
        request: BacktestRunCommandRequest,
    ) -> BacktestResult:
        scenario = load_backtest_scenario(
            request.scenario_path,
        )
        async with cli_runtime_scope(
            plugin_dirs=request.plugin_dirs,
            autoload_plugins=bool(request.plugin_dirs),
            provider_profile=scenario.provider_profile,
        ) as scope:
            service = scope.get(BacktestApplicationService)
            service_runner = scope.get(ServiceRunner)
            result = await service_runner.run(
                service,
                ServiceRequest(
                    payload=BacktestRunRequest(
                        scenario=scenario,
                        persist_results=request.persist_results,
                        checkpoint_workflow_runs=request.checkpoint_workflow_runs,
                        output_format=_validated_run_output_format(
                            request.output_format
                        ),
                    ),
                    metadata={
                        "source": "polaris_cli",
                        "command": "backtest run",
                        "scenario_path": str(request.scenario_path),
                    },
                ),
            )
        result.raise_if_failed()
        if result.result is None:
            raise RuntimeError("Backtest service returned no result.")

        backtest_result = result.result
        if request.persist_results:
            try:
                persistence_result = await _persist_backtest_result(
                    backtest_result,
                )
            except Exception as exc:
                backtest_result = _with_persistence_metadata(
                    backtest_result,
                    status="failed",
                    error=str(exc),
                )
            else:
                if persistence_result.success:
                    backtest_result = _with_persistence_metadata(
                        backtest_result,
                        status="succeeded",
                        records_persisted=persistence_result.records_persisted,
                    )
                else:
                    backtest_result = _with_persistence_metadata(
                        backtest_result,
                        status="failed",
                        error=persistence_result.error,
                    )

        return backtest_result

    async def list_backtests(
        self,
        request: BacktestListCommandRequest,
    ) -> tuple[BacktestRunRecord, ...]:
        return await _list_persisted_backtests(
            BacktestRunPersistenceFilters(
                scenario_id=request.scenario_id,
                workflow_name=request.workflow_name,
                status=request.status,
                limit=request.limit,
            )
        )

    async def show_backtest(
        self,
        request: BacktestShowCommandRequest,
    ) -> BacktestPersistenceBundle:
        bundle = await _get_persisted_backtest_bundle(
            request.backtest_run_id,
        )
        if bundle is None:
            raise ValueError(f"Backtest run not found: {request.backtest_run_id}")
        return bundle

    async def render_backtest_report(
        self,
        request: BacktestReportCommandRequest,
    ) -> str:
        bundle = await self.show_backtest(
            BacktestShowCommandRequest(
                backtest_run_id=request.backtest_run_id,
            )
        )
        artifact = _find_artifact(
            bundle.artifacts,
            request.output_format,
        )
        if artifact is not None:
            return artifact.content

        if request.output_format == "console":
            return _render_persisted_console_summary(
                bundle,
            )

        raise ValueError(
            f"Persisted backtest artifact not found for format: {request.output_format}"
        )


def _with_persistence_metadata(
    result: BacktestResult,
    *,
    status: str,
    error: str | None = None,
    records_persisted: int | None = None,
) -> BacktestResult:
    metadata = dict(result.metadata)
    metadata["persistence_status"] = status
    if error is not None:
        metadata["persistence_error"] = error
    if records_persisted is not None:
        metadata["records_persisted"] = records_persisted

    return BacktestResult(
        backtest_run_id=result.backtest_run_id,
        scenario=result.scenario,
        success=result.success,
        started_at=result.started_at,
        completed_at=result.completed_at,
        status=result.status,
        steps=result.steps,
        metrics=result.metrics,
        artifacts=result.artifacts,
        verifications=result.verifications,
        metadata=metadata,
    )


async def _persist_backtest_result(
    result: BacktestResult,
) -> BacktestPersistenceResult:
    async with application_request_scope() as request_container:
        service = await request_container.get(BacktestPersistenceService)
        return await service.persist_result(
            result,
        )


async def _get_persisted_backtest_bundle(
    backtest_run_id: str,
) -> BacktestPersistenceBundle | None:
    async with application_request_scope() as request_container:
        service = await request_container.get(BacktestPersistenceService)
        return await service.get_bundle(
            backtest_run_id,
        )


async def _list_persisted_backtests(
    filters: BacktestRunPersistenceFilters,
) -> tuple[BacktestRunRecord, ...]:
    async with application_request_scope() as request_container:
        service = await request_container.get(BacktestPersistenceService)
        return tuple(
            await service.list_runs(
                filters,
            )
        )


def _validated_run_output_format(
    value: str,
) -> Literal["console", "json", "markdown"]:
    if value not in {"console", "json", "markdown"}:
        raise ValueError("backtest format must be one of: console, json, markdown")
    return cast(
        Literal["console", "json", "markdown"],
        value,
    )


def _find_artifact(
    artifacts: tuple[BacktestArtifactRecord, ...],
    artifact_format: str,
) -> BacktestArtifactRecord | None:
    for artifact in artifacts:
        if artifact.artifact_format == artifact_format:
            return artifact
    return None


def _render_persisted_console_summary(
    bundle: BacktestPersistenceBundle,
) -> str:
    filled_count = _fill_count(
        bundle,
        "filled",
    )
    rejected_count = _fill_count(
        bundle,
        "rejected",
    )
    return "\n".join(
        (
            f"Backtest: {bundle.scenario.name}",
            f"Run ID: {bundle.run.backtest_run_id}",
            f"Workflow: {bundle.run.workflow_name}",
            f"Status: {bundle.run.status}",
            f"Success: {bundle.run.success}",
            f"Steps: {len(bundle.steps)}",
            f"Filled / Rejected Fills: {filled_count} / {rejected_count}",
        )
    )


def _fill_count(
    bundle: BacktestPersistenceBundle,
    status: str,
) -> int:
    return sum(1 for fill in bundle.fills if fill.status == status)
