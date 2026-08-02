from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.reports import (
    ReportClaimEvidenceLinkModel,
    ReportModel,
    ReportPublicationModel,
    ReportVersionModel,
)
from core.storage.persistence.claim_evidence_links import (
    ClaimEvidenceObservabilityError,
)
from core.storage.persistence.reports import (
    ReportArtifactRecord,
    ReportClaimEvidenceLinkRecord,
    ReportPersistenceBundle,
    ReportPublicationRecord,
    ReportRecord,
    ReportSectionRecord,
    ReportVersionRecord,
)
from core.storage.persistence.repositories.postgres_report_persistence_repository import (  # noqa: E501 - canonical module path
    PostgresReportPersistenceRepository,
)
from core.telemetry.events import TelemetryEvent
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.authority import RiskTier


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
    ) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None

        return self._rows[0]

    def scalars(
        self,
    ) -> FakeExecuteResult:
        return self

    def all(
        self,
    ) -> Sequence[object]:
        return tuple(
            self._rows,
        )


class _FailingMetricObservabilityManager(ObservabilityManager):
    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> None:
        del name, value, tags, attributes
        raise RuntimeError("claim-evidence metrics backend unavailable")


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
        execute_errors: dict[int, SQLAlchemyError] | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.execute_errors = execute_errors or {}
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

        execute_index = len(self.executed)
        if execute_index in self.execute_errors:
            raise self.execute_errors[execute_index]
        if self.error is not None:
            raise self.error

        return self.result

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_report_bundle_uses_idempotent_upserts() -> None:
    session = FakeAsyncSession()
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_report(
        _report(),
        sections=(_section(),),
        artifacts=(_artifact(),),
    )

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert "report_id" in compiled[0]
    assert "section_id" in compiled[1]
    assert "artifact_id" in compiled[2]


@pytest.mark.asyncio
async def test_persist_report_bundle_includes_versions_and_publications() -> None:
    session = FakeAsyncSession()
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_report_bundle(
        ReportPersistenceBundle(
            report=_report(),
            sections=(_section(),),
            artifacts=(_artifact(),),
            versions=(_version(),),
            publications=(_publication(),),
        )
    )

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.records_persisted == 5
    assert session.commits == 1
    assert len(session.executed) == 5
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert "report_id" in compiled[0]
    assert "section_id" in compiled[1]
    assert "artifact_id" in compiled[2]
    assert "version_id" in compiled[3]
    assert "publication_id" in compiled[4]


@pytest.mark.asyncio
async def test_persist_report_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(
        error=SQLAlchemyError(
            "database unavailable",
        )
    )
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_report(
        _report(),
    )

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_report_round_trips_model_to_record() -> None:
    model = ReportModel(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body="# Full report\n",
        structured_payload={"symbol": "SPY"},
        metadata_payload={"source": "test"},
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult(
            [model],
        )
    )
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    record = await repository.get_report(
        "morning_report:exec-1",
    )

    assert record is not None
    assert record.report_type == "morning_report"
    assert record.markdown_body == "# Full report\n"
    assert record.structured_payload == {"symbol": "SPY"}


@pytest.mark.asyncio
async def test_get_version_round_trips_model_to_record() -> None:
    model = ReportVersionModel(
        version_id="morning_report:exec-1:version:1",
        report_id="morning_report:exec-1",
        version_number=1,
        created_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        title="Morning Report",
        markdown_body="# Full version\n",
        structured_payload={"symbol": "SPY"},
        metadata_payload={"source": "test"},
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult(
            [model],
        )
    )
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    record = await repository.get_version(
        "morning_report:exec-1:version:1",
    )

    assert record is not None
    assert record.version_number == 1
    assert record.markdown_body == "# Full version\n"
    assert record.structured_payload == {"symbol": "SPY"}


@pytest.mark.asyncio
async def test_list_publications_round_trips_models_to_records() -> None:
    model = ReportPublicationModel(
        publication_id="morning_report:exec-1:publication:markdown",
        report_id="morning_report:exec-1",
        version_id="morning_report:exec-1:version:1",
        publication_target="markdown_archive",
        publication_status="published",
        requested_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        published_at=datetime(2026, 5, 30, 14, 5, tzinfo=UTC),
        artifact_uri="/reports/morning_report.md",
        metadata_payload={"source": "test"},
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult(
            [model],
        )
    )
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    records = await repository.list_publications(
        report_id="morning_report:exec-1",
        version_id="morning_report:exec-1:version:1",
        publication_target="markdown_archive",
        publication_status="published",
    )

    assert len(records) == 1
    assert records[0].publication_target == "markdown_archive"
    assert records[0].publication_status == "published"
    assert records[0].artifact_uri == "/reports/morning_report.md"


