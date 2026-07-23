from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest

import application.evaluations.model_replacement_gate as gate_module
from application.evaluations import (
    ModelReplacementGateSection,
    ModelReplacementGateStatus,
    ModelReplacementValidationGate,
    ModelReplacementValidationMode,
    ModelReplacementValidationRequest,
    RiskAuthorityGateFailureMode,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_slice_definition_by_name,
)
from application.evaluations.contracts import (
    EvaluationLangfuseProjectionResult,
    EvaluationRunServiceRequest,
    EvaluationRunServiceResult,
)
from config.settings import Settings
from core.storage.persistence.evaluation import EvaluationCaseRecord
from domain.evaluation import (
    EvaluationCase,
    EvaluationMetricResult,
    EvaluationRun,
    EvaluationScore,
    EvaluationStatus,
    EvaluationTargetType,
    EvaluationThreshold,
)


@dataclass(slots=True)
class FakeResultService:
    cases: dict[str, EvaluationCaseRecord]

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None:
        return self.cases.get(case_id)


@dataclass(slots=True)
class RecordingRunService:
    requests: list[EvaluationRunServiceRequest]
    score: float = 0.92
    status: EvaluationStatus = EvaluationStatus.PASSED
    status_by_run_id_fragment: dict[str, EvaluationStatus] = field(default_factory=dict)

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult:
        self.requests.append(request)
        status = self.status
        for fragment, fragment_status in self.status_by_run_id_fragment.items():
            if fragment in request.run_id:
                status = fragment_status
                break
        metric_results = tuple(
            _metric_result(
                run_id=request.run_id,
                case=case,
                metric_name=metric.metric_name,
                threshold=metric.threshold,
                score=self.score,
                status=status,
            )
            for case in request.cases
            for metric in request.metrics
        )
        return EvaluationRunServiceResult(
            run=EvaluationRun(
                run_id=request.run_id,
                target_type=request.target_type,
                status=status,
                evaluator_provider=request.evaluator_provider,
                evaluator_model=request.evaluator_model,
                dataset=request.dataset,
                case_ids=tuple(case.case_id for case in request.cases),
            ),
            metric_results=metric_results,
            persistence_result=_persistence_result(
                runs_written=2,
                metric_results_written=len(metric_results),
            ),
            langfuse_projection_result=EvaluationLangfuseProjectionResult(
                export_results=(),
                pending_count=len(metric_results),
            ),
        )


@pytest.mark.asyncio()
async def test_replacement_gate_runs_complete_replacement_validation() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-001",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
            low_vram_mode=True,
            required_vram_gb=5.0,
            available_vram_gb=8.0,
        )
    )

    assert result.passed_replacement_validation is True
    assert result.exploratory_smoke_only is False
    assert result.validation_scope == "replacement_validation"
    assert result.failed_sections == ()
    assert result.evaluation_run_count == len(run_service.requests)
    assert result.metric_result_count > 0
    assert result.langfuse_projection_attempted is True
    assert result.langfuse_pending_count == result.metric_result_count
    assert {
        ModelReplacementGateSection.STATIC_CONFIG_BOUNDARY,
        ModelReplacementGateSection.STRUCTURED_OUTPUT,
        ModelReplacementGateSection.RAG,
        ModelReplacementGateSection.STRATEGY,
        ModelReplacementGateSection.EXECUTION_RISK_RECOMMENDATION,
        ModelReplacementGateSection.DEEPEVAL_PERSISTENCE,
        ModelReplacementGateSection.LANGFUSE_PROJECTION,
        ModelReplacementGateSection.LOCAL_OPERATIONS_READINESS,
        ModelReplacementGateSection.LOCAL_OPERATIONS,
    } <= {section.section for section in result.sections}
    local_readiness = _section(
        result,
        ModelReplacementGateSection.LOCAL_OPERATIONS_READINESS,
    )
    local_operations = _section(result, ModelReplacementGateSection.LOCAL_OPERATIONS)
    assert local_readiness.status is ModelReplacementGateStatus.PASSED
    assert local_readiness.details["timeout_seconds"] == 60.0
    assert local_readiness.details["minimum_timeout_seconds"] == 30.0
    assert local_readiness.details["recommended_max_concurrency"] == 1
    assert local_operations.status is ModelReplacementGateStatus.PASSED
    assert set(local_operations.case_ids) >= {
        "agent-task-completion-002",
        "agent-task-completion-004",
        "mcp-tool-response-001",
        "mcp-tool-response-003",
    }
    assert {request.target_type.value for request in run_service.requests} >= {
        "agent_task",
        "mcp_tool_response",
        "rag_answer",
        "strategy_synthesis",
        "recommendation_explanation",
    }
    assert any(
        "_local_operations_" in request.run_id for request in run_service.requests
    )
    assert all(
        request.run_id.startswith("model_replacement_gate_gate-001_")
        for request in run_service.requests
    )
    assert all(request.authority_metadata for request in run_service.requests)
    assert all(request.authority_gate_evidence for request in run_service.requests)
    assert {
        request.authority_metadata["gate_profile"] for request in run_service.requests
    } >= {"enhanced_provenance", "vigilant_decision_evidence"}
    execution_section = _section(
        result,
        ModelReplacementGateSection.EXECUTION_RISK_RECOMMENDATION,
    )
    assert execution_section.details["selected_risk_tier"] == "vigilant"
    assert (
        execution_section.details["selected_gate_profile"]
        == "vigilant_decision_evidence"
    )
    assert (
        execution_section.details["authority_gate_failure_mode"]
        == RiskAuthorityGateFailureMode.NONE.value
    )
    assert execution_section.details["model_replacement_gate_id"] == "gate-001"


def test_gate_requires_explicit_settings_dependency() -> None:
    gate_type: Any = ModelReplacementValidationGate

    with pytest.raises(TypeError, match="settings"):
        gate_type(
            result_service=FakeResultService({}),
            run_service=RecordingRunService([]),
        )


@pytest.mark.asyncio()
async def test_gate_reports_explicit_missing_configuration_without_defaults() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_missing_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-missing-config",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
        )
    )

    static_config = _section(
        result,
        ModelReplacementGateSection.STATIC_CONFIG_BOUNDARY,
    )

    assert result.passed_replacement_validation is False
    assert result.validation_failure_reason is not None
    assert static_config.status is ModelReplacementGateStatus.FAILED
    failures = cast("list[str]", static_config.details["failures"])
    assert any("litellm_gateway" in failure for failure in failures)
    assert any("candidate model is not present" in failure for failure in failures)
    assert run_service.requests == []


@pytest.mark.asyncio()
async def test_exploratory_smoke_mode_never_passes_replacement_validation() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-smoke",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.EXPLORATORY_SMOKE,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
        )
    )

    assert result.passed_replacement_validation is False
    assert result.exploratory_smoke_only is True
    assert result.validation_scope == "exploratory_smoke_only"
    assert result.validation_failure_reason == (
        "Exploratory smoke validations do not produce a default "
        "model/profile replacement validation pass."
    )
    assert result.evaluation_run_count == len(run_service.requests)
    assert result.metric_result_count > 0


@pytest.mark.asyncio()
async def test_gate_rejects_missing_model_regression_cases() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService({}),
        run_service=run_service,
        settings=_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-missing-cases",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
        )
    )

    assert result.passed_replacement_validation is False
    assert run_service.requests == []
    assert _section(result, ModelReplacementGateSection.STRUCTURED_OUTPUT).status is (
        ModelReplacementGateStatus.FAILED
    )
    assert _section(result, ModelReplacementGateSection.LOCAL_OPERATIONS).status is (
        ModelReplacementGateStatus.FAILED
    )
    assert (
        "No persisted model-regression cases"
        in _section(
            result,
            ModelReplacementGateSection.RAG,
        ).message
    )
    persistence_section = _section(
        result,
        ModelReplacementGateSection.DEEPEVAL_PERSISTENCE,
    )
    assert persistence_section.status is ModelReplacementGateStatus.SKIPPED


