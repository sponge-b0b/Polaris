from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.recommendations import (
    RecommendationOutcomeRecord,
    RecommendationPersistenceBundle,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
)
from core.storage.persistence.repositories.postgres_recommendation_persistence_repository import (  # noqa: E501
    PostgresRecommendationPersistenceRepository,
)
from core.storage.persistence.serializers.recommendation_persistence_serializer import (
    RecommendationPersistenceSerializer,
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
async def test_persist_recommendation_bundle_uses_idempotent_upserts() -> None:
    session = FakeAsyncSession()
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    result = await repository.persist_recommendation_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.recommendation_id == "rec-1"
    assert result.records_persisted == 5
    assert session.commits == 1
    assert len(session.executed) == 5
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert "recommendation_id" in compiled[0]
    assert "rationale_id" in compiled[1]
    assert "outcome_id" in compiled[2]
    assert "setup_id" in compiled[3]
    assert "watchlist_item_id" in compiled[4]


@pytest.mark.asyncio
async def test_recommendation_idempotency_review_covers_parent_and_children() -> None:
    session = FakeAsyncSession()
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    result = await repository.persist_recommendation_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert len(compiled) == 5
    assert all("ON CONFLICT" in statement for statement in compiled)
    assert all("DO UPDATE" in statement for statement in compiled)
    assert all("DELETE" not in statement for statement in compiled)
    assert "ON CONFLICT (recommendation_id)" in compiled[0]
    assert "ON CONFLICT (rationale_id)" in compiled[1]
    assert "ON CONFLICT (outcome_id)" in compiled[2]
    assert "ON CONFLICT (setup_id)" in compiled[3]
    assert "ON CONFLICT (watchlist_item_id)" in compiled[4]


@pytest.mark.asyncio
async def test_persist_recommendation_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    result = await repository.persist_recommendation_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_recommendation_round_trips_model_to_record() -> None:
    model = RecommendationModel(
        **RecommendationPersistenceSerializer.recommendation_values(
            _recommendation(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    record = await repository.get_recommendation("rec-1")

    assert record is not None
    assert record.recommendation_id == "rec-1"
    assert record.symbol == "AAPL"
    assert record.lineage.execution_id == "exec-1"


@pytest.mark.asyncio
async def test_list_recommendations_returns_typed_records() -> None:
    model = RecommendationModel(
        **RecommendationPersistenceSerializer.recommendation_values(
            _recommendation(),
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    records = await repository.list_recommendations(
        symbol="aapl",
        status="active",
        execution_id="exec-1",
    )

    assert len(records) == 1
    assert records[0].symbol == "AAPL"
    assert records[0].status == "active"


@pytest.mark.asyncio
async def test_list_child_records_returns_typed_records() -> None:
    rationale_model = RecommendationRationaleModel(
        **RecommendationPersistenceSerializer.rationale_values(
            _rationale(),
        )
    )
    outcome_model = RecommendationOutcomeModel(
        **RecommendationPersistenceSerializer.outcome_values(
            _outcome(),
        )
    )
    setup_model = TradeSetupModel(
        **RecommendationPersistenceSerializer.trade_setup_values(
            _trade_setup(),
        )
    )
    watchlist_model = WatchlistItemModel(
        **RecommendationPersistenceSerializer.watchlist_item_values(
            _watchlist_item(),
        )
    )

    rationales = await PostgresRecommendationPersistenceRepository(
        cast(
            AsyncSession, FakeAsyncSession(result=FakeExecuteResult([rationale_model]))
        )
    ).list_rationales("rec-1")
    outcomes = await PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([outcome_model])))
    ).list_outcomes("rec-1")
    setups = await PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([setup_model])))
    ).list_trade_setups(recommendation_id="rec-1", symbol="aapl")
    watchlist_items = await PostgresRecommendationPersistenceRepository(
        cast(
            AsyncSession, FakeAsyncSession(result=FakeExecuteResult([watchlist_model]))
        )
    ).list_watchlist_items(
        recommendation_id="rec-1",
        symbol="aapl",
        status="active",
    )

    assert rationales[0].rationale_text == "Full rationale text."
    assert outcomes[0].outcome == "profitable"
    assert setups[0].setup_id == "rec-1:setup:swing"
    assert watchlist_items[0].watchlist_item_id == "rec-1:watchlist:primary"


def _bundle() -> RecommendationPersistenceBundle:
    return RecommendationPersistenceBundle(
        recommendation=_recommendation(),
        rationales=(_rationale(),),
        outcomes=(_outcome(),),
        trade_setups=(_trade_setup(),),
        watchlist_items=(_watchlist_item(),),
    )


def _recommendation() -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id="rec-1",
        symbol="aapl",
        bias="bullish",
        confidence=0.82,
        setup_quality=0.75,
        risk_score=0.25,
        risk_level="moderate",
        time_horizon="swing",
        status="active",
        lineage=_lineage(),
        created_at=_timestamp(),
        entry_context={"price": 190.0},
        stop_context={"stop": 180.0},
        target_context={"target": 210.0},
        metadata={"source": "strategy_synthesis"},
    )


def _rationale() -> RecommendationRationaleRecord:
    return RecommendationRationaleRecord(
        rationale_id="rec-1:rationale:primary",
        recommendation_id="rec-1",
        rationale_type="primary",
        rationale_text="Full rationale text.",
        confidence=0.8,
        lineage=_lineage(),
        created_at=_timestamp(),
        metadata={"model": "test"},
    )


def _outcome() -> RecommendationOutcomeRecord:
    return RecommendationOutcomeRecord(
        outcome_id="rec-1:outcome:day-1",
        recommendation_id="rec-1",
        evaluated_at=_timestamp(),
        human_action="accepted",
        outcome="profitable",
        outcome_return=0.03,
        outcome_notes="Followed plan.",
        lineage=_lineage(),
        metadata={"reviewed_by": "human"},
    )


def _trade_setup() -> TradeSetupRecord:
    return TradeSetupRecord(
        setup_id="rec-1:setup:swing",
        recommendation_id="rec-1",
        symbol="aapl",
        setup_type="breakout",
        bias="bullish",
        setup_quality=0.78,
        confidence=0.81,
        risk_score=0.24,
        risk_reward_ratio=2.5,
        time_horizon="swing",
        lineage=_lineage(),
        created_at=_timestamp(),
        entry_context={"trigger": 191.0},
        stop_context={"stop": 180.0},
        target_context={"target": 210.0},
        metadata={"source": "recommendation"},
    )


def _watchlist_item() -> WatchlistItemRecord:
    return WatchlistItemRecord(
        watchlist_item_id="rec-1:watchlist:primary",
        recommendation_id="rec-1",
        symbol="aapl",
        reason="High-quality setup with clear risk controls.",
        priority=1,
        status="active",
        bias="bullish",
        confidence=0.8,
        setup_quality=0.77,
        lineage=_lineage(),
        created_at=_timestamp(),
        metadata={"list": "morning_report"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="recommendation_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=UTC)
