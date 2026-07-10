from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.audit.audit_persistence_models import (
    PersistenceAuditEventRecord,
)
from core.storage.persistence.audit.audit_persistence_models import (
    PersistenceAuditEventResult,
)


class PersistenceAuditEventRepository(Protocol):
    """
    Async repository contract for append-only persistence audit events.
    """

    async def persist_audit_event(
        self,
        event: PersistenceAuditEventRecord,
    ) -> PersistenceAuditEventResult: ...

    async def get_audit_event(
        self,
        audit_event_id: str,
    ) -> PersistenceAuditEventRecord | None: ...

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
    ) -> Sequence[PersistenceAuditEventRecord]: ...
