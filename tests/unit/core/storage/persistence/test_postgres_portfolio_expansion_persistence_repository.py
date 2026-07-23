from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.portfolio import (
    PortfolioAllocationSnapshotModel,
    PortfolioEquityHistoryPointModel,
    PortfolioExposureSnapshotModel,
    PortfolioPositionHistoryModel,
    PortfolioPositionLatestModel,
    PortfolioRiskSnapshotModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.portfolio import (
    PortfolioAllocationSnapshotRecord,
    PortfolioEquityHistoryPointRecord,
    PortfolioExpansionPersistenceBundle,
    PortfolioExposureSnapshotRecord,
    PortfolioPositionHistoryRecord,
    PortfolioPositionLatestRecord,
    PortfolioRiskSnapshotRecord,
)
from core.storage.persistence.repositories.postgres_portfolio_expansion_persistence_repository import (  # noqa: E501
    PostgresPortfolioExpansionPersistenceRepository,
)
from core.storage.persistence.serializers.portfolio_persistence_serializer import (
    PortfolioPersistenceSerializer,
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
async def test_persist_portfolio_bundle_inserts_history_and_upserts_latest() -> None:
    session = FakeAsyncSession()
    repository = PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_portfolio_expansion_bundle(_bundle())

    compiled = [
        str(
            statement.compile(
                dialect=postgresql.dialect(),
            )
        )
        for statement in session.executed
    ]

    assert result.success is True
    assert result.account_id == "acct-1"
    assert result.records_persisted == 6
    assert session.commits == 1
    assert len(session.executed) == 6
    assert "portfolio_equity_history_points" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "account_id, source, timeframe, observed_at" in compiled[0]
    assert "portfolio_positions_history" in compiled[1]
    assert "ON CONFLICT" not in compiled[1]
    assert "portfolio_positions_latest" in compiled[2]
    assert "ON CONFLICT" in compiled[2]
    assert "account_id, symbol" in compiled[2]
    assert "portfolio_exposure_snapshots" in compiled[3]
    assert "ON CONFLICT" not in compiled[3]
    assert "portfolio_risk_snapshots" in compiled[4]
    assert "portfolio_allocation_snapshots" in compiled[5]


@pytest.mark.asyncio
async def test_portfolio_idempotency_review_latest_upserts_append_records_insert_only() -> (  # noqa: E501
    None
):
    session = FakeAsyncSession()
    repository = PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_portfolio_expansion_bundle(_bundle())

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
    assert "portfolio_equity_history_points" in compiled[0]
    assert "ON CONFLICT (account_id, source, timeframe, observed_at)" in compiled[0]
    assert "DO NOTHING" in compiled[0]
    assert "portfolio_positions_history" in compiled[1]
    assert "ON CONFLICT" not in compiled[1]
    assert "portfolio_positions_latest" in compiled[2]
    assert "ON CONFLICT (account_id, symbol)" in compiled[2]
    assert "DO UPDATE" in compiled[2]
    assert "portfolio_exposure_snapshots" in compiled[3]
    assert "ON CONFLICT" not in compiled[3]
    assert "portfolio_risk_snapshots" in compiled[4]
    assert "ON CONFLICT" not in compiled[4]
    assert "portfolio_allocation_snapshots" in compiled[5]
    assert "ON CONFLICT" not in compiled[5]


@pytest.mark.asyncio
async def test_persist_portfolio_bundle_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_portfolio_expansion_bundle(_bundle())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_list_equity_history_points_returns_typed_records() -> None:
    model = PortfolioEquityHistoryPointModel(
        **PortfolioPersistenceSerializer.equity_history_point_values(
            _equity_history_point()
        )
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))

    records = await PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, session)
    ).list_equity_history_points(
        account_id="acct-1",
        source="alpaca",
        timeframe="1D",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert records == (_equity_history_point(),)
    compiled = str(session.executed[0].compile(dialect=postgresql.dialect()))
    assert "portfolio_equity_history_points" in compiled
    assert "ORDER BY portfolio_equity_history_points.observed_at" in compiled


@pytest.mark.asyncio
async def test_list_position_records_returns_typed_records() -> None:
    history_model = PortfolioPositionHistoryModel(
        **PortfolioPersistenceSerializer.position_history_values(_position_history())
    )
    latest_model = PortfolioPositionLatestModel(
        **PortfolioPersistenceSerializer.position_latest_values(_position_latest())
    )

    history = await PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([history_model])))
    ).list_position_history(
        account_id="acct-1",
        symbol="spy",
        start=_timestamp(),
        end=_timestamp(),
    )
    latest = await PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([latest_model])))
    ).list_latest_positions(
        account_id="acct-1",
        symbol="spy",
    )

    assert history[0].position_history_id == "position-history-1"
    assert history[0].symbol == "SPY"
    assert latest[0].position_latest_id == "portfolio_position_latest:acct-1:SPY"
    assert latest[0].weight == 0.42


