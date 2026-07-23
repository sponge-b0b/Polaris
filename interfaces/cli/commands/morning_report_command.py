from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from application.reports import (
    MorningReportAssembler,
    MorningReportDocument,
    MorningReportMarkdownRenderer,
    MorningReportPersistenceService,
    ReportArtifactReference,
)
from core.bootstrap.di_providers import application_request_scope
from core.storage.persistence.reports import ReportPersistenceResult
from interfaces.cli.commands.workflow_command_boundary import (
    build_interactive_input_reader,
    build_progress_renderer,
    emit_cli_status_line,
    emit_control_notification,
    emit_rendered_workflow_output,
    render_workflow_output_with_fallback,
    validate_workflow_artifact_format,
)
from interfaces.cli.rendering.workflow_rendering import (
    WorkflowRenderEnvelope,
    workflow_exception_to_render_envelope,
)
from interfaces.cli.services.async_runner import run_cli_async
from interfaces.cli.services.workflow_command_service import (
    MorningReportCommandRequest,
    WorkflowCommandService,
)

DEFAULT_MORNING_REPORT_WORKFLOW = "morning_report"


def morning_report(
    symbol: Annotated[
        str,
        typer.Option(
            "--symbol",
            "-s",
            help="Primary symbol for report context.",
        ),
    ] = "SPY",
    output_format: Annotated[
        str | None,
        typer.Option(
            "--format",
            "-f",
            help=(
                "Optional additional report file format: html, json, "
                "markdown, or pdf. Terminal output is always rendered."
            ),
        ),
    ] = None,
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
    raw: Annotated[
        bool,
        typer.Option(
            "--raw/--no-raw",
            help=(
                "Render the generic workflow output instead of the "
                "professional morning report for terminal/markdown output."
            ),
        ),
    ] = False,
    plugin_dirs: Annotated[
        list[Path],
        typer.Option(
            "--plugin-dir",
            help="Plugin directory to autoload before running the workflow.",
        ),
    ] = None,
) -> None:
    if plugin_dirs is None:
        plugin_dirs = []
    validate_workflow_artifact_format(
        output_format,
    )

    try:
        service = WorkflowCommandService(
            default_morning_report_workflow=DEFAULT_MORNING_REPORT_WORKFLOW,
        )
        progress_renderer = build_progress_renderer()
        envelope = run_cli_async(
            service.run_morning_report(
                MorningReportCommandRequest(
                    symbol=symbol,
                    plugin_dirs=tuple(
                        plugin_dirs,
                    ),
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
            workflow_name=DEFAULT_MORNING_REPORT_WORKFLOW,
            summary={
                "symbol": symbol,
                "interface": "cli",
                "command": "morning-report",
            },
        )

    rendered = render_workflow_output_with_fallback(
        envelope,
        output_format,
        output_path=output,
        raw=raw,
        renderer_name="Morning report",
    )
    written_path = emit_rendered_workflow_output(
        rendered=rendered,
        output=output,
    )
    _persist_rendered_morning_report(
        envelope,
        raw=raw,
        written_path=written_path,
    )

    if not envelope.success:
        raise typer.Exit(
            code=1,
        )


def _persist_rendered_morning_report(
    envelope: WorkflowRenderEnvelope,
    *,
    raw: bool,
    written_path: Path | None,
) -> None:
    if raw or envelope.workflow_name != DEFAULT_MORNING_REPORT_WORKFLOW:
        return

    if not _postgres_report_persistence_enabled():
        return

    try:
        document = MorningReportAssembler().assemble(
            envelope.to_dict(),
        )
        markdown_body = MorningReportMarkdownRenderer().render(
            document,
        )
        artifact_references = (
            (
                ReportArtifactReference.from_path(
                    written_path,
                ),
            )
            if written_path is not None
            else ()
        )
        result = run_cli_async(
            _persist_morning_report_to_postgres(
                document,
                markdown_body=markdown_body,
                artifact_references=artifact_references,
            )
        )
        if not result.success:
            emit_cli_status_line(
                f"[persistence] failed to persist morning report: {result.error}"
            )
    except Exception as exc:
        emit_cli_status_line(f"[persistence] failed to persist morning report: {exc}")


async def _persist_morning_report_to_postgres(
    document: MorningReportDocument,
    *,
    markdown_body: str,
    artifact_references: tuple[ReportArtifactReference, ...],
) -> ReportPersistenceResult:
    async with application_request_scope() as request_container:
        service = await request_container.get(MorningReportPersistenceService)
        return await service.persist(
            document,
            markdown_body=markdown_body,
            artifact_references=artifact_references,
        )


def _postgres_report_persistence_enabled() -> bool:
    value = os.environ.get(
        "POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE",
        "",
    )
    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
