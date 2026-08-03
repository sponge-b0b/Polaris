from __future__ import annotations

from typing import Any, cast

from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceResidualRiskAcceptanceModel,
    GovernanceReviewDecisionModel,
    GovernanceReviewTaskModel,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditOutcome,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditOutcome,
    AutomatedPolicyAuditRecord,
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionOutcome,
    GovernanceReviewDecisionRecord,
    GovernanceReviewerActorType,
    GovernanceReviewerIdentity,
    GovernanceReviewTaskRecord,
    GovernanceReviewTaskStatus,
    JsonObject,
)
from domain.authority import RiskTier


class AutomatedDecisionAuditPersistenceSerializer:
    """Serialize automated policy/governance audit records at the DB boundary."""

    @staticmethod
    def policy_values(record: AutomatedPolicyAuditRecord) -> dict[str, Any]:
        return {
            "audit_record_id": record.audit_record_id,
            "subject_type": record.subject_type,
            "subject_id": record.subject_id,
            "risk_tier": record.risk_tier.value,
            "authority_metadata": dict(record.authority_metadata),
            "evidence_packet_id": record.evidence_packet_id,
            "evidence_packet_version": record.evidence_packet_version,
            "outcome": record.outcome.value,
            "policy_name": record.policy_name,
            "reason": record.reason,
            "message": record.message,
            "metadata_payload": dict(record.metadata),
            "timestamp": record.timestamp,
        }

    @staticmethod
    def governance_values(record: AutomatedGovernanceAuditRecord) -> dict[str, Any]:
        return {
            "audit_record_id": record.audit_record_id,
            "subject_type": record.subject_type,
            "subject_id": record.subject_id,
            "risk_tier": record.risk_tier.value,
            "authority_metadata": dict(record.authority_metadata),
            "evidence_packet_id": record.evidence_packet_id,
            "evidence_packet_version": record.evidence_packet_version,
            "outcome": record.outcome.value,
            "rule_name": record.rule_name,
            "reason": record.reason,
            "message": record.message,
            "metadata_payload": dict(record.metadata),
            "timestamp": record.timestamp,
        }

    @staticmethod
    def review_task_values(task: GovernanceReviewTaskRecord) -> dict[str, Any]:
        return {
            "review_task_id": task.review_task_id,
            "automated_governance_audit_record_id": (
                task.automated_governance_audit_record_id
            ),
            "subject_type": task.subject_type,
            "subject_id": task.subject_id,
            "risk_tier": task.risk_tier.value,
            "authority_metadata": dict(task.authority_metadata),
            "review_scope": task.review_scope,
            "intended_sink": task.intended_sink,
            "requested_action": task.requested_action,
            "status": task.status.value,
            "evidence_packet_id": task.evidence_packet_id,
            "evidence_packet_version": task.evidence_packet_version,
            "evidence_references": dict(task.evidence_references),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    @staticmethod
    def review_decision_values(
        decision: GovernanceReviewDecisionRecord,
    ) -> dict[str, Any]:
        return {
            "review_decision_id": decision.review_decision_id,
            "review_task_id": decision.review_task_id,
            "automated_governance_audit_record_id": (
                decision.automated_governance_audit_record_id
            ),
            "subject_type": decision.subject_type,
            "subject_id": decision.subject_id,
            "risk_tier": decision.risk_tier.value,
            "outcome": decision.outcome.value,
            "reviewer_id": decision.reviewer.reviewer_id,
            "reviewer_actor_type": decision.reviewer.actor_type.value,
            "reviewer_display_name": decision.reviewer.display_name,
            "rationale": decision.rationale,
            "review_scope": decision.review_scope,
            "evidence_packet_id": decision.evidence_packet_id,
            "evidence_packet_version": decision.evidence_packet_version,
            "resulting_task_status": decision.resulting_task_status_value,
            "requested_remediation": decision.requested_remediation,
            "residual_risk_acceptance_required": (
                decision.residual_risk_acceptance_required
            ),
            "residual_risk_acceptance_id": decision.residual_risk_acceptance_id,
            "metadata_payload": dict(decision.metadata),
            "decided_at": decision.decided_at,
        }

    @staticmethod
    def residual_risk_acceptance_values(
        acceptance: GovernanceResidualRiskAcceptanceRecord,
    ) -> dict[str, Any]:
        return {
            "acceptance_id": acceptance.acceptance_id,
            "review_task_id": acceptance.review_task_id,
            "subject_type": acceptance.subject_type,
            "subject_id": acceptance.subject_id,
            "risk_tier": acceptance.risk_tier.value,
            "reviewer_id": acceptance.reviewer.reviewer_id,
            "reviewer_actor_type": acceptance.reviewer.actor_type.value,
            "reviewer_display_name": acceptance.reviewer.display_name,
            "rationale": acceptance.rationale,
            "review_scope": acceptance.review_scope,
            "residual_risk_scope": acceptance.residual_risk_scope,
            "evidence_packet_id": acceptance.evidence_packet_id,
            "evidence_packet_version": acceptance.evidence_packet_version,
            "metadata_payload": dict(acceptance.metadata),
            "accepted_at": acceptance.accepted_at,
        }

    @staticmethod
    def policy_record_from_model(
        model: AutomatedPolicyAuditRecordModel,
    ) -> AutomatedPolicyAuditRecord:
        return AutomatedPolicyAuditRecord(
            audit_record_id=model.audit_record_id,
            subject=AutomatedDecisionSubject(
                subject_type=model.subject_type,
                subject_id=model.subject_id,
            ),
            risk_tier=RiskTier(model.risk_tier),
            authority_metadata=cast(JsonObject, model.authority_metadata),
            evidence=_evidence_from_model(
                model.evidence_packet_id,
                model.evidence_packet_version,
            ),
            outcome=AutomatedPolicyAuditOutcome(model.outcome),
            policy_name=model.policy_name,
            reason=model.reason,
            message=model.message,
            metadata=cast(JsonObject, model.metadata_payload),
            timestamp=model.timestamp,
        )

    @staticmethod
    def governance_record_from_model(
        model: AutomatedGovernanceAuditRecordModel,
    ) -> AutomatedGovernanceAuditRecord:
        return AutomatedGovernanceAuditRecord(
            audit_record_id=model.audit_record_id,
            subject=AutomatedDecisionSubject(
                subject_type=model.subject_type,
                subject_id=model.subject_id,
            ),
            risk_tier=RiskTier(model.risk_tier),
            authority_metadata=cast(JsonObject, model.authority_metadata),
            evidence=_evidence_from_model(
                model.evidence_packet_id,
                model.evidence_packet_version,
            ),
            outcome=AutomatedGovernanceAuditOutcome(model.outcome),
            rule_name=model.rule_name,
            reason=model.reason,
            message=model.message,
            metadata=cast(JsonObject, model.metadata_payload),
            timestamp=model.timestamp,
        )

    @staticmethod
    def review_task_from_model(
        model: GovernanceReviewTaskModel,
    ) -> GovernanceReviewTaskRecord:
        return GovernanceReviewTaskRecord(
            review_task_id=model.review_task_id,
            automated_governance_audit_record_id=(
                model.automated_governance_audit_record_id
            ),
            subject=AutomatedDecisionSubject(
                subject_type=model.subject_type,
                subject_id=model.subject_id,
            ),
            risk_tier=RiskTier(model.risk_tier),
            authority_metadata=cast(JsonObject, model.authority_metadata),
            review_scope=model.review_scope,
            intended_sink=model.intended_sink,
            requested_action=model.requested_action,
            status=GovernanceReviewTaskStatus(model.status),
            evidence=AutomatedDecisionEvidenceReference(
                packet_id=model.evidence_packet_id,
                packet_version=model.evidence_packet_version,
            ),
            evidence_references=cast(JsonObject, model.evidence_references),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def review_decision_from_model(
        model: GovernanceReviewDecisionModel,
    ) -> GovernanceReviewDecisionRecord:
        return GovernanceReviewDecisionRecord(
            review_decision_id=model.review_decision_id,
            review_task_id=model.review_task_id,
            automated_governance_audit_record_id=(
                model.automated_governance_audit_record_id
            ),
            subject=AutomatedDecisionSubject(
                subject_type=model.subject_type,
                subject_id=model.subject_id,
            ),
            risk_tier=RiskTier(model.risk_tier),
            outcome=GovernanceReviewDecisionOutcome(model.outcome),
            reviewer=GovernanceReviewerIdentity(
                reviewer_id=model.reviewer_id,
                actor_type=GovernanceReviewerActorType(model.reviewer_actor_type),
                display_name=model.reviewer_display_name,
            ),
            rationale=model.rationale,
            review_scope=model.review_scope,
            evidence=AutomatedDecisionEvidenceReference(
                packet_id=model.evidence_packet_id,
                packet_version=model.evidence_packet_version,
            ),
            resulting_task_status=GovernanceReviewTaskStatus(
                model.resulting_task_status,
            ),
            requested_remediation=model.requested_remediation,
            residual_risk_acceptance_required=(model.residual_risk_acceptance_required),
            residual_risk_acceptance_id=model.residual_risk_acceptance_id,
            metadata=cast(JsonObject, model.metadata_payload),
            decided_at=model.decided_at,
        )

    @staticmethod
    def residual_risk_acceptance_from_model(
        model: GovernanceResidualRiskAcceptanceModel,
    ) -> GovernanceResidualRiskAcceptanceRecord:
        return GovernanceResidualRiskAcceptanceRecord(
            acceptance_id=model.acceptance_id,
            review_task_id=model.review_task_id,
            subject=AutomatedDecisionSubject(
                subject_type=model.subject_type,
                subject_id=model.subject_id,
            ),
            risk_tier=RiskTier(model.risk_tier),
            reviewer=GovernanceReviewerIdentity(
                reviewer_id=model.reviewer_id,
                actor_type=GovernanceReviewerActorType(model.reviewer_actor_type),
                display_name=model.reviewer_display_name,
            ),
            rationale=model.rationale,
            review_scope=model.review_scope,
            residual_risk_scope=model.residual_risk_scope,
            evidence=AutomatedDecisionEvidenceReference(
                packet_id=model.evidence_packet_id,
                packet_version=model.evidence_packet_version,
            ),
            metadata=cast(JsonObject, model.metadata_payload),
            accepted_at=model.accepted_at,
        )


def _evidence_from_model(
    packet_id: str | None,
    packet_version: int | None,
) -> AutomatedDecisionEvidenceReference | None:
    if packet_id is None:
        return None
    if packet_version is None:
        raise ValueError("evidence_packet_version is required with evidence_packet_id.")
    return AutomatedDecisionEvidenceReference(
        packet_id=packet_id,
        packet_version=packet_version,
    )
