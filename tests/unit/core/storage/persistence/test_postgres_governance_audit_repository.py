from __future__ import annotations

from datetime import UTC, datetime
from inspect import Parameter, signature
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceResidualRiskAcceptanceModel,
    GovernanceReviewDecisionModel,
    GovernanceReviewTaskModel,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
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
from core.storage.persistence.repositories.postgres_governance_audit_repository import (
    PostgresAutomatedDecisionAuditRepository,
)
from core.storage.persistence.serializers import (
    AutomatedDecisionAuditPersistenceSerializer,
)
from domain.authority import RiskTier
from tests.helpers.risk_authority_examples import authority_metadata_for_tier


@pytest.mark.parametrize(
    ("records_persisted", "error"),
    [
        (0, "successful audit persistence"),
        (-1, "records_persisted"),
    ],
)
def test_successful_audit_persistence_result_requires_positive_durable_evidence(
    records_persisted: int,
    error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        AutomatedDecisionAuditPersistenceResult.succeeded(
            "policy-audit-1",
            records_persisted=records_persisted,
        )


def test_successful_audit_persistence_result_requires_an_observed_write_count() -> None:
    parameters = signature(AutomatedDecisionAuditPersistenceResult.succeeded).parameters

    assert parameters["records_persisted"].default is Parameter.empty


@pytest.mark.asyncio
async def test_persist_policy_audit_record_uses_authoritative_postgres_insert() -> None:
    session = FakeAsyncSession()
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    record = _policy_record(AutomatedPolicyAuditOutcome.DENY)

    result = await repository.persist_policy_audit_record(record)

    assert result.success is True
    assert result.audit_record_id == "policy-audit-1"
    assert session.committed is True
    compiled = session.executed[0].compile(dialect=postgresql.dialect())
    assert "INSERT INTO automated_policy_audit_records" in str(compiled)
    assert compiled.params["outcome"] == "deny"


@pytest.mark.asyncio
@pytest.mark.parametrize("rowcount", [0, -1])
async def test_persist_policy_audit_record_fails_closed_without_persisted_row(
    rowcount: int,
) -> None:
    session = FakeAsyncSession(result=FakeExecuteResult([], rowcount=rowcount))
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))

    result = await repository.persist_policy_audit_record(
        _policy_record(AutomatedPolicyAuditOutcome.DENY)
    )

    assert result.success is False
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_persist_policy_audit_record_fails_closed_without_rowcount() -> None:
    session = FakeAsyncSession(result=object())
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))

    result = await repository.persist_policy_audit_record(
        _policy_record(AutomatedPolicyAuditOutcome.DENY)
    )

    assert result.success is False
    assert session.committed is False
    assert session.rolled_back is True


@pytest.mark.asyncio
async def test_list_governance_audit_records_filters_queryable_states() -> None:
    model = AutomatedGovernanceAuditRecordModel(
        **AutomatedDecisionAuditPersistenceSerializer.governance_values(
            _governance_record(AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    start = datetime(2026, 8, 2, 11, 0, tzinfo=UTC)
    end = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)

    records = await repository.list_governance_audit_records(
        subject_type="recommendation",
        subject_id="rec-1",
        risk_tier="vigilant",
        outcome="require_approval",
        rule_name="authority_metadata_governance",
        evidence_packet_id="packet-1",
        start=start,
        end=end,
    )

    assert len(records) == 1
    assert records[0].outcome is AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL
    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    for expected_fragment in (
        "automated_governance_audit_records",
        "subject_type",
        "subject_id",
        "risk_tier",
        "outcome",
        "rule_name",
        "evidence_packet_id",
        "timestamp >=",
        "timestamp <=",
        "ORDER BY",
    ):
        assert expected_fragment in compiled


@pytest.mark.asyncio
async def test_list_policy_audit_records_filters_queryable_states() -> None:
    policy_record = _policy_record(AutomatedPolicyAuditOutcome.DENY)
    model = AutomatedPolicyAuditRecordModel(
        **AutomatedDecisionAuditPersistenceSerializer.policy_values(policy_record),
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    start = datetime(2026, 8, 2, 11, 0, tzinfo=UTC)
    end = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)

    records = await repository.list_policy_audit_records(
        subject_type="recommendation",
        subject_id="rec-1",
        risk_tier="enhanced",
        outcome="deny",
        policy_name="capital_policy",
        evidence_packet_id="packet-1",
        start=start,
        end=end,
    )

    assert records == (policy_record,)
    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    for expected_fragment in (
        "automated_policy_audit_records",
        "subject_type",
        "subject_id",
        "risk_tier",
        "outcome",
        "policy_name",
        "evidence_packet_id",
        "timestamp >=",
        "timestamp <=",
        "ORDER BY",
    ):
        assert expected_fragment in compiled


@pytest.mark.asyncio
async def test_persist_review_task_uses_sink_scoped_evidence_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    task = _review_task_record()

    result = await repository.persist_governance_review_task(task)

    assert result.success is True
    assert result.review_task_id == "governance-review-task-1"
    assert session.committed is True
    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))
    assert "INSERT INTO governance_review_tasks" in compiled
    assert "uq_governance_review_tasks_scoped_evidence_sink_action" in compiled


@pytest.mark.asyncio
async def test_list_review_tasks_filters_pending_evidence_queue() -> None:
    model = GovernanceReviewTaskModel(
        **AutomatedDecisionAuditPersistenceSerializer.review_task_values(
            _review_task_record(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))

    tasks = await repository.list_governance_review_tasks(
        subject_type="recommendation",
        subject_id="rec-1",
        risk_tier="vigilant",
        status="pending",
        evidence_packet_id="packet-1",
    )

    assert tasks == (_review_task_record(),)
    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    for expected_fragment in (
        "governance_review_tasks",
        "subject_type",
        "subject_id",
        "risk_tier",
        "status",
        "evidence_packet_id",
        "ORDER BY",
    ):
        assert expected_fragment in compiled


@pytest.mark.asyncio
async def test_persist_review_decision_uses_immutable_insert() -> None:
    session = FakeAsyncSession()
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    decision = _review_decision_record()

    result = await repository.persist_governance_review_decision(decision)

    assert result.success is True
    assert result.audit_record_id == "governance-review-decision-1"
    compiled = session.executed[0].compile(dialect=postgresql.dialect())
    assert "INSERT INTO governance_review_decisions" in str(compiled)
    assert compiled.params["reviewer_id"] == "reviewer-1"
    assert compiled.params["evidence_packet_version"] == 1
    assert compiled.params["resulting_task_status"] == "approved"
    assert compiled.params["requested_remediation"] is None


@pytest.mark.asyncio
async def test_persist_residual_risk_acceptance_uses_scoped_insert() -> None:
    session = FakeAsyncSession()
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    acceptance = _residual_risk_acceptance_record()

    result = await repository.persist_residual_risk_acceptance(acceptance)

    assert result.success is True
    assert result.audit_record_id == "governance-residual-risk-acceptance-1"
    compiled = session.executed[0].compile(dialect=postgresql.dialect())
    assert "INSERT INTO governance_residual_risk_acceptances" in str(compiled)
    assert compiled.params["residual_risk_scope"] == ("recommendation publication only")
    assert compiled.params["evidence_packet_version"] == 1


@pytest.mark.asyncio
async def test_update_review_task_status_updates_visible_state() -> None:
    session = FakeAsyncSession()
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))
    updated_at = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)

    result = await repository.update_governance_review_task_status(
        review_task_id="governance-review-task-1",
        status=GovernanceReviewTaskStatus.APPROVED,
        updated_at=updated_at,
    )

    assert result.success is True
    compiled = session.executed[0].compile(dialect=postgresql.dialect())
    assert "UPDATE governance_review_tasks" in str(compiled)
    assert compiled.params["status"] == "approved"
    assert compiled.params["updated_at"] == updated_at


