from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.audit import PersistenceAuditEventModel
from core.storage.persistence.audit import PersistenceAuditActor
from core.storage.persistence.audit import PersistenceAuditEventRecord
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage


class PersistenceAuditEventSerializer:
    """
    Serializer between typed audit event records and SQLAlchemy models.

    JSON dictionaries are introduced here because this module is the database
    persistence boundary. Application layers should work with typed audit
    records and serialize only when crossing into Postgres.
    """

    @staticmethod
    def event_values(
        record: PersistenceAuditEventRecord,
    ) -> dict[str, Any]:
        return {
            "audit_event_id": record.audit_event_id,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "action": record.action,
            "system_source": record.system_source,
            "actor_id": record.actor_id,
            "actor_type": record.actor_type,
            "timestamp": record.timestamp,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def event_from_model(
        model: PersistenceAuditEventModel,
    ) -> PersistenceAuditEventRecord:
        return PersistenceAuditEventRecord(
            audit_event_id=model.audit_event_id,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            action=model.action,
            timestamp=model.timestamp,
            actor=PersistenceAuditActor(
                system_source=model.system_source,
                actor_id=model.actor_id,
                actor_type=model.actor_type,
            ),
            lineage=PersistenceLineage(
                workflow_name=model.workflow_name,
                execution_id=model.execution_id,
                runtime_id=model.runtime_id,
                node_name=model.node_name,
            ),
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )
