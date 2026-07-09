from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.audit import PersistenceAuditEventModel


def test_audit_event_model_is_imported_into_base_metadata() -> None:
    assert "persistence_audit_events" in Base.metadata.tables


def test_audit_event_model_persists_append_only_entity_action_actor_lineage() -> None:
    columns = PersistenceAuditEventModel.__table__.c
    primary_keys = {
        column.name for column in PersistenceAuditEventModel.__table__.primary_key
    }

    assert primary_keys == {"audit_event_id"}
    assert columns.entity_type.nullable is False
    assert columns.entity_id.nullable is False
    assert columns.action.nullable is False
    assert columns.system_source.nullable is False
    assert columns.actor_id.nullable is True
    assert columns.actor_type.nullable is True
    assert columns.timestamp.nullable is False
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_audit_event_model_uses_jsonb_at_persistence_boundary() -> None:
    assert isinstance(
        PersistenceAuditEventModel.__table__.c.metadata.type,
        JSONB,
    )


def test_audit_event_model_indexes_entity_action_timestamp_and_lineage() -> None:
    table = cast(Table, PersistenceAuditEventModel.__table__)
    index_names = {index.name for index in table.indexes}

    assert "idx_persistence_audit_events_entity" in index_names
    assert "idx_persistence_audit_events_action_timestamp" in index_names
    assert "idx_persistence_audit_events_entity_action_timestamp" in index_names
    assert "idx_persistence_audit_events_workflow_execution" in index_names
    assert "idx_persistence_audit_events_runtime_node" in index_names
