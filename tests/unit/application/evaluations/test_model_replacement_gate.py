from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from application.evaluations import (
    ModelReplacementGateSection,
    ModelReplacementGateStatus,
    ModelReplacementValidationGate,
    ModelReplacementValidationMode,
    ModelReplacementValidationRequest,
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

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult:
        self.requests.append(request)
        metric_results = tuple(
            _metric_result(
                run_id=request.run_id,
                case=case,
                metric_name=metric.metric_name,
                threshold=metric.threshold,
                score=self.score,
                status=self.status,
            )
            for case in request.cases
            for metric in request.metrics
        )
        return EvaluationRunServiceResult(
            run=EvaluationRun(
                run_id=request.run_id,
                target_type=request.target_type,
                status=self.status,
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
async def test_replacement_gate_runs_complete_approval_validation() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_approval_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-001",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_APPROVAL,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
            low_vram_mode=True,
            required_vram_gb=5.0,
            available_vram_gb=8.0,
        )
    )

    assert result.approved_for_replacement is True
    assert result.exploratory_smoke_only is False
    assert result.approval_scope == "replacement_approval"
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
        ModelReplacementGateSection.LOCAL_OPERATIONS,
    } <= {section.section for section in result.sections}
    assert {request.target_type.value for request in run_service.requests} >= {
        "rag_answer",
        "strategy_synthesis",
        "recommendation_explanation",
    }
    assert all(
        request.run_id.startswith("model_replacement_gate_gate-001_")
        for request in run_service.requests
    )


@pytest.mark.asyncio()
async def test_exploratory_smoke_mode_never_approves_replacement() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_approval_settings(),
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

    assert result.approved_for_replacement is False
    assert result.exploratory_smoke_only is True
    assert result.approval_scope == "exploratory_smoke_only"
    assert result.approval_denial_reason == (
        "Exploratory smoke validations cannot approve default "
        "model/profile replacement."
    )
    assert result.evaluation_run_count == len(run_service.requests)
    assert result.metric_result_count > 0


@pytest.mark.asyncio()
async def test_gate_rejects_missing_model_regression_cases() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService({}),
        run_service=run_service,
        settings=_approval_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-missing-cases",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_APPROVAL,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=60.0,
        )
    )

    assert result.approved_for_replacement is False
    assert run_service.requests == []
    assert _section(result, ModelReplacementGateSection.STRUCTURED_OUTPUT).status is (
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
async def test_gate_reports_timeout_and_low_vram_viability_failures() -> None:
    run_service = RecordingRunService([])
    gate = ModelReplacementValidationGate(
        result_service=FakeResultService(_model_regression_records()),
        run_service=run_service,
        settings=_approval_settings(),
    )

    result = await gate.validate(
        ModelReplacementValidationRequest(
            gate_id="gate-low-vram",
            candidate_profile_name="local-qwen-profile",
            candidate_model="polaris-local-synthesis",
            mode=ModelReplacementValidationMode.REPLACEMENT_APPROVAL,
            evaluator_provider="litellm",
            evaluator_model="polaris-local-evaluation",
            timeout_seconds=5.0,
            low_vram_mode=True,
            required_vram_gb=10.0,
            available_vram_gb=4.0,
        )
    )

    local_operations = _section(result, ModelReplacementGateSection.LOCAL_OPERATIONS)

    assert result.approved_for_replacement is False
    assert local_operations.status is ModelReplacementGateStatus.FAILED
    assert local_operations.details["timeout_seconds"] == 5.0
    assert local_operations.details["minimum_timeout_seconds"] == 30.0
    assert local_operations.details["low_vram_mode"] is True
    assert local_operations.details["required_vram_gb"] == 10.0
    assert local_operations.details["available_vram_gb"] == 4.0
    assert run_service.requests == []


def _approval_settings() -> Settings:
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
