from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.macro import EconomicCalendarEventModel
from core.database.models.macro import MacroObservationModel
from core.database.models.macro import MacroRegimeSnapshotModel
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.macro import EconomicCalendarEventRecord
from core.storage.persistence.macro import MacroObservationRecord
from core.storage.persistence.macro import MacroRegimeSnapshotRecord


class MacroPersistenceSerializer:
    """
    Serializer between typed macro persistence records and SQLAlchemy models.

    Macro provider payloads should be normalized into typed records before this
    boundary. JSON dictionaries are introduced here only for PostgreSQL JSONB
    columns that preserve curated inputs, outputs, and metadata for replay,
    audit, and future RAG source curation.
    """

    @staticmethod
    def observation_values(
        record: MacroObservationRecord,
    ) -> dict[str, Any]:
        return {
            "observation_id": record.observation_id,
            "indicator_name": record.indicator_name,
            "observation_timestamp": record.observation_timestamp,
            "source": record.source,
            "value": record.value,
            "indicator_category": record.indicator_category,
            "region": record.region,
            "unit": record.unit,
            "frequency": record.frequency,
            "release_timestamp": record.release_timestamp,
            "vintage_timestamp": record.vintage_timestamp,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def regime_snapshot_values(
        record: MacroRegimeSnapshotRecord,
    ) -> dict[str, Any]:
        return {
            "regime_snapshot_id": record.regime_snapshot_id,
            "timestamp": record.timestamp,
            "source": record.source,
            "region": record.region,
            "inflation_regime": record.inflation_regime,
            "liquidity_regime": record.liquidity_regime,
            "growth_regime": record.growth_regime,
            "fed_stance": record.fed_stance,
            "yield_curve_regime": record.yield_curve_regime,
            "macro_regime": record.macro_regime,
            "economic_regime": record.economic_regime,
            "inflation_score": record.inflation_score,
            "liquidity_score": record.liquidity_score,
            "growth_score": record.growth_score,
            "yield_curve_score": record.yield_curve_score,
            "macro_score": record.macro_score,
            "risk_score": record.risk_score,
            "confidence": record.confidence,
            "inputs": dict(record.inputs),
            "outputs": dict(record.outputs),
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def calendar_event_values(
        record: EconomicCalendarEventRecord,
    ) -> dict[str, Any]:
        return {
            "event_id": record.event_id,
            "event_name": record.event_name,
            "event_timestamp": record.event_timestamp,
            "source": record.source,
            "region": record.region,
            "event_type": record.event_type,
            "importance_score": record.importance_score,
            "actual_value": record.actual_value,
            "forecast_value": record.forecast_value,
            "previous_value": record.previous_value,
            "surprise_score": record.surprise_score,
            "unit": record.unit,
            "currency": record.currency,
            "release_status": record.release_status,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def observation_from_model(
        model: MacroObservationModel,
    ) -> MacroObservationRecord:
        return MacroObservationRecord(
            observation_id=model.observation_id,
            indicator_name=model.indicator_name,
            observation_timestamp=model.observation_timestamp,
            source=model.source,
            value=model.value,
            indicator_category=model.indicator_category,
            region=model.region,
            unit=model.unit,
            frequency=model.frequency,
            release_timestamp=model.release_timestamp,
            vintage_timestamp=model.vintage_timestamp,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def regime_snapshot_from_model(
        model: MacroRegimeSnapshotModel,
    ) -> MacroRegimeSnapshotRecord:
        return MacroRegimeSnapshotRecord(
            regime_snapshot_id=model.regime_snapshot_id,
            timestamp=model.timestamp,
            source=model.source,
            region=model.region,
            inflation_regime=model.inflation_regime,
            liquidity_regime=model.liquidity_regime,
            growth_regime=model.growth_regime,
            fed_stance=model.fed_stance,
            yield_curve_regime=model.yield_curve_regime,
            macro_regime=model.macro_regime,
            economic_regime=model.economic_regime,
            inflation_score=model.inflation_score,
            liquidity_score=model.liquidity_score,
            growth_score=model.growth_score,
            yield_curve_score=model.yield_curve_score,
            macro_score=model.macro_score,
            risk_score=model.risk_score,
            confidence=model.confidence,
            inputs=cast(JsonObject, model.inputs),
            outputs=cast(JsonObject, model.outputs),
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def calendar_event_from_model(
        model: EconomicCalendarEventModel,
    ) -> EconomicCalendarEventRecord:
        return EconomicCalendarEventRecord(
            event_id=model.event_id,
            event_name=model.event_name,
            event_timestamp=model.event_timestamp,
            source=model.source,
            region=model.region,
            event_type=model.event_type,
            importance_score=model.importance_score,
            actual_value=model.actual_value,
            forecast_value=model.forecast_value,
            previous_value=model.previous_value,
            surprise_score=model.surprise_score,
            unit=model.unit,
            currency=model.currency,
            release_status=model.release_status,
            lineage=_lineage_from_model(model),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(
    model: MacroObservationModel
    | MacroRegimeSnapshotModel
    | EconomicCalendarEventModel,
) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )
