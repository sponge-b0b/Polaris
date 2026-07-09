from __future__ import annotations

from collections.abc import Callable
from html import escape
from pathlib import Path
from application.reports import MorningReportAssembler
from application.reports import MorningReportMarkdownRenderer
from interfaces.cli.output.pdf_output_renderer import MarkdownPdfRenderer
from interfaces.cli.output.pdf_output_renderer import MorningReportPdfRenderer
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.output.workflow_output import CliOutputFormat
from interfaces.cli.output.workflow_output import WorkflowOutputArtifact
from interfaces.cli.output.workflow_output import WorkflowOutputBundle
from interfaces.cli.output.workflow_output import output_path_for_format
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope
from interfaces.cli.rendering.workflow_rendering import render_workflow_output

PdfRenderer = Callable[[str], bytes]


def render_workflow_output_bundle(
    envelope: WorkflowRenderEnvelope,
    *,
    output_format: CliOutputFormat | None,
    output_path: Path | None = None,
    raw: bool = False,
    pdf_renderer: PdfRenderer | None = None,
) -> WorkflowOutputBundle:
    """
    Render mandatory CLI stdout plus an optional explicit-format file artifact.

    Runtime data is consumed through the CLI render envelope. Human report
    formatting remains a CLI/report-layer concern, not a runtime concern.
    """

    stdout = _render_stdout(
        envelope,
        output_format=output_format,
        raw=raw,
    )

    if output_format is None:
        return WorkflowOutputBundle(
            stdout=stdout,
        )

    artifact_content = _render_artifact_content(
        envelope,
        output_format=output_format,
        stdout=stdout,
        raw=raw,
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


def _render_stdout(
    envelope: WorkflowRenderEnvelope,
    *,
    output_format: CliOutputFormat | None,
    raw: bool,
) -> str:
    if output_format == "json":
        return format_json(
            envelope,
        )

    if output_format in {
        "html",
        "pdf",
        "markdown",
    }:
        return _render_markdown(
            envelope,
            raw=raw,
        )

    if _is_professional_morning_report(
        envelope,
        raw=raw,
    ):
        return _render_morning_report_markdown(
            envelope,
        )

    return render_workflow_output(
        envelope,
        "console",
    )


def _render_artifact_content(
    envelope: WorkflowRenderEnvelope,
    *,
    output_format: CliOutputFormat,
    stdout: str,
    raw: bool,
    pdf_renderer: PdfRenderer | None,
) -> str | bytes:
    if output_format == "json":
        return stdout

    if output_format == "markdown":
        return stdout

    if output_format == "html":
        return render_html_document(
            stdout,
            title=_document_title(
                envelope,
            ),
        )

    if output_format == "pdf":
        return _render_pdf(
            envelope,
            raw=raw,
            pdf_renderer=pdf_renderer,
        )

    raise ValueError("format must be one of: html, json, markdown, pdf")


def _render_pdf(
    envelope: WorkflowRenderEnvelope,
    *,
    raw: bool,
    pdf_renderer: PdfRenderer | None,
) -> bytes:
    markdown = _render_markdown(
        envelope,
        raw=raw,
    )
    if pdf_renderer is not None:
        return pdf_renderer(
            markdown,
        )

    if _is_professional_morning_report(
        envelope,
        raw=raw,
    ):
        document = MorningReportAssembler().assemble(
            envelope.to_dict(),
        )
        return MorningReportPdfRenderer().render(
            document,
        )

    return MarkdownPdfRenderer().render(
        markdown,
        title=_document_title(
            envelope,
        ),
    )


def _render_markdown(
    envelope: WorkflowRenderEnvelope,
    *,
    raw: bool,
) -> str:
    if _is_professional_morning_report(
        envelope,
        raw=raw,
    ):
        return _render_morning_report_markdown(
            envelope,
        )

    return render_workflow_output(
        envelope,
        "markdown",
    )


def _render_morning_report_markdown(
    envelope: WorkflowRenderEnvelope,
) -> str:
    document = MorningReportAssembler().assemble(
        envelope.to_dict(),
    )
    return MorningReportMarkdownRenderer().render(
        document,
    )


def _is_professional_morning_report(
    envelope: WorkflowRenderEnvelope,
    *,
    raw: bool,
) -> bool:
    return not raw and envelope.workflow_name == "morning_report"


def render_html_document(
    markdown: str,
    *,
    title: str,
) -> str:
    body = _render_basic_markdown_html(
        markdown,
    )
    escaped_title = escape(
        title,
    )

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escaped_title}</title>",
            "  <style>",
            "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem auto; max-width: 960px; line-height: 1.55; color: #17202a; }",
            "    h1, h2, h3 { color: #0b1f3a; }",
            "    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }",
            "    th, td { border: 1px solid #d5d8dc; padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }",
            "    th { background: #f4f6f7; }",
            "    code, pre { background: #f4f6f7; border-radius: 4px; }",
            "    pre { padding: 1rem; overflow-x: auto; }",
            "  </style>",
            "</head>",
            "<body>",
            body,
            "</body>",
            "</html>",
            "",
        ]
    )


