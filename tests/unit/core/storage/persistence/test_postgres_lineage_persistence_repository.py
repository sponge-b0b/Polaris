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

from core.database.models.lineage import PersistenceLineageLinkModel
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceLineageLinkRecord
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.lineage import new_persistence_lineage_link_id
from core.storage.persistence.repositories.postgres_lineage_persistence_repository import (
    PostgresPersistenceLineageLinkRepository,
)
from core.storage.persistence.serializers.lineage_persistence_serializer import (
    PersistenceLineageLinkSerializer,
)


class FakeScalarResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(self, rows: Sequence[object] | None = None) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(self) -> object | None:
        if not self._rows:
            return None
        return self._rows[0]

    def scalars(self) -> FakeScalarResult:
        return FakeScalarResult(self._rows)


class FakeAsyncSession:
    def __init__(
        self,
        result: FakeExecuteResult | None = None,
        error: SQLAlchemyError | None = None,
        results: Sequence[FakeExecuteResult] | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.results = list(results or [])
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if self.error is not None:
            raise self.error
        if self.results:
            return self.results.pop(0)
        return self.result

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_lineage_link_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    result = await repository.persist_lineage_link(
        _link(),
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert result.records_persisted == 1
    assert session.commits == 1
    assert len(session.executed) == 1
    assert "ON CONFLICT" in compiled
    assert "link_id" in compiled


@pytest.mark.asyncio
async def test_persist_lineage_link_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    result = await repository.persist_lineage_link(
        _link(),
    )

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_lineage_link_round_trips_model_to_record() -> None:
    model = PersistenceLineageLinkModel(
        **PersistenceLineageLinkSerializer.link_values(
            _link(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    record = await repository.get_lineage_link("lineage-link-1")

    assert record is not None
    assert record.source_record.record_type == "report"
    assert record.target_record.record_id == "rec-1"
    assert record.relationship_type == "produced"


@pytest.mark.asyncio
async def test_list_links_for_source_returns_typed_records() -> None:
    model = PersistenceLineageLinkModel(
        **PersistenceLineageLinkSerializer.link_values(
            _link(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    records = await repository.list_links_for_source(
        PersistenceRecordIdentity(
            record_type="report",
            record_id="morning_report:exec-1",
        )
    )

    assert len(records) == 1
    assert records[0].target_record.record_type == "recommendation"


@pytest.mark.asyncio
async def test_list_links_for_target_returns_typed_records() -> None:
    model = PersistenceLineageLinkModel(
        **PersistenceLineageLinkSerializer.link_values(
            _link(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    records = await repository.list_links_for_target(
        PersistenceRecordIdentity(
            record_type="recommendation",
            record_id="rec-1",
        )
    )

    assert len(records) == 1
    assert records[0].source_record.record_id == "morning_report:exec-1"


@pytest.mark.asyncio
async def test_traverse_downstream_lineage_returns_bounded_typed_paths() -> None:
    report = _identity(
        "report",
        "morning_report:exec-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [
                    _model(
                        _link_between(
                            report,
                            recommendation,
                            "produced",
                        )
                    )
                ]
            ),
            FakeExecuteResult(
                [
                    _model(
                        _link_between(
                            recommendation,
                            signal,
                            "uses",
                        )
                    )
                ]
            ),
        )
    )
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    result = await repository.traverse_downstream_lineage(
        report,
        max_depth=2,
        max_edges=5,
        relationship_types=(
            "produced",
            "uses",
        ),
    )

    assert result.truncated is False
    assert result.edges_considered == 2
    assert result.path_count == 2
    assert result.paths[0].terminal_record == recommendation
    assert result.paths[1].terminal_record == signal
    assert result.visited_records == (
        report,
        recommendation,
        signal,
    )
    assert len(session.executed) == 2

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "source_record_type" in compiled
    assert "relationship_type" in compiled
    assert "ORDER BY" in compiled
    assert "LIMIT" in compiled


@pytest.mark.asyncio
async def test_traverse_upstream_lineage_returns_reverse_paths() -> None:
    report = _identity(
        "report",
        "morning_report:exec-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [
                    _model(
                        _link_between(
                            recommendation,
                            signal,
                            "uses",
                        )
                    )
                ]
            ),
            FakeExecuteResult(
                [
                    _model(
                        _link_between(
                            report,
                            recommendation,
                            "produced",
                        )
                    )
                ]
            ),
        )
    )
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    result = await repository.traverse_upstream_lineage(
        signal,
        max_depth=2,
        max_edges=5,
    )

    assert result.path_count == 2
    assert result.paths[0].terminal_record == recommendation
    assert result.paths[1].terminal_record == report
    assert result.visited_records == (
        signal,
        recommendation,
        report,
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "target_record_type" in compiled


@pytest.mark.asyncio
async def test_traverse_lineage_respects_edge_limit_and_marks_truncated() -> None:
    report = _identity(
        "report",
        "morning_report:exec-1",
    )
    recommendation = _identity(
        "recommendation",
        "rec-1",
    )
    signal = _identity(
        "signal",
        "signal-1",
    )
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult(
                [
                    _model(
                        _link_between(
                            report,
                            recommendation,
                            "produced",
                        )
                    ),
                    _model(
                        _link_between(
                            report,
                            signal,
                            "uses",
                        )
                    ),
                ]
            ),
        )
    )
    repository = PostgresPersistenceLineageLinkRepository(cast(AsyncSession, session))

    result = await repository.traverse_downstream_lineage(
        report,
        max_depth=2,
        max_edges=1,
    )

    assert result.truncated is True
    assert result.edges_considered == 1
    assert result.path_count == 1
    assert result.paths[0].terminal_record == recommendation


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


def _identity(
    record_type: str,
    record_id: str,
) -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type=record_type,
        record_id=record_id,
    )


def _link_between(
    source_record: PersistenceRecordIdentity,
    target_record: PersistenceRecordIdentity,
    relationship_type: str,
) -> PersistenceLineageLinkRecord:
    return PersistenceLineageLinkRecord(
        link_id=new_persistence_lineage_link_id(
            source_record=source_record,
            target_record=target_record,
            relationship_type=relationship_type,
        ),
        source_record=source_record,
        target_record=target_record,
        relationship_type=relationship_type,
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="lineage_node",
        ),
        created_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
    )


def _model(
    link: PersistenceLineageLinkRecord,
) -> PersistenceLineageLinkModel:
    return PersistenceLineageLinkModel(
        **PersistenceLineageLinkSerializer.link_values(
            link,
        )
    )
