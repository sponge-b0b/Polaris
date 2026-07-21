from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceBundle,
    AgentIntelligencePersistenceResult,
    AgentReasoningRecord,
    AgentRecommendationRecord,
    AgentRiskAssessmentRecord,
    new_agent_reasoning_id,
    new_agent_recommendation_id,
    new_agent_risk_assessment_id,
)
from core.storage.persistence.lineage import (
    PersistenceLineage,
    PersistenceRecordIdentity,
)
from domain.llm import ReasoningTraceViolationError

_TIMESTAMP = datetime(2026, 5, 31, 14, 0, tzinfo=UTC)
_AGENT_SIGNAL_ID = "agent-signal-1"
_FULL_REASONING_TEXT = "Full reasoning paragraph. " * 200
_FULL_LLM_RESPONSE = "Full model response token stream. " * 250


def test_agent_reasoning_record_is_typed_immutable_and_preserves_full_text() -> None:
    record = _reasoning_record()

    assert record.agent_signal_id == _AGENT_SIGNAL_ID
    assert record.symbol == "SPY"
    assert record.universe == "us_equities"
    assert record.reasoning_text == _FULL_REASONING_TEXT.strip()
    assert record.full_llm_response == _FULL_LLM_RESPONSE.strip()
    assert len(record.reasoning_text) == len(_FULL_REASONING_TEXT.strip())
    assert len(record.full_llm_response or "") == len(_FULL_LLM_RESPONSE.strip())
    assert record.linked_records == (
        PersistenceRecordIdentity(
            record_type="agent_signal",
            record_id=_AGENT_SIGNAL_ID,
        ),
    )

    with pytest.raises(FrozenInstanceError):
        record.agent_name = "ChangedAgent"  # type: ignore[misc]


def test_agent_recommendation_record_validates_and_preserves_full_rationale() -> None:
    full_rationale = "Recommendation rationale with detailed evidence. " * 150
    record = AgentRecommendationRecord(
        agent_recommendation_id="agent-recommendation-1",
        agent_signal_id=_AGENT_SIGNAL_ID,
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        timestamp=_TIMESTAMP,
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
        rationale_text=full_rationale,
        full_llm_response=_FULL_LLM_RESPONSE,
        supporting_signals=(
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id=_AGENT_SIGNAL_ID,
            ),
        ),
    )

    assert record.agent_signal_id == _AGENT_SIGNAL_ID
    assert record.symbol == "QQQ"
    assert record.confidence == 0.82
    assert record.conviction == 0.7
    assert record.rationale_text == full_rationale.strip()
    assert len(record.rationale_text or "") == len(full_rationale.strip())
    assert record.full_llm_response == _FULL_LLM_RESPONSE.strip()


def test_agent_risk_assessment_record_validates_scores_and_preserves_text() -> None:
    full_assessment = "Risk assessment with full scenario details. " * 175
    mitigation = "Reduce gross exposure if volatility expansion confirms. " * 80
    record = AgentRiskAssessmentRecord(
        risk_assessment_id="agent-risk-assessment-1",
        agent_signal_id=_AGENT_SIGNAL_ID,
        agent_name="DrawdownRiskAgent",
        agent_type="risk",
        timestamp=_TIMESTAMP,
        risk_type="drawdown",
        assessment_text=full_assessment,
        lineage=_lineage(),
        symbol="spy",
        universe="us_equities",
        risk_level="moderate",
        risk_score=0.35,
        confidence=0.76,
        mitigation=mitigation,
        full_llm_response=_FULL_LLM_RESPONSE,
        supporting_signals=(
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id=_AGENT_SIGNAL_ID,
            ),
        ),
    )

    assert record.agent_signal_id == _AGENT_SIGNAL_ID
    assert record.symbol == "SPY"
    assert record.risk_score == 0.35
    assert record.confidence == 0.76
    assert record.assessment_text == full_assessment.strip()
    assert record.mitigation == mitigation.strip()
    assert len(record.assessment_text) == len(full_assessment.strip())
    assert record.full_llm_response == _FULL_LLM_RESPONSE.strip()


