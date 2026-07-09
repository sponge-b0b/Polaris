from __future__ import annotations

from collections.abc import AsyncIterator
from collections.abc import Callable
from contextlib import asynccontextmanager
import json
from types import SimpleNamespace
from typing import Any
from typing import cast

from typer.testing import CliRunner

from interfaces.cli.app import create_app
from interfaces.cli.commands import morning_report_command
from interfaces.cli.commands import workflow_command
import interfaces.cli.services.workflow_command_service as workflow_command_service
from interfaces.cli.services.workflow_command_service import MorningReportCommandRequest
from interfaces.cli.services.workflow_command_service import WorkflowRunCommandRequest
from interfaces.cli.formatters.console_formatter import format_workflow_run
from interfaces.cli.formatters.json_formatter import format_json
from interfaces.cli.formatters.markdown_formatter import format_workflow_run_markdown
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope
from interfaces.cli.rendering.workflow_rendering import (
    workflow_exception_to_render_envelope,
)
from interfaces.cli.rendering.workflow_rendering import (
    workflow_result_to_render_envelope,
)


def _runtime_scope_from_builder(
    builder: Callable[..., Any],
) -> Callable[..., Any]:
    @asynccontextmanager
    async def scope(**kwargs: object) -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            runtime=await builder(**kwargs),
        )

    return scope


def test_failed_workflow_result_extracts_errors_failed_nodes_and_partial_payload() -> (
    None
):
    envelope = workflow_result_to_render_envelope(
        _failed_workflow_result(),
    )

    assert envelope.success is False
    assert envelope.status == "failed"
    assert envelope.error_message == "workflow failed"
    assert envelope.failed_nodes == ("technical_agent",)
    assert [error.message for error in envelope.errors] == [
        "workflow failed",
        "context failure",
        "indicator unavailable",
    ]
    assert envelope.payload["morning_report"]["symbol"] == "SPY"


def test_console_formatter_renders_failure_errors_and_partial_output() -> None:
    rendered = format_workflow_run(
        _failed_workflow_result(),
    )

    assert "Workflow: morning_report" in rendered
    assert "Success: False" in rendered
    assert "Status: failed" in rendered
    assert "Error: workflow failed" in rendered
    assert "Failed nodes: technical_agent" in rendered
    assert "Symbol: SPY" in rendered
    assert "Partial report" in rendered
    assert "Errors:" in rendered
    assert "indicator unavailable" in rendered


def test_markdown_formatter_renders_failure_errors_and_partial_output() -> None:
    rendered = format_workflow_run_markdown(
        _failed_workflow_result(),
    )

    assert "# morning_report" in rendered
    assert "- Success: `False`" in rendered
    assert "## Failed Nodes" in rendered
    assert "`technical_agent`" in rendered
    assert "## Errors" in rendered
    assert "indicator unavailable" in rendered
    assert "Partial report" in rendered


def test_json_formatter_renders_envelope_for_failed_result() -> None:
    envelope = workflow_result_to_render_envelope(
        _failed_workflow_result(),
    )

    data = json.loads(
        format_json(
            envelope,
        )
    )

    assert data["success"] is False
    assert data["error_message"] == "workflow failed"
    assert data["failed_nodes"] == [
        "technical_agent",
    ]
    assert data["payload"]["morning_report"]["symbol"] == "SPY"
    assert data["errors"][2]["node_name"] == "technical_agent"


def test_successful_real_node_result_extracts_runtime_node_outputs() -> None:
    envelope = workflow_result_to_render_envelope(
        _successful_real_node_workflow_result(),
    )

    assert envelope.success is True
    assert envelope.status == "succeeded"
    assert envelope.payload["workflow_inputs"] == {
        "symbol": "SPY",
    }
    assert (
        envelope.payload["node_outputs"]["technical_agent"]["outputs"][
            "technical_signal"
        ]["directional_score"]
        == 0.42
    )


def test_console_formatter_renders_successful_runtime_node_outputs() -> None:
    rendered = format_workflow_run(
        _successful_real_node_workflow_result(),
    )

    assert "Workflow: morning_report" in rendered
    assert "Success: True" in rendered
    assert "Runtime Node Outputs:" in rendered
    assert "Node: technical_agent" in rendered
    assert '"directional_score": 0.42' in rendered
    assert "Node: execution_risk_guard" in rendered
    assert '"approved": true' in rendered


def test_markdown_formatter_renders_successful_runtime_node_outputs() -> None:
    rendered = format_workflow_run_markdown(
        _successful_real_node_workflow_result(),
    )

    assert "# morning_report" in rendered
    assert "## Runtime Node Outputs" in rendered
    assert "### `technical_agent`" in rendered
    assert "```json" in rendered
    assert '"directional_score": 0.42' in rendered


def test_json_formatter_renders_runtime_node_outputs_payload() -> None:
    envelope = workflow_result_to_render_envelope(
        _successful_real_node_workflow_result(),
    )

    data = json.loads(
        format_json(
            envelope,
        )
    )

    assert data["success"] is True
    assert (
        data["payload"]["node_outputs"]["technical_agent"]["outputs"][
            "technical_signal"
        ]["directional_score"]
        == 0.42
    )


def test_exception_envelope_renders_without_runtime_result() -> None:
    envelope = workflow_exception_to_render_envelope(
        RuntimeError(
            "provider key missing",
        ),
        workflow_name="morning_report",
    )

    rendered = format_workflow_run(
        envelope,
    )

    assert envelope.success is False
    assert "Workflow: morning_report" in rendered
    assert "Success: False" in rendered
    assert "provider key missing" in rendered


def test_morning_report_command_renders_output_when_runtime_setup_raises(
    monkeypatch,
) -> None:
    async def raise_runtime_error(**_: object) -> object:
        raise RuntimeError(
            "provider key missing",
        )

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(raise_runtime_error),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
        ],
    )

    assert result.exit_code == 1
    assert "# Polaris Morning Financial Report" in result.output
    assert "| Workflow Status | Failed |" in result.output
    assert "provider key missing" in result.output


def test_morning_report_command_renders_professional_report_by_default(
    monkeypatch,
) -> None:
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
        ],
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.output
    assert "## Executive Summary" in result.output
    assert "## Portfolio Snapshot" in result.output
    assert "### Portfolio PnL" in result.output
    assert "### Portfolio Exposure" in result.output
    assert "### Portfolio Risk & Constraints" in result.output
    assert "Margin Utilization" in result.output
    assert "$1,250.55" in result.output
    assert "Account Restrictions" in result.output
    assert "## Macro / Fundamental Backdrop" in result.output
    assert "## Technical Setup" in result.output
    assert "## News & Sentiment" in result.output
    assert "## Risk Assessment" in result.output
    assert "## Recommended Action Plan" in result.output
    assert "Macro full LLM response for the CLI report." in result.output
    assert "Runtime Node Outputs:" not in result.output
    assert "```json" not in result.output


def test_morning_report_command_markdown_renders_professional_report(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(
        tmp_path,
    )
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--format",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.output
    assert "| Symbol | SPY |" in result.output
    assert "## Recommended Action Plan" in result.output
    assert "### Portfolio PnL" in result.output
    assert "Margin Utilization" in result.output
    assert "This action plan is decision support only" in result.output
    assert "## Runtime Node Outputs" not in result.output


def test_morning_report_command_raw_uses_generic_workflow_rendering(
    monkeypatch,
) -> None:
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--raw",
        ],
    )

    assert result.exit_code == 0
    assert "Workflow: morning_report" in result.output
    assert "Success: True" in result.output
    assert "Runtime Node Outputs:" in result.output
    assert "Node: technical_agent" in result.output
    assert '"directional_score": 0.42' in result.output
    assert "# Polaris Morning Financial Report" not in result.output


def test_morning_report_command_rejects_obsolete_console_format() -> None:
    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--format",
            "console",
        ],
    )

    assert result.exit_code != 0
    assert "--format console is obsolete" in result.output


def test_morning_report_command_rejects_removed_progress_flag() -> None:
    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--progress",
        ],
    )

    assert result.exit_code != 0
    assert "--progress" in result.output


