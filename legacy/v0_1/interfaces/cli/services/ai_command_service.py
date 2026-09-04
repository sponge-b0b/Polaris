from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol, TypeVar, cast
from uuid import uuid4

from application.ai_optimization import (
    AiOptimizationRequest,
    AiOptimizationResult,
    AiOptimizationTarget,
    coerce_ai_optimization_target,
    evaluation_target_type_for_optimization,
)
from application.evaluations import (
    EvaluationRunService,
    canonical_evaluation_dataset_definition_by_name,
    intelligence_evaluation_metric_specs,
    rag_evaluation_metric_specs,
)
from config.settings import Settings
from core.bootstrap.di_providers import application_request_scope
from core.storage.persistence.ai_artifacts import (
    AiArtifactApprovalStatus,
    AiArtifactPersistenceRepository,
    AiArtifactType,
    AiPromptProgramArtifactRecord,
    approval_status_value,
    artifact_type_value,
)
from core.storage.persistence.evaluation import EvaluationPersistenceRepository
from domain.evaluation import EvaluationTargetType
from integration.providers.ai_optimization import DspyOptimizationProvider
from integration.providers.llm_evaluation import EvaluationMetricSpec

logger = logging.getLogger(__name__)

DependencyT = TypeVar("DependencyT")
_RAG_EVALUATION_TARGET_TYPES = frozenset(
    {
        EvaluationTargetType.RAG_ANSWER,
        EvaluationTargetType.RAG_RETRIEVAL,
        EvaluationTargetType.RAG_GENERATION,
    }
)


class AiOptimizationServicePort(Protocol):
    async def optimize(
        self,
        request: AiOptimizationRequest,
    ) -> AiOptimizationResult: ...


class AiArtifactRepositoryPort(Protocol):
    async def upsert_artifact(
        self,
        record: AiPromptProgramArtifactRecord,
    ) -> AiPromptProgramArtifactRecord: ...

    async def get_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None: ...

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: AiArtifactType | str | None = None,
        active: bool | None = None,
        limit: int | None = None,
    ) -> Sequence[AiPromptProgramArtifactRecord]: ...

    async def get_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> AiPromptProgramArtifactRecord | None: ...

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str,
        approved_at: datetime,
    ) -> AiPromptProgramArtifactRecord | None: ...

    async def deactivate_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None: ...


