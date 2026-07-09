from __future__ import annotations

from application.reports import MorningReportAssembler
from application.reports import MorningReportMarkdownRenderer

from tests.unit.application.reports.morning.test_morning_report_assembler import (
    FULL_MACRO_LLM_RESPONSE,
)
from tests.unit.application.reports.morning.test_morning_report_assembler import (
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
