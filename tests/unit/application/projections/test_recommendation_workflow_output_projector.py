from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest

from application.persistence.recommendations import RecommendationPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    TradeRecommendationWorkflowOutputProjector,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonObject,
    JsonValue,
)
from core.storage.persistence.recommendations import (
    RecommendationPersistenceBundle,
    RecommendationPersistenceRepository,
    RecommendationPersistenceResult,
)
from domain.authority import GateProfile, RiskTier
from domain.workflow_outputs import (
    TRADE_RECOMMENDATION_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


def _authority_metadata(metadata: JsonObject) -> Mapping[str, JsonValue]:
    return cast(Mapping[str, JsonValue], metadata["risk_authority"])


@pytest.mark.asyncio
async def test_trade_recommendation_projector_maps_trade_proposal_distinctly() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
    )

    outcome = await projector.project(_projector_request())

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 3
    assert len(repository.bundles) == 1
    bundle = repository.bundles[0]
    assert bundle.recommendation.status == "trade_proposal"
    assert bundle.recommendation.symbol == "SPY"
    assert bundle.recommendation.bias == "bullish"
    assert bundle.trade_setups[0].setup_type == "trade_recommendation"
    assert bundle.trade_setups[0].risk_reward_ratio == 2.0
    assert bundle.rationales[0].rationale_type == "trade_recommendation"

    recommendation_authority = _authority_metadata(bundle.recommendation.metadata)
    assert recommendation_authority["risk_tier"] == RiskTier.VIGILANT.value
    assert (
        recommendation_authority["gate_profile"]
        == GateProfile.VIGILANT_DECISION_EVIDENCE.value
    )
    assert recommendation_authority["intended_sink"] == "recommendation"
    assert recommendation_authority["canonical_owner"] == "recommendation_service"
    assert recommendation_authority["durable_authority"] is True

    rationale_authority = _authority_metadata(bundle.rationales[0].metadata)
    assert rationale_authority["risk_tier"] == RiskTier.ENHANCED.value
    assert rationale_authority["authority_effect"] == "advisory_context"
    assert rationale_authority["content_type"] == "recommendation_explanation"
    assert rationale_authority["durable_authority"] is False


@pytest.mark.asyncio
async def test_trade_recommendation_projector_ignores_model_authority_claims() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_model_claims())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    bundle = repository.bundles[0]
    recommendation_authority = _authority_metadata(bundle.recommendation.metadata)
    assert recommendation_authority["risk_tier"] == RiskTier.VIGILANT.value
    assert recommendation_authority["authority_effect"] == "canonical_record"
    assert recommendation_authority["gate_profile"] == (
        GateProfile.VIGILANT_DECISION_EVIDENCE.value
    )
    assert recommendation_authority["ignored_model_authority_claims"] == [
        "authority_effect",
        "governance_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier",
    ]
    assert "governance_approved" not in bundle.recommendation.metadata
    assert "production_ready" not in bundle.recommendation.metadata
    assert "residual_risk_accepted" not in bundle.recommendation.metadata

    rationale_authority = _authority_metadata(bundle.rationales[0].metadata)
    assert rationale_authority["risk_tier"] == RiskTier.ENHANCED.value
    assert rationale_authority["authority_effect"] == "advisory_context"
    assert rationale_authority["ignored_model_authority_claims"] == [
        "authority_effect",
        "governance_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier",
    ]


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
            records_persisted=(
                1
                + len(bundle.rationales)
                + len(bundle.outcomes)
                + len(bundle.trade_setups)
                + len(bundle.watchlist_items)
            ),
        )


def _projector_request(
    *,
    node: CompletedNodeOutputRecord | None = None,
) -> WorkflowOutputProjectorRequest:
    run = _run()
    node_output = node or _node()
    return WorkflowOutputProjectorRequest(
        run=run,
        node_output=node_output,
        source_fingerprint="fingerprint-1",
        lineage=build_workflow_output_projection_lineage(
            run=run,
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
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
        execution_mode=CompletedRunExecutionMode.NORMAL,
    )


def _node() -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-trade",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name="trade_packager",
        node_type="trade",
        output_contract=TRADE_RECOMMENDATION_OUTPUT_CONTRACT,
        output_schema_version=WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
        status="succeeded",
        success=True,
        outputs=cast(
            JsonObject,
            {
                "symbol": "SPY",
                "regime": "bullish",
                "confidence": 0.74,
                "features": {
                    "trade_quality_score": 0.82,
                    "risk_pressure": 0.3,
                    "stop_distance": 1.5,
                    "take_profit_distance": 3.0,
                    "trade_intent": {
                        "direction": "long",
                        "entry_bias": "pullback",
                        "position_sizing_hint": "small",
                        "stop_distance": 1.5,
                        "take_profit_distance": 3.0,
                        "reasoning": "Constructive setup with contained risk.",
                    },
                    "thesis": "Constructive setup with contained risk.",
                },
            },
        ),
        metadata={"quality_status": "normal"},
        errors_json=(),
        started_at=datetime(2026, 7, 10, 13, 29, tzinfo=UTC),
        completed_at=datetime(2026, 7, 10, 13, 31, tzinfo=UTC),
        duration_seconds=120.0,
    )


def _node_with_model_claims() -> CompletedNodeOutputRecord:
    node = _node()
    outputs = dict(node.outputs)
    features = dict(cast(Mapping[str, JsonValue], outputs["features"]))
    features["risk_authority"] = cast(
        JsonValue,
        {
            "risk_tier": "baseline",
            "authority_effect": "execution_decision",
            "governance_approved": True,
            "production_ready": True,
            "residual_risk_accepted": True,
        },
    )
    outputs["features"] = cast(JsonValue, features)
    return replace(node, outputs=cast(JsonObject, outputs))
