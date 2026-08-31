from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.evaluations._enhanced_readiness_evidence import (
    COVERAGE_ARTIFACT,
    DERIVED_ARTIFACTS,
    EVIDENCE_VERSION,
    PROVENANCE_ARTIFACT,
    REPLACEMENT_ARTIFACT,
    RETENTION_ARTIFACT,
    MetricEvidence,
    RunEvidence,
    artifact_version,
    coverage_payload,
    dataset_evidence,
    enhanced_profile,
    metric_evidence,
    observability_evidence,
    packet_payload,
    replacement_payload,
    unique_artifacts,
)
from application.evaluations.evaluation_datasets import EVALUATION_DATASET_VERSION
from application.evaluations.evaluation_gate_evidence import (
    reacquire_authority_gate_decision_evidence,
)
from application.evaluations.model_replacement_gate import (
    MODEL_REPLACEMENT_DATASET_SLICE_NAME,
    ModelReplacementGateSection,
    ModelReplacementGateStatus,
    ModelReplacementValidationMode,
    ModelReplacementValidationRequest,
    ModelReplacementValidationResult,
)
from application.evaluations.readiness_gate import (
    ReadinessArtifactEvidence,
    ReadinessDatasetEvidence,
    ReadinessGateEvidence,
    ReadinessGateRequest,
    ReadinessGateService,
    ReadinessGateVerdict,
)
from application.evaluations.readiness_profiles import (
    ReadinessDatasetScope,
    ReadinessProfile,
    ReadinessRunMode,
)
from application.evaluations.risk_authority_gate import RiskAuthorityGateEvidence
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
    JsonObject,
)
from domain.authority import RiskAuthorityContract
from domain.evaluation import EvaluationStatus, EvaluationTargetType


class EnhancedReadinessPersistencePort(Protocol):
    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None: ...

    async def get_run(self, run_id: str) -> EvaluationRunRecord | None: ...

    async def list_metric_results(
        self,
        run_id: str,
    ) -> Sequence[EvaluationMetricResultRecord]: ...

    async def list_artifacts(
        self,
        run_id: str,
    ) -> Sequence[EvaluationArtifactRecord]: ...

    async def create_artifact(
        self,
        record: EvaluationArtifactRecord,
    ) -> EvaluationArtifactRecord: ...


@dataclass(frozen=True, slots=True)
class EnhancedReadinessRequest:
    """Persisted evidence identities for one Enhanced readiness claim."""

    gate_run_id: str
    correlation_id: str
    target_type: EvaluationTargetType
    run_mode: ReadinessRunMode
    persistence_run_id: str
    evaluation_run_ids: tuple[str, ...]
    reference_run_ids: tuple[str, ...]
    authority_evidence: RiskAuthorityGateEvidence
    artifact_run_ids: tuple[str, ...] = ()
    model_replacement_request: ModelReplacementValidationRequest | None = None
    model_replacement: ModelReplacementValidationResult | None = None
    supplied_authority_metadata: Mapping[str, object] | RiskAuthorityContract | None = (
        None
    )

    def __post_init__(self) -> None:
        for name in ("gate_run_id", "correlation_id", "persistence_run_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        for name in (
            "evaluation_run_ids",
            "reference_run_ids",
            "artifact_run_ids",
        ):
            values = tuple(_required(value, name) for value in getattr(self, name))
            if len(values) != len(set(values)):
                raise ValueError(f"{name} cannot contain duplicate identities.")
            object.__setattr__(self, name, values)


