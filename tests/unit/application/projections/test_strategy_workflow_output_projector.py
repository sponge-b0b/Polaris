from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import cast

import pytest

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.persistence.lineage import LineagePersistenceService
from application.persistence.recommendations import RecommendationPersistenceService
from application.persistence.strategy import StrategyPersistenceService
from application.projections.workflow_outputs.projection_identity import (
    build_workflow_output_projection_lineage,
)
from application.projections.workflow_outputs.projection_models import (
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRequest,
)
from application.projections.workflow_outputs.projectors import (
    StrategyHypothesisWorkflowOutputProjector,
    StrategySynthesisWorkflowOutputProjector,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
    CompletedRunExecutionMode,
    CompletedRunRecord,
    JsonObject,
    JsonValue,
)
from core.storage.persistence.decision_evidence import (
    DecisionEvidencePacketPersistenceRepository,
    DecisionEvidencePacketPersistenceResult,
    DecisionEvidencePacketRecord,
)
from core.storage.persistence.lineage import (
    PersistenceLineageLinkRecord,
    PersistenceLineageLinkRepository,
    PersistenceLineageLinkResult,
    PersistenceLineageTraversalRequest,
    PersistenceLineageTraversalResult,
    PersistenceRecordIdentity,
)
from core.storage.persistence.recommendations import (
    RecommendationPersistenceBundle,
    RecommendationPersistenceRepository,
    RecommendationPersistenceResult,
)
from core.storage.persistence.strategy import (
    StrategyHypothesisPersistenceResult,
    StrategyHypothesisRecord,
    StrategyPersistenceBundle,
    StrategyPersistenceRepository,
    StrategyPersistenceResult,
)
from domain.authority import GateProfile, RiskTier
from domain.workflow_outputs import (
    STRATEGY_BULL_HYPOTHESIS_OUTPUT_CONTRACT,
    STRATEGY_SYNTHESIS_OUTPUT_CONTRACT,
    WORKFLOW_OUTPUT_SCHEMA_VERSION_V1,
)


