from __future__ import annotations

from dishka import Provider
from dishka import Scope
from dishka import provide

from application.evaluations.evaluation_dataset_service import EvaluationDatasetService
from application.evaluations.evaluation_jobs import EvaluationJobProcessor
from application.evaluations.evaluation_langfuse_projection_service import (
    EvaluationLangfuseProjectionService,
)
from application.evaluations.evaluation_result_service import EvaluationResultService
from application.evaluations.evaluation_telemetry import EvaluationTelemetry
from application.evaluations.evaluation_run_service import EvaluationRunService
from application.observability.langfuse_projection import AiObservabilityProjector
from config.settings import Settings
from core.storage.persistence.evaluation import EvaluationPersistenceRepository
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability import ObservabilityManager
from integration.providers.llm_evaluation import DeepEvalEvaluationProvider
from integration.providers.llm_evaluation import EvaluationProvider


class ApplicationEvaluationsDIProvider(Provider):
    """Request-scoped composition for canonical LLM evaluation workflows."""

    scope = Scope.REQUEST

    @provide
    def provide_evaluation_dataset_service(
        self,
        repository: EvaluationPersistenceRepository,
    ) -> EvaluationDatasetService:
        return EvaluationDatasetService(repository)

    @provide
    def provide_evaluation_result_service(
        self,
        repository: EvaluationPersistenceRepository,
    ) -> EvaluationResultService:
        return EvaluationResultService(repository)

    @provide
    def provide_evaluation_langfuse_projection_service(
        self,
        projector: AiObservabilityProjector,
    ) -> EvaluationLangfuseProjectionService:
        return EvaluationLangfuseProjectionService(projector)

    @provide
    def provide_evaluation_telemetry(
        self,
        observability_manager: ObservabilityManager,
    ) -> EvaluationTelemetry:
        return EvaluationTelemetry(observability_manager)

    @provide
    def provide_evaluation_provider(
        self,
        settings: Settings,
        integration_telemetry: IntegrationTelemetry,
    ) -> EvaluationProvider:
        settings.validate_deepeval_evaluation(require_configured=True)
        return DeepEvalEvaluationProvider(
            judge_provider=settings.DEEPEVAL_JUDGE_PROVIDER or "",
            judge_model=settings.DEEPEVAL_JUDGE_MODEL or "",
            default_threshold=settings.DEEPEVAL_DEFAULT_THRESHOLD,
            max_concurrency=settings.DEEPEVAL_MAX_CONCURRENCY,
            timeout_seconds=settings.DEEPEVAL_TIMEOUT_SECONDS,
            telemetry_opt_out=settings.DEEPEVAL_TELEMETRY_OPT_OUT,
            telemetry=integration_telemetry,
        )

    @provide
    def provide_evaluation_run_service(
        self,
        provider: EvaluationProvider,
        repository: EvaluationPersistenceRepository,
        projection_service: EvaluationLangfuseProjectionService,
        telemetry: EvaluationTelemetry,
    ) -> EvaluationRunService:
        return EvaluationRunService(provider, repository, projection_service, telemetry)

    @provide
    def provide_evaluation_job_processor(
        self,
        run_service: EvaluationRunService,
        result_service: EvaluationResultService,
        projection_service: EvaluationLangfuseProjectionService,
        telemetry: EvaluationTelemetry,
    ) -> EvaluationJobProcessor:
        return EvaluationJobProcessor(
            run_service=run_service,
            result_service=result_service,
            projection_service=projection_service,
            telemetry=telemetry,
        )
