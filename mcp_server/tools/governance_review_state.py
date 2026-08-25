"""Thin MCP boundary for canonical governance review-state queries."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import cast

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import JsonValue

from application.governance import (
    AutomatedDecisionAuditService,
    GovernanceReviewState,
    GovernanceReviewTaskQuery,
)
from core.security.sensitive_data import sanitize_sensitive_mapping
from core.storage.persistence.governance_audit import (
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionRecord,
)
from mcp_server.contracts.models import (
    GovernanceResidualRiskAcceptanceSummary,
    GovernanceReviewDecisionSummary,
    GovernanceReviewStatesListRequest,
    GovernanceReviewStatesListResponse,
    GovernanceReviewStateSummary,
)
from mcp_server.lifespan import McpApplicationContext
from mcp_server.request_scope import mcp_dependency_scope
from mcp_server.telemetry import McpToolFailureCategory

logger = logging.getLogger(__name__)

_TOOL_NAME = "polaris_governance_review_states_list"
_SAFE_FAILURE_MESSAGE = "Polaris governance review-state request failed."


class McpGovernanceReviewStatePolicyError(ValueError):
    """Safe validation failure raised by the governance review-state boundary."""


async def execute_governance_review_states_list(
    request: GovernanceReviewStatesListRequest,
    application_context: McpApplicationContext,
    *,
    request_id: str | None = None,
) -> GovernanceReviewStatesListResponse:
    """List canonical governance review states without exposing mutation paths."""

    invocation = await application_context.telemetry.tool_started(
        tool_name=_TOOL_NAME,
        transport=application_context.settings.transport,
        request_id=request_id,
        page_size=request.limit,
    )
    try:
        _validate_request_policy(request, application_context)
        query = _to_query(request)
        async with mcp_dependency_scope(
            application_context,
            AutomatedDecisionAuditService,
        ) as service:
            states = await service.list_governance_review_states(query)
        response = _to_response(tuple(states), request=request)
    except asyncio.CancelledError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.CANCELLED,
            error=exc,
        )
        raise
    except McpGovernanceReviewStatePolicyError as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.VALIDATION,
            error=exc,
        )
        logger.warning(
            "MCP governance review-state request rejected by boundary policy.",
            extra={"request_id": invocation.request_id},
        )
        raise ToolError(str(exc)) from exc
    except Exception as exc:
        await application_context.telemetry.tool_failed(
            invocation,
            failure_category=McpToolFailureCategory.APPLICATION,
            error=exc,
        )
        logger.error(
            "MCP governance review-state request failed.",
            extra={
                "request_id": invocation.request_id,
                "error_type": type(exc).__name__,
            },
        )
        raise ToolError(_SAFE_FAILURE_MESSAGE) from exc

    await application_context.telemetry.tool_completed(
        invocation,
        result_status="succeeded",
    )
    return response


def _validate_request_policy(
    request: GovernanceReviewStatesListRequest,
    application_context: McpApplicationContext,
) -> None:
    max_page_size = application_context.settings.max_page_size
    if request.limit > max_page_size:
        raise McpGovernanceReviewStatePolicyError(
            f"limit cannot exceed {max_page_size}.",
        )


def _to_query(request: GovernanceReviewStatesListRequest) -> GovernanceReviewTaskQuery:
    return GovernanceReviewTaskQuery(
        subject_type=request.subject_type,
        subject_id=request.subject_id,
        risk_tier=request.risk_tier,
        status=request.status,
        approval_state=request.approval_state,
        review_scope=request.review_scope,
        intended_sink=request.intended_sink,
        requested_action=request.requested_action,
        evidence_packet_id=request.evidence_packet_id,
        evidence_packet_version=request.evidence_packet_version,
        closed=request.closed,
    )


def _to_response(
    states: tuple[GovernanceReviewState, ...],
    *,
    request: GovernanceReviewStatesListRequest,
) -> GovernanceReviewStatesListResponse:
    total_count = len(states)
    page = states[request.offset : request.offset + request.limit]
    next_offset = request.offset + len(page)
    has_more = next_offset < total_count

    return GovernanceReviewStatesListResponse(
        review_states=tuple(_to_state_summary(state) for state in page),
        total_count=total_count,
        offset=request.offset,
        limit=request.limit,
        has_more=has_more,
        next_offset=next_offset if has_more else None,
    )


def _to_state_summary(state: GovernanceReviewState) -> GovernanceReviewStateSummary:
    task = state.task
    automated_decision = state.automated_decision
    return GovernanceReviewStateSummary(
        review_task_id=task.review_task_id,
        subject_type=task.subject_type,
        subject_id=task.subject_id,
        risk_tier=task.risk_tier.value,
        status=task.status.value,
        approval_state=state.approval_state.value,
        review_scope=task.review_scope,
        intended_sink=task.intended_sink,
        requested_action=task.requested_action,
        evidence_packet_id=task.evidence_packet_id,
        evidence_packet_version=task.evidence_packet_version,
        closed=state.closed,
        created_at=task.created_at,
        updated_at=task.updated_at,
        automated_governance_audit_record_id=(
            automated_decision.audit_record_id
            if automated_decision is not None
            else task.automated_governance_audit_record_id
        ),
        automated_governance_outcome=(
            automated_decision.outcome.value if automated_decision is not None else None
        ),
        automated_governance_reason=(
            automated_decision.reason if automated_decision is not None else None
        ),
        authority_metadata=_sanitize_mapping(task.authority_metadata),
        evidence_references=_sanitize_mapping(task.evidence_references),
        audit_history=tuple(
            _to_decision_summary(decision) for decision in state.audit_history
        ),
        residual_risk_acceptances=tuple(
            _to_acceptance_summary(acceptance)
            for acceptance in state.residual_risk_acceptances
        ),
    )


def _to_decision_summary(
    decision: GovernanceReviewDecisionRecord,
) -> GovernanceReviewDecisionSummary:
    return GovernanceReviewDecisionSummary(
        review_decision_id=decision.review_decision_id,
        outcome=decision.outcome.value,
        reviewer_id=decision.reviewer.reviewer_id,
        reviewer_actor_type=decision.reviewer.actor_type.value,
        review_scope=decision.review_scope,
        evidence_packet_id=decision.evidence_packet_id,
        evidence_packet_version=decision.evidence_packet_version,
        decided_at=decision.decided_at,
        resulting_task_status=decision.resulting_task_status_value,
        residual_risk_acceptance_required=(decision.residual_risk_acceptance_required),
        residual_risk_acceptance_id=decision.residual_risk_acceptance_id,
        requested_remediation=decision.requested_remediation,
    )


def _to_acceptance_summary(
    acceptance: GovernanceResidualRiskAcceptanceRecord,
) -> GovernanceResidualRiskAcceptanceSummary:
    return GovernanceResidualRiskAcceptanceSummary(
        acceptance_id=acceptance.acceptance_id,
        reviewer_id=acceptance.reviewer.reviewer_id,
        reviewer_actor_type=acceptance.reviewer.actor_type.value,
        review_scope=acceptance.review_scope,
        residual_risk_scope=acceptance.residual_risk_scope,
        evidence_packet_id=acceptance.evidence_packet_id,
        evidence_packet_version=acceptance.evidence_packet_version,
        accepted_at=acceptance.accepted_at,
    )


def _sanitize_mapping(value: object) -> dict[str, JsonValue]:
    return cast(
        dict[str, JsonValue],
        sanitize_sensitive_mapping(value if isinstance(value, Mapping) else {}),
    )


__all__ = ["execute_governance_review_states_list"]
