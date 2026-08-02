from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.governance import (
    AutomatedDecisionAuditContext,
    AutomatedDecisionAuditService,
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
)
from domain.authority import RiskAuthorityContract, classify_risk_authority
from tests.helpers.risk_authority_examples import (
    recommendation_explanation_authority_input,
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
    timestamp: datetime | None = None,
) -> AutomatedDecisionAuditContext:
    return AutomatedDecisionAuditContext(
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        authority=authority
        or classify_risk_authority(recommendation_explanation_authority_input()),
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        timestamp=timestamp,
    )


class FakeAutomatedDecisionAuditRepository(AutomatedDecisionAuditRepository):
    def __init__(self) -> None:
        self.policy_records: list[AutomatedPolicyAuditRecord] = []
        self.governance_records: list[AutomatedGovernanceAuditRecord] = []

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