def test_morning_report_command_rejects_removed_interactive_control_flag() -> None:
    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--interactive-control",
        ],
    )

    assert result.exit_code != 0
    assert "--interactive-control" in result.output


def test_morning_report_command_enables_progress_and_control_by_default(
    monkeypatch,
) -> None:
    captured_request: dict[str, object] = {}

    class FakeWorkflowCommandService:
        def __init__(
            self,
            **_: object,
        ) -> None:
            pass

        async def run_morning_report(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            captured_request["request"] = request
            return workflow_result_to_render_envelope(
                _professional_morning_report_workflow_result(),
            )

    monkeypatch.setattr(
        morning_report_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
        ],
    )

    request = cast(
        MorningReportCommandRequest,
        captured_request["request"],
    )

    assert result.exit_code == 0
    assert request.progress_handler is not None
    assert request.interactive_control is True
    assert request.control_handler is not None


def test_workflow_run_command_renders_failed_workflow_result(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **_: object,
        ) -> dict[str, object]:
            return _failed_workflow_result()

    class FakeEventBus:
        def subscribe_all(
            self,
            _: object,
        ) -> None:
            pass

        def unsubscribe_all(
            self,
            _: object,
        ) -> None:
            pass

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = FakeEventBus()

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )
    monkeypatch.chdir(
        tmp_path,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 1
    assert "[control]" not in result.stdout
    assert "[control]" in result.stderr
    data = json.loads(
        result.stdout,
    )
    assert data["workflow_name"] == "morning_report"
    assert data["success"] is False
    assert data["payload"]["morning_report"]["summary"] == "Partial report"


def test_workflow_run_command_renders_morning_report_by_default(
    monkeypatch,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _professional_morning_report_workflow_result(),
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
        ],
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.output
    assert "## Executive Summary" in result.output
    assert "Macro full LLM response for the CLI report." in result.output
    assert "Runtime Node Outputs:" not in result.output


def test_workflow_run_command_rejects_obsolete_console_format() -> None:
    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
            "--format",
            "console",
        ],
    )

    assert result.exit_code != 0
    assert "--format console is obsolete" in result.output


def test_workflow_run_command_rejects_removed_progress_flag() -> None:
    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
            "--progress",
        ],
    )

    assert result.exit_code != 0
    assert "--progress" in result.output


def test_workflow_run_command_rejects_removed_interactive_control_flag() -> None:
    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
            "--interactive-control",
        ],
    )

    assert result.exit_code != 0
    assert "--interactive-control" in result.output


def test_workflow_run_command_enables_progress_and_control_by_default(
    monkeypatch,
) -> None:
    captured_request: dict[str, object] = {}

    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            captured_request["request"] = request
            return workflow_result_to_render_envelope(
                _successful_real_node_workflow_result(),
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
        ],
    )

    request = cast(
        WorkflowRunCommandRequest,
        captured_request["request"],
    )

    assert result.exit_code == 0
    assert request.progress_handler is not None
    assert request.interactive_control is True
    assert request.control_handler is not None


def test_morning_report_command_markdown_writes_default_artifact(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(
        tmp_path,
    )
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--format",
            "markdown",
        ],
    )

    files = list(
        tmp_path.glob(
            "morning_report_*.md",
        )
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    assert "# Polaris Morning Financial Report" in files[0].read_text(
        encoding="utf-8",
    )
    assert f"[output] wrote {files[0]}" in result.stderr


def test_morning_report_command_html_writes_default_artifact_and_readable_stdout(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(
        tmp_path,
    )
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--format",
            "html",
        ],
    )

    files = list(
        tmp_path.glob(
            "morning_report_*.html",
        )
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.stdout
    assert "<html" not in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    html = files[0].read_text(
        encoding="utf-8",
    )
    assert "<!doctype html>" in html.lower()
    assert "Polaris Morning Financial Report" in html
    assert f"[output] wrote {files[0]}" in result.stderr


def test_morning_report_command_json_writes_default_artifact_and_clean_stdout(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(
        tmp_path,
    )
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--format",
            "json",
        ],
    )

    files = list(
        tmp_path.glob(
            "morning_report_*.json",
        )
    )
    stdout_data = json.loads(
        result.stdout,
    )

    assert result.exit_code == 0
    assert stdout_data["workflow_name"] == "morning_report"
    assert stdout_data["success"] is True
    assert "[control]" not in result.stdout
    assert "[output]" not in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    assert (
        json.loads(
            files[0].read_text(
                encoding="utf-8",
            )
        )
        == stdout_data
    )
    assert f"[output] wrote {files[0]}" in result.stderr


