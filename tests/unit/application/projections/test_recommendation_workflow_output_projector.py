from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest

from application.decision_evidence import (
    DecisionEvidenceClaimBindingService,
    RecommendationClaimEvidenceBindingTarget,
    StaleDecisionEvidenceSourceError,
)
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
    RecommendationClaimEvidenceLinkRecord,
    RecommendationPersistenceBundle,
    RecommendationPersistenceRepository,
    RecommendationPersistenceResult,
)
from domain.authority import GateProfile, RiskTier
from domain.decision_evidence import (
    DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY,
    ClaimMaterialityTier,
)
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


@pytest.mark.asyncio
async def test_trade_recommendation_projector_attaches_claim_packet_refs() -> None:
    repository = _FakeRecommendationRepository()
    claim_binding_service = _FakeRecommendationClaimBindingService(
        (
            RecommendationClaimEvidenceLinkRecord(
                link_id=(
                    "recommendation:exec-1:SPY:trade_recommendation:claim_evidence:recommendation:exec-1:SPY:trade_recommendation:rationale:trade_recommendation:"
                    "recommendation:exec-1:SPY:trade_recommendation:rationale:trade_recommendation:claim:claim-1:packet-1:claim-1"
                ),
                recommendation_id="recommendation:exec-1:SPY:trade_recommendation",
                rationale_id="recommendation:exec-1:SPY:trade_recommendation:rationale:trade_recommendation",
                claim_target_id="recommendation:exec-1:SPY:trade_recommendation:rationale:trade_recommendation:claim:claim-1",
                packet_id="packet-1",
                packet_claim_id="claim-1",
                risk_tier=RiskTier.ENHANCED,
                material=True,
                supporting_evidence_ids=("evidence-1",),
                reconstruction_reference_ids=("workflow-node",),
                uncertainty_ids=("uncertainty-1",),
                limitation_ids=("limitation-1",),
            ),
        )
    )
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
        claim_binding_service=cast(
            DecisionEvidenceClaimBindingService,
            claim_binding_service,
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_claim_references())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 4
    assert len(repository.bundles[0].claim_evidence_links) == 1
    link = repository.bundles[0].claim_evidence_links[0]
    assert link.packet_id == "packet-1"
    assert link.packet_claim_id == "claim-1"
    assert link.uncertainty_ids == ("uncertainty-1",)
    assert link.limitation_ids == ("limitation-1",)
    assert claim_binding_service.targets == (
        RecommendationClaimEvidenceBindingTarget(
            rationale_id="recommendation:exec-1:SPY:trade_recommendation:rationale:trade_recommendation",
            claim_target_id="recommendation:exec-1:SPY:trade_recommendation:rationale:trade_recommendation:claim:claim-1",
            claim_references=claim_binding_service.targets[0].claim_references,
        ),
    )
    claim_metadata = cast(
        dict[str, JsonValue],
        repository.bundles[0]
        .rationales[0]
        .metadata[DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY],
    )
    assert claim_metadata["packet_ids"] == ["packet-1"]
    assert claim_metadata["reconstruction_reference_ids"] == ["workflow-node"]
    claim_references = cast(
        list[dict[str, JsonValue]],
        claim_metadata["claim_references"],
    )
    assert claim_references[0]["claim_id"] == "claim-1"
    assert claim_references[0]["supporting_evidence_ids"] == ["evidence-1"]
    assert claim_references[0]["uncertainty_ids"] == ["uncertainty-1"]
    assert claim_references[0]["limitation_ids"] == ["limitation-1"]
    serialized = str(claim_metadata)
    assert "canonical evidence summary" not in serialized
    assert "raw_payload" not in serialized


@pytest.mark.asyncio
async def test_trade_projector_fails_closed_for_missing_material_binding() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
        claim_binding_service=cast(
            DecisionEvidenceClaimBindingService,
            _FakeRecommendationClaimBindingService(()),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_claim_references())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_type == "ClaimEvidenceBindingError"
    assert "material claim 'claim-1'" in str(outcome.error_message)
    assert "lacks required decision-evidence packet binding" in str(
        outcome.error_message
    )
    assert repository.bundles == []


