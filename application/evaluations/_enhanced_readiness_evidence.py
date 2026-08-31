from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from application.evaluations.evaluation_run_service import (
    expected_authority_metadata_for_evaluation_target,
)
from application.evaluations.model_replacement_gate import (
    ModelReplacementValidationRequest,
    ModelReplacementValidationResult,
)
from application.evaluations.readiness_gate import (
    ReadinessArtifactEvidence,
    ReadinessDatasetEvidence,
    ReadinessLiveServiceEvidence,
    ReadinessMetricEvidence,
)
from application.evaluations.readiness_profiles import (
    ReadinessDatasetScope,
    ReadinessMetricRequirement,
    ReadinessProfile,
    ReadinessRunMode,
    readiness_profile_for_gate,
)
from application.evaluations.risk_authority_gate import RiskAuthorityGateEvidence
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationDatasetRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
    JsonObject,
    LangfuseProjectionStatus,
)
from domain.authority import (
    GateProfile,
    risk_authority_contract_from_metadata,
)
from domain.evaluation import EvaluationStatus, EvaluationTargetType

COVERAGE_ARTIFACT = "canonical_evaluation_coverage"
PROVENANCE_ARTIFACT = "provenance_reconstruction"
RETENTION_ARTIFACT = "retention_reconstruction"
REPLACEMENT_ARTIFACT = "model_replacement_validation_evidence"
DERIVED_ARTIFACTS = {
    COVERAGE_ARTIFACT,
    PROVENANCE_ARTIFACT,
    RETENTION_ARTIFACT,
}
EVIDENCE_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class RunEvidence:
    run: EvaluationRunRecord
    dataset: EvaluationDatasetRecord
    metrics: tuple[EvaluationMetricResultRecord, ...]


@dataclass(frozen=True, slots=True)
class MetricEvidence:
    readiness: tuple[ReadinessMetricEvidence, ...]
    payload: tuple[JsonObject, ...]


def enhanced_profile(target_type: EvaluationTargetType) -> ReadinessProfile:
    authority = risk_authority_contract_from_metadata(
        expected_authority_metadata_for_evaluation_target(target_type)
    )
    if authority.gate_profile is not GateProfile.ENHANCED_PROVENANCE:
        raise ValueError("EnhancedReadinessService requires an Enhanced target type.")
    return readiness_profile_for_gate(authority.gate_profile)


def dataset_evidence(
    profile: ReadinessProfile,
    *,
    target_type: EvaluationTargetType,
    run_mode: ReadinessRunMode,
    current: tuple[RunEvidence, ...],
) -> tuple[ReadinessDatasetEvidence, ...]:
    result: list[ReadinessDatasetEvidence] = []
    for requirement in profile.dataset_requirements:
        if (
            requirement.scope is not ReadinessDatasetScope.DATASET
            or not requirement.applies_to(
                target_type=target_type,
                run_mode=run_mode,
            )
        ):
            continue
        match = next(
            (
                item.dataset
                for item in current
                if item.dataset.name == requirement.name
                and item.dataset.version == requirement.version
            ),
            None,
        )
        if match is not None:
            result.append(
                ReadinessDatasetEvidence(
                    requirement.name,
                    requirement.version,
                    requirement.scope,
                    match.dataset_id,
                )
            )
    return tuple(result)


def metric_evidence(
    profile: ReadinessProfile,
    current: tuple[RunEvidence, ...],
    reference: tuple[RunEvidence, ...],
) -> MetricEvidence:
    if not _runs_are_comparable(current, reference):
        return MetricEvidence((), ())
    readiness: list[ReadinessMetricEvidence] = []
    payload: list[JsonObject] = []
    target_type = cast(EvaluationTargetType, current[0].run.target_type)
    for requirement in profile.metric_requirements:
        if not requirement.applies_to(target_type):
            continue
        current_records = _metric_records(current, requirement)
        reference_records = _metric_records(reference, requirement)
        if not current_records or not reference_records:
            continue
        current_score = min(record.score for record in current_records)
        reference_score = min(record.score for record in reference_records)
        drift = max(0.0, reference_score - current_score)
        readiness.append(
            ReadinessMetricEvidence(
                requirement.metric_name,
                requirement.version,
                current_score,
                drift,
                min(record.metric_result_id for record in current_records),
            )
        )
        payload.append(
            cast(
                JsonObject,
                {
                    "metric_name": requirement.metric_name,
                    "threshold_version": requirement.version,
                    "minimum_score": requirement.minimum_score,
                    "allowed_drift": requirement.allowed_drift,
                    "current_score": current_score,
                    "reference_score": reference_score,
                    "drift": drift,
                    "current_metric_result_ids": sorted(
                        record.metric_result_id for record in current_records
                    ),
                    "reference_metric_result_ids": sorted(
                        record.metric_result_id for record in reference_records
                    ),
                    "evaluator_provider": current[0].run.evaluator_provider,
                    "evaluator_model": current[0].run.evaluator_model,
                },
            )
        )
    return MetricEvidence(tuple(readiness), tuple(payload))