def test_morning_report_command_pdf_writes_binary_artifact_and_text_stdout(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(
        tmp_path,
    )
    _patch_cli_runtime(
        monkeypatch,
        _professional_morning_report_workflow_result(),
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "morning-report",
            "--format",
            "pdf",
        ],
    )

    files = list(
        tmp_path.glob(
            "morning_report_*.pdf",
        )
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.stdout
    assert "%PDF" not in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    assert (
        files[0]
        .read_bytes()
        .startswith(
            b"%PDF",
        )
    )


def test_workflow_run_command_generic_default_uses_console_fallback_without_file(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _generic_workflow_result(),
            )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "generic_workflow",
        ],
    )

    assert result.exit_code == 0
    assert "Workflow: generic_workflow" in result.stdout
    assert "Runtime Node Outputs:" in result.stdout
    assert "# generic_workflow" not in result.stdout
    assert (
        list(
            tmp_path.glob(
                "generic_workflow_*",
            )
        )
        == []
    )


def test_workflow_run_command_generic_markdown_writes_default_artifact(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _generic_workflow_result(),
            )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "generic_workflow",
            "--format",
            "markdown",
        ],
    )

    files = list(
        tmp_path.glob(
            "generic_workflow_*.md",
        )
    )

    assert result.exit_code == 0
    assert "# generic_workflow" in result.stdout
    assert "Runtime Node Outputs" in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    assert files[0].read_text(
        encoding="utf-8",
    ) == result.stdout.rstrip(
        "\n",
    )


def test_workflow_run_command_generic_html_writes_default_artifact_and_readable_stdout(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _generic_workflow_result(),
            )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "generic_workflow",
            "--format",
            "html",
        ],
    )

    files = list(
        tmp_path.glob(
            "generic_workflow_*.html",
        )
    )

    assert result.exit_code == 0
    assert "# generic_workflow" in result.stdout
    assert "<html" not in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    html = files[0].read_text(
        encoding="utf-8",
    )
    assert "<html" in html
    assert "generic_workflow" in html


def test_workflow_run_command_generic_pdf_writes_default_artifact_and_text_stdout(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _generic_workflow_result(),
            )

    monkeypatch.chdir(
        tmp_path,
    )
    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "generic_workflow",
            "--format",
            "pdf",
        ],
    )

    files = list(
        tmp_path.glob(
            "generic_workflow_*.pdf",
        )
    )

    assert result.exit_code == 0
    assert "# generic_workflow" in result.stdout
    assert "%PDF" not in result.stdout
    assert (
        len(
            files,
        )
        == 1
    )
    assert (
        files[0]
        .read_bytes()
        .startswith(
            b"%PDF",
        )
    )


def test_workflow_run_command_json_output_override_writes_artifact_clean_stdout(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _successful_real_node_workflow_result(),
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )
    output_path = tmp_path / "workflow.json"

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
            "--format",
            "json",
            "--output",
            str(
                output_path,
            ),
        ],
    )

    stdout_data = json.loads(
        result.stdout,
    )
    file_data = json.loads(
        output_path.read_text(
            encoding="utf-8",
        )
    )

    assert result.exit_code == 0
    assert stdout_data["workflow_name"] == "morning_report"
    assert file_data == stdout_data
    assert "[control]" not in result.stdout
    assert f"[output] wrote {output_path}" in result.stderr


