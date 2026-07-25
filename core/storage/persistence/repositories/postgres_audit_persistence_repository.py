from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.audit import PersistenceAuditEventModel
from core.storage.persistence.audit import (
    PersistenceAuditEventRecord,
    PersistenceAuditEventRepository,
    PersistenceAuditEventResult,
)
from core.storage.persistence.serializers.audit_persistence_serializer import (
    PersistenceAuditEventSerializer,
)


class PostgresPersistenceAuditEventRepository(PersistenceAuditEventRepository):
    """
    PostgreSQL adapter for append-only persistence audit events.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session

    async def persist_audit_event(
        self,
        event: PersistenceAuditEventRecord,
    ) -> PersistenceAuditEventResult:
        try:
            await self._session.execute(
                _insert_audit_event_statement(
                    event,
                )
            )
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()

            return PersistenceAuditEventResult.failed(
                str(exc),
            )

        return PersistenceAuditEventResult.succeeded(
            audit_event_id=event.audit_event_id,
        )

    async def get_audit_event(
        self,
        audit_event_id: str,
    ) -> PersistenceAuditEventRecord | None:
        stmt = select(PersistenceAuditEventModel).where(
            PersistenceAuditEventModel.audit_event_id == audit_event_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        return PersistenceAuditEventSerializer.event_from_model(
            model,
        )

    async def list_audit_events(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        system_source: str | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[PersistenceAuditEventRecord, ...]:
        stmt = _audit_event_query_statement(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            system_source=system_source,
            actor_id=actor_id,
            actor_type=actor_type,
            workflow_name=workflow_name,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            start=start,
            end=end,
        )
        result = await self._session.execute(stmt)

        return tuple(
            PersistenceAuditEventSerializer.event_from_model(
                model,
            )
            for model in result.scalars().all()
        )


def _insert_audit_event_statement(
    event: PersistenceAuditEventRecord,
) -> Any:
    values = PersistenceAuditEventSerializer.event_values(
        event,
    )
    return insert(PersistenceAuditEventModel).values(**values)


def _audit_event_query_statement(
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    system_source: str | None = None,
    actor_id: str | None = None,
    actor_type: str | None = None,
    workflow_name: str | None = None,
    execution_id: str | None = None,
    runtime_id: str | None = None,
    node_name: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> Any:
    stmt = select(PersistenceAuditEventModel)
    for column, value in (
        (PersistenceAuditEventModel.entity_type, entity_type),
        (PersistenceAuditEventModel.entity_id, entity_id),
        (PersistenceAuditEventModel.action, action),
        (PersistenceAuditEventModel.system_source, system_source),
        (PersistenceAuditEventModel.actor_id, actor_id),
        (PersistenceAuditEventModel.actor_type, actor_type),
        (PersistenceAuditEventModel.workflow_name, workflow_name),
        (PersistenceAuditEventModel.execution_id, execution_id),
        (PersistenceAuditEventModel.runtime_id, runtime_id),
        (PersistenceAuditEventModel.node_name, node_name),
    ):
        stmt = _where_if_not_none(
            stmt,
            column,
            value,
        )

    stmt = _where_timestamp_window(
        stmt,
        start=start,
        end=end,
    )

    return stmt.order_by(
        PersistenceAuditEventModel.timestamp.desc(),
        PersistenceAuditEventModel.audit_event_id.asc(),
    )


def _where_if_not_none(
    stmt: Any,
    column: Any,
    value: Any | None,
) -> Any:
    if value is None:
        return stmt
    return stmt.where(
        column == value,
    )


def _where_timestamp_window(
    stmt: Any,
    *,
    start: datetime | None,
    end: datetime | None,
) -> Any:
    if start is not None:
        stmt = stmt.where(
            PersistenceAuditEventModel.timestamp >= start,
        )
    if end is not None:
        stmt = stmt.where(
            PersistenceAuditEventModel.timestamp <= end,
        )
    return stmt