@pytest.mark.asyncio
async def test_trade_projector_fails_closed_for_invalid_material_binding() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
        claim_binding_service=cast(
            DecisionEvidenceClaimBindingService,
            _FakeRecommendationClaimBindingService(
                (_recommendation_claim_link(packet_id="packet-substituted"),)
            ),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_claim_references())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_type == "ClaimEvidenceBindingError"
    assert "unexpected material decision-evidence packet binding" in str(
        outcome.error_message
    )
    assert repository.bundles == []


@pytest.mark.asyncio
async def test_trade_projector_fails_closed_for_substituted_material_link() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
        claim_binding_service=cast(
            DecisionEvidenceClaimBindingService,
            _FakeRecommendationClaimBindingService(
                (
                    replace(
                        _recommendation_claim_link(),
                        reconstruction_reference_ids=("workflow-node-substituted",),
                    ),
                )
            ),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_claim_references())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_type == "ClaimEvidenceBindingError"
    assert (
        "reconstruction references do not match required canonical claim reference"
        in str(outcome.error_message)
    )
    assert repository.bundles == []


@pytest.mark.asyncio
async def test_trade_projector_allows_contextual_claim_without_binding() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_contextual_claim_reference())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert repository.bundles[0].claim_evidence_links == ()
    claim_metadata = cast(
        dict[str, JsonValue],
        repository.bundles[0]
        .rationales[0]
        .metadata[DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY],
    )
    claim_references = cast(
        list[dict[str, JsonValue]],
        claim_metadata["claim_references"],
    )
    assert claim_references[0]["materiality"] == ClaimMaterialityTier.CONTEXTUAL.value


@pytest.mark.asyncio
async def test_trade_projector_fails_closed_for_stale_claim_evidence() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
        claim_binding_service=cast(
            DecisionEvidenceClaimBindingService,
            _FailingRecommendationClaimBindingService(
                StaleDecisionEvidenceSourceError("stale evidence")
            ),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_claim_references())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_type == "StaleDecisionEvidenceSourceError"
    assert outcome.error_message == "stale evidence"
    assert repository.bundles == []


@pytest.mark.asyncio
async def test_trade_projector_fails_closed_for_unsupported_claims() -> None:
    repository = _FakeRecommendationRepository()
    projector = TradeRecommendationWorkflowOutputProjector(
        RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, repository),
        ),
    )

    outcome = await projector.project(
        _projector_request(node=_node_with_unsupported_claim_reference())
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_type == "UnsupportedMaterialClaimError"
    assert outcome.error_message == (
        "material claim 'claim-unsupported' lacks supporting evidence."
    )
    assert repository.bundles == []


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
                + len(bundle.claim_evidence_links)
            ),
        )


class _FakeRecommendationClaimBindingService:
    def __init__(
        self,
        links: tuple[RecommendationClaimEvidenceLinkRecord, ...],
    ) -> None:
        self.links = links
        self.targets: tuple[RecommendationClaimEvidenceBindingTarget, ...] = ()

    async def bind_recommendation_claims(
        self,
        *,
        recommendation_id: str,
        targets: tuple[RecommendationClaimEvidenceBindingTarget, ...],
    ) -> tuple[RecommendationClaimEvidenceLinkRecord, ...]:
        self.targets = tuple(targets)
        return self.links


class _FailingRecommendationClaimBindingService:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def bind_recommendation_claims(
        self,
        *,
        recommendation_id: str,
        targets: tuple[RecommendationClaimEvidenceBindingTarget, ...],
    ) -> tuple[RecommendationClaimEvidenceLinkRecord, ...]:
        raise self.exc


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


