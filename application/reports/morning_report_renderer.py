from __future__ import annotations

from application.reports.morning_report_models import MorningReportDocument
from application.reports.morning_report_models import ReportBullet
from application.reports.morning_report_models import ReportMetric
from application.reports.morning_report_models import ReportSection
from application.reports.morning_report_models import ReportTable


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
        lines: list[str] = []

        lines.extend(
            self._render_header(
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
        cleaned = summary.strip()
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
        return value.strip()

    def _escape_text(
        self,
        value: str,
    ) -> str:
        return " ".join(
            value.split(),
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
