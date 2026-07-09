from __future__ import annotations

from pathlib import Path
import sys
from typing import cast

import typer

from interfaces.cli.output import CliOutputFormat
from interfaces.cli.output import WorkflowOutputBundle
from interfaces.cli.output import emit_workflow_output_bundle
from interfaces.cli.output import render_workflow_output_bundle
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope
from interfaces.cli.rendering.workflow_rendering import render_workflow_output
from interfaces.cli.services.workflow_control_input_service import AsyncLineReader
from interfaces.cli.services.workflow_control_input_service import (
    WorkflowControlNotification,
)
from interfaces.cli.services.workflow_progress_service import (
    WorkflowProgressConsoleRenderer,
)


_WORKFLOW_ARTIFACT_FORMATS = frozenset(
    {
        "html",
        "json",
        "markdown",
        "pdf",
    }
)


def validate_workflow_artifact_format(
    output_format: str | None,
) -> None:
    if output_format is None:
        return

    if output_format == "console":
        raise typer.BadParameter(
            "--format console is obsolete. Console output is now the default. "
            "Use --format html, json, markdown, or pdf to also select a file format."
        )

    if output_format not in _WORKFLOW_ARTIFACT_FORMATS:
        raise typer.BadParameter("format must be one of: html, json, markdown, pdf")


def build_interactive_input_reader() -> AsyncLineReader | None:
    if sys.stdin.isatty():
        return None

    return _closed_interactive_input


async def _closed_interactive_input() -> str | None:
    return None


def build_progress_renderer() -> WorkflowProgressConsoleRenderer:
    return WorkflowProgressConsoleRenderer(
        emitter=emit_cli_status_line,
    )


def emit_control_notification(
    notification: WorkflowControlNotification,
) -> None:
    typer.echo(
        notification.to_console(),
        err=True,
    )


def render_workflow_output_with_fallback(
    envelope: WorkflowRenderEnvelope,
    output_format: str | None,
    *,
    output_path: Path | None,
    raw: bool = False,
    renderer_name: str = "Workflow output",
) -> WorkflowOutputBundle:
    try:
        return render_workflow_output_bundle(
            envelope,
            output_format=cast(
                CliOutputFormat | None,
                output_format,
            ),
            output_path=output_path,
            raw=raw,
        )
    except Exception as exc:
        try:
            generic_output = render_workflow_output(
                envelope,
                _fallback_render_format(
                    output_format,
                ),
            )
        except Exception as fallback_exc:
            return WorkflowOutputBundle(
                stdout=(
                    f"Workflow: {envelope.workflow_name}\n"
                    f"Execution: {envelope.execution_id}\n"
                    f"Success: {envelope.success}\n"
                    f"Status: {envelope.status}\n"
                    f"Error: {renderer_name.lower()} renderer failed: {exc}\n"
                    f"Fallback Error: {fallback_exc}"
                )
            )

        return WorkflowOutputBundle(
            stdout=(
                f"{renderer_name} renderer failed; showing generic workflow output.\n"
                f"Render Error: {exc}\n\n"
                f"{generic_output}"
            )
        )


def emit_rendered_workflow_output(
    *,
    rendered: WorkflowOutputBundle,
    output: Path | None,
) -> Path | None:
    return emit_workflow_output_bundle(
        rendered,
        explicit_output_path=output,
        stdout_emitter=typer.echo,
        status_emitter=emit_cli_status_line,
    )


def _fallback_render_format(
    output_format: str | None,
) -> str:
    if output_format == "json":
        return "json"

    if output_format in {
        "html",
        "markdown",
        "pdf",
    }:
        return "markdown"

    return "console"


def emit_cli_status_line(
    line: str,
) -> None:
    typer.echo(
        line,
        err=True,
    )
