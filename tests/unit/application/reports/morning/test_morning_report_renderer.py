from __future__ import annotations

import pytest

from application.reports import MorningReportAssembler, MorningReportMarkdownRenderer
from application.reports.morning_report_models import (
    MorningReportDocument,
    ReportBullet,
    ReportMetric,
    ReportSection,
    ReportTable,
    ReportTableRow,
)
from domain.llm import ReasoningTraceViolationError
from tests.unit.application.reports.morning.test_morning_report_assembler import (
    FULL_MACRO_LLM_RESPONSE,
    FULL_STRATEGY_LLM_RESPONSE,
    _complete_workflow_result,
)


def test_renderer_outputs_professional_sections_without_raw_runtime_json() -> None:
    document = MorningReportAssembler().assemble(
        _complete_workflow_result(),
    )

    rendered = MorningReportMarkdownRenderer().render(
        document,
    )

    assert "# Polaris Morning Financial Report" in rendered
    assert "## Executive Summary" in rendered
    assert "## Portfolio Snapshot" in rendered
    assert "## Macro / Fundamental Backdrop" in rendered
    assert "## Technical Setup" in rendered
    assert "Breadth Regime" in rendered
    assert "% Above 50DMA" in rendered
    assert "McClellan Oscillator" in rendered
    assert "Price / A-D Divergence" in rendered
    assert "## News & Sentiment" in rendered
    assert "## Risk Assessment" in rendered
    assert "## Recommended Action Plan" in rendered
    assert "## Run Status" in rendered

    assert FULL_MACRO_LLM_RESPONSE in rendered
    assert "END_OF_FULL_LLM_RESPONSE" in rendered
    assert FULL_STRATEGY_LLM_RESPONSE in rendered
    assert "Strategy Case Comparison" in rendered
    assert "Selected thesis" in rendered
    assert "Runtime Node Outputs" not in rendered
    assert "```json" not in rendered
    assert "node_outputs" not in rendered
    assert "SECRET_RAW_RUNTIME_VALUE" not in rendered


def test_renderer_includes_workflow_errors_in_human_report() -> None:
    document = MorningReportAssembler().assemble(
        {
            "workflow_name": "morning_report",
            "execution_id": "exec-error",
            "status": "failed",
            "summary": {
                "symbol": "SPY",
            },
            "error_message": "provider key missing",
            "errors": [
                {
                    "message": "technical data unavailable",
                    "node_name": "technical_agent",
                    "error_type": "DataUnavailable",
                }
            ],
        }
    )

    rendered = MorningReportMarkdownRenderer().render(
        document,
    )

    assert "### Errors" in rendered
    assert "provider key missing" in rendered
    assert "technical data unavailable" in rendered


def test_renderer_strips_reasoning_traces_from_publication_markdown() -> None:
    section = ReportSection(
        title="Executive Summary",
        summary="<think>private deliberation</think>\nVisible summary.",
        metrics=(
            ReportMetric(
                label="Confidence",
                value="82.0%",
                note="```reasoning\nhidden note\n```\nSource-backed note.",
            ),
        ),
        bullets=(
            ReportBullet(
                text="<thinking>hidden bullet</thinking>\nVisible bullet.",
                label="Posture",
            ),
        ),
        risks=(
            ReportBullet(
                text="Chain of thought: internal risk trace.\n"
                "Final answer: Watch liquidity.",
            ),
        ),
        recommendations=(
            ReportBullet(
                text="```scratchpad\nprivate action plan\n```\nKeep evidence attached.",
            ),
        ),
        tables=(
            ReportTable(
                title="Evidence Table",
                rows=(
                    ReportTableRow(
                        label="Source",
                        value="Curated report",
                        note=(
                            "<reasoning>hidden table note</reasoning>\n"
                            "Retrieved evidence."
                        ),
                    ),
                ),
            ),
        ),
    )

    rendered = MorningReportMarkdownRenderer().render(
        _document_with_section(section),
    )

    assert "Visible summary." in rendered
    assert "Source-backed note." in rendered
    assert "Visible bullet." in rendered
    assert "Watch liquidity." in rendered
    assert "Keep evidence attached." in rendered
    assert "Retrieved evidence." in rendered
    assert "private deliberation" not in rendered
    assert "hidden note" not in rendered
    assert "hidden bullet" not in rendered
    assert "internal risk trace" not in rendered
    assert "private action plan" not in rendered
    assert "hidden table note" not in rendered
    assert "<think" not in rendered
    assert "```reasoning" not in rendered


def test_renderer_rejects_unsafe_reasoning_trace_before_publication() -> None:
    section = ReportSection(
        title="Executive Summary",
        summary="<think>private deliberation without a closing tag",
    )

    with pytest.raises(ReasoningTraceViolationError, match="morning_report.markdown"):
        MorningReportMarkdownRenderer().render(
            _document_with_section(section),
        )


def _document_with_section(section: ReportSection) -> MorningReportDocument:
    unavailable = ReportSection.unavailable("Unavailable")
    return MorningReportDocument(
        title="Polaris Morning Financial Report",
        subtitle="Decision-support report for SPY",
        symbol="SPY",
        execution_id="exec-safe",
        generated_at="2026-07-20T13:30:00Z",
        status="succeeded",
        executive_summary=section,
        portfolio_snapshot=unavailable,
        macro_backdrop=unavailable,
        technical_setup=unavailable,
        news_sentiment=unavailable,
        risk_assessment=unavailable,
        recommended_action_plan=unavailable,
    )
