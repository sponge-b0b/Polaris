from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
)
from core.storage.persistence.serializers import (
    AutomatedDecisionAuditPersistenceSerializer,
)
from domain.authority import RiskTier
from tests.helpers.risk_authority_examples import authority_metadata_for_tier


@pytest.mark.parametrize("outcome", tuple(AutomatedPolicyAuditOutcome))
def test_policy_audit_serializer_round_trips_authoritative_postgres_record(
    outcome: AutomatedPolicyAuditOutcome,
) -> None:
    record = _policy_record(outcome)
    model = AutomatedPolicyAuditRecordModel(
        **AutomatedDecisionAuditPersistenceSerializer.policy_values(record)
    )

    round_tripped = (
        AutomatedDecisionAuditPersistenceSerializer.policy_record_from_model(
            model,
        )
    )

    assert round_tripped == record
    assert round_tripped.outcome is outcome
    assert round_tripped.evidence_packet_id == "packet-1"
    assert round_tripped.evidence_packet_version == 1


@pytest.mark.parametrize("outcome", tuple(AutomatedGovernanceAuditOutcome))
def test_governance_audit_serializer_persists_all_governance_outcomes(
    outcome: AutomatedGovernanceAuditOutcome,
) -> None:
    record = _governance_record(outcome)
    model = AutomatedGovernanceAuditRecordModel(
        **AutomatedDecisionAuditPersistenceSerializer.governance_values(record)
    )

    round_tripped = (
        AutomatedDecisionAuditPersistenceSerializer.governance_record_from_model(model)
    )

    assert round_tripped == record
    assert round_tripped.outcome is outcome


def test_model_authority_claims_cannot_be_authoritative_audit_metadata() -> None:
    metadata = {
        **authority_metadata_for_tier(RiskTier.BASELINE),
        "production_ready": True,
    }

    with pytest.raises(ValueError, match="production_ready"):
        AutomatedPolicyAuditRecord(
            audit_record_id="policy-audit-1",
            subject=AutomatedDecisionSubject("recommendation", "rec-1"),
            risk_tier=RiskTier.BASELINE,
            authority_metadata=metadata,
            evidence=None,
            outcome=AutomatedPolicyAuditOutcome.ALLOW,
            policy_name="policy",
            timestamp=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
        )


def test_nested_model_authority_claims_cannot_be_authoritative_audit_metadata() -> None:
    metadata = {
        **authority_metadata_for_tier(RiskTier.BASELINE),
        "nested": [{"approved": True}],
    }

    with pytest.raises(ValueError, match="approved"):
        AutomatedGovernanceAuditRecord(
            audit_record_id="governance-audit-1",
            subject=AutomatedDecisionSubject("recommendation", "rec-1"),
            risk_tier=RiskTier.BASELINE,
            authority_metadata=metadata,
            evidence=None,
            outcome=AutomatedGovernanceAuditOutcome.ALLOW,
            rule_name="rule",
            timestamp=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
        )


def _policy_record(
    outcome: AutomatedPolicyAuditOutcome,
) -> AutomatedPolicyAuditRecord:
    return AutomatedPolicyAuditRecord(
        audit_record_id="policy-audit-1",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.ENHANCED,
        authority_metadata=authority_metadata_for_tier(RiskTier.ENHANCED),
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        outcome=outcome,
        policy_name="capital_policy",
        reason="policy_reason",
        message="policy message",
        metadata={"policy_version": "2026-08-02"},
        timestamp=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def _governance_record(
    outcome: AutomatedGovernanceAuditOutcome,
) -> AutomatedGovernanceAuditRecord:
    return AutomatedGovernanceAuditRecord(
        audit_record_id=f"governance-audit-{outcome.value}",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        authority_metadata=authority_metadata_for_tier(RiskTier.VIGILANT),
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        outcome=outcome,
        rule_name="authority_metadata_governance",
        reason="governance_reason",
        message="governance message",
        metadata={"rule_version": "2026-08-02"},
        timestamp=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )
