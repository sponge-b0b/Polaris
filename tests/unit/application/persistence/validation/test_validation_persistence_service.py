from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone

import pytest

from application.persistence.validation import ValidationPersistenceService
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.validation import PersistenceExpectedLineage
from core.storage.persistence.validation import PersistenceExternalSourceValidationSpec
from core.storage.persistence.validation import PersistenceRecordValidationTarget
from core.storage.persistence.validation import PersistenceValidationStatus


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeCuratedRecord:
    generated_at: datetime
    confidence: float
    lineage: PersistenceLineage = field(default_factory=PersistenceLineage)
    source: str | None = None
    external_id: str | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class RepresentativeManualRecord:
    title: str = "manual research note"


@pytest.mark.asyncio
async def test_validation_service_coordinates_checks_for_valid_curated_record() -> None:
    service = ValidationPersistenceService()
    record = RepresentativeCuratedRecord(
        generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        confidence=0.82,
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        source="fmp",
        external_id="article-1",
    )

    result = await service.validate_record_object(
        record_type="news_article",
        record_id="article-1",
        record=record,
        expected_lineage=PersistenceExpectedLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        require_lineage=True,
        required_timestamp_field_names=("generated_at",),
        now=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0
    assert result.metadata == {"validator": "persistence_validation_service"}


@pytest.mark.asyncio
async def test_validation_service_returns_typed_issues_without_mutating_record() -> (
    None
):
    service = ValidationPersistenceService()
    record = RepresentativeCuratedRecord(
        generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        confidence=1.4,
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        source="fmp",
        external_id=None,
    )

    result = await service.validate_record_object(
        record_type="news_article",
        record_id="article-1",
        record=record,
        expected_lineage=PersistenceExpectedLineage(
            workflow_name="morning_report",
            execution_id="exec-2",
        ),
        now=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
    )

    assert result.status == PersistenceValidationStatus.FAILED
    assert result.is_valid is False
    assert [issue.field_name for issue in result.issues] == [
        "confidence",
        "lineage.execution_id",
        "dedupe_key",
    ]
    assert record.confidence == 1.4
    assert record.lineage.execution_id == "exec-1"


@pytest.mark.asyncio
async def test_validation_service_warns_for_manual_records_created_outside_workflows() -> (
    None
):
    service = ValidationPersistenceService()

    result = await service.validate_record_object(
        record_type="manual_research_note",
        record_id="note-1",
        record=RepresentativeManualRecord(),
    )

    assert result.status == PersistenceValidationStatus.WARNING
    assert result.is_valid is True
    assert result.issues[0].field_name == "lineage"


@pytest.mark.asyncio
async def test_validation_service_batches_representative_records() -> None:
    service = ValidationPersistenceService()
    valid = PersistenceRecordValidationTarget(
        identity=PersistenceRecordIdentity(
            record_type="news_article",
            record_id="article-1",
        ),
        record=RepresentativeCuratedRecord(
            generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
            confidence=0.82,
            lineage=PersistenceLineage(
                workflow_name="morning_report",
                execution_id="exec-1",
            ),
            source="fmp",
            external_id="article-1",
        ),
    )
    invalid = PersistenceRecordValidationTarget(
        identity=PersistenceRecordIdentity(
            record_type="news_article",
            record_id="article-2",
        ),
        record=RepresentativeCuratedRecord(
            generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
            confidence=-0.1,
            lineage=PersistenceLineage(
                workflow_name="morning_report",
                execution_id="exec-1",
            ),
            source="fmp",
            external_id="article-2",
        ),
    )

    batch = await service.validate_records(
        (
            valid,
            invalid,
        ),
        expected_lineage=PersistenceExpectedLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        required_timestamp_field_names=("generated_at",),
        now=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
    )

    assert batch.status == PersistenceValidationStatus.FAILED
    assert batch.record_count == 2
    assert batch.issue_count == 1
    assert batch.results[0].status == PersistenceValidationStatus.PASSED
    assert batch.results[1].status == PersistenceValidationStatus.FAILED
    assert batch.metadata == {"validator": "persistence_validation_service"}


@pytest.mark.asyncio
async def test_validation_service_accepts_custom_source_specs() -> None:
    service = ValidationPersistenceService()
    record = RepresentativeCuratedRecord(
        generated_at=datetime(2026, 5, 30, 13, 0, tzinfo=timezone.utc),
        confidence=0.82,
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        source="internal-research",
    )

    result = await service.validate_record_object(
        record_type="internal_note",
        record_id="note-1",
        record=record,
        expected_lineage=PersistenceExpectedLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        source_spec=PersistenceExternalSourceValidationSpec(
            dedupe_key_field_names=("source",),
        ),
        now=datetime(2026, 5, 30, 14, 0, tzinfo=timezone.utc),
    )

    assert result.status == PersistenceValidationStatus.PASSED
    assert result.issue_count == 0
