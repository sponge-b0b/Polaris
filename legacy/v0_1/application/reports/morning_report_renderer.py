from __future__ import annotations

from typing import cast

from application.reports.authority import (
    ensure_report_publication_authority,
    report_authority_metadata,
)
from application.reports.morning_report_models import (
    MorningReportDocument,
    ReportBullet,
    ReportMetric,
    ReportSection,
    ReportTable,
)
from domain.llm import sanitize_reasoning_trace_text_for_boundary


class MorningReportMarkdownRenderer:
    """
    Render a typed morning report document as professional markdown.

    This renderer intentionally consumes only typed report objects. It does not
    render runtime node payloads, execution metadata dumps, or raw JSON.
    """

    def render(
        self,
        document: MorningReportDocument,
    ) -> str:
        ensure_report_publication_authority(
            contract=document.authority,
            content_texts=self._document_text_values(
                document,
            ),
            boundary_name="morning_report.markdown",
        )
        lines: list[str] = []

        lines.extend(
            self._render_header(
                document,
            )
        )
        lines.extend(
            self._render_authority_boundary(
                document,
            )
        )
        lines.extend(
            self._render_section(
                document.executive_summary,
            )
        )
        lines.extend(
            self._render_section(
                document.portfolio_snapshot,
            )
        )
        lines.extend(
            self._render_section(
                document.macro_backdrop,
            )
        )
        lines.extend(
            self._render_section(
                document.technical_setup,
            )
        )
        lines.extend(
            self._render_section(
                document.news_sentiment,
            )
        )
        lines.extend(
            self._render_section(
                document.risk_assessment,
            )
        )
        lines.extend(
            self._render_section(
                document.recommended_action_plan,
            )
        )
        lines.extend(
            self._render_run_status(
                document,
            )
        )

        return self._clean_output(
            lines,
        )

    def _render_header(
        self,
        document: MorningReportDocument,
    ) -> list[str]:
        return [
            f"# {self._escape_text(document.title)}",
            "",
            f"_{self._escape_text(document.subtitle)}_",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Symbol | {self._escape_cell(document.symbol)} |",
            f"| Generated At | {self._escape_cell(document.generated_at)} |",
            f"| Execution ID | `{self._escape_cell(document.execution_id)}` |",
            f"| Workflow Status | {self._escape_cell(document.status)} |",
            "",
        ]

    def _render_authority_boundary(
        self,
        document: MorningReportDocument,
    ) -> list[str]:
        authority = report_authority_metadata(
            document.authority,
        )
        risk_authority_value = authority["risk_authority"]
        if isinstance(
            risk_authority_value,
            dict,
        ):
            risk_authority = cast(
                "dict[object, object]",
                risk_authority_value,
            )
        else:
            risk_authority = {}

        lines = [
            "## Authority Boundary",
            "",
            "This report is non-authoritative decision support. It is not a "
            "portfolio, strategy, governance, readiness, or execution decision.",
            "",
            "### Classification",
            "",
            "| Field | Value |",
            "| --- | --- |",
            self._authority_table_row(
                "Risk Tier",
                risk_authority,
                "risk_tier",
            ),
            self._authority_table_row(
                "Intended Sink",
                risk_authority,
                "intended_sink",
            ),
            self._authority_table_row(
                "Authority Effect",
                risk_authority,
                "authority_effect",
            ),
            self._authority_table_row(
                "Source of Truth",
                risk_authority,
                "source_of_truth",
            ),
            self._authority_table_row(
                "Canonical Owner",
                risk_authority,
                "canonical_owner",
            ),
            self._authority_table_row(
                "Evidence Sufficient",
                risk_authority,
                "evidence_sufficient",
            ),
            "",
            "### Provenance and Limitations",
            "",
            f"- Workflow execution: `{self._escape_text(document.execution_id)}`.",
            f"- Workflow status: {self._escape_text(document.status)}.",
            f"- Generated at: {self._escape_text(document.generated_at)}.",
        ]
        for limitation in document.authority_limitations:
            lines.append(f"- {self._escape_text(limitation)}")
        lines.append(
            "",
        )
        return lines

    def _authority_table_row(
        self,
        label: str,
        risk_authority: dict[object, object],
        key: str,
    ) -> str:
        value = risk_authority.get(
            key,
            "unknown",
        )
        return f"| {label} | {self._escape_cell(str(value))} |"

    def _render_section(
        self,
        section: ReportSection,
    ) -> list[str]:
        lines = [
            f"## {self._escape_text(section.title)}",
            "",
        ]

        if section.summary:
            lines.extend(
                self._render_summary(
                    section.summary,
                )
            )

        if section.metrics:
            lines.extend(
                self._render_metrics(
                    section.metrics,
                )
            )

        if section.bullets:
            lines.extend(
                self._render_bullets(
                    "Key Observations",
                    section.bullets,
                )
            )

        if section.risks:
            lines.extend(
                self._render_bullets(
                    "Risks / Watch Items",
                    section.risks,
                )
            )

        if section.recommendations:
            lines.extend(
                self._render_bullets(
                    "Decision Support",
                    section.recommendations,
                )
            )

        for table in section.tables:
            lines.extend(
                self._render_table(
                    table,
                )
            )

        return lines

    def _render_summary(
        self,
        summary: str,
    ) -> list[str]:
        cleaned = self._preserve_text(
            summary,
        )
        if not cleaned:
            return []

        return [
            cleaned,
            "",
        ]

    def _render_metrics(
        self,
        metrics: tuple[ReportMetric, ...],
    ) -> list[str]:
        lines = [
            "| Metric | Value | Note |",
            "| --- | ---: | --- |",
        ]
        for metric in metrics:
            lines.append(
                "| "
                f"{self._escape_cell(metric.label)} | "
                f"{self._escape_cell(metric.value)} | "
                f"{self._escape_cell(metric.note or '')} |"
            )

        lines.append(
            "",
        )
        return lines

    def _render_table(
        self,
        table: ReportTable,
    ) -> list[str]:
        if not table.rows:
            return []

        lines = [
            f"### {self._escape_text(table.title)}",
            "",
            "| Item | Value | Note |",
            "| --- | ---: | --- |",
        ]
        for row in table.rows:
            lines.append(
                "| "
                f"{self._escape_cell(row.label)} | "
                f"{self._escape_cell(row.value)} | "
                f"{self._escape_cell(row.note or '')} |"
            )

        lines.append(
            "",
        )
        return lines

    def _render_bullets(
        self,
        title: str,
        bullets: tuple[ReportBullet, ...],
    ) -> list[str]:
        lines = [
            f"### {title}",
            "",
        ]
        for bullet in bullets:
            text = self._preserve_text(
                bullet.text,
            )
            if bullet.label:
                label = self._escape_text(
                    bullet.label,
                )
                lines.append(f"- **{label}:** {text}")
            else:
                lines.append(f"- {text}")

        lines.append(
            "",
        )
        return lines

    def _render_run_status(
        self,
        document: MorningReportDocument,
    ) -> list[str]:
        lines = [
            "## Run Status",
            "",
            "The workflow result was converted into a human-readable financial report. "
            "Raw runtime node output is intentionally omitted from this view.",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Execution ID | `{self._escape_cell(document.execution_id)}` |",
            f"| Status | {self._escape_cell(document.status)} |",
            f"| Generated At | {self._escape_cell(document.generated_at)} |",
            "",
        ]

        if document.run_errors:
            lines.extend(
                [
                    "### Errors",
                    "",
                ]
            )
            for error in document.run_errors:
                lines.append(f"- {self._escape_text(error)}")
            lines.append(
                "",
            )

        return lines

    def _document_text_values(
        self,
        document: MorningReportDocument,
    ) -> tuple[str, ...]:
        values = [
            document.title,
            document.subtitle,
            document.symbol,
            document.execution_id,
            document.generated_at,
            document.status,
            *document.run_errors,
        ]
        for section in (
            document.executive_summary,
            document.portfolio_snapshot,
            document.macro_backdrop,
            document.technical_setup,
            document.news_sentiment,
            document.risk_assessment,
            document.recommended_action_plan,
        ):
            values.extend(
                self._section_text_values(
                    section,
                )
            )
        if document.appendix is not None:
            values.extend(
                self._section_text_values(
                    document.appendix,
                )
            )
        return tuple(value for value in values if value)

    def _section_text_values(
        self,
        section: ReportSection,
    ) -> tuple[str, ...]:
        values = [
            section.title,
            section.summary,
        ]
        for metric in section.metrics:
            values.extend((metric.label, metric.value, metric.note or ""))
        for bullet in (
            *section.bullets,
            *section.risks,
            *section.recommendations,
        ):
            values.extend((bullet.label or "", bullet.text))
        for table in section.tables:
            values.append(table.title)
            for row in table.rows:
                values.extend((row.label, row.value, row.note or ""))
        return tuple(value for value in values if value)

    def _clean_output(
        self,
        lines: list[str],
    ) -> str:
        while lines and lines[-1] == "":
            lines.pop()

        return (
            "\n".join(
                lines,
            )
            + "\n"
        )

    def _preserve_text(
        self,
        value: str,
    ) -> str:
        return sanitize_reasoning_trace_text_for_boundary(
            value,
            boundary_name="morning_report.markdown",
        )

    def _escape_text(
        self,
        value: str,
    ) -> str:
        safe_value = sanitize_reasoning_trace_text_for_boundary(
            value,
            boundary_name="morning_report.markdown",
        )
        return " ".join(
            safe_value.split(),
        )

    def _escape_cell(
        self,
        value: str,
    ) -> str:
        return self._escape_text(
            value,
        ).replace(
            "|",
            "\\|",
        )
