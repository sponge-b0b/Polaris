from __future__ import annotations

from typing import Any, cast

from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditOutcome,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditOutcome,
    AutomatedPolicyAuditRecord,
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
