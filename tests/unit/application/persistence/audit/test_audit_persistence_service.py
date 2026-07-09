from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.audit import AuditPersistenceFilters
from application.persistence.audit import AuditPersistenceService
from core.storage.persistence.audit import PersistenceAuditActor
from core.storage.persistence.audit import PersistenceAuditEventRecord
from core.storage.persistence.audit import PersistenceAuditEventResult
from core.storage.persistence.lineage import PersistenceLineage


@pytest.mark.asyncio
async def test_persist_audit_event_delegates_typed_append_only_record() -> None:
    event = _event()
    repository = FakeAuditRepository(events=())
    service = AuditPersistenceService(repository)

    result = await service.persist_audit_event(
        event,
    )

    assert result.success is True
    assert result.audit_event_id == "audit-event-1"
    assert result.records_persisted == 1
    assert repository.persisted == (event,)


@pytest.mark.asyncio
async def test_get_audit_event_returns_typed_event() -> None:
    event = _event()
    service = AuditPersistenceService(
        FakeAuditRepository(
            events=(event,),
        )
    )

    result = await service.get_audit_event(
        "audit-event-1",
    )

    assert result == event


@pytest.mark.asyncio
async def test_list_audit_events_preserves_sequence_api_and_result_envelope() -> None:
    event = _event()
    repository = FakeAuditRepository(
        events=(event,),
    )
    service = AuditPersistenceService(repository)
    filters = AuditPersistenceFilters(
        entity_type=" recommendation ",
        entity_id=" rec-1 ",
        action=" upsert ",
        system_source=" recommendation-service ",
        actor_id=" user-1 ",
        actor_type=" human ",
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        runtime_id=" runtime-1 ",
        node_name=" recommendation_node ",
        start=datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc),
        end=datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc),
    )

    records = await service.list_audit_events(
        filters,
    )
    result = await service.list_audit_events_result(
        filters,
    )

    assert records == (event,)
    assert result.records == (event,)
    assert result.total_count == 1
    assert result.query is not None
    assert result.query.lineage.workflow_name == "morning_report"
    assert result.query.lineage.execution_id == "exec-1"
    assert result.query.time_range.start == datetime(
        2026,
        5,
        31,
        13,
        0,
        tzinfo=timezone.utc,
    )
    assert result.query.metadata["entity_type"] == "recommendation"
    assert result.query.metadata["action"] == "upsert"
    assert repository.last_filters == {
        "entity_type": "recommendation",
        "entity_id": "rec-1",
        "action": "upsert",
        "system_source": "recommendation-service",
        "actor_id": "user-1",
        "actor_type": "human",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "runtime_id": "runtime-1",
        "node_name": "recommendation_node",
        "start": datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc),
        "end": datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc),
    }


def test_audit_filters_validate_time_window() -> None:
    with pytest.raises(ValueError, match="start"):
        AuditPersistenceFilters(
            start=datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc),
            end=datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc),
        )


class FakeAuditRepository:
    def __init__(
        self,
        *,
        events: Sequence[PersistenceAuditEventRecord],
    ) -> None:
        self._events = tuple(events)
        self.persisted: tuple[PersistenceAuditEventRecord, ...] = ()
        self.last_filters: dict[str, object | None] | None = None

    async def persist_audit_event(
        self,
        event: PersistenceAuditEventRecord,
    ) -> PersistenceAuditEventResult:
        self.persisted = (*self.persisted, event)
        return PersistenceAuditEventResult.succeeded(
            audit_event_id=event.audit_event_id,
        )

    async def get_audit_event(
        self,
        audit_event_id: str,
    ) -> PersistenceAuditEventRecord | None:
        for event in self._events:
            if event.audit_event_id == audit_event_id:
                return event
        return None

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
    ) -> Sequence[PersistenceAuditEventRecord]:
        self.last_filters = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "system_source": system_source,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "workflow_name": workflow_name,
            "execution_id": execution_id,
            "runtime_id": runtime_id,
            "node_name": node_name,
            "start": start,
            "end": end,
        }
        return self._events


def _event() -> PersistenceAuditEventRecord:
    return PersistenceAuditEventRecord(
        audit_event_id="audit-event-1",
        entity_type="recommendation",
        entity_id="rec-1",
        action="upsert",
        timestamp=datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc),
        actor=PersistenceAuditActor(
            system_source="recommendation-service",
            actor_id="user-1",
            actor_type="human",
        ),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="recommendation_node",
        ),
        metadata={"reason": "curated write"},
    )
