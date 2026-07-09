from __future__ import annotations

from typing import Any

from interfaces.cli.rendering.workflow_rendering import WorkflowRenderEnvelope
from interfaces.cli.rendering.workflow_rendering import (
    workflow_result_to_render_envelope,
)


def ensure_workflow_render_envelope(
    result: Any,
) -> WorkflowRenderEnvelope:
    if isinstance(
        result,
        WorkflowRenderEnvelope,
    ):
        return result

    return workflow_result_to_render_envelope(
        result,
    )


def workflow_morning_report(
    envelope: WorkflowRenderEnvelope,
) -> dict[str, Any]:
    morning_report = envelope.payload.get(
        "morning_report",
        {},
    )

    if isinstance(morning_report, dict):
        return morning_report

    return {}


def workflow_node_outputs(
    envelope: WorkflowRenderEnvelope,
) -> dict[str, Any]:
    node_outputs = envelope.payload.get(
        "node_outputs",
        {},
    )

    if isinstance(node_outputs, dict):
        return node_outputs

    return {}


def additional_workflow_payload(
    envelope: WorkflowRenderEnvelope,
) -> dict[str, Any]:
    return {
        key: value
        for key, value in envelope.payload.items()
        if key
        not in {
            "morning_report",
            "node_outputs",
        }
    }
