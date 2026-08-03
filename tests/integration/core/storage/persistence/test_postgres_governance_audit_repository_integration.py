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
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                GovernanceReviewTaskModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                GovernanceResidualRiskAcceptanceModel.__table__,
            ).create(
                sync_connection,
                checkfirst=True,
            )
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                GovernanceReviewDecisionModel.__table__,
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
            review_task = _review_task_record(governance_record)
            review_task_result = await repository.persist_governance_review_task(
                review_task,
            )
            acceptance = _residual_risk_acceptance_record(review_task)
            acceptance_result = await repository.persist_residual_risk_acceptance(
                acceptance,
            )
            decision = _review_decision_record(
                review_task,
                residual_risk_acceptance_id=acceptance.acceptance_id,
            )
            decision_result = await repository.persist_governance_review_decision(
                decision,
            )
            status_result = await repository.update_governance_review_task_status(
                review_task_id=review_task.review_task_id,
                status=GovernanceReviewTaskStatus.APPROVED,
                updated_at=decision.decided_at,
            )

            assert policy_result.success is True
            assert governance_result.success is True
            assert review_task_result.success is True
            assert acceptance_result.success is True
            assert decision_result.success is True
            assert status_result.success is True

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
            persisted_review_task = await repository.get_governance_review_task(
                review_task.review_task_id,
            )
            persisted_acceptance = await repository.get_residual_risk_acceptance(
                acceptance.acceptance_id,
            )
            persisted_decision = await repository.get_governance_review_decision(
                decision.review_decision_id,
            )
            queried_review_tasks = await repository.list_governance_review_tasks(
                status="approved",
                evidence_packet_id="ticket-129-packet",
            )
            queried_decisions = await repository.list_governance_review_decisions(
                outcome="approved",
                evidence_packet_id="ticket-129-packet",
            )
            queried_acceptances = await repository.list_residual_risk_acceptances(
                evidence_packet_id="ticket-129-packet",
            )

        assert persisted_policy == policy_record
        assert persisted_governance == governance_record
        assert queried_governance == (governance_record,)
        assert persisted_review_task is not None
        assert persisted_review_task.status is GovernanceReviewTaskStatus.APPROVED
        assert persisted_review_task.updated_at == decision.decided_at
        assert queried_review_tasks == (persisted_review_task,)
        assert persisted_acceptance == acceptance
        assert persisted_decision == decision
        assert queried_decisions == (decision,)
        assert queried_acceptances == (acceptance,)
    finally:
        await _delete_test_records(postgres_session_factory)


async def _delete_test_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(GovernanceReviewDecisionModel).where(
                GovernanceReviewDecisionModel.review_decision_id.like(
                    "ticket-129-%",
                )
            )
        )
        await session.execute(
            delete(GovernanceResidualRiskAcceptanceModel).where(
                GovernanceResidualRiskAcceptanceModel.acceptance_id.like(
                    "ticket-129-%",
                )
            )
        )
        await session.execute(
            delete(GovernanceReviewTaskModel).where(
                GovernanceReviewTaskModel.review_task_id.like(
                    "ticket-129-%",
                )
            )
        )
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


def _review_task_record(
    governance_record: AutomatedGovernanceAuditRecord,
) -> GovernanceReviewTaskRecord:
    assert governance_record.evidence is not None
    return GovernanceReviewTaskRecord(
        review_task_id="ticket-129-governance-review-task",
        automated_governance_audit_record_id=governance_record.audit_record_id,
        subject=governance_record.subject,
        risk_tier=governance_record.risk_tier,
        authority_metadata=governance_record.authority_metadata,
        review_scope="recommendation",
        intended_sink="recommendation",
        requested_action="governance_reason",
        status=GovernanceReviewTaskStatus.PENDING,
        evidence=governance_record.evidence,
        evidence_references={
            "automated_governance_audit_record_id": governance_record.audit_record_id,
        },
        created_at=governance_record.timestamp,
        updated_at=governance_record.timestamp,
    )


def _review_decision_record(
    review_task: GovernanceReviewTaskRecord,
    *,
    residual_risk_acceptance_id: str,
) -> GovernanceReviewDecisionRecord:
    return GovernanceReviewDecisionRecord(
        review_decision_id="ticket-129-review-decision",
        review_task_id=review_task.review_task_id,
        automated_governance_audit_record_id=(
            review_task.automated_governance_audit_record_id
        ),
        subject=review_task.subject,
        risk_tier=review_task.risk_tier,
        outcome=GovernanceReviewDecisionOutcome.APPROVED,
        reviewer=_reviewer(),
        rationale="Human reviewer approved the scoped evidence packet.",
        review_scope=review_task.review_scope,
        evidence=review_task.evidence,
        decided_at=datetime(2026, 8, 2, 13, 0, tzinfo=UTC),
        residual_risk_acceptance_required=True,
        residual_risk_acceptance_id=residual_risk_acceptance_id,
    )


def _residual_risk_acceptance_record(
    review_task: GovernanceReviewTaskRecord,
) -> GovernanceResidualRiskAcceptanceRecord:
    return GovernanceResidualRiskAcceptanceRecord(
        acceptance_id="ticket-129-residual-risk-acceptance",
        review_task_id=review_task.review_task_id,
        subject=review_task.subject,
        risk_tier=review_task.risk_tier,
        reviewer=_reviewer(),
        rationale="Accept residual market risk for this output only.",
        review_scope=review_task.review_scope,
        residual_risk_scope="recommendation publication only",
        evidence=review_task.evidence,
        accepted_at=datetime(2026, 8, 2, 13, 5, tzinfo=UTC),
    )


def _reviewer() -> GovernanceReviewerIdentity:
    return GovernanceReviewerIdentity(
        reviewer_id="reviewer-1",
        actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
        display_name="Jane Reviewer",
    )
