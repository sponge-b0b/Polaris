from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.agent_intelligence.agent_intelligence_persistence_models import (  # noqa: E501
    AgentIntelligencePersistenceBundle,
    AgentIntelligencePersistenceResult,
    AgentReasoningRecord,
    AgentRecommendationRecord,
    AgentRiskAssessmentRecord,
)


class AgentIntelligencePersistenceRepository(Protocol):
    """
    Async repository contract for enriched durable agent intelligence records.

    Agent signals remain the primary signal table. These records enrich those
    primary signals with full reasoning, recommendation, and risk-assessment
    audit trails linked by ``agent_signal_id``.
    """

    async def persist_intelligence_bundle(
        self,
        bundle: AgentIntelligencePersistenceBundle,
    ) -> AgentIntelligencePersistenceResult: ...

    async def persist_reasoning(
        self,
        reasoning: AgentReasoningRecord,
    ) -> AgentIntelligencePersistenceResult: ...

    async def persist_recommendation(
        self,
        recommendation: AgentRecommendationRecord,
    ) -> AgentIntelligencePersistenceResult: ...

    async def persist_risk_assessment(
        self,
        risk_assessment: AgentRiskAssessmentRecord,
    ) -> AgentIntelligencePersistenceResult: ...

    async def get_reasoning(
        self,
        reasoning_id: str,
    ) -> AgentReasoningRecord | None: ...

    async def get_recommendation(
        self,
        agent_recommendation_id: str,
    ) -> AgentRecommendationRecord | None: ...

    async def get_risk_assessment(
        self,
        risk_assessment_id: str,
    ) -> AgentRiskAssessmentRecord | None: ...

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
    ) -> Sequence[AgentReasoningRecord]: ...

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
    ) -> Sequence[AgentRecommendationRecord]: ...

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
    ) -> Sequence[AgentRiskAssessmentRecord]: ...
