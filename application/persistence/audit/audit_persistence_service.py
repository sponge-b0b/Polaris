from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from core.storage.persistence.audit import PersistenceAuditEventRecord
from core.storage.persistence.audit import PersistenceAuditEventRepository
from core.storage.persistence.audit import PersistenceAuditEventResult
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.query import PersistenceCommonQuery
from core.storage.persistence.query import PersistenceListResult

from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class AuditPersistenceFilters:
    """
    Typed application-layer filters for persistence audit event retrieval.
    """

    entity_type: str | None = None
    entity_id: str | None = None
    action: str | None = None
    system_source: str | None = None
    actor_id: str | None = None
    actor_type: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "entity_type",
            "entity_id",
            "action",
            "system_source",
            "actor_id",
            "actor_type",
            "workflow_name",
            "execution_id",
            "runtime_id",
            "node_name",
        ):
            object.__setattr__(
                self,
                field_name,
                clean_optional_identifier(
                    getattr(
                        self,
                        field_name,
                    ),
                    field_name,
                ),
            )
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be less than or equal to end.")

    def to_common_query(
        self,
    ) -> PersistenceCommonQuery:
        return build_common_query(
            record_type="persistence_audit_event",
            workflow_name=self.workflow_name,
            execution_id=self.execution_id,
            runtime_id=self.runtime_id,
            node_name=self.node_name,
            start=self.start,
            end=self.end,
            metadata={
                "entity_type": self.entity_type,
                "entity_id": self.entity_id,
                "action": self.action,
                "system_source": self.system_source,
                "actor_id": self.actor_id,
                "actor_type": self.actor_type,
            },
        )


class AuditPersistenceService:
    """
    Application service for append-only persistence audit events.
    """

    def __init__(
        self,
        repository: PersistenceAuditEventRepository,
    ) -> None:
        self._repository = repository

    async def persist_audit_event(
        self,
        event: PersistenceAuditEventRecord,
    ) -> PersistenceAuditEventResult:
        return await self._repository.persist_audit_event(
            event,
        )

    async def get_audit_event(
        self,
        audit_event_id: str,
    ) -> PersistenceAuditEventRecord | None:
        return await self._repository.get_audit_event(
            audit_event_id,
        )

    async def list_audit_events(
        self,
        filters: AuditPersistenceFilters | None = None,
    ) -> Sequence[PersistenceAuditEventRecord]:
        result = await self.list_audit_events_result(
            filters,
        )
        return result.records

    async def list_audit_events_result(
        self,
        filters: AuditPersistenceFilters | None = None,
    ) -> PersistenceListResult[PersistenceAuditEventRecord]:
        active_filters = filters or AuditPersistenceFilters()
        records = tuple(
            await self._repository.list_audit_events(
                entity_type=active_filters.entity_type,
                entity_id=active_filters.entity_id,
                action=active_filters.action,
                system_source=active_filters.system_source,
                actor_id=active_filters.actor_id,
                actor_type=active_filters.actor_type,
                workflow_name=active_filters.workflow_name,
                execution_id=active_filters.execution_id,
                runtime_id=active_filters.runtime_id,
                node_name=active_filters.node_name,
                start=active_filters.start,
                end=active_filters.end,
            )
        )
        return build_list_result(
            records,
            query=active_filters.to_common_query(),
        )
