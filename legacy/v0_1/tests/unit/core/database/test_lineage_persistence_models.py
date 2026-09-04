from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.lineage import PersistenceLineageLinkModel


def test_lineage_link_model_is_imported_into_base_metadata() -> None:
    assert "persistence_lineage_links" in Base.metadata.tables


def test_lineage_link_model_persists_generic_cross_record_relationships() -> None:
    columns = PersistenceLineageLinkModel.__table__.c
    primary_keys = {
        column.name for column in PersistenceLineageLinkModel.__table__.primary_key
    }

    assert primary_keys == {"link_id"}
    assert columns.source_record_type.nullable is False
    assert columns.source_record_id.nullable is False
    assert columns.relationship_type.nullable is False
    assert columns.target_record_type.nullable is False
    assert columns.target_record_id.nullable is False
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.node_name.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_lineage_link_model_uses_jsonb_at_persistence_boundary() -> None:
    assert isinstance(
        PersistenceLineageLinkModel.__table__.c.metadata.type,
        JSONB,
    )


def test_lineage_link_model_indexes_query_paths() -> None:
    table = cast(Table, PersistenceLineageLinkModel.__table__)
    index_names = {index.name for index in table.indexes}

    assert "idx_persistence_lineage_links_source" in index_names
    assert "idx_persistence_lineage_links_target" in index_names
    assert "idx_persistence_lineage_links_relationship" in index_names
    assert "idx_persistence_lineage_links_workflow_execution" in index_names