def _authority_metadata(metadata: JsonObject) -> Mapping[str, JsonValue]:
    return cast(Mapping[str, JsonValue], metadata["risk_authority"])


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
    lineage_repository = _FakeLineageRepository()
    packet_repository = _FakeDecisionEvidencePacketRepository()
    run = _run()
    bull_node = _bull_node()
    synthesis_node = _synthesis_node()
    bundle = CompletedRunBundle(run=run, node_outputs=(bull_node, synthesis_node))
    lineage_service = LineagePersistenceService(
        cast(PersistenceLineageLinkRepository, lineage_repository),
    )
    packet_service = DecisionEvidencePacketPersistenceService(
        repository=cast(
            DecisionEvidencePacketPersistenceRepository,
            packet_repository,
        ),
        completed_run_archive=cast(
            CompletedRunArchive, _FakeCompletedRunArchive(bundle)
        ),
    )
    projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        recommendation_persistence_service=RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, recommendation_repository),
        ),
        decision_evidence_packet_persistence_service=packet_service,
        lineage_persistence_service=lineage_service,
    )

    outcome = await projector.project(
        _projector_request(
            synthesis_node,
            run=run,
            bundle=bundle,
        )
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.records_written == 9
    assert set(packet_repository.records) == {"strategy-packet-1"}
    packet = await packet_service.reconstruct_packet("strategy-packet-1")
    assert packet.packet_id == "strategy-packet-1"
    assert packet.output_id == "node-output-synthesis"
    assert {constraint.constraint_id for constraint in packet.constraints} == {
        "bull:assumption:bull-liquidity"
    }
    assert {limitation.limitation_id for limitation in packet.limitations} == {
        "bull:invalidation:bull-invalidated"
    }
    assert packet.uncertainties[0].evidence_ids == ("bull-momentum",)
    evidence = packet.evidence[0]
    assert evidence.evidence_id == "bull-momentum"
    assert evidence.support_snapshot is not None
    assert evidence.support_snapshot.snapshot_id == "bull-momentum:support-snapshot"
    assert "node-output-bull" in evidence.support_snapshot.redacted_content
    assert len(strategy_repository.bundles) == 1
    strategy_bundle = strategy_repository.bundles[0]
    assert strategy_bundle.decision.symbol == "SPY"
    assert strategy_bundle.decision.selected_perspective == "bull"
    assert "evidence_packet_ids" not in strategy_bundle.decision.metadata
    assert "strategy-packet-1" not in str(strategy_bundle.decision.metadata)
    assert len(strategy_bundle.hypotheses) == 1
    assert strategy_bundle.hypotheses[0].perspective == "bull"
    assert len(strategy_bundle.evaluations) == 1

    assert len(recommendation_repository.bundles) == 1
    recommendation_bundle = recommendation_repository.bundles[0]
    assert recommendation_bundle.recommendation.status == "strategy_recommendation"
    assert recommendation_bundle.recommendation.metadata["strategy_decision_id"]
    assert "evidence_packet_ids" not in recommendation_bundle.recommendation.metadata
    assert "strategy-packet-1" not in str(recommendation_bundle.recommendation.metadata)
    assert "evidence_packet_ids" not in recommendation_bundle.rationales[0].metadata
    assert "strategy-packet-1" not in str(recommendation_bundle.rationales[0].metadata)
    assert recommendation_bundle.rationales[0].rationale_type == "strategy_synthesis"

    decision_authority = _authority_metadata(strategy_bundle.decision.metadata)
    assert decision_authority["risk_tier"] == RiskTier.VIGILANT.value
    assert decision_authority["gate_profile"] == (
        GateProfile.VIGILANT_DECISION_EVIDENCE.value
    )
    assert decision_authority["canonical_owner"] == "strategy_service"
    assert decision_authority["intended_sink"] == "durable_domain_record"

    recommendation_authority = _authority_metadata(
        recommendation_bundle.recommendation.metadata
    )
    assert recommendation_authority["risk_tier"] == RiskTier.VIGILANT.value
    assert recommendation_authority["canonical_owner"] == "recommendation_service"
    assert recommendation_authority["intended_sink"] == "recommendation"

    rationale_authority = _authority_metadata(
        recommendation_bundle.rationales[0].metadata
    )
    assert rationale_authority["risk_tier"] == RiskTier.ENHANCED.value
    assert rationale_authority["authority_effect"] == "advisory_context"

    packet_identity = PersistenceRecordIdentity(
        record_type="decision_evidence_packet",
        record_id="strategy-packet-1",
    )
    lineage_links = await lineage_service.list_links_for_target(packet_identity)
    assert lineage_links
    lineage_sources = {
        (link.source_record.record_type, link.source_record.record_id): link
        for link in lineage_links
    }
    assert set(lineage_sources) == {
        (
            "strategy_synthesis_decision",
            strategy_bundle.decision.decision_id,
        ),
        (
            "recommendation",
            recommendation_bundle.recommendation.recommendation_id,
        ),
        (
            "recommendation_rationale",
            recommendation_bundle.rationales[0].rationale_id,
        ),
    }
    assert {link.relationship_type for link in lineage_links} == {
        "supported_by_decision_evidence_packet"
    }
    assert all(link.target_record == packet_identity for link in lineage_links)
    assert all(
        link.metadata["projection_source"] == "strategy_synthesis"
        for link in lineage_links
    )
    assert all(
        link.metadata["node_output_id"] == "node-output-synthesis"
        for link in lineage_links
    )


@pytest.mark.asyncio
async def test_strategy_synthesis_projector_ignores_model_authority_claims() -> None:
    strategy_repository = _FakeStrategyRepository()
    recommendation_repository = _FakeRecommendationRepository()
    lineage_repository = _FakeLineageRepository()
    packet_repository = _FakeDecisionEvidencePacketRepository()
    run = _run()
    bull_node = _bull_node()
    synthesis_node = _synthesis_node_with_model_claims()
    bundle = CompletedRunBundle(run=run, node_outputs=(bull_node, synthesis_node))
    lineage_service = LineagePersistenceService(
        cast(PersistenceLineageLinkRepository, lineage_repository),
    )
    packet_service = DecisionEvidencePacketPersistenceService(
        repository=cast(
            DecisionEvidencePacketPersistenceRepository,
            packet_repository,
        ),
        completed_run_archive=cast(
            CompletedRunArchive, _FakeCompletedRunArchive(bundle)
        ),
    )
    projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        recommendation_persistence_service=RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, recommendation_repository),
        ),
        decision_evidence_packet_persistence_service=packet_service,
        lineage_persistence_service=lineage_service,
    )

    outcome = await projector.project(
        _projector_request(
            synthesis_node,
            run=run,
            bundle=bundle,
        )
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    strategy_bundle = strategy_repository.bundles[0]
    ignored_claims = [
        "authority_effect",
        "governance_approved",
        "production_ready",
        "residual_risk_accepted",
        "risk_tier",
    ]
    decision_authority = _authority_metadata(strategy_bundle.decision.metadata)
    assert decision_authority["risk_tier"] == RiskTier.VIGILANT.value
    assert decision_authority["authority_effect"] == ("deterministic_platform_decision")
    assert decision_authority["ignored_model_authority_claims"] == ignored_claims
    assert "governance_approved" not in strategy_bundle.decision.metadata
    assert "production_ready" not in strategy_bundle.decision.metadata
    assert "residual_risk_accepted" not in strategy_bundle.decision.metadata

    recommendation_bundle = recommendation_repository.bundles[0]
    recommendation_authority = _authority_metadata(
        recommendation_bundle.recommendation.metadata
    )
    assert recommendation_authority["risk_tier"] == RiskTier.VIGILANT.value
    assert recommendation_authority["authority_effect"] == "canonical_record"
    assert recommendation_authority["ignored_model_authority_claims"] == ignored_claims
    rationale_authority = _authority_metadata(
        recommendation_bundle.rationales[0].metadata
    )
    assert rationale_authority["risk_tier"] == RiskTier.ENHANCED.value
    assert rationale_authority["authority_effect"] == "advisory_context"
    assert rationale_authority["ignored_model_authority_claims"] == ignored_claims


@pytest.mark.asyncio
async def test_strategy_synthesis_projector_fails_when_lineage_persistence_fails() -> (
    None
):
    strategy_repository = _FakeStrategyRepository()
    recommendation_repository = _FakeRecommendationRepository()
    lineage_repository = _FakeLineageRepository(fail_after=0)
    packet_repository = _FakeDecisionEvidencePacketRepository()
    lineage_service = LineagePersistenceService(
        cast(PersistenceLineageLinkRepository, lineage_repository),
    )
    run = _run()
    bull_node = _bull_node()
    synthesis_node = _synthesis_node()
    bundle = CompletedRunBundle(run=run, node_outputs=(bull_node, synthesis_node))
    packet_service = DecisionEvidencePacketPersistenceService(
        repository=cast(
            DecisionEvidencePacketPersistenceRepository,
            packet_repository,
        ),
        completed_run_archive=cast(
            CompletedRunArchive, _FakeCompletedRunArchive(bundle)
        ),
    )
    projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        recommendation_persistence_service=RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, recommendation_repository),
        ),
        decision_evidence_packet_persistence_service=packet_service,
        lineage_persistence_service=lineage_service,
    )

    outcome = await projector.project(
        _projector_request(
            synthesis_node,
            run=run,
            bundle=bundle,
        )
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_message == (
        "Evidence packet lineage persistence failed: lineage unavailable"
    )
    assert len(strategy_repository.bundles) == 1
    assert len(recommendation_repository.bundles) == 1
    assert lineage_repository.links == []


@pytest.mark.asyncio
async def test_strategy_synthesis_projector_fails_closed_without_support_evidence() -> (
    None
):
    strategy_repository = _FakeStrategyRepository()
    recommendation_repository = _FakeRecommendationRepository()
    lineage_repository = _FakeLineageRepository()
    packet_repository = _FakeDecisionEvidencePacketRepository()
    run = _run()
    bull_node = _bull_node_without_support_evidence()
    synthesis_node = _synthesis_node()
    bundle = CompletedRunBundle(run=run, node_outputs=(bull_node, synthesis_node))
    lineage_service = LineagePersistenceService(
        cast(PersistenceLineageLinkRepository, lineage_repository),
    )
    packet_service = DecisionEvidencePacketPersistenceService(
        repository=cast(
            DecisionEvidencePacketPersistenceRepository,
            packet_repository,
        ),
        completed_run_archive=cast(
            CompletedRunArchive, _FakeCompletedRunArchive(bundle)
        ),
    )
    projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        recommendation_persistence_service=RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, recommendation_repository),
        ),
        decision_evidence_packet_persistence_service=packet_service,
        lineage_persistence_service=lineage_service,
    )

    outcome = await projector.project(
        _projector_request(synthesis_node, run=run, bundle=bundle)
    )

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_message is not None
    assert "lacks supporting evidence references" in outcome.error_message
    assert strategy_repository.bundles == []
    assert recommendation_repository.bundles == []
    assert packet_repository.records == {}
    assert lineage_repository.links == []