def _render_basic_markdown_html(
    markdown: str,
) -> str:
    lines: list[str] = []
    in_unordered_list = False
    in_code_block = False
    code_lines: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                lines.append(
                    "<pre><code>"
                    + escape(
                        "\n".join(
                            code_lines,
                        )
                    )
                    + "</code></pre>"
                )
                code_lines = []
                in_code_block = False
            else:
                _close_list_if_needed(
                    lines,
                    in_unordered_list,
                )
                in_unordered_list = False
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(
                line,
            )
            continue

        if not stripped:
            _close_list_if_needed(
                lines,
                in_unordered_list,
            )
            in_unordered_list = False
            continue

        if stripped.startswith("# "):
            _close_list_if_needed(
                lines,
                in_unordered_list,
            )
            in_unordered_list = False
            lines.append(f"<h1>{escape(stripped[2:])}</h1>")
            continue

        if stripped.startswith("## "):
            _close_list_if_needed(
                lines,
                in_unordered_list,
            )
            in_unordered_list = False
            lines.append(f"<h2>{escape(stripped[3:])}</h2>")
            continue

        if stripped.startswith("### "):
            _close_list_if_needed(
                lines,
                in_unordered_list,
            )
            in_unordered_list = False
            lines.append(f"<h3>{escape(stripped[4:])}</h3>")
            continue

        if stripped.startswith("- "):
            if not in_unordered_list:
                lines.append("<ul>")
                in_unordered_list = True
            lines.append(f"  <li>{escape(stripped[2:])}</li>")
            continue

        if stripped.startswith("|"):
            _close_list_if_needed(
                lines,
                in_unordered_list,
            )
            in_unordered_list = False
            lines.append(f"<pre>{escape(stripped)}</pre>")
            continue

        _close_list_if_needed(
            lines,
            in_unordered_list,
        )
        in_unordered_list = False
        lines.append(f"<p>{escape(stripped)}</p>")

    if in_code_block:
        lines.append(
            "<pre><code>"
            + escape(
                "\n".join(
                    code_lines,
                )
            )
            + "</code></pre>"
        )

    _close_list_if_needed(
        lines,
        in_unordered_list,
    )
    return "\n".join(
        lines,
    )


def _close_list_if_needed(
    lines: list[str],
    in_unordered_list: bool,
) -> None:
    if in_unordered_list:
        lines.append("</ul>")


def _document_title(
    envelope: WorkflowRenderEnvelope,
) -> str:
    workflow_name = envelope.workflow_name or "workflow"
    execution_id = envelope.execution_id
    if execution_id:
        return f"{workflow_name} {execution_id}"

    return workflow_name
