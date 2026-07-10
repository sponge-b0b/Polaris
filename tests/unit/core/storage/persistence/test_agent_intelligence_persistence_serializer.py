from __future__ import annotations

from datetime import datetime
from datetime import timezone

from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_intelligence import AgentRecommendationModel
from core.database.models.agent_intelligence import AgentRiskAssessmentModel
from core.storage.persistence.agent_intelligence import AgentReasoningRecord
from core.storage.persistence.agent_intelligence import AgentRecommendationRecord
from core.storage.persistence.agent_intelligence import AgentRiskAssessmentRecord
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.serializers.agent_intelligence_persistence_serializer import (
    AgentIntelligencePersistenceSerializer,
)


_FULL_TEXT = "Full text must not be truncated. " * 200
_FULL_LLM_RESPONSE = "Full LLM response must not be truncated. " * 250


def test_agent_intelligence_serializer_flattens_reasoning_record() -> None:
    record = _reasoning()

    values = AgentIntelligencePersistenceSerializer.reasoning_values(record)

    assert values["reasoning_id"] == "agent-reasoning-1"
    assert values["agent_signal_id"] == "agent-signal-1"
    assert values["symbol"] == "SPY"
    assert values["reasoning_text"] == _FULL_TEXT.strip()
    assert values["full_llm_response"] == _FULL_LLM_RESPONSE.strip()
    assert values["linked_records"] == [
        {"record_type": "agent_signal", "record_id": "agent-signal-1"},
    ]
    assert values["workflow_name"] == "morning_report"
    assert values["execution_id"] == "exec-1"
    assert values["metadata_payload"] == {"source": "unit-test"}


def test_agent_intelligence_serializer_round_trips_reasoning_record() -> None:
    model = AgentReasoningModel(
        **AgentIntelligencePersistenceSerializer.reasoning_values(_reasoning())
    )

    record = AgentIntelligencePersistenceSerializer.reasoning_from_model(model)

    assert record.reasoning_id == "agent-reasoning-1"
    assert record.agent_signal_id == "agent-signal-1"
    assert record.symbol == "SPY"
    assert record.reasoning_text == _FULL_TEXT.strip()
    assert record.full_llm_response == _FULL_LLM_RESPONSE.strip()
    assert record.linked_records[0].record_type == "agent_signal"
    assert record.lineage.node_name == "technical_node"
    assert record.metadata == {"source": "unit-test"}


def test_agent_intelligence_serializer_flattens_recommendation_record() -> None:
    record = _recommendation()

    values = AgentIntelligencePersistenceSerializer.recommendation_values(record)

    assert values["agent_recommendation_id"] == "agent-recommendation-1"
    assert values["agent_signal_id"] == "agent-signal-1"
    assert values["recommendation_type"] == "portfolio_posture"
    assert values["recommendation_text"] == "Maintain moderate risk-on posture."
    assert values["rationale_text"] == _FULL_TEXT.strip()
    assert values["full_llm_response"] == _FULL_LLM_RESPONSE.strip()
    assert values["supporting_signals"] == [
        {"record_type": "agent_signal", "record_id": "agent-signal-1"},
    ]
    assert values["confidence"] == 0.82
    assert values["metadata_payload"] == {"source": "unit-test"}


def test_agent_intelligence_serializer_round_trips_recommendation_record() -> None:
    model = AgentRecommendationModel(
        **AgentIntelligencePersistenceSerializer.recommendation_values(
            _recommendation()
        )
    )

    record = AgentIntelligencePersistenceSerializer.recommendation_from_model(model)

    assert record.agent_recommendation_id == "agent-recommendation-1"
    assert record.agent_signal_id == "agent-signal-1"
    assert record.symbol == "QQQ"
    assert record.rationale_text == _FULL_TEXT.strip()
    assert record.full_llm_response == _FULL_LLM_RESPONSE.strip()
    assert record.supporting_signals[0].record_id == "agent-signal-1"
    assert record.lineage.workflow_name == "morning_report"


def test_agent_intelligence_serializer_flattens_risk_assessment_record() -> None:
    record = _risk_assessment()

    values = AgentIntelligencePersistenceSerializer.risk_assessment_values(record)

    assert values["risk_assessment_id"] == "agent-risk-assessment-1"
    assert values["agent_signal_id"] == "agent-signal-1"
    assert values["risk_type"] == "drawdown"
    assert values["assessment_text"] == _FULL_TEXT.strip()
    assert values["mitigation"] == _FULL_TEXT.strip()
    assert values["full_llm_response"] == _FULL_LLM_RESPONSE.strip()
    assert values["supporting_signals"] == [
        {"record_type": "agent_signal", "record_id": "agent-signal-1"},
    ]
    assert values["risk_score"] == 0.35
    assert values["metadata_payload"] == {"source": "unit-test"}


def test_agent_intelligence_serializer_round_trips_risk_assessment_record() -> None:
    model = AgentRiskAssessmentModel(
        **AgentIntelligencePersistenceSerializer.risk_assessment_values(
            _risk_assessment()
        )
    )

    record = AgentIntelligencePersistenceSerializer.risk_assessment_from_model(model)

    assert record.risk_assessment_id == "agent-risk-assessment-1"
    assert record.agent_signal_id == "agent-signal-1"
    assert record.symbol == "SPY"
    assert record.assessment_text == _FULL_TEXT.strip()
    assert record.mitigation == _FULL_TEXT.strip()
    assert record.full_llm_response == _FULL_LLM_RESPONSE.strip()
    assert record.supporting_signals[0].record_type == "agent_signal"
    assert record.lineage.execution_id == "exec-1"


def _reasoning() -> AgentReasoningRecord:
    return AgentReasoningRecord(
        reasoning_id="agent-reasoning-1",
        agent_signal_id="agent-signal-1",
        agent_name="TechnicalAgent",
        agent_type="technical",
        timestamp=_timestamp(),
        reasoning_text=_FULL_TEXT,
        lineage=_lineage(),
        symbol="spy",
        universe="us_equities",
        reasoning_type="signal_interpretation",
        model_name="gpt-test",
        prompt_version="technical-v1",
        full_llm_response=_FULL_LLM_RESPONSE,
        inputs={"lookback_days": 20},
        outputs={"trend": "bullish"},
        linked_records=(_agent_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _recommendation() -> AgentRecommendationRecord:
    return AgentRecommendationRecord(
        agent_recommendation_id="agent-recommendation-1",
        agent_signal_id="agent-signal-1",
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        timestamp=_timestamp(),
        recommendation_type="portfolio_posture",
        recommendation_text="Maintain moderate risk-on posture.",
        lineage=_lineage(),
        symbol="qqq",
        universe="us_equities",
        bias="bullish",
        action="hold",
        confidence=0.82,
        conviction=0.7,
        time_horizon="swing",
        rationale_text=_FULL_TEXT,
        full_llm_response=_FULL_LLM_RESPONSE,
        supporting_signals=(_agent_signal_identity(),),
        inputs={"risk_regime": "moderate"},
        outputs={"posture": "risk_on"},
        metadata={"source": "unit-test"},
    )


def _risk_assessment() -> AgentRiskAssessmentRecord:
    return AgentRiskAssessmentRecord(
        risk_assessment_id="agent-risk-assessment-1",
        agent_signal_id="agent-signal-1",
        agent_name="DrawdownRiskAgent",
        agent_type="risk",
        timestamp=_timestamp(),
        risk_type="drawdown",
        assessment_text=_FULL_TEXT,
        lineage=_lineage(),
        symbol="spy",
        universe="us_equities",
        risk_level="moderate",
        risk_score=0.35,
        confidence=0.76,
        mitigation=_FULL_TEXT,
        full_llm_response=_FULL_LLM_RESPONSE,
        inputs={"max_drawdown": 0.08},
        outputs={"risk_level": "moderate"},
        supporting_signals=(_agent_signal_identity(),),
        metadata={"source": "unit-test"},
    )


def _agent_signal_identity() -> PersistenceRecordIdentity:
    return PersistenceRecordIdentity(
        record_type="agent_signal",
        record_id="agent-signal-1",
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_node",
    )


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)
