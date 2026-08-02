from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import cast

import pytest
import pytest_asyncio
from sqlalchemy import Table, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
from core.storage.persistence.repositories import (
    PostgresAutomatedDecisionAuditRepository,
)
from domain.authority import RiskTier
from tests.helpers.risk_authority_examples import authority_metadata_for_tier

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "POLARIS_TEST_DATABASE_URL is required for Postgres persistence integration "
        "tests."
    ),
)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                AutomatedPolicyAuditRecordModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                AutomatedGovernanceAuditRecordModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )

    yield session_factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_governance_audit_records_survive_round_trip(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    policy_record = _policy_record(AutomatedPolicyAuditOutcome.SKIP)
    governance_record = _governance_record(
        AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL,
    )

    await _delete_test_records(postgres_session_factory)
    try:
        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)

            policy_result = await repository.persist_policy_audit_record(policy_record)
            governance_result = await repository.persist_governance_audit_record(
                governance_record,
            )

            assert policy_result.success is True
            assert governance_result.success is True

        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)

            persisted_policy = await repository.get_policy_audit_record(
                policy_record.audit_record_id,
            )
            persisted_governance = await repository.get_governance_audit_record(
                governance_record.audit_record_id,
            )
            queried_governance = await repository.list_governance_audit_records(
                outcome="require_approval",
                evidence_packet_id="ticket-129-packet",
            )

        assert persisted_policy == policy_record
        assert persisted_governance == governance_record
        assert queried_governance == (governance_record,)
    finally:
        await _delete_test_records(postgres_session_factory)


async def _delete_test_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(AutomatedGovernanceAuditRecordModel).where(
                AutomatedGovernanceAuditRecordModel.audit_record_id.like(
                    "ticket-129-%",
                )
            )
        )
        await session.execute(
            delete(AutomatedPolicyAuditRecordModel).where(
                AutomatedPolicyAuditRecordModel.audit_record_id.like(
                    "ticket-129-%",
                )
            )
        )
        await session.commit()


def _policy_record(
    outcome: AutomatedPolicyAuditOutcome,
) -> AutomatedPolicyAuditRecord:
    return AutomatedPolicyAuditRecord(
        audit_record_id="ticket-129-policy-audit",
        subject=AutomatedDecisionSubject("recommendation", "ticket-129-rec"),
        risk_tier=RiskTier.ENHANCED,
        authority_metadata=authority_metadata_for_tier(RiskTier.ENHANCED),
        evidence=AutomatedDecisionEvidenceReference("ticket-129-packet", 1),
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
        audit_record_id="ticket-129-governance-audit",
        subject=AutomatedDecisionSubject("recommendation", "ticket-129-rec"),
        risk_tier=RiskTier.VIGILANT,
        authority_metadata=authority_metadata_for_tier(RiskTier.VIGILANT),
        evidence=AutomatedDecisionEvidenceReference("ticket-129-packet", 1),
        outcome=outcome,
        rule_name="authority_metadata_governance",
        reason="governance_reason",
        message="governance message",
        metadata={"rule_version": "2026-08-02"},
        timestamp=datetime(2026, 8, 2, 12, 0, tzinfo=UTC),
    )
