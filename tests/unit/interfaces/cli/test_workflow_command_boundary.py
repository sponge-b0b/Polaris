from __future__ import annotations

from pathlib import Path

import pytest

from interfaces.cli.commands import workflow_command_boundary
from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope


def test_workflow_output_fallback_preserves_complete_terminal_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete_response = "begin\n" + ("complete content " * 1_000) + "\nend"
    envelope = WorkflowRenderEnvelope(
        workflow_name="analysis",
        execution_id="exec-cancelled",
        success=False,
        status="cancelled",
        payload={
            "node_outputs": {
                "analysis_agent": {
                    "outputs": {
                        "llm_response": complete_response,
                    }
                }
            }
        },
    )

    def fail_primary_renderer(*_: object, **__: object) -> object:
        raise RuntimeError("primary renderer unavailable")

    monkeypatch.setattr(
        workflow_command_boundary,
        "render_workflow_output_bundle",
        fail_primary_renderer,
    )

    rendered = workflow_command_boundary.render_workflow_output_with_fallback(
        envelope,
        None,
        output_path=None,
    )

    assert "renderer failed; showing generic workflow output" in rendered.stdout
    assert "Status: cancelled" in rendered.stdout
    assert rendered.stdout.count("complete content") == 1_000
    assert rendered.artifact is None


def test_workflow_output_last_resort_preserves_real_workflow_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = WorkflowRenderEnvelope(
        workflow_name="analysis",
        execution_id="exec-partial",
        success=False,
        status="partial",
    )

    def fail_renderer(*_: object, **__: object) -> object:
        raise RuntimeError("renderer unavailable")

    monkeypatch.setattr(
        workflow_command_boundary,
        "render_workflow_output_bundle",
        fail_renderer,
    )
    monkeypatch.setattr(
        workflow_command_boundary,
        "render_workflow_output",
        fail_renderer,
    )

    rendered = workflow_command_boundary.render_workflow_output_with_fallback(
        envelope,
        "markdown",
        output_path=Path("unused.md"),
    )

    assert "Success: False" in rendered.stdout
    assert "Status: partial" in rendered.stdout
    assert "Status: failed" not in rendered.stdout
    assert "Fallback Error: renderer unavailable" in rendered.stdout
    assert rendered.artifact is None
