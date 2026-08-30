from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from application.evaluations import (
    OutputGovernanceGateEvidence,
    RiskAuthorityGateEvidence,
    RiskAuthorityGateFailureMode,
)
from application.governance import (
    GovernanceReviewApprovalState,
    GovernedOutputReleaseDecision,
    GovernedOutputReleaseRequest,
)
from application.presentation import (
    PresentationSinkDecisionService,
    PresentationSinkDisposition,
)
from application.reports.authority import morning_report_authority
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    GovernanceReviewDecisionOutcome,
)
from core.telemetry.observability import ObservabilityManager
from domain.authority import RiskAuthorityContract, RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
)
from tests.helpers.risk_authority_examples import (
    authority_input_for_tier,
    outside_authority_tool_response_input,
    runtime_evidence_authority_input,
)


def _packet(
    tier: RiskTier,
    *,
    packet_id: str = "packet-1",
    authority: RiskAuthorityContract | None = None,
) -> DecisionEvidencePacket:
    evidence_id = "evidence-1"
    return DecisionEvidencePacket(
        packet_id=packet_id,
        output_id="output-1",
        authority=authority
        or classify_risk_authority(authority_input_for_tier(tier)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="Supported material claim.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=(evidence_id,),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id=evidence_id,
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=("workflow-node",),
                summary="Runtime node output supporting the material claim.",
                support_snapshot=SupportingEvidenceSnapshot(
                    snapshot_id="evidence-1:support-snapshot",
                    summary="Runtime node output supporting the material claim.",
                    redacted_content="Supported material claim evidence.",
                    source_label="workflow_node_output:workflow-node",
                ),
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="workflow-node",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="run-1:node:analysis",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-07-25T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
        workflow_name="morning_report",
        workflow_definition_fingerprint="test-definition-fingerprint",
        execution_id="exec-1",
    )


def _governance_evidence(
    packet: DecisionEvidencePacket,
) -> OutputGovernanceGateEvidence:
    request = GovernedOutputReleaseRequest(
        authority=packet.authority,
        subject=AutomatedDecisionSubject(
            subject_type="recommendation",
            subject_id=packet.output_id,
        ),
        evidence=AutomatedDecisionEvidenceReference(
            packet_id=packet.packet_id,
            packet_version=packet.schema_version,
        ),
        review_scope="publication",
        requested_action="publish",
        boundary_name="recommendation.publication",
    )
    return OutputGovernanceGateEvidence.from_release_decision(
        request=request,
        decision=GovernedOutputReleaseDecision(
            allowed=True,
            reason="canonical governance permits release",
            approval_state=GovernanceReviewApprovalState.REVIEW_APPROVED,
            review_task_id="governance-review-task-1",
            review_decision_outcome=GovernanceReviewDecisionOutcome.APPROVED,
        ),
    )


def _enhanced_report_evidence(
    authority: RiskAuthorityContract,
) -> RiskAuthorityGateEvidence:
    packet = _packet(RiskTier.ENHANCED, authority=authority)
    return RiskAuthorityGateEvidence(
        provenance_record_ids=("report-source-1",),
        decision_evidence_packets=(packet,),
    )


@pytest.mark.asyncio
async def test_baseline_internal_missing_metadata_remains_eligible() -> None:
    expected = classify_risk_authority(runtime_evidence_authority_input())

    decision = await PresentationSinkDecisionService().evaluate(
        None,
        expected_authority_metadata=expected,
    )

    assert decision.disposition is PresentationSinkDisposition.ELIGIBLE
    assert decision.may_present
    assert decision.risk_tier is RiskTier.BASELINE
    assert decision.authority_metadata is None
    assert decision.gate_failure_mode is RiskAuthorityGateFailureMode.NONE
    assert decision.decision_evidence_packet_ids == ()


@pytest.mark.asyncio
async def test_enhanced_missing_packet_is_withheld_by_canonical_gate() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    decision = await PresentationSinkDecisionService().evaluate(
        authority,
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("rag-doc-1",),
        ),
    )

    assert decision.disposition is PresentationSinkDisposition.WITHHELD
    assert not decision.may_present
    assert decision.gate_failure_mode is (
        RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )


@pytest.mark.asyncio
async def test_enhanced_complete_readiness_is_eligible() -> None:
    packet = _packet(RiskTier.ENHANCED)

    decision = await PresentationSinkDecisionService().evaluate(
        packet.authority,
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("rag-doc-1",),
            decision_evidence_packets=(packet,),
        ),
        limitations=("Answer remains non-authoritative decision support.",),
    )

    assert decision.disposition is PresentationSinkDisposition.ELIGIBLE
    assert decision.provenance_record_ids == ("rag-doc-1",)
    assert decision.decision_evidence_packet_ids == (packet.packet_id,)
    assert decision.limitations == (
        "Answer remains non-authoritative decision support.",
    )


@pytest.mark.asyncio
async def test_capital_relevant_enhanced_missing_governed_release_is_withheld() -> None:
    authority = morning_report_authority()

    decision = await PresentationSinkDecisionService().evaluate(
        authority,
        evidence=_enhanced_report_evidence(authority),
    )

    assert decision.readiness_passed
    assert decision.gate_failure_mode is RiskAuthorityGateFailureMode.NONE
    assert decision.disposition is PresentationSinkDisposition.WITHHELD
    assert not decision.may_present
    assert decision.governed_release_allowed is None
    assert "Canonical governed output release decision is required." in decision.reasons


@pytest.mark.asyncio
async def test_capital_relevant_enhanced_allowed_release_is_eligible() -> None:
    authority = morning_report_authority()
    release_decision = GovernedOutputReleaseDecision(
        allowed=True,
        reason="canonical governance permits release",
        approval_state=GovernanceReviewApprovalState.REVIEW_APPROVED,
        review_task_id="governance-review-task-1",
        review_decision_outcome=GovernanceReviewDecisionOutcome.APPROVED,
    )

    decision = await PresentationSinkDecisionService().evaluate(
        authority,
        evidence=_enhanced_report_evidence(authority),
        governed_release_decisions=(release_decision,),
    )

    assert decision.disposition is PresentationSinkDisposition.ELIGIBLE
    assert decision.governed_release_allowed
    assert decision.governance_approval_states == (
        GovernanceReviewApprovalState.REVIEW_APPROVED,
    )


@pytest.mark.parametrize(
    "approval_state",
    [
        GovernanceReviewApprovalState.PENDING_REVIEW,
        GovernanceReviewApprovalState.REVIEW_DENIED,
        GovernanceReviewApprovalState.REVIEW_CONTESTED,
        GovernanceReviewApprovalState.CHANGES_REQUESTED,
    ],
)
@pytest.mark.asyncio
async def test_capital_relevant_enhanced_non_releasable_governance_is_withheld(
    approval_state: GovernanceReviewApprovalState,
) -> None:
    authority = morning_report_authority()
    release_decision = GovernedOutputReleaseDecision(
        allowed=False,
        reason=f"canonical governance blocks release: {approval_state.value}",
        approval_state=approval_state,
        review_task_id="governance-review-task-1",
    )

    decision = await PresentationSinkDecisionService().evaluate(
        authority,
        evidence=_enhanced_report_evidence(authority),
        governed_release_decisions=(release_decision,),
    )

    assert decision.disposition is PresentationSinkDisposition.WITHHELD
    assert not decision.may_present
    assert decision.governed_release_allowed is False
    assert release_decision.reason in decision.reasons


@pytest.mark.asyncio
async def test_vigilant_missing_governance_accountability_is_withheld() -> None:
    packet = _packet(RiskTier.VIGILANT)

    decision = await PresentationSinkDecisionService().evaluate(
        packet.authority,
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("recommendation-record-1",),
            decision_evidence_packets=(packet,),
        ),
    )

    assert decision.disposition is PresentationSinkDisposition.WITHHELD
    assert decision.gate_failure_mode is (
        RiskAuthorityGateFailureMode.OUTPUT_GOVERNANCE_EVIDENCE_REQUIRED
    )


@pytest.mark.asyncio
async def test_vigilant_complete_governance_accountability_is_eligible() -> None:
    packet = _packet(RiskTier.VIGILANT)
    governance_evidence = _governance_evidence(packet)

    decision = await PresentationSinkDecisionService().evaluate(
        packet.authority,
        evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("recommendation-record-1",),
            decision_evidence_packets=(packet,),
            output_governance_evidence=(governance_evidence,),
        ),
    )

    assert decision.disposition is PresentationSinkDisposition.ELIGIBLE
    assert decision.governed_release_allowed
    assert decision.governance_approval_states == (
        GovernanceReviewApprovalState.REVIEW_APPROVED,
    )


