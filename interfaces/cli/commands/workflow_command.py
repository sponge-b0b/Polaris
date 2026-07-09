from __future__ import annotations

from pathlib import Path
from typing import Annotated
from typing import Any

import typer

from interfaces.cli.bootstrap.container import cli_runtime_scope
from interfaces.cli.commands.workflow_command_boundary import (
    build_interactive_input_reader,
)
from interfaces.cli.commands.workflow_command_boundary import build_progress_renderer
from interfaces.cli.commands.workflow_command_boundary import emit_control_notification
from interfaces.cli.commands.workflow_command_boundary import (
    emit_rendered_workflow_output,
)
from interfaces.cli.commands.workflow_command_boundary import (
    render_workflow_output_with_fallback,
)
from interfaces.cli.commands.workflow_command_boundary import (
    validate_workflow_artifact_format,
)
from interfaces.cli.formatters.console_formatter import format_workflow_list
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.formatters.json_formatter import to_jsonable
from interfaces.cli.rendering.workflow_rendering import render_workflow_output
from interfaces.cli.rendering.workflow_rendering import (
    workflow_exception_to_render_envelope,
)
from interfaces.cli.services.async_runner import run_cli_async
from interfaces.cli.services.workflow_command_service import WorkflowCommandService
from interfaces.cli.services.workflow_command_service import WorkflowRunCommandRequest

workflow_app = typer.Typer(
    help="Run and inspect registered runtime workflows.",
    no_args_is_help=True,
)


OutputFormat = Annotated[
    str,
    typer.Option(
        "--format",
        "-f",
        help="Output format: console, json, or markdown.",
    ),
]


RunOutputFormat = Annotated[
    str | None,
    typer.Option(
        "--format",
        "-f",
        help=(
            "Optional additional workflow file format: html, json, markdown, "
            "or pdf. Terminal output is always rendered."
        ),
    ),
]


PluginDirs = Annotated[
    list[Path],
    typer.Option(
        "--plugin-dir",
        help="Plugin directory to autoload before running commands.",
    ),
]


def _render(
    value: Any,
    output_format: str,
) -> str:
    try:
        return render_workflow_output(
            value,
            output_format,
        )
    except ValueError as exc:
        raise typer.BadParameter(
            str(exc),
        ) from exc


@workflow_app.command("list")
def list_workflows(
    tag: Annotated[
        str | None,
        typer.Option(
            "--tag",
            help="Filter workflows by tag.",
        ),
    ] = None,
    output_format: OutputFormat = "console",
    plugin_dirs: PluginDirs = [],
) -> None:
    summaries = run_cli_async(
        _list_workflow_summaries(
            tag=tag,
            plugin_dirs=tuple(plugin_dirs),
        )
    )

    if output_format == "json":
        typer.echo(
            format_json(summaries),
        )
        return

    if output_format != "console":
        raise typer.BadParameter("workflow list supports console or json output")

    typer.echo(
        format_workflow_list(
            summaries,
        )
    )


@workflow_app.command("describe")
def describe_workflow(
    workflow_name: Annotated[
        str,
        typer.Argument(
            help="Registered workflow name.",
        ),
    ],
    output_format: OutputFormat = "json",
    plugin_dirs: PluginDirs = [],
) -> None:
    description = run_cli_async(
        _describe_workflow(
            workflow_name,
            plugin_dirs=tuple(plugin_dirs),
        )
    )

    typer.echo(
        format_json(
            description,
        )
        if output_format == "json"
        else description
    )


async def _list_workflow_summaries(
    *,
    tag: str | None,
    plugin_dirs: tuple[Path, ...],
) -> list[dict[str, Any]]:
    async with cli_runtime_scope(
        plugin_dirs=plugin_dirs,
        autoload_plugins=bool(plugin_dirs),
    ) as scope:
        return [
            summary.to_dict()
            for summary in scope.runtime.facade.list_workflow_summaries(
                tag=tag,
            )
        ]


async def _describe_workflow(
    workflow_name: str,
    *,
    plugin_dirs: tuple[Path, ...],
) -> Any:
    async with cli_runtime_scope(
        plugin_dirs=plugin_dirs,
        autoload_plugins=bool(plugin_dirs),
    ) as scope:
        return scope.runtime.facade.describe_workflow(
            workflow_name,
        )


@workflow_app.command(
    "run",
    help=(
        "Run a workflow. Terminal output, progress notifications, and "
        "interactive workflow control are enabled by default; --format writes "
        "an additional output file."
    ),
)
def run_workflow(
    workflow_name: Annotated[
        str,
        typer.Argument(
            help="Registered workflow name.",
        ),
    ],
    mode: Annotated[
        str,
        typer.Option(
            "--mode",
            help="Runtime mode.",
        ),
    ] = "live",
    execution_id: Annotated[
        str | None,
        typer.Option(
            "--execution-id",
            help="Optional execution id.",
        ),
    ] = None,
    metadata: Annotated[
        list[str],
        typer.Option(
            "--metadata",
            help="Metadata as key=value. May be repeated.",
        ),
    ] = [],
    output_format: RunOutputFormat = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Optional output file path. With --format, writes the selected "
                "artifact there; without --format, mirrors terminal text."
            ),
        ),
    ] = None,
    plugin_dirs: PluginDirs = [],
) -> None:
    validate_workflow_artifact_format(
        output_format,
    )
    parsed_metadata = _parse_metadata(
        metadata,
    )

    try:
        service = WorkflowCommandService()
        progress_renderer = build_progress_renderer()
        envelope = run_cli_async(
            service.run_workflow(
                WorkflowRunCommandRequest(
                    workflow_name=workflow_name,
                    mode=mode,
                    execution_id=execution_id,
                    metadata=parsed_metadata,
                    plugin_dirs=tuple(
                        plugin_dirs,
                    ),
                    error_summary={
                        "mode": mode,
                        "metadata": list(
                            metadata,
                        ),
                        "interface": "cli",
                        "command": "workflow run",
                    },
                    progress_handler=progress_renderer.handle,
                    interactive_control=True,
                    interactive_input=build_interactive_input_reader(),
                    control_handler=emit_control_notification,
                )
            )
        )
    except Exception as exc:
        envelope = workflow_exception_to_render_envelope(
            exc,
            workflow_name=workflow_name,
            execution_id=execution_id,
            summary={
                "mode": mode,
                "metadata": list(
                    metadata,
                ),
                "interface": "cli",
                "command": "workflow run",
            },
        )

    rendered = render_workflow_output_with_fallback(
        envelope,
        output_format,
        output_path=output,
    )
    emit_rendered_workflow_output(
        rendered=rendered,
        output=output,
    )

    if not envelope.success:
        raise typer.Exit(
            code=1,
        )


def _parse_metadata(
    metadata: list[str],
) -> dict[str, Any]:
    parsed: dict[str, Any] = {}

    for item in metadata:
        if "=" not in item:
            raise typer.BadParameter("metadata must use key=value format")

        key, value = item.split(
            "=",
            1,
        )
        parsed[key] = value

    return parsed


def workflow_result_to_dict(
    value: Any,
) -> dict[str, Any]:
    return to_jsonable(
        value,
    )
