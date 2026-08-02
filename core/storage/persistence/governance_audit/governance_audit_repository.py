from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.governance_audit.governance_audit_models import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditRecord,
)


class AutomatedDecisionAuditRepository(Protocol):
    """Repository for authoritative automated policy/governance audit records."""

    async def persist_policy_audit_record(
        self,
        record: AutomatedPolicyAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def persist_governance_audit_record(
        self,
        record: AutomatedGovernanceAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult: ...

    async def get_policy_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedPolicyAuditRecord | None: ...

    async def get_governance_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedGovernanceAuditRecord | None: ...

    async def list_policy_audit_records(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        outcome: str | None = None,
        policy_name: str | None = None,
        evidence_packet_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AutomatedPolicyAuditRecord]: ...

    async def list_governance_audit_records(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        outcome: str | None = None,
        rule_name: str | None = None,
        evidence_packet_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AutomatedGovernanceAuditRecord]: ...
