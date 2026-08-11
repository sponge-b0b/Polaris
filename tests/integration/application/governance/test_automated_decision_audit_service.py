from __future__ import annotations

import os
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock

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
    GovernedOutputReleaseRequest,
    GovernedWorkflowExecutionService,
)
from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceResidualRiskAcceptanceModel,
    GovernanceReviewDecisionModel,
    GovernanceReviewTaskModel,
)
from core.runtime.contracts.runtime_node import RuntimeNode
from core.runtime.governance import GovernanceResult
from core.runtime.governance.builtins.require_approval_for_live_mode_rule import (
    RequireApprovalForLiveModeRule,
)
from core.runtime.governance.governance_engine import GovernanceEngine
from core.runtime.governance.governance_registry import GovernanceRegistry
from core.runtime.governance.governance_rule import BaseGovernanceRule
from core.runtime.policies import PolicyResult
from core.runtime.state.runtime_context import RuntimeContext
from core.runtime.state.runtime_node_output import RuntimeNodeOutput
from core.storage.persistence.governance_audit import (
    AutomatedDecisionEvidenceReference,
    AutomatedDecisionSubject,
    AutomatedGovernanceAuditOutcome,
    AutomatedPolicyAuditOutcome,
    GovernanceReviewDecisionOutcome,
    GovernanceReviewerActorType,
    GovernanceReviewerIdentity,
    GovernanceReviewTaskStatus,
)
from core.storage.persistence.repositories import (
    PostgresAutomatedDecisionAuditRepository,
)
from core.workflow.bootstrap.workflow_bootstrap import (
    WorkflowBootstrapConfig,
    build_workflow_runtime_async,
)
from core.workflow.models.workflow_graph_definition import WorkflowGraphDefinition
from core.workflow.models.workflow_node_definition import WorkflowNodeDefinition
from domain.authority import IntendedSink, RiskTier, classify_risk_authority
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
    recommendation_explanation_authority_input,
)

TEST_DATABASE_URL = os.environ.get("POLARIS_TEST_DATABASE_URL")
TICKET_134_PACKET_ID = "ticket-134-packet"
TICKET_138_PACKET_ID = "ticket-138-packet"
TICKET_143_PACKET_ID = "ticket-143-packet"
TICKET_153_PACKET_ID = "ticket-153-packet"
TICKET_154_PACKET_ID = "ticket-154-packet"


class GovernanceAuditRuntimeNode(RuntimeNode):
    node_name = "governance_audit_runtime_node"
    node_type = "test.governance_audit.node"
    node_version = "1.0.0"

    parallel_safe = True

    async def _execute(
        self,
        context: RuntimeContext,
    ) -> RuntimeNodeOutput:
        return RuntimeNodeOutput.success_output(
            outputs={
                "ran": True,
            },
        )


class GovernanceAuditWorkflow(WorkflowGraphDefinition):
    @property
    def workflow_name(
        self,
    ) -> str:
        return "governance_audit_workflow"

    @property
    def workflow_description(
        self,
    ) -> str:
        return "Workflow used to prove facade governance audit persistence."

    def build_graph(
        self,
    ) -> list[WorkflowNodeDefinition]:
        return [
            WorkflowNodeDefinition(
                name="governance_audit_node",
                node_type=GovernanceAuditRuntimeNode,
                dependencies=(),
                enabled=True,
                tags=("governance", "audit", "test"),
            )
        ]


class StaticGovernanceResultRule(BaseGovernanceRule):
    """Return one controlled outcome through the production facade path."""

    rule_name = "static_governance_result"

    def __init__(self, result: GovernanceResult) -> None:
        self._result = result
        self.rule_name = result.rule_name

    async def evaluate(
        self,
        subject: object,
        context: dict[str, object] | None = None,
    ) -> GovernanceResult:
        if (context or {}).get("governance_phase") == "workflow_registration":
            return GovernanceResult.allow(self.rule_name)
        return self._result


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


@pytest.mark.asyncio
async def test_workflow_facade_requires_approval_records_postgres_audit_and_review_task(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _delete_ticket_138_records(postgres_session_factory)
    try:
        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            audit_service = AutomatedDecisionAuditService(repository)
            runtime = await build_workflow_runtime_async(
                config=WorkflowBootstrapConfig(
                    enable_governance=True,
                    enable_policies=False,
                    enable_telemetry=False,
                    enable_jsonl_telemetry=False,
                ),
                workflow_definitions=[
                    GovernanceAuditWorkflow(),
                ],
                governance_engine=GovernanceEngine(
                    registry=GovernanceRegistry(
                        rules=[
                            RequireApprovalForLiveModeRule(),
                        ],
                    )
                ),
            )
            packet = _ticket_138_packet()
            packet_persistence_service = AsyncMock()
            packet_persistence_service.reconstruct_packet.return_value = packet
            execution_service = GovernedWorkflowExecutionService(
                workflow_facade=runtime.facade,
                automated_decision_audit_service=audit_service,
                decision_evidence_packet_persistence_service=(
                    packet_persistence_service
                ),
                evidence_lifecycle=AsyncMock(),
                evidence_resolver=_resolver_returning(packet),
            )

            with pytest.raises(RuntimeError, match="live_mode_requires_approval"):
                await execution_service.run_workflow(
                    workflow_name="governance_audit_workflow",
                    execution_id="ticket-138-workflow-run",
                    mode="live",
                    archive_on_completion=False,
                    checkpoint_on_completion=False,
                )

        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            audit_service = AutomatedDecisionAuditService(repository)
            governance_records = await audit_service.list_governance_audit_records(
                AutomatedDecisionAuditQuery(
                    subject_type="workflow",
                    subject_id="ticket-138-workflow-run",
                    risk_tier=RiskTier.VIGILANT,
                    outcome=AutomatedGovernanceAuditOutcome.REQUIRE_APPROVAL,
                    rule_name="require_approval_for_live_mode",
                    evidence_packet_id=TICKET_138_PACKET_ID,
                    evidence_packet_version=1,
                ),
            )
            pending_states = await audit_service.list_governance_review_states(
                GovernanceReviewTaskQuery(
                    subject_type="workflow",
                    subject_id="ticket-138-workflow-run",
                    risk_tier="vigilant",
                    approval_state=GovernanceReviewApprovalState.PENDING_REVIEW,
                    review_scope="workflow",
                    requested_action="live_mode_requires_approval",
                    evidence_packet_id=TICKET_138_PACKET_ID,
                    evidence_packet_version=1,
                    closed=False,
                ),
            )

        assert len(governance_records) == 1
        assert len(pending_states) == 1
        assert pending_states[0].task.automated_governance_audit_record_id == (
            governance_records[0].audit_record_id
        )
    finally:
        await _delete_ticket_138_records(postgres_session_factory)


@pytest.mark.asyncio
async def test_sink_scoped_review_tasks_isolate_approval_and_release_state(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    publication_authority = classify_risk_authority(
        recommendation_explanation_authority_input(),
    )
    promotion_authority = replace(
        publication_authority,
        intended_sink=IntendedSink.DURABLE_DOMAIN_RECORD,
    )
    subject = AutomatedDecisionSubject("recommendation", "ticket-153-rec")
    evidence = AutomatedDecisionEvidenceReference(TICKET_153_PACKET_ID, 1)
    governance_result = GovernanceResult.require_approval(
        rule_name="ticket_153_governance_rule",
        message="Each release sink requires independent human review.",
        reason="ticket_153_requires_approval",
        metadata={"authority_subject_family": "recommendation"},
    )

    await _delete_ticket_153_records(postgres_session_factory)
    try:
        async with postgres_session_factory() as session:
            service = AutomatedDecisionAuditService(
                PostgresAutomatedDecisionAuditRepository(session),
            )
            publication_result = await service.record_governance_decision(
                context=AutomatedDecisionAuditContext(
                    subject=subject,
                    authority=publication_authority,
                    evidence=evidence,
                ),
                result=governance_result,
            )
            promotion_result = await service.record_governance_decision(
                context=AutomatedDecisionAuditContext(
                    subject=subject,
                    authority=promotion_authority,
                    evidence=evidence,
                ),
                result=governance_result,
            )
            publication_upsert_result = await service.record_governance_decision(
                context=AutomatedDecisionAuditContext(
                    subject=subject,
                    authority=publication_authority,
                    evidence=evidence,
                ),
                result=governance_result,
            )

            assert publication_result.review_task_id is not None
            assert promotion_result.review_task_id is not None
            assert publication_result.review_task_id != promotion_result.review_task_id
            assert publication_upsert_result.review_task_id == (
                publication_result.review_task_id
            )

        async with postgres_session_factory() as session:
            service = AutomatedDecisionAuditService(
                PostgresAutomatedDecisionAuditRepository(session),
            )
            publication_states = await service.list_governance_review_states(
                GovernanceReviewTaskQuery(
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    intended_sink=publication_authority.intended_sink.value,
                    evidence_packet_id=evidence.packet_id,
                    evidence_packet_version=evidence.packet_version,
                ),
            )
            promotion_states = await service.list_governance_review_states(
                GovernanceReviewTaskQuery(
                    subject_type=subject.subject_type,
                    subject_id=subject.subject_id,
                    intended_sink=promotion_authority.intended_sink.value,
                    evidence_packet_id=evidence.packet_id,
                    evidence_packet_version=evidence.packet_version,
                ),
            )

            assert len(publication_states) == 1
            assert len(promotion_states) == 1
            publication_task = publication_states[0].task
            promotion_task = promotion_states[0].task
            assert publication_task.review_task_id == publication_result.review_task_id
            assert promotion_task.review_task_id == promotion_result.review_task_id
            assert publication_task.intended_sink == IntendedSink.RECOMMENDATION.value
            assert (
                promotion_task.intended_sink == IntendedSink.DURABLE_DOMAIN_RECORD.value
            )

            await service.resolve_governance_review_task(
                GovernanceReviewResolutionRequest(
                    review_task_id=publication_task.review_task_id,
                    outcome=GovernanceReviewDecisionOutcome.APPROVED,
                    reviewer=_reviewer(),
                    rationale="Approve only the recommendation publication sink.",
                    reviewed_evidence=publication_task.evidence,
                    review_scope=publication_task.review_scope,
                ),
            )

            publication_release = await service.evaluate_governed_output_release(
                GovernedOutputReleaseRequest(
                    authority=publication_authority,
                    subject=subject,
                    evidence=evidence,
                    review_scope=publication_task.review_scope,
                    requested_action=publication_task.requested_action,
                    boundary_name="ticket-153 recommendation publication",
                ),
            )
            promotion_release = await service.evaluate_governed_output_release(
                GovernedOutputReleaseRequest(
                    authority=promotion_authority,
                    subject=subject,
                    evidence=evidence,
                    review_scope=promotion_task.review_scope,
                    requested_action=promotion_task.requested_action,
                    boundary_name="ticket-153 durable promotion",
                ),
            )

        assert publication_release.allowed is True
        assert publication_release.review_task_id == publication_task.review_task_id
        assert promotion_release.allowed is False
        assert promotion_release.review_task_id == promotion_task.review_task_id
        assert promotion_release.approval_state is (
            GovernanceReviewApprovalState.PENDING_REVIEW
        )
    finally:
        await _delete_ticket_153_records(postgres_session_factory)


@pytest.mark.asyncio
async def test_governed_release_requires_exact_postgres_residual_risk_scope(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    authority = classify_risk_authority(
        recommendation_explanation_authority_input(),
    )
    subject = AutomatedDecisionSubject("recommendation", "ticket-154-rec")
    evidence = AutomatedDecisionEvidenceReference(TICKET_154_PACKET_ID, 1)
    narrow_scope = "recommendation publication only"
    broader_scope = "recommendation publication and durable promotion"

    await _delete_ticket_154_records(postgres_session_factory)
    try:
        async with postgres_session_factory() as session:
            repository = PostgresAutomatedDecisionAuditRepository(session)
            service = AutomatedDecisionAuditService(
                repository,
            )
            governance_result = await service.record_governance_decision(
                context=AutomatedDecisionAuditContext(
                    subject=subject,
                    authority=authority,
                    evidence=evidence,
                ),
                result=GovernanceResult.require_approval(
                    rule_name="ticket_154_governance_rule",
                    message="Scoped residual-risk acceptance is required.",
                    reason="ticket_154_requires_approval",
                    metadata={"authority_subject_family": "recommendation"},
                ),
            )

            assert governance_result.review_task_id is not None
            review_task = await repository.get_governance_review_task(
                governance_result.review_task_id,
            )
            assert review_task is not None
            resolution = await service.resolve_governance_review_task(
                GovernanceReviewResolutionRequest(
                    review_task_id=review_task.review_task_id,
                    outcome=GovernanceReviewDecisionOutcome.APPROVED,
                    reviewer=_reviewer(),
                    rationale="Approve this narrow residual-risk scope only.",
                    reviewed_evidence=evidence,
                    review_scope=review_task.review_scope,
                    residual_risk_remaining=True,
                    residual_risk_acceptance=GovernanceResidualRiskAcceptanceRequest(
                        reviewer=_reviewer(),
                        rationale=(
                            "Accept residual risk for recommendation publication only."
                        ),
                        residual_risk_scope=narrow_scope,
                    ),
                ),
            )

        async with postgres_session_factory() as session:
            service = AutomatedDecisionAuditService(
                PostgresAutomatedDecisionAuditRepository(session),
            )
            broader_release = await service.evaluate_governed_output_release(
                GovernedOutputReleaseRequest(
                    authority=authority,
                    subject=subject,
                    evidence=evidence,
                    review_scope=review_task.review_scope,
                    requested_action=review_task.requested_action,
                    boundary_name="ticket-154 broader governed release",
                    residual_risk_acceptance_required=True,
                    residual_risk_scope=broader_scope,
                ),
            )
            exact_release = await service.evaluate_governed_output_release(
                GovernedOutputReleaseRequest(
                    authority=authority,
                    subject=subject,
                    evidence=evidence,
                    review_scope=review_task.review_scope,
                    requested_action=review_task.requested_action,
                    boundary_name="ticket-154 exact governed release",
                    residual_risk_acceptance_required=True,
                    residual_risk_scope=narrow_scope,
                ),
            )

        assert broader_release.allowed is False
        assert broader_release.approval_state is (
            GovernanceReviewApprovalState.RESIDUAL_RISK_ACCEPTANCE_REQUIRED
        )
        assert broader_release.residual_risk_acceptance_id is None
        assert exact_release.allowed is True
        assert exact_release.review_task_id == review_task.review_task_id
        assert resolution.residual_risk_acceptance is not None
        assert exact_release.residual_risk_acceptance_id == (
            resolution.residual_risk_acceptance.acceptance_id
        )
    finally:
        await _delete_ticket_154_records(postgres_session_factory)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("result", "outcome", "blocks_execution"),
    (
        (
            GovernanceResult.allow("ticket_143_allow"),
            AutomatedGovernanceAuditOutcome.ALLOW,
            False,
        ),
        (
            GovernanceResult.warn(
                "ticket_143_warn",
                message="Governance warning recorded.",
            ),
            AutomatedGovernanceAuditOutcome.WARN,
            False,
        ),
        (
            GovernanceResult.deny(
                "ticket_143_deny",
                message="Governance denial recorded.",
                reason="ticket_143_denied",
            ),
            AutomatedGovernanceAuditOutcome.DENY,
            True,
        ),
        (
            GovernanceResult.skip(
                "ticket_143_skip",
                message="Governance check skipped.",
            ),
            AutomatedGovernanceAuditOutcome.SKIP,
            False,
        ),
    ),
)
async def test_governed_execution_persists_nonapproval_outcomes(
    postgres_session_factory: async_sessionmaker[AsyncSession],
    result: GovernanceResult,
    outcome: AutomatedGovernanceAuditOutcome,
    blocks_execution: bool,
) -> None:
    await _delete_ticket_143_records(postgres_session_factory)
    try:
        async with postgres_session_factory() as session:
            audit_service = AutomatedDecisionAuditService(
                PostgresAutomatedDecisionAuditRepository(session),
            )
            runtime = await build_workflow_runtime_async(
                config=WorkflowBootstrapConfig(
                    enable_governance=True,
                    enable_policies=False,
                    enable_telemetry=False,
                    enable_jsonl_telemetry=False,
                ),
                workflow_definitions=[GovernanceAuditWorkflow()],
                governance_engine=GovernanceEngine(
                    registry=GovernanceRegistry(
                        rules=[StaticGovernanceResultRule(result)],
                    ),
                ),
            )
            packet = _ticket_143_packet()
            packet_persistence_service = AsyncMock()
            packet_persistence_service.reconstruct_packet.return_value = packet
            execution_service = GovernedWorkflowExecutionService(
                workflow_facade=runtime.facade,
                automated_decision_audit_service=audit_service,
                decision_evidence_packet_persistence_service=(
                    packet_persistence_service
                ),
                evidence_lifecycle=AsyncMock(),
                evidence_resolver=_resolver_returning(packet),
            )
            run = execution_service.run_workflow(
                workflow_name="governance_audit_workflow",
                execution_id="ticket-143-workflow-run",
                mode="live",
                archive_on_completion=False,
                checkpoint_on_completion=False,
            )
            if blocks_execution:
                with pytest.raises(RuntimeError, match="ticket_143_denied"):
                    await run
            else:
                assert (await run).success is True

        async with postgres_session_factory() as session:
            audit_service = AutomatedDecisionAuditService(
                PostgresAutomatedDecisionAuditRepository(session),
            )
            records = await audit_service.list_governance_audit_records(
                AutomatedDecisionAuditQuery(
                    subject_type="workflow",
                    subject_id="ticket-143-workflow-run",
                    risk_tier=RiskTier.VIGILANT,
                    outcome=outcome,
                    rule_name=result.rule_name,
                    evidence_packet_id=TICKET_143_PACKET_ID,
                    evidence_packet_version=1,
                ),
            )

        assert len(records) == 1
    finally:
        await _delete_ticket_143_records(postgres_session_factory)


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


async def _delete_ticket_138_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(GovernanceReviewDecisionModel).where(
                GovernanceReviewDecisionModel.evidence_packet_id
                == TICKET_138_PACKET_ID,
            )
        )
        await session.execute(
            delete(GovernanceResidualRiskAcceptanceModel).where(
                GovernanceResidualRiskAcceptanceModel.evidence_packet_id
                == TICKET_138_PACKET_ID,
            )
        )
        await session.execute(
            delete(GovernanceReviewTaskModel).where(
                GovernanceReviewTaskModel.evidence_packet_id == TICKET_138_PACKET_ID,
            )
        )
        await session.execute(
            delete(AutomatedGovernanceAuditRecordModel).where(
                AutomatedGovernanceAuditRecordModel.evidence_packet_id
                == TICKET_138_PACKET_ID,
            )
        )
        await session.execute(
            delete(AutomatedPolicyAuditRecordModel).where(
                AutomatedPolicyAuditRecordModel.evidence_packet_id
                == TICKET_138_PACKET_ID,
            )
        )
        await session.commit()


async def _delete_ticket_143_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await session.execute(
            delete(AutomatedGovernanceAuditRecordModel).where(
                AutomatedGovernanceAuditRecordModel.evidence_packet_id
                == TICKET_143_PACKET_ID,
            )
        )
        await session.commit()


async def _delete_ticket_153_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        for model in (
            GovernanceReviewDecisionModel,
            GovernanceResidualRiskAcceptanceModel,
            GovernanceReviewTaskModel,
            AutomatedGovernanceAuditRecordModel,
        ):
            await session.execute(
                delete(model).where(
                    model.evidence_packet_id == TICKET_153_PACKET_ID,
                )
            )
        await session.commit()


async def _delete_ticket_154_records(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        for model in (
            GovernanceReviewDecisionModel,
            GovernanceResidualRiskAcceptanceModel,
            GovernanceReviewTaskModel,
            AutomatedGovernanceAuditRecordModel,
        ):
            await session.execute(
                delete(model).where(
                    model.evidence_packet_id == TICKET_154_PACKET_ID,
                )
            )
        await session.commit()


def _ticket_138_packet() -> DecisionEvidencePacket:
    return _ticket_packet(
        packet_id=TICKET_138_PACKET_ID,
        output_id="ticket-138-workflow-output",
    )


def _ticket_143_packet() -> DecisionEvidencePacket:
    return _ticket_packet(
        packet_id=TICKET_143_PACKET_ID,
        output_id="ticket-143-workflow-output",
    )


def _ticket_packet(
    *,
    packet_id: str,
    output_id: str,
) -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        packet_id=packet_id,
        output_id=output_id,
        authority=classify_risk_authority(
            recommendation_explanation_authority_input(),
        ),
        claims=(
            MaterialClaim(
                claim_id="ticket-138-claim",
                text="Governed workflow evidence supports review.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("ticket-138-evidence",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="ticket-138-evidence",
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=("ticket-138-workflow-node",),
                summary="Workflow output retained for governance review.",
                support_snapshot=SupportingEvidenceSnapshot(
                    snapshot_id="ticket-138-snapshot",
                    summary="Redacted workflow evidence.",
                    redacted_content="governed workflow evidence",
                    source_label="workflow_node_output:ticket-138",
                ),
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="ticket-138-workflow-node",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="ticket-138-workflow-run:governance-audit-node",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-08-09T00:00:00Z",
            policy_id="ticket-138-retention",
        ),
    )


def _reviewer() -> GovernanceReviewerIdentity:
    return GovernanceReviewerIdentity(
        reviewer_id="reviewer-1",
        actor_type=GovernanceReviewerActorType.HUMAN_REVIEWER,
        display_name="Jane Reviewer",
    )


def _resolver_returning(evidence: DecisionEvidencePacket) -> AsyncMock:
    resolver = AsyncMock()
    resolver.resolve.return_value = evidence
    return resolver
