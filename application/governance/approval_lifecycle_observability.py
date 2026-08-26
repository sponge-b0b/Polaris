from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditRecord,
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionOutcome,
    GovernanceReviewDecisionRecord,
    GovernanceReviewTaskRecord,
    JsonObject,
)
from core.telemetry.events.telemetry_event import TelemetryEvent, TelemetryEventLevel
from core.telemetry.events.telemetry_exception_details import TelemetryExceptionDetails
from core.telemetry.observability import ObservabilityManager
from core.telemetry.tracing import TraceContext
from domain.authority import RiskAuthorityContract, RiskTier

logger = logging.getLogger(__name__)

_APPROVAL_LIFECYCLE_SOURCE = "application.governance.approval_lifecycle"
_APPROVAL_LIFECYCLE_EVENT_PREFIX = "governance.approval_lifecycle"
_APPROVAL_LIFECYCLE_EVENTS_TOTAL = "governance.approval_lifecycle.events.total"
_APPROVAL_LIFECYCLE_FAILURES_TOTAL = "governance.approval_lifecycle.failures.total"
_APPROVAL_LIFECYCLE_REQUIRED_TOTAL = (
    "governance.approval_lifecycle.required_approvals.total"
)
_APPROVAL_LIFECYCLE_BLOCKED_RELEASES_TOTAL = (
    "governance.approval_lifecycle.blocked_releases.total"
)

_REVIEW_OUTCOME_TO_LIFECYCLE_OUTCOME = {
    GovernanceReviewDecisionOutcome.APPROVED: "approved",
    GovernanceReviewDecisionOutcome.DENIED: "denied",
    GovernanceReviewDecisionOutcome.CONTESTED: "contested",
    GovernanceReviewDecisionOutcome.CHANGES_REQUESTED: "changes_requested",
    GovernanceReviewDecisionOutcome.OVERRIDDEN: "override",
}


