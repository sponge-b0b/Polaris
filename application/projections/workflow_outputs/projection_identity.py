from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Final
from uuid import NAMESPACE_URL, uuid5

from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunRecord,
)
from core.storage.persistence.lineage import (
    PersistenceLineage,
    PersistenceRecordIdentity,
    require_non_empty_identifier,
)

if TYPE_CHECKING:
    from application.projections.workflow_outputs.projection_models import (
        WorkflowOutputProjectorRequest,
    )

WORKFLOW_OUTPUT_PROJECTED_RECORD_NAMESPACE: Final = (
    "polaris.workflow_output_projected_record"
)


def build_workflow_output_projection_lineage(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
) -> PersistenceLineage:
    """Build canonical workflow/runtime lineage for one projected node output."""
    _validate_node_output_belongs_to_run(run=run, node_output=node_output)
    return PersistenceLineage(
        workflow_name=run.workflow_name,
        execution_id=run.execution_id,
        runtime_id=run.runtime_id,
        node_name=node_output.node_name,
    )


def build_projected_record_identity(
    *,
    record_type: str,
    execution_id: str,
    node_name: str,
    domain_natural_key: str,
    source_timestamp: datetime | str,
) -> PersistenceRecordIdentity:
    """Build a deterministic identity for a workflow-output-derived record."""
    clean_record_type = require_non_empty_identifier(record_type, "record_type")
    return PersistenceRecordIdentity(
        record_type=clean_record_type,
        record_id=build_projected_record_id(
            record_type=clean_record_type,
            execution_id=execution_id,
            node_name=node_name,
            domain_natural_key=domain_natural_key,
            source_timestamp=source_timestamp,
        ),
    )


def build_projected_record_identity_from_projector_request(
    *,
    request: WorkflowOutputProjectorRequest,
    record_type: str,
    domain_natural_key: str,
    source_timestamp: datetime | str,
) -> PersistenceRecordIdentity:
    """Build deterministic projected-record identity from a projector request."""
    return build_projected_record_identity(
        record_type=record_type,
        execution_id=require_non_empty_identifier(
            request.lineage.execution_id,
            "lineage.execution_id",
        ),
        node_name=require_non_empty_identifier(
            request.lineage.node_name,
            "lineage.node_name",
        ),
        domain_natural_key=domain_natural_key,
        source_timestamp=source_timestamp,
    )


def build_projected_record_id(
    *,
    record_type: str,
    execution_id: str,
    node_name: str,
    domain_natural_key: str,
    source_timestamp: datetime | str,
) -> str:
    """Build a stable record ID from the canonical projection identity seed.

    Projectors should use this for records derived deterministically from an
    archived workflow output. The seed deliberately includes execution lineage,
    the producing node, the domain natural key, and the source/observation
    timestamp so replaying the same archived evidence updates the same record
    instead of creating duplicates.
    """
    clean_record_type = require_non_empty_identifier(record_type, "record_type")
    seed = "|".join(
        (
            WORKFLOW_OUTPUT_PROJECTED_RECORD_NAMESPACE,
            clean_record_type,
            require_non_empty_identifier(execution_id, "execution_id"),
            require_non_empty_identifier(node_name, "node_name"),
            require_non_empty_identifier(domain_natural_key, "domain_natural_key"),
            _source_timestamp_token(source_timestamp),
        )
    )
    return f"{clean_record_type}:{uuid5(NAMESPACE_URL, seed)}"


def _source_timestamp_token(source_timestamp: datetime | str) -> str:
    if isinstance(source_timestamp, datetime):
        return source_timestamp.isoformat()
    return require_non_empty_identifier(source_timestamp, "source_timestamp")


def _validate_node_output_belongs_to_run(
    *,
    run: CompletedRunRecord,
    node_output: CompletedNodeOutputRecord,
) -> None:
    expected_actual_pairs = (
        ("run_id", run.run_id, node_output.run_id),
        ("workflow_name", run.workflow_name, node_output.workflow_name),
        ("execution_id", run.execution_id, node_output.execution_id),
    )
    for field_name, expected, actual in expected_actual_pairs:
        if expected != actual:
            raise ValueError(
                "node output does not belong to completed run: "
                f"{field_name} expected {expected!r}, got {actual!r}."
            )