@pytest.mark.asyncio()
async def test_gate_reports_timeout_and_low_vram_readiness_failures() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-low-vram",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=5.0,
            low_vram_mode=True,
            required_vram_gb=10.0,
            available_vram_gb=4.0,
        )
    )

    local_readiness = _section(
        result,
        ModelReplacementGateSection.LOCAL_OPERATIONS_READINESS,
    )
    local_operations = _section(result, ModelReplacementGateSection.LOCAL_OPERATIONS)

    assert result.passed_replacement_validation is False
    assert local_readiness.status is ModelReplacementGateStatus.FAILED
    assert local_readiness.details["timeout_seconds"] == 5.0
    assert local_readiness.details["minimum_timeout_seconds"] == 30.0
    assert local_readiness.details["low_vram_mode"] is True
    assert local_readiness.details["required_vram_gb"] == 10.0
    assert local_readiness.details["available_vram_gb"] == 4.0
    assert local_readiness.details["recommended_max_concurrency"] == 1
    assert local_operations.status is ModelReplacementGateStatus.SKIPPED
    assert local_operations.details["skip_reason"] == "gate_prerequisites_failed"
    assert run_service.requests == []


@pytest.mark.asyncio()
async def test_gate_reports_failed_local_operations_behavior() -> None:
    run_service = RecordingRunService(
        [],
        status_by_run_id_fragment={"_local_operations_": EvaluationStatus.FAILED},
    )
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-local-failed",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
        )
    )

    local_operations = _section(result, ModelReplacementGateSection.LOCAL_OPERATIONS)

    assert result.passed_replacement_validation is False
    assert local_operations.status is ModelReplacementGateStatus.FAILED
    assert "failed" in local_operations.details["run_statuses"]
    assert result.validation_failure_reason is not None
    assert "local_operations" in result.validation_failure_reason


@pytest.mark.asyncio()
async def test_gate_reports_unsupported_local_operations_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_metric_specs = gate_module._metric_specs_for_target

    def metric_specs_without_local_operations(
        target_type: EvaluationTargetType,
    ) -> tuple[Any, ...]:
        if target_type in {
            EvaluationTargetType.AGENT_TASK,
            EvaluationTargetType.MCP_TOOL_RESPONSE,
        }:
            return ()
        return original_metric_specs(target_type)

    monkeypatch.setattr(
        gate_module,
        "_metric_specs_for_target",
        metric_specs_without_local_operations,
    )
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_validation_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-local-unsupported",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_VALIDATION,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
        )
    )

    local_operations = _section(result, ModelReplacementGateSection.LOCAL_OPERATIONS)

    assert result.passed_replacement_validation is False
    assert local_operations.status is ModelReplacementGateStatus.UNSUPPORTED
    assert (
        local_operations.details["unsupported_reason"]
        == "no_supported_metrics_for_target_type"
    )
    assert set(local_operations.details["unsupported_target_types"]) == {
        "agent_task",
        "mcp_tool_response",
    }
    assert set(local_operations.details["unsupported_case_ids"]) >= {
        "agent-task-completion-002",
        "mcp-tool-response-001",
    }


def _validation_settings() -> Settings:
    return Settings(
        LITELLM_ENABLED=True,
        LITELLM_API_KEY="test-api-key",
        LITELLM_REJECT_MODEL_FALLBACK=True,
        DEEPEVAL_ENABLED=True,
        DEEPEVAL_JUDGE_PROVIDER="litellm",
        DEEPEVAL_JUDGE_MODEL="polaris-local-evaluation",
        LANGFUSE_HOST="http://localhost:3000",
        LANGFUSE_PUBLIC_KEY="test-public-key",
        LANGFUSE_SECRET_KEY="test-secret-key",
        DEFAULT_MODEL="polaris-local-synthesis",
        STRUCTURED_OUTPUT_MODEL="polaris-local-synthesis",
        RAG_SYNTHESIS_MODEL="polaris-local-synthesis",
        STRATEGY_SYNTHESIS_MODEL="polaris-local-synthesis",
    )