def test_agent_intelligence_records_sanitize_traces_before_persistence() -> None:
    reasoning = AgentReasoningRecord(
        reasoning_id="agent-reasoning-1",
        agent_signal_id=_AGENT_SIGNAL_ID,
        agent_name="TechnicalAgent",
        agent_type="technical",
        timestamp=_TIMESTAMP,
        reasoning_text="<think>private reasoning</think>\nVisible reasoning.",
        full_llm_response="```reasoning\nprivate response\n```\nVisible response.",
        outputs={
            "chain_of_thought": "private output reasoning",
            "summary": "visible output",
        },
        metadata={
            "scratchpad": "private metadata reasoning",
            "source": "unit-test",
        },
    )
    recommendation = AgentRecommendationRecord(
        agent_recommendation_id="agent-recommendation-1",
        agent_signal_id=_AGENT_SIGNAL_ID,
        agent_name="StrategySynthesisAgent",
        agent_type="strategy",
        timestamp=_TIMESTAMP,
        recommendation_type="portfolio_posture",
        recommendation_text=(
            "<thinking>private rec reasoning</thinking>\nHold exposure."
        ),
        rationale_text="```scratchpad\nprivate rationale\n```\nVisible rationale.",
    )
    risk = AgentRiskAssessmentRecord(
        risk_assessment_id="agent-risk-assessment-1",
        agent_signal_id=_AGENT_SIGNAL_ID,
        agent_name="DrawdownRiskAgent",
        agent_type="risk",
        timestamp=_TIMESTAMP,
        risk_type="drawdown",
        assessment_text=(
            "<reasoning>private risk reasoning</reasoning>\nModerate drawdown risk."
        ),
        mitigation="Chain of thought: private mitigation reasoning.\n"
        "Final answer: Reduce gross exposure on confirmation.",
    )

    assert reasoning.reasoning_text == "Visible reasoning."
    assert reasoning.full_llm_response == "Visible response."
    assert reasoning.outputs == {"summary": "visible output"}
    assert reasoning.metadata == {"source": "unit-test"}
    assert recommendation.recommendation_text == "Hold exposure."
    assert recommendation.rationale_text == "Visible rationale."
    assert risk.assessment_text == "Moderate drawdown risk."
    assert risk.mitigation == "Reduce gross exposure on confirmation."
    assert "private" not in str(reasoning)
    assert "private" not in str(recommendation)
    assert "private" not in str(risk)


def test_agent_intelligence_records_fail_closed_on_unsafe_reasoning_trace() -> None:
    with pytest.raises(ReasoningTraceViolationError) as exc_info:
        AgentReasoningRecord(
            reasoning_id="agent-reasoning-1",
            agent_signal_id=_AGENT_SIGNAL_ID,
            agent_name="TechnicalAgent",
            agent_type="technical",
            timestamp=_TIMESTAMP,
            reasoning_text="<think>hidden reasoning without a close tag",
        )

    message = str(exc_info.value)
    assert "AgentReasoningRecord.reasoning_text" in message
    assert "hidden reasoning" not in message


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("reasoning_id", {"reasoning_id": " "}),
        ("agent_signal_id", {"agent_signal_id": ""}),
        ("reasoning_text", {"reasoning_text": " "}),
    ],
)
def test_agent_reasoning_record_validates_required_fields(
    field_name: str,
    kwargs: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "reasoning_id": "agent-reasoning-1",
        "agent_signal_id": _AGENT_SIGNAL_ID,
        "agent_name": "TechnicalAgent",
        "agent_type": "technical",
        "timestamp": _TIMESTAMP,
        "reasoning_text": "Full reasoning.",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=field_name):
        AgentReasoningRecord(**values)  # type: ignore[arg-type]


def test_agent_recommendation_record_validates_ratio_fields() -> None:
    with pytest.raises(ValueError, match="confidence"):
        AgentRecommendationRecord(
            agent_recommendation_id="agent-recommendation-1",
            agent_signal_id=_AGENT_SIGNAL_ID,
            agent_name="PortfolioManagerAgent",
            agent_type="portfolio",
            timestamp=_TIMESTAMP,
            recommendation_type="allocation",
            recommendation_text="Increase cash reserve.",
            confidence=1.2,
        )

    with pytest.raises(ValueError, match="conviction"):
        AgentRecommendationRecord(
            agent_recommendation_id="agent-recommendation-1",
            agent_signal_id=_AGENT_SIGNAL_ID,
            agent_name="PortfolioManagerAgent",
            agent_type="portfolio",
            timestamp=_TIMESTAMP,
            recommendation_type="allocation",
            recommendation_text="Increase cash reserve.",
            conviction=-0.1,
        )


def test_agent_risk_assessment_record_validates_ratio_fields() -> None:
    with pytest.raises(ValueError, match="risk_score"):
        AgentRiskAssessmentRecord(
            risk_assessment_id="agent-risk-assessment-1",
            agent_signal_id=_AGENT_SIGNAL_ID,
            agent_name="VolatilityRiskAgent",
            agent_type="risk",
            timestamp=_TIMESTAMP,
            risk_type="volatility",
            assessment_text="Volatility is elevated.",
            risk_score=-0.1,
        )

    with pytest.raises(ValueError, match="confidence"):
        AgentRiskAssessmentRecord(
            risk_assessment_id="agent-risk-assessment-1",
            agent_signal_id=_AGENT_SIGNAL_ID,
            agent_name="VolatilityRiskAgent",
            agent_type="risk",
            timestamp=_TIMESTAMP,
            risk_type="volatility",
            assessment_text="Volatility is elevated.",
            confidence=1.1,
        )


def test_agent_intelligence_persistence_result_validates_state() -> None:
    success = AgentIntelligencePersistenceResult.succeeded(
        primary_record_id="agent-reasoning-1",
        records_persisted=3,
    )
    failure = AgentIntelligencePersistenceResult.failed(
        "database unavailable",
    )

    assert success.success is True
    assert success.records_persisted == 3
    assert success.primary_record_id == "agent-reasoning-1"
    assert failure.success is False
    assert failure.error == "database unavailable"

    with pytest.raises(ValueError, match="records_persisted"):
        AgentIntelligencePersistenceResult(
            success=True,
            records_persisted=-1,
            primary_record_id="agent-reasoning-1",
        )

    with pytest.raises(ValueError, match="successful"):
        AgentIntelligencePersistenceResult(
            success=True,
            primary_record_id="agent-reasoning-1",
            error="unexpected",
        )

    with pytest.raises(ValueError, match="primary_record_id"):
        AgentIntelligencePersistenceResult(
            success=True,
        )

    with pytest.raises(ValueError, match="error"):
        AgentIntelligencePersistenceResult.failed(
            " ",
        )


def test_agent_intelligence_ids_are_stable() -> None:
    assert (
        new_agent_reasoning_id(
            agent_signal_id=_AGENT_SIGNAL_ID,
            timestamp=_TIMESTAMP,
            reasoning_key="chain-of-thought-summary",
        )
        == "agent_reasoning:agent-signal-1:"
        "2026-05-31T14:00:00+00:00:chain-of-thought-summary"
    )
    assert (
        new_agent_recommendation_id(
            agent_signal_id=_AGENT_SIGNAL_ID,
            timestamp=_TIMESTAMP,
            recommendation_key="primary",
        )
        == "agent_recommendation:agent-signal-1:2026-05-31T14:00:00+00:00:primary"
    )
    assert (
        new_agent_risk_assessment_id(
            agent_signal_id=_AGENT_SIGNAL_ID,
            timestamp=_TIMESTAMP,
            risk_key="drawdown",
        )
        == "agent_risk_assessment:agent-signal-1:2026-05-31T14:00:00+00:00:drawdown"
    )


def test_bundle_groups_enriched_intelligence_records() -> None:
    bundle = AgentIntelligencePersistenceBundle(
        reasoning=(_reasoning_record(),),
        recommendations=(
            AgentRecommendationRecord(
                agent_recommendation_id="agent-recommendation-1",
                agent_signal_id=_AGENT_SIGNAL_ID,
                agent_name="StrategySynthesisAgent",
                agent_type="strategy",
                timestamp=_TIMESTAMP,
                recommendation_type="portfolio_posture",
                recommendation_text="Maintain moderate risk-on posture.",
            ),
        ),
        risk_assessments=(
            AgentRiskAssessmentRecord(
                risk_assessment_id="agent-risk-assessment-1",
                agent_signal_id=_AGENT_SIGNAL_ID,
                agent_name="DrawdownRiskAgent",
                agent_type="risk",
                timestamp=_TIMESTAMP,
                risk_type="drawdown",
                assessment_text="Drawdown risk is moderate.",
            ),
        ),
    )

    assert len(bundle.reasoning) == 1
    assert len(bundle.recommendations) == 1
    assert len(bundle.risk_assessments) == 1


def _reasoning_record() -> AgentReasoningRecord:
    return AgentReasoningRecord(
        reasoning_id="agent-reasoning-1",
        agent_signal_id=_AGENT_SIGNAL_ID,
        agent_name="TechnicalAgent",
        agent_type="technical",
        timestamp=_TIMESTAMP,
        reasoning_text=_FULL_REASONING_TEXT,
        lineage=_lineage(),
        symbol="spy",
        universe="us_equities",
        reasoning_type="signal_interpretation",
        model_name="gpt-test",
        prompt_version="technical-v1",
        full_llm_response=_FULL_LLM_RESPONSE,
        inputs={"lookback_days": 20},
        outputs={"trend": "bullish"},
        linked_records=(
            PersistenceRecordIdentity(
                record_type="agent_signal",
                record_id=_AGENT_SIGNAL_ID,
            ),
        ),
        metadata={"source": "unit-test"},
    )


def _lineage() -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_node",
    )
