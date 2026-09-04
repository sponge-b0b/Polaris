from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement, Select

from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceResidualRiskAcceptanceModel,
    GovernanceReviewDecisionModel,
    GovernanceReviewTaskModel,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedDecisionAuditRepository,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditRecord,
    GovernanceResidualRiskAcceptanceRecord,
    GovernanceReviewDecisionRecord,
    GovernanceReviewTaskRecord,
    GovernanceReviewTaskStatus,
)
from core.storage.persistence.serializers import (
    AutomatedDecisionAuditPersistenceSerializer,
)


@runtime_checkable
class _RowCountResult(Protocol):
    @property
    def rowcount(self) -> int: ...


def _records_persisted(result: Result[Any]) -> int:
    if not isinstance(result, _RowCountResult):
        raise ValueError("database write result does not expose a row count")
    if result.rowcount < 1:
        raise ValueError("database write result did not persist a record")
    return result.rowcount


class PostgresAutomatedDecisionAuditRepository(AutomatedDecisionAuditRepository):
    """PostgreSQL adapter for authoritative automated decision audit records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_policy_audit_record(
        self,
        record: AutomatedPolicyAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(_insert_policy_statement(record))
            records_persisted = _records_persisted(result)
            await self._session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self._session.rollback()
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=record.audit_record_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            record.audit_record_id,
            records_persisted=records_persisted,
        )

    async def persist_governance_audit_record(
        self,
        record: AutomatedGovernanceAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(_insert_governance_statement(record))
            records_persisted = _records_persisted(result)
            await self._session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self._session.rollback()
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=record.audit_record_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            record.audit_record_id,
            records_persisted=records_persisted,
        )

    async def persist_governance_review_task(
        self,
        task: GovernanceReviewTaskRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(_upsert_review_task_statement(task))
            records_persisted = _records_persisted(result)
            await self._session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self._session.rollback()
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=task.review_task_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            task.review_task_id,
            records_persisted=records_persisted,
            review_task_id=task.review_task_id,
        )

    async def get_policy_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedPolicyAuditRecord | None:
        result = await self._session.execute(
            select(AutomatedPolicyAuditRecordModel).where(
                AutomatedPolicyAuditRecordModel.audit_record_id == audit_record_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return AutomatedDecisionAuditPersistenceSerializer.policy_record_from_model(
            model,
        )

    async def get_governance_review_task(
        self,
        review_task_id: str,
    ) -> GovernanceReviewTaskRecord | None:
        result = await self._session.execute(
            select(GovernanceReviewTaskModel).where(
                GovernanceReviewTaskModel.review_task_id == review_task_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return AutomatedDecisionAuditPersistenceSerializer.review_task_from_model(
            model,
        )

    async def update_governance_review_task_status(
        self,
        *,
        review_task_id: str,
        status: GovernanceReviewTaskStatus,
        updated_at: datetime,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(
                update(GovernanceReviewTaskModel)
                .where(GovernanceReviewTaskModel.review_task_id == review_task_id)
                .values(status=status.value, updated_at=updated_at)
            )
            records_persisted = _records_persisted(result)
            await self._session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self._session.rollback()
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=review_task_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            review_task_id,
            records_persisted=records_persisted,
            review_task_id=review_task_id,
        )

    async def resolve_governance_review_task(
        self,
        *,
        decision: GovernanceReviewDecisionRecord,
        acceptance: GovernanceResidualRiskAcceptanceRecord | None,
        expected_task_updated_at: datetime,
        resolution_fingerprint: str,
    ) -> tuple[
        GovernanceReviewDecisionRecord,
        GovernanceResidualRiskAcceptanceRecord | None,
    ]:
        """Atomically append one review decision and update its task state."""
        try:
            if self._session.in_transaction():
                await self._session.rollback()
            async with self._session.begin():
                task_result = await self._session.execute(
                    select(GovernanceReviewTaskModel)
                    .where(
                        GovernanceReviewTaskModel.review_task_id
                        == decision.review_task_id
                    )
                    .with_for_update()
                )
                task = task_result.scalar_one_or_none()
                if task is None:
                    raise ValueError("governance review task was not found.")

                existing_result = await self._session.execute(
                    select(GovernanceReviewDecisionModel).where(
                        GovernanceReviewDecisionModel.review_task_id
                        == decision.review_task_id,
                        GovernanceReviewDecisionModel.resolution_fingerprint
                        == resolution_fingerprint,
                    )
                )
                existing = existing_result.scalar_one_or_none()
                if existing is not None:
                    persisted_acceptance = await self._acceptance_for_decision(existing)
                    return (
                        AutomatedDecisionAuditPersistenceSerializer.review_decision_from_model(
                            existing
                        ),
                        persisted_acceptance,
                    )

                if task.updated_at != expected_task_updated_at:
                    raise ValueError(
                        "governance review task changed before this resolution could "
                        "be applied."
                    )

                if acceptance is not None:
                    acceptance_result = await self._session.execute(
                        _insert_residual_risk_acceptance(acceptance)
                    )
                    _records_persisted(acceptance_result)

                decision_result = await self._session.execute(
                    _insert_review_decision(
                        decision,
                        resolution_fingerprint=resolution_fingerprint,
                    )
                )
                _records_persisted(decision_result)
                status_result = await self._session.execute(
                    update(GovernanceReviewTaskModel)
                    .where(
                        GovernanceReviewTaskModel.review_task_id
                        == decision.review_task_id
                    )
                    .values(
                        status=decision.resulting_task_status.value,
                        updated_at=decision.decided_at,
                    )
                )
                _records_persisted(status_result)
        except (SQLAlchemyError, ValueError):
            await self._session.rollback()
            raise
        return decision, acceptance

    async def get_governance_review_resolution(
        self,
        *,
        review_task_id: str,
        resolution_fingerprint: str,
    ) -> (
        tuple[
            GovernanceReviewDecisionRecord,
            GovernanceResidualRiskAcceptanceRecord | None,
        ]
        | None
    ):
        result = await self._session.execute(
            select(GovernanceReviewDecisionModel).where(
                GovernanceReviewDecisionModel.review_task_id == review_task_id,
                GovernanceReviewDecisionModel.resolution_fingerprint
                == resolution_fingerprint,
            )
        )
        decision = result.scalar_one_or_none()
        if decision is None:
            return None
        return (
            AutomatedDecisionAuditPersistenceSerializer.review_decision_from_model(
                decision
            ),
            await self._acceptance_for_decision(decision),
        )

    async def _acceptance_for_decision(
        self,
        decision: GovernanceReviewDecisionModel,
    ) -> GovernanceResidualRiskAcceptanceRecord | None:
        if decision.residual_risk_acceptance_id is None:
            return None
        result = await self._session.execute(
            select(GovernanceResidualRiskAcceptanceModel).where(
                GovernanceResidualRiskAcceptanceModel.acceptance_id
                == decision.residual_risk_acceptance_id
            )
        )
        acceptance = result.scalar_one_or_none()
        if acceptance is None:
            raise ValueError(
                "resolved review decision has no residual-risk acceptance."
            )
        serializer = AutomatedDecisionAuditPersistenceSerializer
        return serializer.residual_risk_acceptance_from_model(
            acceptance,
        )

    async def persist_governance_review_decision(
        self,
        decision: GovernanceReviewDecisionRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(_insert_review_decision(decision))
            records_persisted = _records_persisted(result)
            await self._session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self._session.rollback()
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=decision.review_decision_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            decision.review_decision_id,
            records_persisted=records_persisted,
        )

    async def get_governance_review_decision(
        self,
        review_decision_id: str,
    ) -> GovernanceReviewDecisionRecord | None:
        result = await self._session.execute(
            select(GovernanceReviewDecisionModel).where(
                GovernanceReviewDecisionModel.review_decision_id == review_decision_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return AutomatedDecisionAuditPersistenceSerializer.review_decision_from_model(
            model,
        )

    async def persist_residual_risk_acceptance(
        self,
        acceptance: GovernanceResidualRiskAcceptanceRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(
                _insert_residual_risk_acceptance(acceptance)
            )
            records_persisted = _records_persisted(result)
            await self._session.commit()
        except (SQLAlchemyError, ValueError) as exc:
            await self._session.rollback()
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=acceptance.acceptance_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            acceptance.acceptance_id,
            records_persisted=records_persisted,
        )

    async def get_residual_risk_acceptance(
        self,
        acceptance_id: str,
    ) -> GovernanceResidualRiskAcceptanceRecord | None:
        result = await self._session.execute(
            select(GovernanceResidualRiskAcceptanceModel).where(
                GovernanceResidualRiskAcceptanceModel.acceptance_id == acceptance_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        serializer = AutomatedDecisionAuditPersistenceSerializer
        return serializer.residual_risk_acceptance_from_model(model)

    async def get_governance_audit_record(
        self,
        audit_record_id: str,
    ) -> AutomatedGovernanceAuditRecord | None:
        result = await self._session.execute(
            select(AutomatedGovernanceAuditRecordModel).where(
                AutomatedGovernanceAuditRecordModel.audit_record_id == audit_record_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return AutomatedDecisionAuditPersistenceSerializer.governance_record_from_model(
            model,
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
    ) -> tuple[AutomatedPolicyAuditRecord, ...]:
        stmt = _policy_query_statement(
            subject_type=subject_type,
            subject_id=subject_id,
            risk_tier=risk_tier,
            outcome=outcome,
            policy_name=policy_name,
            evidence_packet_id=evidence_packet_id,
            start=start,
            end=end,
        )
        result = await self._session.execute(stmt)
        return tuple(
            AutomatedDecisionAuditPersistenceSerializer.policy_record_from_model(model)
            for model in result.scalars().all()
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
    ) -> tuple[AutomatedGovernanceAuditRecord, ...]:
        stmt = _governance_query_statement(
            subject_type=subject_type,
            subject_id=subject_id,
            risk_tier=risk_tier,
            outcome=outcome,
            rule_name=rule_name,
            evidence_packet_id=evidence_packet_id,
            start=start,
            end=end,
        )
        result = await self._session.execute(stmt)
        return tuple(
            AutomatedDecisionAuditPersistenceSerializer.governance_record_from_model(
                model,
            )
            for model in result.scalars().all()
        )

    async def list_governance_review_tasks(
        self,
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        risk_tier: str | None = None,
        status: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> tuple[GovernanceReviewTaskRecord, ...]:
        stmt = _review_task_query_statement(
            subject_type=subject_type,
            subject_id=subject_id,
            risk_tier=risk_tier,
            status=status,
            evidence_packet_id=evidence_packet_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            AutomatedDecisionAuditPersistenceSerializer.review_task_from_model(model)
            for model in result.scalars().all()
        )

    async def list_governance_review_decisions(
        self,
        *,
        review_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        outcome: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> tuple[GovernanceReviewDecisionRecord, ...]:
        stmt = _review_decision_query_statement(
            review_task_id=review_task_id,
            subject_type=subject_type,
            subject_id=subject_id,
            outcome=outcome,
            evidence_packet_id=evidence_packet_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            AutomatedDecisionAuditPersistenceSerializer.review_decision_from_model(
                model
            )
            for model in result.scalars().all()
        )

    async def list_residual_risk_acceptances(
        self,
        *,
        review_task_id: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        evidence_packet_id: str | None = None,
    ) -> tuple[GovernanceResidualRiskAcceptanceRecord, ...]:
        stmt = _residual_risk_acceptance_query_statement(
            review_task_id=review_task_id,
            subject_type=subject_type,
            subject_id=subject_id,
            evidence_packet_id=evidence_packet_id,
        )
        result = await self._session.execute(stmt)
        return tuple(
            AutomatedDecisionAuditPersistenceSerializer.residual_risk_acceptance_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _insert_policy_statement(record: AutomatedPolicyAuditRecord):
    return insert(AutomatedPolicyAuditRecordModel).values(
        **AutomatedDecisionAuditPersistenceSerializer.policy_values(record),
    )


def _insert_governance_statement(record: AutomatedGovernanceAuditRecord):
    return insert(AutomatedGovernanceAuditRecordModel).values(
        **AutomatedDecisionAuditPersistenceSerializer.governance_values(record),
    )


def _upsert_review_task_statement(task: GovernanceReviewTaskRecord):
    values = AutomatedDecisionAuditPersistenceSerializer.review_task_values(task)
    statement = insert(GovernanceReviewTaskModel).values(**values)
    return statement.on_conflict_do_update(
        constraint="uq_governance_review_tasks_scoped_evidence_sink_action",
        set_={
            "automated_governance_audit_record_id": (
                statement.excluded.automated_governance_audit_record_id
            ),
            "authority_metadata": statement.excluded.authority_metadata,
            "evidence_references": statement.excluded.evidence_references,
            "updated_at": statement.excluded.updated_at,
        },
    )


def _insert_review_decision(
    decision: GovernanceReviewDecisionRecord,
    *,
    resolution_fingerprint: str | None = None,
):
    serializer = AutomatedDecisionAuditPersistenceSerializer
    values = serializer.review_decision_values(decision)
    values["resolution_fingerprint"] = (
        resolution_fingerprint or decision.review_decision_id
    )
    return insert(GovernanceReviewDecisionModel).values(
        **values,
    )


def _insert_residual_risk_acceptance(
    acceptance: GovernanceResidualRiskAcceptanceRecord,
):
    return insert(GovernanceResidualRiskAcceptanceModel).values(
        **AutomatedDecisionAuditPersistenceSerializer.residual_risk_acceptance_values(
            acceptance,
        ),
    )


def _policy_query_statement(
    *,
    subject_type: str | None,
    subject_id: str | None,
    risk_tier: str | None,
    outcome: str | None,
    policy_name: str | None,
    evidence_packet_id: str | None,
    start: datetime | None,
    end: datetime | None,
) -> Select[tuple[AutomatedPolicyAuditRecordModel]]:
    stmt = select(AutomatedPolicyAuditRecordModel)
    if subject_type is not None:
        stmt = stmt.where(AutomatedPolicyAuditRecordModel.subject_type == subject_type)
    if subject_id is not None:
        stmt = stmt.where(AutomatedPolicyAuditRecordModel.subject_id == subject_id)
    if risk_tier is not None:
        stmt = stmt.where(AutomatedPolicyAuditRecordModel.risk_tier == risk_tier)
    if outcome is not None:
        stmt = stmt.where(AutomatedPolicyAuditRecordModel.outcome == outcome)
    if policy_name is not None:
        stmt = stmt.where(AutomatedPolicyAuditRecordModel.policy_name == policy_name)
    if evidence_packet_id is not None:
        stmt = stmt.where(
            AutomatedPolicyAuditRecordModel.evidence_packet_id == evidence_packet_id
        )
    return _timestamp_window(
        stmt,
        AutomatedPolicyAuditRecordModel.timestamp,
        start,
        end,
    ).order_by(
        AutomatedPolicyAuditRecordModel.timestamp.desc(),
        AutomatedPolicyAuditRecordModel.audit_record_id.asc(),
    )


def _governance_query_statement(
    *,
    subject_type: str | None,
    subject_id: str | None,
    risk_tier: str | None,
    outcome: str | None,
    rule_name: str | None,
    evidence_packet_id: str | None,
    start: datetime | None,
    end: datetime | None,
) -> Select[tuple[AutomatedGovernanceAuditRecordModel]]:
    stmt = select(AutomatedGovernanceAuditRecordModel)
    if subject_type is not None:
        stmt = stmt.where(
            AutomatedGovernanceAuditRecordModel.subject_type == subject_type
        )
    if subject_id is not None:
        stmt = stmt.where(AutomatedGovernanceAuditRecordModel.subject_id == subject_id)
    if risk_tier is not None:
        stmt = stmt.where(AutomatedGovernanceAuditRecordModel.risk_tier == risk_tier)
    if outcome is not None:
        stmt = stmt.where(AutomatedGovernanceAuditRecordModel.outcome == outcome)
    if rule_name is not None:
        stmt = stmt.where(AutomatedGovernanceAuditRecordModel.rule_name == rule_name)
    if evidence_packet_id is not None:
        stmt = stmt.where(
            AutomatedGovernanceAuditRecordModel.evidence_packet_id == evidence_packet_id
        )
    return _timestamp_window(
        stmt,
        AutomatedGovernanceAuditRecordModel.timestamp,
        start,
        end,
    ).order_by(
        AutomatedGovernanceAuditRecordModel.timestamp.desc(),
        AutomatedGovernanceAuditRecordModel.audit_record_id.asc(),
    )


def _review_task_query_statement(
    *,
    subject_type: str | None,
    subject_id: str | None,
    risk_tier: str | None,
    status: str | None,
    evidence_packet_id: str | None,
) -> Select[tuple[GovernanceReviewTaskModel]]:
    stmt = select(GovernanceReviewTaskModel)
    if subject_type is not None:
        stmt = stmt.where(GovernanceReviewTaskModel.subject_type == subject_type)
    if subject_id is not None:
        stmt = stmt.where(GovernanceReviewTaskModel.subject_id == subject_id)
    if risk_tier is not None:
        stmt = stmt.where(GovernanceReviewTaskModel.risk_tier == risk_tier)
    if status is not None:
        stmt = stmt.where(GovernanceReviewTaskModel.status == status)
    if evidence_packet_id is not None:
        stmt = stmt.where(
            GovernanceReviewTaskModel.evidence_packet_id == evidence_packet_id
        )
    return stmt.order_by(
        GovernanceReviewTaskModel.created_at.desc(),
        GovernanceReviewTaskModel.review_task_id.asc(),
    )


def _review_decision_query_statement(
    *,
    review_task_id: str | None,
    subject_type: str | None,
    subject_id: str | None,
    outcome: str | None,
    evidence_packet_id: str | None,
) -> Select[tuple[GovernanceReviewDecisionModel]]:
    stmt = select(GovernanceReviewDecisionModel)
    if review_task_id is not None:
        stmt = stmt.where(
            GovernanceReviewDecisionModel.review_task_id == review_task_id
        )
    if subject_type is not None:
        stmt = stmt.where(GovernanceReviewDecisionModel.subject_type == subject_type)
    if subject_id is not None:
        stmt = stmt.where(GovernanceReviewDecisionModel.subject_id == subject_id)
    if outcome is not None:
        stmt = stmt.where(GovernanceReviewDecisionModel.outcome == outcome)
    if evidence_packet_id is not None:
        stmt = stmt.where(
            GovernanceReviewDecisionModel.evidence_packet_id == evidence_packet_id
        )
    return stmt.order_by(
        GovernanceReviewDecisionModel.decided_at.desc(),
        GovernanceReviewDecisionModel.review_decision_id.asc(),
    )


def _residual_risk_acceptance_query_statement(
    *,
    review_task_id: str | None,
    subject_type: str | None,
    subject_id: str | None,
    evidence_packet_id: str | None,
) -> Select[tuple[GovernanceResidualRiskAcceptanceModel]]:
    stmt = select(GovernanceResidualRiskAcceptanceModel)
    if review_task_id is not None:
        stmt = stmt.where(
            GovernanceResidualRiskAcceptanceModel.review_task_id == review_task_id
        )
    if subject_type is not None:
        stmt = stmt.where(
            GovernanceResidualRiskAcceptanceModel.subject_type == subject_type
        )
    if subject_id is not None:
        stmt = stmt.where(
            GovernanceResidualRiskAcceptanceModel.subject_id == subject_id
        )
    if evidence_packet_id is not None:
        stmt = stmt.where(
            GovernanceResidualRiskAcceptanceModel.evidence_packet_id
            == evidence_packet_id
        )
    return stmt.order_by(
        GovernanceResidualRiskAcceptanceModel.accepted_at.desc(),
        GovernanceResidualRiskAcceptanceModel.acceptance_id.asc(),
    )


def _timestamp_window(
    stmt: Select[tuple[object]],
    timestamp: ColumnElement[datetime],
    start: datetime | None,
    end: datetime | None,
) -> Select[tuple[object]]:
    if start is not None:
        stmt = stmt.where(timestamp >= start)
    if end is not None:
        stmt = stmt.where(timestamp <= end)
    return stmt
