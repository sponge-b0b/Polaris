from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.market import (
    MarketBreadthSnapshotModel,
    MarketContextSnapshotModel,
    MarketEventSnapshotModel,
    MarketIndicatorModel,
    MarketOhlcvModel,
    TechnicalAnalysisSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.market import (
    MarketBreadthSnapshotRecord,
    MarketContextSnapshotRecord,
    MarketEventSnapshotRecord,
    MarketIndicatorRecord,
    MarketOhlcvRecord,
    MarketPersistenceBundle,
    TechnicalAnalysisSnapshotRecord,
)
from core.storage.persistence.repositories.postgres_market_persistence_repository import (  # noqa: E501
    PostgresMarketPersistenceRepository,
)
from core.storage.persistence.serializers.market_persistence_serializer import (
    MarketPersistenceSerializer,
)


class FakeScalarResult:
    def __init__(self, rows: Sequence[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(self, rows: Sequence[object] | None = None) -> None:
        self._rows = list(rows or [])

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
async def test_persist_market_bundle_upserts_facts_and_inserts_snapshots() -> None:
    session = FakeAsyncSession()
    repository = PostgresMarketPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_market_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "ohlcv-1"
    assert result.records_persisted == 6
    assert session.commits == 1
    assert len(session.executed) == 6
    assert "market_ohlcv" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "symbol, timestamp, source" in compiled[0]
    assert "market_indicators" in compiled[1]
    assert "ON CONFLICT" in compiled[1]
    assert "symbol, timestamp, source, indicator_name, timeframe" in compiled[1]
    assert "market_context_snapshots" in compiled[2]
    assert "ON CONFLICT" not in compiled[2]
    assert "technical_analysis_snapshots" in compiled[3]
    assert "ON CONFLICT" not in compiled[3]
    assert "market_breadth_snapshots" in compiled[4]
    assert "ON CONFLICT" not in compiled[4]
    assert "market_event_snapshots" in compiled[5]
    assert "ON CONFLICT" not in compiled[5]


@pytest.mark.asyncio
async def test_market_idempotency_review_source_key_facts_and_append_snapshots() -> (
    None
):
    session = FakeAsyncSession()
    repository = PostgresMarketPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_market_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert len(compiled) == 6
    assert "market_ohlcv" in compiled[0]
    assert "ON CONFLICT (symbol, timestamp, source)" in compiled[0]
    assert "DO UPDATE" in compiled[0]
    assert "market_indicators" in compiled[1]
    assert (
        "ON CONFLICT (symbol, timestamp, source, indicator_name, timeframe)"
        in compiled[1]
    )
    assert "DO UPDATE" in compiled[1]
    for statement in compiled[2:]:
        assert "ON CONFLICT" not in statement
    assert all("DELETE" not in statement.upper() for statement in compiled)


@pytest.mark.asyncio
async def test_persist_market_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresMarketPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_market_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_list_market_fact_records_returns_typed_records() -> None:
    ohlcv_model = MarketOhlcvModel(**MarketPersistenceSerializer.ohlcv_values(_ohlcv()))
    indicator_model = MarketIndicatorModel(
        **MarketPersistenceSerializer.indicator_values(_indicator())
    )

    ohlcv = await PostgresMarketPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([ohlcv_model])))
    ).list_ohlcv(
        symbol="spy",
        source="fmp",
        start=_timestamp(),
        end=_timestamp(),
    )
    indicators = await PostgresMarketPersistenceRepository(
        cast(
            AsyncSession, FakeAsyncSession(result=FakeExecuteResult([indicator_model]))
        )
    ).list_indicators(
        symbol="spy",
        indicator_name="rsi_14",
        source="technical-service",
        timeframe="1d",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert ohlcv[0].ohlcv_id == "ohlcv-1"
    assert ohlcv[0].symbol == "SPY"
    assert indicators[0].indicator_id == "indicator-1"
    assert indicators[0].parameters == {"period": 14}


@pytest.mark.asyncio
async def test_list_market_snapshot_records_returns_typed_records() -> None:
    context_model = MarketContextSnapshotModel(
        **MarketPersistenceSerializer.context_snapshot_values(_context())
    )
    technical_model = TechnicalAnalysisSnapshotModel(
        **MarketPersistenceSerializer.technical_snapshot_values(_technical())
    )
    breadth_model = MarketBreadthSnapshotModel(
        **MarketPersistenceSerializer.breadth_snapshot_values(_breadth())
    )
    event_model = MarketEventSnapshotModel(
        **MarketPersistenceSerializer.event_snapshot_values(_event())
    )

    contexts = await PostgresMarketPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([context_model])))
    ).list_context_snapshots(
        universe="sp500",
        source="market-context-service",
        market_regime="bullish",
        start=_timestamp(),
        end=_timestamp(),
    )
    technicals = await PostgresMarketPersistenceRepository(
        cast(
            AsyncSession, FakeAsyncSession(result=FakeExecuteResult([technical_model]))
        )
    ).list_technical_snapshots(
        symbol="spy",
        source="technical-service",
        technical_regime="bullish",
        start=_timestamp(),
        end=_timestamp(),
    )
    breadth = await PostgresMarketPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([breadth_model])))
    ).list_breadth_snapshots(
        universe="sp500",
        source="breadth-service",
        breadth_regime="constructive",
        start=_timestamp(),
        end=_timestamp(),
    )
    events = await PostgresMarketPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([event_model])))
    ).list_event_snapshots(
        symbol="spy",
        source="market-events-service",
        regime_bias="risk_off",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert contexts[0].context_snapshot_id == "context-1"
    assert contexts[0].market_context_payload == {"summary": "risk-on"}
    assert technicals[0].technical_snapshot_id == "technical-1"
    assert technicals[0].regime_payload == {"signal": "uptrend"}
    assert breadth[0].breadth_snapshot_id == "breadth-1"
    assert breadth[0].breadth_payload == {"summary": "constructive"}
    assert events[0].event_snapshot_id == "event-1"
    assert events[0].volatility_forecast == "high"


def _bundle() -> MarketPersistenceBundle:
    return MarketPersistenceBundle(
        ohlcv=(_ohlcv(),),
        indicators=(_indicator(),),
        context_snapshots=(_context(),),
        technical_snapshots=(_technical(),),
        breadth_snapshots=(_breadth(),),
        event_snapshots=(_event(),),
    )


def _ohlcv() -> MarketOhlcvRecord:
    return MarketOhlcvRecord(
        ohlcv_id="ohlcv-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="fmp",
        open_price=530.0,
        high_price=535.0,
        low_price=529.0,
        close_price=532.0,
        adjusted_close=532.0,
        volume=1_000_000.0,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _indicator() -> MarketIndicatorRecord:
    return MarketIndicatorRecord(
        indicator_id="indicator-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="technical-service",
        indicator_name="rsi_14",
        indicator_value=61.5,
        timeframe="1d",
        parameters={"period": 14},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _context() -> MarketContextSnapshotRecord:
    return MarketContextSnapshotRecord(
        context_snapshot_id="context-1",
        timestamp=_timestamp(),
        source="market-context-service",
        universe="sp500",
        market_regime="bullish",
        volatility_regime="normal",
        breadth_regime="constructive",
        trend_score=0.6,
        volatility_score=0.3,
        breadth_score=0.4,
        risk_score=0.25,
        vix=14.5,
        vvix=82.0,
        inputs_payload={"vix": 14.5},
        market_context_payload={"summary": "risk-on"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _technical() -> TechnicalAnalysisSnapshotRecord:
    return TechnicalAnalysisSnapshotRecord(
        technical_snapshot_id="technical-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="technical-service",
        technical_regime="bullish",
        trend_regime="uptrend",
        volatility_regime="normal",
        breadth_regime="constructive",
        directional_technical_score=0.7,
        trend_score=0.65,
        volatility_score=0.25,
        breadth_score=0.45,
        risk_score=0.2,
        confidence=0.82,
        inputs_payload={"prices": 252},
        snapshot_payload={"rsi_14": 61.5},
        regime_payload={"signal": "uptrend"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _breadth() -> MarketBreadthSnapshotRecord:
    return MarketBreadthSnapshotRecord(
        breadth_snapshot_id="breadth-1",
        timestamp=_timestamp(),
        universe="sp500",
        source="breadth-service",
        advances_count=320,
        declines_count=170,
        unchanged_count=10,
        new_highs=30,
        new_lows=8,
        ad_line=1250.0,
        pct_above_50dma=0.62,
        pct_above_200dma=0.58,
        breadth_score=0.5,
        breadth_risk_score=0.2,
        breadth_regime="constructive",
        inputs_payload={"advancers": 320},
        breadth_payload={"summary": "constructive"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _event() -> MarketEventSnapshotRecord:
    return MarketEventSnapshotRecord(
        event_snapshot_id="event-1",
        symbol="spy",
        timestamp=_timestamp(),
        source="market-events-service",
        market_pressure_score=0.45,
        volatility_forecast="high",
        regime_bias="risk_off",
        event_count=3,
        high_impact_count=1,
        events_payload={"events": ["cpi"]},
        high_impact_events_payload={"events": ["fomc"]},
        risk_projection_payload={"expected_volatility": "high"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_analysis",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=UTC)