@pytest.mark.asyncio
async def test_prohibited_boundary_is_blocked() -> None:
    authority = classify_risk_authority(outside_authority_tool_response_input())

    decision = await PresentationSinkDecisionService().evaluate(authority)

    assert decision.disposition is PresentationSinkDisposition.BLOCKED
    assert not decision.may_present
    assert decision.gate_failure_mode is (
        RiskAuthorityGateFailureMode.PROHIBITED_BOUNDARY
    )


@pytest.mark.asyncio
async def test_invalid_authority_metadata_is_blocked() -> None:
    malformed = await PresentationSinkDecisionService().evaluate(
        {"risk_tier": "enhanced"},
    )
    inconsistent_metadata = classify_risk_authority(
        authority_input_for_tier(RiskTier.VIGILANT)
    ).to_metadata()
    inconsistent_metadata["risk_tier"] = RiskTier.BASELINE.value
    inconsistent_metadata["gate_profile"] = "baseline_internal"
    inconsistent = await PresentationSinkDecisionService().evaluate(
        inconsistent_metadata,
    )

    assert malformed.disposition is PresentationSinkDisposition.BLOCKED
    assert malformed.gate_failure_mode is (
        RiskAuthorityGateFailureMode.METADATA_MALFORMED
    )
    assert inconsistent.disposition is PresentationSinkDisposition.BLOCKED
    assert inconsistent.gate_failure_mode is (
        RiskAuthorityGateFailureMode.METADATA_INCONSISTENT
    )


@pytest.mark.asyncio
async def test_boundary_constraints_can_only_reduce_canonical_eligibility() -> None:
    authority = classify_risk_authority(runtime_evidence_authority_input())
    service = PresentationSinkDecisionService()

    degraded = await service.evaluate(
        authority,
        degradation_reasons=("Optional source is temporarily unavailable.",),
    )
    withheld = await service.evaluate(
        authority,
        withholding_reasons=("Required citation is missing.",),
    )
    blocked = await service.evaluate(
        authority,
        blocking_reasons=("Unsafe authority claim detected.",),
    )

    assert degraded.disposition is PresentationSinkDisposition.DEGRADED
    assert degraded.may_present
    assert withheld.disposition is PresentationSinkDisposition.WITHHELD
    assert not withheld.may_present
    assert blocked.disposition is PresentationSinkDisposition.BLOCKED
    assert not blocked.may_present


@pytest.mark.asyncio
async def test_degradation_cannot_soften_a_failed_canonical_gate() -> None:
    authority = classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED))

    decision = await PresentationSinkDecisionService().evaluate(
        authority,
        degradation_reasons=("Optional source is unavailable.",),
    )

    assert decision.disposition is PresentationSinkDisposition.WITHHELD
    assert decision.gate_failure_mode is (
        RiskAuthorityGateFailureMode.DECISION_EVIDENCE_REQUIRED
    )


@pytest.mark.asyncio
async def test_non_eligible_decision_emits_one_sanitized_canonical_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observability = ObservabilityManager()
    warning = AsyncMock()
    monkeypatch.setattr(observability, "warning", warning)
    authority = classify_risk_authority(outside_authority_tool_response_input())

    decision = await PresentationSinkDecisionService(observability).evaluate(
        authority,
        blocking_reasons=("sensitive reason that must not enter telemetry",),
        limitations=("sensitive limitation that must not enter telemetry",),
    )

    assert decision.disposition is PresentationSinkDisposition.BLOCKED
    warning.assert_awaited_once()
    call = warning.await_args
    assert call.args == (
        "presentation.sink_decision",
        "PresentationSinkDecisionService",
    )
    assert call.kwargs["attributes"] == {
        "disposition": "blocked",
        "risk_tier": "prohibited_outside_authority",
        "gate_profile": "prohibited_boundary",
        "gate_failure_mode": "prohibited_boundary",
        "reason_count": 2,
        "limitation_count": 1,
    }
    assert "sensitive" not in str(call.kwargs)


@pytest.mark.asyncio
async def test_telemetry_failure_does_not_replace_sink_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observability = ObservabilityManager()
    warning = AsyncMock(side_effect=RuntimeError("telemetry unavailable"))
    monkeypatch.setattr(observability, "warning", warning)
    authority = classify_risk_authority(outside_authority_tool_response_input())

    decision = await PresentationSinkDecisionService(observability).evaluate(authority)

    assert decision.disposition is PresentationSinkDisposition.BLOCKED
    warning.assert_awaited_once()
