"""Canonical catalog of built-in Polaris workflows."""

from __future__ import annotations

from dataclasses import dataclass

from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.models.workflow_node_definition import WorkflowNodeDefinition
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskAuthorityContract,
    SourceOfTruthCategory,
    classify_risk_authority,
)
from workflows.definitions.reports.morning_report import MorningReportWorkflow


class EvaluationGateNode(RuntimeNode):
    """Registry marker node for evaluation authority-gate packet identity."""

    node_name = "evaluation_gate"
    node_type = "evaluation_gate"
    node_version = "1.0.0"

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(outputs={})


class EvaluationGateWorkflow(WorkflowGraphDefinition):
    """Registry identity for evaluation authority-gate evidence packets."""

    @property
    def workflow_name(self) -> str:
        return "evaluation_gate"

    @property
    def workflow_description(self) -> str:
        return "Canonical evaluation authority-gate evidence packet boundary."

    def build_graph(self) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="evaluation_gate",
                node_type=EvaluationGateNode,
                max_retries=0,
                tags=("evaluation", "governance"),
            )
        ]


@dataclass(frozen=True, slots=True)
class BuiltinWorkflowRegistration:
    """Catalog-owned invocation facts for one built-in workflow."""

    definition: WorkflowGraphDefinition
    authority: RiskAuthorityContract


def get_builtin_workflow_registrations() -> tuple[BuiltinWorkflowRegistration, ...]:
    """Return built-ins with the authority facts owned by the platform catalog."""

    return (
        BuiltinWorkflowRegistration(
            definition=MorningReportWorkflow(),
            authority=classify_risk_authority(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.RUNTIME_EVIDENCE,
                    authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
                    canonical_owner=CanonicalOwner.RUNTIME,
                    source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
                    intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
                )
            ),
        ),
        BuiltinWorkflowRegistration(
            definition=EvaluationGateWorkflow(),
            authority=classify_risk_authority(
                RiskAuthorityClassificationInput(
                    content_type=AiOutputContentType.RUNTIME_EVIDENCE,
                    authority_effect=AuthorityEffect.NON_AUTHORITATIVE_INFORMATION,
                    canonical_owner=CanonicalOwner.EVALUATION_SERVICE,
                    source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
                    intended_sink=IntendedSink.EVALUATION_GATE,
                )
            ),
        ),
    )


def get_builtin_workflow_registration(
    workflow_name: str,
) -> BuiltinWorkflowRegistration:
    """Return the catalog-owned registration for one built-in workflow."""

    normalized_workflow_name = workflow_name.strip()
    for registration in get_builtin_workflow_registrations():
        if registration.definition.workflow_name == normalized_workflow_name:
            return registration
    raise KeyError(
        f"Built-in workflow is not registered in the catalog: {workflow_name}"
    )


def get_builtin_workflows() -> list[WorkflowGraphDefinition]:
    """Return public executable built-in workflows."""

    return [MorningReportWorkflow()]