class AiOptimizationContextFactory(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[AiOptimizationServicePort]: ...


class AiArtifactContextFactory(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[AiArtifactRepositoryPort]: ...


@dataclass(frozen=True, slots=True)
class AiOptimizeCommandResult:
    success: bool
    message: str
    optimization_result: AiOptimizationResult | None = None
    error: str | None = None

    @property
    def artifact_id(self) -> str | None:
        if (
            self.optimization_result is None
            or self.optimization_result.artifact is None
        ):
            return None
        return self.optimization_result.artifact.artifact_id

    @property
    def evaluation_run_id(self) -> str | None:
        if self.optimization_result is None:
            return None
        return self.optimization_result.evaluation_result.run.run_id


@dataclass(frozen=True, slots=True)
class AiArtifactListCommandResult:
    success: bool
    artifacts: tuple[AiPromptProgramArtifactRecord, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AiArtifactCommandResult:
    success: bool
    message: str
    artifact: AiPromptProgramArtifactRecord | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AiCommandService:
    """CLI-facing facade for AI optimization and prompt/program artifacts."""

    optimization_service: AiOptimizationServicePort | None = None
    artifact_repository: AiArtifactRepositoryPort | None = None
    optimization_context_factory: AiOptimizationContextFactory | None = None
    artifact_context_factory: AiArtifactContextFactory | None = None
    settings: Settings | None = None

    async def optimize(
        self,
        *,
        target: str,
        dataset: str,
        model: str | None = None,
        prompt_name: str | None = None,
        prompt_version: str = "v1",
        artifact_name: str | None = None,
        artifact_version: str = "v1",
        max_cases: int | None = None,
        timeout_seconds: float | None = None,
    ) -> AiOptimizeCommandResult:
        try:
            settings = self._settings()
            settings.validate_deepeval_evaluation(require_configured=True)
            optimization_target = coerce_ai_optimization_target(target)
            dataset_id = _resolve_dataset_id(dataset)
            metrics = _metric_specs_for_optimization_target(optimization_target)
            request = AiOptimizationRequest(
                optimization_id=f"ai_opt_{uuid4().hex}",
                target=optimization_target,
                dataset_id=dataset_id,
                metrics=metrics,
                evaluator_provider=settings.DEEPEVAL_JUDGE_PROVIDER or "",
                evaluator_model=settings.DEEPEVAL_JUDGE_MODEL or "",
                model_name=model or settings.DSPY_OPTIMIZATION_MODEL,
                prompt_name=prompt_name or optimization_target.value,
                prompt_version=prompt_version,
                artifact_name=artifact_name or f"{optimization_target.value}_dspy",
                artifact_version=artifact_version,
                max_trainset_cases=max_cases or settings.DSPY_MAX_TRAINSET_CASES,
                timeout_seconds=timeout_seconds or settings.DEEPEVAL_TIMEOUT_SECONDS,
            )
            async with self._optimization_service_context() as service:
                result = await service.optimize(request)
        except Exception as exc:
            logger.debug("AI optimization command failed.", exc_info=True)
            return AiOptimizeCommandResult(
                success=False,
                message="AI optimization failed.",
                error=str(exc),
            )
        return AiOptimizeCommandResult(
            success=True,
            message="AI optimization completed.",
            optimization_result=result,
        )

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: str | None = None,
        active: bool | None = None,
        limit: int | None = 20,
    ) -> AiArtifactListCommandResult:
        try:
            async with self._artifact_repository_context() as repository:
                artifacts = tuple(
                    await repository.list_artifacts(
                        target_component=target_component,
                        artifact_type=artifact_type,
                        active=active,
                        limit=limit,
                    )
                )
        except Exception as exc:
            logger.debug("AI artifact listing failed.", exc_info=True)
            return AiArtifactListCommandResult(success=False, error=str(exc))
        return AiArtifactListCommandResult(success=True, artifacts=artifacts)

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str = "cli",
    ) -> AiArtifactCommandResult:
        try:
            async with self._artifact_repository_context() as repository:
                artifact = await repository.approve_artifact(
                    artifact_id,
                    approved_by=approved_by,
                    approved_at=datetime.now(UTC),
                )
        except Exception as exc:
            logger.debug("AI artifact approval failed.", exc_info=True)
            return AiArtifactCommandResult(
                success=False,
                message="AI artifact approval failed.",
                error=str(exc),
            )
        if artifact is None:
            return AiArtifactCommandResult(
                success=False,
                message="AI artifact was not found.",
                error=f"No AI artifact found for {artifact_id}.",
            )
        return AiArtifactCommandResult(
            success=True,
            message="AI artifact approved. Activate it explicitly before runtime use.",
            artifact=artifact,
        )

    async def activate_artifact(self, artifact_id: str) -> AiArtifactCommandResult:
        try:
            async with self._artifact_repository_context() as repository:
                artifact = await repository.get_artifact(artifact_id)
                if artifact is None:
                    return AiArtifactCommandResult(
                        success=False,
                        message="AI artifact was not found.",
                        error=f"No AI artifact found for {artifact_id}.",
                    )
                if artifact.approval_status is not AiArtifactApprovalStatus.APPROVED:
                    return AiArtifactCommandResult(
                        success=False,
                        message="AI artifact activation was denied.",
                        error="Only approved AI artifacts can be activated.",
                        artifact=artifact,
                    )
                current_active = await repository.get_active_artifact(
                    artifact.target_component,
                    artifact_type=artifact.artifact_type,
                )
                if (
                    current_active is not None
                    and current_active.artifact_id != artifact_id
                ):
                    await repository.deactivate_artifact(current_active.artifact_id)
                activated = await repository.upsert_artifact(
                    replace(artifact, active=True)
                )
        except Exception as exc:
            logger.debug("AI artifact activation failed.", exc_info=True)
            return AiArtifactCommandResult(
                success=False,
                message="AI artifact activation failed.",
                error=str(exc),
            )
        return AiArtifactCommandResult(
            success=True,
            message="AI artifact activated.",
            artifact=activated,
        )

    async def deactivate_artifact(self, artifact_id: str) -> AiArtifactCommandResult:
        try:
            async with self._artifact_repository_context() as repository:
                artifact = await repository.deactivate_artifact(artifact_id)
        except Exception as exc:
            logger.debug("AI artifact deactivation failed.", exc_info=True)
            return AiArtifactCommandResult(
                success=False,
                message="AI artifact deactivation failed.",
                error=str(exc),
            )
        if artifact is None:
            return AiArtifactCommandResult(
                success=False,
                message="AI artifact was not found.",
                error=f"No AI artifact found for {artifact_id}.",
            )
        return AiArtifactCommandResult(
            success=True,
            message="AI artifact deactivated.",
            artifact=artifact,
        )

    def _settings(self) -> Settings:
        return self.settings or Settings()

    @asynccontextmanager
    async def _optimization_service_context(
        self,
    ) -> AsyncIterator[AiOptimizationServicePort]:
        if self.optimization_service is not None:
            yield self.optimization_service
            return
        if self.optimization_context_factory is not None:
            async with self.optimization_context_factory() as service:
                yield service
            return
        async with default_ai_optimization_context() as service:
            yield service

    @asynccontextmanager
    async def _artifact_repository_context(
        self,
    ) -> AsyncIterator[AiArtifactRepositoryPort]:
        if self.artifact_repository is not None:
            yield self.artifact_repository
            return
        if self.artifact_context_factory is not None:
            async with self.artifact_context_factory() as repository:
                yield repository
            return
        async with default_ai_artifact_repository_context() as repository:
            yield repository


@asynccontextmanager
async def default_ai_optimization_context() -> AsyncIterator[AiOptimizationServicePort]:
    from application.ai_optimization import AiOptimizationService

    async with application_request_scope() as request_container:
        evaluation_repository = await request_container.get(
            EvaluationPersistenceRepository
        )
        artifact_repository = await request_container.get(
            cast(type[AiArtifactRepositoryPort], AiArtifactPersistenceRepository)
        )
        evaluation_runner = await request_container.get(EvaluationRunService)
        settings = await request_container.get(Settings)
        yield AiOptimizationService(
            evaluation_repository=evaluation_repository,
            artifact_repository=artifact_repository,
            optimization_provider=DspyOptimizationProvider(
                gateway_base_url=settings.LITELLM_BASE_URL,
                gateway_api_key=settings.LITELLM_API_KEY,
            ),
            evaluation_runner=evaluation_runner,
        )


@asynccontextmanager
async def default_ai_artifact_repository_context() -> AsyncIterator[
    AiArtifactRepositoryPort
]:
    async with _default_dependency_context(
        cast(type[AiArtifactRepositoryPort], AiArtifactPersistenceRepository)
    ) as repository:
        yield repository


@asynccontextmanager
async def _default_dependency_context[DependencyT](
    dependency_type: type[DependencyT],
) -> AsyncIterator[DependencyT]:
    async with application_request_scope() as request_container:
        yield await request_container.get(dependency_type)


def render_ai_optimize_result(result: AiOptimizeCommandResult) -> str:
    lines = [
        "AI Optimization",
        f"Status: {'succeeded' if result.success else 'failed'}",
        f"Message: {result.message}",
    ]
    if result.optimization_result is not None:
        optimization = result.optimization_result
        lines.extend(
            (
                f"Optimization ID: {optimization.optimization_id}",
                f"Target: {optimization.target.value}",
                f"Optimization status: {optimization.status.value}",
                f"Evaluation run ID: {optimization.evaluation_result.run.run_id}",
                f"Evaluation status: {optimization.evaluation_result.run.status.value}",
                f"Metric results: {optimization.evaluation_result.metric_result_count}",
                f"Artifact persisted: {_yes_no(optimization.artifact_persisted)}",
            )
        )
        if optimization.artifact is not None:
            lines.extend(_artifact_detail_lines(optimization.artifact))
    if result.error is not None:
        lines.append(f"Error: {result.error}")
    return "\n".join(lines)


def render_ai_artifacts(result: AiArtifactListCommandResult) -> str:
    if not result.success:
        return "\n".join(("AI Artifacts", "Status: failed", f"Error: {result.error}"))
    lines = ["AI Artifacts", "Status: succeeded", f"Count: {len(result.artifacts)}"]
    for artifact in result.artifacts:
        lines.extend(("", *_artifact_summary_lines(artifact)))
    return "\n".join(lines)


def render_ai_artifact_command_result(result: AiArtifactCommandResult) -> str:
    lines = [
        "AI Artifact",
        f"Status: {'succeeded' if result.success else 'failed'}",
        f"Message: {result.message}",
    ]
    if result.artifact is not None:
        lines.extend(_artifact_detail_lines(result.artifact))
    if result.error is not None:
        lines.append(f"Error: {result.error}")
    return "\n".join(lines)


def _artifact_summary_lines(artifact: AiPromptProgramArtifactRecord) -> tuple[str, ...]:
    return (
        f"- {artifact.artifact_id}",
        f"  Target: {artifact.target_component}",
        f"  Type: {artifact_type_value(artifact.artifact_type)}",
        f"  Name: {artifact.artifact_name}",
        f"  Version: {artifact.artifact_version}",
        f"  Status: {approval_status_value(artifact.approval_status)}",
        f"  Active: {_yes_no(artifact.active)}",
        f"  Model: {artifact.provider_name}/{artifact.model_name}",
        f"  Evaluation dataset: {artifact.evaluation_dataset_id or '<none>'}",
        f"  Evaluation run: {artifact.evaluation_run_id or '<none>'}",
    )


def _artifact_detail_lines(artifact: AiPromptProgramArtifactRecord) -> tuple[str, ...]:
    return (
        f"Artifact ID: {artifact.artifact_id}",
        f"Artifact type: {artifact_type_value(artifact.artifact_type)}",
        f"Artifact name: {artifact.artifact_name}",
        f"Artifact version: {artifact.artifact_version}",
        f"Target component: {artifact.target_component}",
        f"Model: {artifact.provider_name}/{artifact.model_name}",
        f"Prompt reference: {artifact.prompt_reference}",
        f"Prompt hash: {artifact.prompt_hash}",
        f"Approval status: {approval_status_value(artifact.approval_status)}",
        f"Approved by: {artifact.approved_by or '<none>'}",
        f"Active: {_yes_no(artifact.active)}",
        f"Evaluation dataset: {artifact.evaluation_dataset_id or '<none>'}",
        f"Evaluation run: {artifact.evaluation_run_id or '<none>'}",
        f"Langfuse trace: {artifact.langfuse_trace_id or '<none>'}",
    )


def _resolve_dataset_id(dataset: str) -> str:
    cleaned_dataset = dataset.strip()
    if not cleaned_dataset:
        raise ValueError("dataset cannot be empty.")
    for candidate in (cleaned_dataset, cleaned_dataset.replace("-", "_")):
        try:
            return canonical_evaluation_dataset_definition_by_name(
                candidate
            ).reference.dataset_id
        except KeyError:
            continue
    return cleaned_dataset


def _metric_specs_for_optimization_target(
    target: AiOptimizationTarget,
) -> tuple[EvaluationMetricSpec, ...]:
    evaluation_target = evaluation_target_type_for_optimization(target)
    if evaluation_target in _RAG_EVALUATION_TARGET_TYPES:
        return rag_evaluation_metric_specs()
    return intelligence_evaluation_metric_specs(evaluation_target)


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
