from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

from application.projections.workflow_outputs import (
    WorkflowOutputProjectionEligibilityContext,
    WorkflowOutputProjectionEligibilityPolicy,
    WorkflowOutputProjectionEligibilityStatus,
    WorkflowOutputProjectionOutcome,
    WorkflowOutputProjectionRegistry,
    WorkflowOutputProjectionSkipReason,
    WorkflowOutputProjectionStatus,
    WorkflowOutputProjectorRegistration,
    WorkflowOutputProjectorRequest,
    WorkflowOutputQualityStatus,
    WorkflowProjectionExecutionMode,
)
from core.storage.persistence.completed_run_archive import (
    CompletedNodeOutputRecord,
    CompletedRunRecord,
    JsonObject,
)
from domain.authority import (
    AiOutputContentType,
    AuthorityEffect,
    CanonicalOwner,
    IntendedSink,
    RiskAuthorityClassificationInput,
    RiskTier,
    SourceOfTruthCategory,
    classify_risk_authority,
)


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
    assert decision.authority_contract is not None
    assert decision.authority_contract.risk_tier is RiskTier.ENHANCED
    assert (
        decision.authority_contract.authority_effect is AuthorityEffect.CANONICAL_RECORD
    )
    assert (
        decision.authority_contract.intended_sink is IntendedSink.DURABLE_DOMAIN_RECORD
    )
    assert decision.authority_metadata == _authority_metadata()


def test_policy_requires_authority_metadata_for_durable_curation() -> None:
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={}),
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_REQUIRED
    )
    assert decision.authority_contract is None
    assert decision.authority_metadata is None


def test_policy_allows_explicit_internal_baseline_without_duplicative_metadata() -> (
    None
):
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={}),
            intended_sink=IntendedSink.INTERNAL_RUNTIME_EVIDENCE,
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.BASELINE_RUNTIME_EVIDENCE_ONLY
    )
    assert decision.authority_contract is not None
    assert decision.authority_contract.risk_tier is RiskTier.BASELINE
    assert (
        decision.authority_contract.intended_sink
        is IntendedSink.INTERNAL_RUNTIME_EVIDENCE
    )
    assert decision.authority_metadata == decision.authority_contract.to_metadata()


def test_policy_rejects_malformed_authority_metadata() -> None:
    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={"risk_authority": "enhanced"}),
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_MALFORMED
    )
    assert decision.authority_contract is None


def test_policy_rejects_authority_metadata_with_inconsistent_intended_sink() -> None:
    metadata = _authority_metadata(intended_sink=IntendedSink.RECOMMENDATION)

    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={"risk_authority": metadata}),
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_INCONSISTENT
    )
    assert decision.authority_contract is not None
    assert decision.authority_contract.intended_sink is IntendedSink.RECOMMENDATION
    assert decision.authority_metadata == metadata


def test_policy_rejects_tampered_authority_tier_before_projection() -> None:
    metadata = _authority_metadata()
    metadata["risk_tier"] = RiskTier.BASELINE.value
    metadata["gate_profile"] = "baseline_internal"

    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={"risk_authority": metadata}),
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.AUTHORITY_METADATA_INCONSISTENT
    )
    assert decision.authority_contract is not None
    assert decision.authority_contract.risk_tier is RiskTier.BASELINE


def test_policy_allows_vigilant_authority_metadata_when_consistent() -> None:
    metadata = _authority_metadata(capital_relevant=True, durable_authority=True)

    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={"risk_authority": metadata}),
        ),
        _registry(),
    )

    assert decision.eligible is True
    assert decision.authority_contract is not None
    assert decision.authority_contract.risk_tier is RiskTier.VIGILANT
    assert (
        decision.authority_contract.intended_sink is IntendedSink.DURABLE_DOMAIN_RECORD
    )


def test_policy_rejects_prohibited_outside_authority_before_projection() -> None:
    metadata = _authority_metadata(authority_effect=AuthorityEffect.OUTSIDE_AUTHORITY)

    decision = _policy().evaluate(
        WorkflowOutputProjectionEligibilityContext(
            run=_run(),
            node_output=_node(metadata={"risk_authority": metadata}),
        ),
        _registry(),
    )

    assert decision.skipped is True
    assert (
        decision.skip_reason
        is WorkflowOutputProjectionSkipReason.PROHIBITED_OUTSIDE_AUTHORITY
    )
    assert decision.authority_contract is not None
    assert (
        decision.authority_contract.risk_tier is RiskTier.PROHIBITED_OUTSIDE_AUTHORITY
    )
    assert "prohibited_outside_authority" in str(decision.message)


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


def test_policy_explicitly_excludes_report_and_backtest_persistence_boundaries() -> (
    None
):
    cases = (
        (
            "polaris.report.morning_report_document",
            WorkflowOutputProjectionSkipReason.REPORT_PERSISTENCE_BOUNDARY,
            "MorningReportPersistenceService",
        ),
        (
            "polaris.backtest.result_bundle",
            WorkflowOutputProjectionSkipReason.BACKTEST_PERSISTENCE_BOUNDARY,
            "BacktestPersistenceService",
        ),
    )

    for output_contract, skip_reason, owning_service in cases:
        decision = _policy().evaluate(
            WorkflowOutputProjectionEligibilityContext(
                run=_run(),
                node_output=_node(output_contract=output_contract),
            ),
            _registry(),
        )

        assert decision.skipped is True
        assert decision.skip_reason is skip_reason
        assert owning_service in str(decision.message)


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
    metadata: dict[str, object] | None = None,
) -> CompletedNodeOutputRecord:
    resolved_metadata = (
        {"risk_authority": _authority_metadata()} if metadata is None else metadata
    )
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
        metadata=cast(JsonObject, resolved_metadata),
        errors_json=(),
        started_at=None,
        completed_at=None,
        duration_seconds=None,
    )


def _authority_metadata(
    *,
    authority_effect: AuthorityEffect = AuthorityEffect.CANONICAL_RECORD,
    intended_sink: IntendedSink = IntendedSink.DURABLE_DOMAIN_RECORD,
    capital_relevant: bool = False,
    durable_authority: bool = True,
) -> dict[str, object]:
    return classify_risk_authority(
        RiskAuthorityClassificationInput(
            content_type=AiOutputContentType.DURABLE_RECORD,
            authority_effect=authority_effect,
            canonical_owner=CanonicalOwner.WORKFLOW_OUTPUT_CURATION,
            source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
            intended_sink=intended_sink,
            capital_relevant=capital_relevant,
            durable_authority=durable_authority,
        )
    ).to_metadata()
