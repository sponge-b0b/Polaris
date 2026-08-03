from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import cast

import pytest
import pytest_asyncio
from sqlalchemy import Table, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from application.governance import (
    AutomatedDecisionAuditContext,
    AutomatedDecisionAuditQuery,
    AutomatedDecisionAuditService,
    GovernanceResidualRiskAcceptanceQuery,
    GovernanceResidualRiskAcceptanceRequest,
    GovernanceReviewApprovalState,
    GovernanceReviewDecisionQuery,
    GovernanceReviewResolutionRequest,
    GovernanceReviewTaskQuery,
)
from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceResidualRiskAcceptanceModel,
    GovernanceReviewDecisionModel,
    GovernanceReviewTaskModel,
)
from core.runtime.governance import GovernanceResult
from core.runtime.policies import PolicyResult
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedPolicyAuditOutcome,
    GovernanceReviewDecisionOutcome,
    GovernanceReviewerActorType,
    GovernanceReviewerIdentity,
    GovernanceReviewTaskStatus,
)
from core.storage.persistence.repositories import (
    PostgresAutomatedDecisionAuditRepository,
)
from domain.authority import RiskTier, classify_risk_authority
from tests.helpers.risk_authority_examples import (
    recommendation_explanation_authority_input,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")
TICKET_134_PACKET_ID = "ticket-134-packet"

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason=(
        "POLARIS_TEST_DATABASE_URL is required for Postgres-backed application "
        "governance integration tests."
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
            ).create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                AutomatedGovernanceAuditRecordModel.__table__,
            ).create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                GovernanceReviewTaskModel.__table__,
            ).create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                GovernanceResidualRiskAcceptanceModel.__table__,
            ).create(sync_connection, checkfirst=True)
        )
        await connection.run_sync(
            lambda sync_connection: cast(
                Table,
                GovernanceReviewDecisionModel.__table__,
            ).create(sync_connection, checkfirst=True)
        )

    yield session_factory

    await engine.dispose()


