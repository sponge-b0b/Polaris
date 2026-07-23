from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

import pytest

from application.persistence.export.json_persistence_export_service import (
    JsonPersistenceExportResult,
    JsonPersistenceExportService,
    ReportHistoryExportRequest,
)
from core.storage.persistence.export import (
    PersistenceExportDestination,
    PersistenceExportDestinationType,
    PersistenceExportFormat,
    PersistenceExportRequest,
)
from core.storage.persistence.lineage import (
    PersistenceLineageLinkRecord,
    PersistenceLineagePath,
    PersistenceLineagePathSegment,
    PersistenceLineageTraversalDirection,
    PersistenceLineageTraversalRequest,
    PersistenceLineageTraversalResult,
    PersistenceRecordIdentity,
)


class SampleRegime(StrEnum):
    BULLISH = "bullish"


@dataclass(
    frozen=True,
    slots=True,
)
class SampleNestedRecord:
    quality_score: Decimal
    tags: tuple[str, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class SampleCuratedRecord:
    record_id: str
    symbol: str
    observed_at: datetime
    regime: SampleRegime
    nested: SampleNestedRecord
    metadata: dict[str, object]


class RecordWithAsDict:
    def as_dict(
        self,
    ) -> dict[str, object]:
        return {
            "record_id": "recommendation-1",
            "generated_at": datetime(
                2026,
                5,
                29,
                14,
                30,
                tzinfo=UTC,
            ),
            "confidence": Decimal("0.82"),
            "lineage": {
                "execution_id": "exec-1",
            },
        }


class UnsupportedRecord:
    pass


@pytest.mark.asyncio
async def test_json_export_service_serializes_selected_typed_records_to_json_payload() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    service = JsonPersistenceExportService()
    request = PersistenceExportRequest(
        domains=(
            " Reports ",
            "recommendations",
        ),
        destination=PersistenceExportDestination(
            destination_type=PersistenceExportDestinationType.MEMORY,
        ),
    )
    record = SampleCuratedRecord(
        record_id="report-1",
        symbol="aapl",
        observed_at=datetime(
            2026,
            5,
            29,
            13,
            15,
            tzinfo=UTC,
        ),
        regime=SampleRegime.BULLISH,
        nested=SampleNestedRecord(
            quality_score=Decimal("0.97"),
            tags=(
                "curated",
                "morning-report",
            ),
        ),
        metadata={
            "uuid": UUID("12345678-1234-5678-1234-567812345678"),
            "scores": (
                Decimal("0.75"),
                Decimal("0.80"),
            ),
        },
    )

    result = await service.export_records(
        request=request,
        records_by_domain={
            "reports": [record],
            "recommendations": [],
            "telemetry": [UnsupportedRecord()],
        },
    )

    assert isinstance(
        result,
        JsonPersistenceExportResult,
    )
    assert result.success is True
    assert result.payload is not None
    assert result.export_result.records_exported == 1
    assert result.export_result.domain_record_counts == {
        "reports": 1,
        "recommendations": 0,
    }
    assert set(result.payload.records_by_domain) == {
        "reports",
        "recommendations",
    }

    report_payload = result.payload.records_by_domain["reports"][0]
    assert report_payload["record_id"] == "report-1"
    assert report_payload["symbol"] == "aapl"
    assert report_payload["observed_at"] == "2026-05-29T13:15:00+00:00"
    assert report_payload["regime"] == "bullish"
    assert report_payload["nested"] == {
        "quality_score": "0.97",
        "tags": (
            "curated",
            "morning-report",
        ),
    }
    assert report_payload["metadata"] == {
        "uuid": "12345678-1234-5678-1234-567812345678",
        "scores": (
            "0.75",
            "0.80",
        ),
    }


@pytest.mark.asyncio
async def test_json_export_service_uses_record_as_dict_at_boundary() -> None:
    service = JsonPersistenceExportService()
    request = PersistenceExportRequest(
        domains=("recommendations",),
    )

    result = await service.export_records(
        request=request,
        records_by_domain={
            "recommendations": [RecordWithAsDict()],
        },
    )

    assert result.success is True
    assert result.payload is not None
    payload = result.payload.records_by_domain["recommendations"][0]
    assert payload == {
        "record_id": "recommendation-1",
        "generated_at": "2026-05-29T14:30:00+00:00",
        "confidence": "0.82",
        "lineage": {
            "execution_id": "exec-1",
        },
    }


@pytest.mark.asyncio
async def test_json_export_service_rejects_unsupported_format_without_payload() -> None:
    service = JsonPersistenceExportService()
    request = PersistenceExportRequest(
        domains=("reports",),
        export_format=PersistenceExportFormat.CSV,
    )

    result = await service.export_records(
        request=request,
        records_by_domain={
            "reports": [],
        },
    )

    assert result.success is False
    assert result.payload is None
    assert result.export_result.records_exported == 0
    assert (
        result.export_result.error
        == "JsonPersistenceExportService only supports json exports."
    )


@pytest.mark.asyncio
async def test_json_export_service_returns_failure_for_unserializable_record() -> None:
    service = JsonPersistenceExportService()
    request = PersistenceExportRequest(
        domains=("reports",),
    )

    result = await service.export_records(
        request=request,
        records_by_domain={
            "reports": [UnsupportedRecord()],
        },
    )

    assert result.success is False
    assert result.payload is None
    assert result.export_result.records_exported == 0
    assert "dataclass instances or expose as_dict" in str(
        result.export_result.error,
    )


@dataclass(
    frozen=True,
    slots=True,
)
class SampleRecord:
    record_id: str
    record_type: str
    generated_at: datetime
    text: str


@dataclass(
    frozen=True,
    slots=True,
)
class SampleReportBundle:
    report: SampleRecord
    sections: tuple[SampleRecord, ...] = ()
    artifacts: tuple[SampleRecord, ...] = ()
    versions: tuple[SampleRecord, ...] = ()
    publications: tuple[SampleRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class SampleRecommendationBundle:
    recommendation: SampleRecord
    rationales: tuple[SampleRecord, ...] = ()
    outcomes: tuple[SampleRecord, ...] = ()
    trade_setups: tuple[SampleRecord, ...] = ()
    watchlist_items: tuple[SampleRecord, ...] = ()


class FakeReportHistoryReportService:
    def __init__(
        self,
        bundle: SampleReportBundle | None,
    ) -> None:
        self.bundle = bundle
        self.report_ids: list[str] = []

    async def get_bundle(
        self,
        report_id: str,
    ) -> SampleReportBundle | None:
        self.report_ids.append(
            report_id,
        )
        return self.bundle


class FakeReportHistoryLineageService:
    def __init__(
        self,
        result: PersistenceLineageTraversalResult,
    ) -> None:
        self.result = result
        self.root_record: PersistenceRecordIdentity | None = None
        self.max_depth: int | None = None
        self.max_edges: int | None = None
        self.relationship_types: tuple[str, ...] = ()

    async def trace_downstream_lineage(
        self,
        root_record: PersistenceRecordIdentity,
        *,
        max_depth: int = 3,
        max_edges: int = 250,
        relationship_types: tuple[str, ...] = (),
    ) -> PersistenceLineageTraversalResult:
        self.root_record = root_record
        self.max_depth = max_depth
        self.max_edges = max_edges
        self.relationship_types = relationship_types
        return self.result


class FakeRecommendationHistoryService:
    def __init__(
        self,
        bundle: SampleRecommendationBundle | None,
    ) -> None:
        self.bundle = bundle

    async def get_bundle(
        self,
        recommendation_id: str,
    ) -> SampleRecommendationBundle | None:
        assert recommendation_id == "recommendation-1"
        return self.bundle


class FakeAgentSignalHistoryService:
    async def get_signal(
        self,
        signal_id: str,
    ) -> SampleRecord | None:
        assert signal_id == "signal-1"
        return _sample_record(
            "signal-1",
            "agent_signal",
        )


class FakeAgentIntelligenceHistoryService:
    async def get_reasoning(
        self,
        reasoning_id: str,
    ) -> SampleRecord | None:
        assert reasoning_id == "reasoning-1"
        return _sample_record(
            "reasoning-1",
            "agent_reasoning",
        )

    async def get_recommendation(
        self,
        agent_recommendation_id: str,
    ) -> SampleRecord | None:
        assert agent_recommendation_id == "agent-recommendation-1"
        return _sample_record(
            "agent-recommendation-1",
            "agent_recommendation",
        )

    async def get_risk_assessment(
        self,
        risk_assessment_id: str,
    ) -> SampleRecord | None:
        assert risk_assessment_id == "risk-1"
        return _sample_record(
            "risk-1",
            "agent_risk_assessment",
        )


class FakeAttributionHistoryService:
    async def get_attribution(
        self,
        attribution_id: str,
    ) -> SampleRecord | None:
        assert attribution_id == "attribution-1"
        return _sample_record(
            "attribution-1",
            "attribution",
        )

    async def get_signal_attribution(
        self,
        signal_attribution_id: str,
    ) -> SampleRecord | None:
        assert signal_attribution_id == "signal-attribution-1"
        return _sample_record(
            "signal-attribution-1",
            "signal_attribution",
        )

    async def get_recommendation_attribution(
        self,
        recommendation_attribution_id: str,
    ) -> SampleRecord | None:
        assert recommendation_attribution_id == "recommendation-attribution-1"
        return _sample_record(
            "recommendation-attribution-1",
            "recommendation_attribution",
        )


@pytest.mark.asyncio
async def test_export_report_history_exports_linked_records_from_lineage() -> None:
    service = JsonPersistenceExportService()
    report_bundle = SampleReportBundle(
        report=_sample_record(
            "report-1",
            "report",
        ),
        sections=(
            _sample_record(
                "section-1",
                "report_section",
            ),
        ),
        versions=(
            _sample_record(
                "version-1",
                "report_version",
            ),
        ),
    )
    recommendation_bundle = SampleRecommendationBundle(
        recommendation=_sample_record(
            "recommendation-1",
            "recommendation",
        ),
        rationales=(
            _sample_record(
                "rationale-1",
                "recommendation_rationale",
            ),
        ),
    )
    lineage_result = _lineage_result(
        "report-1",
        (
            PersistenceRecordIdentity(
                record_type="recommendation",
                record_id="recommendation-1",
            ),
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id="signal-1",
            ),
            PersistenceRecordIdentity(
                record_type="agent_reasoning",
                record_id="reasoning-1",
            ),
            PersistenceRecordIdentity(
                record_type="recommendation_attribution",
                record_id="recommendation-attribution-1",
            ),
        ),
    )
    lineage_service = FakeReportHistoryLineageService(
        lineage_result,
    )
    export_request = PersistenceExportRequest(
        domains=(
            "reports",
            "report_sections",
            "report_versions",
            "recommendations",
            "recommendation_rationales",
            "agent_signals",
            "agent_reasoning",
            "recommendation_attributions",
            "lineage_paths",
        ),
    )

    result = await service.export_report_history(
        ReportHistoryExportRequest(
            report_id="report-1",
            export_request=export_request,
            max_depth=2,
            max_edges=10,
        ),
        report_service=FakeReportHistoryReportService(
            report_bundle,
        ),
        lineage_service=lineage_service,
        recommendation_service=FakeRecommendationHistoryService(
            recommendation_bundle,
        ),
        agent_signal_service=FakeAgentSignalHistoryService(),
        agent_intelligence_service=FakeAgentIntelligenceHistoryService(),
        attribution_service=FakeAttributionHistoryService(),
    )

    assert result.success is True
    assert result.payload is not None
    assert result.export_result.domain_record_counts == {
        "reports": 1,
        "report_sections": 1,
        "report_versions": 1,
        "recommendations": 1,
        "recommendation_rationales": 1,
        "agent_signals": 1,
        "agent_reasoning": 1,
        "recommendation_attributions": 1,
        "lineage_paths": 4,
    }
    assert lineage_service.root_record == PersistenceRecordIdentity(
        record_type="report",
        record_id="report-1",
    )
    assert lineage_service.max_depth == 2
    assert lineage_service.max_edges == 10
    assert result.payload.records_by_domain["recommendations"][0]["record_id"] == (
        "recommendation-1"
    )
    assert result.payload.records_by_domain["agent_signals"][0]["record_type"] == (
        "agent_signal"
    )


@pytest.mark.asyncio
async def test_export_report_history_without_lineage_exports_report_bundle_only() -> (
    None
):
    service = JsonPersistenceExportService()
    report_bundle = SampleReportBundle(
        report=_sample_record(
            "report-1",
            "report",
        ),
        artifacts=(
            _sample_record(
                "artifact-1",
                "report_artifact",
            ),
        ),
    )
    export_request = PersistenceExportRequest(
        domains=(
            "reports",
            "report_artifacts",
            "recommendations",
        ),
    )

    result = await service.export_report_history(
        ReportHistoryExportRequest(
            report_id="report-1",
            export_request=export_request,
        ),
        report_service=FakeReportHistoryReportService(
            report_bundle,
        ),
    )

    assert result.success is True
    assert result.payload is not None
    assert result.export_result.domain_record_counts == {
        "reports": 1,
        "report_artifacts": 1,
        "recommendations": 0,
    }


@pytest.mark.asyncio
async def test_export_report_history_returns_failure_when_report_is_missing() -> None:
    service = JsonPersistenceExportService()
    export_request = PersistenceExportRequest(
        domains=("reports",),
    )

    result = await service.export_report_history(
        ReportHistoryExportRequest(
            report_id="missing-report",
            export_request=export_request,
        ),
        report_service=FakeReportHistoryReportService(
            None,
        ),
    )

    assert result.success is False
    assert result.payload is None
    assert result.export_result.error == (
        "Report history export source not found: missing-report."
    )


def _sample_record(
    record_id: str,
    record_type: str,
) -> SampleRecord:
    return SampleRecord(
        record_id=record_id,
        record_type=record_type,
        generated_at=datetime(
            2026,
            5,
            29,
            15,
            45,
            tzinfo=UTC,
        ),
        text=f"Curated {record_type}",
    )


def _lineage_result(
    report_id: str,
    linked_records: tuple[PersistenceRecordIdentity, ...],
) -> PersistenceLineageTraversalResult:
    root_record = PersistenceRecordIdentity(
        record_type="report",
        record_id=report_id,
    )
    request = PersistenceLineageTraversalRequest(
        root_record=root_record,
        direction=PersistenceLineageTraversalDirection.DOWNSTREAM,
        max_depth=2,
        max_edges=10,
    )
    paths = tuple(
        _single_edge_path(
            root_record,
            linked_record,
        )
        for linked_record in linked_records
    )
    return PersistenceLineageTraversalResult(
        request=request,
        paths=paths,
        edges_considered=len(
            paths,
        ),
    )


def _single_edge_path(
    root_record: PersistenceRecordIdentity,
    target_record: PersistenceRecordIdentity,
) -> PersistenceLineagePath:
    link = PersistenceLineageLinkRecord(
        link_id=f"link:{root_record.record_id}:{target_record.record_id}",
        source_record=root_record,
        target_record=target_record,
        relationship_type="supports",
        created_at=datetime(
            2026,
            5,
            29,
            15,
            0,
            tzinfo=UTC,
        ),
    )
    return PersistenceLineagePath(
        root_record=root_record,
        direction=PersistenceLineageTraversalDirection.DOWNSTREAM,
        segments=(
            PersistenceLineagePathSegment(
                depth=1,
                from_record=root_record,
                to_record=target_record,
                link=link,
            ),
        ),
    )
