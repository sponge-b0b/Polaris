from __future__ import annotations

from dishka import Provider, Scope, provide

from application.observability.ai_observability_contracts import (
    AiObservabilityCapturePolicy,
    AiRedactionMode,
)
from application.observability.ai_observability_export_service import (
    AiObservabilityExportQueueService,
    AiObservabilityExportWorker,
    AiObservabilityRetentionService,
    DurableLangfuseAiObservabilitySink,
)
from application.observability.ai_observability_operational_status import (
    AiObservabilityOperationalStatusService,
)
from application.observability.ai_prompt_management import AiPromptGovernancePolicy
from application.observability.langfuse_projection import (
    AiObservabilityProjector,
    LangfuseObservationMapper,
)
from application.observability.langfuse_sdk_exporter import LangfuseSdkExportClient
from config.settings import Settings
from core.storage.persistence.ai_observability import AiObservabilityExportJobRepository
from core.telemetry.observability.observability_manager import ObservabilityManager


class ApplicationObservabilityDIProvider(Provider):
    """Request-scoped composition for AI observability projections."""

    scope = Scope.REQUEST

    @provide
    def provide_ai_observability_capture_policy(
        self,
        settings: Settings,
    ) -> AiObservabilityCapturePolicy:
        return AiObservabilityCapturePolicy(
            capture_prompts=settings.LANGFUSE_CAPTURE_PROMPTS,
            capture_responses=settings.LANGFUSE_CAPTURE_RESPONSES,
            capture_contexts=settings.LANGFUSE_CAPTURE_CONTEXTS,
            capture_user_input=settings.LANGFUSE_CAPTURE_USER_INPUT,
            redaction_mode=AiRedactionMode(settings.LANGFUSE_REDACTION_MODE),
            max_payload_characters=settings.LANGFUSE_MAX_PAYLOAD_CHARACTERS,
            max_metadata_value_characters=(
                settings.LANGFUSE_MAX_METADATA_VALUE_CHARACTERS
            ),
            retention_days=settings.LANGFUSE_RETENTION_DAYS,
        )

    @provide
    def provide_ai_prompt_governance_policy(
        self,
        settings: Settings,
    ) -> AiPromptGovernancePolicy:
        return AiPromptGovernancePolicy(environment=settings.LANGFUSE_ENVIRONMENT)

    @provide
    def provide_langfuse_observation_mapper(
        self,
        capture_policy: AiObservabilityCapturePolicy,
        prompt_governance_policy: AiPromptGovernancePolicy,
        settings: Settings,
    ) -> LangfuseObservationMapper:
        return LangfuseObservationMapper(
            capture_policy=capture_policy,
            environment=settings.LANGFUSE_ENVIRONMENT,
            release=settings.LANGFUSE_RELEASE,
            prompt_governance_policy=prompt_governance_policy,
        )

    @provide
    def provide_ai_observability_export_queue_service(
        self,
        repository: AiObservabilityExportJobRepository,
        mapper: LangfuseObservationMapper,
        observability_manager: ObservabilityManager,
    ) -> AiObservabilityExportQueueService:
        return AiObservabilityExportQueueService(
            repository=repository,
            mapper=mapper,
            observability_manager=observability_manager,
        )

    @provide
    def provide_ai_observability_projector(
        self,
        queue_service: AiObservabilityExportQueueService,
    ) -> AiObservabilityProjector:
        return AiObservabilityProjector(
            DurableLangfuseAiObservabilitySink(queue_service)
        )

    @provide
    def provide_langfuse_sdk_export_client(
        self,
        settings: Settings,
    ) -> LangfuseSdkExportClient:
        return LangfuseSdkExportClient.from_settings(settings)

    @provide
    def provide_ai_observability_export_worker(
        self,
        repository: AiObservabilityExportJobRepository,
        client: LangfuseSdkExportClient,
        observability_manager: ObservabilityManager,
    ) -> AiObservabilityExportWorker:
        return AiObservabilityExportWorker(
            repository=repository,
            client=client,
            observability_manager=observability_manager,
        )

    @provide
    def provide_ai_observability_operational_status_service(
        self,
        repository: AiObservabilityExportJobRepository,
        settings: Settings,
        observability_manager: ObservabilityManager,
    ) -> AiObservabilityOperationalStatusService:
        return AiObservabilityOperationalStatusService(
            repository=repository,
            settings=settings,
            observability_manager=observability_manager,
        )

    @provide
    def provide_ai_observability_retention_service(
        self,
        repository: AiObservabilityExportJobRepository,
        settings: Settings,
        observability_manager: ObservabilityManager,
    ) -> AiObservabilityRetentionService:
        return AiObservabilityRetentionService(
            repository=repository,
            retention_days=settings.LANGFUSE_RETENTION_DAYS,
            observability_manager=observability_manager,
        )
