from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.reports import ReportModel
from core.database.models.reports import ReportPublicationModel
from core.database.models.reports import ReportVersionModel
from core.storage.persistence.reports import ReportArtifactRecord
from core.storage.persistence.reports import ReportPersistenceBundle
from core.storage.persistence.reports import ReportPublicationRecord
from core.storage.persistence.reports import ReportRecord
from core.storage.persistence.reports import ReportSectionRecord
from core.storage.persistence.reports import ReportVersionRecord
from core.storage.persistence.repositories.postgres_report_persistence_repository import (
    PostgresReportPersistenceRepository,
)


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


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

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
        generated_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
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
        created_at=datetime(2026, 5, 30, 14, tzinfo=timezone.utc),
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
        requested_at=datetime(2026, 5, 30, 14, tzinfo=timezone.utc),
        published_at=datetime(2026, 5, 30, 14, 5, tzinfo=timezone.utc),
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


def _report() -> ReportRecord:
    return ReportRecord(
        report_id="morning_report:exec-1",
        report_type="morning_report",
        title="Morning Report",
        generated_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
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
        created_at=datetime(2026, 5, 30, 14, tzinfo=timezone.utc),
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
        requested_at=datetime(2026, 5, 30, 14, tzinfo=timezone.utc),
        published_at=datetime(2026, 5, 30, 14, 5, tzinfo=timezone.utc),
        artifact_uri="/reports/morning_report.md",
    )