@pytest.mark.asyncio
async def test_list_snapshot_records_returns_typed_records() -> None:
    exposure_model = PortfolioExposureSnapshotModel(
        **PortfolioPersistenceSerializer.exposure_snapshot_values(_exposure())
    )
    risk_model = PortfolioRiskSnapshotModel(
        **PortfolioPersistenceSerializer.risk_snapshot_values(_risk())
    )
    allocation_model = PortfolioAllocationSnapshotModel(
        **PortfolioPersistenceSerializer.allocation_snapshot_values(_allocation())
    )

    exposures = await PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([exposure_model])))
    ).list_exposure_snapshots(
        account_id="acct-1",
        exposure_type="sector",
        start=_timestamp(),
        end=_timestamp(),
    )
    risks = await PostgresPortfolioExpansionPersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([risk_model])))
    ).list_risk_snapshots(
        account_id="acct-1",
        risk_level="moderate",
        start=_timestamp(),
        end=_timestamp(),
    )
    allocations = await PostgresPortfolioExpansionPersistenceRepository(
        cast(
            AsyncSession, FakeAsyncSession(result=FakeExecuteResult([allocation_model]))
        )
    ).list_allocation_snapshots(
        account_id="acct-1",
        allocation_type="sector",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert exposures[0].exposure_snapshot_id == "exposure-1"
    assert exposures[0].exposure_value == -0.15
    assert risks[0].risk_snapshot_id == "risk-1"
    assert risks[0].risk_signals == {"capital_preservation": "ok"}
    assert allocations[0].allocation_snapshot_id == "allocation-1"
    assert allocations[0].drift == 0.05


def _bundle() -> PortfolioExpansionPersistenceBundle:
    return PortfolioExpansionPersistenceBundle(
        equity_history_points=(_equity_history_point(),),
        position_history=(_position_history(),),
        position_latest=(_position_latest(),),
        exposure_snapshots=(_exposure(),),
        risk_snapshots=(_risk(),),
        allocation_snapshots=(_allocation(),),
    )


def _equity_history_point() -> PortfolioEquityHistoryPointRecord:
    return PortfolioEquityHistoryPointRecord(
        portfolio_equity_history_point_id=(
            "portfolio_equity_history_point:acct-1:alpaca:1D:2026-05-31T13:00:00+00:00"
        ),
        account_id="acct-1",
        source="alpaca",
        timeframe="1D",
        observed_at=_timestamp(),
        equity=100_000.123456789,
        profit_loss=1_250.987654321,
        profit_loss_pct=0.01250987654321,
        base_value=98_749.135802468,
        cashflow_payload={"deposit": 250.125},
        lineage=_lineage(),
    )


def _position_history() -> PortfolioPositionHistoryRecord:
    return PortfolioPositionHistoryRecord(
        position_history_id="position-history-1",
        account_id="acct-1",
        symbol="spy",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=5300.0,
        cost_basis=5000.0,
        weight=0.42,
        sector="ETF",
        theme="core",
        beta=1.0,
        risk_weight=0.35,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _position_latest() -> PortfolioPositionLatestRecord:
    return PortfolioPositionLatestRecord(
        position_latest_id="portfolio_position_latest:acct-1:SPY",
        account_id="acct-1",
        symbol="spy",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        quantity=10.0,
        market_value=5300.0,
        cost_basis=5000.0,
        weight=0.42,
        sector="ETF",
        theme="core",
        beta=1.0,
        risk_weight=0.35,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _exposure() -> PortfolioExposureSnapshotRecord:
    return PortfolioExposureSnapshotRecord(
        exposure_snapshot_id="exposure-1",
        account_id="acct-1",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        exposure_type="sector",
        exposure_name="Technology",
        exposure_value=-0.15,
        weight=0.35,
        beta=1.2,
        risk_weight=0.4,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _risk() -> PortfolioRiskSnapshotRecord:
    return PortfolioRiskSnapshotRecord(
        risk_snapshot_id="risk-1",
        account_id="acct-1",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        portfolio_value=100000.0,
        cash=12000.0,
        account_health="healthy",
        risk_score=0.31,
        risk_level="moderate",
        drawdown_risk=0.2,
        volatility_risk=0.4,
        concentration_risk=0.35,
        liquidity_risk=0.1,
        beta=1.05,
        cash_ratio=0.12,
        equity_retention_ratio=0.98,
        risk_signals={"capital_preservation": "ok"},
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _allocation() -> PortfolioAllocationSnapshotRecord:
    return PortfolioAllocationSnapshotRecord(
        allocation_snapshot_id="allocation-1",
        account_id="acct-1",
        snapshot_id="snapshot-1",
        timestamp=_timestamp(),
        allocation_type="sector",
        allocation_name="Technology",
        current_weight=0.35,
        target_weight=0.3,
        drift=0.05,
        market_value=35000.0,
        lineage=_lineage(),
        metadata={"source": "unit-test"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="portfolio_state",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 13, 0, tzinfo=UTC)
