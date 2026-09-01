from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from application.presentation.governed_result import GovernedPresentationResult
from application.reports import MorningReportDocument, MorningReportMarkdownRenderer
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.output.governed_morning_report_pdf import MorningReportPdfRenderer
from interfaces.cli.output.pdf_output_renderer import MarkdownPdfRenderer
from interfaces.cli.output.workflow_output import (
    CliOutputFormat,
    WorkflowOutputArtifact,
    WorkflowOutputBundle,
    output_path_for_format,
)
from interfaces.cli.output.workflow_output_renderer import (
    render_html_document,
)
from interfaces.cli.output.workflow_output_renderer import (
    render_workflow_output_bundle as render_generic_workflow_output_bundle,
)
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope

PdfRenderer = Callable[[str], bytes]


def render_workflow_output_bundle(
    envelope: WorkflowRenderEnvelope,
    *,
    output_format: CliOutputFormat | None,
    output_path: Path | None = None,
    raw: bool = False,
    pdf_renderer: PdfRenderer | None = None,
    governed_morning_report: (
        GovernedPresentationResult[MorningReportDocument] | None
    ) = None,
) -> WorkflowOutputBundle:
    """Render professional morning reports only from application-governed results."""

    if envelope.workflow_name != "morning_report":
        return render_generic_workflow_output_bundle(
            envelope,
            output_format=output_format,
            output_path=output_path,
            raw=raw,
            pdf_renderer=pdf_renderer,
        )
    if raw:
        raise ValueError(
            "raw morning-report output cannot bypass governed presentation."
        )

    markdown = _governed_morning_report_markdown(governed_morning_report)
    stdout = (
        _governed_morning_report_json(governed_morning_report)
        if output_format == "json"
        else markdown
    )
    if output_format is None:
        return WorkflowOutputBundle(stdout=stdout)

    artifact_content = _artifact_content(
        governed_morning_report,
        output_format=output_format,
        stdout=stdout,
        markdown=markdown,
        pdf_renderer=pdf_renderer,
    )
    return WorkflowOutputBundle(
        stdout=stdout,
        artifact=WorkflowOutputArtifact(
            output_format=output_format,
            path=output_path
            or output_path_for_format(
                envelope.workflow_name or "workflow",
                output_format,
            ),
            content=artifact_content,
        ),
    )


def _governed_morning_report_markdown(
    governed_result: GovernedPresentationResult[MorningReportDocument] | None,
) -> str:
    if governed_result is None:
        return _unavailable_markdown(
            disposition="withheld",
            limitations=(
                "The application did not provide a governed morning-report result.",
            ),
        )
    if not governed_result.decision.may_present:
        return _unavailable_markdown(
            disposition=governed_result.projection.disposition,
            limitations=governed_result.projection.limitations,
        )
    return MorningReportMarkdownRenderer().render(governed_result)


def _governed_morning_report_json(
    governed_result: GovernedPresentationResult[MorningReportDocument] | None,
) -> str:
    if governed_result is None:
        return format_json(
            {
                "presentation": {
                    "disposition": "withheld",
                    "may_present": False,
                    "limitations": [
                        "The application did not provide a governed "
                        "morning-report result."
                    ],
                },
                "report": None,
            }
        )
    return format_json(
        {
            "presentation": asdict(governed_result.projection),
            "report": (
                asdict(governed_result.payload)
                if governed_result.payload is not None
                and governed_result.decision.may_present
                else None
            ),
        }
    )


def _artifact_content(
    governed_result: GovernedPresentationResult[MorningReportDocument] | None,
    *,
    output_format: CliOutputFormat,
    stdout: str,
    markdown: str,
    pdf_renderer: PdfRenderer | None,
) -> str | bytes:
    if output_format in {"json", "markdown"}:
        return stdout
    if output_format == "html":
        return render_html_document(
            markdown,
            title="Polaris Morning Financial Report",
        )
    if output_format == "pdf":
        if pdf_renderer is not None:
            return pdf_renderer(markdown)
        if (
            governed_result is not None
            and governed_result.decision.may_present
            and governed_result.payload is not None
        ):
            return MorningReportPdfRenderer().render(governed_result)
        return MarkdownPdfRenderer().render(
            markdown,
            title="Polaris Morning Financial Report",
        )
    raise ValueError("format must be one of: html, json, markdown, pdf")


def _unavailable_markdown(
    *,
    disposition: str,
    limitations: tuple[str, ...],
) -> str:
    lines = [
        "# Polaris Morning Financial Report",
        "",
        "## Presentation Status",
        "",
        "This report is unavailable for external presentation.",
        "",
        f"- Disposition: {disposition}",
    ]
    lines.extend(f"- Limitation: {item}" for item in limitations)
    return "\n".join(lines) + "\n"


__all__ = ["render_workflow_output_bundle"]