class ApprovalLifecycleObservability:
    """Application-owned observability for governance approval lifecycle events."""

    def __init__(
        self,
        observability_manager: ObservabilityManager | None,
    ) -> None:
        self._observability_manager = observability_manager

    async def required_approval(
        self,
        *,
        record: AutomatedGovernanceAuditRecord,
        task: GovernanceReviewTaskRecord,
        trace_context: TraceContext | None,
    ) -> None:
        attributes = {
            **_governance_record_attributes(record),
            **_review_task_attributes(task),
            "decision_kind": "automated_governance",
            "lifecycle_outcome": "required_approval",
            "governance_outcome": record.outcome.value,
        }
        await self._record(
            lifecycle_outcome="required_approval",
            level=TelemetryEventLevel.WARNING,
            success=True,
            attributes=attributes,
            payload={
                **attributes,
                "message": record.message,
                "reason": record.reason,
            },
            trace_context=trace_context,
            metric_names=(_APPROVAL_LIFECYCLE_REQUIRED_TOTAL,),
        )

    async def automated_governance_outcome(
        self,
        *,
        record: AutomatedGovernanceAuditRecord,
        lifecycle_outcome: str,
        trace_context: TraceContext | None,
    ) -> None:
        attributes = {
            **_governance_record_attributes(record),
            "decision_kind": "automated_governance",
            "lifecycle_outcome": lifecycle_outcome,
            "governance_outcome": record.outcome.value,
            "policy_governance_separation": "governance_only",
        }
        await self._record(
            lifecycle_outcome=lifecycle_outcome,
            level=TelemetryEventLevel.WARNING,
            success=True,
            attributes=attributes,
            payload={
                **attributes,
                "message": record.message,
                "reason": record.reason,
            },
            trace_context=trace_context,
        )

    async def review_resolution(
        self,
        *,
        task: GovernanceReviewTaskRecord,
        decision: GovernanceReviewDecisionRecord,
        residual_risk_acceptance: GovernanceResidualRiskAcceptanceRecord | None,
        trace_context: TraceContext | None,
    ) -> None:
        lifecycle_outcome = _REVIEW_OUTCOME_TO_LIFECYCLE_OUTCOME[decision.outcome]
        attributes = {
            **_review_task_attributes(task),
            **_review_decision_attributes(decision),
            "decision_kind": "human_review",
            "lifecycle_outcome": lifecycle_outcome,
            "approval_state": decision.resulting_task_status_value,
            "policy_governance_separation": "governance_review_only",
        }
        if residual_risk_acceptance is not None:
            attributes["residual_risk_acceptance_id"] = (
                residual_risk_acceptance.acceptance_id
            )
            attributes["residual_risk_scope"] = (
                residual_risk_acceptance.residual_risk_scope
            )
        await self._record(
            lifecycle_outcome=lifecycle_outcome,
            level=(
                TelemetryEventLevel.INFO
                if lifecycle_outcome in {"approved", "override"}
                else TelemetryEventLevel.WARNING
            ),
            success=True,
            attributes=attributes,
            payload={
                **attributes,
                "rationale": decision.rationale,
                "requested_remediation": decision.requested_remediation,
            },
            trace_context=trace_context,
        )

    async def blocked_release(
        self,
        *,
        authority: RiskAuthorityContract,
        subject: AutomatedDecisionSubject,
        evidence: AutomatedDecisionEvidenceReference,
        review_scope: str,
        requested_action: str,
        boundary_name: str,
        reason: str,
        approval_state: str | None,
        review_task_id: str | None,
        trace_context: TraceContext | None,
    ) -> None:
        attributes = {
            **_subject_attributes(subject),
            **_risk_authority_attributes(authority),
            **_evidence_attributes(evidence),
            "review_scope": review_scope,
            "requested_action": requested_action,
            "boundary_name": boundary_name,
            "review_task_id": review_task_id,
            "approval_state": approval_state,
            "decision_kind": "release_gate",
            "lifecycle_outcome": "blocked_release",
            "failure_reason": reason,
            "policy_governance_separation": "governance_release_gate_only",
        }
        await self._record(
            lifecycle_outcome="blocked_release",
            level=TelemetryEventLevel.WARNING,
            success=False,
            attributes=attributes,
            payload={**attributes, "reason": reason},
            trace_context=trace_context,
            metric_names=(_APPROVAL_LIFECYCLE_BLOCKED_RELEASES_TOTAL,),
        )

    async def review_failure(
        self,
        *,
        operation: str,
        reason: str,
        error: BaseException,
        trace_context: TraceContext | None,
        record: AutomatedGovernanceAuditRecord | None = None,
        task: GovernanceReviewTaskRecord | None = None,
        subject: AutomatedDecisionSubject | None = None,
        risk_tier: RiskTier | None = None,
        evidence: AutomatedDecisionEvidenceReference | None = None,
        review_task_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        traced_error = error
        if traced_error.__traceback__ is None:
            try:
                raise traced_error
            except BaseException as captured_error:  # noqa: BLE001 - preserve diagnostics.
                traced_error = captured_error

        attributes: dict[str, object] = {
            "decision_kind": "governance_review_failure",
            "lifecycle_outcome": "review_failure",
            "operation": operation,
            "failure_reason": reason,
            **dict(metadata or {}),
        }
        if record is not None:
            attributes.update(_governance_record_attributes(record))
        if task is not None:
            attributes.update(_review_task_attributes(task))
        if subject is not None:
            attributes.update(_subject_attributes(subject))
        if risk_tier is not None:
            attributes["risk_tier"] = risk_tier.value
        if evidence is not None:
            attributes.update(_evidence_attributes(evidence))
        if review_task_id is not None:
            attributes["review_task_id"] = review_task_id

        await self._record(
            lifecycle_outcome="review_failure",
            level=TelemetryEventLevel.ERROR,
            success=False,
            attributes=attributes,
            payload={
                **attributes,
                "error_type": type(traced_error).__name__,
                "error_message": str(traced_error),
            },
            trace_context=trace_context,
            error=traced_error,
            metric_names=(_APPROVAL_LIFECYCLE_FAILURES_TOTAL,),
        )

    async def _record(
        self,
        *,
        lifecycle_outcome: str,
        level: TelemetryEventLevel,
        success: bool | None,
        attributes: Mapping[str, object],
        payload: Mapping[str, object],
        trace_context: TraceContext | None,
        error: BaseException | None = None,
        metric_names: tuple[str, ...] = (),
    ) -> None:
        resolved_trace_context = self._trace_context(
            lifecycle_outcome=lifecycle_outcome,
            trace_context=trace_context,
            attributes=attributes,
        )
        self._increment(
            _APPROVAL_LIFECYCLE_EVENTS_TOTAL,
            attributes=_metric_attributes(
                lifecycle_outcome=lifecycle_outcome,
                attributes=attributes,
            ),
        )
        for metric_name in metric_names:
            self._increment(
                metric_name,
                attributes=_metric_attributes(
                    lifecycle_outcome=lifecycle_outcome,
                    attributes=attributes,
                ),
            )

        if self._observability_manager is None:
            return
        try:
            event_type = f"{_APPROVAL_LIFECYCLE_EVENT_PREFIX}.{lifecycle_outcome}"
            await self._observability_manager.emit(
                TelemetryEvent(
                    event_type=event_type,
                    source=_APPROVAL_LIFECYCLE_SOURCE,
                    level=level,
                    workflow_id=(
                        resolved_trace_context.workflow_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    execution_id=(
                        resolved_trace_context.execution_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    runtime_id=(
                        resolved_trace_context.runtime_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    node_name=(
                        resolved_trace_context.node_name
                        if resolved_trace_context is not None
                        else None
                    ),
                    correlation_id=(
                        resolved_trace_context.correlation_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    trace_id=(
                        resolved_trace_context.trace_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    span_id=(
                        resolved_trace_context.span_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    parent_span_id=(
                        resolved_trace_context.parent_span_id
                        if resolved_trace_context is not None
                        else None
                    ),
                    success=success,
                    error_count=1 if success is False else 0,
                    exception_details=(
                        TelemetryExceptionDetails.from_exception(error)
                        if error is not None
                        else None
                    ),
                    attributes={
                        **dict(attributes),
                        **_trace_attributes(resolved_trace_context),
                    },
                    payload=dict(payload),
                )
            )
        except RuntimeError:
            logger.debug(
                "governance_approval_lifecycle.telemetry_emit_failed",
                extra={
                    **dict(attributes),
                    **_trace_attributes(resolved_trace_context),
                    "event_type": event_type,
                },
                exc_info=True,
            )

    def _trace_context(
        self,
        *,
        lifecycle_outcome: str,
        trace_context: TraceContext | None,
        attributes: Mapping[str, object],
    ) -> TraceContext | None:
        if trace_context is not None:
            return trace_context.child(
                node_name="governance_approval_lifecycle",
                attributes={
                    "lifecycle_outcome": lifecycle_outcome,
                    **dict(attributes),
                },
            )
        if self._observability_manager is None:
            return None
        try:
            return self._observability_manager.create_trace_context(
                node_name="governance_approval_lifecycle",
                correlation_id=_correlation_id(attributes),
                attributes={
                    "lifecycle_outcome": lifecycle_outcome,
                    **dict(attributes),
                },
            )
        except RuntimeError:
            logger.debug(
                "governance_approval_lifecycle.trace_context_failed",
                extra=dict(attributes),
                exc_info=True,
            )
            return None

    def _increment(
        self,
        name: str,
        *,
        attributes: Mapping[str, object],
    ) -> None:
        if self._observability_manager is None:
            return
        try:
            self._observability_manager.increment(
                name,
                attributes=dict(attributes),
            )
        except RuntimeError:
            logger.debug(
                "governance_approval_lifecycle.metrics_failed",
                extra=dict(attributes),
                exc_info=True,
            )


def _governance_record_attributes(
    record: AutomatedGovernanceAuditRecord,
) -> JsonObject:
    attributes: dict[str, object] = {
        **_subject_attributes(record.subject),
        "risk_tier": record.risk_tier.value,
        "automated_governance_audit_record_id": record.audit_record_id,
        "governance_rule_name": record.rule_name,
        "governance_reason": record.reason,
        "intended_sink": _metadata_text(record.authority_metadata, "intended_sink"),
        "gate_profile": _metadata_text(record.authority_metadata, "gate_profile"),
        "authority_effect": _metadata_text(
            record.authority_metadata,
            "authority_effect",
        ),
        "source_of_truth": _metadata_text(
            record.authority_metadata,
            "source_of_truth",
        ),
    }
    if record.evidence is not None:
        attributes.update(_evidence_attributes(record.evidence))
    return attributes


def _review_task_attributes(task: GovernanceReviewTaskRecord) -> JsonObject:
    return {
        **_subject_attributes(task.subject),
        **_evidence_attributes(task.evidence),
        "risk_tier": task.risk_tier.value,
        "review_task_id": task.review_task_id,
        "automated_governance_audit_record_id": (
            task.automated_governance_audit_record_id
        ),
        "review_scope": task.review_scope,
        "requested_action": task.requested_action,
        "intended_sink": task.intended_sink,
        "review_task_status": task.status.value,
        "gate_profile": _metadata_text(task.authority_metadata, "gate_profile"),
        "authority_effect": _metadata_text(task.authority_metadata, "authority_effect"),
        "source_of_truth": _metadata_text(task.authority_metadata, "source_of_truth"),
    }


def _review_decision_attributes(
    decision: GovernanceReviewDecisionRecord,
) -> JsonObject:
    return {
        **_subject_attributes(decision.subject),
        **_evidence_attributes(decision.evidence),
        "risk_tier": decision.risk_tier.value,
        "review_decision_id": decision.review_decision_id,
        "review_task_id": decision.review_task_id,
        "review_scope": decision.review_scope,
        "review_outcome": decision.outcome.value,
        "reviewer_id": decision.reviewer.reviewer_id,
        "reviewer_actor_type": decision.reviewer.actor_type.value,
        "resulting_task_status": decision.resulting_task_status_value,
        "residual_risk_acceptance_required": (
            decision.residual_risk_acceptance_required
        ),
        "residual_risk_acceptance_id": decision.residual_risk_acceptance_id,
    }


def _subject_attributes(subject: AutomatedDecisionSubject) -> JsonObject:
    return {
        "subject_type": subject.subject_type,
        "subject_id": subject.subject_id,
    }


def _risk_authority_attributes(authority: RiskAuthorityContract) -> JsonObject:
    return {
        "risk_tier": authority.risk_tier.value,
        "authority_effect": authority.authority_effect.value,
        "content_type": authority.content_type.value,
        "canonical_owner": authority.canonical_owner.value,
        "source_of_truth": authority.source_of_truth.value,
        "intended_sink": authority.intended_sink.value,
        "gate_profile": authority.gate_profile.value,
        "capital_relevant": authority.capital_relevant,
        "durable_authority": authority.durable_authority,
        "externally_visible": authority.externally_visible,
        "governance_impact": authority.governance_impact,
        "evidence_sufficient": authority.evidence_sufficient,
    }


def _evidence_attributes(evidence: AutomatedDecisionEvidenceReference) -> JsonObject:
    return {
        "evidence_packet_id": evidence.packet_id,
        "evidence_packet_version": evidence.packet_version,
    }


def _trace_attributes(trace_context: TraceContext | None) -> JsonObject:
    if trace_context is None:
        return {}
    return {
        "trace_id": trace_context.trace_id,
        "span_id": trace_context.span_id,
        "parent_span_id": trace_context.parent_span_id,
        "correlation_id": trace_context.correlation_id,
    }


def _metric_attributes(
    *,
    lifecycle_outcome: str,
    attributes: Mapping[str, object],
) -> JsonObject:
    return {
        "lifecycle_outcome": lifecycle_outcome,
        "decision_kind": str(attributes.get("decision_kind") or "unknown"),
        "risk_tier": str(attributes.get("risk_tier") or "unknown"),
        "approval_state": str(attributes.get("approval_state") or "unknown"),
        "governance_outcome": str(attributes.get("governance_outcome") or "unknown"),
    }


def _correlation_id(attributes: Mapping[str, object]) -> str | None:
    review_task_id = attributes.get("review_task_id")
    if isinstance(review_task_id, str) and review_task_id.strip():
        return review_task_id
    subject_type = attributes.get("subject_type")
    subject_id = attributes.get("subject_id")
    if isinstance(subject_type, str) and isinstance(subject_id, str):
        return f"{subject_type}:{subject_id}"
    return None


def _metadata_text(metadata: Mapping[str, Any], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None
