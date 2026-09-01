from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from application.reports import (
    MorningReportAssembler,
    MorningReportDocument,
    MorningReportMarkdownRenderer,
    MorningReportPersistenceService,
    MorningReportPresentationPreparation,
    ReportArtifactReference,
)
from config.settings import Settings
from core.bootstrap.di_providers import application_request_scope
from core.storage.persistence.reports import ReportPersistenceResult
from interfaces.cli.commands.workflow_command_boundary import (
    build_progress_renderer,
    emit_cli_status_line,
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
                "Raw workflow output is not available from the governed "
                "morning-report presentation boundary."
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
    validate_workflow_artifact_format(output_format)
    if raw:
        raise typer.BadParameter(
            "--raw cannot bypass governed morning-report presentation."
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
                    plugin_dirs=tuple(plugin_dirs),
                    progress_handler=progress_renderer.handle,
                    interactive_control=False,
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

    preparation = _prepare_morning_report_presentation(envelope)
    rendered = render_workflow_output_with_fallback(
        envelope,
        output_format,
        output_path=output,
        raw=False,
        renderer_name="Morning report",
        governed_morning_report=(None if preparation is None else preparation.result),
    )
    written_path = emit_rendered_workflow_output(
        rendered=rendered,
        output=output,
    )
    _persist_governed_morning_report(
        preparation,
        written_path=written_path,
    )

    presentation_failed = (
        preparation is None or not preparation.result.decision.may_present
    )
    if not envelope.success or presentation_failed:
        raise typer.Exit(code=1)


def _prepare_morning_report_presentation(
    envelope: WorkflowRenderEnvelope,
) -> MorningReportPresentationPreparation | None:
    if envelope.workflow_name != DEFAULT_MORNING_REPORT_WORKFLOW:
        return None
    try:
        document = MorningReportAssembler().assemble(envelope.to_dict())
        return run_cli_async(_prepare_morning_report(document))
    except Exception as exc:
        emit_cli_status_line(
            f"[presentation] failed to govern morning report: {type(exc).__name__}"
        )
        return None


def _persist_governed_morning_report(
    preparation: MorningReportPresentationPreparation | None,
    *,
    written_path: Path | None,
) -> None:
    if preparation is None:
        return
    if not Settings().ENABLE_POSTGRES_REPORT_PERSISTENCE:
        return
    if not preparation.result.decision.may_present:
        emit_cli_status_line(
            "[persistence] morning report was not persisted because presentation "
            f"is {preparation.result.projection.disposition}"
        )
        return

    try:
        markdown_body = MorningReportMarkdownRenderer().render(preparation.result)
        artifact_references = (
            (ReportArtifactReference.from_path(written_path),)
            if written_path is not None
            else ()
        )
        result = run_cli_async(
            _persist_morning_report_to_postgres(
                preparation,
                markdown_body=markdown_body,
                artifact_references=artifact_references,
            )
        )
        if not result.success:
            emit_cli_status_line(
                f"[persistence] failed to persist morning report: {result.error}"
            )
    except Exception as exc:
        emit_cli_status_line(
            f"[persistence] failed to persist morning report: {type(exc).__name__}"
        )


async def _prepare_morning_report(
    document: MorningReportDocument,
) -> MorningReportPresentationPreparation:
    async with application_request_scope() as request_container:
        service = await request_container.get(MorningReportPersistenceService)
        return await service.prepare_presentation(document)


async def _persist_morning_report_to_postgres(
    preparation: MorningReportPresentationPreparation,
    *,
    markdown_body: str,
    artifact_references: tuple[ReportArtifactReference, ...],
) -> ReportPersistenceResult:
    async with application_request_scope() as request_container:
        service = await request_container.get(MorningReportPersistenceService)
        return await service.persist(
            preparation,
            markdown_body=markdown_body,
            artifact_references=artifact_references,
        )
