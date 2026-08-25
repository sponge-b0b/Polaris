from __future__ import annotations

from core.database.base import Base
from core.database.models import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceResidualRiskAcceptanceModel,
    GovernanceReviewDecisionModel,
    GovernanceReviewTaskModel,
)


def test_automated_decision_audit_models_are_imported_into_metadata() -> None:
    assert "automated_policy_audit_records" in Base.metadata.tables
    assert "automated_governance_audit_records" in Base.metadata.tables
    assert "governance_review_tasks" in Base.metadata.tables
    assert "governance_review_decisions" in Base.metadata.tables
    assert "governance_residual_risk_acceptances" in Base.metadata.tables


def test_policy_and_governance_audit_models_have_separate_outcome_shapes() -> None:
    policy_constraints = {
        constraint.name
        for constraint in AutomatedPolicyAuditRecordModel.__table__.constraints
    }
    governance_constraints = {
        constraint.name
        for constraint in AutomatedGovernanceAuditRecordModel.__table__.constraints
    }

    assert "ck_automated_policy_audit_records_outcome" in policy_constraints
    assert "ck_automated_governance_audit_records_outcome" in governance_constraints
    assert "rule_name" not in AutomatedPolicyAuditRecordModel.__table__.columns
    assert "policy_name" not in AutomatedGovernanceAuditRecordModel.__table__.columns


def test_automated_decision_audit_models_index_queryable_states() -> None:
    policy_indexes = {
        index.name for index in AutomatedPolicyAuditRecordModel.__table__.indexes
    }
    governance_indexes = {
        index.name for index in AutomatedGovernanceAuditRecordModel.__table__.indexes
    }

    assert "ix_automated_policy_audit_records_outcome" in policy_indexes
    assert "ix_automated_governance_audit_records_outcome" in governance_indexes
    assert "idx_automated_policy_audit_subject_outcome" in policy_indexes
    assert "idx_automated_governance_audit_subject_outcome" in governance_indexes


def test_governance_review_task_model_captures_scoped_review_work_queue() -> None:
    constraints = {
        constraint.name
        for constraint in GovernanceReviewTaskModel.__table__.constraints
    }
    indexes = {index.name for index in GovernanceReviewTaskModel.__table__.indexes}

    assert "ck_governance_review_tasks_status" in constraints
    assert "ck_governance_review_tasks_risk_tier" in constraints
    assert "uq_governance_review_tasks_scoped_evidence_sink_action" in constraints
    assert (
        "automated_governance_audit_record_id"
        in GovernanceReviewTaskModel.__table__.columns
    )
    assert "evidence_packet_version" in GovernanceReviewTaskModel.__table__.columns
    assert "intended_sink" in GovernanceReviewTaskModel.__table__.columns
    assert "ix_governance_review_tasks_status" in indexes
    assert "idx_governance_review_tasks_subject_status" in indexes
    assert "idx_governance_review_tasks_evidence_status" in indexes


def test_review_decision_model_captures_attributable_outcome_audit() -> None:
    constraints = {
        constraint.name
        for constraint in GovernanceReviewDecisionModel.__table__.constraints
    }
    indexes = {index.name for index in GovernanceReviewDecisionModel.__table__.indexes}

    assert "ck_governance_review_decisions_outcome" in constraints
    assert "ck_governance_review_decisions_resulting_status" in constraints
    assert "ck_governance_review_decisions_reviewer_actor_type" in constraints
    assert "reviewer_id" in GovernanceReviewDecisionModel.__table__.columns
    assert "rationale" in GovernanceReviewDecisionModel.__table__.columns
    assert "resulting_task_status" in GovernanceReviewDecisionModel.__table__.columns
    assert "requested_remediation" in GovernanceReviewDecisionModel.__table__.columns
    assert "evidence_packet_version" in GovernanceReviewDecisionModel.__table__.columns
    assert "ix_governance_review_decisions_resulting_task_status" in indexes
    assert "idx_governance_review_decisions_task_outcome" in indexes
    assert "idx_governance_review_decisions_evidence_outcome" in indexes


def test_residual_risk_acceptance_model_is_scoped_to_evidence_version() -> None:
    constraints = {
        constraint.name
        for constraint in GovernanceResidualRiskAcceptanceModel.__table__.constraints
    }
    indexes = {
        index.name for index in GovernanceResidualRiskAcceptanceModel.__table__.indexes
    }

    assert "ck_governance_residual_risk_acceptances_risk_tier" in constraints
    assert "uq_governance_residual_acceptances_scoped_evidence" in constraints
    assert "reviewer_id" in GovernanceResidualRiskAcceptanceModel.__table__.columns
    assert "rationale" in GovernanceResidualRiskAcceptanceModel.__table__.columns
    assert "residual_risk_scope" in (
        GovernanceResidualRiskAcceptanceModel.__table__.columns
    )
    assert "evidence_packet_version" in (
        GovernanceResidualRiskAcceptanceModel.__table__.columns
    )
    assert "idx_governance_residual_acceptances_task_evidence" in indexes
