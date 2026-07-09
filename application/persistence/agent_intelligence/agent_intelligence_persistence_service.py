from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceBundle,
)
from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceRepository,
)
from core.storage.persistence.agent_intelligence import (
    AgentIntelligencePersistenceResult,
)
from core.storage.persistence.agent_intelligence import AgentReasoningRecord
from core.storage.persistence.agent_intelligence import AgentRecommendationRecord
from core.storage.persistence.agent_intelligence import AgentRiskAssessmentRecord
from core.storage.persistence.lineage import clean_optional_identifier
from core.storage.persistence.query import PersistenceCommonQuery
from core.storage.persistence.query import PersistenceListResult

from application.persistence.query_result_helpers import build_common_query
from application.persistence.query_result_helpers import build_list_result


@dataclass(
    frozen=True,
    slots=True,
)
class AgentReasoningPersistenceFilters:
    """
    Typed application-layer filters for enriched agent reasoning retrieval.
    """

    agent_signal_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _normalize_common_filters(
            self,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRecommendationPersistenceFilters:
    """
    Typed application-layer filters for enriched agent recommendation retrieval.
    """

    agent_signal_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _normalize_common_filters(
            self,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class AgentRiskAssessmentPersistenceFilters:
    """
    Typed application-layer filters for enriched agent risk assessment retrieval.
    """

    agent_signal_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    agent_name: str | None = None
    agent_type: str | None = None
    symbol: str | None = None
    universe: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(
        self,
    ) -> None:
        _normalize_common_filters(
            self,
        )


class AgentIntelligencePersistenceService:
    """
    Application service for enriched agent intelligence persistence.

    The service coordinates typed records through the repository protocol only.
    It preserves ``agent_signals`` as the primary signal table and persists
    reasoning, recommendation, and risk-assessment records only as enriched
    intelligence linked by ``agent_signal_id``.
    """

    def __init__(
        self,
        repository: AgentIntelligencePersistenceRepository,
    ) -> None:
        self._repository = repository

    async def persist_bundle(
        self,
        bundle: AgentIntelligencePersistenceBundle,
    ) -> AgentIntelligencePersistenceResult:
        return await self._repository.persist_intelligence_bundle(
            bundle,
        )

    async def persist_records(
        self,
        *,
        reasoning: Sequence[AgentReasoningRecord] = (),
        recommendations: Sequence[AgentRecommendationRecord] = (),
        risk_assessments: Sequence[AgentRiskAssessmentRecord] = (),
    ) -> AgentIntelligencePersistenceResult:
        return await self.persist_bundle(
            AgentIntelligencePersistenceBundle(
                reasoning=tuple(
                    reasoning,
                ),
                recommendations=tuple(
                    recommendations,
                ),
                risk_assessments=tuple(
                    risk_assessments,
                ),
            )
        )

    async def persist_reasoning(
        self,
        reasoning: AgentReasoningRecord,
    ) -> AgentIntelligencePersistenceResult:
        return await self._repository.persist_reasoning(
            reasoning,
        )

    async def persist_recommendation(
        self,
        recommendation: AgentRecommendationRecord,
    ) -> AgentIntelligencePersistenceResult:
        return await self._repository.persist_recommendation(
            recommendation,
        )

    async def persist_risk_assessment(
        self,
        risk_assessment: AgentRiskAssessmentRecord,
    ) -> AgentIntelligencePersistenceResult:
        return await self._repository.persist_risk_assessment(
            risk_assessment,
        )

    async def get_reasoning(
        self,
        reasoning_id: str,
    ) -> AgentReasoningRecord | None:
        return await self._repository.get_reasoning(
            reasoning_id,
        )

    async def get_recommendation(
        self,
        agent_recommendation_id: str,
    ) -> AgentRecommendationRecord | None:
        return await self._repository.get_recommendation(
            agent_recommendation_id,
        )

    async def get_risk_assessment(
        self,
        risk_assessment_id: str,
    ) -> AgentRiskAssessmentRecord | None:
        return await self._repository.get_risk_assessment(
            risk_assessment_id,
        )

    async def list_reasoning(
        self,
        filters: AgentReasoningPersistenceFilters | None = None,
    ) -> Sequence[AgentReasoningRecord]:
        result = await self.list_reasoning_result(
            filters,
        )
        return result.records

    async def list_reasoning_result(
        self,
        filters: AgentReasoningPersistenceFilters | None = None,
    ) -> PersistenceListResult[AgentReasoningRecord]:
        active_filters = filters or AgentReasoningPersistenceFilters()
        records = await self._repository.list_reasoning(
            agent_signal_id=active_filters.agent_signal_id,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_agent_intelligence_query(
            record_type="agent_reasoning",
            filters=active_filters,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_recommendations(
        self,
        filters: AgentRecommendationPersistenceFilters | None = None,
    ) -> Sequence[AgentRecommendationRecord]:
        result = await self.list_recommendations_result(
            filters,
        )
        return result.records

    async def list_recommendations_result(
        self,
        filters: AgentRecommendationPersistenceFilters | None = None,
    ) -> PersistenceListResult[AgentRecommendationRecord]:
        active_filters = filters or AgentRecommendationPersistenceFilters()
        records = await self._repository.list_recommendations(
            agent_signal_id=active_filters.agent_signal_id,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_agent_intelligence_query(
            record_type="agent_recommendation",
            filters=active_filters,
        )
        return build_list_result(
            records,
            query=query,
        )

    async def list_risk_assessments(
        self,
        filters: AgentRiskAssessmentPersistenceFilters | None = None,
    ) -> Sequence[AgentRiskAssessmentRecord]:
        result = await self.list_risk_assessments_result(
            filters,
        )
        return result.records

    async def list_risk_assessments_result(
        self,
        filters: AgentRiskAssessmentPersistenceFilters | None = None,
    ) -> PersistenceListResult[AgentRiskAssessmentRecord]:
        active_filters = filters or AgentRiskAssessmentPersistenceFilters()
        records = await self._repository.list_risk_assessments(
            agent_signal_id=active_filters.agent_signal_id,
            workflow_name=active_filters.workflow_name,
            execution_id=active_filters.execution_id,
            agent_name=active_filters.agent_name,
            agent_type=active_filters.agent_type,
            symbol=active_filters.symbol,
            universe=active_filters.universe,
            start=active_filters.start,
            end=active_filters.end,
        )
        query = _build_agent_intelligence_query(
            record_type="agent_risk_assessment",
            filters=active_filters,
        )
        return build_list_result(
            records,
            query=query,
        )


def _build_agent_intelligence_query(
    *,
    record_type: str,
    filters: AgentReasoningPersistenceFilters
    | AgentRecommendationPersistenceFilters
    | AgentRiskAssessmentPersistenceFilters,
) -> PersistenceCommonQuery:
    return build_common_query(
        record_type=record_type,
        workflow_name=filters.workflow_name,
        execution_id=filters.execution_id,
        symbol=filters.symbol,
        start=filters.start,
        end=filters.end,
        metadata={
            "agent_signal_id": filters.agent_signal_id,
            "agent_name": filters.agent_name,
            "agent_type": filters.agent_type,
            "universe": filters.universe,
        },
    )


def _normalize_common_filters(
    filters: AgentReasoningPersistenceFilters
    | AgentRecommendationPersistenceFilters
    | AgentRiskAssessmentPersistenceFilters,
) -> None:
    object.__setattr__(
        filters,
        "agent_signal_id",
        clean_optional_identifier(
            filters.agent_signal_id,
            "agent_signal_id",
        ),
    )
    object.__setattr__(
        filters,
        "workflow_name",
        clean_optional_identifier(
            filters.workflow_name,
            "workflow_name",
        ),
    )
    object.__setattr__(
        filters,
        "execution_id",
        clean_optional_identifier(
            filters.execution_id,
            "execution_id",
        ),
    )
    object.__setattr__(
        filters,
        "agent_name",
        clean_optional_identifier(
            filters.agent_name,
            "agent_name",
        ),
    )
    object.__setattr__(
        filters,
        "agent_type",
        clean_optional_identifier(
            filters.agent_type,
            "agent_type",
        ),
    )
    object.__setattr__(
        filters,
        "symbol",
        _clean_optional_symbol(
            filters.symbol,
        ),
    )
    object.__setattr__(
        filters,
        "universe",
        clean_optional_identifier(
            filters.universe,
            "universe",
        ),
    )
    _require_ordered_time_window(
        filters.start,
        filters.end,
    )


def _clean_optional_symbol(
    symbol: str | None,
) -> str | None:
    clean_symbol = clean_optional_identifier(
        symbol,
        "symbol",
    )
    if clean_symbol is None:
        return None

    return clean_symbol.upper()


def _require_ordered_time_window(
    start: datetime | None,
    end: datetime | None,
) -> None:
    if start is not None and end is not None and start > end:
        raise ValueError("start must be less than or equal to end.")
