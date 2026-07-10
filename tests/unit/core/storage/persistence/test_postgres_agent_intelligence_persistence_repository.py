from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_intelligence import AgentRecommendationModel
from core.database.models.agent_intelligence import AgentRiskAssessmentModel
from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceBundle,
)
from core.storage.persistence.agent_intelligence import AgentReasoningRecord
from core.storage.persistence.agent_intelligence import AgentRecommendationRecord
from core.storage.persistence.agent_intelligence import AgentRiskAssessmentRecord
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity
from core.storage.persistence.repositories.postgres_agent_intelligence_persistence_repository import (
    PostgresAgentIntelligencePersistenceRepository,
)
from core.storage.persistence.serializers.agent_intelligence_persistence_serializer import (
    AgentIntelligencePersistenceSerializer,
)


class FakeScalarResult:
    def __init__(
        self,
        rows: Sequence[object],
    ) -> None:
        self._rows = list(rows)

    def all(
        self,
    ) -> list[object]:
        return self._rows


class FakeExecuteResult:
    def __init__(
        self,
        rows: Sequence[object] | None = None,
    ) -> None:
        self._rows = list(rows or [])

    def scalar_one_or_none(
        self,
    ) -> object | None:
        if not self._rows:
            return None

        return self._rows[0]

    def scalars(
        self,
    ) -> FakeScalarResult:
        return FakeScalarResult(
            self._rows,
        )


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

    async def execute(
        self,
        statement: Any,
    ) -> FakeExecuteResult:
        self.executed.append(statement)

        if self.error is not None:
            raise self.error

        return self.result

    async def commit(
        self,
    ) -> None:
        self.commits += 1

    async def rollback(
        self,
    ) -> None:
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_persist_intelligence_bundle_upserts_enriched_signal_records() -> None:
    session = FakeAsyncSession()
    repository = PostgresAgentIntelligencePersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_intelligence_bundle(_bundle())

    compiled = [
        str(statement.compile(dialect=postgresql.dialect()))
        for statement in session.executed
    ]

    assert result.success is True
    assert result.primary_record_id == "agent-reasoning-1"
    assert result.records_persisted == 3
    assert session.commits == 1
    assert len(session.executed) == 3
    assert "agent_reasoning" in compiled[0]
    assert "ON CONFLICT" in compiled[0]
    assert "agent_signal_id" in compiled[0]
    assert "agent_recommendations" in compiled[1]
    assert "ON CONFLICT" in compiled[1]
    assert "agent_risk_assessments" in compiled[2]
    assert "ON CONFLICT" in compiled[2]


@pytest.mark.asyncio
async def test_persist_reasoning_rolls_back_on_sqlalchemy_error() -> None:
    session = FakeAsyncSession(error=SQLAlchemyError("database unavailable"))
    repository = PostgresAgentIntelligencePersistenceRepository(
        cast(AsyncSession, session),
    )

    result = await repository.persist_reasoning(_reasoning())

    assert result.success is False
    assert result.error is not None
    assert session.commits == 0
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_get_reasoning_returns_typed_record() -> None:
    model = AgentReasoningModel(
        **AgentIntelligencePersistenceSerializer.reasoning_values(_reasoning())
    )
    repository = PostgresAgentIntelligencePersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([model])))
    )

    record = await repository.get_reasoning("agent-reasoning-1")

    assert record is not None
    assert record.reasoning_id == "agent-reasoning-1"
    assert record.agent_signal_id == "agent-signal-1"
    assert record.full_llm_response == _full_llm_response()
    assert record.linked_records[0].record_type == "agent_signal"


@pytest.mark.asyncio
async def test_get_recommendation_returns_typed_record() -> None:
    model = AgentRecommendationModel(
        **AgentIntelligencePersistenceSerializer.recommendation_values(
            _recommendation()
        )
    )
    repository = PostgresAgentIntelligencePersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([model])))
    )

    record = await repository.get_recommendation("agent-recommendation-1")

    assert record is not None
    assert record.agent_recommendation_id == "agent-recommendation-1"
    assert record.agent_signal_id == "agent-signal-1"
    assert record.rationale_text == _full_text()
    assert record.supporting_signals[0].record_id == "agent-signal-1"


@pytest.mark.asyncio
async def test_get_risk_assessment_returns_typed_record() -> None:
    model = AgentRiskAssessmentModel(
        **AgentIntelligencePersistenceSerializer.risk_assessment_values(
            _risk_assessment()
        )
    )
    repository = PostgresAgentIntelligencePersistenceRepository(
        cast(AsyncSession, FakeAsyncSession(result=FakeExecuteResult([model])))
    )

    record = await repository.get_risk_assessment("agent-risk-assessment-1")

    assert record is not None
    assert record.risk_assessment_id == "agent-risk-assessment-1"
    assert record.agent_signal_id == "agent-signal-1"
    assert record.assessment_text == _full_text()
    assert record.full_llm_response == _full_llm_response()


@pytest.mark.asyncio
async def test_list_methods_return_ordered_typed_records_with_common_filters() -> None:
    reasoning_model = AgentReasoningModel(
        **AgentIntelligencePersistenceSerializer.reasoning_values(_reasoning())
    )
    recommendation_model = AgentRecommendationModel(
        **AgentIntelligencePersistenceSerializer.recommendation_values(
            _recommendation()
        )
    )
    risk_model = AgentRiskAssessmentModel(
        **AgentIntelligencePersistenceSerializer.risk_assessment_values(
            _risk_assessment()
        )
    )

    reasoning = await PostgresAgentIntelligencePersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([reasoning_model])),
        )
    ).list_reasoning(
        agent_signal_id="agent-signal-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        agent_name="TechnicalAgent",
        agent_type="technical",
        symbol="spy",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )
    recommendations = await PostgresAgentIntelligencePersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([recommendation_model])),
        )
    ).list_recommendations(
        agent_signal_id="agent-signal-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        agent_name="TechnicalAgent",
        agent_type="technical",
        symbol="spy",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )
    risk_assessments = await PostgresAgentIntelligencePersistenceRepository(
        cast(
            AsyncSession,
            FakeAsyncSession(result=FakeExecuteResult([risk_model])),
        )
    ).list_risk_assessments(
        agent_signal_id="agent-signal-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        agent_name="TechnicalAgent",
        agent_type="technical",
        symbol="spy",
        universe="us_equities",
        start=_timestamp(),
        end=_timestamp(),
    )

    assert reasoning[0].reasoning_id == "agent-reasoning-1"
    assert recommendations[0].agent_recommendation_id == "agent-recommendation-1"
    assert risk_assessments[0].risk_assessment_id == "agent-risk-assessment-1"


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


def _timestamp() -> datetime:
    return datetime(2026, 5, 31, 14, 0, tzinfo=timezone.utc)


def _full_text() -> str:
    return ("Full text must not be truncated. " * 200).strip()


def _full_llm_response() -> str:
    return ("Full LLM response must not be truncated. " * 250).strip()
