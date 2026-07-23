from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from typing import Any

import pytest

from core.storage.persistence.audit import (
    PersistenceAuditActor,
    PersistenceAuditEventRecord,
    PersistenceAuditEventResult,
    new_persistence_audit_event_id,
)
from core.storage.persistence.lineage import PersistenceLineage


def test_audit_actor_normalizes_and_serializes_source_context() -> None:
    actor = PersistenceAuditActor(
        system_source=" persistence-service ",
        actor_id=" user-1 ",
        actor_type=" human ",
    )

    assert actor.system_source == "persistence-service"
    assert actor.actor_id == "user-1"
    assert actor.actor_type == "human"
    assert actor.as_dict() == {
        "system_source": "persistence-service",
        "actor_id": "user-1",
        "actor_type": "human",
    }

    with pytest.raises(FrozenInstanceError):
        actor.system_source = "mutated"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"system_source": " "}, "system_source"),
    ],
)
def test_audit_actor_validates_required_source(
    kwargs: dict[str, Any],
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        PersistenceAuditActor(
            **kwargs,
        )


def test_audit_event_record_is_typed_normalized_and_boundary_serializable() -> None:
    timestamp = datetime(2026, 5, 31, 13, 45, tzinfo=UTC)
    event = PersistenceAuditEventRecord(
        audit_event_id=" audit-1 ",
        entity_type=" recommendation ",
        entity_id=" rec-1 ",
        action=" upsert ",
        timestamp=timestamp,
        actor=PersistenceAuditActor(
            system_source="recommendation-persistence-service",
            actor_id="user-1",
        ),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            node_name="recommendation_node",
        ),
        metadata={"reason": "curated write"},
    )

    assert event.audit_event_id == "audit-1"
    assert event.entity_type == "recommendation"
    assert event.entity_id == "rec-1"
    assert event.entity.record_type == "recommendation"
    assert event.entity.record_id == "rec-1"
    assert event.action == "upsert"
    assert event.system_source == "recommendation-persistence-service"
    assert event.actor_id == "user-1"
    assert event.actor_type is None
    assert event.as_dict() == {
        "audit_event_id": "audit-1",
        "entity_type": "recommendation",
        "entity_id": "rec-1",
        "action": "upsert",
        "timestamp": "2026-05-31T13:45:00+00:00",
        "actor": {
            "system_source": "recommendation-persistence-service",
            "actor_id": "user-1",
        },
        "lineage": {
            "workflow_name": "morning_report",
            "execution_id": "exec-1",
            "node_name": "recommendation_node",
        },
        "metadata": {"reason": "curated write"},
    }

    with pytest.raises(FrozenInstanceError):
        event.action = "delete"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"audit_event_id": " "}, "audit_event_id"),
        ({"entity_type": " "}, "entity_type"),
        ({"entity_id": " "}, "entity_id"),
        ({"action": " "}, "action"),
    ],
)
def test_audit_event_record_validates_required_fields(
    kwargs: dict[str, Any],
    field_name: str,
) -> None:
    values: dict[str, Any] = {
        "audit_event_id": "audit-1",
        "entity_type": "report",
        "entity_id": "report-1",
        "action": "create",
        "timestamp": datetime(2026, 5, 31, tzinfo=UTC),
        "actor": PersistenceAuditActor(
            system_source="report-service",
        ),
    }
    values.update(
        kwargs,
    )

    with pytest.raises(ValueError, match=field_name):
        PersistenceAuditEventRecord(
            **values,
        )


def test_audit_event_result_validates_success_and_failure_state() -> None:
    success = PersistenceAuditEventResult(
        success=True,
        audit_event_id=" audit-1 ",
    )
    failure = PersistenceAuditEventResult(
        success=False,
        error="database unavailable",
    )

    assert success.audit_event_id == "audit-1"
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="audit_event_id"):
        PersistenceAuditEventResult(
            success=True,
        )
    with pytest.raises(ValueError, match="error"):
        PersistenceAuditEventResult(
            success=False,
        )


def test_audit_event_id_helper_creates_append_only_unique_ids() -> None:
    first = new_persistence_audit_event_id()
    second = new_persistence_audit_event_id()

    assert first.startswith("persistence_audit_event:")
    assert second.startswith("persistence_audit_event:")
    assert first != second
