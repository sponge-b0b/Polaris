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

from core.database.models.audit import PersistenceAuditEventModel
from core.storage.persistence.audit import PersistenceAuditActor
from core.storage.persistence.audit import PersistenceAuditEventRecord
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.repositories.postgres_audit_persistence_repository import (
    PostgresPersistenceAuditEventRepository,
)
from core.storage.persistence.serializers.audit_persistence_serializer import (
    PersistenceAuditEventSerializer,
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
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        if self.error is not None:
            raise self.error
        return self.result

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_audit_event_uses_append_only_insert() -> None:
    session = FakeAsyncSession()
    repository = PostgresPersistenceAuditEventRepository(cast(AsyncSession, session))

    result = await repository.persist_audit_event(
        _event(),
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert result.audit_event_id == "audit-event-1"
    assert result.records_persisted == 1
    assert session.commits == 1
    assert session.rollbacks == 0
    assert len(session.executed) == 1
    assert "INSERT INTO persistence_audit_events" in compiled
    assert "ON CONFLICT" not in compiled


@pytest.mark.asyncio
async def test_persist_audit_event_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresPersistenceAuditEventRepository(cast(AsyncSession, session))

    result = await repository.persist_audit_event(
        _event(),
    )

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_audit_event_round_trips_model_to_record() -> None:
    model = PersistenceAuditEventModel(
        **PersistenceAuditEventSerializer.event_values(
            _event(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresPersistenceAuditEventRepository(cast(AsyncSession, session))

    record = await repository.get_audit_event("audit-event-1")

    assert record is not None
    assert record.audit_event_id == "audit-event-1"
    assert record.entity_type == "recommendation"
    assert record.actor.system_source == "recommendation-service"


@pytest.mark.asyncio
async def test_list_audit_events_returns_typed_records_and_filters_query() -> None:
    model = PersistenceAuditEventModel(
        **PersistenceAuditEventSerializer.event_values(
            _event(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresPersistenceAuditEventRepository(cast(AsyncSession, session))
    start = datetime(2026, 5, 31, 13, 0, tzinfo=timezone.utc)
    end = datetime(2026, 5, 31, 15, 0, tzinfo=timezone.utc)

    records = await repository.list_audit_events(
        entity_type="recommendation",
        entity_id="rec-1",
        action="upsert",
        system_source="recommendation-service",
        actor_id="user-1",
        actor_type="human",
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="recommendation_node",
        start=start,
        end=end,
    )

    assert len(records) == 1
    assert records[0].audit_event_id == "audit-event-1"
    assert records[0].lineage.execution_id == "exec-1"

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    for expected_fragment in (
        "entity_type",
        "entity_id",
        "action",
        "system_source",
        "actor_id",
        "actor_type",
        "workflow_name",
        "execution_id",
        "runtime_id",
        "node_name",
        "timestamp >=",
        "timestamp <=",
        "ORDER BY",
    ):
        assert expected_fragment in compiled


def _event() -> PersistenceAuditEventRecord:
    return PersistenceAuditEventRecord(
        audit_event_id="audit-event-1",
        entity_type="recommendation",
        entity_id="rec-1",
        action="upsert",
        timestamp=datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc),
        actor=PersistenceAuditActor(
            system_source="recommendation-service",
            actor_id="user-1",
            actor_type="human",
        ),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="recommendation_node",
        ),
        metadata={"reason": "curated write"},
    )
