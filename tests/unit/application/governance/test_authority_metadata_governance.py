from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from application.governance import AuthorityMetadataGovernanceRule
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEligibilityDecision,
    WorkflowOutputProjectionEligibilityStatus,
)
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.runtime.governance import (
    GovernanceDecision,
    GovernanceEngine,
    GovernanceRegistry,
)
from core.storage.persistence.recommendations import RecommendationRecord
from core.storage.persistence.reports import ReportRecord
from domain.authority import (
    RiskTier,
    authority_contract_metadata,
    classify_risk_authority,
)
from tests.helpers.risk_authority_examples import (
    authority_metadata_for_tier,
    insufficient_runtime_evidence_authority_input,
    recommendation_explanation_authority_input,
    workflow_curation_authority_input,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tier", "subject", "expected_decision", "expected_reason"),
    [
        (
            RiskTier.BASELINE,
            "baseline internal evidence",
            GovernanceDecision.ALLOW,
            "baseline_authority_allowed",
        ),
        (
            RiskTier.ENHANCED,
            "enhanced durable record",
            GovernanceDecision.WARN,
            "enhanced_authority_requires_provenance",
        ),
        (
            RiskTier.VIGILANT,
            "vigilant capital output",
            GovernanceDecision.REQUIRE_APPROVAL,
            "vigilant_authority_requires_approval",
        ),
        (
            RiskTier.PROHIBITED_OUTSIDE_AUTHORITY,
            "outside authority output",
            GovernanceDecision.DENY,
            "prohibited_outside_authority",
        ),
    ],
)
async def test_governance_engine_maps_canonical_authority_tiers_to_outcomes(
    tier: RiskTier,
    subject: str,
    expected_decision: GovernanceDecision,
    expected_reason: str,
) -> None:
    result = await _engine().evaluate(
        subject={"risk_authority": _authority_metadata(tier)},
        context={"authority_subject_family": subject},
        emit_telemetry=False,
    )

    rule_result = result.results[0]
    assert rule_result.decision is expected_decision
    assert rule_result.reason == expected_reason
    assert rule_result.metadata["authority_subject_family"] == subject
    assert rule_result.metadata["risk_authority"]["risk_tier"] == tier.value
    assert rule_result.metadata["approval_subsystem_claimed"] is False


@pytest.mark.asyncio
async def test_governance_accepts_real_output_family_metadata() -> None:
    subjects = (
        _workflow_curation_decision(),
        _recommendation_record(),
        _rag_result(),
        _report_record(),
    )

    for subject in subjects:
        result = await _engine().evaluate(subject, emit_telemetry=False)

        rule_result = result.results[0]
        assert rule_result.decision in {
            GovernanceDecision.WARN,
            GovernanceDecision.REQUIRE_APPROVAL,
        }
        assert rule_result.metadata["risk_authority"]
        assert rule_result.metadata["authority_metadata_source"] in {
            "authority_contract",
            "authority_metadata",
            "metadata.risk_authority",
        }


@pytest.mark.asyncio
async def test_required_authority_metadata_fails_closed() -> None:
    result = await _engine().evaluate(
        subject=_SubjectWithMetadata(metadata={}),
        context={"authority_metadata_required": True},
        emit_telemetry=False,
    )

    rule_result = result.results[0]
    assert rule_result.decision is GovernanceDecision.DENY
    assert rule_result.reason == "authority_metadata_required"
    assert rule_result.metadata["authority_metadata_present"] is False


@pytest.mark.asyncio
async def test_enhanced_and_vigilant_outputs_require_evidence_when_absent() -> None:
    enhanced = await _engine().evaluate(
        subject={"risk_authority": _enhanced_metadata_with_insufficient_evidence()},
        emit_telemetry=False,
    )
    vigilant = await _engine().evaluate(
        subject={
            "risk_authority": _authority_metadata(
                RiskTier.VIGILANT, evidence_sufficient=False
            )
        },
        emit_telemetry=False,
    )

    assert enhanced.results[0].decision is GovernanceDecision.REQUIRE_APPROVAL
    assert enhanced.results[0].reason == "enhanced_authority_evidence_required"
    assert vigilant.results[0].decision is GovernanceDecision.DENY
    assert vigilant.results[0].reason == "vigilant_authority_evidence_required"


