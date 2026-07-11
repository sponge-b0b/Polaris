from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import cast

import pytest

from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    StrategyHypothesisWorkflowOutputProjector,
)
from application.projections.workflow_outputs.projectors import (
    StrategySynthesisWorkflowOutputProjector,
)
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunBundle
from core.storage.persistence.completed_run_archive import CompletedRunExecutionMode
from core.storage.persistence.completed_run_archive import CompletedRunRecord
from core.storage.persistence.completed_run_archive import JsonObject
from core.storage.persistence.recommendations import RecommendationPersistenceBundle
from core.storage.persistence.recommendations import RecommendationPersistenceRepository
from core.storage.persistence.recommendations import RecommendationPersistenceResult
from core.storage.persistence.strategy import StrategyHypothesisPersistenceResult
from core.storage.persistence.strategy import StrategyHypothesisRecord
from core.storage.persistence.strategy import StrategyPersistenceBundle
from core.storage.persistence.strategy import StrategyPersistenceRepository
from core.storage.persistence.strategy import StrategyPersistenceResult
from domain.workflow_outputs import STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import STRATEGY_SYNTHESIS_OUTPUT_CONTRACT
from domain.workflow_outputs import WORKFLOW_OUTPUT_SCHEMA_VERSION_V1


@pytest.mark.asyncio
async def test_strategy_hypothesis_projector_persists_first_class_hypothesis() -> None:
    strategy_repository = _FakeStrategyRepository()
    projector = StrategyHypothesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        projector_name="strategy_bull_hypothesis_projector",
    )

    outcome = await projector.project(_projector_request(_bull_node()))

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 1
    assert len(strategy_repository.hypothesis_batches) == 1
    hypothesis = strategy_repository.hypothesis_batches[0][0]
    assert hypothesis.symbol == "SPY"
    assert hypothesis.perspective == "bull"
    assert hypothesis.evidence_fingerprint == "bull-fingerprint"
    assert hypothesis.metadata["node_output_id"] == "node-output-bull"


@pytest.mark.asyncio
async def test_strategy_synthesis_projector_persists_decision_and_recommendation() -> (
    None
):
    strategy_repository = _FakeStrategyRepository()
    recommendation_repository = _FakeRecommendationRepository()
    run = _run()
    bull_node = _bull_node()
    synthesis_node = _synthesis_node()
    projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        recommendation_persistence_service=RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, recommendation_repository),
        ),
    )

    outcome = await projector.project(
        _projector_request(
            synthesis_node,
            run=run,
            bundle=CompletedRunBundle(
                run=run, node_outputs=(bull_node, synthesis_node)
            ),
        )
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert len(strategy_repository.bundles) == 1
    strategy_bundle = strategy_repository.bundles[0]
    assert strategy_bundle.decision.symbol == "SPY"
    assert strategy_bundle.decision.selected_perspective == "bull"
    assert len(strategy_bundle.hypotheses) == 1
    assert strategy_bundle.hypotheses[0].perspective == "bull"
    assert len(strategy_bundle.evaluations) == 1

    assert len(recommendation_repository.bundles) == 1
    recommendation_bundle = recommendation_repository.bundles[0]
    assert recommendation_bundle.recommendation.status == "strategy_recommendation"
    assert recommendation_bundle.recommendation.metadata["strategy_decision_id"]
    assert recommendation_bundle.rationales[0].rationale_type == "strategy_synthesis"


class _FakeStrategyRepository:
    def __init__(self) -> None:
        self.hypothesis_batches: list[tuple[StrategyHypothesisRecord, ...]] = []
        self.bundles: list[StrategyPersistenceBundle] = []

    async def persist_hypotheses(
        self,
        hypotheses: tuple[StrategyHypothesisRecord, ...],
    ) -> StrategyHypothesisPersistenceResult:
        self.hypothesis_batches.append(tuple(hypotheses))
        return StrategyHypothesisPersistenceResult.succeeded(
            hypothesis_ids=tuple(item.hypothesis_id for item in hypotheses),
            records_persisted=len(hypotheses),
        )

    async def persist_strategy_bundle(
        self,
        bundle: StrategyPersistenceBundle,
    ) -> StrategyPersistenceResult:
        self.bundles.append(bundle)
        return StrategyPersistenceResult.succeeded(
            decision_id=bundle.decision.decision_id,
            records_persisted=1 + len(bundle.hypotheses) + len(bundle.evaluations),
        )


class _FakeRecommendationRepository:
    def __init__(self) -> None:
        self.bundles: list[RecommendationPersistenceBundle] = []

    async def persist_recommendation_bundle(
        self,
        bundle: RecommendationPersistenceBundle,
    ) -> RecommendationPersistenceResult:
        self.bundles.append(bundle)
        return RecommendationPersistenceResult.succeeded(
            recommendation_id=bundle.recommendation.recommendation_id,
            records_persisted=1 + len(bundle.rationales),
        )


def _projector_request(
    node_output: CompletedNodeOutputRecord,
    *,
    run: CompletedRunRecord | None = None,
    bundle: CompletedRunBundle | None = None,
) -> WorkflowOutputProjectorRequest:
    active_run = run or _run()
    return WorkflowOutputProjectorRequest(
        run=active_run,
        node_output=node_output,
        source_fingerprint="fingerprint-1",
        bundle=bundle,
        lineage=build_workflow_output_projection_lineage(
            run=active_run,
            node_output=node_output,
        ),
        requested_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
    )


def _run() -> CompletedRunRecord:
    return CompletedRunRecord(
        run_id="run-1",
        workflow_name="morning_report",
        workflow_id="workflow-1",
        execution_id="exec-1",
        runtime_id="runtime-1",
        status="succeeded",
        success=True,
        context_json={},
        inputs_json={"symbol": "SPY", "horizon": "short_term"},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 35, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=2,
        completed_node_count=2,
        failed_node_count=0,
        execution_mode=CompletedRunExecutionMode.NORMAL,
    )


def _bull_node() -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-bull",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="bull_agent",
        node_type="strategy",
        output_contract=STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=cast(JsonObject, {"strategy_hypothesis": _bull_hypothesis_payload()}),
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _synthesis_node() -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-synthesis",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="strategy_synthesis_agent",
        node_type="strategy",
        output_contract=STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=cast(
            JsonObject,
            {"features": {"strategy_synthesis_decision": _decision_payload()}},
        ),
        metadata={"quality_status": "degraded"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 32, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 34, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _bull_hypothesis_payload() -> dict[str, object]:
    return {
        "perspective": "bull",
        "thesis": "Bullish setup remains favored.",
        "directional_bias": 0.65,
        "hypothesis_strength": 0.72,
        "confidence": 0.8,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "key_assumptions": [],
        "invalidation_conditions": [],
        "risks": ["reversal risk"],
        "recommendations": ["Prefer constructive exposure."],
        "data_quality_flags": [],
        "evidence_fingerprint": "bull-fingerprint",
    }


def _decision_payload() -> dict[str, object]:
    return {
        "selected_perspective": "bull",
        "selection_status": "selected",
        "directional_score": 0.61,
        "confidence": 0.78,
        "regime": "bullish",
        "uncertainty": 0.22,
        "evaluations": [
            {
                "perspective": "bull",
                "perspective_weight": 0.6,
                "contradiction_burden": 0.2,
                "assumption_support": 0.8,
                "invalidated": False,
                "candidate_score": 0.74,
                "posterior_weight": 1.0,
                "rank": 1,
                "selection_status": "selected",
                "degraded_reasons": [],
            }
        ],
        "degraded_reasons": [],
        "thesis": "Bullish strategy remains favored.",
        "signals": ["technical confirmation"],
        "risks": ["headline risk"],
        "recommendations": ["Maintain constructive allocation."],
    }
