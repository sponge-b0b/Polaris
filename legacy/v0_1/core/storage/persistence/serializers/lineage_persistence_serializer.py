from __future__ import annotations

from typing import Any, cast

from core.database.models.lineage import PersistenceLineageLinkModel
from core.storage.persistence.lineage.lineage_persistence_models import (
    JsonObject,
    PersistenceLineage,
    PersistenceLineageLinkRecord,
    PersistenceRecordIdentity,
)


class PersistenceLineageLinkSerializer:
    """
    Serializer between typed lineage-link records and SQLAlchemy models.

    JSON dictionaries are introduced here because this module is the database
    persistence boundary. Runtime/application layers should work with typed
    lineage records and only serialize when crossing into Postgres.
    """

    @staticmethod
    def link_values(
        record: PersistenceLineageLinkRecord,
    ) -> dict[str, Any]:
        return {
            "link_id": record.link_id,
            "source_record_type": record.source_record.record_type,
            "source_record_id": record.source_record.record_id,
            "relationship_type": record.relationship_type,
            "target_record_type": record.target_record.record_type,
            "target_record_id": record.target_record.record_id,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def link_from_model(
        model: PersistenceLineageLinkModel,
    ) -> PersistenceLineageLinkRecord:
        return PersistenceLineageLinkRecord(
            link_id=model.link_id,
            source_record=PersistenceRecordIdentity(
                record_type=model.source_record_type,
                record_id=model.source_record_id,
            ),
            target_record=PersistenceRecordIdentity(
                record_type=model.target_record_type,
                record_id=model.target_record_id,
            ),
            relationship_type=model.relationship_type,
            lineage=PersistenceLineage(
                workflow_name=model.workflow_name,
                execution_id=model.execution_id,
                runtime_id=model.runtime_id,
                node_name=model.node_name,
            ),
            created_at=model.created_at,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )
