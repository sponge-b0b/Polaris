from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement, Select

from core.database.models.governance_audit import (
    AutomatedGovernanceAuditRecordModel,
    AutomatedPolicyAuditRecordModel,
    GovernanceReviewTaskModel,
)
from core.storage.persistence.governance_audit import (
    AutomatedDecisionAuditPersistenceResult,
    AutomatedDecisionAuditRepository,
    AutomatedGovernanceAuditRecord,
    AutomatedPolicyAuditRecord,
    GovernanceReviewTaskRecord,
)
from core.storage.persistence.serializers import (
    AutomatedDecisionAuditPersistenceSerializer,
)

logger = logging.getLogger(__name__)


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
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            logger.exception(
                "Automated policy audit record write failed.",
                extra={"audit_record_id": record.audit_record_id},
            )
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=record.audit_record_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            record.audit_record_id,
            records_persisted=max(getattr(result, "rowcount", 1), 0),
        )

    async def persist_governance_audit_record(
        self,
        record: AutomatedGovernanceAuditRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(_insert_governance_statement(record))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            logger.exception(
                "Automated governance audit record write failed.",
                extra={"audit_record_id": record.audit_record_id},
            )
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=record.audit_record_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            record.audit_record_id,
            records_persisted=max(getattr(result, "rowcount", 1), 0),
        )

    async def persist_governance_review_task(
        self,
        task: GovernanceReviewTaskRecord,
    ) -> AutomatedDecisionAuditPersistenceResult:
        try:
            result = await self._session.execute(_upsert_review_task_statement(task))
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            logger.exception(
                "Governance review task write failed.",
                extra={"review_task_id": task.review_task_id},
            )
            return AutomatedDecisionAuditPersistenceResult.failed(
                str(exc),
                audit_record_id=task.review_task_id,
            )
        return AutomatedDecisionAuditPersistenceResult.succeeded(
            task.review_task_id,
            records_persisted=max(getattr(result, "rowcount", 1), 0),
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
        constraint="uq_governance_review_tasks_scoped_evidence_action",
        set_={
            "automated_governance_audit_record_id": (
                statement.excluded.automated_governance_audit_record_id
            ),
            "authority_metadata": statement.excluded.authority_metadata,
            "evidence_references": statement.excluded.evidence_references,
            "updated_at": statement.excluded.updated_at,
        },
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
        stmt, AutomatedPolicyAuditRecordModel, start, end
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
