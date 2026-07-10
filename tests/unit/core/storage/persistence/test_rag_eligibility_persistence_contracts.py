from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.rag import RagSourceEligibilityRecord
from core.storage.persistence.rag import RagSourceEligibilityResult
from core.storage.persistence.rag import new_rag_source_eligibility_id


def test_rag_source_eligibility_record_is_metadata_only_typed_and_immutable() -> None:
    record = _eligibility_record()

    assert record.eligibility_id == (
        "rag_source_eligibility:reports:morning_report:report-1"
    )
    assert record.source_table == "reports"
    assert record.source_id == "report-1"
    assert record.source_type == "morning_report"
    assert record.source_key == (
        "reports",
        "morning_report",
        "report-1",
    )
    assert record.eligible is True
    assert record.reason == "Curated human-readable report."
    assert record.quality_score == 0.91
    assert record.metadata == {"reviewer": "default_rules"}

    with pytest.raises(FrozenInstanceError):
        record.eligible = False  # type: ignore[misc]


def test_rag_source_eligibility_record_serializes_boundary_dict() -> None:
    record = _eligibility_record()

    payload = record.as_dict()

    assert payload == {
        "eligibility_id": "rag_source_eligibility:reports:morning_report:report-1",
        "source_table": "reports",
        "source_id": "report-1",
        "source_type": "morning_report",
        "eligible": True,
        "reason": "Curated human-readable report.",
        "quality_score": 0.91,
        "reviewed_timestamp": "2026-05-31T14:00:00+00:00",
        "metadata": {"reviewer": "default_rules"},
    }


def test_rag_source_eligibility_record_does_not_create_rag_ingestion_payloads() -> None:
    payload = _eligibility_record().as_dict()

    assert "document_id" not in payload
    assert "chunk_id" not in payload
    assert "job_id" not in payload
    assert "embedding" not in payload
    assert "vector_store" not in payload
    assert "graph_store" not in payload


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"eligibility_id": " "}, "eligibility_id"),
        ({"source_table": ""}, "source_table"),
        ({"source_id": " "}, "source_id"),
        ({"source_type": ""}, "source_type"),
        ({"reason": " "}, "reason"),
        ({"quality_score": -0.01}, "quality_score"),
        ({"quality_score": 1.01}, "quality_score"),
    ],
)
def test_rag_source_eligibility_record_validates_required_fields_and_quality(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "eligibility_id": "rag_source_eligibility:reports:morning_report:report-1",
        "source_table": "reports",
        "source_id": "report-1",
        "source_type": "morning_report",
        "eligible": True,
        "reason": "Curated human-readable report.",
        "quality_score": 0.91,
        "reviewed_timestamp": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        RagSourceEligibilityRecord(**values)  # type: ignore[arg-type]


def test_rag_source_eligibility_result_validates_success_and_failure_state() -> None:
    success = RagSourceEligibilityResult.succeeded(
        eligibility_id="rag_source_eligibility:reports:morning_report:report-1",
    )
    failure = RagSourceEligibilityResult.failed("database unavailable")

    assert success.success is True
    assert success.records_persisted == 1
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="eligibility_id"):
        RagSourceEligibilityResult(success=True)

    with pytest.raises(ValueError, match="records_persisted"):
        RagSourceEligibilityResult(
            success=True,
            eligibility_id="eligibility-1",
            records_persisted=-1,
        )

    with pytest.raises(ValueError, match="error"):
        RagSourceEligibilityResult.failed(" ")

    with pytest.raises(ValueError, match="successful"):
        RagSourceEligibilityResult(
            success=True,
            eligibility_id="eligibility-1",
            error="unexpected",
        )


def test_rag_source_eligibility_id_helper_is_stable_for_postgres_sources() -> None:
    eligibility_id = new_rag_source_eligibility_id(
        source_table=" reports ",
        source_type=" morning_report ",
        source_id=" report-1 ",
    )
    repeat_eligibility_id = new_rag_source_eligibility_id(
        source_table="reports",
        source_type="morning_report",
        source_id="report-1",
    )

    assert eligibility_id == repeat_eligibility_id
    assert eligibility_id == "rag_source_eligibility:reports:morning_report:report-1"

    with pytest.raises(ValueError, match="source_id"):
        new_rag_source_eligibility_id(
            source_table="reports",
            source_type="morning_report",
            source_id=" ",
        )


def _eligibility_record() -> RagSourceEligibilityRecord:
    return RagSourceEligibilityRecord(
        eligibility_id=" rag_source_eligibility:reports:morning_report:report-1 ",
        source_table=" reports ",
        source_id=" report-1 ",
        source_type=" morning_report ",
        eligible=True,
        reason=" Curated human-readable report. ",
        quality_score=0.91,
        reviewed_timestamp=_timestamp(),
        metadata={"reviewer": "default_rules"},
    )


def _timestamp() -> datetime:
    return datetime(
        2026,
        5,
        31,
        14,
        0,
        tzinfo=timezone.utc,
    )
