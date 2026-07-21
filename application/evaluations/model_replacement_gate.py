from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from application.evaluations.contracts import (
    EvaluationRunServiceRequest,
    EvaluationRunServiceResult,
)
from application.evaluations.evaluation_datasets import (
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_slice_definition_by_name,
)
from application.evaluations.rag_evaluation_metrics import (
    intelligence_evaluation_metric_specs,
    rag_evaluation_metric_specs,
)
from config.rag_model_config import RagModelConfig
from config.settings import Settings
from config.strategy_model_config import StrategyModelConfig
from core.storage.persistence.evaluation import (
    EvaluationCaseRecord,
    JsonObject,
    JsonValue,
)
from domain.evaluation import (
    EvaluationCase,
    EvaluationDatasetReference,
    EvaluationStatus,
    EvaluationTargetType,
)
from integration.providers.llm_evaluation import EvaluationMetricSpec

MODEL_REPLACEMENT_DATASET_SLICE_NAME = "model_regression"
MODEL_REPLACEMENT_MINIMUM_TIMEOUT_SECONDS = 30.0


class ModelReplacementValidationMode(StrEnum):
    """Execution scope for model/profile validation gate attempts."""

    EXPLORATORY_SMOKE = "exploratory_smoke"
    REPLACEMENT_VALIDATION = "replacement_validation"


class ModelReplacementGateStatus(StrEnum):
    """Section-level status for the model replacement validation gate."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ModelReplacementGateSection(StrEnum):
    """Canonical checks that must pass for model replacement validation."""

    STATIC_CONFIG_BOUNDARY = "static_config_boundary"
    STRUCTURED_OUTPUT = "structured_output"
    RAG = "rag"
    STRATEGY = "strategy"
    EXECUTION_RISK_RECOMMENDATION = "execution_risk_recommendation"
    DEEPEVAL_PERSISTENCE = "deepeval_persistence"
    LANGFUSE_PROJECTION = "langfuse_projection"
    LOCAL_OPERATIONS = "local_operations"


@dataclass(frozen=True, slots=True)
class ModelReplacementValidationRequest:
    """Application request for validating a candidate default model/profile."""

    candidate_profile_name: str
    candidate_model: str
    evaluator_provider: str
    evaluator_model: str
    gate_id: str | None = None
    mode: ModelReplacementValidationMode | str = (
        ModelReplacementValidationMode.REPLACEMENT_VALIDATION
    )
    dataset_slice_name: str = MODEL_REPLACEMENT_DATASET_SLICE_NAME
    timeout_seconds: float | None = None
    low_vram_mode: bool = False
    required_vram_gb: float | None = None
    available_vram_gb: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "candidate_profile_name",
            _clean_required(self.candidate_profile_name, "candidate_profile_name"),
        )
        object.__setattr__(
            self,
            "candidate_model",
            _clean_required(self.candidate_model, "candidate_model"),
        )
        object.__setattr__(
            self,
            "evaluator_provider",
            _clean_required(self.evaluator_provider, "evaluator_provider"),
        )
        object.__setattr__(
            self,
            "evaluator_model",
            _clean_required(self.evaluator_model, "evaluator_model"),
        )
        if self.gate_id is not None:
            object.__setattr__(
                self,
                "gate_id",
                _clean_required(self.gate_id, "gate_id"),
            )
        object.__setattr__(
            self,
            "mode",
            _coerce_validation_mode(self.mode),
        )
        object.__setattr__(
            self,
            "dataset_slice_name",
            _clean_required(self.dataset_slice_name, "dataset_slice_name"),
        )
        if self.timeout_seconds is not None and self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")
        if self.required_vram_gb is not None and self.required_vram_gb <= 0.0:
            raise ValueError("required_vram_gb must be greater than 0.0.")
        if self.available_vram_gb is not None and self.available_vram_gb <= 0.0:
            raise ValueError("available_vram_gb must be greater than 0.0.")

    @property
    def effective_gate_id(self) -> str:
        return self.gate_id or f"{uuid4().hex}"


@dataclass(frozen=True, slots=True)
class ModelReplacementGateSectionResult:
    """Outcome for one section of the replacement validation gate."""

    section: ModelReplacementGateSection
    status: ModelReplacementGateStatus
    message: str
    details: JsonObject
    run_ids: tuple[str, ...] = ()
    case_ids: tuple[str, ...] = ()
    metric_result_count: int = 0

    @property
    def passed(self) -> bool:
        return self.status is ModelReplacementGateStatus.PASSED


@dataclass(frozen=True, slots=True)
class ModelReplacementValidationResult:
    """Full gate result for a candidate model/profile validation attempt.

    The pass/fail fields report validation evidence only; they are not
    governance approval decisions and do not mutate runtime model defaults.
    """

    gate_id: str
    candidate_profile_name: str
    candidate_model: str
    mode: ModelReplacementValidationMode
    sections: tuple[ModelReplacementGateSectionResult, ...]
    passed_replacement_validation: bool
    validation_failure_reason: str | None = None

    @property
    def validation_scope(self) -> str:
        if self.mode is ModelReplacementValidationMode.EXPLORATORY_SMOKE:
            return "exploratory_smoke_only"
        return "replacement_validation"

    @property
    def exploratory_smoke_only(self) -> bool:
        return self.mode is ModelReplacementValidationMode.EXPLORATORY_SMOKE

    @property
    def failed_sections(self) -> tuple[ModelReplacementGateSection, ...]:
        return tuple(
            section.section
            for section in self.sections
            if section.status is ModelReplacementGateStatus.FAILED
        )

    @property
    def evaluation_run_ids(self) -> tuple[str, ...]:
        return tuple(run_id for section in self.sections for run_id in section.run_ids)

    @property
    def evaluation_run_count(self) -> int:
        return len(self.evaluation_run_ids)

    @property
    def metric_result_count(self) -> int:
        return sum(section.metric_result_count for section in self.sections)

    @property
    def langfuse_projection_attempted(self) -> bool:
        section = _find_section(
            self.sections,
            ModelReplacementGateSection.LANGFUSE_PROJECTION,
        )
        if section is None:
            return False
        return bool(section.details.get("attempted"))

    @property
    def langfuse_exported_count(self) -> int:
        return _langfuse_count(self.sections, "exported_count")

    @property
    def langfuse_pending_count(self) -> int:
        return _langfuse_count(self.sections, "pending_count")

    @property
    def langfuse_failed_count(self) -> int:
        return _langfuse_count(self.sections, "failed_count")

    @property
    def langfuse_skipped_count(self) -> int:
        return _langfuse_count(self.sections, "skipped_count")


class ModelReplacementResultServicePort(Protocol):
    """Read boundary for persisted evaluation cases used by the gate."""

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None: ...


class ModelReplacementRunServicePort(Protocol):
    """Evaluation execution boundary used by the gate."""

    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult: ...


@dataclass(frozen=True, slots=True)
class _LoadedCase:
    record: EvaluationCaseRecord
    dataset: EvaluationDatasetReference

    @property
    def case_id(self) -> str:
        return self.record.case_id

    @property
    def target_type(self) -> EvaluationTargetType:
        return _coerce_target_type(self.record.target_type)

    @property
    def tags(self) -> frozenset[str]:
        return frozenset(self.record.tags)


@dataclass(frozen=True, slots=True)
class _EvaluationAccumulator:
    run_ids: tuple[str, ...]
    metric_result_count: int
    statuses: tuple[EvaluationStatus, ...]
    langfuse_exported_count: int
    langfuse_pending_count: int
    langfuse_failed_count: int
    langfuse_skipped_count: int
    persistence_runs_written: int
    persistence_metric_results_written: int

    @property
    def passed(self) -> bool:
        return bool(self.run_ids) and all(
            status is EvaluationStatus.PASSED for status in self.statuses
        )


@dataclass(frozen=True, slots=True)
class ModelReplacementValidationGate:
    """Validate candidate model/profile replacement through canonical evaluations."""

    result_service: ModelReplacementResultServicePort
    run_service: ModelReplacementRunServicePort
    settings: Settings

    async def validate(
        self,
        request: ModelReplacementValidationRequest,
    ) -> ModelReplacementValidationResult:
        gate_id = request.effective_gate_id
        sections: list[ModelReplacementGateSectionResult] = []
        static_section = _static_config_boundary_section(self.settings, request)
        local_section = _local_operations_section(self.settings, request)
        sections.extend((static_section, local_section))

        loaded_cases = await self._load_cases(request)
        if static_section.passed and local_section.passed and loaded_cases:
            sections.extend(
                await self._evaluation_sections(
                    gate_id,
                    request,
                    loaded_cases,
                )
            )
        else:
            sections.extend(_skipped_evaluation_sections(loaded_cases))

        passed_validation = _passed_replacement_validation(request.mode, sections)
        return ModelReplacementValidationResult(
            gate_id=gate_id,
            candidate_profile_name=request.candidate_profile_name,
            candidate_model=request.candidate_model,
            mode=_coerce_validation_mode(request.mode),
            sections=tuple(sections),
            passed_replacement_validation=passed_validation,
            validation_failure_reason=_validation_failure_reason(
                request.mode, sections
            ),
        )

    async def _load_cases(
        self,
        request: ModelReplacementValidationRequest,
    ) -> tuple[_LoadedCase, ...]:
        slice_definition = canonical_evaluation_dataset_slice_definition_by_name(
            request.dataset_slice_name
        )
        loaded_cases: list[_LoadedCase] = []
        for membership in slice_definition.memberships:
            dataset_definition = canonical_evaluation_dataset_definition_by_name(
                membership.dataset_name
            )
            for case_id in membership.case_ids:
                case_record = await self.result_service.get_case(case_id)
                if case_record is None:
                    continue
                if case_record.dataset_id != dataset_definition.reference.dataset_id:
                    continue
                loaded_cases.append(
                    _LoadedCase(
                        record=case_record,
                        dataset=dataset_definition.reference,
                    )
                )
        return tuple(loaded_cases)

    async def _evaluation_sections(
        self,
        gate_id: str,
        request: ModelReplacementValidationRequest,
        loaded_cases: tuple[_LoadedCase, ...],
    ) -> tuple[ModelReplacementGateSectionResult, ...]:
        section_results: list[ModelReplacementGateSectionResult] = []
        section_accumulators: list[_EvaluationAccumulator] = []
        for section, cases in _cases_by_validation_section(loaded_cases):
            accumulator = await self._run_section_evaluations(
                gate_id,
                section,
                request,
                cases,
            )
            section_accumulators.append(accumulator)
            section_results.append(
                _evaluation_section_result(section, cases, accumulator)
            )
        section_results.append(_deepeval_persistence_section(section_accumulators))
        section_results.append(_langfuse_projection_section(section_accumulators))
        return tuple(section_results)

    async def _run_section_evaluations(
        self,
        gate_id: str,
        section: ModelReplacementGateSection,
        request: ModelReplacementValidationRequest,
        loaded_cases: tuple[_LoadedCase, ...],
    ) -> _EvaluationAccumulator:
        run_ids: list[str] = []
        statuses: list[EvaluationStatus] = []
        metric_result_count = 0
        exported_count = 0
        pending_count = 0
        failed_count = 0
        skipped_count = 0
        persistence_runs_written = 0
        persistence_metric_results_written = 0

        grouped_cases = _group_cases_by_target_and_dataset(loaded_cases)
        for (target_type, dataset), cases in grouped_cases.items():
            metrics = _metric_specs_for_target(target_type)
            if not metrics:
                continue
            run_id = _evaluation_run_id(gate_id, section, target_type, dataset)
            result = await self.run_service.run_evaluation(
                EvaluationRunServiceRequest(
                    run_id=run_id,
                    target_type=target_type,
                    cases=tuple(
                        _case_record_to_domain(case.record, case.dataset)
                        for case in cases
                    ),
                    metrics=metrics,
                    evaluator_provider=request.evaluator_provider,
                    evaluator_model=request.evaluator_model,
                    dataset=dataset,
                    timeout_seconds=request.timeout_seconds,
                )
            )
            run_ids.append(result.run.run_id)
            statuses.append(result.run.status)
            metric_result_count += result.metric_result_count
            persistence_runs_written += result.persistence_result.runs_written
            persistence_metric_results_written += (
                result.persistence_result.metric_results_written
            )
            projection = result.langfuse_projection_result
            if projection is not None:
                exported_count += projection.exported_count
                pending_count += projection.pending_count
                failed_count += projection.failed_count
                skipped_count += projection.skipped_count
        return _EvaluationAccumulator(
            run_ids=tuple(run_ids),
            metric_result_count=metric_result_count,
            statuses=tuple(statuses),
            langfuse_exported_count=exported_count,
            langfuse_pending_count=pending_count,
            langfuse_failed_count=failed_count,
            langfuse_skipped_count=skipped_count,
            persistence_runs_written=persistence_runs_written,
            persistence_metric_results_written=persistence_metric_results_written,
        )


def _static_config_boundary_section(
    settings: Settings,
    request: ModelReplacementValidationRequest,
) -> ModelReplacementGateSectionResult:
    failures: list[str] = []
    details: dict[str, JsonValue] = {
        "candidate_profile_name": request.candidate_profile_name,
        "candidate_model": request.candidate_model,
    }
    for validator_name, validator in (
        (
            "litellm_gateway",
            lambda: settings.validate_litellm_gateway(require_configured=True),
        ),
        (
            "deepeval_evaluation",
            lambda: settings.validate_deepeval_evaluation(require_configured=True),
        ),
        (
            "langfuse_observability",
            lambda: settings.validate_langfuse_observability(require_configured=True),
        ),
    ):
        try:
            validator()
        except ValueError as exc:
            failures.append(f"{validator_name}: {exc}")
    try:
        strategy_config = StrategyModelConfig.from_settings(settings)
        rag_config = RagModelConfig.from_settings(settings)
    except ValueError as exc:
        failures.append(f"model_config: {exc}")
        strategy_config = None
        rag_config = None
    aliases = _configured_candidate_aliases(settings, request.candidate_model)
    details["configured_candidate_aliases"] = aliases
    details["structured_output_provider"] = settings.STRUCTURED_OUTPUT_PROVIDER
    details["structured_output_mode"] = settings.STRUCTURED_OUTPUT_INSTRUCTOR_MODE
    if strategy_config is not None:
        details["strategy_synthesis_model"] = strategy_config.synthesis_model
    if rag_config is not None:
        details["rag_synthesis_model"] = rag_config.synthesis_model
    if not aliases:
        failures.append(
            "candidate model is not present on any configured model boundary."
        )
    if not settings.LITELLM_REJECT_MODEL_FALLBACK:
        failures.append("LiteLLM model fallback must be rejected for replacements.")
    if failures:
        return ModelReplacementGateSectionResult(
            section=ModelReplacementGateSection.STATIC_CONFIG_BOUNDARY,
            status=ModelReplacementGateStatus.FAILED,
            message="Static/config boundary checks failed.",
            details={**details, "failures": failures},
        )
    return ModelReplacementGateSectionResult(
        section=ModelReplacementGateSection.STATIC_CONFIG_BOUNDARY,
        status=ModelReplacementGateStatus.PASSED,
        message="Static/config boundary checks passed.",
        details=details,
    )


def _local_operations_section(
    settings: Settings,
    request: ModelReplacementValidationRequest,
) -> ModelReplacementGateSectionResult:
    timeout_seconds = request.timeout_seconds or settings.DEEPEVAL_TIMEOUT_SECONDS
    failures: list[str] = []
    if timeout_seconds < MODEL_REPLACEMENT_MINIMUM_TIMEOUT_SECONDS:
        failures.append("timeout_seconds is below the replacement-gate minimum.")
    if request.low_vram_mode:
        if request.required_vram_gb is None:
            failures.append("required_vram_gb is required in low-VRAM mode.")
        if request.available_vram_gb is None:
            failures.append("available_vram_gb is required in low-VRAM mode.")
        if (
            request.required_vram_gb is not None
            and request.available_vram_gb is not None
            and request.required_vram_gb > request.available_vram_gb
        ):
            failures.append("candidate model requires more VRAM than is available.")
    details: JsonObject = {
        "timeout_seconds": timeout_seconds,
        "minimum_timeout_seconds": MODEL_REPLACEMENT_MINIMUM_TIMEOUT_SECONDS,
        "low_vram_mode": request.low_vram_mode,
        "required_vram_gb": request.required_vram_gb,
        "available_vram_gb": request.available_vram_gb,
        "litellm_max_concurrency": settings.LITELLM_MAX_CONCURRENCY,
        "deepeval_max_concurrency": settings.DEEPEVAL_MAX_CONCURRENCY,
    }
    if failures:
        return ModelReplacementGateSectionResult(
            section=ModelReplacementGateSection.LOCAL_OPERATIONS,
            status=ModelReplacementGateStatus.FAILED,
            message="Local operations viability checks failed.",
            details={**details, "failures": failures},
        )
    return ModelReplacementGateSectionResult(
        section=ModelReplacementGateSection.LOCAL_OPERATIONS,
        status=ModelReplacementGateStatus.PASSED,
        message="Local operations viability checks passed.",
        details=details,
    )


def _cases_by_validation_section(
    loaded_cases: tuple[_LoadedCase, ...],
) -> tuple[tuple[ModelReplacementGateSection, tuple[_LoadedCase, ...]], ...]:
    return (
        (
            ModelReplacementGateSection.STRUCTURED_OUTPUT,
            _filter_cases(loaded_cases, tags={"structured_output"}),
        ),
        (
            ModelReplacementGateSection.RAG,
            _filter_cases(
                loaded_cases,
                target_types=_RAG_TARGET_TYPES,
                tags={"rag_quality", "rag_grounding", "prompt_injection"},
            ),
        ),
        (
            ModelReplacementGateSection.STRATEGY,
            _filter_cases(
                loaded_cases,
                target_types={EvaluationTargetType.STRATEGY_SYNTHESIS},
                tags={"strategy_hypothesis", "strategy_synthesis"},
            ),
        ),
        (
            ModelReplacementGateSection.EXECUTION_RISK_RECOMMENDATION,
            _filter_cases(
                loaded_cases,
                target_types={EvaluationTargetType.RECOMMENDATION_EXPLANATION},
                tags={"execution_risk", "recommendation_explanation"},
            ),
        ),
    )


def _filter_cases(
    loaded_cases: tuple[_LoadedCase, ...],
    *,
    target_types: (
        set[EvaluationTargetType] | frozenset[EvaluationTargetType] | None
    ) = None,
    tags: set[str] | frozenset[str] | None = None,
) -> tuple[_LoadedCase, ...]:
    target_filter = frozenset(target_types or ())
    tag_filter = frozenset(tags or ())
    return tuple(
        loaded_case
        for loaded_case in loaded_cases
        if (not target_filter or loaded_case.target_type in target_filter)
        and (not tag_filter or bool(loaded_case.tags & tag_filter))
    )


def _evaluation_section_result(
    section: ModelReplacementGateSection,
    cases: tuple[_LoadedCase, ...],
    accumulator: _EvaluationAccumulator,
) -> ModelReplacementGateSectionResult:
    if not cases:
        return _missing_cases_section(section)
    if not accumulator.run_ids:
        return ModelReplacementGateSectionResult(
            section=section,
            status=ModelReplacementGateStatus.FAILED,
            message="No supported DeepEval metrics are configured for this section.",
            details={"case_count": len(cases), "case_ids": _case_ids(cases)},
            case_ids=_case_ids(cases),
        )
    status = (
        ModelReplacementGateStatus.PASSED
        if accumulator.passed
        else ModelReplacementGateStatus.FAILED
    )
    return ModelReplacementGateSectionResult(
        section=section,
        status=status,
        message=(
            f"{section.value} checks passed."
            if status is ModelReplacementGateStatus.PASSED
            else f"{section.value} checks failed."
        ),
        details={
            "case_count": len(cases),
            "case_ids": _case_ids(cases),
            "run_statuses": tuple(status.value for status in accumulator.statuses),
        },
        run_ids=accumulator.run_ids,
        case_ids=_case_ids(cases),
        metric_result_count=accumulator.metric_result_count,
    )


def _deepeval_persistence_section(
    accumulators: Sequence[_EvaluationAccumulator],
) -> ModelReplacementGateSectionResult:
    run_count = sum(len(accumulator.run_ids) for accumulator in accumulators)
    metric_result_count = sum(
        accumulator.metric_result_count for accumulator in accumulators
    )
    runs_written = sum(
        accumulator.persistence_runs_written for accumulator in accumulators
    )
    metric_results_written = sum(
        accumulator.persistence_metric_results_written for accumulator in accumulators
    )
    passed = run_count > 0 and runs_written > 0 and metric_results_written > 0
    return ModelReplacementGateSectionResult(
        section=ModelReplacementGateSection.DEEPEVAL_PERSISTENCE,
        status=(
            ModelReplacementGateStatus.PASSED
            if passed
            else ModelReplacementGateStatus.FAILED
        ),
        message=(
            "DeepEval evaluations ran and persisted results."
            if passed
            else "DeepEval evaluations did not persist replacement-gate results."
        ),
        details={
            "run_count": run_count,
            "metric_result_count": metric_result_count,
            "runs_written": runs_written,
            "metric_results_written": metric_results_written,
        },
    )


def _langfuse_projection_section(
    accumulators: Sequence[_EvaluationAccumulator],
) -> ModelReplacementGateSectionResult:
    exported_count = sum(
        accumulator.langfuse_exported_count for accumulator in accumulators
    )
    pending_count = sum(
        accumulator.langfuse_pending_count for accumulator in accumulators
    )
    failed_count = sum(
        accumulator.langfuse_failed_count for accumulator in accumulators
    )
    skipped_count = sum(
        accumulator.langfuse_skipped_count for accumulator in accumulators
    )
    accepted_count = exported_count + pending_count
    attempted = accepted_count + failed_count + skipped_count > 0
    passed = attempted and failed_count == 0 and accepted_count > 0
    return ModelReplacementGateSectionResult(
        section=ModelReplacementGateSection.LANGFUSE_PROJECTION,
        status=(
            ModelReplacementGateStatus.PASSED
            if passed
            else ModelReplacementGateStatus.FAILED
        ),
        message=(
            "Evaluation observations/results were projected to Langfuse."
            if passed
            else (
                "Evaluation observations/results were not accepted by "
                "Langfuse projection."
            )
        ),
        details={
            "attempted": attempted,
            "exported_count": exported_count,
            "pending_count": pending_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
        },
    )


def _skipped_evaluation_sections(
    loaded_cases: tuple[_LoadedCase, ...],
) -> tuple[ModelReplacementGateSectionResult, ...]:
    skipped: list[ModelReplacementGateSectionResult] = []
    for section, cases in _cases_by_validation_section(loaded_cases):
        if cases:
            skipped.append(
                ModelReplacementGateSectionResult(
                    section=section,
                    status=ModelReplacementGateStatus.SKIPPED,
                    message="Checks skipped because gate prerequisites failed.",
                    details={"case_count": len(cases), "case_ids": _case_ids(cases)},
                    case_ids=_case_ids(cases),
                )
            )
        else:
            skipped.append(_missing_cases_section(section))
    skipped.append(
        ModelReplacementGateSectionResult(
            section=ModelReplacementGateSection.DEEPEVAL_PERSISTENCE,
            status=ModelReplacementGateStatus.SKIPPED,
            message="DeepEval evaluation skipped because prerequisites failed.",
            details={"run_count": 0, "metric_result_count": 0},
        )
    )
    skipped.append(
        ModelReplacementGateSectionResult(
            section=ModelReplacementGateSection.LANGFUSE_PROJECTION,
            status=ModelReplacementGateStatus.SKIPPED,
            message="Langfuse projection skipped because DeepEval did not run.",
            details={
                "attempted": False,
                "exported_count": 0,
                "pending_count": 0,
                "failed_count": 0,
                "skipped_count": 0,
            },
        )
    )
    return tuple(skipped)


def _missing_cases_section(
    section: ModelReplacementGateSection,
) -> ModelReplacementGateSectionResult:
    return ModelReplacementGateSectionResult(
        section=section,
        status=ModelReplacementGateStatus.FAILED,
        message="No persisted model-regression cases are available for this check.",
        details={"case_count": 0, "case_ids": ()},
    )


def _passed_replacement_validation(
    mode: ModelReplacementValidationMode | str,
    sections: Sequence[ModelReplacementGateSectionResult],
) -> bool:
    if (
        _coerce_validation_mode(mode)
        is not ModelReplacementValidationMode.REPLACEMENT_VALIDATION
    ):
        return False
    return all(
        section.status is ModelReplacementGateStatus.PASSED for section in sections
    )


def _validation_failure_reason(
    mode: ModelReplacementValidationMode | str,
    sections: Sequence[ModelReplacementGateSectionResult],
) -> str | None:
    if (
        _coerce_validation_mode(mode)
        is ModelReplacementValidationMode.EXPLORATORY_SMOKE
    ):
        return (
            "Exploratory smoke validations do not produce a default "
            "model/profile replacement validation pass."
        )
    failed_sections = tuple(
        section.section.value
        for section in sections
        if section.status is not ModelReplacementGateStatus.PASSED
    )
    if failed_sections:
        return "Replacement validation failed gate sections: " + ", ".join(
            failed_sections
        )
    return None


def _group_cases_by_target_and_dataset(
    loaded_cases: tuple[_LoadedCase, ...],
) -> dict[
    tuple[EvaluationTargetType, EvaluationDatasetReference],
    tuple[_LoadedCase, ...],
]:
    grouped: defaultdict[
        tuple[EvaluationTargetType, EvaluationDatasetReference], list[_LoadedCase]
    ] = defaultdict(list)
    for loaded_case in loaded_cases:
        grouped[(loaded_case.target_type, loaded_case.dataset)].append(loaded_case)
    return {key: tuple(value) for key, value in grouped.items()}


def _metric_specs_for_target(
    target_type: EvaluationTargetType,
) -> tuple[EvaluationMetricSpec, ...]:
    if target_type in _RAG_TARGET_TYPES:
        return rag_evaluation_metric_specs()
    return intelligence_evaluation_metric_specs(target_type)


def _case_record_to_domain(
    record: EvaluationCaseRecord,
    dataset: EvaluationDatasetReference,
) -> EvaluationCase:
    return EvaluationCase(
        case_id=record.case_id,
        target_type=_coerce_target_type(record.target_type),
        input_text=record.input_text,
        actual_output=record.actual_output,
        dataset=dataset,
        expected_output=record.expected_output,
        rubric=record.rubric,
        source_record_ids=record.source_record_ids,
        workflow_execution_id=record.workflow_execution_id,
        langfuse_trace_id=record.langfuse_trace_id,
        langfuse_observation_id=record.langfuse_observation_id,
        retrieval_context=record.retrieval_context,
        citation_context_ids=record.citation_context_ids,
        tags=record.tags,
        created_at=record.created_at or datetime.now(UTC),
    )


def _evaluation_run_id(
    gate_id: str,
    section: ModelReplacementGateSection,
    target_type: EvaluationTargetType,
    dataset: EvaluationDatasetReference,
) -> str:
    return (
        f"model_replacement_gate_{gate_id}_{section.value}_"
        f"{target_type.value}_{dataset.name}"
    )


def _configured_candidate_aliases(
    settings: Settings,
    candidate_model: str,
) -> tuple[str, ...]:
    values = {
        "DEFAULT_MODEL": settings.DEFAULT_MODEL,
        "STRUCTURED_OUTPUT_MODEL": settings.STRUCTURED_OUTPUT_MODEL,
        "STRATEGY_PERSPECTIVE_REASONING_MODEL": (
            settings.STRATEGY_PERSPECTIVE_REASONING_MODEL
        ),
        "STRATEGY_SYNTHESIS_MODEL": settings.STRATEGY_SYNTHESIS_MODEL,
        "RAG_QUERY_REWRITE_MODEL": settings.RAG_QUERY_REWRITE_MODEL,
        "RAG_ADAPTIVE_TRIAGE_MODEL": settings.RAG_ADAPTIVE_TRIAGE_MODEL,
        "RAG_ROUTE_SELECTION_MODEL": settings.RAG_ROUTE_SELECTION_MODEL,
        "RAG_HYDE_MODEL": settings.RAG_HYDE_MODEL,
        "RAG_CRAG_GRADER_MODEL": settings.RAG_CRAG_GRADER_MODEL,
        "RAG_CRAG_QUERY_REWRITE_MODEL": settings.RAG_CRAG_QUERY_REWRITE_MODEL,
        "RAG_SELF_REFLECTION_MODEL": settings.RAG_SELF_REFLECTION_MODEL,
        "RAG_SYNTHESIS_MODEL": settings.RAG_SYNTHESIS_MODEL,
        "DSPY_OPTIMIZATION_MODEL": settings.DSPY_OPTIMIZATION_MODEL,
    }
    return tuple(name for name, value in values.items() if value == candidate_model)


def _find_section(
    sections: Sequence[ModelReplacementGateSectionResult],
    section_name: ModelReplacementGateSection,
) -> ModelReplacementGateSectionResult | None:
    for section in sections:
        if section.section is section_name:
            return section
    return None


def _langfuse_count(
    sections: Sequence[ModelReplacementGateSectionResult],
    key: str,
) -> int:
    section = _find_section(sections, ModelReplacementGateSection.LANGFUSE_PROJECTION)
    if section is None:
        return 0
    value = section.details.get(key, 0)
    return value if isinstance(value, int) else 0


def _case_ids(cases: tuple[_LoadedCase, ...]) -> tuple[str, ...]:
    return tuple(loaded_case.case_id for loaded_case in cases)


def _clean_required(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _coerce_validation_mode(
    value: ModelReplacementValidationMode | str,
) -> ModelReplacementValidationMode:
    if isinstance(value, ModelReplacementValidationMode):
        return value
    return ModelReplacementValidationMode(value)


def _coerce_target_type(value: EvaluationTargetType | str) -> EvaluationTargetType:
    if isinstance(value, EvaluationTargetType):
        return value
    return EvaluationTargetType(value)


_RAG_TARGET_TYPES = frozenset(
    {
        EvaluationTargetType.RAG_ANSWER,
        EvaluationTargetType.RAG_RETRIEVAL,
        EvaluationTargetType.RAG_GENERATION,
    }
)
