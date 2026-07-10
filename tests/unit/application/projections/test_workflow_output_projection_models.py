from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from application.projections.workflow_outputs import CompletedRunProjectionSummary
from application.projections.workflow_outputs import WorkflowOutputProjectionOutcome
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionReconciliationRequest,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionReconciliationResult,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRequest
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionRetryRequest,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionRetryResult
from application.projections.workflow_outputs import WorkflowOutputProjectionStatus


def test_projection_request_is_immutable_and_cleans_identifiers() -> None:
    request = WorkflowOutputProjectionRequest(
        workflow_name=" morning_report ",
        execution_id=" exec-1 ",
        run_id=" run-1 ",
    )

    assert request.workflow_name == "morning_report"
    assert request.execution_id == "exec-1"
    assert request.run_id == "run-1"

    with pytest.raises(FrozenInstanceError):
        request.workflow_name = "other"  # type: ignore[misc]


def test_projection_request_rejects_empty_required_fields() -> None:
    with pytest.raises(ValueError, match="workflow_name cannot be empty"):
        WorkflowOutputProjectionRequest(workflow_name=" ", execution_id="exec-1")

    with pytest.raises(ValueError, match="run_id cannot be empty"):
        WorkflowOutputProjectionRequest(
            workflow_name="morning_report",
            execution_id="exec-1",
            run_id=" ",
        )


def test_projection_outcome_coerces_status_and_validates_schema_version() -> None:
    outcome = WorkflowOutputProjectionOutcome(
        status="succeeded",
        projector_name="technical_projector",
        node_name="technical_agent",
        output_contract="polaris.market.technical_analysis",
        output_schema_version=1,
        source_fingerprint="fingerprint-1",
        records_written=2,
    )

    assert outcome.status is WorkflowOutputProjectionStatus.SUCCEEDED
    assert outcome.succeeded is True
    assert outcome.records_written == 2

    with pytest.raises(ValueError, match="output_schema_version must be positive"):
        WorkflowOutputProjectionOutcome(
            status=WorkflowOutputProjectionStatus.PENDING,
            projector_name="technical_projector",
            node_name="technical_agent",
            output_contract="polaris.market.technical_analysis",
            output_schema_version=0,
            source_fingerprint="fingerprint-1",
        )


def test_projection_summary_reports_counts_without_mutation() -> None:
    summary = CompletedRunProjectionSummary(
        workflow_name="morning_report",
        execution_id="exec-1",
        outcomes=(
            WorkflowOutputProjectionOutcome(
                status=WorkflowOutputProjectionStatus.SUCCEEDED,
                projector_name="technical_projector",
                node_name="technical_agent",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                source_fingerprint="fingerprint-1",
                records_written=3,
            ),
            WorkflowOutputProjectionOutcome(
                status=WorkflowOutputProjectionStatus.SKIPPED,
                projector_name="news_projector",
                node_name="news_agent",
                output_contract="polaris.news.analysis",
                output_schema_version=1,
                source_fingerprint="fingerprint-2",
            ),
            WorkflowOutputProjectionOutcome(
                status=WorkflowOutputProjectionStatus.FAILED,
                projector_name="portfolio_projector",
                node_name="portfolio_state_builder",
                output_contract="polaris.portfolio.state",
                output_schema_version=1,
                source_fingerprint="fingerprint-3",
                error_message="boom",
            ),
        ),
    )

    assert summary.total_jobs == 3
    assert summary.succeeded_jobs == 1
    assert summary.skipped_jobs == 1
    assert summary.failed_jobs == 1
    assert summary.records_written == 3
    assert summary.success is False


def test_retry_request_and_result_validate_retry_bounds() -> None:
    request = WorkflowOutputProjectionRetryRequest(
        workflow_name="morning_report",
        statuses=("failed", "skipped"),
        limit=10,
    )

    assert request.statuses == (
        WorkflowOutputProjectionStatus.FAILED,
        WorkflowOutputProjectionStatus.SKIPPED,
    )

    with pytest.raises(ValueError, match="limit must be positive"):
        WorkflowOutputProjectionRetryRequest(limit=0)

    with pytest.raises(ValueError, match="retried_jobs cannot exceed matched_jobs"):
        WorkflowOutputProjectionRetryResult(
            requested=request,
            matched_jobs=1,
            retried_jobs=2,
        )


def test_reconciliation_request_and_result_validate_bounds() -> None:
    request = WorkflowOutputProjectionReconciliationRequest(limit=25)

    assert request.dry_run is True
    assert request.enqueue_missing_jobs is False

    with pytest.raises(ValueError, match="limit must be positive"):
        WorkflowOutputProjectionReconciliationRequest(limit=0)

    with pytest.raises(ValueError, match="missing_projection_runs cannot exceed"):
        WorkflowOutputProjectionReconciliationResult(
            requested=request,
            scanned_runs=1,
            missing_projection_runs=2,
        )
