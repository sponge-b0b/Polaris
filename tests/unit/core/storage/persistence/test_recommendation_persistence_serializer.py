from __future__ import annotations

from datetime import UTC, datetime

from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.storage.persistence.lineage import (
    PersistenceLineage,
    PersistenceRecordIdentity,
)
from core.storage.persistence.recommendations import (
    RecommendationOutcomeRecord,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
)
from core.storage.persistence.serializers.recommendation_persistence_serializer import (
    RecommendationPersistenceSerializer,
)


def test_recommendation_serializer_flattens_typed_parent_record() -> None:
    record = _recommendation()

    values = RecommendationPersistenceSerializer.recommendation_values(record)

    assert values["recommendation_id"] == "rec-1"
    assert values["symbol"] == "AAPL"
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["entry_context"] == {"price": 190.0}
    assert values["supporting_signals"] == [
        {
            "record_type": "agent_signal",
            "record_id": "signal-1",
        }
    ]
    assert values["metadata_payload"] == {"source": "strategy_synthesis"}


def test_recommendation_serializer_round_trips_parent_model() -> None:
    model = RecommendationModel(
        **RecommendationPersistenceSerializer.recommendation_values(
            _recommendation(),
        )
    )

    record = RecommendationPersistenceSerializer.recommendation_from_model(model)

    assert record.recommendation_id == "rec-1"
    assert record.symbol == "AAPL"
    assert record.lineage.node_name == "recommendation_node"
    assert record.entry_context == {"price": 190.0}
    assert record.supporting_signals == (
        PersistenceRecordIdentity(
            record_type="agent_signal",
            record_id="signal-1",
        ),
    )


def test_recommendation_serializer_preserves_full_rationale_text() -> None:
    full_text = "Long-form rationale. " * 200
    rationale = _rationale(full_text=full_text)

    values = RecommendationPersistenceSerializer.rationale_values(rationale)
    model = RecommendationRationaleModel(**values)
    record = RecommendationPersistenceSerializer.rationale_from_model(model)

    assert values["rationale_text"] == full_text
    assert record.rationale_text == full_text


def test_recommendation_serializer_round_trips_child_records() -> None:
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

    outcome = RecommendationPersistenceSerializer.outcome_from_model(outcome_model)
    setup = RecommendationPersistenceSerializer.trade_setup_from_model(setup_model)
    item = RecommendationPersistenceSerializer.watchlist_item_from_model(
        watchlist_model
    )

    assert outcome.outcome_id == "rec-1:outcome:day-1"
    assert outcome.human_action == "accepted"
    assert setup.setup_id == "rec-1:setup:swing"
    assert setup.entry_context == {"trigger": 191.0}
    assert item.watchlist_item_id == "rec-1:watchlist:primary"
    assert item.priority == 1


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
        supporting_signals=(
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id="signal-1",
            ),
        ),
        metadata={"source": "strategy_synthesis"},
    )


def _rationale(
    *,
    full_text: str = "Momentum and risk-adjusted setup are favorable.",
) -> RecommendationRationaleRecord:
    return RecommendationRationaleRecord(
        rationale_id="rec-1:rationale:primary",
        recommendation_id="rec-1",
        rationale_type="primary",
        rationale_text=full_text,
        confidence=0.8,
        lineage=_lineage(),
        created_at=_timestamp(),
        supporting_signals=(
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id="signal-1",
            ),
        ),
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
