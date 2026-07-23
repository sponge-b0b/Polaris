from __future__ import annotations

from typing import Any, cast

from core.database.models.recommendations import (
    RecommendationModel,
    RecommendationOutcomeModel,
    RecommendationRationaleModel,
    TradeSetupModel,
    WatchlistItemModel,
)
from core.storage.persistence.lineage import (
    JsonObject,
    PersistenceLineage,
    PersistenceRecordIdentity,
)
from core.storage.persistence.recommendations import (
    RecommendationOutcomeRecord,
    RecommendationRationaleRecord,
    RecommendationRecord,
    TradeSetupRecord,
    WatchlistItemRecord,
)


class RecommendationPersistenceSerializer:
    """
    Serializer between typed recommendation records and SQLAlchemy models.

    JSON dictionaries/lists are introduced here because this module is the
    database persistence boundary. Intelligence/application layers should use
    the typed recommendation records and only serialize when crossing into
    Postgres, telemetry, replay, or other persistence boundaries.
    """

    @staticmethod
    def recommendation_values(
        record: RecommendationRecord,
    ) -> dict[str, Any]:
        return {
            "recommendation_id": record.recommendation_id,
            "symbol": record.symbol,
            "bias": record.bias,
            "confidence": record.confidence,
            "setup_quality": record.setup_quality,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "time_horizon": record.time_horizon,
            "status": record.status,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "entry_context": dict(record.entry_context),
            "stop_context": dict(record.stop_context),
            "target_context": dict(record.target_context),
            "supporting_signals": _identity_values(record.supporting_signals),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def rationale_values(
        record: RecommendationRationaleRecord,
    ) -> dict[str, Any]:
        return {
            "rationale_id": record.rationale_id,
            "recommendation_id": record.recommendation_id,
            "rationale_type": record.rationale_type,
            "rationale_text": record.rationale_text,
            "confidence": record.confidence,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "supporting_signals": _identity_values(record.supporting_signals),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def outcome_values(
        record: RecommendationOutcomeRecord,
    ) -> dict[str, Any]:
        return {
            "outcome_id": record.outcome_id,
            "recommendation_id": record.recommendation_id,
            "evaluated_at": record.evaluated_at,
            "human_action": record.human_action,
            "outcome": record.outcome,
            "outcome_return": record.outcome_return,
            "outcome_notes": record.outcome_notes,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def trade_setup_values(
        record: TradeSetupRecord,
    ) -> dict[str, Any]:
        return {
            "setup_id": record.setup_id,
            "recommendation_id": record.recommendation_id,
            "symbol": record.symbol,
            "setup_type": record.setup_type,
            "bias": record.bias,
            "setup_quality": record.setup_quality,
            "confidence": record.confidence,
            "risk_score": record.risk_score,
            "risk_reward_ratio": record.risk_reward_ratio,
            "time_horizon": record.time_horizon,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "entry_context": dict(record.entry_context),
            "stop_context": dict(record.stop_context),
            "target_context": dict(record.target_context),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def watchlist_item_values(
        record: WatchlistItemRecord,
    ) -> dict[str, Any]:
        return {
            "watchlist_item_id": record.watchlist_item_id,
            "recommendation_id": record.recommendation_id,
            "symbol": record.symbol,
            "reason": record.reason,
            "priority": record.priority,
            "status": record.status,
            "bias": record.bias,
            "confidence": record.confidence,
            "setup_quality": record.setup_quality,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def recommendation_from_model(
        model: RecommendationModel,
    ) -> RecommendationRecord:
        return RecommendationRecord(
            recommendation_id=model.recommendation_id,
            symbol=model.symbol,
            bias=model.bias,
            confidence=model.confidence,
            setup_quality=model.setup_quality,
            risk_score=model.risk_score,
            risk_level=model.risk_level,
            time_horizon=model.time_horizon,
            status=model.status,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            entry_context=cast(JsonObject, model.entry_context),
            stop_context=cast(JsonObject, model.stop_context),
            target_context=cast(JsonObject, model.target_context),
            supporting_signals=_identities_from_values(model.supporting_signals),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def rationale_from_model(
        model: RecommendationRationaleModel,
    ) -> RecommendationRationaleRecord:
        return RecommendationRationaleRecord(
            rationale_id=model.rationale_id,
            recommendation_id=model.recommendation_id,
            rationale_type=model.rationale_type,
            rationale_text=model.rationale_text,
            confidence=model.confidence,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            supporting_signals=_identities_from_values(model.supporting_signals),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def outcome_from_model(
        model: RecommendationOutcomeModel,
    ) -> RecommendationOutcomeRecord:
        return RecommendationOutcomeRecord(
            outcome_id=model.outcome_id,
            recommendation_id=model.recommendation_id,
            evaluated_at=model.evaluated_at,
            human_action=model.human_action,
            outcome=model.outcome,
            outcome_return=model.outcome_return,
            outcome_notes=model.outcome_notes,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def trade_setup_from_model(
        model: TradeSetupModel,
    ) -> TradeSetupRecord:
        return TradeSetupRecord(
            setup_id=model.setup_id,
            recommendation_id=model.recommendation_id,
            symbol=model.symbol,
            setup_type=model.setup_type,
            bias=model.bias,
            setup_quality=model.setup_quality,
            confidence=model.confidence,
            risk_score=model.risk_score,
            risk_reward_ratio=model.risk_reward_ratio,
            time_horizon=model.time_horizon,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            entry_context=cast(JsonObject, model.entry_context),
            stop_context=cast(JsonObject, model.stop_context),
            target_context=cast(JsonObject, model.target_context),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def watchlist_item_from_model(
        model: WatchlistItemModel,
    ) -> WatchlistItemRecord:
        return WatchlistItemRecord(
            watchlist_item_id=model.watchlist_item_id,
            recommendation_id=model.recommendation_id,
            symbol=model.symbol,
            reason=model.reason,
            priority=model.priority,
            status=model.status,
            bias=model.bias,
            confidence=model.confidence,
            setup_quality=model.setup_quality,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(
    model: Any,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )


def _identity_values(
    identities: tuple[PersistenceRecordIdentity, ...],
) -> list[dict[str, str]]:
    return [identity.as_dict() for identity in identities]


def _identities_from_values(
    values: object,
) -> tuple[PersistenceRecordIdentity, ...]:
    if not isinstance(values, list):
        return ()

    identities: list[PersistenceRecordIdentity] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        record_type = value.get("record_type")
        record_id = value.get("record_id")
        if not isinstance(record_type, str) or not isinstance(record_id, str):
            continue
        identities.append(
            PersistenceRecordIdentity(
                record_type=record_type,
                record_id=record_id,
            )
        )

    return tuple(identities)