def _claim_reference_metadata(
    *,
    supporting_evidence_ids: list[str] | None = None,
    materiality: ClaimMaterialityTier = ClaimMaterialityTier.READINESS_GATING,
) -> dict[str, JsonValue]:
    supporting_ids = (
        ["evidence-1"] if supporting_evidence_ids is None else supporting_evidence_ids
    )
    return cast(
        dict[str, JsonValue],
        {
            "schema_version": 1,
            "packet_ids": ["packet-1"],
            "reconstruction_reference_ids": ["workflow-node"],
            "claim_references": [
                {
                    "schema_version": 1,
                    "packet_id": "packet-1",
                    "output_id": "node-output-trade",
                    "claim_id": ("claim-1" if supporting_ids else "claim-unsupported"),
                    "risk_tier": RiskTier.ENHANCED.value,
                    "material": materiality.gates_readiness,
                    "materiality": materiality.value,
                    "supporting_evidence_ids": supporting_ids,
                    "reconstruction_reference_ids": ["workflow-node"],
                    "uncertainty_ids": ["uncertainty-1"],
                    "limitation_ids": ["limitation-1"],
                }
            ],
        },
    )


def _node_with_claim_references() -> CompletedNodeOutputRecord:
    node = _node()
    outputs = dict(node.outputs)
    features = dict(cast(Mapping[str, JsonValue], outputs["features"]))
    features[DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY] = cast(
        JsonValue,
        _claim_reference_metadata(),
    )
    outputs["features"] = cast(JsonValue, features)
    return replace(node, outputs=cast(JsonObject, outputs))


def _node_with_contextual_claim_reference() -> CompletedNodeOutputRecord:
    node = _node()
    outputs = dict(node.outputs)
    features = dict(cast(Mapping[str, JsonValue], outputs["features"]))
    features[DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY] = cast(
        JsonValue,
        _claim_reference_metadata(
            supporting_evidence_ids=[],
            materiality=ClaimMaterialityTier.CONTEXTUAL,
        ),
    )
    outputs["features"] = cast(JsonValue, features)
    return replace(node, outputs=cast(JsonObject, outputs))


def _node_with_unsupported_claim_reference() -> CompletedNodeOutputRecord:
    node = _node()
    outputs = dict(node.outputs)
    features = dict(cast(Mapping[str, JsonValue], outputs["features"]))
    features[DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY] = cast(
        JsonValue,
        _claim_reference_metadata(supporting_evidence_ids=[]),
    )
    outputs["features"] = cast(JsonValue, features)
    return replace(node, outputs=cast(JsonObject, outputs))


def _recommendation_claim_link(
    *,
    packet_id: str = "packet-1",
    packet_claim_id: str = "claim-1",
) -> RecommendationClaimEvidenceLinkRecord:
    return RecommendationClaimEvidenceLinkRecord(
        link_id=(
            "recommendation:exec-1:SPY:trade_recommendation:claim_evidence:"
            "recommendation:exec-1:SPY:trade_recommendation:rationale:"
            "trade_recommendation:recommendation:exec-1:SPY:trade_recommendation:"
            f"rationale:trade_recommendation:claim:claim-1:{packet_id}:"
            f"{packet_claim_id}"
        ),
        recommendation_id="recommendation:exec-1:SPY:trade_recommendation",
        rationale_id=(
            "recommendation:exec-1:SPY:trade_recommendation:rationale:"
            "trade_recommendation"
        ),
        claim_target_id=(
            "recommendation:exec-1:SPY:trade_recommendation:rationale:"
            "trade_recommendation:claim:claim-1"
        ),
        packet_id=packet_id,
        packet_claim_id=packet_claim_id,
        risk_tier=RiskTier.ENHANCED,
        material=True,
        supporting_evidence_ids=("evidence-1",),
        reconstruction_reference_ids=("workflow-node",),
        uncertainty_ids=("uncertainty-1",),
        limitation_ids=("limitation-1",),
    )