@pytest.mark.asyncio
async def test_application_review_queries_read_authoritative_postgres_records(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _delete_ticket_134_records(postgres_session_factory)
    try:
        review_task_id: str | None = None
        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            service = AutomatedDecisionAuditService(repository)
            context = AutomatedDecisionAuditContext(
                subject=AutomatedDecisionSubject(
                    "recommendation",
                    "ticket-134-rec",
                ),
                authority=classify_risk_authority(
                    recommendation_explanation_authority_input(),
                ),
                evidence=AutomatedDecisionEvidenceReference(
                    TICKET_134_PACKET_ID,
                    7,
                ),
                timestamp=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
            )

            await service.record_policy_decision(
                context=context,
                result=PolicyResult.deny(
                    policy_name="ticket_134_policy",
                    message="capital limit requires review visibility",
                    reason="ticket_134_policy_denied",
                ),
            )
            governance_result = await service.record_governance_decision(
                context=context,
                result=GovernanceResult.require_approval(
                    rule_name="ticket_134_governance_rule",
                    message="vigilant output requires human review",
                    reason="ticket_134_requires_approval",
                    metadata={"authority_subject_family": "recommendation"},
                ),
            )
            review_task_id = governance_result.review_task_id

        assert review_task_id is not None
        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            service = AutomatedDecisionAuditService(repository)

            policy_records = await service.list_policy_audit_records(
                AutomatedDecisionAuditQuery(
                    subject_type="recommendation",
                    subject_id="ticket-134-rec",
                    risk_tier=RiskTier.VIGILANT,
                    outcome=AutomatedPolicyAuditOutcome.DENY,
                    policy_name="ticket_134_policy",
                    evidence_packet_id=TICKET_134_PACKET_ID,
                    evidence_packet_version=7,
                ),
            )
            pending_states = await service.list_governance_review_states(
                GovernanceReviewTaskQuery(
                    subject_type="recommendation",
                    subject_id="ticket-134-rec",
                    risk_tier="vigilant",
                    approval_state=GovernanceReviewApprovalState.PENDING_REVIEW,
                    review_scope="recommendation",
                    requested_action="ticket_134_requires_approval",
                    evidence_packet_id=TICKET_134_PACKET_ID,
                    evidence_packet_version=7,
                    closed=False,
                ),
            )

        assert len(policy_records) == 1
        assert len(pending_states) == 1
        assert pending_states[0].review_task_id == review_task_id
        assert pending_states[0].audit_history == ()

        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            service = AutomatedDecisionAuditService(repository)
            task = await repository.get_governance_review_task(review_task_id)
            assert task is not None
            await service.resolve_governance_review_task(
                GovernanceReviewResolutionRequest(
                    review_task_id=review_task_id,
                    outcome=GovernanceReviewDecisionOutcome.APPROVED,
                    reviewer=_reviewer(),
                    rationale="Human reviewer approves ticket 134 visibility state.",
                    reviewed_evidence=task.evidence,
                    review_scope=task.review_scope,
                    residual_risk_remaining=True,
                    residual_risk_acceptance=GovernanceResidualRiskAcceptanceRequest(
                        reviewer=_reviewer(),
                        rationale="Accept residual risk for ticket 134 output only.",
                        residual_risk_scope="ticket 134 publication only",
                    ),
                ),
            )

        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            service = AutomatedDecisionAuditService(repository)
            closed_states = await service.list_governance_review_states(
                GovernanceReviewTaskQuery(
                    status=GovernanceReviewTaskStatus.APPROVED,
                    evidence_packet_id=TICKET_134_PACKET_ID,
                    evidence_packet_version=7,
                    closed=True,
                ),
            )
            decisions = await service.list_governance_review_decisions(
                GovernanceReviewDecisionQuery(
                    review_task_id=review_task_id,
                    outcome=GovernanceReviewDecisionOutcome.APPROVED,
                    reviewer_id="reviewer-1",
                    reviewer_actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
                    evidence_packet_id=TICKET_134_PACKET_ID,
                    evidence_packet_version=7,
                ),
            )
            acceptances = await service.list_residual_risk_acceptances(
                GovernanceResidualRiskAcceptanceQuery(
                    review_task_id=review_task_id,
                    residual_risk_scope="ticket 134 publication only",
                    reviewer_id="reviewer-1",
                    reviewer_actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
                    evidence_packet_id=TICKET_134_PACKET_ID,
                    evidence_packet_version=7,
                ),
            )
            inspected_state = await service.get_governance_review_state(review_task_id)

        assert len(closed_states) == 1
        assert len(decisions) == 1
        assert len(acceptances) == 1
        assert inspected_state.approval_state is (
            GovernanceReviewApprovalState.REVIEW_APPROVED
        )
        assert inspected_state.audit_history == decisions
        assert inspected_state.residual_risk_acceptances == acceptances
        assert inspected_state.task.status is GovernanceReviewTaskStatus.APPROVED
    finally:
        await _delete_ticket_134_records(postgres_session_factory)


async def _delete_ticket_134_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(GovernanceReviewDecisionModel).where(
                GovernanceReviewDecisionModel.evidence_packet_id
                == TICKET_134_PACKET_ID,
            )
        )
        await session.execute(
            delete(GovernanceResidualRiskAcceptanceModel).where(
                GovernanceResidualRiskAcceptanceModel.evidence_packet_id
                == TICKET_134_PACKET_ID,
            )
        )
        await session.execute(
            delete(GovernanceReviewTaskModel).where(
                GovernanceReviewTaskModel.evidence_packet_id == TICKET_134_PACKET_ID,
            )
        )
        await session.execute(
            delete(AutomatedGovernanceAuditRecordModel).where(
                AutomatedGovernanceAuditRecordModel.evidence_packet_id
                == TICKET_134_PACKET_ID,
            )
        )
        await session.execute(
            delete(AutomatedPolicyAuditRecordModel).where(
                AutomatedPolicyAuditRecordModel.evidence_packet_id
                == TICKET_134_PACKET_ID,
            )
        )
        await session.commit()


def _reviewer() -> GovernanceReviewerIdentity:
    return GovernanceReviewerIdentity(
        reviewer_id="reviewer-1",
        actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
        display_name="Jane Reviewer",
    )
