from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.recommendations import RecommendationOutcomeRecord
from core.storage.persistence.recommendations import RecommendationPersistenceBundle
from core.storage.persistence.recommendations import RecommendationPersistenceResult
from core.storage.persistence.recommendations import RecommendationRationaleRecord
from core.storage.persistence.recommendations import RecommendationRecord
from core.storage.persistence.recommendations import TradeSetupRecord
from core.storage.persistence.recommendations import WatchlistItemRecord
from core.storage.persistence.recommendations import new_recommendation_child_id
from core.storage.persistence.recommendations import new_recommendation_id


def test_recommendation_record_is_typed_normalized_and_immutable() -> None:
    record = _recommendation()

    assert record.recommendation_id == "recommendation:exec-1:SPY:primary"
    assert record.symbol == "SPY"
    assert record.bias == "bullish"
    assert record.confidence == 0.82
    assert record.setup_quality == 0.74
    assert record.risk_score == 0.31
    assert record.risk_level == "moderate"
    assert record.time_horizon == "swing"
    assert record.status == "active"
    assert record.entry_context == {"entry_zone": "pullback"}
    assert record.stop_context == {"invalidates_below": 520.0}
    assert record.target_context == {"target": 550.0}
    assert record.supporting_signals[0].record_type == "agent_signal"
    assert record.lineage.execution_id == "exec-1"

    with pytest.raises(FrozenInstanceError):
        record.symbol = "QQQ"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "field_name"),
    [
        ({"recommendation_id": " "}, "recommendation_id"),
        ({"symbol": ""}, "symbol"),
        ({"bias": " "}, "bias"),
        ({"confidence": 1.1}, "confidence"),
        ({"setup_quality": -0.1}, "setup_quality"),
        ({"risk_score": 1.2}, "risk_score"),
    ],
)
def test_recommendation_record_validates_required_fields_and_scores(
    kwargs: dict[str, object],
    field_name: str,
) -> None:
    values: dict[str, object] = {
        "recommendation_id": "recommendation:exec-1:SPY:primary",
        "symbol": "SPY",
        "bias": "bullish",
        "confidence": 0.82,
        "created_at": _timestamp(),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        RecommendationRecord(**values)  # type: ignore[arg-type]


def test_recommendation_rationale_preserves_full_text_and_supporting_signals() -> None:
    long_rationale = "Full LLM rationale. " * 200
    rationale = RecommendationRationaleRecord(
        rationale_id="recommendation:exec-1:SPY:primary:rationale:primary",
        recommendation_id="recommendation:exec-1:SPY:primary",
        rationale_type="primary",
        rationale_text=long_rationale,
        confidence=0.8,
        created_at=_timestamp(),
        supporting_signals=(_signal_identity(),),
    )

    assert rationale.rationale_text == long_rationale
    assert rationale.supporting_signals == (_signal_identity(),)

    with pytest.raises(ValueError, match="rationale_text"):
        RecommendationRationaleRecord(
            rationale_id="rationale-1",
            recommendation_id="recommendation-1",
            rationale_type="primary",
            rationale_text=" ",
            created_at=_timestamp(),
        )


def test_recommendation_outcome_captures_human_action_and_outcome() -> None:
    outcome = RecommendationOutcomeRecord(
        outcome_id="recommendation:exec-1:SPY:primary:outcome:20260530",
        recommendation_id="recommendation:exec-1:SPY:primary",
        evaluated_at=_timestamp(),
        human_action=" watched ",
        outcome=" profitable ",
        outcome_return=0.04,
        outcome_notes=" Followed after confirmation. ",
    )

    assert outcome.human_action == "watched"
    assert outcome.outcome == "profitable"
    assert outcome.outcome_notes == "Followed after confirmation."
    assert outcome.outcome_return == 0.04


def test_trade_setup_record_preserves_broker_agnostic_context() -> None:
    setup = TradeSetupRecord(
        setup_id="recommendation:exec-1:SPY:primary:setup:breakout",
        recommendation_id=" recommendation:exec-1:SPY:primary ",
        symbol=" spy ",
        setup_type="breakout",
        bias="bullish",
        setup_quality=0.75,
        confidence=0.8,
        risk_score=0.25,
        risk_reward_ratio=2.5,
        time_horizon=" swing ",
        created_at=_timestamp(),
        entry_context={"entry": 530.0},
        stop_context={"stop": 520.0},
        target_context={"target": 555.0},
    )

    assert setup.symbol == "SPY"
    assert setup.recommendation_id == "recommendation:exec-1:SPY:primary"
    assert setup.time_horizon == "swing"
    assert setup.risk_reward_ratio == 2.5

    with pytest.raises(ValueError, match="risk_reward_ratio"):
        TradeSetupRecord(
            setup_id="setup-1",
            symbol="SPY",
            setup_type="breakout",
            bias="bullish",
            risk_reward_ratio=-1.0,
            created_at=_timestamp(),
        )


def test_watchlist_item_record_preserves_status_priority_and_scores() -> None:
    item = WatchlistItemRecord(
        watchlist_item_id="watchlist:exec-1:SPY",
        recommendation_id=" recommendation:exec-1:SPY:primary ",
        symbol=" spy ",
        reason=" Momentum setup forming. ",
        priority=2,
        status=" active ",
        bias=" bullish ",
        confidence=0.7,
        setup_quality=0.76,
        created_at=_timestamp(),
    )

    assert item.symbol == "SPY"
    assert item.reason == "Momentum setup forming."
    assert item.recommendation_id == "recommendation:exec-1:SPY:primary"
    assert item.status == "active"
    assert item.bias == "bullish"

    with pytest.raises(ValueError, match="priority"):
        WatchlistItemRecord(
            watchlist_item_id="watchlist-1",
            symbol="SPY",
            reason="Setup forming.",
            priority=-1,
            created_at=_timestamp(),
        )


def test_recommendation_bundle_groups_atomic_persistence_payload() -> None:
    recommendation = _recommendation()
    bundle = RecommendationPersistenceBundle(
        recommendation=recommendation,
        rationales=(
            RecommendationRationaleRecord(
                rationale_id="rationale-1",
                recommendation_id=recommendation.recommendation_id,
                rationale_type="primary",
                rationale_text="Full rationale",
                created_at=_timestamp(),
            ),
        ),
        outcomes=(
            RecommendationOutcomeRecord(
                outcome_id="outcome-1",
                recommendation_id=recommendation.recommendation_id,
                evaluated_at=_timestamp(),
                human_action="watched",
            ),
        ),
        trade_setups=(
            TradeSetupRecord(
                setup_id="setup-1",
                recommendation_id=recommendation.recommendation_id,
                symbol="SPY",
                setup_type="pullback",
                bias="bullish",
                created_at=_timestamp(),
            ),
        ),
        watchlist_items=(
            WatchlistItemRecord(
                watchlist_item_id="watchlist-1",
                recommendation_id=recommendation.recommendation_id,
                symbol="SPY",
                reason="Setup improving.",
                created_at=_timestamp(),
            ),
        ),
    )

    assert bundle.recommendation == recommendation
    assert len(bundle.rationales) == 1
    assert len(bundle.outcomes) == 1
    assert len(bundle.trade_setups) == 1
    assert len(bundle.watchlist_items) == 1


def test_recommendation_persistence_result_validates_state() -> None:
    success = RecommendationPersistenceResult.succeeded(
        recommendation_id="recommendation-1",
    )
    failure = RecommendationPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.recommendation_id == "recommendation-1"
    assert failure.success is False

    with pytest.raises(ValueError, match="error"):
        RecommendationPersistenceResult.failed(
            " ",
        )

    with pytest.raises(ValueError, match="successful"):
        RecommendationPersistenceResult(
            success=True,
            recommendation_id="recommendation-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="recommendation_id"):
        RecommendationPersistenceResult(
            success=True,
        )


def test_recommendation_id_helpers_are_stable_with_execution_lineage() -> None:
    recommendation_id = new_recommendation_id(
        symbol=" spy ",
        execution_id=" exec-1 ",
        recommendation_key=" primary ",
    )
    child_id = new_recommendation_child_id(
        recommendation_id=recommendation_id,
        child_type="rationale",
        child_key="primary",
    )

    assert recommendation_id == "recommendation:exec-1:SPY:primary"
    assert child_id == "recommendation:exec-1:SPY:primary:rationale:primary"


def test_recommendation_child_id_helpers_are_duplicate_safe_for_each_child_type() -> (
    None
):
    recommendation_id = new_recommendation_id(
        symbol=" spy ",
        execution_id=" exec-1 ",
        recommendation_key=" primary ",
    )

    child_ids = {
        child_type: new_recommendation_child_id(
            recommendation_id=recommendation_id,
            child_type=child_type,
            child_key=" primary ",
        )
        for child_type in (
            "rationale",
            "outcome",
            "setup",
            "watchlist",
        )
    }

    assert child_ids == {
        "rationale": "recommendation:exec-1:SPY:primary:rationale:primary",
        "outcome": "recommendation:exec-1:SPY:primary:outcome:primary",
        "setup": "recommendation:exec-1:SPY:primary:setup:primary",
        "watchlist": "recommendation:exec-1:SPY:primary:watchlist:primary",
    }
    assert len(set(child_ids.values())) == 4


def _recommendation() -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id="recommendation:exec-1:SPY:primary",
        symbol=" spy ",
        bias="bullish",
        confidence=0.82,
        setup_quality=0.74,
        risk_score=0.31,
        risk_level=" moderate ",
        time_horizon=" swing ",
        status=" active ",
        created_at=_timestamp(),
        lineage=PersistenceLineage(
            workflow_name="morning_report",
            execution_id="exec-1",
            runtime_id="runtime-1",
            node_name="portfolio_manager",
        ),
        entry_context={"entry_zone": "pullback"},
        stop_context={"invalidates_below": 520.0},
        target_context={"target": 550.0},
        supporting_signals=(_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _signal_identity() -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type="agent_signal",
        record_id="signal-1",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 30, tzinfo=timezone.utc)
