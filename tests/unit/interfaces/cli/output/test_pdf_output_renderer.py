from __future__ import annotations

from application.reports.morning_report_models import MorningReportDocument
from application.reports.morning_report_models import ReportBullet
from application.reports.morning_report_models import ReportMetric
from application.reports.morning_report_models import ReportSection
from application.reports.morning_report_models import ReportTable
from application.reports.morning_report_models import ReportTableRow
from interfaces.cli.output import MarkdownPdfRenderer
from interfaces.cli.output import MorningReportPdfRenderer


def test_markdown_pdf_renderer_produces_pdf_bytes() -> None:
    pdf = MarkdownPdfRenderer().render(
        "# Workflow Report\n\n## Summary\n\n- Completed successfully",
    )

    assert pdf.startswith(
        b"%PDF",
    )
    assert (
        len(
            pdf,
        )
        > 100
    )


def test_morning_report_pdf_renderer_produces_pdf_bytes_from_typed_document() -> None:
    pdf = MorningReportPdfRenderer().render(
        _document(),
    )

    assert pdf.startswith(
        b"%PDF",
    )
    assert (
        len(
            pdf,
        )
        > 100
    )


def _document() -> MorningReportDocument:
    section = ReportSection(
        title="Executive Summary",
        summary="Markets are constructive but risk-aware.",
        metrics=(
            ReportMetric(
                label="Confidence",
                value="82.0%",
            ),
        ),
        bullets=(
            ReportBullet(
                label="Bias",
                text="Constructive risk posture.",
            ),
        ),
    )
    portfolio_section = ReportSection(
        title="Portfolio Snapshot",
        summary="Portfolio is long-biased with moderate margin utilization.",
        metrics=(
            ReportMetric(
                label="Margin Utilization",
                value="34.0%",
            ),
        ),
        tables=(
            ReportTable(
                title="Portfolio Risk & Constraints",
                rows=(
                    ReportTableRow(
                        label="Account Restrictions",
                        value="None",
                    ),
                ),
            ),
        ),
    )

    return MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision support only.",
        symbol="SPY",
        execution_id="exec-pdf",
        generated_at="2026-05-27T08:30:12Z",
        status="Succeeded",
        executive_summary=section,
        portfolio_snapshot=portfolio_section,
        macro_backdrop=section,
        technical_setup=section,
        news_sentiment=section,
        risk_assessment=section,
        recommended_action_plan=section,
    )
