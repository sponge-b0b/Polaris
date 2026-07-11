from __future__ import annotations

import typer

from application.projections.workflow_outputs import CompletedRunProjectionSummary
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionOperationsService,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionReconciliationRequest,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionReconciliationResult,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRequest
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionRetryRequest,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRetryResult
from application.projections.workflow_outputs import WorkflowOutputProjectionStatus
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionStatusRequest,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionStatusResult,
)
from core.bootstrap.di_providers import application_request_scope
from core.storage.persistence.projections import MissingProjectionRunRecord
from core.storage.persistence.projections import WorkflowOutputProjectionJobRecord
from contextlib import asynccontextmanager
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import AsyncIterator

from core.workflow.models.destructive_operation_confirmation import (
    DestructiveOperationConfirmation,
)
from core.workflow.models.destructive_operation_confirmation import (
    DestructiveWorkflowOperation,
)
from interfaces.cli.bootstrap.container import cli_runtime_scope
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.services.async_runner import run_cli_async

completed_runs_app = typer.Typer(
    help="Manage completed run archive (audit/history/RAG).",
    no_args_is_help=True,
)

OutputFormat = Annotated[
    str,
    typer.Option(
        "--format",
        "-f",
        help="Output format: console or json.",
    ),
]

PluginDirs = Annotated[
    list[Path],
    typer.Option(
        "--plugin-dir",
        help="Plugin directory to autoload before running commands.",
    ),
]


@completed_runs_app.command("list")
def archive_list(
    workflow_name: Annotated[
        str,
        typer.Argument(
            help="Workflow name to list archived runs for.",
        ),
    ],
    output_format: OutputFormat = "console",
    plugin_dirs: PluginDirs = [],
) -> None:
    """
    List all archived execution IDs for a workflow.
    """
    execution_ids = run_cli_async(
        _list_completed_runs(
            workflow_name,
            plugin_dirs=tuple(plugin_dirs),
        )
    )

    if output_format == "json":
        typer.echo(format_json(execution_ids))
        return

    if output_format != "console":
        raise typer.BadParameter("archive list supports console or json output")

    if not execution_ids:
        typer.echo(f"No archived runs found for workflow: {workflow_name}")
        return

    typer.echo(f"Archived runs for '{workflow_name}':")
    for exec_id in execution_ids:
        typer.echo(f"  {exec_id}")


@completed_runs_app.command("show")
def archive_show(
    workflow_name: Annotated[
        str,
        typer.Argument(
            help="Workflow name.",
        ),
    ],
    execution_id: Annotated[
        str,
        typer.Argument(
            help="Execution ID to load.",
        ),
    ],
    output_format: OutputFormat = "json",
    plugin_dirs: PluginDirs = [],
) -> None:
    """
    Load and display a completed run from archive.
    """
    context = run_cli_async(
        _load_completed_run(
            workflow_name,
            execution_id,
            plugin_dirs=tuple(plugin_dirs),
        )
    )

    if context is None:
        typer.echo(
            f"No archived run found for '{workflow_name}' execution '{execution_id}'"
        )
        raise typer.Exit(code=1)

    if output_format == "json":
        typer.echo(format_json(context.to_dict()))
    elif output_format == "console":
        success = not bool(context.errors)
        status = "succeeded" if success else "failed"

        typer.echo(f"Workflow: {context.workflow_id}")
        typer.echo(f"Runtime ID: {context.runtime_id}")
        typer.echo(f"Execution ID: {context.execution_id}")
        typer.echo(f"Mode: {context.mode}")
        typer.echo(f"Success: {success}")
        typer.echo(f"Status: {status}")
        typer.echo(f"Context Version: {context.context_version}")
        typer.echo(f"Node Outputs: {len(context.node_outputs)}")
        typer.echo(f"Artifacts: {len(context.artifact_refs)}")
        typer.echo(f"Errors: {len(context.errors)}")
    else:
        raise typer.BadParameter("archive show supports console or json output")