def test_workflow_run_command_output_without_format_writes_stdout_text(
    monkeypatch,
    tmp_path,
) -> None:
    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return workflow_result_to_render_envelope(
                _successful_real_node_workflow_result(),
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )
    output_path = tmp_path / "workflow.txt"

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "morning_report",
            "--output",
            str(
                output_path,
            ),
        ],
    )

    assert result.exit_code == 0
    assert "# Polaris Morning Financial Report" in result.stdout
    output_text = output_path.read_text(
        encoding="utf-8",
    )

    assert output_text in result.stdout
    assert f"[output] wrote {output_path}" in result.stderr


def _patch_cli_runtime(
    monkeypatch,
    workflow_result: dict[str, object],
) -> None:
    class FakeFacade:
        def workflow_exists(
            self,
            workflow_name: str,
        ) -> bool:
            return workflow_name == "morning_report"

        async def run_workflow(
            self,
            **_: object,
        ) -> dict[str, object]:
            return workflow_result

    class FakeEventBus:
        def subscribe_all(
            self,
            _: object,
        ) -> None:
            pass

        def unsubscribe_all(
            self,
            _: object,
        ) -> None:
            pass

    class FakeRuntime:
        facade = FakeFacade()
        event_bus = FakeEventBus()

    async def build_runtime(**_: object) -> FakeRuntime:
        return FakeRuntime()

    monkeypatch.setattr(
        workflow_command_service,
        "cli_runtime_scope",
        _runtime_scope_from_builder(build_runtime),
    )


def _professional_morning_report_workflow_result() -> dict[str, object]:
    return {
        "success": True,
        "workflow_name": "morning_report",
        "execution_id": "exec-cli-report",
        "execution_result": {
            "success": True,
            "workflow_name": "morning_report",
            "execution_id": "exec-cli-report",
            "runtime_id": "runtime-cli-report",
            "duration_seconds": 2.5,
            "final_context": {
                "workflow_id": "morning_report",
                "execution_id": "exec-cli-report",
                "mode": "live",
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
                                    "portfolio_value": 500_000,
                                    "cash": 125_000,
                                    "cash_ratio": 0.25,
                                    "cash_pct": 0.25,
                                    "realized_pnl_pct": 0.037,
                                    "unrealized_pnl_pct": 0.024,
                                    "unrealized_intraday_pnl": 1250.55,
                                    "unrealized_intraday_pnl_pct": 0.0013,
                                    "pnl_total_pct": 0.061,
                                    "long_market_value": 360_000,
                                    "short_market_value": 40_000,
                                    "gross_market_value": 400_000,
                                    "net_market_value": 320_000,
                                    "gross_exposure": 0.7,
                                    "net_exposure": 0.6,
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
                                "positions_state": {
                                    "position_count": 5,
                                },
                            },
                        },
                    },
                    "fundamental_agent": {
                        "success": True,
                        "outputs": {
                            "directional_score": 0.55,
                            "confidence": 0.7,
                            "regime": "constructive",
                            "llm_response": "Macro full LLM response for the CLI report.",
                            "features": {
                                "macro_state": {
                                    "fed_stance": "pause",
                                    "liquidity_regime": "neutral",
                                    "inflation_regime": "cooling",
                                    "growth_regime": "resilient",
                                },
                            },
                        },
                    },
                    "technical_agent": {
                        "success": True,
                        "outputs": {
                            "directional_score": 0.42,
                            "confidence": 0.8,
                            "regime": "bullish",
                            "llm_response": "Technical full LLM response for the CLI report.",
                            "features": {
                                "regime": {
                                    "execution_readiness": 0.8,
                                    "signal_quality": 0.75,
                                },
                                "technical_state": {
                                    "trend_direction": "uptrend",
                                    "momentum_state": "positive",
                                },
                                "volatility": {
                                    "volatility_regime": "normal",
                                },
                                "snapshot": {
                                    "close": 450,
                                    "rsi_14": 58,
                                    "atr_14": 4.2,
                                },
                            },
                        },
                    },
                    "news_agent": {
                        "success": True,
                        "outputs": {
                            "regime": "high_relevance",
                            "llm_response": "News full LLM response for the CLI report.",
                            "features": {
                                "headline_count": 3,
                                "market_relevance": "high_relevance",
                                "primary_themes": [
                                    "rates",
                                    "earnings",
                                ],
                            },
                        },
                    },
                    "sentiment_agent": {
                        "success": True,
                        "outputs": {
                            "directional_score": 0.5,
                            "confidence": 0.65,
                            "regime": "neutral",
                            "llm_response": "Sentiment full LLM response for the CLI report.",
                            "features": {
                                "composite_sentiment": 0.52,
                                "fear_greed_state": "neutral",
                                "positioning_state": "balanced",
                            },
                        },
                    },
                    "risk_signal_builder": {
                        "success": True,
                        "outputs": {
                            "features": {
                                "primitive_sources": {
                                    "volatility": 0.4,
                                    "drawdown": 0.2,
                                    "exposure": 0.35,
                                },
                            },
                        },
                    },
                    "risk_aggregator_agent": {
                        "success": True,
                        "outputs": {
                            "confidence": 0.72,
                            "regime": "moderate",
                            "features": {
                                "adjusted_composite_risk": 0.6,
                                "adjusted_risk_pressure": 0.45,
                                "stability_score": 0.55,
                                "risk_regime": "moderate",
                                "risk_bias": "balanced",
                            },
                            "recommendations": [
                                "keep_position_sizes_moderate",
                            ],
                        },
                    },
                    "strategy_synthesis_agent": {
                        "success": True,
                        "outputs": {
                            "confidence": 0.73,
                            "regime": "selective_risk_on",
                            "features": {
                                "posture": "selective_risk_on",
                                "execution_readiness": 0.68,
                                "portfolio_scale_factor": 0.6,
                            },
                            "recommendations": [
                                "add_exposure_selectively",
                            ],
                        },
                    },
                    "portfolio_manager_agent": {
                        "success": True,
                        "outputs": {
                            "regime": "ready_for_review",
                            "features": {
                                "execution_status": "ready_for_review",
                                "scale_factor": 0.6,
                            },
                            "recommendations": [
                                "rebalance_toward_quality",
                            ],
                        },
                    },
                    "trade_packager": {
                        "success": True,
                        "outputs": {
                            "regime": "long_bias",
                            "features": {
                                "trade_intent": {
                                    "direction": "long_bias",
                                    "position_sizing_hint": 0.3,
                                    "trade_quality_score": 0.7,
                                },
                            },
                            "recommendations": [
                                "stage_entries",
                            ],
                        },
                    },
                    "execution_risk_guard": {
                        "success": True,
                        "outputs": {
                            "features": {
                                "execution_guard": {
                                    "mode": "review",
                                    "adjusted_position_size": 0.3,
                                },
                            },
                            "recommendations": [
                                "confirm_liquidity_before_action",
                            ],
                        },
                    },
                },
            },
        },
    }


