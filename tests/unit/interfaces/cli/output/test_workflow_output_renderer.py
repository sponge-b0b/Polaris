from __future__ import annotations

import json
from pathlib import Path

from interfaces.cli.output import render_workflow_output_bundle
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope


def test_default_morning_report_stdout_uses_professional_report() -> None:
    bundle = render_workflow_output_bundle(
        _morning_report_envelope(),
        output_format=None,
    )

    assert bundle.artifact is None
    assert "# Polaris Morning Financial Report" in bundle.stdout
    assert "Runtime Node Outputs:" not in bundle.stdout
    _assert_v2_portfolio_report_fields(
        bundle.stdout,
    )


def test_morning_report_markdown_artifact_includes_v2_portfolio_fields() -> None:
    bundle = render_workflow_output_bundle(
        _morning_report_envelope(),
        output_format="markdown",
        output_path=Path(
            "morning_report.md",
        ),
    )

    assert bundle.artifact is not None
    assert bundle.artifact.content == bundle.stdout
    _assert_v2_portfolio_report_fields(
        bundle.stdout,
    )


def test_morning_report_html_artifact_includes_v2_portfolio_fields() -> None:
    bundle = render_workflow_output_bundle(
        _morning_report_envelope(),
        output_format="html",
        output_path=Path(
            "morning_report.html",
        ),
    )

    assert bundle.artifact is not None
    assert isinstance(
        bundle.artifact.content,
        str,
    )
    assert "<html" in bundle.artifact.content
    _assert_v2_portfolio_report_fields(
        bundle.stdout,
    )
    _assert_v2_portfolio_report_fields(
        bundle.artifact.content,
    )


def test_default_generic_stdout_uses_console_rendering_without_artifact() -> None:
    bundle = render_workflow_output_bundle(
        _generic_envelope(),
        output_format=None,
    )

    assert bundle.artifact is None
    assert "Workflow: generic_workflow" in bundle.stdout
    assert "Runtime Node Outputs:" in bundle.stdout
    assert "# generic_workflow" not in bundle.stdout


def test_json_output_uses_same_pretty_json_for_stdout_and_artifact() -> None:
    bundle = render_workflow_output_bundle(
        _generic_envelope(),
        output_format="json",
        output_path=Path(
            "workflow.json",
        ),
    )

    assert bundle.artifact is not None
    assert bundle.artifact.content == bundle.stdout
    assert bundle.artifact.path == Path(
        "workflow.json",
    )
    assert (
        json.loads(
            bundle.stdout,
        )["workflow_name"]
        == "generic_workflow"
    )


def test_markdown_output_uses_same_markdown_for_stdout_and_artifact() -> None:
    bundle = render_workflow_output_bundle(
        _generic_envelope(),
        output_format="markdown",
        output_path=Path(
            "workflow.md",
        ),
    )

    assert bundle.artifact is not None
    assert bundle.artifact.content == bundle.stdout
    assert bundle.artifact.path == Path(
        "workflow.md",
    )
    assert "# generic_workflow" in bundle.stdout


def test_html_output_writes_html_but_prints_readable_markdown() -> None:
    bundle = render_workflow_output_bundle(
        _generic_envelope(),
        output_format="html",
        output_path=Path(
            "workflow.html",
        ),
    )

    assert bundle.artifact is not None
    assert "<html" not in bundle.stdout
    assert "# generic_workflow" in bundle.stdout
    assert isinstance(
        bundle.artifact.content,
        str,
    )
    assert "<html" in bundle.artifact.content
    assert "generic_workflow" in bundle.artifact.content


def test_pdf_output_prints_text_and_uses_pdf_renderer_for_bytes() -> None:
    bundle = render_workflow_output_bundle(
        _generic_envelope(),
        output_format="pdf",
        output_path=Path(
            "workflow.pdf",
        ),
        pdf_renderer=lambda markdown: b"%PDF-" + markdown[:10].encode(),
    )

    assert bundle.artifact is not None
    assert "# generic_workflow" in bundle.stdout
    assert not bundle.stdout.startswith(
        "%PDF",
    )
    assert isinstance(
        bundle.artifact.content,
        bytes,
    )
    assert bundle.artifact.content.startswith(
        b"%PDF-",
    )


