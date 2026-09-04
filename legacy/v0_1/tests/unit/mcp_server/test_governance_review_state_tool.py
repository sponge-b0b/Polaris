"""Tests for the thin ``polaris_governance_review_states_list`` MCP boundary."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from dishka import AsyncContainer
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from application.governance import (
    GovernanceReviewApprovalState,
    GovernanceReviewState,
    GovernanceReviewTaskQuery,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditOutcome,
    AutomatedGovernanceAuditRecord,
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionOutcome,
    GovernanceReviewDecisionRecord,
    GovernanceReviewerActorType,
    GovernanceReviewerIdentity,
    GovernanceReviewTaskRecord,
    GovernanceReviewTaskStatus,
    authority_metadata_from_contract,
)
from core.telemetry.collectors.telemetry_collector import TelemetryCollector
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from core.workflow.bootstrap.workflow_bootstrap import WorkflowBootstrapResult
from domain.authority import classify_risk_authority
from mcp_server.contracts.models import GovernanceReviewStatesListRequest
from mcp_server.lifespan import McpApplicationContext
from mcp_server.settings import McpServerSettings
from mcp_server.telemetry import McpTelemetry
from mcp_server.tools.governance_review_state import (
    execute_governance_review_states_list,
)
from tests.helpers.risk_authority_examples import (
    recommendation_explanation_authority_input,
)

_CREATED_AT = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
_UPDATED_AT = datetime(2026, 8, 23, 12, 5, tzinfo=UTC)
_DECIDED_AT = datetime(2026, 8, 23, 12, 10, tzinfo=UTC)
_ACCEPTED_AT = datetime(2026, 8, 23, 12, 11, tzinfo=UTC)


def _redaction_probe_value() -> str:
    return "-".join(
        (
            "redaction",
            "probe",
        )
    )


class _FakeGovernanceReviewStateService:
    def __init__(
        self,
        result: tuple[GovernanceReviewState, ...] | BaseException,
    ) -> None:
        self._result = result
        self.queries: list[GovernanceReviewTaskQuery] = []

    async def list_governance_review_states(
        self,
        query: GovernanceReviewTaskQuery | None = None,
    ) -> tuple[GovernanceReviewState, ...]:
        self.queries.append(query or GovernanceReviewTaskQuery())
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result


class _RequestContainer:
    def __init__(self, service: object) -> None:
        self._service = service

    async def get(self, dependency_type: type[object]) -> object:
        assert dependency_type.__name__ == "AutomatedDecisionAuditService"
        return self._service


class _RequestScope:
    def __init__(self, service: object) -> None:
        self._container = _RequestContainer(service)
        self.closed = False

    async def __aenter__(self) -> _RequestContainer:
        return self._container

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object,
    ) -> None:
        self.closed = True


class _ApplicationContainer:
    def __init__(self, service: object) -> None:
        self._service = service
        self.scopes: list[_RequestScope] = []

    def __call__(self) -> _RequestScope:
        scope = _RequestScope(self._service)
        self.scopes.append(scope)
        return scope


def _context(
    service: object,
    *,
    settings: McpServerSettings | None = None,
) -> tuple[McpApplicationContext, InMemoryTelemetrySink, _ApplicationContainer]:
    sink = InMemoryTelemetrySink()
    manager = ObservabilityManager(
        collector=TelemetryCollector(sinks=(sink,)),
        enable_domain_metrics=False,
    )
    container = _ApplicationContainer(service)
    return (
        McpApplicationContext(
            container=cast(AsyncContainer, container),
            runtime=cast(WorkflowBootstrapResult, SimpleNamespace()),
            telemetry=McpTelemetry(manager),
            settings=settings or McpServerSettings(),
        ),
        sink,
        container,
    )


@pytest.mark.asyncio
async def test_governance_review_states_list_surfaces_authoritative_state() -> None:
    redaction_probe = _redaction_probe_value()
    state = _review_state()
    service = _FakeGovernanceReviewStateService((state,))
    context, sink, container = _context(service)

    response = await execute_governance_review_states_list(
        GovernanceReviewStatesListRequest(
            subject_type="recommendation",
            subject_id="rec-1",
            risk_tier="vigilant",
            approval_state="review_approved",
            review_scope="recommendation",
            intended_sink="recommendation",
            requested_action="vigilant_authority_requires_approval",
            evidence_packet_id="packet-1",
            evidence_packet_version=1,
            closed=True,
        ),
        context,
        request_id="governance-review-state-1",
    )

    assert service.queries == [
        GovernanceReviewTaskQuery(
            subject_type="recommendation",
            subject_id="rec-1",
            risk_tier="vigilant",
            approval_state="review_approved",
            review_scope="recommendation",
            intended_sink="recommendation",
            requested_action="vigilant_authority_requires_approval",
            evidence_packet_id="packet-1",
            evidence_packet_version=1,
            closed=True,
        )
    ]
    assert response.total_count == 1
    assert response.has_more is False
    exposed = response.review_states[0]
    assert exposed.review_task_id == "governance_review_task:task-1"
    assert exposed.approval_state == "review_approved"
    assert exposed.status == "approved"
    assert exposed.closed is True
    assert exposed.automated_governance_outcome == "require_approval"
    assert exposed.audit_history[0].outcome == "approved"
    assert exposed.residual_risk_acceptances[0].residual_risk_scope == (
        "material_recommendation_claims"
    )
    serialized = response.model_dump_json()
    assert redaction_probe not in serialized
    assert "[REDACTED]" in serialized
    assert container.scopes[0].closed is True
    assert [event.event_type for event in sink.events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert all(
        event.correlation_id == "governance-review-state-1" for event in sink.events
    )


@pytest.mark.asyncio
async def test_governance_review_states_list_applies_boundary_pagination() -> None:
    states = (_review_state(task_id="1"), _review_state(task_id="2"))
    service = _FakeGovernanceReviewStateService(states)
    context, _, _ = _context(service)

    response = await execute_governance_review_states_list(
        GovernanceReviewStatesListRequest(offset=1, limit=1),
        context,
    )

    assert [state.review_task_id for state in response.review_states] == [
        "governance_review_task:2",
    ]
    assert response.total_count == 2
    assert response.has_more is False
    assert response.next_offset is None


@pytest.mark.asyncio
async def test_governance_review_states_list_rejects_page_size_before_service() -> None:
    service = _FakeGovernanceReviewStateService(())
    context, sink, container = _context(
        service,
        settings=McpServerSettings(max_page_size=2),
    )

    with pytest.raises(ToolError, match="limit cannot exceed 2"):
        await execute_governance_review_states_list(
            GovernanceReviewStatesListRequest(limit=3),
            context,
        )

    assert service.queries == []
    assert container.scopes == []
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "validation"


@pytest.mark.asyncio
async def test_governance_review_states_list_sanitizes_failure_and_closes_scope() -> (
    None
):
    redaction_probe = _redaction_probe_value()
    service = _FakeGovernanceReviewStateService(
        RuntimeError(f"dependency failure detail: {redaction_probe}"),
    )
    context, sink, container = _context(service)

    with pytest.raises(
        ToolError,
        match="Polaris governance review-state request failed",
    ) as caught:
        await execute_governance_review_states_list(
            GovernanceReviewStatesListRequest(),
            context,
        )

    assert "postgresql://" not in str(caught.value)
    assert redaction_probe not in str(caught.value)
    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "application"
    assert sink.events[-1].attributes["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_governance_review_states_list_preserves_cancellation() -> None:
    service = _FakeGovernanceReviewStateService(asyncio.CancelledError())
    context, sink, container = _context(service)

    with pytest.raises(asyncio.CancelledError):
        await execute_governance_review_states_list(
            GovernanceReviewStatesListRequest(),
            context,
        )

    assert container.scopes[0].closed is True
    assert sink.events[-1].event_type == "mcp.tool.failed"
    assert sink.events[-1].attributes["failure_category"] == "cancelled"


@pytest.mark.parametrize(
    "field_name",
    (
        "approve",
        "deny",
        "override",
        "accept_residual_risk",
        "mutate_review_state",
        "bypass_review",
    ),
)
def test_governance_review_states_request_rejects_mutation_attempts(
    field_name: str,
) -> None:
    with pytest.raises(ValidationError):
        GovernanceReviewStatesListRequest.model_validate({field_name: True})


def test_governance_review_states_list_is_registered_read_only_idempotent() -> None:
    from mcp_server.server import server

    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    tool = tools["polaris_governance_review_states_list"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.fn_metadata.output_model is not None
    assert tool.fn_metadata.output_model.__name__ == (
        "GovernanceReviewStatesListResponse"
    )


def _review_state(*, task_id: str = "task-1") -> GovernanceReviewState:
    subject = AutomatedDecisionSubject("recommendation", "rec-1")
    evidence = AutomatedDecisionEvidenceReference("packet-1", 1)
    authority = classify_risk_authority(recommendation_explanation_authority_input())
    authority_metadata = authority_metadata_from_contract(authority)
    reviewer = GovernanceReviewerIdentity(
        reviewer_id="reviewer-1",
        actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
        display_name="Reviewer One",
    )
    audit_record = AutomatedGovernanceAuditRecord(
        audit_record_id=f"automated_governance_audit:{task_id}",
        subject=subject,
        risk_tier=authority.risk_tier,
        authority_metadata=authority_metadata,
        evidence=evidence,
        outcome=AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL,
        rule_name="authority_metadata_governance",
        timestamp=_CREATED_AT,
        reason="vigilant_authority_requires_approval",
        message="Vigilant authority requires review.",
        metadata={"password": _redaction_probe_value()},
    )
    task = GovernanceReviewTaskRecord(
        review_task_id=f"governance_review_task:{task_id}",
        automated_governance_audit_record_id=audit_record.audit_record_id,
        subject=subject,
        risk_tier=authority.risk_tier,
        authority_metadata=authority_metadata,
        review_scope="recommendation",
        intended_sink="recommendation",
        requested_action="vigilant_authority_requires_approval",
        status=GovernanceReviewTaskStatus.APPROVED,
        evidence=evidence,
        evidence_references={
            "api_key": _redaction_probe_value(),
            "packet": "packet-1",
        },
        created_at=_CREATED_AT,
        updated_at=_UPDATED_AT,
    )
    decision = GovernanceReviewDecisionRecord(
        review_decision_id=f"governance_review_decision:{task_id}",
        review_task_id=task.review_task_id,
        automated_governance_audit_record_id=audit_record.audit_record_id,
        subject=subject,
        risk_tier=authority.risk_tier,
        outcome=GovernanceReviewDecisionOutcome.APPROVED,
        reviewer=reviewer,
        rationale="Evidence supports the scoped recommendation.",
        review_scope=task.review_scope,
        evidence=evidence,
        decided_at=_DECIDED_AT,
    )
    acceptance = GovernanceResidualRiskAcceptanceRecord(
        acceptance_id=f"governance_residual_risk_acceptance:{task_id}",
        review_task_id=task.review_task_id,
        subject=subject,
        risk_tier=authority.risk_tier,
        reviewer=reviewer,
        rationale="Residual risk is scoped and accepted.",
        review_scope=task.review_scope,
        residual_risk_scope="material_recommendation_claims",
        evidence=evidence,
        accepted_at=_ACCEPTED_AT,
    )
    return GovernanceReviewState(
        task=task,
        approval_state=GovernanceReviewApprovalState.REVIEW_APPROVED,
        automated_decision=audit_record,
        audit_history=(decision,),
        residual_risk_acceptances=(acceptance,),
    )