@completed_runs_app.command("delete")
def archive_delete(
    workflow_name: Annotated[
        str,
        typer.Argument(
            help="Workflow name.",
        ),
    ],
    execution_id: Annotated[
        str,
        typer.Argument(
            help="Execution ID to delete.",
        ),
    ],
    plugin_dirs: PluginDirs = [],
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Confirm deletion without prompt.",
        ),
    ] = False,
) -> None:
    """
    Delete a specific archived run.
    """
    if not confirm:
        typer.confirm(
            f"Delete archived run '{execution_id}' for workflow '{workflow_name}'?",
            abort=True,
        )

    run_cli_async(
        _delete_completed_run(
            workflow_name,
            execution_id,
            plugin_dirs=tuple(plugin_dirs),
        )
    )
    typer.echo(f"Deleted archived run '{execution_id}' for workflow '{workflow_name}'")


@completed_runs_app.command("cleanup")
def archive_cleanup(
    max_age_days: Annotated[
        int | None,
        typer.Option(
            "--max-age-days",
            help="Delete runs older than this many days.",
        ),
    ] = None,
    max_count: Annotated[
        int | None,
        typer.Option(
            "--max-count",
            help="Keep only the most recent N runs per workflow.",
        ),
    ] = None,
    plugin_dirs: PluginDirs = [],
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Confirm cleanup without prompt.",
        ),
    ] = False,
) -> None:
    """
    Clean up archived runs based on retention policy.
    """
    deleted = run_cli_async(
        _cleanup_completed_runs(
            max_age_days=max_age_days,
            max_count=max_count,
            plugin_dirs=tuple(plugin_dirs),
            confirm=confirm,
        )
    )
    typer.echo(f"Deleted {deleted} archived runs")


@completed_runs_app.command("projection-status")
def projection_status(
    workflow_name: Annotated[
        str | None,
        typer.Option(
            "--workflow",
            help="Filter projection jobs by workflow name.",
        ),
    ] = None,
    execution_id: Annotated[
        str | None,
        typer.Option(
            "--execution-id",
            help="Filter projection jobs by execution ID.",
        ),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option(
            "--run-id",
            help="Filter projection jobs by completed-run ID.",
        ),
    ] = None,
    projector_name: Annotated[
        str | None,
        typer.Option(
            "--projector",
            help="Filter projection jobs by projector name.",
        ),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        typer.Option(
            "--status",
            help="Projection status to include; repeat for multiple statuses.",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="Maximum projection jobs to return.",
        ),
    ] = 50,
    output_format: OutputFormat = "console",
) -> None:
    """Inspect durable workflow-output projection jobs."""
    result = run_cli_async(
        _projection_status(
            WorkflowOutputProjectionStatusRequest(
                run_id=run_id,
                workflow_name=workflow_name,
                execution_id=execution_id,
                projector_name=projector_name,
                statuses=_parse_projection_statuses(statuses),
                limit=limit,
            )
        )
    )
    _render_projection_status(result, output_format)


@completed_runs_app.command("project")
def project_completed_run_outputs(
    workflow_name: Annotated[
        str,
        typer.Argument(help="Workflow name to project from the completed-run archive."),
    ],
    execution_id: Annotated[
        str,
        typer.Argument(help="Execution ID to project."),
    ],
    run_id: Annotated[
        str | None,
        typer.Option(
            "--run-id",
            help="Optional completed-run ID for traceability.",
        ),
    ] = None,
    force_reproject: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Reproject even when existing projection jobs are terminal.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Inspect eligible outputs without writing projection jobs or records.",
        ),
    ] = False,
    output_format: OutputFormat = "console",
) -> None:
    """Project one archived completed run into curated records."""
    result = run_cli_async(
        _project_completed_run_outputs(
            WorkflowOutputProjectionRequest(
                workflow_name=workflow_name,
                execution_id=execution_id,
                run_id=run_id,
                force_reproject=force_reproject,
                dry_run=dry_run,
            )
        )
    )
    _render_projection_summary(result, output_format)


