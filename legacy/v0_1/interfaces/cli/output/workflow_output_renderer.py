from __future__ import annotations

from collections.abc import Callable
from html import escape
from pathlib import Path

from application.reports import MorningReportAssembler, MorningReportMarkdownRenderer
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.output.pdf_output_renderer import (
    MarkdownPdfRenderer,
    MorningReportPdfRenderer,
)
from interfaces.cli.output.workflow_output import (
    CliOutputFormat,
    WorkflowOutputArtifact,
    WorkflowOutputBundle,
    output_path_for_format,
)
from interfaces.cli.rendering.workflow_rendering import (
    WorkflowRenderEnvelope,
    render_workflow_output,
)

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
            (
                "    body { font-family: -apple-system, BlinkMacSystemFont, "
                "'Segoe UI', sans-serif; margin: 2rem auto; max-width: 960px; "
                "line-height: 1.55; color: #17202a; }"
            ),
            "    h1, h2, h3 { color: #0b1f3a; }",
            "    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }",
            "    th, td { border: 1px solid #d5d8dc; padding: 0.45rem 0.6rem; "
            "text-align: left; vertical-align: top; }",
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
        in_unordered_list, in_code_block = _append_basic_markdown_html_line(
            lines=lines,
            line=raw_line.rstrip(),
            in_unordered_list=in_unordered_list,
            in_code_block=in_code_block,
            code_lines=code_lines,
        )

    if in_code_block:
        _append_code_block(lines, code_lines)

    _close_list_if_needed(lines, in_unordered_list)
    return "\n".join(lines)


def _append_basic_markdown_html_line(
    *,
    lines: list[str],
    line: str,
    in_unordered_list: bool,
    in_code_block: bool,
    code_lines: list[str],
) -> tuple[bool, bool]:
    stripped = line.strip()

    if stripped.startswith("```"):
        return _toggle_basic_markdown_code_block(
            lines=lines,
            in_unordered_list=in_unordered_list,
            in_code_block=in_code_block,
            code_lines=code_lines,
        )
    if in_code_block:
        code_lines.append(line)
        return in_unordered_list, True
    if not stripped:
        _close_list_if_needed(lines, in_unordered_list)
        return False, False
    if _append_basic_markdown_heading(lines, stripped, in_unordered_list):
        return False, False
    if stripped.startswith("- "):
        if not in_unordered_list:
            lines.append("<ul>")
        lines.append(f"  <li>{escape(stripped[2:])}</li>")
        return True, False

    _close_list_if_needed(lines, in_unordered_list)
    lines.append(_basic_markdown_block(stripped))
    return False, False


def _toggle_basic_markdown_code_block(
    *,
    lines: list[str],
    in_unordered_list: bool,
    in_code_block: bool,
    code_lines: list[str],
) -> tuple[bool, bool]:
    if in_code_block:
        _append_code_block(lines, code_lines)
        code_lines.clear()
        return in_unordered_list, False

    _close_list_if_needed(lines, in_unordered_list)
    return False, True


def _append_basic_markdown_heading(
    lines: list[str],
    stripped: str,
    in_unordered_list: bool,
) -> bool:
    heading = _basic_markdown_heading(stripped)
    if heading is None:
        return False

    _close_list_if_needed(lines, in_unordered_list)
    level, text = heading
    lines.append(f"<h{level}>{escape(text)}</h{level}>")
    return True


def _basic_markdown_heading(stripped: str) -> tuple[int, str] | None:
    if stripped.startswith("# "):
        return 1, stripped[2:]
    if stripped.startswith("## "):
        return 2, stripped[3:]
    if stripped.startswith("### "):
        return 3, stripped[4:]
    return None


def _basic_markdown_block(stripped: str) -> str:
    if stripped.startswith("|"):
        return f"<pre>{escape(stripped)}</pre>"
    return f"<p>{escape(stripped)}</p>"


def _append_code_block(lines: list[str], code_lines: list[str]) -> None:
    lines.append("<pre><code>" + escape("\n".join(code_lines)) + "</code></pre>")


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
