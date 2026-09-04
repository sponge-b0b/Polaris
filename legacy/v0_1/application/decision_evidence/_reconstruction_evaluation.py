from __future__ import annotations

from dataclasses import dataclass

from application.decision_evidence._reconstruction_contracts import (
    EvaluationProvenanceRepository,
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
)
from application.decision_evidence._reconstruction_digest import (
    datetime_value,
    enum_value,
    stable_content_digest,
)
from core.storage.persistence.evaluation import (
    EvaluationArtifactRecord,
    EvaluationMetricResultRecord,
    EvaluationRunRecord,
)
from domain.decision_evidence import ReconstructionReference


async def validate_evaluation_run(
    *,
    repository: EvaluationProvenanceRepository | None,
    reference: ReconstructionReference,
) -> None:
    if repository is None:
        raise MissingDecisionEvidenceSourceError(
            "evaluation provenance repository is required to reconstruct "
            f"evaluation run source record '{reference.record_id}'."
        )

    run = await repository.get_run(reference.record_id)
    if run is None:
        raise MissingDecisionEvidenceSourceError(
            f"evaluation run source record '{reference.record_id}' was not found."
        )
    if run.run_id != reference.record_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "evaluation run evidence does not match reconstruction identifier "
            f"'{reference.record_id}'."
        )
    if reference.content_digest is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "evaluation run reconstruction reference must include a content digest."
        )

    content_digest = calculate_evaluation_run_evidence_digest(run=run)
    if content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "evaluation run evidence content digest is stale for "
            f"'{reference.record_id}'."
        )


async def validate_evaluation_metric_result(
    *,
    repository: EvaluationProvenanceRepository | None,
    reference: ReconstructionReference,
) -> None:
    if repository is None:
        raise MissingDecisionEvidenceSourceError(
            "evaluation provenance repository is required to reconstruct "
            f"evaluation metric result source record '{reference.record_id}'."
        )
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "evaluation metric result reconstruction reference must include "
            "an evaluation run snapshot_id."
        )

    metric_result = await _load_metric_result(
        repository=repository,
        run_id=reference.snapshot_id,
        metric_result_id=reference.record_id,
    )
    if metric_result.run_id != reference.snapshot_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "evaluation metric result evidence does not belong to evaluation "
            f"run '{reference.snapshot_id}'."
        )
    if reference.content_digest is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "evaluation metric result reconstruction reference must include "
            "a content digest."
        )

    content_digest = calculate_evaluation_metric_result_evidence_digest(
        metric_result=metric_result,
    )
    if content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "evaluation metric result evidence content digest is stale for "
            f"'{reference.record_id}'."
        )


async def validate_linked_artifact(
    *,
    repository: EvaluationProvenanceRepository | None,
    reference: ReconstructionReference,
) -> None:
    _validate_linked_artifact_reference(reference)
    evaluation_artifact = _parse_evaluation_artifact_record_id(reference.record_id)
    if evaluation_artifact is None:
        return

    if repository is None:
        raise MissingDecisionEvidenceSourceError(
            "evaluation provenance repository is required to reconstruct "
            f"linked artifact source record '{reference.record_id}'."
        )
    artifact = await _load_evaluation_artifact(
        repository=repository,
        run_id=evaluation_artifact.run_id,
        artifact_id=evaluation_artifact.artifact_id,
    )
    if artifact.run_id != evaluation_artifact.run_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "linked evaluation artifact evidence does not belong to evaluation "
            f"run '{evaluation_artifact.run_id}'."
        )
    if reference.content_digest is not None:
        content_digest = calculate_evaluation_artifact_evidence_digest(
            artifact=artifact,
        )
        if content_digest != reference.content_digest:
            raise StaleDecisionEvidenceSourceError(
                "linked evaluation artifact evidence content digest is stale "
                f"for '{reference.record_id}'."
            )


def calculate_evaluation_run_evidence_digest(
    *,
    run: EvaluationRunRecord,
) -> str:
    """Calculate a stable digest from safe evaluation run provenance fields."""

    return stable_content_digest(
        {
            "run_id": run.run_id,
            "target_type": enum_value(run.target_type),
            "status": enum_value(run.status),
            "evaluator_provider": run.evaluator_provider,
            "evaluator_model": run.evaluator_model,
            "dataset_id": run.dataset_id,
            "case_ids": tuple(run.case_ids),
            "started_at": datetime_value(run.started_at),
            "completed_at": datetime_value(run.completed_at),
            "error_message": run.error_message,
        }
    )


def calculate_evaluation_metric_result_evidence_digest(
    *,
    metric_result: EvaluationMetricResultRecord,
) -> str:
    """Calculate a stable digest from safe evaluation metric result fields."""

    return stable_content_digest(
        {
            "metric_result_id": metric_result.metric_result_id,
            "run_id": metric_result.run_id,
            "case_id": metric_result.case_id,
            "metric_name": metric_result.metric_name,
            "score": metric_result.score,
            "status": enum_value(metric_result.status),
            "evaluator_provider": metric_result.evaluator_provider,
            "evaluator_model": metric_result.evaluator_model,
            "threshold": metric_result.threshold,
            "threshold_version": metric_result.threshold_version,
            "passed": metric_result.passed,
            "duration_ms": metric_result.duration_ms,
            "error_message": metric_result.error_message,
        }
    )


def calculate_evaluation_artifact_evidence_digest(
    *,
    artifact: EvaluationArtifactRecord,
) -> str:
    """Calculate a stable digest from safe evaluation artifact identity fields."""

    return stable_content_digest(
        {
            "artifact_id": artifact.artifact_id,
            "run_id": artifact.run_id,
            "artifact_type": artifact.artifact_type,
            "case_id": artifact.case_id,
            "uri": artifact.uri,
            "payload": artifact.payload,
            "created_at": datetime_value(artifact.created_at),
        }
    )


async def _load_metric_result(
    *,
    repository: EvaluationProvenanceRepository,
    run_id: str,
    metric_result_id: str,
) -> EvaluationMetricResultRecord:
    metric_results = await repository.list_metric_results(run_id)
    for metric_result in metric_results:
        if metric_result.metric_result_id == metric_result_id:
            return metric_result
    raise MissingDecisionEvidenceSourceError(
        f"evaluation metric result source record '{metric_result_id}' was not found."
    )


async def _load_evaluation_artifact(
    *,
    repository: EvaluationProvenanceRepository,
    run_id: str,
    artifact_id: str,
) -> EvaluationArtifactRecord:
    artifacts = await repository.list_artifacts(run_id)
    for artifact in artifacts:
        if artifact.artifact_id == artifact_id:
            return artifact
    raise MissingDecisionEvidenceSourceError(
        f"evaluation artifact source record '{artifact_id}' was not found."
    )


@dataclass(frozen=True, slots=True)
class _EvaluationArtifactIdentity:
    run_id: str
    artifact_id: str


def _parse_evaluation_artifact_record_id(
    record_id: str,
) -> _EvaluationArtifactIdentity | None:
    parts = record_id.split(":")
    if len(parts) != 3 or parts[0] != "evaluation-artifact":
        return None
    if not parts[1] or not parts[2]:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "evaluation linked artifact reconstruction identifier must be "
            "'evaluation-artifact:<run_id>:<artifact_id>'."
        )
    return _EvaluationArtifactIdentity(run_id=parts[1], artifact_id=parts[2])


def _validate_linked_artifact_reference(reference: ReconstructionReference) -> None:
    if reference.source_of_truth is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "linked artifact reconstruction reference must identify its source of "
            "truth."
        )