def _failed_workflow_result() -> dict[str, object]:
    return {
        "success": False,
        "workflow_name": "morning_report",
        "execution_id": "exec-123",
        "execution_result": {
            "success": False,
            "workflow_name": "morning_report",
            "execution_id": "exec-123",
            "runtime_id": "runtime-123",
            "duration_seconds": 1.25,
            "error_message": "workflow failed",
            "final_context": {
                "mode": "live",
                "context_version": 4,
                "workflow_inputs": {
                    "morning_report": {
                        "result": {
                            "symbol": "SPY",
                            "generated_at": "2026-05-25T08:00:00Z",
                            "summary": "Partial report",
                            "risks": [
                                "data quality",
                            ],
                            "opportunities": [
                                "defensive rebalance",
                            ],
                        }
                    }
                },
                "errors": [
                    {
                        "message": "context failure",
                    }
                ],
                "node_outputs": {
                    "technical_agent": {
                        "success": False,
                        "errors": [
                            {
                                "message": "indicator unavailable",
                                "type": "DataUnavailable",
                            }
                        ],
                    }
                },
            },
        },
    }


def _successful_real_node_workflow_result() -> dict[str, object]:
    return {
        "success": True,
        "workflow_name": "morning_report",
        "execution_id": "exec-456",
        "execution_result": {
            "success": True,
            "workflow_name": "morning_report",
            "execution_id": "exec-456",
            "runtime_id": "runtime-456",
            "duration_seconds": 2.5,
            "final_context": {
                "workflow_id": "morning_report",
                "execution_id": "exec-456",
                "mode": "live",
                "context_version": 7,
                "workflow_inputs": {
                    "symbol": "SPY",
                },
                "node_outputs": {
                    "technical_agent": {
                        "success": True,
                        "outputs": {
                            "technical_signal": {
                                "directional_score": 0.42,
                                "confidence": 0.8,
                                "regime": "bullish",
                            }
                        },
                    },
                    "execution_risk_guard": {
                        "success": True,
                        "outputs": {
                            "approved": True,
                            "reason": "within policy limits",
                        },
                    },
                },
            },
        },
    }


