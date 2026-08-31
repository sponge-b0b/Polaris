from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import cast

import pytest

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.evaluations.enhanced_readiness import (
    EnhancedReadinessRequest,
    EnhancedReadinessService,
)
from application.evaluations.evaluation_datasets import (
    CANONICAL_EVALUATION_DATASET_DEFINITIONS,
    EVALUATION_DATASET_VERSION,
)
from application.evaluations.model_replacement_gate import (
    MODEL_REPLACEMENT_DATASET_SLICE_NAME,
    ModelReplacementGateSection,
    ModelReplacementGateSectionResult,
    ModelReplacementGateStatus,
    ModelReplacementValidationMode,
    ModelReplacementValidationRequest,
    ModelReplacementValidationResult,
)
from application.evaluations.readiness_gate import (
    READINESS_GATE_ARTIFACT_TYPE,
    ReadinessGateService,
    ReadinessSection,
    ReadinessSectionStatus,
    ReadinessVerdictStatus,
)
from application.evaluations.readiness_profiles import (
    ReadinessRunMode,
    readiness_profile_for_gate,
)
from application.evaluations.risk_authority_gate import RiskAuthorityGateEvidence
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
    LangfuseProjectionStatus,
)
from domain.authority import GateProfile, RiskTier, classify_risk_authority
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
)
from domain.evaluation import EvaluationStatus, EvaluationTargetType
from tests.helpers.risk_authority_examples import authority_input_for_tier


@dataclass
class _FakeRepository:
    datasets: dict[str, EvaluationDatasetRecord] = field(default_factory=dict)
    runs: dict[str, EvaluationRunRecord] = field(default_factory=dict)
    metrics: dict[str, tuple[EvaluationMetricResultRecord, ...]] = field(
        default_factory=dict
    )
    artifacts: list[EvaluationArtifactRecord] = field(default_factory=list)

    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None:
        return self.datasets.get(dataset_id)

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None:
        return self.runs.get(run_id)

    async def list_metric_results(
        self,
        run_id: str,
    ) -> tuple[EvaluationMetricResultRecord, ...]:
        return self.metrics.get(run_id, ())

    async def list_artifacts(
        self,
        run_id: str,
    ) -> tuple[EvaluationArtifactRecord, ...]:
        return tuple(item for item in self.artifacts if item.run_id == run_id)

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord:
        self.artifacts.append(record)
        return record


@dataclass(frozen=True)
class _PacketPersistenceResult:
    packet_id: str
    success: bool = True
    records_persisted: int = 1


@dataclass
class _FakePacketPersistence:
    packets: dict[str, DecisionEvidencePacket] = field(default_factory=dict)

    async def persist_packet(
        self,
        packet: DecisionEvidencePacket,
    ) -> _PacketPersistenceResult:
        self.packets[packet.packet_id] = packet
        return _PacketPersistenceResult(packet.packet_id)

    async def reconstruct_packet(self, packet_id: str) -> DecisionEvidencePacket:
        return self.packets[packet_id]


def _packet() -> DecisionEvidencePacket:
    return DecisionEvidencePacket(
        packet_id="enhanced-packet-1",
        output_id="rag-answer-1",
        authority=classify_risk_authority(authority_input_for_tier(RiskTier.ENHANCED)),
        claims=(
            MaterialClaim(
                claim_id="claim-1",
                text="Supported material claim.",
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=("rag-source-1",),
                ),
            ),
        ),
        evidence=(
            EvidenceReference(
                evidence_id="rag-source-1",
                kind=EvidenceReferenceKind.WORKFLOW_NODE_OUTPUT,
                reconstruction_reference_ids=("workflow-node-1",),
                summary="Persisted source evidence.",
                support_snapshot=SupportingEvidenceSnapshot(
                    snapshot_id="snapshot-1",
                    summary="Persisted source evidence.",
                    redacted_content="Supported material claim evidence.",
                    source_label="workflow_node_output:workflow-node-1",
                ),
            ),
        ),
        reconstruction_references=(
            ReconstructionReference(
                reference_id="workflow-node-1",
                kind=ReconstructionReferenceKind.WORKFLOW_NODE_OUTPUT,
                record_id="workflow-run-1:node:rag",
            ),
        ),
        retention=EvidenceRetentionRequirement(
            retain_until="2031-08-31T00:00:00Z",
            policy_id="enhanced-provenance-5y",
        ),
        workflow_name="rag_answer",
        workflow_definition_fingerprint="rag-answer-definition-v1",
        execution_id="workflow-run-1",
    )