def _runs_are_comparable(
    current: tuple[RunEvidence, ...],
    reference: tuple[RunEvidence, ...],
) -> bool:
    if not current or not reference:
        return False
    datasets = [
        {(item.dataset.dataset_id, item.dataset.version) for item in group}
        for group in (current, reference)
    ]
    judges = {
        (item.run.evaluator_provider, item.run.evaluator_model)
        for item in (*current, *reference)
    }
    return len(datasets[0]) == 1 and datasets[0] == datasets[1] and len(judges) == 1


def _metric_records(
    runs: tuple[RunEvidence, ...],
    requirement: ReadinessMetricRequirement,
) -> tuple[EvaluationMetricResultRecord, ...]:
    return tuple(
        record
        for item in runs
        for record in item.metrics
        if record.metric_name == requirement.metric_name
        and record.status is EvaluationStatus.PASSED
        and record.passed is True
        and record.threshold_version == requirement.version
        and record.threshold == requirement.minimum_score
        and record.evaluator_provider == item.run.evaluator_provider
        and record.evaluator_model == item.run.evaluator_model
        and record.langfuse_projection_status is LangfuseProjectionStatus.PROJECTED
    )


def observability_evidence(
    current: tuple[RunEvidence, ...],
    reference: tuple[RunEvidence, ...],
) -> tuple[ReadinessLiveServiceEvidence, ...]:
    runs = (*current, *reference)
    if not runs or any(
        item.run.langfuse_projection_status is not LangfuseProjectionStatus.PROJECTED
        for item in runs
    ):
        return ()
    return (
        ReadinessLiveServiceEvidence(
            "observability_projection",
            "langfuse:" + ",".join(sorted(item.run.run_id for item in runs)),
        ),
    )


def coverage_payload(
    profile: ReadinessProfile,
    current: tuple[RunEvidence, ...],
    reference: tuple[RunEvidence, ...],
    metrics: MetricEvidence,
) -> JsonObject | None:
    if not current or not reference:
        return None
    target_type = cast(EvaluationTargetType, current[0].run.target_type)
    required = sum(
        requirement.applies_to(target_type)
        for requirement in profile.metric_requirements
    )
    if (
        len(metrics.readiness) != required
        or not observability_evidence(current, reference)
    ):
        return None
    return cast(
        JsonObject,
        {
            "schema_version": 1,
            "profile_version": profile.profile_version,
            "current_run_ids": [item.run.run_id for item in current],
            "reference_run_ids": [item.run.run_id for item in reference],
            "datasets": [
                {
                    "dataset_id": item.dataset.dataset_id,
                    "name": item.dataset.name,
                    "version": item.dataset.version,
                    "case_ids": list(item.run.case_ids),
                }
                for item in current
            ],
            "metrics": list(metrics.payload),
        },
    )


def packet_payload(evidence: RiskAuthorityGateEvidence) -> JsonObject | None:
    if not evidence.decision_evidence_packets:
        return None
    return cast(
        JsonObject,
        {
            "schema_version": 1,
            "packets": [
                {
                    "packet_id": packet.packet_id,
                    "packet_version": packet.schema_version,
                    "output_id": packet.output_id,
                    "workflow_name": packet.workflow_name,
                    "workflow_definition_fingerprint": (
                        packet.workflow_definition_fingerprint
                    ),
                    "execution_id": packet.execution_id,
                    "retention_policy_id": packet.retention.policy_id,
                    "retain_until": packet.retention.retain_until,
                }
                for packet in evidence.decision_evidence_packets
            ],
        },
    )


def replacement_payload(
    claim: ModelReplacementValidationRequest,
    result: ModelReplacementValidationResult,
) -> JsonObject:
    return cast(
        JsonObject,
        {
            "schema_version": 1,
            "gate_id": result.gate_id,
            "candidate_profile_name": result.candidate_profile_name,
            "candidate_model": result.candidate_model,
            "dataset_slice_name": claim.dataset_slice_name,
            "mode": result.mode.value,
            "passed_replacement_validation": result.passed_replacement_validation,
            "validation_failure_reason": result.validation_failure_reason,
            "evaluation_run_ids": list(result.evaluation_run_ids),
            "metric_result_count": result.metric_result_count,
            "sections": [
                {
                    "section": section.section.value,
                    "status": section.status.value,
                    "message": section.message,
                    "details": section.details,
                    "run_ids": list(section.run_ids),
                    "case_ids": list(section.case_ids),
                    "metric_result_count": section.metric_result_count,
                }
                for section in result.sections
            ],
        },
    )


def unique_artifacts(
    artifacts: Sequence[ReadinessArtifactEvidence],
) -> tuple[ReadinessArtifactEvidence, ...]:
    by_id: dict[tuple[str, str], ReadinessArtifactEvidence] = {}
    for artifact in artifacts:
        by_id.setdefault((artifact.artifact_type, artifact.artifact_id), artifact)
    return tuple(by_id.values())


def artifact_version(record: EvaluationArtifactRecord) -> str | None:
    if record.payload is None:
        return None
    for key in ("version", "profile_version"):
        value = record.payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