@completed_runs_app.command("retry-projection")
def retry_projection_jobs(
    workflow_name: Annotated[
        str | None,
        typer.Option("--workflow", help="Filter retryable jobs by workflow name."),
    ] = None,
    execution_id: Annotated[
        str | None,
        typer.Option("--execution-id", help="Filter retryable jobs by execution ID."),
    ] = None,
    projector_name: Annotated[
        str | None,
        typer.Option("--projector", help="Filter retryable jobs by projector name."),
    ] = None,
    statuses: Annotated[
        list[str] | None,
        typer.Option(
            "--status",
            help="Projection status to retry; defaults to failed.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Maximum jobs to match for retry."),
    ] = None,
    stale_running_minutes: Annotated[
        int | None,
        typer.Option(
            "--stale-running-minutes",
            help="Mark running jobs older than this many minutes as failed before retrying.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Report matching jobs without retrying."),
    ] = False,
    output_format: OutputFormat = "console",
) -> None:
    """Retry failed projection jobs and optionally recover stale running jobs."""
    result = run_cli_async(
        _retry_projection_jobs(
            WorkflowOutputProjectionRetryRequest(
                workflow_name=workflow_name,
                execution_id=execution_id,
                projector_name=projector_name,
                statuses=_parse_projection_statuses(statuses)
                or (WorkflowOutputProjectionStatus.FAILED,),
                limit=limit,
                dry_run=dry_run,
                stale_running_started_before=_stale_started_before(
                    stale_running_minutes
                ),
            )
        )
    )
    _render_projection_retry_result(result, output_format)


@completed_runs_app.command("reconcile-projections")
def reconcile_projection_jobs(
    workflow_name: Annotated[
        str | None,
        typer.Option("--workflow", help="Filter archived runs by workflow name."),
    ] = None,
    execution_id: Annotated[
        str | None,
        typer.Option("--execution-id", help="Filter archived runs by execution ID."),
    ] = None,
    since: Annotated[
        datetime | None,
        typer.Option(
            "--since",
            help="Only include runs completed at or after this ISO timestamp.",
        ),
    ] = None,
    until: Annotated[
        datetime | None,
        typer.Option(
            "--until",
            help="Only include runs completed at or before this ISO timestamp.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Maximum missing archived runs to inspect."),
    ] = None,
    enqueue_missing_jobs: Annotated[
        bool,
        typer.Option(
            "--enqueue-missing-jobs",
            help="Project archived runs that have no projection jobs.",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Report missing runs without projection writes unless disabled.",
        ),
    ] = True,
    output_format: OutputFormat = "console",
) -> None:
    """Find archived runs with missing projection jobs and optionally project them."""
    result = run_cli_async(
        _reconcile_projection_jobs(
            WorkflowOutputProjectionReconciliationRequest(
                workflow_name=workflow_name,
                execution_id=execution_id,
                since=since,
                until=until,
                limit=limit,
                enqueue_missing_jobs=enqueue_missing_jobs,
                dry_run=dry_run,
            )
        )
    )
    _render_projection_reconciliation_result(result, output_format)


async def _list_completed_runs(
    workflow_name: str,
    *,
    plugin_dirs: tuple[Path, ...],
) -> list[str]:
    async with cli_runtime_scope(
        plugin_dirs=plugin_dirs,
        autoload_plugins=bool(plugin_dirs),
    ) as scope:
        return await scope.runtime.facade.list_completed_runs(workflow_name)


async def _load_completed_run(
    workflow_name: str,
    execution_id: str,
    *,
    plugin_dirs: tuple[Path, ...],
) -> Any:
    async with cli_runtime_scope(
        plugin_dirs=plugin_dirs,
        autoload_plugins=bool(plugin_dirs),
    ) as scope:
        return await scope.runtime.facade.load_completed_run(
            workflow_name,
            execution_id,
        )


async def _delete_completed_run(
    workflow_name: str,
    execution_id: str,
    *,
    plugin_dirs: tuple[Path, ...],
) -> None:
    async with cli_runtime_scope(
        plugin_dirs=plugin_dirs,
        autoload_plugins=bool(plugin_dirs),
    ) as scope:
        await scope.runtime.facade.delete_completed_run(
            workflow_name,
            execution_id,
            confirmation=DestructiveOperationConfirmation(
                operation=DestructiveWorkflowOperation.DELETE_COMPLETED_RUN,
                target=f"{workflow_name}:{execution_id}",
                requested_by="polaris_cli",
                confirmed=True,
            ),
        )


async def _cleanup_completed_runs(
    *,
    max_age_days: int | None,
    max_count: int | None,
    plugin_dirs: tuple[Path, ...],
    confirm: bool,
) -> int:
    async with cli_runtime_scope(
        plugin_dirs=plugin_dirs,
        autoload_plugins=bool(plugin_dirs),
    ) as scope:
        runtime = scope.runtime
        effective_max_age_days = (
            runtime.config.completed_run_retention_max_age_days
            if max_age_days is None
            else max_age_days
        )
        effective_max_count = (
            runtime.config.completed_run_retention_max_count
            if max_count is None
            else max_count
        )

        if effective_max_age_days is None and effective_max_count is None:
            raise typer.BadParameter(
                "At least one of --max-age-days, --max-count, or configured "
                "completed-run retention defaults must be set"
            )

        if not confirm:
            typer.confirm(
                "Clean up archived runs "
                f"(max_age_days={effective_max_age_days}, "
                f"max_count={effective_max_count})?",
                abort=True,
            )

        return await runtime.facade.cleanup_completed_runs(
            max_age_days=effective_max_age_days,
            max_count=effective_max_count,
            confirmation=DestructiveOperationConfirmation(
                operation=DestructiveWorkflowOperation.CLEANUP_COMPLETED_RUNS,
                target="completed_runs",
                requested_by="polaris_cli",
                confirmed=True,
            ),
        )


@asynccontextmanager
async def _projection_operations_scope() -> AsyncIterator[
    WorkflowOutputProjectionOperationsService
]:
    async with application_request_scope() as request_container:
        yield await request_container.get(WorkflowOutputProjectionOperationsService)


async def _projection_status(
    request: WorkflowOutputProjectionStatusRequest,
) -> WorkflowOutputProjectionStatusResult:
    async with _projection_operations_scope() as service:
        return await service.projection_status(request)


async def _project_completed_run_outputs(
    request: WorkflowOutputProjectionRequest,
) -> CompletedRunProjectionSummary:
    async with _projection_operations_scope() as service:
        return await service.project(request)


async def _retry_projection_jobs(
    request: WorkflowOutputProjectionRetryRequest,
) -> WorkflowOutputProjectionRetryResult:
    async with _projection_operations_scope() as service:
        return await service.retry_projection(request)


async def _reconcile_projection_jobs(
    request: WorkflowOutputProjectionReconciliationRequest,
) -> WorkflowOutputProjectionReconciliationResult:
    async with _projection_operations_scope() as service:
        return await service.reconcile_projections(request)


def _parse_projection_statuses(
    statuses: list[str] | None,
) -> tuple[WorkflowOutputProjectionStatus, ...]:
    if not statuses:
        return ()
    return tuple(WorkflowOutputProjectionStatus(status) for status in statuses)


def _stale_started_before(minutes: int | None) -> datetime | None:
    if minutes is None:
        return None
    if minutes <= 0:
        raise typer.BadParameter("--stale-running-minutes must be positive")
    return datetime.now(UTC) - timedelta(minutes=minutes)


def _render_projection_status(
    result: WorkflowOutputProjectionStatusResult,
    output_format: str,
) -> None:
    if output_format == "json":
        typer.echo(format_json(_projection_status_result_to_dict(result)))
        return
    if output_format != "console":
        raise typer.BadParameter("projection-status supports console or json output")

    typer.echo("Projection Jobs")
    typer.echo(f"Total: {result.total_jobs}")
    if not result.jobs:
        return
    for job in result.jobs:
        typer.echo(
            "  "
            f"{_status_value(job.status)}: {job.workflow_name}/{job.execution_id} "
            f"node={job.node_name} projector={job.projector_name} "
            f"attempts={job.attempt_count} job={job.projection_job_id}"
        )
        if job.last_error:
            typer.echo(f"    error: {job.last_error}")


def _render_projection_summary(
    summary: CompletedRunProjectionSummary,
    output_format: str,
) -> None:
    if output_format == "json":
        typer.echo(format_json(_projection_summary_to_dict(summary)))
        return
    if output_format != "console":
        raise typer.BadParameter("project supports console or json output")

    typer.echo("Workflow Output Projection")
    typer.echo(f"Workflow: {summary.workflow_name}")
    typer.echo(f"Execution: {summary.execution_id}")
    typer.echo(f"Run ID: {summary.run_id}")
    typer.echo(f"Success: {summary.success}")
    typer.echo(f"Jobs: {summary.total_jobs}")
    typer.echo(f"Succeeded: {summary.succeeded_jobs}")
    typer.echo(f"Failed: {summary.failed_jobs}")
    typer.echo(f"Skipped: {summary.skipped_jobs}")
    typer.echo(f"Records Written: {summary.records_written}")
    for outcome in summary.outcomes:
        typer.echo(
            "  "
            f"{_status_value(outcome.status)}: {outcome.node_name} "
            f"projector={outcome.projector_name} records={outcome.records_written}"
        )
        if outcome.message:
            typer.echo(f"    message: {outcome.message}")
        if outcome.error_message:
            typer.echo(f"    error: {outcome.error_message}")


def _render_projection_retry_result(
    result: WorkflowOutputProjectionRetryResult,
    output_format: str,
) -> None:
    if output_format == "json":
        typer.echo(format_json(_retry_result_to_dict(result)))
        return
    if output_format != "console":
        raise typer.BadParameter("retry-projection supports console or json output")

    typer.echo("Projection Retry")
    typer.echo(f"Matched Jobs: {result.matched_jobs}")
    typer.echo(f"Retried Jobs: {result.retried_jobs}")
    typer.echo(f"Recovered Stale Running Jobs: {result.recovered_stale_running_jobs}")
    typer.echo(f"Dry Run: {result.requested.dry_run}")
    for summary in result.summaries:
        typer.echo(
            f"  {summary.workflow_name}/{summary.execution_id}: "
            f"success={summary.success} jobs={summary.total_jobs} "
            f"records={summary.records_written}"
        )


def _render_projection_reconciliation_result(
    result: WorkflowOutputProjectionReconciliationResult,
    output_format: str,
) -> None:
    if output_format == "json":
        typer.echo(format_json(_reconciliation_result_to_dict(result)))
        return
    if output_format != "console":
        raise typer.BadParameter(
            "reconcile-projections supports console or json output"
        )

    typer.echo("Projection Reconciliation")
    typer.echo(f"Scanned Runs: {result.scanned_runs}")
    typer.echo(f"Missing Projection Runs: {result.missing_projection_runs}")
    typer.echo(f"Enqueued Jobs: {result.enqueued_jobs}")
    typer.echo(f"Dry Run: {result.requested.dry_run}")
    for run in result.missing_runs:
        typer.echo(
            f"  missing: {run.workflow_name}/{run.execution_id} "
            f"run={run.run_id} completed_at={run.completed_at}"
        )
    for summary in result.summaries:
        typer.echo(
            f"  projected: {summary.workflow_name}/{summary.execution_id} "
            f"jobs={summary.total_jobs} records={summary.records_written}"
        )


