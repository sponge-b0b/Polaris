from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.attribution import AttributionRecordModel
from core.database.models.attribution import RecommendationAttributionModel
from core.database.models.attribution import SignalAttributionModel
from core.storage.persistence.attribution import AttributionRecord
from core.storage.persistence.attribution import RecommendationAttributionRecord
from core.storage.persistence.attribution import SignalAttributionRecord
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.lineage import PersistenceRecordIdentity


class AttributionPersistenceSerializer:
    """
    Serializer between typed attribution records and PostgreSQL models.

    JSON dictionaries are introduced here only at the persistence boundary for
    linked persisted source records and metadata. Attribution explanations are
    preserved as full, untruncated text columns.
    """

    @staticmethod
    def attribution_values(
        record: AttributionRecord,
    ) -> dict[str, Any]:
        return {
            "attribution_id": record.attribution_id,
            "target_record_type": record.target_record.record_type,
            "target_record_id": record.target_record.record_id,
            "attribution_type": record.attribution_type,
            "contribution_type": record.contribution_type,
            "contribution_score": record.contribution_score,
            "confidence": record.confidence,
            "explanation": record.explanation,
            "timestamp": record.timestamp,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "source_records": _identity_values(record.source_records),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def signal_attribution_values(
        record: SignalAttributionRecord,
    ) -> dict[str, Any]:
        return {
            "signal_attribution_id": record.signal_attribution_id,
            "signal_id": record.signal_id,
            "attribution_type": record.attribution_type,
            "contribution_type": record.contribution_type,
            "contribution_score": record.contribution_score,
            "confidence": record.confidence,
            "explanation": record.explanation,
            "timestamp": record.timestamp,
            "signal_type": record.signal_type,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "symbol": record.symbol,
            "universe": record.universe,
            "source_records": _identity_values(record.source_records),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def recommendation_attribution_values(
        record: RecommendationAttributionRecord,
    ) -> dict[str, Any]:
        return {
            "recommendation_attribution_id": record.recommendation_attribution_id,
            "recommendation_id": record.recommendation_id,
            "signal_id": record.signal_id,
            "attribution_type": record.attribution_type,
            "contribution_type": record.contribution_type,
            "contribution_score": record.contribution_score,
            "confidence": record.confidence,
            "explanation": record.explanation,
            "timestamp": record.timestamp,
            "agent_name": record.agent_name,
            "agent_type": record.agent_type,
            "symbol": record.symbol,
            "universe": record.universe,
            "source_records": _identity_values(record.source_records),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def attribution_from_model(
        model: AttributionRecordModel,
    ) -> AttributionRecord:
        return AttributionRecord(
            attribution_id=model.attribution_id,
            target_record=PersistenceRecordIdentity(
                record_type=model.target_record_type,
                record_id=model.target_record_id,
            ),
            attribution_type=model.attribution_type,
            contribution_type=model.contribution_type,
            contribution_score=model.contribution_score,
            confidence=model.confidence,
            explanation=model.explanation,
            timestamp=model.timestamp,
            lineage=_lineage_from_model(model),
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            source_records=_identities_from_values(model.source_records),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def signal_attribution_from_model(
        model: SignalAttributionModel,
    ) -> SignalAttributionRecord:
        return SignalAttributionRecord(
            signal_attribution_id=model.signal_attribution_id,
            signal_id=model.signal_id,
            attribution_type=model.attribution_type,
            contribution_type=model.contribution_type,
            contribution_score=model.contribution_score,
            confidence=model.confidence,
            explanation=model.explanation,
            timestamp=model.timestamp,
            lineage=_lineage_from_model(model),
            signal_type=model.signal_type,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            symbol=model.symbol,
            universe=model.universe,
            source_records=_identities_from_values(model.source_records),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def recommendation_attribution_from_model(
        model: RecommendationAttributionModel,
    ) -> RecommendationAttributionRecord:
        return RecommendationAttributionRecord(
            recommendation_attribution_id=model.recommendation_attribution_id,
            recommendation_id=model.recommendation_id,
            attribution_type=model.attribution_type,
            contribution_type=model.contribution_type,
            contribution_score=model.contribution_score,
            confidence=model.confidence,
            explanation=model.explanation,
            timestamp=model.timestamp,
            lineage=_lineage_from_model(model),
            signal_id=model.signal_id,
            agent_name=model.agent_name,
            agent_type=model.agent_type,
            symbol=model.symbol,
            universe=model.universe,
            source_records=_identities_from_values(model.source_records),
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
    model: AttributionRecordModel
    | SignalAttributionModel
    | RecommendationAttributionModel,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
