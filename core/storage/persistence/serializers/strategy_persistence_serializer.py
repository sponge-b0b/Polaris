from __future__ import annotations

from typing import Any
from typing import cast

from core.database.models.strategy import StrategyHypothesisEvaluationModel
from core.database.models.strategy import StrategyHypothesisModel
from core.database.models.strategy import StrategySynthesisDecisionModel
from core.storage.persistence.lineage import JsonObject
from core.storage.persistence.lineage import PersistenceLineage
from core.storage.persistence.strategy import StrategyHypothesisEvaluationRecord
from core.storage.persistence.strategy import StrategyHypothesisRecord
from core.storage.persistence.strategy import StrategySynthesisDecisionRecord


class StrategyPersistenceSerializer:
    """
    Serializer between typed strategy records and SQLAlchemy models.

    JSON collections are introduced only at this database persistence boundary;
    strategy intelligence and application coordination use typed records.
    """

    @staticmethod
    def hypothesis_values(record: StrategyHypothesisRecord) -> dict[str, Any]:
        return {
            "hypothesis_id": record.hypothesis_id,
            "symbol": record.symbol,
            "perspective": record.perspective,
            "thesis": record.thesis,
            "directional_bias": record.directional_bias,
            "hypothesis_strength": record.hypothesis_strength,
            "confidence": record.confidence,
            "evidence_fingerprint": record.evidence_fingerprint,
            "invalidated": record.invalidated,
            "horizon": record.horizon,
            "as_of": record.as_of,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "supporting_evidence": _json_object_list(record.supporting_evidence),
            "contradicting_evidence": _json_object_list(record.contradicting_evidence),
            "key_assumptions": _json_object_list(record.key_assumptions),
            "invalidation_conditions": _json_object_list(
                record.invalidation_conditions
            ),
            "risks": list(record.risks),
            "recommendations": list(record.recommendations),
            "data_quality_flags": list(record.data_quality_flags),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def decision_values(record: StrategySynthesisDecisionRecord) -> dict[str, Any]:
        return {
            "decision_id": record.decision_id,
            "symbol": record.symbol,
            "selected_perspective": record.selected_perspective,
            "selection_status": record.selection_status,
            "directional_score": record.directional_score,
            "confidence": record.confidence,
            "regime": record.regime,
            "uncertainty": record.uncertainty,
            "thesis": record.thesis,
            "evidence_fingerprint": record.evidence_fingerprint,
            "horizon": record.horizon,
            "as_of": record.as_of,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "signals": list(record.signals),
            "risks": list(record.risks),
            "recommendations": list(record.recommendations),
            "degraded_reasons": list(record.degraded_reasons),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def evaluation_values(record: StrategyHypothesisEvaluationRecord) -> dict[str, Any]:
        return {
            "evaluation_id": record.evaluation_id,
            "decision_id": record.decision_id,
            "hypothesis_id": record.hypothesis_id,
            "symbol": record.symbol,
            "perspective": record.perspective,
            "perspective_weight": record.perspective_weight,
            "contradiction_burden": record.contradiction_burden,
            "assumption_support": record.assumption_support,
            "invalidated": record.invalidated,
            "candidate_score": record.candidate_score,
            "posterior_weight": record.posterior_weight,
            "rank": record.rank,
            "selection_status": record.selection_status,
            "evidence_fingerprint": record.evidence_fingerprint,
            "horizon": record.horizon,
            "as_of": record.as_of,
            "workflow_name": record.lineage.workflow_name,
            "execution_id": record.lineage.execution_id,
            "runtime_id": record.lineage.runtime_id,
            "node_name": record.lineage.node_name,
            "created_at": record.created_at,
            "degraded_reasons": list(record.degraded_reasons),
            "metadata_payload": dict(record.metadata),
        }

    @staticmethod
    def hypothesis_from_model(
        model: StrategyHypothesisModel,
    ) -> StrategyHypothesisRecord:
        return StrategyHypothesisRecord(
            hypothesis_id=model.hypothesis_id,
            symbol=model.symbol,
            perspective=model.perspective,
            thesis=model.thesis,
            directional_bias=model.directional_bias,
            hypothesis_strength=model.hypothesis_strength,
            confidence=model.confidence,
            evidence_fingerprint=model.evidence_fingerprint,
            invalidated=model.invalidated,
            horizon=model.horizon,
            as_of=model.as_of,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            supporting_evidence=_json_objects_from_values(model.supporting_evidence),
            contradicting_evidence=_json_objects_from_values(
                model.contradicting_evidence
            ),
            key_assumptions=_json_objects_from_values(model.key_assumptions),
            invalidation_conditions=_json_objects_from_values(
                model.invalidation_conditions
            ),
            risks=_strings_from_values(model.risks),
            recommendations=_strings_from_values(model.recommendations),
            data_quality_flags=_strings_from_values(model.data_quality_flags),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def decision_from_model(
        model: StrategySynthesisDecisionModel,
    ) -> StrategySynthesisDecisionRecord:
        return StrategySynthesisDecisionRecord(
            decision_id=model.decision_id,
            symbol=model.symbol,
            selected_perspective=model.selected_perspective,
            selection_status=model.selection_status,
            directional_score=model.directional_score,
            confidence=model.confidence,
            regime=model.regime,
            uncertainty=model.uncertainty,
            thesis=model.thesis,
            evidence_fingerprint=model.evidence_fingerprint,
            horizon=model.horizon,
            as_of=model.as_of,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            signals=_strings_from_values(model.signals),
            risks=_strings_from_values(model.risks),
            recommendations=_strings_from_values(model.recommendations),
            degraded_reasons=_strings_from_values(model.degraded_reasons),
            metadata=cast(JsonObject, model.metadata_payload),
        )

    @staticmethod
    def evaluation_from_model(
        model: StrategyHypothesisEvaluationModel,
    ) -> StrategyHypothesisEvaluationRecord:
        return StrategyHypothesisEvaluationRecord(
            evaluation_id=model.evaluation_id,
            decision_id=model.decision_id,
            hypothesis_id=model.hypothesis_id,
            symbol=model.symbol,
            perspective=model.perspective,
            perspective_weight=model.perspective_weight,
            contradiction_burden=model.contradiction_burden,
            assumption_support=model.assumption_support,
            invalidated=model.invalidated,
            candidate_score=model.candidate_score,
            posterior_weight=model.posterior_weight,
            rank=model.rank,
            selection_status=model.selection_status,
            evidence_fingerprint=model.evidence_fingerprint,
            horizon=model.horizon,
            as_of=model.as_of,
            lineage=_lineage_from_model(model),
            created_at=model.created_at,
            degraded_reasons=_strings_from_values(model.degraded_reasons),
            metadata=cast(JsonObject, model.metadata_payload),
        )


def _lineage_from_model(model: Any) -> PersistenceLineage:
    return PersistenceLineage(
        workflow_name=model.workflow_name,
        execution_id=model.execution_id,
        runtime_id=model.runtime_id,
        node_name=model.node_name,
    )


def _json_object_list(values: tuple[JsonObject, ...]) -> list[dict[str, object]]:
    return [dict(value) for value in values]


def _json_objects_from_values(values: object) -> tuple[JsonObject, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(cast(JsonObject, value) for value in values if isinstance(value, dict))


def _strings_from_values(values: object) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, str))
