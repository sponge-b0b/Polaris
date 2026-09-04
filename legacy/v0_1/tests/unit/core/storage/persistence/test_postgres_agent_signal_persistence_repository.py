from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.agent_signals import AgentSignalModel
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.repositories import (
    postgres_agent_signal_persistence_repository as signal_repositories,
)
from core.storage.persistence.serializers.agent_signal_persistence_serializer import (
    AgentSignalPersistenceSerializer,
)

PostgresAgentSignalPersistenceRepository = (
    signal_repositories.PostgresAgentSignalPersistenceRepository
)


class FakeScalarResult:
    def __init__(
        self,
        rows: Sequence[object],
    ) -> None:
        self._rows = list(rows)

    def all(
        self,
    ) -> list[object]:
        return self._rows


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
    ) -> FakeScalarResult:
        return FakeScalarResult(
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
async def test_persist_signal_uses_idempotent_upsert() -> None:
    session = FakeAsyncSession()
    repository = PostgresAgentSignalPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_signal(
        _signal_record(),
    )

    compiled = str(
        session.executed[0].compile(
            dialect=postgresql.dialect(),
        )
    )

    assert result.success is True
    assert result.records_persisted == 1
    assert session.commits == 1
    assert "ON CONFLICT" in compiled
    assert "signal_id" in compiled
    assert "llm_response" in compiled


@pytest.mark.asyncio
async def test_persist_signal_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(
        error=SQLAlchemyError(
            "database unavailable",
        )
    )
    repository = PostgresAgentSignalPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    result = await repository.persist_signal(
        _signal_record(),
    )

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_signal_round_trips_model_to_record() -> None:
    model = AgentSignalModel(
        **AgentSignalPersistenceSerializer.signal_values(
            _signal_record(),
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult(
            [model],
        )
    )
    repository = PostgresAgentSignalPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    record = await repository.get_signal(
        "agent_signal:exec-1:TechnicalAgent:technical",
    )

    assert record is not None
    assert record.agent_name == "TechnicalAgent"
    assert record.signals == {"trend": "bullish"}
    assert record.llm_response == "Full LLM response."


@pytest.mark.asyncio
async def test_list_signals_for_execution_returns_ordered_typed_records() -> None:
    model = AgentSignalModel(
        **AgentSignalPersistenceSerializer.signal_values(
            _signal_record(),
        )
    )
    session = FakeAsyncSession(
        result=FakeExecuteResult(
            [model],
        )
    )
    repository = PostgresAgentSignalPersistenceRepository(
        cast(
            AsyncSession,
            session,
        )
    )

    records = await repository.list_signals_for_execution(
        workflow_name="morning_report",
        execution_id="exec-1",
    )

    assert len(records) == 1
    assert records[0].signal_id == "agent_signal:exec-1:TechnicalAgent:technical"


def _signal_record() -> AgentSignalRecord:
    return AgentSignalRecord(
        signal_id="agent_signal:exec-1:TechnicalAgent:technical",
        agent_name="TechnicalAgent",
        agent_type="technical",
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical",
        symbol="SPY",
        universe=("SPY", "QQQ"),
        timestamp=datetime(2026, 5, 30, tzinfo=UTC),
        directional_score=0.6,
        confidence=0.82,
        regime="bullish",
        signals={"trend": "bullish"},
        risks={"drawdown": "moderate"},
        recommendations={"posture": "risk-on"},
        features={"rsi": 61.0},
        reasoning_text="Full technical reasoning.",
        llm_response="Full LLM response.",
        metadata={"source": "unit-test"},
    )