@pytest.mark.asyncio
async def test_persist_report_bundle_includes_claim_evidence_links() -> None:
    session = FakeAsyncSession()
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_report_bundle(
        ReportPersistenceBundle(
            report=_report(),
            claim_evidence_links=(_claim_evidence_link(),),
        )
    )

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.records_persisted == 2
    assert len(session.executed) == 2
    assert "ON CONFLICT (link_id)" in compiled[1]
    assert "report_claim_evidence_links" in compiled[1]


@pytest.mark.asyncio
async def test_persist_report_claim_evidence_links_records_success_observability() -> (
    None
):
    observability_manager, sink = _observability()
    session = FakeAsyncSession()
    repository = PostgresReportPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    result = await repository.persist_report_bundle(
        ReportPersistenceBundle(
            report=_report(),
            claim_evidence_links=(_claim_evidence_link(),),
        )
    )

    assert result.success is True
    event = _datastore_event(sink)
    assert event.success is True
    assert event.event_type == "storage.postgres.operation"
    assert event.duration_seconds is not None
    assert event.attributes["operation"] == "report_claim_evidence_link_write"
    assert event.attributes["operation_kind"] == "datastore_operation"
    assert event.attributes["database_system"] == "postgresql"
    assert event.attributes["report_id"] == "morning_report:exec-1"
    assert event.payload["records_persisted"] == 1
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.report_claim_evidence_link.operations.total" in metric_names
    )
    assert (
        "storage.postgres.report_claim_evidence_link.duration_seconds" in metric_names
    )


@pytest.mark.asyncio
async def test_persist_report_claim_links_survives_observability_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeAsyncSession()
    repository = PostgresReportPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=_FailingMetricObservabilityManager(),
    )

    with caplog.at_level(
        logging.ERROR,
        logger="core.storage.persistence.claim_evidence_links",
    ):
        result = await repository.persist_report_bundle(
            ReportPersistenceBundle(
                report=_report(),
                claim_evidence_links=(_claim_evidence_link(),),
            )
        )

    assert result.success is True
    assert result.records_persisted == 2
    assert session.commits == 1
    failure_logs = [
        record
        for record in caplog.records
        if record.message == "Claim-evidence PostgreSQL observability recording failed."
    ]
    assert failure_logs
    failure = failure_logs[0]
    assert failure.exc_info is not None
    exc_type, exc, _traceback = failure.exc_info
    assert exc_type is ClaimEvidenceObservabilityError
    assert exc is not None
    assert isinstance(exc.__cause__, RuntimeError)


@pytest.mark.asyncio
async def test_persist_report_claim_evidence_links_logs_and_records_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observability_manager, sink = _observability()
    session = FakeAsyncSession(
        execute_errors={2: SQLAlchemyError("database unavailable")},
    )
    repository = PostgresReportPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    with caplog.at_level(logging.ERROR):
        result = await repository.persist_report_bundle(
            ReportPersistenceBundle(
                report=_report(),
                claim_evidence_links=(_claim_evidence_link(),),
            )
        )

    assert result.success is False
    assert session.rollbacks == 1
    event = _datastore_event(sink)
    assert event.success is False
    assert event.error_count == 1
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "SQLAlchemyError"
    assert "database unavailable" in event.exception_details.stack_trace
    assert event.attributes["operation"] == "report_claim_evidence_link_write"
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.report_claim_evidence_link.operations.failed" in metric_names
    )
    failure_logs = [
        record
        for record in caplog.records
        if record.message == "Report PostgreSQL claim-evidence link write failed."
    ]
    assert failure_logs
    assert failure_logs[0].exc_info is not None
    failure_context = vars(failure_logs[0])
    assert failure_context["report_id"] == "morning_report:exec-1"
    assert failure_context["operation"] == "report_claim_evidence_link_write"


@pytest.mark.asyncio
async def test_list_report_claim_evidence_links_returns_typed_records() -> None:
    model = ReportClaimEvidenceLinkModel(
        link_id="morning_report:exec-1:claim_evidence:claim-1:packet-1:claim-a",
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier="enhanced",
        material=True,
        supporting_evidence_ids=["evidence-1"],
        reconstruction_reference_ids=["reconstruction-1"],
        uncertainty_ids=["uncertainty-1"],
        limitation_ids=["limitation-1"],
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult(
            [model],
        )
    )
    repository = PostgresReportPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    records = await repository.list_claim_evidence_links(
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        packet_id="packet-1",
        claim_target_id="claim-1",
    )

    assert len(records) == 1
    assert records[0].risk_tier is RiskTier.ENHANCED
    assert records[0].supporting_evidence_ids == ("evidence-1",)
    assert records[0].reconstruction_reference_ids == ("reconstruction-1",)


