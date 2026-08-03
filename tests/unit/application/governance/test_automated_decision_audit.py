from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.governance import (
    AutomatedDecisionAuditContext,
    AutomatedDecisionAuditService,
    GovernanceResidualRiskAcceptanceRequest,
    GovernanceReviewApprovalState,
    GovernanceReviewResolutionRequest,
    GovernedOutputReleaseRequest,
)
from core.runtime.governance import GovernanceEvaluationResult, GovernanceResult
from core.runtime.policies import PolicyEvaluationResult, PolicyResult
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedDecisionAuditRepository,
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
from domain.authority import RiskAuthorityContract, classify_risk_authority
from tests.helpers.risk_authority_examples import (
    rag_answer_authority_input,
    recommendation_explanation_authority_input,
    runtime_evidence_authority_input,
)


@pytest.mark.asyncio
async def test_records_policy_decision_as_separate_authoritative_audit_record() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    timestamp = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)

    result = await service.record_policy_decision(
        context=_context(timestamp=timestamp),
        result=PolicyResult.deny(
            policy_name="capital_preservation_policy",
            message="capital limit breached",
            reason="capital_limit_breached",
            metadata={"limit_id": "gross-exposure"},
        ),
    )

    assert result.success is True
    assert result.audit_record_id == repository.policy_records[0].audit_record_id
    assert len(repository.policy_records) == 1
    assert repository.governance_records == []
    record = repository.policy_records[0]
    assert record.subject == AutomatedDecisionSubject("recommendation", "rec-1")
    assert record.outcome is AutomatedPolicyAuditOutcome.DENY
    assert record.policy_name == "capital_preservation_policy"
    assert record.reason == "capital_limit_breached"
    assert record.message == "capital limit breached"
    assert record.risk_tier.value == record.authority_metadata["risk_tier"]
    assert record.evidence == AutomatedDecisionEvidenceReference("packet-1", 1)
    assert record.timestamp == timestamp


@pytest.mark.asyncio
async def test_records_governance_require_approval_as_queryable_audit_record() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)

    result = await service.record_governance_decision(
        context=_context(),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="vigilant output requires approval",
            reason="vigilant_authority_requires_approval",
            metadata={"risk_authority": {"risk_tier": "vigilant"}},
        ),
    )

    assert result.success is True
    assert len(repository.governance_records) == 1
    assert repository.policy_records == []
    record = repository.governance_records[0]
    assert record.outcome is AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL
    assert record.rule_name == "authority_metadata_governance"
    assert record.reason == "vigilant_authority_requires_approval"
    assert record.metadata["approval_required"] is True
    assert record.metadata["blocking"] is True
    assert record.evidence_packet_id == "packet-1"
    assert record.evidence_packet_version == 1

    queried = await repository.list_governance_audit_records(
        outcome="require_approval",
        evidence_packet_id="packet-1",
    )
    assert queried == (record,)


@pytest.mark.asyncio
async def test_enhanced_require_approval_creates_review_task_for_packet_version() -> (
    None
):
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    enhanced_authority = classify_risk_authority(
        rag_answer_authority_input(
            externally_visible=False,
            evidence_sufficient=False,
        ),
    )

    result = await service.record_governance_decision(
        context=_context(authority=enhanced_authority),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="enhanced output requires evidence review",
            reason="enhanced_authority_evidence_required",
            metadata={"authority_subject_family": "rag_answer"},
        ),
    )

    assert result.success is True
    assert result.review_task_id == repository.review_tasks[0].review_task_id
    record = repository.governance_records[0]
    task = repository.review_tasks[0]
    assert task.automated_governance_audit_record_id == record.audit_record_id
    assert task.risk_tier.value == "enhanced"
    assert task.review_scope == "rag_answer"
    assert task.intended_sink == "rag_answer"
    assert task.requested_action == "enhanced_authority_evidence_required"
    assert task.status is GovernanceReviewTaskStatus.PENDING
    assert task.evidence_packet_id == "packet-1"
    assert task.evidence_packet_version == 1
    assert task.evidence_references["evidence_packet"] == {
        "packet_id": "packet-1",
        "packet_version": 1,
    }


@pytest.mark.asyncio
async def test_enhanced_approval_state_is_visible_after_review_resolution() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_enhanced_review_task(service)
    task = repository.review_tasks[0]

    result = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Evidence is sufficient for the scoped RAG answer.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
        )
    )

    assert result.approval_state is GovernanceReviewApprovalState.REVIEW_APPROVED
    assert result.review_approved is True
    visible_state = await service.approval_state_for_review_task(task.review_task_id)
    assert visible_state is GovernanceReviewApprovalState.REVIEW_APPROVED


