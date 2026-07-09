"""Canonical catalog of built-in Polaris workflows."""

from __future__ import annotations

from core.workflow.models.workflow_graph_definition import (
    WorkflowGraphDefinition,
)
from workflows.definitions.reports.morning_report import MorningReportWorkflow


def get_builtin_workflows() -> list[WorkflowGraphDefinition]:
    """Return the statically registered platform workflows."""

    return [
        MorningReportWorkflow(),
    ]
