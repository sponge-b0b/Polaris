from __future__ import annotations

from datetime import datetime
from datetime import timezone

from core.database.models.agent_signals import AgentSignalModel
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.serializers.agent_signal_persistence_serializer import (
    AgentSignalPersistenceSerializer,
)


def test_agent_signal_serializer_preserves_full_reasoning_and_payloads() -> None:
    full_llm_response = "Detailed agent rationale. " * 200
    record = _signal_record(
        llm_response=full_llm_response,
    )

    values = AgentSignalPersistenceSerializer.signal_values(
        record,
    )

    assert values["signal_id"] == record.signal_id
    assert values["universe"] == ["SPY", "QQQ"]
    assert values["signal_payload"] == {"trend": "bullish"}
    assert values["risk_payload"] == {"drawdown": "moderate"}
    assert values["recommendation_payload"] == {"posture": "risk-on"}
    assert values["feature_payload"] == {"rsi": 61.0}
    assert values["reasoning_text"] == "Full technical reasoning."
    assert values["llm_response"] == full_llm_response


def test_agent_signal_serializer_round_trips_model_to_record() -> None:
    record = _signal_record()
    model = AgentSignalModel(
        **AgentSignalPersistenceSerializer.signal_values(
            record,
        )
    )

    round_tripped = AgentSignalPersistenceSerializer.signal_from_model(
        model,
    )

    assert round_tripped.signal_id == record.signal_id
    assert round_tripped.universe == ("SPY", "QQQ")
    assert round_tripped.signals == {"trend": "bullish"}
    assert round_tripped.risks == {"drawdown": "moderate"}
    assert round_tripped.recommendations == {"posture": "risk-on"}
    assert round_tripped.features == {"rsi": 61.0}
    assert round_tripped.llm_response == record.llm_response


def _signal_record(
    *,
    llm_response: str = "Full LLM response.",
) -> AgentSignalRecord:
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
        timestamp=datetime(2026, 5, 30, tzinfo=timezone.utc),
        directional_score=0.6,
        confidence=0.82,
        regime="bullish",
        signals={"trend": "bullish"},
        risks={"drawdown": "moderate"},
        recommendations={"posture": "risk-on"},
        features={"rsi": 61.0},
        reasoning_text="Full technical reasoning.",
        llm_response=llm_response,
        metadata={"source": "unit-test"},
    )
