from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.agent_intelligence import AgentReasoningModel
from core.database.models.agent_intelligence import AgentRecommendationModel
from core.database.models.agent_intelligence import AgentRiskAssessmentModel
from core.storage.persistence.agent_intelligence import AgentReasoningRecord
from core.storage.persistence.agent_intelligence import AgentRecommendationRecord
from core.storage.persistence.agent_intelligence import AgentRiskAssessmentRecord
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity


class AgentIntelligencePersistenceSerializer:
    """
    Serializer between enriched typed agent-intelligence records and DB models.

    JSON dictionaries are introduced here only at the PostgreSQL persistence
    boundary for curated inputs/outputs, supporting persisted identities, and
    metadata. Full reasoning, rationale, assessment, and LLM text are preserved
    as untruncated text columns.
    """

    @staticmethod
    def reasoning_values(
        record: AgentReasoningRecord,
    ) -> dict[str, Any]:
        return {
            "reasoning_id": record.reasoning_id,
            "agent_signal_id": record.agent_signal_id,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "timestamp": record.timestamp,
            "reasoning_type": record.reasoning_type,
            "model_name": record.model_name,
            "prompt_version": record.prompt_version,
            "symbol": record.symbol,
            "universe": record.universe,
            "reasoning_text": record.reasoning_text,
            "full_llm_response": record.full_llm_response,
            "inputs": dict(record.inputs),
            "outputs": dict(record.outputs),
            "linked_records": _identity_values(record.linked_records),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def recommendation_values(
        record: AgentRecommendationRecord,
    ) -> dict[str, Any]:
        return {
            "agent_recommendation_id": record.agent_recommendation_id,
            "agent_signal_id": record.agent_signal_id,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "timestamp": record.timestamp,
            "recommendation_type": record.recommendation_type,
            "recommendation_text": record.recommendation_text,
            "symbol": record.symbol,
            "universe": record.universe,
            "bias": record.bias,
            "action": record.action,
            "confidence": record.confidence,
            "conviction": record.conviction,
            "time_horizon": record.time_horizon,
            "rationale_text": record.rationale_text,
            "full_llm_response": record.full_llm_response,
            "supporting_signals": _identity_values(record.supporting_signals),
            "inputs": dict(record.inputs),
            "outputs": dict(record.outputs),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def risk_assessment_values(
        record: AgentRiskAssessmentRecord,
    ) -> dict[str, Any]:
        return {
            "risk_assessment_id": record.risk_assessment_id,
            "agent_signal_id": record.agent_signal_id,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "timestamp": record.timestamp,
            "risk_type": record.risk_type,
            "assessment_text": record.assessment_text,
            "symbol": record.symbol,
            "universe": record.universe,
            "risk_level": record.risk_level,
            "risk_score": record.risk_score,
            "confidence": record.confidence,
            "mitigation": record.mitigation,
            "full_llm_response": record.full_llm_response,
            "inputs": dict(record.inputs),
            "outputs": dict(record.outputs),
            "supporting_signals": _identity_values(record.supporting_signals),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def reasoning_from_model(
        model: AgentReasoningModel,
    ) -> AgentReasoningRecord:
        return AgentReasoningRecord(
            reasoning_id=model.reasoning_id,
            agent_signal_id=model.agent_signal_id,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            timestamp=model.timestamp,
            reasoning_type=model.reasoning_type,
            model_name=model.model_name,
            prompt_version=model.prompt_version,
            symbol=model.symbol,
            universe=model.universe,
            reasoning_text=model.reasoning_text,
            full_llm_response=model.full_llm_response,
            inputs=cast(JsonObject, model.inputs),
            outputs=cast(JsonObject, model.outputs),
            linked_records=_identities_from_values(model.linked_records),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def recommendation_from_model(
        model: AgentRecommendationModel,
    ) -> AgentRecommendationRecord:
        return AgentRecommendationRecord(
            agent_recommendation_id=model.agent_recommendation_id,
            agent_signal_id=model.agent_signal_id,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            timestamp=model.timestamp,
            recommendation_type=model.recommendation_type,
            recommendation_text=model.recommendation_text,
            symbol=model.symbol,
            universe=model.universe,
            bias=model.bias,
            action=model.action,
            confidence=model.confidence,
            conviction=model.conviction,
            time_horizon=model.time_horizon,
            rationale_text=model.rationale_text,
            full_llm_response=model.full_llm_response,
            supporting_signals=_identities_from_values(model.supporting_signals),
            inputs=cast(JsonObject, model.inputs),
            outputs=cast(JsonObject, model.outputs),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def risk_assessment_from_model(
        model: AgentRiskAssessmentModel,
    ) -> AgentRiskAssessmentRecord:
        return AgentRiskAssessmentRecord(
            risk_assessment_id=model.risk_assessment_id,
            agent_signal_id=model.agent_signal_id,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            timestamp=model.timestamp,
            risk_type=model.risk_type,
            assessment_text=model.assessment_text,
            symbol=model.symbol,
            universe=model.universe,
            risk_level=model.risk_level,
            risk_score=model.risk_score,
            confidence=model.confidence,
            mitigation=model.mitigation,
            full_llm_response=model.full_llm_response,
            inputs=cast(JsonObject, model.inputs),
            outputs=cast(JsonObject, model.outputs),
            supporting_signals=_identities_from_values(model.supporting_signals),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _identity_values(
    identities: tuple[PersistenceRecordIdentity, ...],
) -> list[dict[str, str]]:
    return [identity.as_dict() for identity in identities]


def _identities_from_values(
    values: list[dict[str, Any]],
) -> tuple[PersistenceRecordIdentity, ...]:
    return tuple(
        PersistenceRecordIdentity(
            record_type=str(value["record_type"]),
            record_id=str(value["record_id"]),
        )
        for value in values
    )


def _lineage_from_model(
    model: AgentReasoningModel | AgentRecommendationModel | AgentRiskAssessmentModel,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