def _missing_validation_settings() -> Settings:
    return Settings(
        LITELLM_ENABLED=False,
        LITELLM_API_KEY=None,
        LITELLM_REJECT_MODEL_FALLBACK=True,
        DEEPEVAL_ENABLED=False,
        DEEPEVAL_JUDGE_PROVIDER=None,
        DEEPEVAL_JUDGE_MODEL=None,
        LANGFUSE_HOST=None,
        LANGFUSE_PUBLIC_KEY=None,
        LANGFUSE_SECRET_KEY=None,
        DEFAULT_MODEL="unrelated-local-model",
        STRUCTURED_OUTPUT_MODEL="unrelated-local-model",
        RAG_SYNTHESIS_MODEL="unrelated-local-model",
        STRATEGY_SYNTHESIS_MODEL="unrelated-local-model",
    )


def _model_regression_records() -> dict[str, EvaluationCaseRecord]:
    records: dict[str, EvaluationCaseRecord] = {}
    slice_definition = canonical_evaluation_dataset_slice_definition_by_name(
        "model_regression"
    )
    fixture_root = Path("tests/evaluation/fixtures")
    for membership in slice_definition.memberships:
        definition = canonical_evaluation_dataset_definition_by_name(
            membership.dataset_name
        )
        if definition.deterministic_fixture_uri is None:
            raise AssertionError("model-regression fixture URI is required")
        fixture_path = fixture_root / Path(definition.deterministic_fixture_uri).name
        rows = _jsonl_rows(fixture_path)
        rows_by_case_id = {str(row["case_id"]): row for row in rows}
        for case_id in membership.case_ids:
            row = rows_by_case_id[case_id]
            records[case_id] = EvaluationCaseRecord(
                case_id=case_id,
                dataset_id=definition.reference.dataset_id,
                target_type=row["target_type"],
                input_text=str(row["input_text"]),
                actual_output=str(row["actual_output"]),
                expected_output=_optional_string(row.get("expected_output")),
                rubric=_optional_string(row.get("rubric")),
                source_record_ids=tuple(row.get("source_record_ids", ())),
                workflow_execution_id=_optional_string(
                    row.get("workflow_execution_id")
                ),
                retrieval_context=tuple(row.get("retrieval_context", ())),
                citation_context_ids=tuple(row.get("citation_context_ids", ())),
                tags=tuple(row.get("tags", ())),
            )
    return records


def _jsonl_rows(path: Path) -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(line) for line in path.read_text().splitlines() if line)


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AssertionError("expected optional string value")
    return value


def _metric_result(
    *,
    run_id: str,
    case: EvaluationCase,
    metric_name: str,
    threshold: EvaluationThreshold | None,
    score: float,
    status: EvaluationStatus,
) -> EvaluationMetricResult:
    effective_threshold = threshold or EvaluationThreshold(metric_name, 0.70)
    return EvaluationMetricResult(
        run_id=run_id,
        case_id=case.case_id,
        score=EvaluationScore(
            metric_name=metric_name,
            score=score,
            threshold=effective_threshold,
            reason="deterministic gate evaluation",
        ),
        status=status,
        evaluator_provider="deepeval",
        evaluator_model="polaris-local-evaluation",
        duration_ms=1.0,
    )


def _persistence_result(
    *,
    runs_written: int = 0,
    metric_results_written: int = 0,
) -> Any:
    from core.storage.persistence.evaluation import EvaluationPersistenceResult

    return EvaluationPersistenceResult(
        runs_written=runs_written,
        metric_results_written=metric_results_written,
    )


def _section(result: Any, section: ModelReplacementGateSection) -> Any:
    for item in result.sections:
        if item.section is section:
            return item
    raise AssertionError(f"missing section {section.value}")
