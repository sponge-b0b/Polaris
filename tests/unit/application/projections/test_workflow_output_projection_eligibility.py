from __future__ import annotations

from dataclasses import dataclass

import pytest

from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEligibilityContext,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEligibilityPolicy,
)
from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEligibilityStatus,
)
from application.projections.workflow_outputs import WorkflowOutputProjectionOutcome
from application.projections.workflow_outputs import WorkflowOutputProjectionRegistry
from application.projections.workflow_outputs import WorkflowOutputProjectionSkipReason
from application.projections.workflow_outputs import WorkflowOutputProjectorRegistration
from application.projections.workflow_outputs import WorkflowOutputProjectionStatus
from application.projections.workflow_outputs import WorkflowOutputProjectorRequest
from application.projections.workflow_outputs import WorkflowOutputQualityStatus
from application.projections.workflow_outputs import WorkflowProjectionExecutionMode
from core.storage.persistence.completed_run_archive import CompletedNodeOutputRecord
from core.storage.persistence.completed_run_archive import CompletedRunRecord


@dataclass(frozen=True, slots=True)
class StubProjector:
    projector_name: str

    async def project(
        self,
        request: WorkflowOutputProjectorRequest,
    ) -> WorkflowOutputProjectionOutcome:
        return WorkflowOutputProjectionOutcome(
            status=WorkflowOutputProjectionStatus.SUCCEEDED,
            projector_name=self.projector_name,
            node_name=request.node_output.node_name,
            output_contract=request.node_output.output_contract or "unsupported",
            output_schema_version=request.node_output.output_schema_version or 1,
            source_fingerprint=request.source_fingerprint,
            records_written=1,
        )


def test_policy_projects_successful_supported_node_output() -> None:
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(),
        ),
        _registry(),
    )

    assert decision.status is WorkflowOutputProjectionEligibilityStatus.ELIGIBLE
    assert decision.eligible is True
    assert decision.projector_name == "technical_projector"
    assert decision.skip_reason is None


def test_policy_skips_failed_and_skipped_node_outputs() -> None:
    failed = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(success=False, status="failed"),
        ),
        _registry(),
    )
    skipped = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(success=False, status="skipped"),
        ),
        _registry(),
    )

    assert failed.skipped is True
    assert failed.skip_reason is WorkflowOutputProjectionSkipReason.NODE_NOT_SUCCESSFUL
    assert skipped.skip_reason is WorkflowOutputProjectionSkipReason.NODE_SKIPPED


def test_policy_skips_backtest_and_simulated_execution_modes() -> None:
    for mode in (
        WorkflowProjectionExecutionMode.BACKTEST,
        WorkflowProjectionExecutionMode.SIMULATED,
    ):
        decision = _policy().evaluate(
            WorkflowOutputProjectionEligibilityContext(
                run=_run(),
                node_output=_node(),
                execution_mode=mode,
            ),
            _registry(),
        )

        assert decision.skipped is True
        assert (
            decision.skip_reason
            is WorkflowOutputProjectionSkipReason.NON_PRODUCTION_EXECUTION
        )


def test_policy_allows_replay_and_force_reproject_for_normal_completed_runs() -> None:
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(),
            execution_mode="replay",
            force_reproject=True,
        ),
        _registry(),
    )

    assert decision.eligible is True
    assert decision.projector_name == "technical_projector"


def test_policy_skips_unknown_contract_and_schema_version() -> None:
    unknown_contract = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(output_contract="polaris.news.analysis"),
        ),
        _registry(),
    )
    unknown_version = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(output_schema_version=2),
        ),
        _registry(),
    )

    assert (
        unknown_contract.skip_reason
        is WorkflowOutputProjectionSkipReason.UNSUPPORTED_CONTRACT
    )
    assert (
        unknown_version.skip_reason
        is WorkflowOutputProjectionSkipReason.UNSUPPORTED_SCHEMA_VERSION
    )


def test_policy_uses_node_name_only_as_additional_validation() -> None:
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(node_name="portfolio_state_builder"),
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason is WorkflowOutputProjectionSkipReason.UNSUPPORTED_NODE_NAME
    )


def test_policy_skips_degraded_output_without_first_class_target_quality_fields() -> (
    None
):
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(),
            quality_status=WorkflowOutputQualityStatus.DEGRADED,
        ),
        _registry(persists_quality_status=False),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.QUALITY_STATUS_NOT_PERSISTABLE
    )


def test_policy_allows_degraded_output_when_projector_persists_quality_status() -> None:
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(),
            quality_status="fallback",
        ),
        _registry(persists_quality_status=True),
    )

    assert decision.eligible is True
    assert decision.projector_name == "technical_projector"


def test_context_rejects_unknown_execution_mode_and_quality_status() -> None:
    with pytest.raises(ValueError, match="Unsupported completed-run execution mode"):
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(),
            execution_mode="paper",
        )

    with pytest.raises(ValueError, match="Unsupported workflow output quality status"):
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(),
            quality_status="partial",
        )


def _policy() -> WorkflowOutputProjectionEligibilityPolicy:
    return WorkflowOutputProjectionEligibilityPolicy()


def _registry(
    *, persists_quality_status: bool = False
) -> WorkflowOutputProjectionRegistry:
    return WorkflowOutputProjectionRegistry(
        (
            WorkflowOutputProjectorRegistration(
                projector_name="technical_projector",
                output_contract="polaris.market.technical_analysis",
                output_schema_version=1,
                projector=StubProjector(projector_name="technical_projector"),
                supported_node_names=("technical_agent",),
                persists_quality_status=persists_quality_status,
            ),
        )
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
        inputs_json={},
        outputs_json={},
        metadata={},
        errors_json=(),
        started_at=None,
        completed_at=None,
        duration_seconds=None,
        node_count=1,
        completed_node_count=1,
        failed_node_count=0,
    )


def _node(
    *,
    node_name: str = "technical_agent",
    success: bool | None = True,
    status: str = "succeeded",
    output_contract: str | None = "polaris.market.technical_analysis",
    output_schema_version: int | None = 1,
) -> CompletedNodeOutputRecord:
    return CompletedNodeOutputRecord(
        node_output_id="node-output-1",
        run_id="run-1",
        workflow_name="morning_report",
        execution_id="exec-1",
        node_name=node_name,
        node_type="runtime_node",
        output_contract=output_contract,
        output_schema_version=output_schema_version,
        status=status,
        success=success,
        outputs={"technical_score": 0.8},
        metadata={},
        errors_json=(),
        started_at=None,
        completed_at=None,
        duration_seconds=None,
    )
