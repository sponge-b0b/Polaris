from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, TypeVar
from uuid import uuid4

from application.evaluations import (
    EvaluationDatasetSeedRequest,
    EvaluationDatasetSeedResult,
    EvaluationResultBundle,
    EvaluationRunServiceRequest,
    EvaluationRunServiceResult,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_definitions,
    intelligence_evaluation_metric_specs,
    rag_evaluation_metric_specs,
)
from config.settings import Settings
from core.bootstrap.di_providers import application_request_scope
from core.storage.persistence.evaluation import (
    EvaluationCaseRecord,
    EvaluationDatasetRecord,
)
from domain.evaluation import (
    EvaluationCase,
    EvaluationDatasetReference,
    EvaluationTargetType,
)
from integration.providers.llm_evaluation import EvaluationMetricSpec

logger = logging.getLogger(__name__)

DependencyT = TypeVar("DependencyT")
_RAG_TARGET_TYPES = frozenset(
    {
        EvaluationTargetType.RAG_ANSWER,
        EvaluationTargetType.RAG_RETRIEVAL,
        EvaluationTargetType.RAG_GENERATION,
    }
)


class EvaluationResultServicePort(Protocol):
    async def get_dataset(self, dataset_id: str) -> EvaluationDatasetRecord | None: ...

    async def get_case(self, case_id: str) -> EvaluationCaseRecord | None: ...

    async def get_run_results(self, run_id: str) -> EvaluationResultBundle | None: ...

    async def list_dataset_cases(
        self,
        dataset_id: str,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]: ...

    async def list_latest_cases(
        self,
        target_type: EvaluationTargetType,
        *,
        limit: int | None = None,
    ) -> Sequence[EvaluationCaseRecord]: ...


class EvaluationRunServicePort(Protocol):
    async def run_evaluation(
        self,
        request: EvaluationRunServiceRequest,
    ) -> EvaluationRunServiceResult: ...


class EvaluationDatasetSeedServicePort(Protocol):
    async def seed_canonical_datasets(
        self,
        request: EvaluationDatasetSeedRequest,
    ) -> EvaluationDatasetSeedResult: ...


class EvaluationResultContextFactory(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[EvaluationResultServicePort]: ...


class EvaluationRunContextFactory(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[EvaluationRunServicePort]: ...


class EvaluationDatasetSeedContextFactory(Protocol):
    def __call__(
        self,
    ) -> AbstractAsyncContextManager[EvaluationDatasetSeedServicePort]: ...


@dataclass(frozen=True, slots=True)
class EvaluationStatusCommandResult:
    enabled: bool
    configured: bool
    strict_mode: bool
    judge_provider: str | None
    judge_model: str | None
    default_threshold: float
    max_concurrency: int
    timeout_seconds: float
    canonical_dataset_count: int
    message: str


@dataclass(frozen=True, slots=True)
class EvaluationDatasetListItem:
    name: str
    dataset_id: str
    version: str
    target_type: str
    description: str
    active: bool
    persisted: bool
    persisted_case_count: int | None = None


@dataclass(frozen=True, slots=True)
class EvaluationDatasetsCommandResult:
    success: bool
    items: tuple[EvaluationDatasetListItem, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationDatasetSeedCommandResult:
    success: bool
    seed_result: EvaluationDatasetSeedResult | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationRunCommandResult:
    success: bool
    message: str
    run_result: EvaluationRunServiceResult | None = None
    error: str | None = None

    @property
    def run_id(self) -> str | None:
        if self.run_result is None:
            return None
        return self.run_result.run.run_id

    @property
    def run_status(self) -> str | None:
        if self.run_result is None:
            return None
        return self.run_result.run.status.value


@dataclass(frozen=True, slots=True)
class EvaluationResultsCommandResult:
    success: bool
    bundle: EvaluationResultBundle | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationCommandService:
    """CLI-facing facade for canonical Polaris LLM-evaluation services."""

    result_service: EvaluationResultServicePort | None = None
    run_service: EvaluationRunServicePort | None = None
    dataset_seed_service: EvaluationDatasetSeedServicePort | None = None
    result_context_factory: EvaluationResultContextFactory | None = None
    run_context_factory: EvaluationRunContextFactory | None = None
    dataset_seed_context_factory: EvaluationDatasetSeedContextFactory | None = None
    settings: Settings | None = None

    async def status(self) -> EvaluationStatusCommandResult:
        settings = self._settings()
        configured = _is_configured(settings)
        return EvaluationStatusCommandResult(
            enabled=settings.DEEPEVAL_ENABLED,
            configured=configured,
            strict_mode=settings.DEEPEVAL_STRICT_MODE,
            judge_provider=settings.DEEPEVAL_JUDGE_PROVIDER,
            judge_model=settings.DEEPEVAL_JUDGE_MODEL,
            default_threshold=settings.DEEPEVAL_DEFAULT_THRESHOLD,
            max_concurrency=settings.DEEPEVAL_MAX_CONCURRENCY,
            timeout_seconds=settings.DEEPEVAL_TIMEOUT_SECONDS,
            canonical_dataset_count=len(canonical_evaluation_dataset_definitions()),
            message=(
                "DeepEval evaluation is configured."
                if configured
                else "DeepEval evaluation is not fully configured."
            ),
        )

    async def list_datasets(self) -> EvaluationDatasetsCommandResult:
        try:
            async with self._result_service_context() as result_service:
                items: list[EvaluationDatasetListItem] = []
                for definition in canonical_evaluation_dataset_definitions():
                    persisted = await result_service.get_dataset(
                        definition.reference.dataset_id
                    )
                    case_count = len(
                        await result_service.list_dataset_cases(
                            definition.reference.dataset_id
                        )
                    )
                    items.append(
                        EvaluationDatasetListItem(
                            name=definition.reference.name,
                            dataset_id=definition.reference.dataset_id,
                            version=definition.reference.version,
                            target_type=definition.target_type.value,
                            description=definition.description,
                            active=definition.active
                            if persisted is None
                            else persisted.active,
                            persisted=persisted is not None,
                            persisted_case_count=case_count,
                        )
                    )
        except Exception as exc:
            logger.debug("Evaluation dataset listing failed.", exc_info=True)
            return EvaluationDatasetsCommandResult(success=False, error=str(exc))
        return EvaluationDatasetsCommandResult(success=True, items=tuple(items))

    async def seed_datasets(
        self,
        dataset_name: str | None = None,
        *,
        dry_run: bool = False,
    ) -> EvaluationDatasetSeedCommandResult:
        try:
            request = EvaluationDatasetSeedRequest(
                dataset_name=dataset_name,
                dry_run=dry_run,
            )
            async with self._dataset_seed_service_context() as seed_service:
                result = await seed_service.seed_canonical_datasets(request)
        except Exception as exc:
            logger.debug("Evaluation dataset seed failed.", exc_info=True)
            return EvaluationDatasetSeedCommandResult(success=False, error=str(exc))
        return EvaluationDatasetSeedCommandResult(success=True, seed_result=result)

    async def run_dataset(self, dataset_name: str) -> EvaluationRunCommandResult:
        try:
            definition = canonical_evaluation_dataset_definition_by_name(dataset_name)
        except (KeyError, ValueError) as exc:
            return EvaluationRunCommandResult(
                success=False,
                message="Evaluation dataset was not found.",
                error=str(exc),
            )
        settings_error = self._validate_run_configuration()
        if settings_error is not None:
            return settings_error
        async with self._result_service_context() as result_service:
            cases = tuple(
                await result_service.list_dataset_cases(definition.reference.dataset_id)
            )
        if not cases:
            return EvaluationRunCommandResult(
                success=False,
                message="Evaluation dataset has no persisted cases.",
                error=f"No cases found for dataset {definition.reference.dataset_id}.",
            )
        return await self._run_cases(
            target_type=definition.target_type,
            cases=cases,
            dataset=definition.reference,
        )

    async def run_rag_case(self, case_id: str) -> EvaluationRunCommandResult:
        settings_error = self._validate_run_configuration()
        if settings_error is not None:
            return settings_error
        async with self._result_service_context() as result_service:
            case = await result_service.get_case(case_id)
        if case is None:
            return EvaluationRunCommandResult(
                success=False,
                message="Evaluation case was not found.",
                error=f"No evaluation case found for {case_id}.",
            )
        target_type = _coerce_target_type(case.target_type)
        if target_type not in _RAG_TARGET_TYPES:
            return EvaluationRunCommandResult(
                success=False,
                message="Evaluation case is not a RAG case.",
                error=f"Case {case_id} has target type {target_type.value}.",
            )
        return await self._run_cases(
            target_type=target_type,
            cases=(case,),
            dataset=_dataset_reference_for_case(case),
        )

    async def run_latest_rag(self) -> EvaluationRunCommandResult:
        settings_error = self._validate_run_configuration()
        if settings_error is not None:
            return settings_error
        cases: list[EvaluationCaseRecord] = []
        async with self._result_service_context() as result_service:
            for target_type in _RAG_TARGET_TYPES:
                cases.extend(
                    await result_service.list_latest_cases(target_type, limit=1)
                )
        if not cases:
            return EvaluationRunCommandResult(
                success=False,
                message="No persisted RAG evaluation cases are available.",
                error="No RAG cases found.",
            )
        latest_case = max(cases, key=_case_created_at)
        return await self._run_cases(
            target_type=_coerce_target_type(latest_case.target_type),
            cases=(latest_case,),
            dataset=_dataset_reference_for_case(latest_case),
        )

    async def results(self, run_id: str) -> EvaluationResultsCommandResult:
        try:
            async with self._result_service_context() as result_service:
                bundle = await result_service.get_run_results(run_id)
        except Exception as exc:
            logger.debug("Evaluation result lookup failed.", exc_info=True)
            return EvaluationResultsCommandResult(success=False, error=str(exc))
        if bundle is None:
            return EvaluationResultsCommandResult(
                success=False,
                error=f"No evaluation run found for {run_id}.",
            )
        return EvaluationResultsCommandResult(success=True, bundle=bundle)

    async def _run_cases(
        self,
        *,
        target_type: EvaluationTargetType,
        cases: Sequence[EvaluationCaseRecord],
        dataset: EvaluationDatasetReference | None,
    ) -> EvaluationRunCommandResult:
        settings = self._settings()
        metrics = _metric_specs_for_target(target_type)
        if not metrics:
            return EvaluationRunCommandResult(
                success=False,
                message="No evaluation metrics are defined for this target type.",
                error=f"No metrics found for target type {target_type.value}.",
            )
        request = EvaluationRunServiceRequest(
            run_id=_new_evaluation_run_id(),
            target_type=target_type,
            cases=tuple(_case_record_to_domain(case, dataset) for case in cases),
            metrics=metrics,
            evaluator_provider=settings.DEEPEVAL_JUDGE_PROVIDER or "",
            evaluator_model=settings.DEEPEVAL_JUDGE_MODEL or "",
            dataset=dataset,
            timeout_seconds=settings.DEEPEVAL_TIMEOUT_SECONDS,
        )
        try:
            async with self._run_service_context() as run_service:
                result = await run_service.run_evaluation(request)
        except Exception as exc:
            logger.debug("Evaluation run failed.", exc_info=True)
            return EvaluationRunCommandResult(
                success=False,
                message="Evaluation run failed.",
                error=str(exc),
            )
        return EvaluationRunCommandResult(
            success=True,
            message="Evaluation run completed.",
            run_result=result,
        )

    def _validate_run_configuration(self) -> EvaluationRunCommandResult | None:
        try:
            self._settings().validate_deepeval_evaluation(require_configured=True)
        except ValueError as exc:
            return EvaluationRunCommandResult(
                success=False,
                message="DeepEval evaluation is not configured.",
                error=str(exc),
            )
        return None

    def _settings(self) -> Settings:
        return self.settings or Settings()

    @asynccontextmanager
    async def _result_service_context(
        self,
    ) -> AsyncIterator[EvaluationResultServicePort]:
        if self.result_service is not None:
            yield self.result_service
            return
        if self.result_context_factory is not None:
            async with self.result_context_factory() as service:
                yield service
            return
        async with default_evaluation_result_context() as service:
            yield service

    @asynccontextmanager
    async def _run_service_context(self) -> AsyncIterator[EvaluationRunServicePort]:
        if self.run_service is not None:
            yield self.run_service
            return
        if self.run_context_factory is not None:
            async with self.run_context_factory() as service:
                yield service
            return
        async with default_evaluation_run_context() as service:
            yield service

    @asynccontextmanager
    async def _dataset_seed_service_context(
        self,
    ) -> AsyncIterator[EvaluationDatasetSeedServicePort]:
        if self.dataset_seed_service is not None:
            yield self.dataset_seed_service
            return
        if self.dataset_seed_context_factory is not None:
            async with self.dataset_seed_context_factory() as service:
                yield service
            return
        async with default_evaluation_dataset_seed_context() as service:
            yield service


@asynccontextmanager
async def default_evaluation_result_context() -> AsyncIterator[
    EvaluationResultServicePort
]:
    from application.evaluations import EvaluationResultService

    async with _default_evaluation_dependency_context(
        EvaluationResultService
    ) as service:
        yield service


@asynccontextmanager
async def default_evaluation_run_context() -> AsyncIterator[EvaluationRunServicePort]:
    from application.evaluations import EvaluationRunService

    async with _default_evaluation_dependency_context(EvaluationRunService) as service:
        yield service


@asynccontextmanager
async def default_evaluation_dataset_seed_context() -> AsyncIterator[
    EvaluationDatasetSeedServicePort
]:
    from application.evaluations import EvaluationDatasetService

    async with _default_evaluation_dependency_context(
        EvaluationDatasetService
    ) as service:
        yield service


@asynccontextmanager
async def _default_evaluation_dependency_context[DependencyT](
    dependency_type: type[DependencyT],
) -> AsyncIterator[DependencyT]:
    async with application_request_scope() as request_container:
        yield await request_container.get(dependency_type)


def render_evaluation_status(result: EvaluationStatusCommandResult) -> str:
    return "\n".join(
        (
            "Polaris Evaluation Status",
            f"Enabled: {result.enabled}",
            f"Configured: {result.configured}",
            f"Strict mode: {result.strict_mode}",
            f"Judge provider: {result.judge_provider or '<unconfigured>'}",
            f"Judge model: {result.judge_model or '<unconfigured>'}",
            f"Default threshold: {result.default_threshold}",
            f"Max concurrency: {result.max_concurrency}",
            f"Timeout seconds: {result.timeout_seconds}",
            f"Canonical datasets: {result.canonical_dataset_count}",
            f"Message: {result.message}",
        )
    )


def render_evaluation_datasets(result: EvaluationDatasetsCommandResult) -> str:
    if not result.success:
        return "\n".join(
            ("Evaluation Datasets", "Status: failed", f"Error: {result.error}")
        )
    lines = ["Evaluation Datasets", "Status: succeeded", f"Count: {len(result.items)}"]
    for item in result.items:
        lines.extend(
            (
                "",
                f"- {item.name} ({item.dataset_id})",
                f"  Target: {item.target_type}",
                f"  Version: {item.version}",
                f"  Persisted: {_yes_no(item.persisted)}",
                f"  Active: {_yes_no(item.active)}",
                f"  Cases: {item.persisted_case_count}",
                f"  Description: {item.description}",
            )
        )
    return "\n".join(lines)


def render_evaluation_dataset_seed_result(
    result: EvaluationDatasetSeedCommandResult,
) -> str:
    if not result.success or result.seed_result is None:
        return "\n".join(
            ("Evaluation Dataset Seed", "Status: failed", f"Error: {result.error}")
        )
    seed_result = result.seed_result
    lines = [
        "Evaluation Dataset Seed",
        "Status: succeeded",
        f"Dry run: {_yes_no(seed_result.dry_run)}",
        f"Datasets: {seed_result.dataset_count}",
        f"Cases: {seed_result.case_count}",
        f"Datasets written: {seed_result.datasets_written}",
        f"Cases written: {seed_result.cases_written}",
    ]
    for item in seed_result.items:
        lines.extend(
            (
                "",
                f"- {item.name} ({item.dataset_id})",
                f"  Fixture: {item.fixture_uri}",
                f"  Cases: {item.case_count}",
                f"  Persisted: {_yes_no(item.persisted)}",
            )
        )
    return "\n".join(lines)


def render_evaluation_run_result(result: EvaluationRunCommandResult) -> str:
    lines = [
        "Evaluation Run",
        f"Status: {'succeeded' if result.success else 'failed'}",
        f"Message: {result.message}",
    ]
    if result.run_result is not None:
        lines.extend(
            (
                f"Run ID: {result.run_result.run.run_id}",
                f"Run status: {result.run_result.run.status.value}",
                f"Target type: {result.run_result.run.target_type.value}",
                f"Metric results: {result.run_result.metric_result_count}",
                "Langfuse projection attempted: "
                f"{result.run_result.langfuse_projection_attempted}",
            )
        )
    if result.error is not None:
        lines.append(f"Error: {result.error}")
    return "\n".join(lines)


def render_evaluation_results(result: EvaluationResultsCommandResult) -> str:
    if not result.success or result.bundle is None:
        return "\n".join(
            ("Evaluation Results", "Status: failed", f"Error: {result.error}")
        )
    bundle = result.bundle
    lines = [
        "Evaluation Results",
        "Status: succeeded",
        f"Run ID: {bundle.run.run_id}",
        f"Run status: {_status_value(bundle.run.status)}",
        f"Target type: {_target_type_value(bundle.run.target_type)}",
        f"Dataset ID: {bundle.run.dataset_id or '<none>'}",
        f"Metric results: {bundle.metric_result_count}",
        f"Artifacts: {len(bundle.artifacts)}",
    ]
    if bundle.metric_results:
        lines.append("")
        lines.append("Metrics:")
    for metric_result in bundle.metric_results:
        lines.append(
            "- "
            f"{metric_result.case_id} {metric_result.metric_name}: "
            f"score={metric_result.score} "
            f"threshold={metric_result.threshold} "
            f"passed={metric_result.passed} "
            f"status={_status_value(metric_result.status)}"
        )
        if metric_result.reason:
            lines.append(f"  Reason: {metric_result.reason}")
        if metric_result.error_message:
            lines.append(f"  Error: {metric_result.error_message}")
    return "\n".join(lines)


def _metric_specs_for_target(
    target_type: EvaluationTargetType,
) -> tuple[EvaluationMetricSpec, ...]:
    if target_type in _RAG_TARGET_TYPES:
        return rag_evaluation_metric_specs()
    return intelligence_evaluation_metric_specs(target_type)


def _case_record_to_domain(
    record: EvaluationCaseRecord,
    dataset: EvaluationDatasetReference | None,
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


def _dataset_reference_for_case(
    case: EvaluationCaseRecord,
) -> EvaluationDatasetReference | None:
    if case.dataset_id is None:
        return None
    for definition in canonical_evaluation_dataset_definitions():
        if definition.reference.dataset_id == case.dataset_id:
            return definition.reference
    return None


def _coerce_target_type(value: EvaluationTargetType | str) -> EvaluationTargetType:
    if isinstance(value, EvaluationTargetType):
        return value
    return EvaluationTargetType(value)


def _case_created_at(case: EvaluationCaseRecord) -> datetime:
    return case.created_at or datetime.min.replace(tzinfo=UTC)


def _is_configured(settings: Settings) -> bool:
    return bool(
        settings.DEEPEVAL_ENABLED
        and settings.DEEPEVAL_JUDGE_PROVIDER
        and settings.DEEPEVAL_JUDGE_MODEL
    )


def _new_evaluation_run_id() -> str:
    return f"eval_{uuid4().hex}"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _target_type_value(value: EvaluationTargetType | str) -> str:
    return value.value if isinstance(value, EvaluationTargetType) else value


def _status_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)
