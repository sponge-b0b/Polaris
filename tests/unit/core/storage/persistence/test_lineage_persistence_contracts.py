from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceLineageLinkRecord
from core.storage.persistence.lineage import PersistenceLineageLinkResult
from core.storage.persistence.lineage import PersistenceRecordContext
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.lineage import PersistenceSourceReference
from core.storage.persistence.lineage import build_source_reference
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.lineage import new_persistence_lineage_link_id
from core.storage.persistence.lineage import require_non_empty_identifier


def test_persistence_lineage_is_typed_normalized_and_immutable() -> None:
    lineage = PersistenceLineage(
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        runtime_id=" runtime-1 ",
        node_name=" technical_node ",
    )

    assert lineage.workflow_name == "morning_report"
    assert lineage.execution_id == "exec-1"
    assert lineage.runtime_id == "runtime-1"
    assert lineage.node_name == "technical_node"
    assert lineage.as_dict() == {
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "runtime_id": "runtime-1",
        "node_name": "technical_node",
    }

    with pytest.raises(FrozenInstanceError):
        lineage.workflow_name = "changed"  # type: ignore[misc]


def test_persistence_lineage_omits_empty_optional_fields() -> None:
    lineage = PersistenceLineage(
        workflow_name=" ",
        execution_id=None,
        runtime_id="runtime-1",
        node_name="\t",
    )

    assert lineage.workflow_name is None
    assert lineage.execution_id is None
    assert lineage.runtime_id == "runtime-1"
    assert lineage.node_name is None
    assert lineage.as_dict() == {
        "runtime_id": "runtime-1",
    }


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"source_type": " ", "source_id": "record-1"}, "source_type"),
        ({"source_type": "report", "source_id": ""}, "source_id"),
    ],
)
def test_source_reference_requires_canonical_source_identifiers(
    kwargs: dict[str, str],
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        PersistenceSourceReference(**kwargs)


def test_source_reference_is_normalized_and_serializable() -> None:
    source = build_source_reference(
        source_type=" report ",
        source_id=" morning_report:exec-1 ",
        source_table=" reports ",
    )

    assert source.source_type == "report"
    assert source.source_id == "morning_report:exec-1"
    assert source.source_table == "reports"
    assert source.as_dict() == {
        "source_type": "report",
        "source_id": "morning_report:exec-1",
        "source_table": "reports",
    }


def test_record_identity_requires_record_type_and_id() -> None:
    identity = PersistenceRecordIdentity(
        record_type=" recommendation ",
        record_id=" rec-1 ",
    )

    assert identity.record_type == "recommendation"
    assert identity.record_id == "rec-1"
    assert identity.as_dict() == {
        "record_type": "recommendation",
        "record_id": "rec-1",
    }

    with pytest.raises(ValueError, match="record_type"):
        PersistenceRecordIdentity(
            record_type=" ",
            record_id="rec-1",
        )

    with pytest.raises(ValueError, match="record_id"):
        PersistenceRecordIdentity(
            record_type="recommendation",
            record_id="",
        )


def test_record_context_validates_timestamp_order() -> None:
    created_at = datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc)
    updated_at = created_at + timedelta(minutes=5)
    context = PersistenceRecordContext(
        identity=PersistenceRecordIdentity(
            record_type="signal",
            record_id="signal-1",
        ),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        source=PersistenceSourceReference(
            source_type="workflow",
            source_id="exec-1",
        ),
        created_at=created_at,
        updated_at=updated_at,
    )

    assert context.identity.record_id == "signal-1"
    assert context.lineage.execution_id == "exec-1"
    assert context.source is not None
    assert context.source.source_type == "workflow"

    with pytest.raises(ValueError, match="updated_at"):
        PersistenceRecordContext(
            identity=PersistenceRecordIdentity(
                record_type="signal",
                record_id="signal-1",
            ),
            created_at=created_at,
            updated_at=created_at - timedelta(seconds=1),
        )


def test_validation_helpers_normalize_optional_and_required_values() -> None:
    assert clean_optional_identifier("  node-a  ", "node_name") == "node-a"
    assert clean_optional_identifier(" ", "node_name") is None
    assert require_non_empty_identifier(" source-1 ", "source_id") == "source-1"

    with pytest.raises(ValueError, match="source_id"):
        require_non_empty_identifier(None, "source_id")


def test_lineage_link_record_preserves_cross_record_relationship() -> None:
    source_record = PersistenceRecordIdentity(
        record_type="report",
        record_id="morning_report:exec-1",
    )
    target_record = PersistenceRecordIdentity(
        record_type="recommendation",
        record_id="rec-1",
    )
    link_id = new_persistence_lineage_link_id(
        source_record=source_record,
        target_record=target_record,
        relationship_type="produced",
    )
    link = PersistenceLineageLinkRecord(
        link_id=link_id,
        source_record=source_record,
        target_record=target_record,
        relationship_type=" produced ",
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="recommendation_node",
        ),
        created_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        metadata={"reason": "report recommendation"},
    )

    assert link.link_id == (
        "persistence_lineage_link:"
        "report:morning_report:exec-1:produced:recommendation:rec-1"
    )
    assert link.relationship_type == "produced"
    assert link.lineage.workflow_name == "morning_report"
    assert link.metadata == {"reason": "report recommendation"}


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"link_id": " ", "relationship_type": "produced"}, "link_id"),
        ({"link_id": "link-1", "relationship_type": ""}, "relationship_type"),
    ],
)
def test_lineage_link_record_validates_required_fields(
    kwargs: dict[str, str],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "link_id": "link-1",
        "source_record": PersistenceRecordIdentity(
            record_type="report",
            record_id="report-1",
        ),
        "target_record": PersistenceRecordIdentity(
            record_type="signal",
            record_id="signal-1",
        ),
        "relationship_type": "uses",
        "created_at": datetime(2026, 5, 30, tzinfo=timezone.utc),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        PersistenceLineageLinkRecord(**values)  # type: ignore[arg-type]


def test_lineage_link_record_rejects_self_links() -> None:
    identity = PersistenceRecordIdentity(
        record_type="signal",
        record_id="signal-1",
    )

    with pytest.raises(ValueError, match="same record"):
        PersistenceLineageLinkRecord(
            link_id="link-1",
            source_record=identity,
            target_record=identity,
            relationship_type="references",
            created_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        )


def test_lineage_link_result_validates_state() -> None:
    success = PersistenceLineageLinkResult.succeeded(
        link_id="link-1",
    )
    failure = PersistenceLineageLinkResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.link_id == "link-1"
    assert failure.success is False

    with pytest.raises(ValueError, match="error"):
        PersistenceLineageLinkResult.failed(
            " ",
        )

    with pytest.raises(ValueError, match="successful"):
        PersistenceLineageLinkResult(
            success=True,
            link_id="link-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="link_id"):
        PersistenceLineageLinkResult(
            success=True,
        )