@pytest.mark.asyncio
async def test_vigilant_require_approval_creates_review_task_for_human_review() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)

    result = await service.record_governance_decision(
        context=_context(),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="vigilant output requires approval",
            reason="vigilant_authority_requires_approval",
            metadata={"authority_subject_family": "recommendation"},
        ),
    )

    assert result.success is True
    task = repository.review_tasks[0]
    assert task.risk_tier.value == "vigilant"
    assert task.review_scope == "recommendation"
    assert task.intended_sink == "recommendation"
    assert task.requested_action == "vigilant_authority_requires_approval"
    assert task.status is GovernanceReviewTaskStatus.PENDING


@pytest.mark.asyncio
async def test_baseline_allow_warn_do_not_create_review_tasks() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    baseline_authority = classify_risk_authority(runtime_evidence_authority_input())

    await service.record_governance_evaluation(
        context=_context(authority=baseline_authority),
        evaluation=GovernanceEvaluationResult(
            subject_type="runtime_evidence",
            results=(
                GovernanceResult.allow(
                    rule_name="authority_metadata_governance",
                    message="baseline allowed",
                ),
                GovernanceResult.warn(
                    rule_name="baseline_warning_rule",
                    message="baseline warning",
                    reason="baseline_warning",
                ),
            ),
        ),
    )

    assert [record.outcome for record in repository.governance_records] == [
        AutomatedGovernanceAuditOutcome.ALLOW,
        AutomatedGovernanceAuditOutcome.WARN,
    ]
    assert repository.review_tasks == []


@pytest.mark.asyncio
async def test_deny_and_skip_do_not_create_pending_human_review_tasks() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)

    await service.record_governance_evaluation(
        context=_context(),
        evaluation=GovernanceEvaluationResult(
            subject_type="recommendation",
            results=(
                GovernanceResult.deny(
                    rule_name="authority_metadata_governance",
                    message="outside authority denied",
                    reason="prohibited_authority",
                ),
                GovernanceResult.skip(
                    rule_name="manual_review_rule",
                    message="review not applicable",
                    reason="not_applicable",
                ),
            ),
        ),
    )

    assert [record.outcome for record in repository.governance_records] == [
        AutomatedGovernanceAuditOutcome.DENY,
        AutomatedGovernanceAuditOutcome.SKIP,
    ]
    assert all(
        record.metadata["approval_required"] is False
        for record in repository.governance_records
    )
    assert repository.review_tasks == []


@pytest.mark.asyncio
async def test_duplicate_scoped_evidence_version_reuses_open_review_task() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    governance_result = GovernanceResult.require_approval(
        rule_name="authority_metadata_governance",
        message="vigilant output requires approval",
        reason="vigilant_authority_requires_approval",
        metadata={"authority_subject_family": "recommendation"},
    )

    first = await service.record_governance_decision(
        context=_context(),
        result=governance_result,
    )
    second = await service.record_governance_decision(
        context=_context(),
        result=governance_result,
    )

    assert first.success is True
    assert second.success is True
    assert first.review_task_id == second.review_task_id
    assert len(repository.governance_records) == 2
    assert len(repository.review_tasks) == 1
    assert repository.review_tasks[0].automated_governance_audit_record_id == (
        repository.governance_records[1].audit_record_id
    )


@pytest.mark.asyncio
async def test_human_reviewer_approves_task_with_immutable_audit_entry() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]
    decided_at = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)

    result = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Evidence packet supports scoped publication.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            decided_at=decided_at,
        )
    )

    assert result.approval_state is GovernanceReviewApprovalState.REVIEW_APPROVED
    assert result.review_approved is True
    assert repository.review_tasks[0].status is GovernanceReviewTaskStatus.APPROVED
    assert len(repository.review_decisions) == 1
    decision = repository.review_decisions[0]
    assert decision.outcome is GovernanceReviewDecisionOutcome.APPROVED
    assert decision.reviewer == _reviewer()
    assert decision.rationale == "Evidence packet supports scoped publication."
    assert decision.review_scope == task.review_scope
    assert decision.evidence == task.evidence
    assert decision.decided_at == decided_at


@pytest.mark.asyncio
async def test_human_reviewer_denies_task_with_visible_denied_state() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    result = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.DENIED,
            reviewer=_reviewer(),
            rationale="Evidence packet omits material uncertainty.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
        )
    )

    assert result.approval_state is GovernanceReviewApprovalState.REVIEW_DENIED
    assert result.review_approved is False
    assert repository.review_tasks[0].status is GovernanceReviewTaskStatus.DENIED
    assert repository.review_decisions[0].outcome is (
        GovernanceReviewDecisionOutcome.DENIED
    )
    visible_state = await service.approval_state_for_review_task(task.review_task_id)
    assert visible_state is GovernanceReviewApprovalState.REVIEW_DENIED