def _profile():
    return readiness_profile_for_gate(GateProfile.ENHANCED_PROVENANCE)


def _rag_answer_dataset_definition():
    return next(
        definition
        for definition in CANONICAL_EVALUATION_DATASET_DEFINITIONS
        if definition.target_type is EvaluationTargetType.RAG_ANSWER
    )


def _seed_repository() -> _FakeRepository:
    repository = _FakeRepository()
    definition = _rag_answer_dataset_definition()
    repository.datasets[definition.reference.dataset_id] = EvaluationDatasetRecord(
        dataset_id=definition.reference.dataset_id,
        name=definition.reference.name,
        version=definition.reference.version,
        target_type=definition.target_type,
        source_lineage=definition.source_lineage,
        deterministic_fixture_uri=definition.deterministic_fixture_uri,
        threshold_profile=definition.threshold_profile,
    )
    for run_id in ("current-run", "reference-run"):
        repository.runs[run_id] = EvaluationRunRecord(
            run_id=run_id,
            target_type=EvaluationTargetType.RAG_ANSWER,
            status=EvaluationStatus.PASSED,
            evaluator_provider="fake-provider",
            evaluator_model="fake-judge-v1",
            dataset_id=definition.reference.dataset_id,
            case_ids=(f"{run_id}-case",),
            langfuse_projection_status=LangfuseProjectionStatus.PROJECTED,
        )

    current: list[EvaluationMetricResultRecord] = []
    reference: list[EvaluationMetricResultRecord] = []
    for index, requirement in enumerate(
        item
        for item in _profile().metric_requirements
        if item.applies_to(EvaluationTargetType.RAG_ANSWER)
    ):
        current_score = min(1.0, requirement.minimum_score + 0.08)
        reference_score = min(1.0, current_score + 0.01)
        for run_id, score, records in (
            ("current-run", current_score, current),
            ("reference-run", reference_score, reference),
        ):
            records.append(
                EvaluationMetricResultRecord(
                    metric_result_id=f"{run_id}-metric-{index}",
                    run_id=run_id,
                    case_id=f"{run_id}-case",
                    metric_name=requirement.metric_name,
                    score=score,
                    status=EvaluationStatus.PASSED,
                    evaluator_provider="fake-provider",
                    evaluator_model="fake-judge-v1",
                    threshold=requirement.minimum_score,
                    threshold_version=requirement.version,
                    passed=True,
                    langfuse_projection_status=LangfuseProjectionStatus.PROJECTED,
                )
            )
    repository.metrics["current-run"] = tuple(current)
    repository.metrics["reference-run"] = tuple(reference)
    for artifact_type in (
        "baseline_architecture_regression",
        "structured_output_conformance",
    ):
        repository.artifacts.append(
            EvaluationArtifactRecord(
                artifact_id=f"artifact:{artifact_type}",
                run_id="current-run",
                artifact_type=artifact_type,
                payload={"version": "v1"},
            )
        )
    return repository


def _request(
    *,
    run_mode: ReadinessRunMode = ReadinessRunMode.RELEASE,
    evaluation_run_ids: tuple[str, ...] = ("current-run",),
    reference_run_ids: tuple[str, ...] = ("reference-run",),
    replacement_request: ModelReplacementValidationRequest | None = None,
    replacement_result: ModelReplacementValidationResult | None = None,
) -> EnhancedReadinessRequest:
    return EnhancedReadinessRequest(
        gate_run_id="enhanced-readiness-1",
        correlation_id="enhanced-correlation-1",
        target_type=EvaluationTargetType.RAG_ANSWER,
        run_mode=run_mode,
        persistence_run_id="current-run",
        evaluation_run_ids=evaluation_run_ids,
        reference_run_ids=reference_run_ids,
        authority_evidence=RiskAuthorityGateEvidence(
            provenance_record_ids=("rag-source-1",),
            decision_evidence_packets=(_packet(),),
        ),
        model_replacement_request=replacement_request,
        model_replacement=replacement_result,
    )


def _service(repository: _FakeRepository) -> EnhancedReadinessService:
    return EnhancedReadinessService(
        repository=repository,
        readiness_gate=ReadinessGateService(repository=repository),
        decision_evidence_packet_persistence_service=cast(
            DecisionEvidencePacketPersistenceService,
            _FakePacketPersistence(),
        ),
    )


def _section_status(verdict, section: ReadinessSection) -> ReadinessSectionStatus:
    return next(item.status for item in verdict.sections if item.section is section)


def _replacement() -> tuple[
    ModelReplacementValidationRequest,
    ModelReplacementValidationResult,
]:
    claim = ModelReplacementValidationRequest(
        gate_id="replacement-gate-1",
        candidate_profile_name="default-analysis",
        candidate_model="candidate-model-v2",
        evaluator_provider="fake-provider",
        evaluator_model="fake-judge-v1",
        mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
        dataset_slice_name=MODEL_REPLACEMENT_DATASET_SLICE_NAME,
    )
    sections = tuple(
        ModelReplacementGateSectionResult(
            section=section,
            status=ModelReplacementGateStatus.PASSED,
            message=f"{section.value} passed",
            details={},
            run_ids=("replacement-run",)
            if section is ModelReplacementGateSection.RAG
            else (),
            case_ids=("replacement-case",)
            if section is ModelReplacementGateSection.RAG
            else (),
            metric_result_count=1
            if section is ModelReplacementGateSection.RAG
            else 0,
        )
        for section in ModelReplacementGateSection
    )
    result = ModelReplacementValidationResult(
        gate_id=claim.gate_id or "",
        candidate_profile_name=claim.candidate_profile_name,
        candidate_model=claim.candidate_model,
        mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
        sections=sections,
        passed_replacement_validation=True,
    )
    return claim, result


def test_enhanced_profile_v2_owns_structured_output_requirement() -> None:
    profile = _profile()

    assert profile.profile_version == "enhanced_v2"
    assert "structured_output_conformance" in profile.required_artifacts
    assert profile.metric_requirements
    assert all(item.allowed_drift == 0.05 for item in profile.metric_requirements)


@pytest.mark.asyncio
async def test_complete_persisted_enhanced_evidence_passes() -> None:
    repository = _seed_repository()

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.PASSED
    assert verdict.profile.profile_version == "enhanced_v2"
    for section in (
        ReadinessSection.AUTHORITY,
        ReadinessSection.DATASETS,
        ReadinessSection.METRICS,
        ReadinessSection.ARTIFACTS,
        ReadinessSection.LIVE_SERVICES,
        ReadinessSection.PERSISTENCE,
    ):
        assert _section_status(verdict, section) is ReadinessSectionStatus.PASSED

    artifacts = {item.artifact_type: item for item in repository.artifacts}
    assert "canonical_evaluation_coverage" in artifacts
    assert "provenance_reconstruction" in artifacts
    assert "retention_reconstruction" in artifacts
    assert READINESS_GATE_ARTIFACT_TYPE in artifacts
    coverage = artifacts["canonical_evaluation_coverage"].payload
    assert coverage is not None
    assert coverage["current_run_ids"] == ["current-run"]
    assert coverage["reference_run_ids"] == ["reference-run"]
    assert coverage["metrics"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["missing_reference", "stale_threshold", "judge"])
async def test_missing_stale_or_incompatible_metric_evidence_fails_closed(
    failure: str,
) -> None:
    repository = _seed_repository()
    request = _request()
    if failure == "missing_reference":
        request = replace(request, reference_run_ids=("missing-reference",))
    elif failure == "stale_threshold":
        first, *rest = repository.metrics["reference-run"]
        repository.metrics["reference-run"] = (
            replace(first, threshold_version="stale-threshold-v0"),
            *rest,
        )
    else:
        repository.runs["reference-run"] = replace(
            repository.runs["reference-run"],
            evaluator_model="different-judge",
        )

    verdict = await _service(repository).evaluate(request)

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.METRICS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_persisted_metric_drift_above_profile_allowance_fails() -> None:
    repository = _seed_repository()
    requirement = next(
        item
        for item in _profile().metric_requirements
        if item.applies_to(EvaluationTargetType.RAG_ANSWER)
    )
    current = list(repository.metrics["current-run"])
    reference = list(repository.metrics["reference-run"])
    current[0] = replace(current[0], score=requirement.minimum_score)
    reference[0] = replace(
        reference[0],
        score=min(1.0, requirement.minimum_score + 0.10),
    )
    repository.metrics["current-run"] = tuple(current)
    repository.metrics["reference-run"] = tuple(reference)

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.METRICS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_unprojected_evaluation_evidence_fails_live_requirement() -> None:
    repository = _seed_repository()
    repository.runs["current-run"] = replace(
        repository.runs["current-run"],
        langfuse_projection_status=LangfuseProjectionStatus.PENDING,
    )

    verdict = await _service(repository).evaluate(_request())

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.LIVE_SERVICES) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_model_replacement_result_alone_cannot_grant_readiness() -> None:
    repository = _seed_repository()
    claim, result = _replacement()
    repository.runs["replacement-run"] = EvaluationRunRecord(
        run_id="replacement-run",
        target_type=EvaluationTargetType.RAG_ANSWER,
        status=EvaluationStatus.PASSED,
        evaluator_provider="fake-provider",
        evaluator_model="fake-judge-v1",
    )

    verdict = await _service(repository).evaluate(
        _request(
            run_mode=ReadinessRunMode.MODEL_PROFILE_REPLACEMENT,
            evaluation_run_ids=(),
            reference_run_ids=(),
            replacement_request=claim,
            replacement_result=result,
        )
    )

    assert verdict.status is ReadinessVerdictStatus.FAILED
    assert _section_status(verdict, ReadinessSection.DATASETS) is (
        ReadinessSectionStatus.FAILED
    )
    assert _section_status(verdict, ReadinessSection.METRICS) is (
        ReadinessSectionStatus.FAILED
    )


@pytest.mark.asyncio
async def test_full_replacement_evidence_contributes_without_overriding_gate() -> None:
    repository = _seed_repository()
    claim, result = _replacement()
    definition = _rag_answer_dataset_definition()
    repository.runs["replacement-run"] = EvaluationRunRecord(
        run_id="replacement-run",
        target_type=EvaluationTargetType.RAG_ANSWER,
        status=EvaluationStatus.PASSED,
        evaluator_provider="fake-provider",
        evaluator_model="fake-judge-v1",
        dataset_id=definition.reference.dataset_id,
    )

    verdict = await _service(repository).evaluate(
        _request(
            run_mode=ReadinessRunMode.MODEL_PROFILE_REPLACEMENT,
            replacement_request=claim,
            replacement_result=result,
        )
    )

    assert verdict.status is ReadinessVerdictStatus.PASSED
    assert any(
        item.name == MODEL_REPLACEMENT_DATASET_SLICE_NAME
        and item.version == EVALUATION_DATASET_VERSION
        for item in verdict.evidence.datasets
    )
    replacement_artifact = next(
        item
        for item in repository.artifacts
        if item.artifact_type == "model_replacement_validation_evidence"
    )
    assert replacement_artifact.payload is not None
    assert replacement_artifact.payload["candidate_profile_name"] == "default-analysis"
    assert replacement_artifact.payload["candidate_model"] == "candidate-model-v2"
    assert replacement_artifact.payload["dataset_slice_name"] == (
        MODEL_REPLACEMENT_DATASET_SLICE_NAME
    )
