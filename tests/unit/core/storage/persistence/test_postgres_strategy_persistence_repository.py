from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.strategy import StrategyHypothesisEvaluationModel
from core.database.models.strategy import StrategyHypothesisModel
from core.database.models.strategy import StrategySynthesisDecisionModel
from core.storage.persistence.repositories.postgres_strategy_persistence_repository import (
    PostgresStrategyPersistenceRepository,
)
from core.storage.persistence.strategy import StrategyPersistenceBundle
from core.storage.persistence.serializers.strategy_persistence_serializer import (
    StrategyPersistenceSerializer,
)

from tests.unit.core.storage.persistence.strategy_fixtures import strategy_evaluation
from tests.unit.core.storage.persistence.strategy_fixtures import strategy_hypothesis
from tests.unit.core.storage.persistence.strategy_fixtures import (
    strategy_synthesis_decision,
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
        results: Sequence[FakeExecuteResult] | None = None,
        error: SQLAlchemyError | None = None,
    ) -> None:
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
        return FakeExecuteResult()

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_strategy_bundle_uses_idempotent_upserts() -> None:
    session = FakeAsyncSession()
    repository = PostgresStrategyPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_strategy_bundle(_bundle())

    compiled = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.executed
    ]

    assert result.success is True
    assert result.decision_id == "decision-1"
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert "ON CONFLICT (hypothesis_id)" in compiled[0]
    assert "ON CONFLICT (decision_id)" in compiled[1]
    assert "ON CONFLICT (evaluation_id)" in compiled[2]


@pytest.mark.asyncio
async def test_persist_strategy_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresStrategyPersistenceRepository(cast(AsyncSession, session))

    result = await repository.persist_strategy_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_hypothesis_round_trips_model_to_record() -> None:
    model = StrategyHypothesisModel(
        **StrategyPersistenceSerializer.hypothesis_values(strategy_hypothesis())
    )
    session = FakeAsyncSession(results=(FakeExecuteResult([model]),))
    repository = PostgresStrategyPersistenceRepository(cast(AsyncSession, session))

    record = await repository.get_hypothesis("hypothesis-1")

    assert record is not None
    assert record.hypothesis_id == "hypothesis-1"
    assert record.symbol == "SPY"
    assert record.lineage.execution_id == "exec-1"
    assert record.supporting_evidence[0]["source"] == "technical"


@pytest.mark.asyncio
async def test_list_decisions_returns_typed_records() -> None:
    model = StrategySynthesisDecisionModel(
        **StrategyPersistenceSerializer.decision_values(strategy_synthesis_decision())
    )
    session = FakeAsyncSession(results=(FakeExecuteResult([model]),))
    repository = PostgresStrategyPersistenceRepository(cast(AsyncSession, session))

    records = await repository.list_decisions(
        symbol="spy",
        selection_status="selected",
        execution_id="exec-1",
        evidence_fingerprint="fingerprint-1",
    )

    assert len(records) == 1
    assert records[0].symbol == "SPY"
    assert records[0].selection_status == "selected"
    assert records[0].confidence == 0.764567890123


@pytest.mark.asyncio
async def test_get_decision_bundle_returns_decision_evaluations_and_hypotheses() -> (
    None
):
    decision_model = StrategySynthesisDecisionModel(
        **StrategyPersistenceSerializer.decision_values(strategy_synthesis_decision())
    )
    evaluation_model = StrategyHypothesisEvaluationModel(
        **StrategyPersistenceSerializer.evaluation_values(strategy_evaluation())
    )
    hypothesis_model = StrategyHypothesisModel(
        **StrategyPersistenceSerializer.hypothesis_values(strategy_hypothesis())
    )
    session = FakeAsyncSession(
        results=(
            FakeExecuteResult([decision_model]),
            FakeExecuteResult([evaluation_model]),
            FakeExecuteResult([hypothesis_model]),
        )
    )
    repository = PostgresStrategyPersistenceRepository(cast(AsyncSession, session))

    bundle = await repository.get_decision_bundle("decision-1")

    assert bundle is not None
    assert bundle.decision.decision_id == "decision-1"
    assert bundle.evaluations[0].evaluation_id == "decision-1:evaluation:bull"
    assert bundle.hypotheses[0].hypothesis_id == "hypothesis-1"


def _bundle() -> StrategyPersistenceBundle:
    return StrategyPersistenceBundle(
        decision=strategy_synthesis_decision(),
        hypotheses=(strategy_hypothesis(),),
        evaluations=(strategy_evaluation(),),
    )
