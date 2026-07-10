from __future__ import annotations

from datetime import datetime
from datetime import timezone

from core.database.models.lineage import PersistenceLineageLinkModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceLineageLinkRecord
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.serializers.lineage_persistence_serializer import (
    PersistenceLineageLinkSerializer,
)


def test_lineage_serializer_flattens_typed_link_record() -> None:
    link = _link()

    values = PersistenceLineageLinkSerializer.link_values(
        link,
    )

    assert values["link_id"] == "lineage-link-1"
    assert values["source_record_type"] == "report"
    assert values["source_record_id"] == "morning_report:exec-1"
    assert values["relationship_type"] == "produced"
    assert values["target_record_type"] == "recommendation"
    assert values["target_record_id"] == "rec-1"
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"confidence": 0.9}


def test_lineage_serializer_round_trips_model_to_record() -> None:
    model = PersistenceLineageLinkModel(
        **PersistenceLineageLinkSerializer.link_values(
            _link(),
        )
    )

    record = PersistenceLineageLinkSerializer.link_from_model(
        model,
    )

    assert record.link_id == "lineage-link-1"
    assert record.source_record.record_type == "report"
    assert record.target_record.record_id == "rec-1"
    assert record.relationship_type == "produced"
    assert record.lineage.node_name == "recommendation_node"
    assert record.metadata == {"confidence": 0.9}


def _link() -> PersistenceLineageLinkRecord:
    return PersistenceLineageLinkRecord(
        link_id="lineage-link-1",
        source_record=PersistenceRecordIdentity(
            record_type="report",
            record_id="morning_report:exec-1",
        ),
        target_record=PersistenceRecordIdentity(
            record_type="recommendation",
            record_id="rec-1",
        ),
        relationship_type="produced",
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="recommendation_node",
        ),
        created_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        metadata={"confidence": 0.9},
    )
