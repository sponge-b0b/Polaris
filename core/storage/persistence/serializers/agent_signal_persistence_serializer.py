from __future__ import annotations

from typing import Any, cast

from core.database.models.agent_signals import AgentSignalModel
from core.storage.persistence.agent_signals.agent_signal_persistence_models import (
    AgentSignalRecord,
    JsonObject,
)


class AgentSignalPersistenceSerializer:
    """
    Serializer between typed agent signal records and SQLAlchemy models.

    JSON dictionaries are introduced here because this module is the database
    persistence boundary. Agent/intelligence layers should continue to use typed
    signal objects and convert only at this boundary.
    """

    @staticmethod
    def signal_values(
        record: AgentSignalRecord,
    ) -> dict[str, Any]:
        return {
            "signal_id": record.signal_id,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "workflow_name": record.workflow_name,
            "execution_id": record.execution_id,
            "runtime_id": record.runtime_id,
            "node_name": record.node_name,
            "symbol": record.symbol,
            "universe": list(record.universe),
            "timestamp": record.timestamp,
            "directional_score": record.directional_score,
            "confidence": record.confidence,
            "regime": record.regime,
            "signal_payload": dict(record.signals),
            "risk_payload": dict(record.risks),
            "recommendation_payload": dict(record.recommendations),
            "feature_payload": dict(record.features),
            "reasoning_text": record.reasoning_text,
            "llm_response": record.llm_response,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def signal_from_model(
        model: AgentSignalModel,
    ) -> AgentSignalRecord:
        return AgentSignalRecord(
            signal_id=model.signal_id,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            workflow_name=model.workflow_name,
            execution_id=model.execution_id,
            runtime_id=model.runtime_id,
            node_name=model.node_name,
            symbol=model.symbol,
            universe=tuple(model.universe),
            timestamp=model.timestamp,
            directional_score=model.directional_score,
            confidence=model.confidence,
            regime=model.regime,
            signals=cast(
                JsonObject,
                model.signal_payload,
            ),
            risks=cast(
                JsonObject,
                model.risk_payload,
            ),
            recommendations=cast(
                JsonObject,
                model.recommendation_payload,
            ),
            features=cast(
                JsonObject,
                model.feature_payload,
            ),
            reasoning_text=model.reasoning_text,
            llm_response=model.llm_response,
            metadata=cast(
                JsonObject,
                model.metadata_payload,
            ),
        )