@dataclass(frozen=True, slots=True)
class EnhancedReadinessService:
    """Acquire canonical Enhanced evidence and delegate the verdict to #267."""

    repository: EnhancedReadinessPersistencePort
    readiness_gate: ReadinessGateService
    decision_evidence_packet_persistence_service: (
        DecisionEvidencePacketPersistenceService | None
    ) = None

    async def evaluate(self, request: EnhancedReadinessRequest) -> ReadinessGateVerdict:
        profile = enhanced_profile(request.target_type)
        current = await self._load_runs(request.evaluation_run_ids, request.target_type)
        reference = await self._load_runs(
            request.reference_run_ids, request.target_type
        )
        metrics = metric_evidence(profile, current, reference)
        authority = await self._reacquire_authority(request, metrics)

        datasets = list(
            dataset_evidence(
                profile,
                target_type=request.target_type,
                run_mode=request.run_mode,
                current=current,
            )
        )
        artifacts = await self._source_artifacts(request, profile)
        artifacts.extend(
            await self._derived_artifacts(
                request, profile, current, reference, metrics, authority
            )
        )

        replacement = await self._replacement_evidence(request)
        if replacement is not None and request.model_replacement is not None:
            datasets.append(replacement[0])
            artifacts.append(replacement[1])
            authority = replace(
                authority,
                model_replacement_gate_ids=tuple(
                    dict.fromkeys(
                        (
                            *authority.model_replacement_gate_ids,
                            request.model_replacement.gate_id,
                        )
                    )
                ),
            )

        evidence = ReadinessGateEvidence(
            authority=authority,
            datasets=tuple(datasets),
            metrics=metrics.readiness,
            artifacts=unique_artifacts(artifacts),
            live_services=observability_evidence(current, reference),
        )
        return await self.readiness_gate.evaluate(
            ReadinessGateRequest(
                gate_run_id=request.gate_run_id,
                correlation_id=request.correlation_id,
                target_type=request.target_type,
                run_mode=request.run_mode,
                evidence=evidence,
                supplied_authority_metadata=request.supplied_authority_metadata,
                persistence_run_id=request.persistence_run_id,
            )
        )

    async def _load_runs(
        self,
        run_ids: tuple[str, ...],
        target_type: EvaluationTargetType,
    ) -> tuple[RunEvidence, ...]:
        if not run_ids:
            return ()
        loaded: list[RunEvidence] = []
        try:
            for run_id in run_ids:
                run = await self.repository.get_run(run_id)
                if (
                    run is None
                    or run.target_type is not target_type
                    or run.status is not EvaluationStatus.PASSED
                    or run.dataset_id is None
                ):
                    return ()
                dataset = await self.repository.get_dataset(run.dataset_id)
                if (
                    dataset is None
                    or dataset.target_type is not target_type
                    or not dataset.active
                ):
                    return ()
                loaded.append(
                    RunEvidence(
                        run,
                        dataset,
                        tuple(await self.repository.list_metric_results(run_id)),
                    )
                )
        except Exception:
            return ()
        return tuple(loaded)

    async def _reacquire_authority(
        self,
        request: EnhancedReadinessRequest,
        metrics: MetricEvidence,
    ) -> RiskAuthorityGateEvidence:
        evidence = replace(
            request.authority_evidence,
            evaluation_run_ids=tuple(
                dict.fromkeys(
                    (
                        *request.authority_evidence.evaluation_run_ids,
                        *request.evaluation_run_ids,
                    )
                )
            ),
            metric_result_count=metrics.current_result_count,
        )
        reconstructed = await reacquire_authority_gate_decision_evidence(
            evidence=evidence,
            persistence_service=self.decision_evidence_packet_persistence_service,
        )
        return evidence if reconstructed is None else reconstructed

    async def _source_artifacts(
        self,
        request: EnhancedReadinessRequest,
        profile: ReadinessProfile,
    ) -> list[ReadinessArtifactEvidence]:
        required = set(profile.required_artifacts) - DERIVED_ARTIFACTS
        run_ids = dict.fromkeys(
            (
                *request.evaluation_run_ids,
                *request.artifact_run_ids,
                request.persistence_run_id,
            )
        )
        found: list[ReadinessArtifactEvidence] = []
        try:
            for run_id in run_ids:
                for record in await self.repository.list_artifacts(run_id):
                    if record.artifact_type not in required:
                        continue
                    version = artifact_version(record)
                    if version is None:
                        continue
                    found.append(
                        ReadinessArtifactEvidence(
                            record.artifact_type,
                            record.artifact_id,
                            version,
                        )
                    )
        except Exception:
            return []
        return found

    async def _derived_artifacts(
        self,
        request: EnhancedReadinessRequest,
        profile: ReadinessProfile,
        current: tuple[RunEvidence, ...],
        reference: tuple[RunEvidence, ...],
        metrics: MetricEvidence,
        authority: RiskAuthorityGateEvidence,
    ) -> list[ReadinessArtifactEvidence]:
        found: list[ReadinessArtifactEvidence] = []
        coverage = coverage_payload(profile, current, reference, metrics)
        if coverage is not None:
            artifact = await self._persist_artifact(
                request, COVERAGE_ARTIFACT, coverage
            )
            if artifact is not None:
                found.append(artifact)

        packets = packet_payload(authority)
        if packets is not None:
            for artifact_type in (PROVENANCE_ARTIFACT, RETENTION_ARTIFACT):
                artifact = await self._persist_artifact(
                    request, artifact_type, packets
                )
                if artifact is not None:
                    found.append(artifact)
        return found

    async def _replacement_evidence(
        self,
        request: EnhancedReadinessRequest,
    ) -> tuple[ReadinessDatasetEvidence, ReadinessArtifactEvidence] | None:
        if request.run_mode is not ReadinessRunMode.MODEL_PROFILE_REPLACEMENT:
            return None
        result = request.model_replacement
        claim = request.model_replacement_request
        if (
            result is None
            or claim is None
            or not await self._replacement_is_valid(claim, result)
        ):
            return None
        artifact = await self._persist_artifact(
            request,
            REPLACEMENT_ARTIFACT,
            replacement_payload(claim, result),
            identity=result.gate_id,
        )
        if artifact is None:
            return None
        return (
            ReadinessDatasetEvidence(
                MODEL_REPLACEMENT_DATASET_SLICE_NAME,
                EVALUATION_DATASET_VERSION,
                ReadinessDatasetScope.SLICE,
                artifact.artifact_id,
            ),
            artifact,
        )

    async def _replacement_is_valid(
        self,
        claim: ModelReplacementValidationRequest,
        result: ModelReplacementValidationResult,
    ) -> bool:
        sections = {section.section: section.status for section in result.sections}
        if (
            claim.mode is not ModelReplacementValidationMode.REPLACEMENT_VALIDATION
            or claim.dataset_slice_name != MODEL_REPLACEMENT_DATASET_SLICE_NAME
            or claim.gate_id != result.gate_id
            or claim.candidate_profile_name != result.candidate_profile_name
            or claim.candidate_model != result.candidate_model
            or result.mode is not claim.mode
            or not result.passed_replacement_validation
            or set(sections) != set(ModelReplacementGateSection)
            or any(
                status is not ModelReplacementGateStatus.PASSED
                for status in sections.values()
            )
            or not result.evaluation_run_ids
            or result.metric_result_count <= 0
        ):
            return False
        try:
            for run_id in result.evaluation_run_ids:
                run = await self.repository.get_run(run_id)
                if run is None or run.status is not EvaluationStatus.PASSED:
                    return False
        except Exception:
            return False
        return True

    async def _persist_artifact(
        self,
        request: EnhancedReadinessRequest,
        artifact_type: str,
        payload: JsonObject,
        *,
        identity: str | None = None,
    ) -> ReadinessArtifactEvidence | None:
        artifact = EvaluationArtifactRecord(
            artifact_id=(
                f"enhanced_readiness:{request.persistence_run_id}:"
                f"{artifact_type}:{identity or request.gate_run_id}"
            ),
            run_id=request.persistence_run_id,
            artifact_type=artifact_type,
            payload=payload,
        )
        try:
            existing = next(
                (
                    item
                    for item in await self.repository.list_artifacts(
                        request.persistence_run_id
                    )
                    if item.artifact_id == artifact.artifact_id
                ),
                None,
            )
            if existing is None:
                await self.repository.create_artifact(artifact)
            elif existing.artifact_type != artifact_type or existing.payload != payload:
                return None
        except Exception:
            return None
        return ReadinessArtifactEvidence(
            artifact_type, artifact.artifact_id, EVIDENCE_VERSION
        )


def _required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned
