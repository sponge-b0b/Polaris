from __future__ import annotations

import typer
from pathlib import Path
from typing import Annotated
from typing import Any

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
