from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_registry import GovernanceRegistry
from core.runtime.governance.governance_result import GovernanceResult
from core.runtime.governance.governance_rule import BaseGovernanceRule
from core.storage.persistence.governance_audit import AutomatedDecisionSubject
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime,
)
from core.workflow.governance_audit import (
    AutomatedDecisionAuditContext,
    issue_workflow_execution_audit_capability,
)
from domain.authority import classify_risk_authority
from tests.helpers.risk_authority_examples import workflow_curation_authority_input


class DenyBootstrapGovernanceTelemetryRule(BaseGovernanceRule):
    rule_name = "deny_bootstrap_governance_telemetry"
    enabled = True

    async def evaluate(
        self,
        subject: Any,
        context: dict[str, Any] | None = None,
    ) -> GovernanceResult:
        if (context or {}).get("governance_phase") == ("workflow_run_preflight"):
            return GovernanceResult.deny(
                rule_name=self.rule_name,
                message="Denied by bootstrap governance telemetry test.",
                reason="bootstrap_governance_denial",
            )

        return GovernanceResult.allow(
            rule_name=self.rule_name,
        )


@pytest.mark.asyncio
async def test_bootstrap_wires_governance_telemetry() -> None:
    governance_engine = GovernanceEngine(
        registry=GovernanceRegistry(
            rules=[
                DenyBootstrapGovernanceTelemetryRule(),
            ],
        ),
    )

    runtime = build_workflow_runtime(
        config=WorkflowBootstrapConfig(
            enable_governance=True,
            enable_policies=False,
            enable_telemetry=False,
            enable_jsonl_telemetry=False,
            enable_observability=True,
        ),
        governance_engine=governance_engine,
    )

    assert runtime.observability_manager is not None
    assert runtime.governance_engine is not None
    assert runtime.governance_engine.telemetry_emitter is not None

    sink = InMemoryTelemetrySink()

    runtime.observability_manager.add_sink(
        sink,
    )
    audit_service = AsyncMock()
    audit_service.record_governance_evaluation.return_value = ()
    execution_audit_capability = issue_workflow_execution_audit_capability(
        service=audit_service,
        context=AutomatedDecisionAuditContext(
            subject=AutomatedDecisionSubject(
                "workflow",
                "bootstrap-governance-telemetry-test",
            ),
            authority=classify_risk_authority(
                workflow_curation_authority_input(),
            ),
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="bootstrap_governance_denial",
    ):
        await runtime.facade.run_workflow(
            workflow_name="missing_workflow",
            mode="simulation",
            archive_on_completion=False,
            checkpoint_on_completion=False,
            execution_audit_capability=execution_audit_capability,
        )

    audit_service.record_governance_evaluation.assert_awaited_once()

    event_types = [event.event_type for event in sink.events]

    assert "runtime.governance.evaluated" in event_types
    assert "runtime.governance.blocked" in event_types

    blocked_event = [
        event
        for event in sink.events
        if event.event_type == "runtime.governance.blocked"
    ][-1]

    assert blocked_event.success is False
    assert blocked_event.error_count == 1
    assert blocked_event.payload["governance_phase"] == ("workflow_run_preflight")
    assert (
        blocked_event.payload["evaluation"]["results"][0]["reason"]
        == "bootstrap_governance_denial"
    )
