from __future__ import annotations

from application.decision_evidence._reconstruction_contracts import (
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSourceError,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
)
from application.decision_evidence.completed_workflow_assembly import (
    calculate_completed_workflow_node_evidence_digest,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunArchive,
    CompletedRunBundle,
)
from domain.decision_evidence import ReconstructionReference


async def validate_completed_workflow_run(
    *,
    archive: CompletedRunArchive,
    reference: ReconstructionReference,
    bundle_cache: dict[tuple[str, str], CompletedRunBundle],
) -> None:
    workflow_name, execution_id = _parse_completed_workflow_run_record_id(reference)
    bundle = await _load_completed_run_bundle(
        archive=archive,
        workflow_name=workflow_name,
        execution_id=execution_id,
        bundle_cache=bundle_cache,
    )
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "completed workflow run reconstruction reference must include "
            "a snapshot_id."
        )
    if bundle.run.run_id != reference.snapshot_id:
        raise StaleDecisionEvidenceSourceError(
            "completed workflow run evidence is stale for "
            f"'{workflow_name}:{execution_id}'."
        )


async def validate_workflow_node_output(
    *,
    archive: CompletedRunArchive,
    reference: ReconstructionReference,
    bundle_cache: dict[tuple[str, str], CompletedRunBundle],
) -> None:
    workflow_name, execution_id, node_name = _parse_workflow_node_snapshot_id(
        reference,
    )
    bundle = await _load_completed_run_bundle(
        archive=archive,
        workflow_name=workflow_name,
        execution_id=execution_id,
        bundle_cache=bundle_cache,
    )
    node_output = _resolve_node_output(reference, bundle)
    if (
        node_output.run_id != bundle.run.run_id
        or node_output.workflow_name != workflow_name
        or node_output.execution_id != execution_id
        or node_output.node_name != node_name
    ):
        raise SubstitutedDecisionEvidenceSourceError(
            "workflow node output evidence does not belong to completed run "
            f"'{bundle.run.run_id}'."
        )
    if reference.content_digest is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "workflow node output reconstruction reference must include "
            "a content digest."
        )
    content_digest = calculate_completed_workflow_node_evidence_digest(
        run=bundle.run,
        node_output=node_output,
    )
    if content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "workflow node output evidence content digest is stale for "
            f"'{reference.record_id}'."
        )


async def _load_completed_run_bundle(
    *,
    archive: CompletedRunArchive,
    workflow_name: str,
    execution_id: str,
    bundle_cache: dict[tuple[str, str], CompletedRunBundle],
) -> CompletedRunBundle:
    cache_key = (workflow_name, execution_id)
    cached = bundle_cache.get(cache_key)
    if cached is not None:
        return cached

    bundle = await archive.load_archived_run(workflow_name, execution_id)
    if bundle is None:
        raise MissingDecisionEvidenceSourceError(
            "completed workflow run source record "
            f"'{workflow_name}:{execution_id}' was not found."
        )
    if (
        bundle.run.workflow_name != workflow_name
        or bundle.run.execution_id != execution_id
    ):
        raise SubstitutedDecisionEvidenceSourceError(
            "completed workflow run evidence does not match reconstruction "
            f"identifier '{workflow_name}:{execution_id}'."
        )
    bundle_cache[cache_key] = bundle
    return bundle


def _parse_completed_workflow_run_record_id(
    reference: ReconstructionReference,
) -> tuple[str, str]:
    parts = reference.record_id.split(":")
    if len(parts) != 2 or not all(parts):
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "completed workflow run reconstruction identifier must be "
            "'<workflow_name>:<execution_id>'."
        )
    return parts[0], parts[1]


def _parse_workflow_node_snapshot_id(
    reference: ReconstructionReference,
) -> tuple[str, str, str]:
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "workflow node output reconstruction reference must include a snapshot_id."
        )
    parts = reference.snapshot_id.split(":")
    if len(parts) != 3 or not all(parts):
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            "workflow node output reconstruction identifier must be "
            "'<workflow_name>:<execution_id>:<node_name>'."
        )
    return parts[0], parts[1], parts[2]


def _resolve_node_output(
    reference: ReconstructionReference,
    bundle: CompletedRunBundle,
) -> CompletedNodeOutputRecord:
    for node_output in bundle.node_outputs:
        if node_output.node_output_id == reference.record_id:
            return node_output
    raise MissingDecisionEvidenceSourceError(
        f"workflow node output source record '{reference.record_id}' was not found."
    )
