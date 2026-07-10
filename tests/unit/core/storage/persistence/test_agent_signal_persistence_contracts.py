from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime
from datetime import timezone

import pytest

from core.storage.persistence.agent_signals import AgentSignalPersistenceResult
from core.storage.persistence.agent_signals import AgentSignalRecord
from core.storage.persistence.agent_signals import new_agent_signal_id


def test_agent_signal_record_is_typed_and_immutable() -> None:
    record = _signal_record()

    assert record.signal_id == "agent_signal:exec-1:TechnicalAgent:technical"
    assert record.agent_name == "TechnicalAgent"
    assert record.signals["trend"] == "bullish"
    assert record.llm_response is not None

    with pytest.raises(FrozenInstanceError):
        record.agent_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("signal_id", {"signal_id": " "}),
        ("agent_name", {"agent_name": ""}),
        ("agent_type", {"agent_type": " "}),
        ("directional_score", {"directional_score": 1.2}),
        ("confidence", {"confidence": -0.1}),
    ],
)
def test_agent_signal_record_validates_required_fields_and_scores(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "signal_id": "agent_signal:exec-1:TechnicalAgent:technical",
        "agent_name": "TechnicalAgent",
        "agent_type": "technical",
        "timestamp": datetime(2026, 5, 30, tzinfo=timezone.utc),
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        AgentSignalRecord(**values)  # type: ignore[arg-type]


def test_agent_signal_persistence_result_validates_state() -> None:
    success = AgentSignalPersistenceResult.succeeded(
        signal_id="signal-1",
    )
    failure = AgentSignalPersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.signal_id == "signal-1"
    assert failure.success is False

    with pytest.raises(ValueError, match="error"):
        AgentSignalPersistenceResult.failed(
            " ",
        )

    with pytest.raises(ValueError, match="successful"):
        AgentSignalPersistenceResult(
            success=True,
            signal_id="signal-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="signal_id"):
        AgentSignalPersistenceResult(
            success=True,
        )


def test_new_agent_signal_id_is_stable_when_lineage_is_available() -> None:
    signal_id = new_agent_signal_id(
        agent_name="TechnicalAgent",
        execution_id="exec-1",
        node_name="technical_node",
        signal_key="SPY",
    )

    assert signal_id == "agent_signal:exec-1:TechnicalAgent:technical_node:SPY"


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
        timestamp=datetime(2026, 5, 30, tzinfo=timezone.utc),
        directional_score=0.6,
        confidence=0.82,
        regime="bullish",
        signals={"trend": "bullish"},
        risks={"drawdown": "moderate"},
        recommendations={"posture": "risk-on"},
        features={"rsi": 61.0},
        reasoning_text="Full technical reasoning.",
        llm_response="Full LLM response. " * 100,
        metadata={"source": "unit-test"},
    )