def _projection_status_result_to_dict(
    result: WorkflowOutputProjectionStatusResult,
) -> dict[str, Any]:
    return {
        "total_jobs": result.total_jobs,
        "jobs": [_projection_job_to_dict(job) for job in result.jobs],
    }


def _projection_job_to_dict(job: WorkflowOutputProjectionJobRecord) -> dict[str, Any]:
    return {
        "projection_job_id": job.projection_job_id,
        "run_id": job.run_id,
        "workflow_name": job.workflow_name,
        "execution_id": job.execution_id,
        "node_name": job.node_name,
        "projector_name": job.projector_name,
        "output_contract": job.output_contract,
        "output_schema_version": job.output_schema_version,
        "source_fingerprint": job.source_fingerprint,
        "status": _status_value(job.status),
        "attempt_count": job.attempt_count,
        "last_error": job.last_error,
        "created_at": _datetime_to_json(job.created_at),
        "started_at": _datetime_to_json(job.started_at),
        "completed_at": _datetime_to_json(job.completed_at),
        "updated_at": _datetime_to_json(job.updated_at),
    }


def _projection_summary_to_dict(
    summary: CompletedRunProjectionSummary,
) -> dict[str, Any]:
    return {
        "workflow_name": summary.workflow_name,
        "execution_id": summary.execution_id,
        "run_id": summary.run_id,
        "requested_at": _datetime_to_json(summary.requested_at),
        "completed_at": _datetime_to_json(summary.completed_at),
        "success": summary.success,
        "total_jobs": summary.total_jobs,
        "succeeded_jobs": summary.succeeded_jobs,
        "failed_jobs": summary.failed_jobs,
        "skipped_jobs": summary.skipped_jobs,
        "records_written": summary.records_written,
        "outcomes": [
            {
                "status": _status_value(outcome.status),
                "projector_name": outcome.projector_name,
                "node_name": outcome.node_name,
                "output_contract": outcome.output_contract,
                "output_schema_version": outcome.output_schema_version,
                "source_fingerprint": outcome.source_fingerprint,
                "records_written": outcome.records_written,
                "job_id": outcome.job_id,
                "message": outcome.message,
                "error_type": outcome.error_type,
                "error_message": outcome.error_message,
                "started_at": _datetime_to_json(outcome.started_at),
                "completed_at": _datetime_to_json(outcome.completed_at),
            }
            for outcome in summary.outcomes
        ],
    }


def _retry_result_to_dict(
    result: WorkflowOutputProjectionRetryResult,
) -> dict[str, Any]:
    return {
        "matched_jobs": result.matched_jobs,
        "retried_jobs": result.retried_jobs,
        "recovered_stale_running_jobs": result.recovered_stale_running_jobs,
        "dry_run": result.requested.dry_run,
        "summaries": [
            _projection_summary_to_dict(summary) for summary in result.summaries
        ],
    }


def _reconciliation_result_to_dict(
    result: WorkflowOutputProjectionReconciliationResult,
) -> dict[str, Any]:
    return {
        "scanned_runs": result.scanned_runs,
        "missing_projection_runs": result.missing_projection_runs,
        "enqueued_jobs": result.enqueued_jobs,
        "dry_run": result.requested.dry_run,
        "missing_runs": [_missing_run_to_dict(run) for run in result.missing_runs],
        "summaries": [
            _projection_summary_to_dict(summary) for summary in result.summaries
        ],
    }


def _missing_run_to_dict(run: MissingProjectionRunRecord) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "workflow_name": run.workflow_name,
        "execution_id": run.execution_id,
        "completed_at": _datetime_to_json(run.completed_at),
    }


def _status_value(status: Any) -> str:
    return str(status.value) if hasattr(status, "value") else str(status)


def _datetime_to_json(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