def _generic_workflow_result() -> dict[str, object]:
    return {
        "success": True,
        "workflow_name": "generic_workflow",
        "execution_id": "exec-generic",
        "execution_result": {
            "success": True,
            "workflow_name": "generic_workflow",
            "execution_id": "exec-generic",
            "runtime_id": "runtime-generic",
            "duration_seconds": 0.5,
            "final_context": {
                "workflow_id": "generic_workflow",
                "execution_id": "exec-generic",
                "mode": "live",
                "workflow_inputs": {
                    "request_id": "req-generic",
                },
                "node_outputs": {
                    "example_node": {
                        "success": True,
                        "outputs": {
                            "example_signal": {
                                "score": 0.64,
                                "confidence": 0.81,
                                "regime": "constructive",
                            }
                        },
                    }
                },
            },
        },
    }


def test_workflow_run_command_rejects_malformed_metadata_before_execution(
    monkeypatch,
) -> None:
    class UnexpectedWorkflowCommandService:
        def __init__(
            self,
        ) -> None:
            raise AssertionError(
                "workflow service must not start for invalid CLI input"
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        UnexpectedWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "analysis",
            "--metadata",
            "invalid-metadata",
        ],
    )

    assert result.exit_code == 2
    assert "metadata must use key=value format" in result.output
    assert "Workflow: analysis" not in result.output


def test_workflow_run_command_renders_cancelled_output_without_truncation(
    monkeypatch,
) -> None:
    complete_response = "full-response-start\n" + ("deterministic detail " * 1_500)
    complete_response += "\nfull-response-end"

    class FakeWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return WorkflowRenderEnvelope(
                workflow_name="analysis",
                execution_id="exec-cancelled",
                success=False,
                status="cancelled",
                payload={
                    "node_outputs": {
                        "analysis_agent": {
                            "success": False,
                            "outputs": {
                                "llm_response": complete_response,
                            },
                        }
                    }
                },
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FakeWorkflowCommandService,
    )

    result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "analysis",
        ],
    )

    assert result.exit_code == 1
    assert "Status: cancelled" in result.output
    assert result.output.count("deterministic detail") == 1_500
    assert "full-response-end" in result.output


def test_workflow_run_command_renders_partial_output_and_service_failures(
    monkeypatch,
) -> None:
    class PartialWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            return WorkflowRenderEnvelope(
                workflow_name="analysis",
                execution_id="exec-partial",
                success=False,
                status="partial",
                error_message="one node failed",
                payload={
                    "partial_report": {
                        "summary": "usable partial result",
                    }
                },
            )

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        PartialWorkflowCommandService,
    )
    partial_result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "analysis",
        ],
    )

    assert partial_result.exit_code == 1
    assert "Status: partial" in partial_result.output
    assert "usable partial result" in partial_result.output
    assert "one node failed" in partial_result.output

    class FailingWorkflowCommandService:
        async def run_workflow(
            self,
            request: object,
        ) -> WorkflowRenderEnvelope:
            raise RuntimeError("workflow service unavailable")

    monkeypatch.setattr(
        workflow_command,
        "WorkflowCommandService",
        FailingWorkflowCommandService,
    )
    failure_result = CliRunner().invoke(
        create_app(),
        [
            "workflow",
            "run",
            "analysis",
        ],
    )

    assert failure_result.exit_code == 1
    assert "Status: failed" in failure_result.output
    assert "workflow service unavailable" in failure_result.output
