from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.recommendations import (
    RecommendationClaimEvidenceLinkModel,
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.recommendations import (
    RecommendationClaimEvidenceLinkRecord,
    RecommendationOutcomeRecord,
    RecommendationPersistenceBundle,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
)
from core.storage.persistence.repositories.postgres_recommendation_persistence_repository import (  # noqa: E501 - canonical module path
    PostgresRecommendationPersistenceRepository,
)
from core.storage.persistence.serializers.recommendation_persistence_serializer import (
    RecommendationPersistenceSerializer,
)
from core.telemetry.events import TelemetryEvent
from core.telemetry.observability import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from domain.authority import RiskTier


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
        execute_errors: dict[int, SQLAlchemyError] | None = None,
    ) -> None:
        self.result = result or FakeExecuteResult()
        self.error = error
        self.execute_errors = execute_errors or {}
        self.executed: list[Any] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement: Any) -> FakeExecuteResult:
        self.executed.append(statement)
        execute_index = len(self.executed)
        if execute_index in self.execute_errors:
            raise self.execute_errors[execute_index]
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


@pytest.mark.asyncio
async def test_persist_recommendation_bundle_includes_claim_evidence_links() -> None:
    session = FakeAsyncSession()
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    result = await repository.persist_recommendation_bundle(
        RecommendationPersistenceBundle(
            recommendation=_recommendation(),
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
    assert "recommendation_claim_evidence_links" in compiled[1]


@pytest.mark.asyncio
async def test_persist_recommendation_claim_links_records_success_observability() -> (
    None
):
    observability_manager, sink = _observability()
    session = FakeAsyncSession()
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    result = await repository.persist_recommendation_bundle(
        RecommendationPersistenceBundle(
            recommendation=_recommendation(),
            claim_evidence_links=(_claim_evidence_link(),),
        )
    )

    assert result.success is True
    event = _datastore_event(sink)
    assert event.success is True
    assert event.event_type == "storage.postgres.operation"
    assert event.duration_seconds is not None
    assert event.attributes["operation"] == "recommendation_claim_evidence_link_write"
    assert event.attributes["operation_kind"] == "datastore_operation"
    assert event.attributes["database_system"] == "postgresql"
    assert event.attributes["recommendation_id"] == "rec-1"
    assert event.payload["records_persisted"] == 1
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.recommendation_claim_evidence_link.operations.total"
        in metric_names
    )
    assert (
        "storage.postgres.recommendation_claim_evidence_link.duration_seconds"
        in metric_names
    )


@pytest.mark.asyncio
async def test_persist_recommendation_claim_evidence_links_logs_and_records_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observability_manager, sink = _observability()
    session = FakeAsyncSession(
        execute_errors={2: SQLAlchemyError("database unavailable")},
    )
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    with caplog.at_level(logging.ERROR):
        result = await repository.persist_recommendation_bundle(
            RecommendationPersistenceBundle(
                recommendation=_recommendation(),
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
    assert event.attributes["operation"] == "recommendation_claim_evidence_link_write"
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.recommendation_claim_evidence_link.operations.failed"
        in metric_names
    )
    failure_logs = [
        record
        for record in caplog.records
        if record.message
        == "Recommendation PostgreSQL claim-evidence link write failed."
    ]
    assert failure_logs
    assert failure_logs[0].exc_info is not None
    failure_context = vars(failure_logs[0])
    assert failure_context["recommendation_id"] == "rec-1"
    assert failure_context["operation"] == "recommendation_claim_evidence_link_write"


@pytest.mark.asyncio
async def test_list_recommendation_claim_evidence_links_returns_typed_records() -> None:
    model = RecommendationClaimEvidenceLinkModel(
        link_id="rec-1:claim_evidence:claim-1:packet-1:claim-a",
        recommendation_id="rec-1",
        rationale_id="rec-1:rationale:primary",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier="vigilant",
        material=True,
        supporting_evidence_ids=["evidence-1"],
        reconstruction_reference_ids=["reconstruction-1"],
        uncertainty_ids=["uncertainty-1"],
        limitation_ids=["limitation-1"],
    )
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session)
    )

    records = await repository.list_claim_evidence_links(
        recommendation_id="rec-1",
        rationale_id="rec-1:rationale:primary",
        packet_id="packet-1",
        claim_target_id="claim-1",
    )

    assert len(records) == 1
    assert records[0].risk_tier is RiskTier.VIGILANT
    assert records[0].supporting_evidence_ids == ("evidence-1",)
    assert records[0].reconstruction_reference_ids == ("reconstruction-1",)


@pytest.mark.asyncio
async def test_list_recommendation_claim_links_records_success_observability() -> None:
    model = RecommendationClaimEvidenceLinkModel(
        link_id="rec-1:claim_evidence:claim-1:packet-1:claim-a",
        recommendation_id="rec-1",
        rationale_id="rec-1:rationale:primary",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier="vigilant",
        material=True,
        supporting_evidence_ids=["evidence-1"],
        reconstruction_reference_ids=["reconstruction-1"],
        uncertainty_ids=["uncertainty-1"],
        limitation_ids=["limitation-1"],
    )
    observability_manager, sink = _observability()
    session = FakeAsyncSession(result=FakeExecuteResult([model]))
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    records = await repository.list_claim_evidence_links(
        recommendation_id="rec-1",
        rationale_id="rec-1:rationale:primary",
        packet_id="packet-1",
        claim_target_id="claim-1",
    )

    assert len(records) == 1
    event = _datastore_event(sink)
    assert event.success is True
    assert event.duration_seconds is not None
    assert event.attributes["operation"] == "recommendation_claim_evidence_link_read"
    assert event.attributes["operation_kind"] == "datastore_operation"
    assert event.attributes["recommendation_id"] == "rec-1"
    assert event.payload["records_returned"] == 1
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.recommendation_claim_evidence_link.operations.total"
        in metric_names
    )
    assert (
        "storage.postgres.recommendation_claim_evidence_link.duration_seconds"
        in metric_names
    )


@pytest.mark.asyncio
async def test_list_recommendation_claim_evidence_links_logs_and_records_failures(
    caplog: pytest.LogCaptureFixture,
) -> None:
    observability_manager, sink = _observability()
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresRecommendationPersistenceRepository(
        cast(AsyncSession, session),
        observability_manager=observability_manager,
    )

    with caplog.at_level(logging.ERROR), pytest.raises(SQLAlchemyError):
        await repository.list_claim_evidence_links(
            recommendation_id="rec-1",
            rationale_id="rec-1:rationale:primary",
            packet_id="packet-1",
            claim_target_id="claim-1",
        )

    event = _datastore_event(sink)
    assert event.success is False
    assert event.error_count == 1
    assert event.exception_details is not None
    assert event.exception_details.exception_type == "SQLAlchemyError"
    assert "database unavailable" in event.exception_details.stack_trace
    assert event.attributes["operation"] == "recommendation_claim_evidence_link_read"
    metric_names = _metric_names(observability_manager)
    assert (
        "storage.postgres.recommendation_claim_evidence_link.operations.failed"
        in metric_names
    )
    failure_logs = [
        record
        for record in caplog.records
        if record.message
        == "Recommendation PostgreSQL claim-evidence link read failed."
    ]
    assert failure_logs
    assert failure_logs[0].exc_info is not None
    failure_context = vars(failure_logs[0])
    assert failure_context["recommendation_id"] == "rec-1"
    assert failure_context["operation"] == "recommendation_claim_evidence_link_read"


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


def _claim_evidence_link() -> RecommendationClaimEvidenceLinkRecord:
    return RecommendationClaimEvidenceLinkRecord(
        link_id="rec-1:claim_evidence:claim-1:packet-1:claim-a",
        recommendation_id="rec-1",
        rationale_id="rec-1:rationale:primary",
        claim_target_id="claim-1",
        packet_id="packet-1",
        packet_claim_id="claim-a",
        risk_tier=RiskTier.VIGILANT,
        material=True,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("reconstruction-1",),
    )
