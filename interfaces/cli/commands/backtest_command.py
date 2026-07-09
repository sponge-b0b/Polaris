from __future__ import annotations

from pathlib import Path
from typing import Annotated
from typing import Any

import typer

from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.services.async_runner import run_cli_async
from interfaces.cli.services.backtest_command_service import BacktestCommandService
from interfaces.cli.services.backtest_command_service import BacktestListCommandRequest
from interfaces.cli.services.backtest_command_service import (
    BacktestReportCommandRequest,
)
from interfaces.cli.services.backtest_command_service import BacktestRunCommandRequest
from interfaces.cli.services.backtest_command_service import BacktestShowCommandRequest

backtest_app = typer.Typer(
    help="Run and inspect runtime-native backtests.",
    no_args_is_help=True,
)

BacktestOutputFormat = Annotated[
    str,
    typer.Option(
        "--format",
        "-f",
        help="Output format: console, json, or markdown.",
    ),
]

PersistedOutputFormat = Annotated[
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


@backtest_app.callback()
def backtest_callback() -> None:
    return None


@backtest_app.command(
    "run",
    help="Run a deterministic backtest scenario through the canonical runtime.",
)
def run_backtest(
    scenario: Annotated[
        Path,
        typer.Option(
            "--scenario",
            "-s",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Backtest scenario YAML or JSON file.",
        ),
    ],
    output_format: BacktestOutputFormat = "console",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional file path for the rendered backtest output.",
        ),
    ] = None,
    persist_results: Annotated[
        bool,
        typer.Option(
            "--persist-results/--no-persist-results",
            help="Persist workflow and curated backtest results.",
        ),
    ] = True,
    checkpoint_workflow_runs: Annotated[
        bool,
        typer.Option(
            "--checkpoint-workflow-runs/--no-checkpoint-workflow-runs",
            help="Checkpoint each workflow execution in the simulation timeline.",
        ),
    ] = True,
    plugin_dirs: PluginDirs = [],
) -> None:
    _validate_backtest_output_format(
        output_format,
    )
    result = _run_cli_command(
        BacktestCommandService().run_backtest(
            BacktestRunCommandRequest(
                scenario_path=scenario,
                output_format=output_format,
                persist_results=persist_results,
                checkpoint_workflow_runs=checkpoint_workflow_runs,
                plugin_dirs=tuple(plugin_dirs),
            )
        )
    )
    rendered = _render_backtest_result(
        result,
        output_format,
    )
    _emit_output(
        rendered,
        output_path=output,
    )
    persistence_error = _persistence_error(
        result,
    )
    if persistence_error is not None:
        typer.echo(
            f"Persistence warning: {persistence_error}",
            err=True,
        )
        raise typer.Exit(
            code=1,
        )
    if not result.success:
        raise typer.Exit(
            code=1,
        )


@backtest_app.command(
    "list",
    help="List persisted backtest runs from PostgreSQL.",
)
def list_backtests(
    scenario_id: Annotated[
        str | None,
        typer.Option(
            "--scenario-id",
            help="Filter by scenario id.",
        ),
    ] = None,
    workflow_name: Annotated[
        str | None,
        typer.Option(
            "--workflow-name",
            help="Filter by workflow name.",
        ),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Filter by backtest run status.",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            help="Maximum persisted runs to return.",
        ),
    ] = 20,
    output_format: PersistedOutputFormat = "console",
) -> None:
    _validate_persisted_output_format(
        output_format,
    )
    runs = _run_cli_command(
        BacktestCommandService().list_backtests(
            BacktestListCommandRequest(
                scenario_id=scenario_id,
                workflow_name=workflow_name,
                status=status,
                limit=limit,
            )
        )
    )
    typer.echo(
        format_json(runs) if output_format == "json" else _render_run_list(runs),
    )


@backtest_app.command(
    "show",
    help="Show a persisted backtest run summary from PostgreSQL.",
)
def show_backtest(
    backtest_run_id: Annotated[
        str,
        typer.Argument(
            help="Persisted backtest run id.",
        ),
    ],
    output_format: PersistedOutputFormat = "console",
) -> None:
    _validate_persisted_output_format(
        output_format,
    )
    bundle = _run_cli_command(
        BacktestCommandService().show_backtest(
            BacktestShowCommandRequest(
                backtest_run_id=backtest_run_id,
            )
        )
    )
    typer.echo(
        format_json(bundle)
        if output_format == "json"
        else _render_bundle_summary(bundle),
    )


@backtest_app.command(
    "report",
    help="Render a persisted backtest report artifact from PostgreSQL.",
)
def report_backtest(
    backtest_run_id: Annotated[
        str,
        typer.Argument(
            help="Persisted backtest run id.",
        ),
    ],
    output_format: BacktestOutputFormat = "markdown",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional file path for the rendered report artifact.",
        ),
    ] = None,
) -> None:
    _validate_backtest_output_format(
        output_format,
    )
    rendered = _run_cli_command(
        BacktestCommandService().render_backtest_report(
            BacktestReportCommandRequest(
                backtest_run_id=backtest_run_id,
                output_format=output_format,
            )
        )
    )
    _emit_output(
        rendered,
        output_path=output,
    )


def _run_cli_command(
    awaitable: Any,
) -> Any:
    try:
        return run_cli_async(
            awaitable,
        )
    except ValueError as exc:
        raise typer.BadParameter(
            str(exc),
        ) from exc
    except RuntimeError as exc:
        typer.echo(
            f"Error: {exc}",
            err=True,
        )
        raise typer.Exit(
            code=1,
        ) from exc


def _validate_backtest_output_format(
    output_format: str,
) -> None:
    if output_format not in {"console", "json", "markdown"}:
        raise typer.BadParameter("format must be one of: console, json, markdown")


def _validate_persisted_output_format(
    output_format: str,
) -> None:
    if output_format not in {"console", "json"}:
        raise typer.BadParameter("format must be one of: console, json")


def _persistence_error(
    result: Any,
) -> str | None:
    metadata = getattr(
        result,
        "metadata",
        {},
    )
    if not isinstance(metadata, dict):
        metadata = dict(metadata)

    error = metadata.get(
        "persistence_error",
    )
    if error is None:
        return None
    return str(error)


def _render_backtest_result(
    result: Any,
    output_format: str,
) -> str:
    if output_format == "json":
        return result.artifacts.get(
            "json",
            format_json(result),
        )
    if output_format == "markdown":
        return result.artifacts.get(
            "markdown",
            format_json(result),
        )
    return result.artifacts.get(
        "console",
        _render_bundle_like_result_summary(result),
    )


def _render_run_list(
    runs: tuple[Any, ...],
) -> str:
    if not runs:
        return "No persisted backtest runs found."

    lines = [
        "Backtest Runs",
        "============",
    ]
    for run in runs:
        lines.append(
            " - {run_id} | {workflow} | {status} | success={success} | {completed}".format(
                run_id=run.backtest_run_id,
                workflow=run.workflow_name,
                status=run.status,
                success=run.success,
                completed=run.completed_at.isoformat(),
            )
        )
    return "\n".join(lines)


def _render_bundle_summary(
    bundle: Any,
) -> str:
    return "\n".join(
        (
            f"Backtest: {bundle.scenario.name}",
            f"Run ID: {bundle.run.backtest_run_id}",
            f"Scenario: {bundle.run.scenario_id}",
            f"Workflow: {bundle.run.workflow_name}",
            f"Status: {bundle.run.status}",
            f"Success: {bundle.run.success}",
            f"Steps: {len(bundle.steps)}",
            f"Fills: {len(bundle.fills)}",
            f"Metrics: {len(bundle.metrics)}",
            f"Artifacts: {', '.join(artifact.artifact_format for artifact in bundle.artifacts)}",
        )
    )


def _render_bundle_like_result_summary(
    result: Any,
) -> str:
    return "\n".join(
        (
            f"Backtest: {result.scenario.name}",
            f"Run ID: {result.backtest_run_id}",
            f"Workflow: {result.scenario.workflow_name}",
            f"Status: {result.status}",
            f"Success: {result.success}",
            f"Steps: {len(result.steps)}",
        )
    )


def _emit_output(
    rendered: str,
    *,
    output_path: Path | None,
) -> None:
    if output_path is None:
        typer.echo(
            rendered,
        )
        return

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        rendered,
        encoding="utf-8",
    )
    typer.echo(
        f"Wrote backtest output: {output_path}",
        err=True,
    )