@pytest.mark.asyncio
async def test_human_reviewer_contests_task_with_remediation_audit_entry() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]
    contested_at = datetime(2026, 8, 2, 13, 10, tzinfo=UTC)

    result = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.CONTESTED,
            reviewer=_reviewer(),
            rationale="Claim conflicts with cited downside evidence.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            requested_remediation=(
                "Reconcile the downside-risk claim with packet evidence."
            ),
            decided_at=contested_at,
        )
    )

    assert result.approval_state is GovernanceReviewApprovalState.REVIEW_CONTESTED
    assert result.review_approved is False
    assert repository.review_tasks[0].status is GovernanceReviewTaskStatus.CONTESTED
    decision = repository.review_decisions[0]
    assert decision.outcome is GovernanceReviewDecisionOutcome.CONTESTED
    assert decision.resulting_task_status is GovernanceReviewTaskStatus.CONTESTED
    assert decision.requested_remediation == (
        "Reconcile the downside-risk claim with packet evidence."
    )
    assert decision.decided_at == contested_at
    queried = await repository.list_governance_review_decisions(
        review_task_id=task.review_task_id,
        outcome="contested",
        evidence_packet_id="packet-1",
    )
    assert queried == (decision,)


@pytest.mark.asyncio
async def test_request_changes_keeps_output_unapproved_until_new_review_path() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    result = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
            reviewer=_reviewer(),
            rationale="Evidence is stale for the requested publication scope.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            requested_remediation="Regenerate the evidence packet with fresh quotes.",
        )
    )

    assert result.approval_state is GovernanceReviewApprovalState.CHANGES_REQUESTED
    assert result.review_approved is False
    assert repository.review_tasks[0].status is (
        GovernanceReviewTaskStatus.CHANGES_REQUESTED
    )
    decision = repository.review_decisions[0]
    assert decision.outcome is GovernanceReviewDecisionOutcome.CHANGES_REQUESTED
    assert decision.requested_remediation == (
        "Regenerate the evidence packet with fresh quotes."
    )

    with pytest.raises(ValueError, match="cannot accept that outcome"):
        await service.resolve_governance_review_task(
            GovernanceReviewResolutionRequest(
                review_task_id=task.review_task_id,
                outcome=GovernanceReviewDecisionOutcome.APPROVED,
                reviewer=_reviewer(),
                rationale="Attempt to approve the stale packet anyway.",
                reviewed_evidence=task.evidence,
                review_scope=task.review_scope,
            )
        )

    assert len(repository.review_decisions) == 1
    assert repository.review_tasks[0].status is (
        GovernanceReviewTaskStatus.CHANGES_REQUESTED
    )

    updated_evidence = AutomatedDecisionEvidenceReference("packet-1", 2)
    fresh_path = await service.record_governance_decision(
        context=_context(evidence=updated_evidence),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="updated evidence requires approval",
            reason="vigilant_authority_requires_approval",
            metadata={"authority_subject_family": "recommendation"},
        ),
    )
    fresh_task = repository.review_tasks[1]
    assert fresh_path.review_task_id == fresh_task.review_task_id
    assert fresh_task.evidence == updated_evidence

    approved_fresh_path = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=fresh_task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Fresh evidence resolves the requested change.",
            reviewed_evidence=fresh_task.evidence,
            review_scope=fresh_task.review_scope,
        )
    )

    assert approved_fresh_path.approval_state is (
        GovernanceReviewApprovalState.REVIEW_APPROVED
    )
    assert repository.review_tasks[0].status is (
        GovernanceReviewTaskStatus.CHANGES_REQUESTED
    )
    assert repository.review_tasks[1].status is GovernanceReviewTaskStatus.APPROVED


@pytest.mark.asyncio
async def test_override_preserves_original_automated_and_contested_audit_records() -> (
    None
):
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]
    original_audit = repository.governance_records[0]

    contested = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.CONTESTED,
            reviewer=_reviewer(),
            rationale="The automated decision underweights missing evidence.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            requested_remediation="Escalate to governance owner for scoped override.",
        )
    )
    overridden = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.OVERRIDDEN,
            reviewer=_organization_reviewer(),
            rationale="Organization accepts the scoped exception for this packet.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            metadata={"override_ticket": "GOV-123"},
        )
    )

    assert contested.approval_state is GovernanceReviewApprovalState.REVIEW_CONTESTED
    assert overridden.approval_state is GovernanceReviewApprovalState.REVIEW_OVERRIDDEN
    assert overridden.review_approved is False
    assert repository.review_tasks[0].status is GovernanceReviewTaskStatus.OVERRIDDEN
    assert repository.governance_records[0] == original_audit
    assert [decision.outcome for decision in repository.review_decisions] == [
        GovernanceReviewDecisionOutcome.CONTESTED,
        GovernanceReviewDecisionOutcome.OVERRIDDEN,
    ]
    assert repository.review_decisions[1].reviewer == _organization_reviewer()
    assert repository.review_decisions[1].resulting_task_status is (
        GovernanceReviewTaskStatus.OVERRIDDEN
    )


@pytest.mark.asyncio
async def test_vigilant_approval_requires_explicit_residual_risk_acceptance() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    blocked = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Packet is sufficient but residual market risk remains.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            residual_risk_remaining=True,
        )
    )

    assert blocked.approval_state is (
        GovernanceReviewApprovalState.RESIDUAL_RISK_ACCEPTANCE_REQUIRED
    )
    assert blocked.review_approved is False
    assert repository.review_tasks[0].status is GovernanceReviewTaskStatus.PENDING
    assert repository.review_decisions == []
    assert repository.residual_risk_acceptances == []

    accepted_at = datetime(2026, 8, 2, 13, 5, tzinfo=UTC)
    approved = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Human accepts scoped residual market risk.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            residual_risk_remaining=True,
            residual_risk_acceptance=GovernanceResidualRiskAcceptanceRequest(
                reviewer=_reviewer(),
                rationale="Accept residual downside risk for this recommendation.",
                residual_risk_scope="recommendation publication only",
                accepted_at=accepted_at,
            ),
        )
    )

    assert approved.approval_state is GovernanceReviewApprovalState.REVIEW_APPROVED
    assert len(repository.residual_risk_acceptances) == 1
    acceptance = repository.residual_risk_acceptances[0]
    assert acceptance.review_task_id == task.review_task_id
    assert acceptance.evidence == task.evidence
    assert acceptance.review_scope == task.review_scope
    assert acceptance.residual_risk_scope == "recommendation publication only"
    assert acceptance.accepted_at == accepted_at
    assert repository.review_decisions[0].residual_risk_acceptance_id == (
        acceptance.acceptance_id
    )


@pytest.mark.asyncio
async def test_residual_risk_acceptance_is_scoped_to_reviewed_evidence_version() -> (
    None
):
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    with pytest.raises(ValueError, match="evidence version"):
        await service.resolve_governance_review_task(
            GovernanceReviewResolutionRequest(
                review_task_id=task.review_task_id,
                outcome=GovernanceReviewDecisionOutcome.APPROVED,
                reviewer=_reviewer(),
                rationale="Attempt to approve later packet version.",
                reviewed_evidence=AutomatedDecisionEvidenceReference(
                    "packet-1",
                    2,
                ),
                review_scope=task.review_scope,
                residual_risk_remaining=True,
                residual_risk_acceptance=GovernanceResidualRiskAcceptanceRequest(
                    reviewer=_reviewer(),
                    rationale="Attempted broad acceptance.",
                    residual_risk_scope="all future recommendation versions",
                ),
            )
        )

    assert repository.review_decisions == []
    assert repository.residual_risk_acceptances == []


@pytest.mark.asyncio
async def test_governed_release_blocks_matching_review_context() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    pending = await service.evaluate_governed_output_release(
        _release_request(task=task),
    )

    assert pending.allowed is False
    assert pending.approval_state is GovernanceReviewApprovalState.PENDING_REVIEW
    assert pending.review_task_id == task.review_task_id

    approved = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Evidence packet supports scoped durable promotion.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
        )
    )
    assert approved.review_approved is True

    wrong_evidence_version = await service.evaluate_governed_output_release(
        _release_request(
            task=task,
            evidence=AutomatedDecisionEvidenceReference(
                task.evidence.packet_id,
                task.evidence.packet_version + 1,
            ),
        ),
    )
    exact_scope = await service.evaluate_governed_output_release(
        _release_request(task=repository.review_tasks[0]),
    )

    assert wrong_evidence_version.allowed is False
    assert wrong_evidence_version.approval_state is (
        GovernanceReviewApprovalState.PENDING_REVIEW
    )
    assert exact_scope.allowed is True
    assert exact_scope.approval_state is GovernanceReviewApprovalState.REVIEW_APPROVED
    assert exact_scope.review_task_id == task.review_task_id


