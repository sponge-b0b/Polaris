from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

import pytest

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


def test_governance_review_task_serializer_round_trips_work_queue_record() -> None:
    task = _review_task_record()
    model = GovernanceReviewTaskModel(
        **AutomatedDecisionAuditPersistenceSerializer.review_task_values(task)
    )

    round_tripped = AutomatedDecisionAuditPersistenceSerializer.review_task_from_model(
        model,
    )

    assert round_tripped == task
    assert round_tripped.status is GovernanceReviewTaskStatus.PENDING
    assert round_tripped.evidence_packet_id == "packet-1"
    assert round_tripped.evidence_references["evidence_packet"] == {
        "packet_id": "packet-1",
        "packet_version": 1,
    }


def test_review_decision_serializer_round_trips_immutable_audit_entry() -> None:
    decision = _review_decision_record()
    model = GovernanceReviewDecisionModel(
        **AutomatedDecisionAuditPersistenceSerializer.review_decision_values(decision)
    )

    round_tripped = (
        AutomatedDecisionAuditPersistenceSerializer.review_decision_from_model(model)
    )

    assert round_tripped == decision
    assert round_tripped.outcome is GovernanceReviewDecisionOutcome.APPROVED
    assert round_tripped.resulting_task_status is GovernanceReviewTaskStatus.APPROVED
    assert round_tripped.requested_remediation is None
    assert round_tripped.reviewer == _reviewer()
    assert round_tripped.evidence_packet_version == 1


@pytest.mark.parametrize(
    ("outcome", "status", "requested_remediation"),
    (
        (
            GovernanceReviewDecisionOutcome.CONTESTED,
            GovernanceReviewTaskStatus.CONTESTED,
            "Resolve the disputed claim before publication.",
        ),
        (
            GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
            GovernanceReviewTaskStatus.CHANGES_REQUESTED,
            "Regenerate the packet with fresh evidence.",
        ),
        (
            GovernanceReviewDecisionOutcome.OVERRIDDEN,
            GovernanceReviewTaskStatus.OVERRIDDEN,
            None,
        ),
    ),
)
def test_review_decision_serializer_round_trips_contestable_audit_outcomes(
    outcome: GovernanceReviewDecisionOutcome,
    status: GovernanceReviewTaskStatus,
    requested_remediation: str | None,
) -> None:
    decision = _review_decision_record(
        outcome=outcome,
        requested_remediation=requested_remediation,
    )
    model = GovernanceReviewDecisionModel(
        **AutomatedDecisionAuditPersistenceSerializer.review_decision_values(decision)
    )

    round_tripped = (
        AutomatedDecisionAuditPersistenceSerializer.review_decision_from_model(model)
    )

    assert round_tripped == decision
    assert round_tripped.outcome is outcome
    assert round_tripped.resulting_task_status is status
    assert round_tripped.requested_remediation == requested_remediation


def test_residual_risk_acceptance_serializer_round_trips_scoped_record() -> None:
    acceptance = _residual_risk_acceptance_record()
    model = GovernanceResidualRiskAcceptanceModel(
        **AutomatedDecisionAuditPersistenceSerializer.residual_risk_acceptance_values(
            acceptance,
        )
    )

    round_tripped = (
        AutomatedDecisionAuditPersistenceSerializer.residual_risk_acceptance_from_model(
            model,
        )
    )

    assert round_tripped == acceptance
    assert round_tripped.reviewer == _reviewer()
    assert round_tripped.residual_risk_scope == "recommendation publication only"
    assert round_tripped.evidence_packet_version == 1


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


def test_contest_and_request_changes_require_requested_remediation() -> None:
    for outcome in (
        GovernanceReviewDecisionOutcome.CONTESTED,
        GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
    ):
        with pytest.raises(ValueError, match="requested remediation"):
            _review_decision_record(outcome=outcome)


def test_resulting_status_must_match_human_review_outcome() -> None:
    with pytest.raises(ValueError, match="resulting_task_status"):
        GovernanceReviewDecisionRecord(
            review_decision_id="governance-review-decision-1",
            review_task_id="governance-review-task-1",
            automated_governance_audit_record_id="governance-audit-require_approval",
            subject=AutomatedDecisionSubject("recommendation", "rec-1"),
            risk_tier=RiskTier.VIGILANT,
            outcome=GovernanceReviewDecisionOutcome.CONTESTED,
            reviewer=_reviewer(),
            rationale="Human reviewed decision evidence.",
            review_scope="recommendation",
            evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
            decided_at=datetime(2026, 8, 2, 13, 0, tzinfo=UTC),
            resulting_task_status=GovernanceReviewTaskStatus.APPROVED,
            requested_remediation="Resolve the disputed claim.",
        )


def test_nonhuman_review_metadata_cannot_claim_contest_override_or_clear() -> None:
    for metadata in (
        {"contest": True},
        {"override": True},
        {"clear_review_task": True},
        {"satisfy_review_task": True},
    ):
        with pytest.raises(ValueError, match="non-human governance review metadata"):
            _review_decision_record(metadata=metadata)


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


def _review_task_record() -> GovernanceReviewTaskRecord:
    return GovernanceReviewTaskRecord(
        review_task_id="governance-review-task-1",
        automated_governance_audit_record_id="governance-audit-require_approval",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        authority_metadata=authority_metadata_for_tier(RiskTier.VIGILANT),
        review_scope="recommendation",
        intended_sink="recommendation",
        requested_action="vigilant_authority_requires_approval",
        status=GovernanceReviewTaskStatus.PENDING,
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        evidence_references={
            "automated_governance_audit_record_id": "governance-audit-require_approval",
            "evidence_packet": {"packet_id": "packet-1", "packet_version": 1},
        },
        created_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def _review_decision_record(
    *,
    outcome: GovernanceReviewDecisionOutcome = GovernanceReviewDecisionOutcome.APPROVED,
    requested_remediation: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> GovernanceReviewDecisionRecord:
    return GovernanceReviewDecisionRecord(
        review_decision_id=f"governance-review-decision-{outcome.value}",
        review_task_id="governance-review-task-1",
        automated_governance_audit_record_id="governance-audit-require_approval",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        outcome=outcome,
        reviewer=_reviewer(),
        rationale="Human reviewed decision evidence.",
        review_scope="recommendation",
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        requested_remediation=requested_remediation,
        metadata=metadata or {},
        decided_at=datetime(2026, 8, 2, 13, 0, tzinfo=UTC),
    )


def _residual_risk_acceptance_record() -> GovernanceResidualRiskAcceptanceRecord:
    return GovernanceResidualRiskAcceptanceRecord(
        acceptance_id="governance-residual-risk-acceptance-1",
        review_task_id="governance-review-task-1",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        reviewer=_reviewer(),
        rationale="Accept residual downside risk for this output.",
        review_scope="recommendation",
        residual_risk_scope="recommendation publication only",
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        accepted_at=datetime(2026, 8, 2, 13, 5, tzinfo=UTC),
    )


def _reviewer() -> GovernanceReviewerIdentity:
    return GovernanceReviewerIdentity(
        reviewer_id="reviewer-1",
        actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
        display_name="Jane Reviewer",
    )
