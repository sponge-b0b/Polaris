from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from typing import cast
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from application.reports import (
    MorningReportDocument,
    ReportBullet,
    ReportSection,
    ReportTable,
)


class MorningReportPdfRenderer:
    """
    Render a typed morning report document as a PDF artifact.
    """

    def render(
        self,
        document: MorningReportDocument,
    ) -> bytes:
        story: list[Flowable] = []
        styles = _pdf_styles()

        story.append(
            Paragraph(
                escape(
                    document.title,
                ),
                styles["Title"],
            )
        )
        story.append(
            Paragraph(
                escape(
                    document.subtitle,
                ),
                styles["Subtitle"],
            )
        )
        story.append(
            Spacer(
                1,
                0.15 * inch,
            )
        )
        story.append(
            _metadata_table(
                [
                    (
                        "Symbol",
                        document.symbol,
                    ),
                    (
                        "Generated At",
                        document.generated_at,
                    ),
                    (
                        "Execution ID",
                        document.execution_id,
                    ),
                    (
                        "Workflow Status",
                        document.status,
                    ),
                ],
                styles,
            )
        )

        for section in _document_sections(
            document,
        ):
            story.extend(
                _section_flowables(
                    section,
                    styles,
                )
            )

        story.extend(
            _run_status_flowables(
                document,
                styles,
            )
        )

        return _build_pdf(
            story,
        )


class MarkdownPdfRenderer:
    """
    Minimal generic markdown-to-PDF renderer for workflow fallbacks.
    """

    def render(
        self,
        markdown: str,
        *,
        title: str = "Workflow Report",
    ) -> bytes:
        styles = _pdf_styles()
        story = _markdown_pdf_story(
            markdown=markdown,
            title=title,
            styles=styles,
        )
        return _build_pdf(story)


def _markdown_pdf_story(
    *,
    markdown: str,
    title: str,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    story: list[Flowable] = []
    in_code_block = False
    code_lines: list[str] = []
    bullet_items: list[str] = []

    if not markdown.strip():
        story.append(Paragraph(escape(title), styles["Title"]))

    for raw_line in markdown.splitlines():
        in_code_block = _append_markdown_pdf_line(
            story=story,
            styles=styles,
            line=raw_line.rstrip(),
            in_code_block=in_code_block,
            code_lines=code_lines,
            bullet_items=bullet_items,
        )

    _flush_markdown_pdf_bullets(
        story=story,
        styles=styles,
        bullet_items=bullet_items,
    )
    _flush_markdown_pdf_code(
        story=story,
        styles=styles,
        code_lines=code_lines,
    )
    return story


def _append_markdown_pdf_line(
    *,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    line: str,
    in_code_block: bool,
    code_lines: list[str],
    bullet_items: list[str],
) -> bool:
    stripped = line.strip()

    if stripped.startswith("```"):
        return _toggle_markdown_pdf_code_block(
            story=story,
            styles=styles,
            in_code_block=in_code_block,
            code_lines=code_lines,
            bullet_items=bullet_items,
        )
    if in_code_block:
        code_lines.append(line)
        return True
    if not stripped:
        _flush_markdown_pdf_bullets(
            story=story,
            styles=styles,
            bullet_items=bullet_items,
        )
        return False
    if _append_markdown_pdf_heading(story, styles, stripped, bullet_items):
        return False
    if stripped.startswith("- "):
        bullet_items.append(stripped[2:])
        return False

    _flush_markdown_pdf_bullets(story=story, styles=styles, bullet_items=bullet_items)
    style_name = "Code" if stripped.startswith("|") else "BodyText"
    story.append(Paragraph(escape(stripped), styles[style_name]))
    return False


def _toggle_markdown_pdf_code_block(
    *,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    in_code_block: bool,
    code_lines: list[str],
    bullet_items: list[str],
) -> bool:
    if in_code_block:
        _flush_markdown_pdf_code(
            story=story,
            styles=styles,
            code_lines=code_lines,
        )
        return False

    _flush_markdown_pdf_bullets(
        story=story,
        styles=styles,
        bullet_items=bullet_items,
    )
    return True


def _append_markdown_pdf_heading(
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    stripped: str,
    bullet_items: list[str],
) -> bool:
    heading = _markdown_pdf_heading(stripped)
    if heading is None:
        return False

    text, style_name, spacer_height = heading
    _flush_markdown_pdf_bullets(story=story, styles=styles, bullet_items=bullet_items)
    if spacer_height is not None:
        story.append(Spacer(1, spacer_height))
    story.append(Paragraph(escape(text), styles[style_name]))
    return True


def _markdown_pdf_heading(stripped: str) -> tuple[str, str, float | None] | None:
    if stripped.startswith("# "):
        return stripped[2:], "Title", None
    if stripped.startswith("## "):
        return stripped[3:], "Heading2", 0.12 * inch
    if stripped.startswith("### "):
        return stripped[4:], "Heading3", None
    return None


def _flush_markdown_pdf_bullets(
    *,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    bullet_items: list[str],
) -> None:
    if not bullet_items:
        return

    story.append(_bullet_list(bullet_items, styles))
    bullet_items.clear()


def _flush_markdown_pdf_code(
    *,
    story: list[Flowable],
    styles: dict[str, ParagraphStyle],
    code_lines: list[str],
) -> None:
    if not code_lines:
        return

    story.append(
        Paragraph(
            escape("\n".join(code_lines)).replace("\n", "<br/>"),
            styles["Code"],
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    code_lines.clear()


def _document_sections(
    document: MorningReportDocument,
) -> tuple[ReportSection, ...]:
    return (
        document.executive_summary,
        document.portfolio_snapshot,
        document.macro_backdrop,
        document.technical_setup,
        document.news_sentiment,
        document.risk_assessment,
        document.recommended_action_plan,
    )


def _section_flowables(
    section: ReportSection,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    flowables: list[Flowable] = [
        Spacer(
            1,
            0.18 * inch,
        ),
        Paragraph(
            escape(
                section.title,
            ),
            styles["Heading2"],
        ),
    ]

    if section.summary.strip():
        flowables.extend(
            _paragraphs_from_text(
                section.summary,
                styles,
            )
        )

    if section.metrics:
        flowables.append(
            _metadata_table(
                [
                    (
                        metric.label,
                        metric.value,
                        metric.note or "",
                    )
                    for metric in section.metrics
                ],
                styles,
                headers=(
                    "Metric",
                    "Value",
                    "Note",
                ),
            )
        )

    flowables.extend(
        _bullet_group(
            "Key Observations",
            section.bullets,
            styles,
        )
    )
    flowables.extend(
        _bullet_group(
            "Risks / Watch Items",
            section.risks,
            styles,
        )
    )
    flowables.extend(
        _bullet_group(
            "Decision Support",
            section.recommendations,
            styles,
        )
    )

    for table in section.tables:
        flowables.extend(
            _report_table_flowables(
                table,
                styles,
            )
        )

    return flowables


def _run_status_flowables(
    document: MorningReportDocument,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    flowables: list[Flowable] = [
        Spacer(
            1,
            0.18 * inch,
        ),
        Paragraph(
            "Run Status",
            styles["Heading2"],
        ),
        _metadata_table(
            [
                (
                    "Execution ID",
                    document.execution_id,
                ),
                (
                    "Status",
                    document.status,
                ),
                (
                    "Generated At",
                    document.generated_at,
                ),
            ],
            styles,
        ),
    ]

    if document.run_errors:
        flowables.append(
            Paragraph(
                "Errors",
                styles["Heading3"],
            )
        )
        flowables.append(
            _bullet_list(
                document.run_errors,
                styles,
            )
        )

    return flowables


def _bullet_group(
    title: str,
    bullets: tuple[ReportBullet, ...],
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    if not bullets:
        return []

    return [
        Paragraph(
            escape(
                title,
            ),
            styles["Heading3"],
        ),
        _bullet_list(
            [
                f"{bullet.label}: {bullet.text}" if bullet.label else bullet.text
                for bullet in bullets
            ],
            styles,
        ),
    ]


def _report_table_flowables(
    table: ReportTable,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    if not table.rows:
        return []

    return [
        Paragraph(
            escape(
                table.title,
            ),
            styles["Heading3"],
        ),
        _metadata_table(
            [
                (
                    row.label,
                    row.value,
                    row.note or "",
                )
                for row in table.rows
            ],
            styles,
            headers=(
                "Item",
                "Value",
                "Note",
            ),
        ),
    ]


def _paragraphs_from_text(
    text: str,
    styles: dict[str, ParagraphStyle],
) -> list[Flowable]:
    flowables: list[Flowable] = []
    for paragraph in text.split(
        "\n\n",
    ):
        cleaned = paragraph.strip()
        if not cleaned:
            continue
        flowables.append(
            Paragraph(
                escape(
                    cleaned,
                ).replace(
                    "\n",
                    "<br/>",
                ),
                styles["BodyText"],
            )
        )
        flowables.append(
            Spacer(
                1,
                0.08 * inch,
            )
        )

    return flowables


def _bullet_list(
    items: Iterable[str],
    styles: dict[str, ParagraphStyle],
) -> ListFlowable:
    list_items = [
        cast(
            Flowable,
            ListItem(
                Paragraph(
                    escape(
                        item,
                    ),
                    styles["BodyText"],
                ),
            ),
        )
        for item in items
    ]
    return ListFlowable(
        list_items,
        bulletType="bullet",
        leftIndent=0.25 * inch,
    )


def _metadata_table(
    rows: list[tuple[str, ...]],
    styles: dict[str, ParagraphStyle],
    *,
    headers: tuple[str, ...] = (
        "Field",
        "Value",
    ),
) -> Table:
    data: list[list[Paragraph]] = [
        [
            Paragraph(
                escape(
                    header,
                ),
                styles["TableHeader"],
            )
            for header in headers
        ]
    ]
    data.extend(
        [
            Paragraph(
                escape(
                    cell,
                ),
                styles["TableCell"],
            )
            for cell in row
        ]
        for row in rows
    )

    table = Table(
        data,
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        0,
                    ),
                    colors.HexColor(
                        "#f4f6f7",
                    ),
                ),
                (
                    "TEXTCOLOR",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        0,
                    ),
                    colors.HexColor(
                        "#0b1f3a",
                    ),
                ),
                (
                    "GRID",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    0.35,
                    colors.HexColor(
                        "#d5d8dc",
                    ),
                ),
                (
                    "VALIGN",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    6,
                ),
            ]
        )
    )
    return table


def _build_pdf(
    story: list[Flowable],
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="Polaris Workflow Report",
    )
    doc.build(
        story,
    )
    return buffer.getvalue()


def _pdf_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    styles = {
        "Title": cast(ParagraphStyle, sample["Title"]),
        "Subtitle": ParagraphStyle(
            "Subtitle",
            parent=cast(ParagraphStyle, sample["BodyText"]),
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(
                "#566573",
            ),
            spaceAfter=10,
        ),
        "Heading2": cast(ParagraphStyle, sample["Heading2"]),
        "Heading3": cast(ParagraphStyle, sample["Heading3"]),
        "BodyText": cast(ParagraphStyle, sample["BodyText"]),
        "Code": ParagraphStyle(
            "Code",
            parent=cast(ParagraphStyle, sample["Code"]),
            fontName="Courier",
            fontSize=7,
            leading=9,
            backColor=colors.HexColor(
                "#f4f6f7",
            ),
            borderPadding=4,
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=cast(ParagraphStyle, sample["BodyText"]),
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=cast(ParagraphStyle, sample["BodyText"]),
            fontSize=8,
            leading=10,
        ),
    }
    return styles