@pytest.mark.asyncio
async def test_strategy_synthesis_projector_fails_closed_without_snapshots() -> None:
    strategy_repository = _FakeStrategyRepository()
    recommendation_repository = _FakeRecommendationRepository()
    lineage_repository = _FakeLineageRepository()
    packet_repository = _FakeDecisionEvidencePacketRepository()
    run = _run()
    synthesis_node = _synthesis_node()
    lineage_service = LineagePersistenceService(
        cast(PersistenceLineageLinkRepository, lineage_repository),
    )
    packet_service = DecisionEvidencePacketPersistenceService(
        repository=cast(
            DecisionEvidencePacketPersistenceRepository,
            packet_repository,
        ),
        completed_run_archive=cast(CompletedRunArchive, _FakeCompletedRunArchive(None)),
    )
    projector = StrategySynthesisWorkflowOutputProjector(
        strategy_persistence_service=StrategyPersistenceService(
            cast(StrategyPersistenceRepository, strategy_repository),
        ),
        recommendation_persistence_service=RecommendationPersistenceService(
            cast(RecommendationPersistenceRepository, recommendation_repository),
        ),
        decision_evidence_packet_persistence_service=packet_service,
        lineage_persistence_service=lineage_service,
    )

    outcome = await projector.project(_projector_request(synthesis_node, run=run))

    assert outcome.status is WorkflowOutputProjectionStatus.FAILED
    assert outcome.error_message is not None
    assert "retained support snapshots" in outcome.error_message
    assert strategy_repository.bundles == []
    assert recommendation_repository.bundles == []
    assert packet_repository.records == {}
    assert lineage_repository.links == []


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


