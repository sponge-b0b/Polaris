from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.governance_audit import AutomatedGovernanceAuditRecordModel
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditOutcome,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditOutcome,
    AutomatedPolicyAuditRecord,
)
from core.storage.persistence.repositories.postgres_governance_audit_repository import (
    PostgresAutomatedDecisionAuditRepository,
)
from core.storage.persistence.serializers import (
    AutomatedDecisionAuditPersistenceSerializer,
)
from domain.authority import RiskTier
from tests.helpers.risk_authority_examples import authority_metadata_for_tier


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


class FakeAsyncSession:
    def __init__(self, result: FakeExecuteResult | None = None) -> None:
        self.result = result or FakeExecuteResult([])
        self.executed: list[Any] = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        return self.result

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeExecuteResult:
    rowcount = 1

    def __init__(self, models: list[Any]) -> None:
        self._models = models

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
