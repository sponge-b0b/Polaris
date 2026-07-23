from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from application.persistence.export.json_persistence_export_service import (
    JsonPersistenceExportService,
    ReportHistoryExportRequest,
)
from core.storage.persistence.export import PersistenceExportRequest
from core.storage.persistence.lineage import JsonValue
from core.storage.persistence.query import (
    PersistenceCommonQuery,
    PersistenceLineageQuery,
    PersistenceListResult,
    PersistenceReadResult,
    PersistenceSymbolQuery,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ApiReadyRecord:
    record_id: str
    symbol: str
    generated_at: datetime
    confidence: Decimal


@dataclass(
    frozen=True,
    slots=True,
)
class ApiReadyReportBundle:
    report: ApiReadyRecord
    sections: tuple[ApiReadyRecord, ...] = ()
    artifacts: tuple[ApiReadyRecord, ...] = ()
    versions: tuple[ApiReadyRecord, ...] = ()
    publications: tuple[ApiReadyRecord, ...] = ()


class FakeApiReadyReportService:
    def __init__(
        self,
        bundle: ApiReadyReportBundle,
    ) -> None:
        self._bundle = bundle

    async def get_bundle(
        self,
        report_id: str,
    ) -> ApiReadyReportBundle | None:
        assert report_id == self._bundle.report.record_id
        return self._bundle


def test_list_result_preserves_typed_records_and_exposes_api_ready_metadata() -> None:
    record = _api_ready_record(
        record_id="recommendation-1",
    )
    query = PersistenceCommonQuery(
        lineage=PersistenceLineageQuery(
            workflow_name="morning_report",
            execution_id="exec-1",
        ),
        symbols=PersistenceSymbolQuery(
            symbol="aapl",
        ),
        metadata={
            "record_type": "recommendation",
            "status": "published",
        },
    )

    result = PersistenceListResult(
        records=(record,),
        total_count=1,
        query=query,
        metadata={
            "api_boundary": "future_fastapi_mapper",
        },
    )

    assert result.records == (record,)
    assert not isinstance(
        result.records[0],
        dict,
    )
    page_metadata = result.page_metadata()
    assert page_metadata["returned_count"] == 1
    assert page_metadata["query"] == {
        "lineage": {
            "workflow_name": "morning_report",
            "execution_id": "exec-1",
        },
        "source": {},
        "symbols": {
            "symbol": "AAPL",
        },
        "account": {},
        "time_range": {},
        "pagination": {
            "limit": 100,
            "offset": 0,
            "max_limit": 1000,
        },
        "sort": {
            "field_name": "timestamp",
            "direction": "desc",
        },
        "metadata": {
            "record_type": "recommendation",
            "status": "published",
        },
    }
    _assert_json_boundary_payload(
        cast(
            JsonValue,
            page_metadata,
        )
    )


def test_read_result_preserves_typed_record_and_exposes_api_ready_metadata() -> None:
    record = _api_ready_record(
        record_id="report-1",
    )
    result = PersistenceReadResult(
        record=record,
        metadata={
            "record_type": "report",
        },
    )

    assert result.found is True
    assert result.record is record
    assert not isinstance(
        result.record,
        dict,
    )
    assert result.metadata_dict() == {
        "found": True,
        "metadata": {
            "record_type": "report",
        },
    }
    _assert_json_boundary_payload(
        cast(
            JsonValue,
            result.metadata_dict(),
        )
    )


@pytest.mark.asyncio
async def test_json_export_result_is_api_response_ready_at_boundary() -> None:
    service = JsonPersistenceExportService()
    request = PersistenceExportRequest(
        domains=("recommendations",),
    )

    result = await service.export_records(
        request=request,
        records_by_domain={
            "recommendations": [
                _api_ready_record(
                    record_id="recommendation-1",
                )
            ],
        },
    )

    assert result.success is True
    assert result.payload is not None
    exported_records = result.payload.records_by_domain["recommendations"]
    assert exported_records[0] == {
        "record_id": "recommendation-1",
        "symbol": "AAPL",
        "generated_at": "2026-05-29T14:00:00+00:00",
        "confidence": "0.81",
    }
    _assert_json_boundary_payload(
        cast(
            JsonValue,
            result.as_dict(),
        )
    )


@pytest.mark.asyncio
async def test_report_history_export_result_is_api_response_ready_at_boundary() -> None:
    service = JsonPersistenceExportService()
    report = _api_ready_record(
        record_id="report-1",
    )
    section = _api_ready_record(
        record_id="section-1",
    )
    export_request = PersistenceExportRequest(
        domains=(
            "reports",
            "report_sections",
        ),
    )

    result = await service.export_report_history(
        ReportHistoryExportRequest(
            report_id="report-1",
            export_request=export_request,
        ),
        report_service=FakeApiReadyReportService(
            ApiReadyReportBundle(
                report=report,
                sections=(section,),
            )
        ),
    )

    assert result.success is True
    assert result.payload is not None
    assert result.export_result.domain_record_counts == {
        "reports": 1,
        "report_sections": 1,
    }
    _assert_json_boundary_payload(
        cast(
            JsonValue,
            result.as_dict(),
        )
    )


def test_persistence_api_readiness_does_not_add_fastapi_endpoints() -> None:
    searched_roots = (
        Path("application/persistence"),
        Path("core/storage/persistence"),
    )
    offenders: list[str] = []
    for root in searched_roots:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            source = path.read_text()
            if "fastapi" in source.lower():
                offenders.append(
                    str(
                        path,
                    )
                )

    assert offenders == []


def _api_ready_record(
    *,
    record_id: str,
) -> ApiReadyRecord:
    return ApiReadyRecord(
        record_id=record_id,
        symbol="AAPL",
        generated_at=datetime(
            2026,
            5,
            29,
            14,
            0,
            tzinfo=UTC,
        ),
        confidence=Decimal("0.81"),
    )


def _assert_json_boundary_payload(
    value: JsonValue,
) -> None:
    json.dumps(
        value,
        sort_keys=True,
    )