class _FakeLineageRepository:
    def __init__(self, *, fail_after: int | None = None) -> None:
        self.links: list[PersistenceLineageLinkRecord] = []
        self._fail_after = fail_after

    async def persist_lineage_link(
        self,
        link: PersistenceLineageLinkRecord,
    ) -> PersistenceLineageLinkResult:
        if self._fail_after is not None and len(self.links) >= self._fail_after:
            return PersistenceLineageLinkResult.failed("lineage unavailable")
        self.links.append(link)
        return PersistenceLineageLinkResult.succeeded(link_id=link.link_id)

    async def get_lineage_link(
        self,
        link_id: str,
    ) -> PersistenceLineageLinkRecord | None:
        for link in self.links:
            if link.link_id == link_id:
                return link
        return None

    async def list_links_for_source(
        self,
        source_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        return tuple(link for link in self.links if link.source_record == source_record)

    async def list_links_for_target(
        self,
        target_record: PersistenceRecordIdentity,
    ) -> Sequence[PersistenceLineageLinkRecord]:
        return tuple(link for link in self.links if link.target_record == target_record)

    async def traverse_lineage(
        self,
        request: PersistenceLineageTraversalRequest,
    ) -> PersistenceLineageTraversalResult:
        raise NotImplementedError


class _FakeDecisionEvidencePacketRepository:
    def __init__(self) -> None:
        self.records: dict[str, DecisionEvidencePacketRecord] = {}

    async def persist_packet_record(
        self,
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacketPersistenceResult:
        self.records[record.packet_id] = record
        return DecisionEvidencePacketPersistenceResult.succeeded(
            record.packet_id,
        )

    async def get_packet_record(
        self,
        packet_id: str,
    ) -> DecisionEvidencePacketRecord | None:
        return self.records.get(packet_id)


class _FakeCompletedRunArchive:
    def __init__(self, bundle: CompletedRunBundle | None) -> None:
        self._bundle = bundle

    async def archive_run(
        self,
        bundle: CompletedRunBundle,
    ) -> None:
        self._bundle = bundle

    async def load_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> CompletedRunBundle | None:
        if self._bundle is None:
            return None
        if (
            self._bundle.run.workflow_name == workflow_name
            and self._bundle.run.execution_id == execution_id
        ):
            return self._bundle
        return None

    async def list_archived_runs(
        self,
        workflow_name: str,
    ) -> list[str]:
        if self._bundle is None or self._bundle.run.workflow_name != workflow_name:
            return []
        return [self._bundle.run.execution_id]

    async def delete_archived_run(
        self,
        workflow_name: str,
        execution_id: str,
    ) -> None:
        if (
            self._bundle is not None
            and self._bundle.run.workflow_name == workflow_name
            and self._bundle.run.execution_id == execution_id
        ):
            self._bundle = None

    async def cleanup_archived_runs(
        self,
        max_age_days: int | None = None,
        max_count: int | None = None,
    ) -> int:
        return 0


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


def _bull_node_without_support_evidence() -> CompletedNodeOutputRecord:
    from dataclasses import replace

    node = _bull_node()
    payload = _bull_hypothesis_payload()
    payload["supporting_evidence"] = []
    payload["contradicting_evidence"] = [
        {
            "evidence_id": "bull-contradiction",
            "source": "strategy-runtime",
            "name": "contradicting evidence",
            "observed_value": 0.45,
            "strength": 0.50,
            "reliability": 0.70,
            "supports": [],
            "contradicts": ["bull"],
            "explanation": "Contradicting retained evidence is not support.",
        }
    ]
    payload["key_assumptions"] = [
        {
            "assumption_id": "bull-liquidity",
            "perspective": "bull",
            "description": "Liquidity remains supportive.",
            "confidence": 0.70,
            "evidence_ids": ["bull-contradiction"],
        }
    ]
    payload["invalidation_conditions"] = []
    return replace(
        node,
        outputs=cast(JsonObject, {"strategy_hypothesis": payload}),
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
        "supporting_evidence": [
            {
                "evidence_id": "bull-momentum",
                "source": "strategy-runtime",
                "name": "bull momentum",
                "observed_value": 0.74,
                "strength": 0.82,
                "reliability": 0.88,
                "supports": ["bull"],
                "contradicts": [],
                "explanation": "Momentum remains constructive.",
            }
        ],
        "contradicting_evidence": [],
        "key_assumptions": [
            {
                "assumption_id": "bull-liquidity",
                "perspective": "bull",
                "description": "Liquidity remains supportive.",
                "confidence": 0.70,
                "evidence_ids": ["bull-momentum"],
            }
        ],
        "invalidation_conditions": [
            {
                "condition_id": "bull-invalidated",
                "perspective": "bull",
                "description": "Trend exhaustion is elevated.",
                "observed_value": 0.91,
                "operator": "gte",
                "threshold": 0.90,
                "evidence_id": "bull-momentum",
            }
        ],
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
                "synthesis_weight": 1.0,
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
        "evidence_packet_ids": ["strategy-packet-1"],
    }


def _synthesis_node_with_model_claims() -> CompletedNodeOutputRecord:
    from dataclasses import replace

    node = _synthesis_node()
    outputs = dict(node.outputs)
    features = dict(cast(Mapping[str, JsonValue], outputs["features"]))
    features["risk_authority"] = cast(
        JsonValue,
        {
            "risk_tier": "baseline",
            "authority_effect": "governance_decision",
            "governance_approved": True,
            "production_ready": True,
            "residual_risk_accepted": True,
        },
    )
    outputs["features"] = cast(JsonValue, features)
    return replace(node, outputs=cast(JsonObject, outputs))