@pytest.mark.asyncio
async def test_prohibited_outside_authority_is_observable_denial() -> None:
    result = await _engine().evaluate(
        subject={
            "risk_authority": _authority_metadata(RiskTier.PROHIBITED_OUTSIDE_AUTHORITY)
        },
        emit_telemetry=False,
    )

    rule_result = result.results[0]
    assert rule_result.decision is GovernanceDecision.DENY
    assert rule_result.severity == "error"
    assert rule_result.reason == "prohibited_outside_authority"
    assert rule_result.metadata["governance_authority_failure_mode"] == (
        "prohibited_outside_authority"
    )
    assert (
        rule_result.metadata["risk_authority"]["gate_profile"] == "prohibited_boundary"
    )


@pytest.mark.asyncio
async def test_model_output_cannot_approve_governance_or_skip_governance() -> None:
    contract = classify_risk_authority(
        recommendation_explanation_authority_input(
            model_provided_metadata={
                "governance_approved": True,
                "residual_risk_accepted": True,
                "skip_governance": True,
                "risk_tier": "baseline",
            },
        )
    )

    result = await _engine().evaluate(
        subject=authority_contract_metadata(contract),
        emit_telemetry=False,
    )

    rule_result = result.results[0]
    assert rule_result.decision is GovernanceDecision.DENY
    assert rule_result.reason == "model_authority_claims_ignored"
    assert rule_result.metadata["risk_authority"]["risk_tier"] == "vigilant"
    assert rule_result.metadata["risk_authority"]["ignored_model_authority_claims"] == [
        "governance_approved",
        "residual_risk_accepted",
        "risk_tier",
        "skip_governance",
    ]


@pytest.mark.asyncio
async def test_model_output_cannot_downgrade_authority_profile() -> None:
    metadata = _authority_metadata(RiskTier.VIGILANT)
    metadata["risk_tier"] = "baseline"
    metadata["gate_profile"] = "baseline_internal"

    result = await _engine().evaluate(
        subject={"risk_authority": metadata},
        emit_telemetry=False,
    )

    rule_result = result.results[0]
    assert rule_result.decision is GovernanceDecision.DENY
    assert rule_result.reason == "authority_metadata_inconsistent"
    assert rule_result.metadata["expected_risk_tier"] == "vigilant"
    assert rule_result.metadata["observed_risk_tier"] == "baseline"


@dataclass(frozen=True, slots=True)
class _SubjectWithMetadata:
    metadata: dict[str, Any]


def _engine() -> GovernanceEngine:
    return GovernanceEngine(
        registry=GovernanceRegistry([AuthorityMetadataGovernanceRule()]),
    )


def _authority_metadata(
    tier: RiskTier,
    *,
    evidence_sufficient: bool = True,
) -> dict[str, object]:
    return authority_metadata_for_tier(
        tier,
        evidence_sufficient=evidence_sufficient,
    )


def _enhanced_metadata_with_insufficient_evidence() -> dict[str, object]:
    contract = classify_risk_authority(insufficient_runtime_evidence_authority_input())
    assert contract.risk_tier is RiskTier.ENHANCED
    return contract.to_metadata()


def _workflow_curation_decision() -> WorkflowOutputProjectionEligibilityDecision:
    contract = classify_risk_authority(workflow_curation_authority_input())
    return WorkflowOutputProjectionEligibilityDecision(
        status=WorkflowOutputProjectionEligibilityStatus.ELIGIBLE,
        node_name="curated_node",
        output_contract="polaris.test.curated",
        output_schema_version=1,
        authority_contract=contract,
    )


def _recommendation_record() -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id="rec-1",
        symbol="SPY",
        bias="constructive",
        confidence=0.7,
        created_at=datetime(2026, 7, 22, tzinfo=UTC),
        metadata=cast(
            dict[str, Any], {"risk_authority": _authority_metadata(RiskTier.VIGILANT)}
        ),
    )


def _rag_result() -> RagResult:
    request = RagRequest(query="Summarize breadth", request_id="rag-1")
    return RagResult.answered(
        request=request,
        answer_text="Breadth improved.",
        contexts=(),
        metadata=cast(
            dict[str, Any], {"risk_authority": _authority_metadata(RiskTier.ENHANCED)}
        ),
    )


def _report_record() -> ReportRecord:
    return ReportRecord(
        report_id="report-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 7, 22, tzinfo=UTC),
        markdown_body="# Morning Report\n",
        metadata=cast(
            dict[str, Any], {"risk_authority": _authority_metadata(RiskTier.VIGILANT)}
        ),
    )