def _morning_report_envelope() -> WorkflowRenderEnvelope:
    return WorkflowRenderEnvelope(
        workflow_name="morning_report",
        execution_id="exec-report",
        success=True,
        status="succeeded",
        payload={
            "workflow_inputs": {
                "symbol": "SPY",
            },
            "node_outputs": {
                "portfolio_state_builder": {
                    "success": True,
                    "outputs": {
                        "confidence": 0.77,
                        "regime": "balanced",
                        "features": {
                            "portfolio_state": {
                                "portfolio_value": 1_000_000,
                                "cash": 250_000,
                                "cash_ratio": 0.25,
                                "cash_pct": 0.25,
                                "realized_pnl_pct": 0.037,
                                "unrealized_pnl_pct": 0.024,
                                "unrealized_intraday_pnl": 1250.55,
                                "unrealized_intraday_pnl_pct": 0.0013,
                                "pnl_total_pct": 0.061,
                                "long_market_value": 720_000,
                                "short_market_value": 80_000,
                                "gross_market_value": 800_000,
                                "net_market_value": 640_000,
                                "gross_exposure": 0.72,
                                "net_exposure": 0.64,
                                "long_exposure": 0.72,
                                "short_exposure": 0.08,
                                "leverage": 1.21,
                                "largest_position_pct": 0.18,
                                "concentration_score": 0.31,
                                "diversification_score": 0.69,
                                "beta_exposure": 1.08,
                                "beta_risk": 0.42,
                                "portfolio_heat": 0.46,
                                "risk_intensity": 0.41,
                                "margin_utilization_ratio": 0.34,
                                "account_health": "healthy",
                                "trading_blocked": False,
                                "transfers_blocked": False,
                                "account_blocked": False,
                                "trade_suspended_by_user": False,
                                "pattern_day_trader": False,
                                "portfolio_regime": "balanced",
                                "directional_bias": "long_bias",
                            },
                            "equity_state": {
                                "drawdown_percent": 0.035,
                            },
                            "positions_state": {
                                "position_count": 8,
                            },
                        },
                    },
                },
            },
        },
        raw_result={
            "workflow_name": "morning_report",
            "execution_id": "exec-report",
        },
    )


def _generic_envelope() -> WorkflowRenderEnvelope:
    return WorkflowRenderEnvelope(
        workflow_name="generic_workflow",
        execution_id="exec-generic",
        success=True,
        status="succeeded",
        payload={
            "node_outputs": {
                "example_node": {
                    "outputs": {
                        "value": 42,
                    },
                },
            },
        },
        raw_result={
            "workflow_name": "generic_workflow",
            "execution_id": "exec-generic",
        },
    )


def test_pdf_output_uses_default_reportlab_renderer_when_not_injected() -> None:
    bundle = render_workflow_output_bundle(
        _generic_envelope(),
        output_format="pdf",
        output_path=Path(
            "workflow.pdf",
        ),
    )

    assert bundle.artifact is not None
    assert isinstance(
        bundle.artifact.content,
        bytes,
    )
    assert bundle.artifact.content.startswith(
        b"%PDF",
    )
    assert "# generic_workflow" in bundle.stdout


def test_morning_report_pdf_output_uses_professional_report_stdout() -> None:
    bundle = render_workflow_output_bundle(
        _morning_report_envelope(),
        output_format="pdf",
        output_path=Path(
            "morning_report.pdf",
        ),
    )

    assert bundle.artifact is not None
    assert isinstance(
        bundle.artifact.content,
        bytes,
    )
    assert bundle.artifact.content.startswith(
        b"%PDF",
    )
    assert "# Polaris Morning Financial Report" in bundle.stdout
    assert "Runtime Node Outputs:" not in bundle.stdout
    _assert_v2_portfolio_report_fields(
        bundle.stdout,
    )


def _assert_v2_portfolio_report_fields(
    rendered: str,
) -> None:
    assert "Portfolio PnL" in rendered
    assert "Portfolio Exposure" in rendered
    assert (
        "Portfolio Risk & Constraints" in rendered
        or "Portfolio Risk &amp; Constraints" in rendered
    )
    assert "Intraday Unrealized PnL" in rendered
    assert "$1,250.55" in rendered
    assert "Margin Utilization" in rendered
    assert "34.0%" in rendered
    assert "Account Restrictions" in rendered
    assert "None Reported" in rendered
    assert "Directional Bias" in rendered
    assert "Long Bias" in rendered