@pytest.mark.asyncio
async def test_list_report_claim_evidence_links_records_success_observability() -> None:
    model = ReportClaimEvidenceLinkModel(
        link_id="morning_report:exec-1:claim_evidence:claim-1:packet-1:claim-a",
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier="enhanced",
        material=True,
        supporting_evidence_ids=["evidence-1"],
        reconstruction_reference_ids=["reconstruction-1"],
        uncertainty_ids=["uncertainty-1"],
        limitation_ids=["limitation-1"],
    )
    observability_manager, sink = _observability()
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresReportPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    records = await repository.list_claim_evidence_links(
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        packet_id="packet-1",
        claim_target_id="claim-1",
    )

    assert len(records) == 1
    event = _datastore_event(sink)
    assert event.success is True
    assert event.duration_seconds is not None
    assert event.attributes["operation"] == "report_claim_evidence_link_read"
    assert event.attributes["operation_kind"] == "datastore_operation"
    assert event.attributes["report_id"] == "morning_report:exec-1"
    assert event.payload["records_returned"] == 1
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.report_claim_evidence_link.operations.total" in metric_names
    )
    assert (
        "storage.postgres.report_claim_evidence_link.duration_seconds" in metric_names
    )


@pytest.mark.asyncio
async def test_list_report_claim_evidence_links_logs_and_records_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observability_manager, sink = _observability()
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresReportPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    with caplog.at_level(logging.ERROR), pytest.raises(SQLAlchemyError):
        await repository.list_claim_evidence_links(
            report_id="morning_report:exec-1",
            section_id="morning_report:exec-1:section:macro",
            packet_id="packet-1",
            claim_target_id="claim-1",
        )

    event = _datastore_event(sink)
    assert event.success is False
    assert event.error_count == 1
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "SQLAlchemyError"
    assert "database unavailable" in event.exception_details.stack_trace
    assert event.attributes["operation"] == "report_claim_evidence_link_read"
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.report_claim_evidence_link.operations.failed" in metric_names
    )
    failure_logs = [
        record
        for record in caplog.records
        if record.message == "Report PostgreSQL claim-evidence link read failed."
    ]
    assert failure_logs
    assert failure_logs[0].exc_info is not None
    failure_context = vars(failure_logs[0])
    assert failure_context["report_id"] == "morning_report:exec-1"
    assert failure_context["operation"] == "report_claim_evidence_link_read"


def _observability() -> tuple[ObservabilityManager, InMemoryTelemetrySink]:
    sink = InMemoryTelemetrySink()
    observability_manager = ObservabilityManager()
    observability_manager.add_sink(sink)
    return observability_manager, sink


def _datastore_event(sink: InMemoryTelemetrySink) -> TelemetryEvent:
    events = [
        event
        for event in sink.events
        if event.event_type == "storage.postgres.operation"
    ]
    assert len(events) == 1
    return events[0]


def _metric_names(observability_manager: ObservabilityManager) -> set[str]:
    return {point.name for point in observability_manager.metrics_store.points()}


def _report() -> ReportRecord:
    return ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=UTC),
        markdown_body="# Full report\n",
        structured_payload={"symbol": "SPY"},
    )


def _section() -> ReportSectionRecord:
    return ReportSectionRecord(
        section_id="morning_report:exec-1:section:macro",
        report_id="morning_report:exec-1",
        section_key="macro",
        title="Macro",
        display_order=1,
        summary="Full macro summary",
    )


def _artifact() -> ReportArtifactRecord:
    return ReportArtifactRecord(
        artifact_id="morning_report:exec-1:artifact:1",
        report_id="morning_report:exec-1",
        artifact_type="markdown",
        artifact_uri="/tmp/report.md",
    )


def _version() -> ReportVersionRecord:
    return ReportVersionRecord(
        version_id="morning_report:exec-1:version:1",
        report_id="morning_report:exec-1",
        version_number=1,
        created_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        markdown_body="# Full report version\n",
        structured_payload={"symbol": "SPY"},
    )


def _publication() -> ReportPublicationRecord:
    return ReportPublicationRecord(
        publication_id="morning_report:exec-1:publication:markdown",
        report_id="morning_report:exec-1",
        version_id="morning_report:exec-1:version:1",
        publication_target="markdown_archive",
        publication_status="published",
        requested_at=datetime(2026, 5, 30, 14, tzinfo=UTC),
        published_at=datetime(2026, 5, 30, 14, 5, tzinfo=UTC),
        artifact_uri="/reports/morning_report.md",
    )


def _claim_evidence_link() -> ReportClaimEvidenceLinkRecord:
    return ReportClaimEvidenceLinkRecord(
        link_id="morning_report:exec-1:claim_evidence:claim-1:packet-1:claim-a",
        report_id="morning_report:exec-1",
        section_id="morning_report:exec-1:section:macro",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier=RiskTier.ENHANCED,
        material=True,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("reconstruction-1",),
    )