@pytest.mark.asyncio
async def test_list_review_decisions_filters_by_scoped_evidence() -> None:
    decision = _review_decision_record(
        outcome=GovernanceReviewDecisionOutcome.CONTESTED,
        requested_remediation="Reconcile disputed decision evidence.",
    )
    model = GovernanceReviewDecisionModel(
        **AutomatedDecisionAuditPersistenceSerializer.review_decision_values(decision)
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))

    decisions = await repository.list_governance_review_decisions(
        review_task_id="governance-review-task-1",
        subject_type="recommendation",
        subject_id="rec-1",
        outcome="contested",
        evidence_packet_id="packet-1",
    )

    assert decisions == (decision,)
    assert decisions[0].resulting_task_status is GovernanceReviewTaskStatus.CONTESTED
    assert decisions[0].requested_remediation == (
        "Reconcile disputed decision evidence."
    )
    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    for expected_fragment in (
        "governance_review_decisions",
        "review_task_id",
        "subject_type",
        "subject_id",
        "outcome",
        "evidence_packet_id",
        "ORDER BY",
    ):
        assert expected_fragment in compiled


@pytest.mark.asyncio
async def test_list_residual_risk_acceptances_filters_by_scoped_evidence() -> None:
    model = GovernanceResidualRiskAcceptanceModel(
        **AutomatedDecisionAuditPersistenceSerializer.residual_risk_acceptance_values(
            _residual_risk_acceptance_record(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresAutomatedDecisionAuditRepository(cast(AsyncSession, session))

    acceptances = await repository.list_residual_risk_acceptances(
        review_task_id="governance-review-task-1",
        subject_type="recommendation",
        subject_id="rec-1",
        evidence_packet_id="packet-1",
    )

    assert acceptances == (_residual_risk_acceptance_record(),)
    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    for expected_fragment in (
        "governance_residual_risk_acceptances",
        "review_task_id",
        "subject_type",
        "subject_id",
        "evidence_packet_id",
        "ORDER BY",
    ):
        assert expected_fragment in compiled


class FakeAsyncSession:
    def __init__(self, result: Any | None = None) -> None:
        self.result = result or FakeExecuteResult([])
        self.executed: list[Any] = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: Any) -> Any:
        self.executed.append(statement)
        return self.result

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeExecuteResult:
    def __init__(self, models: list[Any], *, rowcount: int = 1) -> None:
        self._models = models
        self.rowcount = rowcount

    def scalar_one_or_none(self) -> Any | None:
        if not self._models:
            return None
        return self._models[0]

    def scalars(self) -> FakeScalars:
        return FakeScalars(self._models)


class FakeScalars:
    def __init__(self, models: list[Any]) -> None:
        self._models = models

    def all(self) -> list[Any]:
        return self._models


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
        audit_record_id="governance-audit-1",
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
        automated_governance_audit_record_id="governance-audit-1",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        authority_metadata=authority_metadata_for_tier(RiskTier.VIGILANT),
        review_scope="recommendation",
        intended_sink="recommendation",
        requested_action="vigilant_authority_requires_approval",
        status=GovernanceReviewTaskStatus.PENDING,
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        evidence_references={
            "automated_governance_audit_record_id": "governance-audit-1",
            "evidence_packet": {"packet_id": "packet-1", "packet_version": 1},
        },
        created_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )


def _review_decision_record(
    *,
    outcome: GovernanceReviewDecisionOutcome = GovernanceReviewDecisionOutcome.APPROVED,
    requested_remediation: str | None = None,
) -> GovernanceReviewDecisionRecord:
    return GovernanceReviewDecisionRecord(
        review_decision_id="governance-review-decision-1",
        review_task_id="governance-review-task-1",
        automated_governance_audit_record_id="governance-audit-1",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        outcome=outcome,
        reviewer=_reviewer(),
        rationale="Human reviewed scoped decision evidence.",
        review_scope="recommendation",
        evidence=AutomatedDecisionEvidenceReference("packet-1", 1),
        requested_remediation=requested_remediation,
        decided_at=datetime(2026, 8, 2, 13, 0, tzinfo=UTC),
    )


def _residual_risk_acceptance_record() -> GovernanceResidualRiskAcceptanceRecord:
    return GovernanceResidualRiskAcceptanceRecord(
        acceptance_id="governance-residual-risk-acceptance-1",
        review_task_id="governance-review-task-1",
        subject=AutomatedDecisionSubject("recommendation", "rec-1"),
        risk_tier=RiskTier.VIGILANT,
        reviewer=_reviewer(),
        rationale="Accept scoped residual risk.",
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
