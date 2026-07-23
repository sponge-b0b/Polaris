from __future__ import annotations

from datetime import UTC, datetime

import pytest

from application.projections.workflow_outputs import (
    WorkflowOutputProjectorRequest,
    build_projected_record_id,
    build_projected_record_identity,
    build_projected_record_identity_from_projector_request,
    build_workflow_output_projection_lineage,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunRecord,
)
from core.storage.persistence.lineage import PersistenceLineage


def test_build_workflow_output_projection_lineage_uses_run_and_node_context() -> None:
    lineage = build_workflow_output_projection_lineage(run=_run(), node_output=_node())

    assert lineage == PersistenceLineage(
        workflow_name="morning_report",
        execution_id="exec-1",
        runtime_id="runtime-1",
        node_name="technical_agent",
    )


def test_build_workflow_output_projection_lineage_rejects_mismatched_node() -> None:
    with pytest.raises(ValueError, match="node output does not belong"):
        build_workflow_output_projection_lineage(
            run=_run(),
            node_output=_node(execution_id="other-exec"),
        )


def test_build_projected_record_id_is_deterministic_and_seeded_by_required_parts() -> (
    None
):
    timestamp = datetime(2026, 7, 9, 12, tzinfo=UTC)

    first = build_projected_record_id(
        record_type="technical_analysis_snapshot",
        execution_id="exec-1",
        node_name="technical_agent",
        domain_natural_key="SPY",
        source_timestamp=timestamp,
    )
    second = build_projected_record_id(
        record_type="technical_analysis_snapshot",
        execution_id="exec-1",
        node_name="technical_agent",
        domain_natural_key="SPY",
        source_timestamp=timestamp,
    )
    changed = build_projected_record_id(
        record_type="technical_analysis_snapshot",
        execution_id="exec-1",
        node_name="technical_agent",
        domain_natural_key="QQQ",
        source_timestamp=timestamp,
    )

    assert first == second
    assert first.startswith("technical_analysis_snapshot:")
    assert first != changed


def test_build_projected_record_id_requires_source_timestamp_and_natural_key() -> None:
    with pytest.raises(ValueError, match="domain_natural_key cannot be empty"):
        build_projected_record_id(
            record_type="technical_analysis_snapshot",
            execution_id="exec-1",
            node_name="technical_agent",
            domain_natural_key=" ",
            source_timestamp=datetime(2026, 7, 9, 12, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="source_timestamp cannot be empty"):
        build_projected_record_id(
            record_type="technical_analysis_snapshot",
            execution_id="exec-1",
            node_name="technical_agent",
            domain_natural_key="SPY",
            source_timestamp=" ",
        )


def test_build_projected_record_identity_returns_persistence_identity() -> None:
    identity = build_projected_record_identity(
        record_type="technical_analysis_snapshot",
        execution_id="exec-1",
        node_name="technical_agent",
        domain_natural_key="SPY",
        source_timestamp="2026-07-09T12:00:00+00:00",
    )

    assert identity.record_type == "technical_analysis_snapshot"
    assert identity.record_id.startswith("technical_analysis_snapshot:")


def test_build_projected_record_identity_from_projector_request_uses_request_lineage() -> (  # noqa: E501
    None
):
    request = WorkflowOutputProjectorRequest(
        run=_run(),
        node_output=_node(),
        source_fingerprint="fingerprint-1",
        lineage=build_workflow_output_projection_lineage(
            run=_run(), node_output=_node()
        ),
    )

    identity = build_projected_record_identity_from_projector_request(
        request=request,
        record_type="technical_analysis_snapshot",
        domain_natural_key="SPY",
        source_timestamp=datetime(2026, 7, 9, 12, tzinfo=UTC),
    )

    assert request.lineage.execution_id == "exec-1"
    assert request.lineage.node_name == "technical_agent"
    assert identity.record_id.startswith("technical_analysis_snapshot:")


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
        inputs_json={},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
        completed_at=datetime(2026, 7, 9, 12, 5, tzinfo=UTC),
        duration_seconds=300.0,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
    )


def _node(*, execution_id: str = "exec-1") -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id=execution_id,
        node_name="technical_agent",
        node_type="runtime_node",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        status="succeeded",
        success=True,
        outputs={"technical_score": 0.8},
        metadata={},
        errors_json=(),
        started_at=datetime(2026, 7, 9, 12, tzinfo=UTC),
        completed_at=datetime(2026, 7, 9, 12, 1, tzinfo=UTC),
        duration_seconds=60.0,
    )