@pytest.mark.parametrize(
    ("outcome", "approval_state"),
    (
        (
            GovernanceReviewDecisionOutcome.DENIED,
            GovernanceReviewApprovalState.REVIEW_DENIED,
        ),
        (
            GovernanceReviewDecisionOutcome.CONTESTED,
            GovernanceReviewApprovalState.REVIEW_CONTESTED,
        ),
        (
            GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
            GovernanceReviewApprovalState.CHANGES_REQUESTED,
        ),
    ),
)
@pytest.mark.asyncio
async def test_governed_release_blocks_non_approved_review_states(
    outcome: GovernanceReviewDecisionOutcome,
    approval_state: GovernanceReviewApprovalState,
) -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=outcome,
            reviewer=_reviewer(),
            rationale="Scoped review does not permit release.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            requested_remediation=(
                "Resolve reviewer objections before publication."
                if outcome
                in {
                    GovernanceReviewDecisionOutcome.CONTESTED,
                    GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
                }
                else None
            ),
        )
    )

    release = await service.evaluate_governed_output_release(
        _release_request(task=repository.review_tasks[0]),
    )

    assert release.allowed is False
    assert release.approval_state is approval_state
    assert release.review_task_id == task.review_task_id
    assert approval_state.value in release.reason


@pytest.mark.asyncio
async def test_governed_release_blocks_cancelled_review_task() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    await repository.update_governance_review_task_status(
        review_task_id=task.review_task_id,
        status=GovernanceReviewTaskStatus.CANCELLED,
        updated_at=datetime(2026, 8, 2, 12, tzinfo=UTC),
    )

    release = await service.evaluate_governed_output_release(
        _release_request(task=repository.review_tasks[0]),
    )

    assert release.allowed is False
    assert release.approval_state is GovernanceReviewApprovalState.PENDING_REVIEW
    assert release.review_task_id == task.review_task_id


@pytest.mark.asyncio
async def test_governed_release_blocks_unresolved_residual_risk_acceptance() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Packet is sufficient for approval.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
        )
    )

    release = await service.evaluate_governed_output_release(
        _release_request(
            task=repository.review_tasks[0],
            residual_risk_acceptance_required=True,
        ),
    )

    assert release.allowed is False
    assert release.approval_state is (
        GovernanceReviewApprovalState.RESIDUAL_RISK_ACCEPTANCE_REQUIRED
    )
    assert release.review_task_id == task.review_task_id


@pytest.mark.asyncio
async def test_vigilant_release_requires_scoped_residual_risk_acceptance() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    blocked_resolution = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Packet is sufficient but residual market risk remains.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            residual_risk_remaining=True,
        )
    )
    assert blocked_resolution.approval_state is (
        GovernanceReviewApprovalState.RESIDUAL_RISK_ACCEPTANCE_REQUIRED
    )

    accepted_at = datetime(2026, 8, 2, 13, 5, tzinfo=UTC)
    approved = await service.resolve_governance_review_task(
        GovernanceReviewResolutionRequest(
            review_task_id=task.review_task_id,
            outcome=GovernanceReviewDecisionOutcome.APPROVED,
            reviewer=_reviewer(),
            rationale="Human accepts scoped residual market risk.",
            reviewed_evidence=task.evidence,
            review_scope=task.review_scope,
            residual_risk_remaining=True,
            residual_risk_acceptance=GovernanceResidualRiskAcceptanceRequest(
                reviewer=_reviewer(),
                rationale="Accept residual downside risk for this release.",
                residual_risk_scope="recommendation publication only",
                accepted_at=accepted_at,
            ),
        )
    )
    assert approved.review_approved is True

    missing_acceptance_scope = await service.evaluate_governed_output_release(
        _release_request(
            task=repository.review_tasks[0],
            review_scope="recommendation-summary",
            residual_risk_acceptance_required=True,
        ),
    )
    exact_scope = await service.evaluate_governed_output_release(
        _release_request(
            task=repository.review_tasks[0],
            residual_risk_acceptance_required=True,
        ),
    )

    assert missing_acceptance_scope.allowed is False
    assert missing_acceptance_scope.approval_state is (
        GovernanceReviewApprovalState.PENDING_REVIEW
    )
    assert exact_scope.allowed is True
    assert exact_scope.residual_risk_acceptance_id == (
        repository.residual_risk_acceptances[0].acceptance_id
    )


@pytest.mark.asyncio
async def test_model_workflow_and_evaluator_metadata_cannot_approve_review() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    await _create_vigilant_review_task(service)
    task = repository.review_tasks[0]

    for metadata, outcome in (
        ({"model_output": "approved"}, GovernanceReviewDecisionOutcome.APPROVED),
        (
            {"workflow_metadata": {"production_ready": True}},
            GovernanceReviewDecisionOutcome.APPROVED,
        ),
        ({"evaluator_score": 1.0}, GovernanceReviewDecisionOutcome.APPROVED),
        (
            {"generated_text": "residual risk accepted"},
            GovernanceReviewDecisionOutcome.APPROVED,
        ),
        (
            {"contest": "model disputes claim"},
            GovernanceReviewDecisionOutcome.CONTESTED,
        ),
        ({"override": True}, GovernanceReviewDecisionOutcome.OVERRIDDEN),
        (
            {"requested_changes_satisfied": True},
            GovernanceReviewDecisionOutcome.CHANGES_REQUESTED,
        ),
    ):
        with pytest.raises(ValueError):
            await service.resolve_governance_review_task(
                GovernanceReviewResolutionRequest(
                    review_task_id=task.review_task_id,
                    outcome=outcome,
                    reviewer=_reviewer(),
                    rationale="Attempt non-human approval path.",
                    reviewed_evidence=task.evidence,
                    review_scope=task.review_scope,
                    requested_remediation=(
                        "Human remediation must not come from metadata."
                    ),
                    metadata=metadata,
                )
            )

    assert repository.review_tasks[0].status is GovernanceReviewTaskStatus.PENDING
    assert repository.review_decisions == []


@pytest.mark.asyncio
async def test_model_metadata_cannot_self_approve_or_lower_audit_risk() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)
    contract = classify_risk_authority(
        recommendation_explanation_authority_input(
            model_provided_metadata={
                "risk_tier": "baseline",
                "approved": True,
                "governance_approved": True,
                "production_ready": True,
                "residual_risk_accepted": True,
            },
        )
    )

    await service.record_governance_decision(
        context=_context(authority=contract),
        result=GovernanceResult.deny(
            rule_name="authority_metadata_governance",
            message="outside authority metadata ignored",
            reason="model_authority_claims_ignored",
        ),
    )

    record = repository.governance_records[0]
    assert record.risk_tier.value == "vigilant"
    assert record.authority_metadata["risk_tier"] == "vigilant"
    ignored_claims = record.authority_metadata["ignored_model_authority_claims"]
    assert isinstance(ignored_claims, list)
    assert set(ignored_claims) >= {
        "governance_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier",
    }
    for forbidden_key in (
        "approved",
        "governance_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier_override",
    ):
        assert forbidden_key not in record.authority_metadata


@pytest.mark.asyncio
async def test_policy_contract_never_records_governance_only_require_approval() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)

    await service.record_policy_decision(
        context=_context(),
        result=PolicyResult.warn(
            policy_name="exposure_policy",
            message="exposure near threshold",
            reason="exposure_warning",
        ),
    )
    await service.record_governance_decision(
        context=_context(),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="approval required",
            reason="vigilant_authority_requires_approval",
        ),
    )

    assert repository.policy_records[0].outcome is AutomatedPolicyAuditOutcome.WARN
    assert repository.governance_records[0].outcome is (
        AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL
    )
    with pytest.raises(ValueError):
        AutomatedPolicyAuditOutcome("require_approval")


@pytest.mark.asyncio
async def test_records_every_policy_and_governance_evaluation_outcome() -> None:
    repository = FakeAutomatedDecisionAuditRepository()
    service = AutomatedDecisionAuditService(repository)

    policy_results = await service.record_policy_evaluation(
        context=_context(),
        evaluation=PolicyEvaluationResult(
            subject_type="recommendation",
            results=(
                PolicyResult.allow(
                    policy_name="capital_policy",
                    message="allowed",
                    metadata={"reason": "capital_ok"},
                ),
                PolicyResult.skip(
                    policy_name="market_hours_policy",
                    message="not applicable",
                    reason="not_live_mode",
                ),
            ),
        ),
    )
    governance_results = await service.record_governance_evaluation(
        context=_context(),
        evaluation=GovernanceEvaluationResult(
            subject_type="recommendation",
            results=(
                GovernanceResult.warn(
                    rule_name="authority_metadata_governance",
                    message="enhanced provenance required",
                    reason="enhanced_authority_requires_provenance",
                ),
                GovernanceResult.skip(
                    rule_name="manual_approval_governance",
                    message="not applicable",
                    reason="not_vigilant",
                ),
            ),
        ),
    )

    assert all(result.success for result in policy_results + governance_results)
    assert [record.outcome for record in repository.policy_records] == [
        AutomatedPolicyAuditOutcome.ALLOW,
        AutomatedPolicyAuditOutcome.SKIP,
    ]
    assert [record.outcome for record in repository.governance_records] == [
        AutomatedGovernanceAuditOutcome.WARN,
        AutomatedGovernanceAuditOutcome.SKIP,
    ]


def _context(
    *,
    authority: RiskAuthorityContract | None = None,
    evidence: AutomatedDecisionEvidenceReference | None = None,
    timestamp: datetime | None = None,
) -> AutomatedDecisionAuditContext:
    return AutomatedDecisionAuditContext(
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        authority=authority
        or classify_risk_authority(recommendation_explanation_authority_input()),
        evidence=evidence or AutomatedDecisionEvidenceReference("packet-1", 1),
        timestamp=timestamp,
    )


class FakeAutomatedDecisionAuditRepository(AutomatedDecisionAuditRepository):
    def __init__(self) -> None:
        self.policy_records: list[AutomatedPolicyAuditRecord] = []
        self.governance_records: list[AutomatedGovernanceAuditRecord] = []
        self.review_tasks: list[GovernanceReviewTaskRecord] = []
        self.review_decisions: list[GovernanceReviewDecisionRecord] = []
        self.residual_risk_acceptances: list[
            GovernanceResidualRiskAcceptanceRecord
        ] = []

    async def persist_policy_audit_record(
        self,
        record: AutomatedPolicyAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        self.policy_records.append(record)
        return AutomatedDecisionAuditPersistenceResult.succeeded(record.audit_record_id)

    async def persist_governance_audit_record(
        self,
        record: AutomatedGovernanceAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        self.governance_records.append(record)
        return AutomatedDecisionAuditPersistenceResult.succeeded(record.audit_record_id)

    async def persist_governance_review_task(
        self,
        task: GovernanceReviewTaskRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        existing_index = next(
            (
                index
                for index, existing_task in enumerate(self.review_tasks)
                if existing_task.review_task_id == task.review_task_id
            ),
            None,
        )
        if existing_index is None:
            self.review_tasks.append(task)
        else:
            self.review_tasks[existing_index] = task
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            task.review_task_id,
            review_task_id=task.review_task_id,
        )

    async def get_governance_review_task(
        self,
        review_task_id: str,
    ) -> GovernanceReviewTaskRecord | None:
        return next(
            (
                task
                for task in self.review_tasks
                if task.review_task_id == review_task_id
            ),
            None,
        )

    async def update_governance_review_task_status(
        self,
        *,
        review_task_id: str,
        status: GovernanceReviewTaskStatus,
        updated_at: datetime,
    ) -> AutomatedDecisionAuditPersistenceResult:
        for index, task in enumerate(self.review_tasks):
            if task.review_task_id == review_task_id:
                self.review_tasks[index] = GovernanceReviewTaskRecord(
                    review_task_id=task.review_task_id,
                    automated_governance_audit_record_id=(
                        task.automated_governance_audit_record_id
                    ),
                    subject=task.subject,
                    risk_tier=task.risk_tier,
                    authority_metadata=task.authority_metadata,
                    review_scope=task.review_scope,
                    intended_sink=task.intended_sink,
                    requested_action=task.requested_action,
                    status=status,
                    evidence=task.evidence,
                    evidence_references=task.evidence_references,
                    created_at=task.created_at,
                    updated_at=updated_at,
                )
                return AutomatedDecisionAuditPersistenceResult.succeeded(
                    review_task_id,
                    review_task_id=review_task_id,
                )
        return AutomatedDecisionAuditPersistenceResult.failed(
            "review_task_not_found",
            audit_record_id=review_task_id,
        )

    async def persist_governance_review_decision(
        self,
        decision: GovernanceReviewDecisionRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        self.review_decisions.append(decision)
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            decision.review_decision_id,
        )

    async def get_governance_review_decision(
        self,
        review_decision_id: str,
    ) -> GovernanceReviewDecisionRecord | None:
        return next(
            (
                decision
                for decision in self.review_decisions
                if decision.review_decision_id == review_decision_id
            ),
            None,
        )

    async def persist_residual_risk_acceptance(
        self,
        acceptance: GovernanceResidualRiskAcceptanceRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        self.residual_risk_acceptances.append(acceptance)
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            acceptance.acceptance_id,
        )

    async def get_residual_risk_acceptance(
        self,
        acceptance_id: str,
    ) -> GovernanceResidualRiskAcceptanceRecord | None:
        return next(
            (
                acceptance
                for acceptance in self.residual_risk_acceptances
                if acceptance.acceptance_id == acceptance_id
            ),
            None,
        )

    async def list_governance_review_tasks(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        status: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> Sequence[GovernanceReviewTaskRecord]:
        return tuple(
            task
            for task in self.review_tasks
            if (subject_type is None or task.subject_type == subject_type)
            and (subject_id is None or task.subject_id == subject_id)
            and (risk_tier is None or task.risk_tier.value == risk_tier)
            and (status is None or task.status.value == status)
            and (
                evidence_packet_id is None
                or task.evidence_packet_id == evidence_packet_id
            )
        )

    async def list_governance_review_decisions(
        self,
        *,
        review_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        outcome: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> Sequence[GovernanceReviewDecisionRecord]:
        return tuple(
            decision
            for decision in self.review_decisions
            if (review_task_id is None or decision.review_task_id == review_task_id)
            and (subject_type is None or decision.subject_type == subject_type)
            and (subject_id is None or decision.subject_id == subject_id)
            and (outcome is None or decision.outcome.value == outcome)
            and (
                evidence_packet_id is None
                or decision.evidence_packet_id == evidence_packet_id
            )
        )

    async def list_residual_risk_acceptances(
        self,
        *,
        review_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> Sequence[GovernanceResidualRiskAcceptanceRecord]:
        return tuple(
            acceptance
            for acceptance in self.residual_risk_acceptances
            if (review_task_id is None or acceptance.review_task_id == review_task_id)
            and (subject_type is None or acceptance.subject_type == subject_type)
            and (subject_id is None or acceptance.subject_id == subject_id)
            and (
                evidence_packet_id is None
                or acceptance.evidence_packet_id == evidence_packet_id
            )
        )

    async def get_policy_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedPolicyAuditRecord | None:
        return next(
            (
                record
                for record in self.policy_records
                if record.audit_record_id == audit_record_id
            ),
            None,
        )

    async def get_governance_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedGovernanceAuditRecord | None:
        return next(
            (
                record
                for record in self.governance_records
                if record.audit_record_id == audit_record_id
            ),
            None,
        )

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
    ) -> Sequence[AutomatedPolicyAuditRecord]:
        return tuple(
            record
            for record in self.policy_records
            if _matches_common_filters(
                record,
                subject_type=subject_type,
                subject_id=subject_id,
                risk_tier=risk_tier,
                outcome=outcome,
                evidence_packet_id=evidence_packet_id,
                start=start,
                end=end,
            )
            and (policy_name is None or record.policy_name == policy_name)
        )

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
    ) -> Sequence[AutomatedGovernanceAuditRecord]:
        return tuple(
            record
            for record in self.governance_records
            if _matches_common_filters(
                record,
                subject_type=subject_type,
                subject_id=subject_id,
                risk_tier=risk_tier,
                outcome=outcome,
                evidence_packet_id=evidence_packet_id,
                start=start,
                end=end,
            )
            and (rule_name is None or record.rule_name == rule_name)
        )


def _matches_common_filters(
    record: AutomatedPolicyAuditRecord | AutomatedGovernanceAuditRecord,
    *,
    subject_type: str | None,
    subject_id: str | None,
    risk_tier: str | None,
    outcome: str | None,
    evidence_packet_id: str | None,
    start: datetime | None,
    end: datetime | None,
) -> bool:
    return (
        (subject_type is None or record.subject_type == subject_type)
        and (subject_id is None or record.subject_id == subject_id)
        and (risk_tier is None or record.risk_tier.value == risk_tier)
        and (outcome is None or record.outcome.value == outcome)
        and (
            evidence_packet_id is None
            or record.evidence_packet_id == evidence_packet_id
        )
        and (start is None or record.timestamp >= start)
        and (end is None or record.timestamp <= end)
    )


async def _create_enhanced_review_task(
    service: AutomatedDecisionAuditService,
) -> None:
    enhanced_authority = classify_risk_authority(
        rag_answer_authority_input(
            externally_visible=False,
            evidence_sufficient=False,
        ),
    )
    await service.record_governance_decision(
        context=_context(authority=enhanced_authority),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="enhanced output requires evidence review",
            reason="enhanced_authority_evidence_required",
            metadata={"authority_subject_family": "rag_answer"},
        ),
    )


async def _create_vigilant_review_task(
    service: AutomatedDecisionAuditService,
) -> None:
    await service.record_governance_decision(
        context=_context(),
        result=GovernanceResult.require_approval(
            rule_name="authority_metadata_governance",
            message="vigilant output requires approval",
            reason="vigilant_authority_requires_approval",
            metadata={"authority_subject_family": "recommendation"},
        ),
    )


def _release_request(
    *,
    task: GovernanceReviewTaskRecord,
    evidence: AutomatedDecisionEvidenceReference | None = None,
    review_scope: str | None = None,
    requested_action: str | None = None,
    residual_risk_acceptance_required: bool = False,
) -> GovernedOutputReleaseRequest:
    return GovernedOutputReleaseRequest(
        authority=_context().authority,
        subject=task.subject,
        evidence=evidence or task.evidence,
        review_scope=review_scope or task.review_scope,
        requested_action=requested_action or task.requested_action,
        boundary_name="recommendation.durable_promotion",
        residual_risk_acceptance_required=residual_risk_acceptance_required,
    )


def _reviewer() -> GovernanceReviewerIdentity:
    return GovernanceReviewerIdentity(
        reviewer_id="reviewer-1",
        actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
        display_name="Jane Reviewer",
    )


def _organization_reviewer() -> GovernanceReviewerIdentity:
    return GovernanceReviewerIdentity(
        reviewer_id="governance-board",
        actor_type=GovernanceReviewerActorType.ORGANIZATION_REVIEWER,
        display_name="Governance Board",
    )
