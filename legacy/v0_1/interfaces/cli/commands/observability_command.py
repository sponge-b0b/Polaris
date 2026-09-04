from __future__ import annotations

from typing import Annotated, Literal

import typer

from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.services.async_runner import run_cli_async
from interfaces.cli.services.observability_command_service import (
    ObservabilityCommandService,
    render_ai_observability_status,
)

observability_app = typer.Typer(
    help="Inspect Polaris observability surfaces.",
    no_args_is_help=True,
)


@observability_app.callback()
def observability_callback() -> None:
    return None


@observability_app.command(
    "ai-status",
    help="Show required Langfuse AI-observability projection status.",
)
def ai_observability_status(
    output_format: Annotated[
        Literal["console", "json"],
        typer.Option("--format", help="Output format."),
    ] = "console",
) -> None:
    status = run_cli_async(ObservabilityCommandService().ai_status())
    if output_format == "json":
        typer.echo(format_json(status))
    else:
        typer.echo(render_ai_observability_status(status))
    if not status.healthy:
        raise typer.Exit(code=1)
