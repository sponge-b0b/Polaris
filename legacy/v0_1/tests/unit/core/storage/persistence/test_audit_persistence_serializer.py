from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.audit import PersistenceAuditEventModel
from core.storage.persistence.audit import (
    PersistenceAuditActor,
    PersistenceAuditEventRecord,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.serializers.audit_persistence_serializer import (
    PersistenceAuditEventSerializer,
)


def test_audit_serializer_flattens_typed_event_record() -> None:
    event = _event()

    values = PersistenceAuditEventSerializer.event_values(
        event,
    )

    assert values["audit_event_id"] == "audit-event-1"
    assert values["entity_type"] == "recommendation"
    assert values["entity_id"] == "rec-1"
    assert values["action"] == "upsert"
    assert values["system_source"] == "recommendation-service"
    assert values["actor_id"] == "user-1"
    assert values["actor_type"] == "human"
    assert values["timestamp"] == datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["runtime_id"] == "runtime-1"
    assert values["node_name"] == "recommendation_node"
    assert values["metadata_payload"] == {"reason": "curated write"}


def test_audit_serializer_round_trips_model_to_record() -> None:
    model = PersistenceAuditEventModel(
        **PersistenceAuditEventSerializer.event_values(
            _event(),
        )
    )

    record = PersistenceAuditEventSerializer.event_from_model(
        model,
    )

    assert record.audit_event_id == "audit-event-1"
    assert record.entity_type == "recommendation"
    assert record.entity_id == "rec-1"
    assert record.action == "upsert"
    assert record.actor.system_source == "recommendation-service"
    assert record.actor_id == "user-1"
    assert record.actor_type == "human"
    assert record.lineage.workflow_name == "morning_report"
    assert record.lineage.execution_id == "exec-1"
    assert record.metadata == {"reason": "curated write"}


def _event() -> PersistenceAuditEventRecord:
    return PersistenceAuditEventRecord(
        audit_event_id="audit-event-1",
        entity_type="recommendation",
        entity_id="rec-1",
        action="upsert",
        timestamp=datetime(2026, 5, 31, 14, 0, tzinfo=UTC),
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
