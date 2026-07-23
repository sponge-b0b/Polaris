from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

import pytest

from application.persistence.agent_intelligence import (
    AgentIntelligencePersistenceService,
    AgentReasoningPersistenceFilters,
    AgentRecommendationPersistenceFilters,
    AgentRiskAssessmentPersistenceFilters,
)
from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceBundle,
    AgentIntelligencePersistenceResult,
    AgentReasoningRecord,
    AgentRecommendationRecord,
    AgentRiskAssessmentRecord,
)
from core.storage.persistence.lineage import (
    PersistenceLineage,
    PersistenceRecordIdentity,
)


class FakeAgentIntelligenceRepository:
    def __init__(
        self,
        *,
        reasoning: Sequence[AgentReasoningRecord] = (),
        recommendations: Sequence[AgentRecommendationRecord] = (),
        risk_assessments: Sequence[AgentRiskAssessmentRecord] = (),
    ) -> None:
        self.bundle: AgentIntelligencePersistenceBundle | None = None
        self.reasoning_records = tuple(reasoning)
        self.recommendation_records = tuple(recommendations)
        self.risk_assessment_records = tuple(risk_assessments)
        self.reasoning_filters: dict[str, str | datetime | None] | None = None
        self.recommendation_filters: dict[str, str | datetime | None] | None = None
        self.risk_assessment_filters: dict[str, str | datetime | None] | None = None
        self.persisted_reasoning: AgentReasoningRecord | None = None
        self.persisted_recommendation: AgentRecommendationRecord | None = None
        self.persisted_risk_assessment: AgentRiskAssessmentRecord | None = None
        self.reasoning_id: str | None = None
        self.agent_recommendation_id: str | None = None
        self.risk_assessment_id: str | None = None

    async def persist_intelligence_bundle(
        self,
        bundle: AgentIntelligencePersistenceBundle,
    ) -> AgentIntelligencePersistenceResult:
        self.bundle = bundle
        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=_primary_record_id(bundle),
            records_persisted=(
                len(bundle.reasoning)
                + len(bundle.recommendations)
                + len(bundle.risk_assessments)
            ),
        )

    async def persist_reasoning(
        self,
        reasoning: AgentReasoningRecord,
    ) -> AgentIntelligencePersistenceResult:
        self.persisted_reasoning = reasoning
        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=reasoning.reasoning_id,
        )

    async def persist_recommendation(
        self,
        recommendation: AgentRecommendationRecord,
    ) -> AgentIntelligencePersistenceResult:
        self.persisted_recommendation = recommendation
        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=recommendation.agent_recommendation_id,
        )

    async def persist_risk_assessment(
        self,
        risk_assessment: AgentRiskAssessmentRecord,
    ) -> AgentIntelligencePersistenceResult:
        self.persisted_risk_assessment = risk_assessment
        return AgentIntelligencePersistenceResult.succeeded(
            primary_record_id=risk_assessment.risk_assessment_id,
        )

    async def get_reasoning(
        self,
        reasoning_id: str,
    ) -> AgentReasoningRecord | None:
        self.reasoning_id = reasoning_id
        return self.reasoning_records[0] if self.reasoning_records else None

    async def get_recommendation(
        self,
        agent_recommendation_id: str,
    ) -> AgentRecommendationRecord | None:
        self.agent_recommendation_id = agent_recommendation_id
        return self.recommendation_records[0] if self.recommendation_records else None

    async def get_risk_assessment(
        self,
        risk_assessment_id: str,
    ) -> AgentRiskAssessmentRecord | None:
        self.risk_assessment_id = risk_assessment_id
        return self.risk_assessment_records[0] if self.risk_assessment_records else None

    async def list_reasoning(
        self,
        *,
        agent_signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentReasoningRecord]:
        self.reasoning_filters = _filters_dict(
            agent_signal_id=agent_signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        )
        return self.reasoning_records

    async def list_recommendations(
        self,
        *,
        agent_signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentRecommendationRecord]:
        self.recommendation_filters = _filters_dict(
            agent_signal_id=agent_signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        )
        return self.recommendation_records

    async def list_risk_assessments(
        self,
        *,
        agent_signal_id: str | None = None,
        workflow_name: str | None = None,
        execution_id: str | None = None,
        agent_name: str | None = None,
        agent_type: str | None = None,
        symbol: str | None = None,
        universe: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[AgentRiskAssessmentRecord]:
        self.risk_assessment_filters = _filters_dict(
            agent_signal_id=agent_signal_id,
            workflow_name=workflow_name,
            execution_id=execution_id,
            agent_name=agent_name,
            agent_type=agent_type,
            symbol=symbol,
            universe=universe,
            start=start,
            end=end,
        )
        return self.risk_assessment_records


@pytest.mark.asyncio
async def test_agent_intelligence_persistence_service_persists_existing_bundle() -> (
    None
):
    repository = FakeAgentIntelligenceRepository()
    service = AgentIntelligencePersistenceService(repository)
    bundle = _bundle()

    result = await service.persist_bundle(bundle)

    assert result.success is True
    assert result.records_persisted == 3
    assert repository.bundle == bundle


@pytest.mark.asyncio
async def test_agent_intelligence_persistence_service_builds_typed_bundle() -> None:
    repository = FakeAgentIntelligenceRepository()
    service = AgentIntelligencePersistenceService(repository)

    result = await service.persist_records(
        reasoning=(_reasoning(),),
        recommendations=(_recommendation(),),
        risk_assessments=(_risk_assessment(),),
    )

    assert result.success is True
    assert repository.bundle is not None
    assert repository.bundle.reasoning[0].agent_signal_id == "agent-signal-1"
    assert repository.bundle.recommendations[0].rationale_text == _full_text()
    assert (
        repository.bundle.risk_assessments[0].full_llm_response == _full_llm_response()
    )


@pytest.mark.asyncio
async def test_agent_intelligence_persistence_service_delegates_individual_persist_methods() -> (  # noqa: E501 - descriptive pytest node id
    None
):
    repository = FakeAgentIntelligenceRepository()
    service = AgentIntelligencePersistenceService(repository)

    reasoning_result = await service.persist_reasoning(_reasoning())
    recommendation_result = await service.persist_recommendation(_recommendation())
    risk_result = await service.persist_risk_assessment(_risk_assessment())

    assert reasoning_result.primary_record_id == "agent-reasoning-1"
    assert recommendation_result.primary_record_id == "agent-recommendation-1"
    assert risk_result.primary_record_id == "agent-risk-assessment-1"
    assert repository.persisted_reasoning is not None
    assert repository.persisted_recommendation is not None
    assert repository.persisted_risk_assessment is not None


@pytest.mark.asyncio
async def test_agent_intelligence_persistence_service_delegates_get_methods() -> None:
    repository = FakeAgentIntelligenceRepository(
        reasoning=(_reasoning(),),
        recommendations=(_recommendation(),),
        risk_assessments=(_risk_assessment(),),
    )
    service = AgentIntelligencePersistenceService(repository)

    reasoning = await service.get_reasoning("agent-reasoning-1")
    recommendation = await service.get_recommendation("agent-recommendation-1")
    risk_assessment = await service.get_risk_assessment("agent-risk-assessment-1")

    assert reasoning is not None
    assert recommendation is not None
    assert risk_assessment is not None
    assert repository.reasoning_id == "agent-reasoning-1"
    assert repository.agent_recommendation_id == "agent-recommendation-1"
    assert repository.risk_assessment_id == "agent-risk-assessment-1"


@pytest.mark.asyncio
async def test_agent_intelligence_persistence_service_uses_typed_filters() -> None:
    repository = FakeAgentIntelligenceRepository(
        reasoning=(_reasoning(),),
        recommendations=(_recommendation(),),
        risk_assessments=(_risk_assessment(),),
    )
    service = AgentIntelligencePersistenceService(repository)
    start = _timestamp()
    end = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)

    reasoning = await service.list_reasoning(
        AgentReasoningPersistenceFilters(
            agent_signal_id=" agent-signal-1 ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            agent_name=" TechnicalAgent ",
            agent_type=" technical ",
            symbol=" spy ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )
    recommendations = await service.list_recommendations(
        AgentRecommendationPersistenceFilters(
            agent_signal_id=" agent-signal-1 ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            agent_name=" StrategySynthesisAgent ",
            agent_type=" strategy ",
            symbol=" qqq ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )
    risk_assessments = await service.list_risk_assessments(
        AgentRiskAssessmentPersistenceFilters(
            agent_signal_id=" agent-signal-1 ",
            workflow_name=" morning_report ",
            execution_id=" exec-1 ",
            agent_name=" DrawdownRiskAgent ",
            agent_type=" risk ",
            symbol=" spy ",
            universe=" us_equities ",
            start=start,
            end=end,
        )
    )

    assert len(reasoning) == 1
    assert len(recommendations) == 1
    assert len(risk_assessments) == 1
    assert repository.reasoning_filters == {
        "agent_signal_id": "agent-signal-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "agent_name": "TechnicalAgent",
        "agent_type": "technical",
        "symbol": "SPY",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }
    assert repository.recommendation_filters == {
        "agent_signal_id": "agent-signal-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "agent_name": "StrategySynthesisAgent",
        "agent_type": "strategy",
        "symbol": "QQQ",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }
    assert repository.risk_assessment_filters == {
        "agent_signal_id": "agent-signal-1",
        "workflow_name": "morning_report",
        "execution_id": "exec-1",
        "agent_name": "DrawdownRiskAgent",
        "agent_type": "risk",
        "symbol": "SPY",
        "universe": "us_equities",
        "start": start,
        "end": end,
    }


@pytest.mark.asyncio
async def test_agent_intelligence_persistence_service_uses_default_filters() -> None:
    repository = FakeAgentIntelligenceRepository(
        reasoning=(_reasoning(),),
        recommendations=(_recommendation(),),
        risk_assessments=(_risk_assessment(),),
    )
    service = AgentIntelligencePersistenceService(repository)

    reasoning = await service.list_reasoning()
    recommendations = await service.list_recommendations()
    risk_assessments = await service.list_risk_assessments()

    assert len(reasoning) == 1
    assert len(recommendations) == 1
    assert len(risk_assessments) == 1
    assert repository.reasoning_filters == _empty_filters()
    assert repository.recommendation_filters == _empty_filters()
    assert repository.risk_assessment_filters == _empty_filters()


@pytest.mark.parametrize(
    "filters",
    [
        AgentReasoningPersistenceFilters,
        AgentRecommendationPersistenceFilters,
        AgentRiskAssessmentPersistenceFilters,
    ],
)
def test_agent_intelligence_time_window_filters_require_ordered_bounds(
    filters: type[
        AgentReasoningPersistenceFilters
        | AgentRecommendationPersistenceFilters
        | AgentRiskAssessmentPersistenceFilters
    ],
) -> None:
    start = datetime(2026, 5, 31, 15, 0, tzinfo=UTC)
    end = _timestamp()

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        filters(
            start=start,
            end=end,
        )


def _bundle() -> AgentIntelligencePersistenceBundle:
    return AgentIntelligencePersistenceBundle(
        reasoning=(_reasoning(),),
        recommendations=(_recommendation(),),
        risk_assessments=(_risk_assessment(),),
    )


def _reasoning() -> AgentReasoningRecord:
    return AgentReasoningRecord(
        reasoning_id="agent-reasoning-1",
        agent_signal_id="agent-signal-1",
        agent_name="TechnicalAgent",
        agent_type="technical",
        timestamp=_timestamp(),
        reasoning_text=_full_text(),
        lineage=_lineage(),
        symbol="spy",
        universe="us_equities",
        reasoning_type="signal_interpretation",
        model_name="gpt-test",
        prompt_version="technical-v1",
        full_llm_response=_full_llm_response(),
        inputs={"lookback_days": 20},
        outputs={"trend": "bullish"},
        linked_records=(_identity(),),
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
        rationale_text=_full_text(),
        full_llm_response=_full_llm_response(),
        supporting_signals=(_identity(),),
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
        assessment_text=_full_text(),
        lineage=_lineage(),
        symbol="spy",
        universe="us_equities",
        risk_level="moderate",
        risk_score=0.35,
        confidence=0.76,
        mitigation=_full_text(),
        full_llm_response=_full_llm_response(),
        inputs={"max_drawdown": 0.08},
        outputs={"risk_level": "moderate"},
        supporting_signals=(_identity(),),
        metadata={"source": "unit-test"},
    )


def _identity() -> PersistenceRecordIdentity:
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


def _filters_dict(
    *,
    agent_signal_id: str | None,
    workflow_name: str | None,
    execution_id: str | None,
    agent_name: str | None,
    agent_type: str | None,
    symbol: str | None,
    universe: str | None,
    start: datetime | None,
    end: datetime | None,
) -> dict[str, str | datetime | None]:
    return {
        "agent_signal_id": agent_signal_id,
        "workflow_name": workflow_name,
        "execution_id": execution_id,
        "agent_name": agent_name,
        "agent_type": agent_type,
        "symbol": symbol,
        "universe": universe,
        "start": start,
        "end": end,
    }


def _empty_filters() -> dict[str, str | datetime | None]:
    return _filters_dict(
        agent_signal_id=None,
        workflow_name=None,
        execution_id=None,
        agent_name=None,
        agent_type=None,
        symbol=None,
        universe=None,
        start=None,
        end=None,
    )


def _primary_record_id(
    bundle: AgentIntelligencePersistenceBundle,
) -> str:
    if bundle.reasoning:
        return bundle.reasoning[0].reasoning_id
    if bundle.recommendations:
        return bundle.recommendations[0].agent_recommendation_id
    if bundle.risk_assessments:
        return bundle.risk_assessments[0].risk_assessment_id
    return "empty-agent-intelligence-persistence-bundle"


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=UTC)


def _full_text() -> str:
    return ("Full text must not be truncated. " * 200).strip()


def _full_llm_response() -> str:
    return ("Full LLM response must not be truncated. " * 250).strip()
