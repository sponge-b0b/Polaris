"""Application-layer services for canonical LLM evaluation workflows."""

from application.evaluations.contracts import (
    EvaluationCaseBuildRequest,
    EvaluationDatasetRegistrationRequest,
    EvaluationDatasetSeedItem,
    EvaluationDatasetSeedRequest,
    EvaluationDatasetSeedResult,
    EvaluationLangfuseProjectionRequest,
    EvaluationLangfuseProjectionResult,
    EvaluationResultBundle,
    EvaluationRunServiceRequest,
    EvaluationRunServiceResult,
)
from application.evaluations.di import ApplicationEvaluationsDIProvider
from application.evaluations.evaluation_case_builder import EvaluationCaseBuilder
from application.evaluations.evaluation_dataset_service import EvaluationDatasetService
from application.evaluations.evaluation_datasets import (
    CANONICAL_EVALUATION_DATASET_DEFINITIONS,
    CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS,
    EVALUATION_DATASET_VERSION,
    EvaluationDatasetDefinition,
    EvaluationDatasetSliceDefinition,
    EvaluationDatasetSliceMembership,
    canonical_evaluation_dataset_definition_by_name,
    canonical_evaluation_dataset_definitions,
    canonical_evaluation_dataset_registration_requests,
    canonical_evaluation_dataset_slice_definition_by_name,
    canonical_evaluation_dataset_slice_definitions,
)
from application.evaluations.evaluation_jobs import (
    EvaluationJobBatchResult,
    EvaluationJobProcessor,
    EvaluationJobRequest,
    EvaluationJobResult,
    EvaluationJobStatus,
    EvaluationJobType,
)
from application.evaluations.evaluation_langfuse_projection_service import (
    EvaluationLangfuseProjectionService,
)
from application.evaluations.evaluation_result_service import EvaluationResultService
from application.evaluations.evaluation_run_service import EvaluationRunService
from application.evaluations.evaluation_telemetry import EvaluationTelemetry
from application.evaluations.rag_evaluation_metrics import (
    INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS,
    INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION,
    RAG_BUILTIN_METRIC_DEFINITIONS,
    RAG_CUSTOM_METRIC_DEFINITIONS,
    RAG_EVALUATION_METRIC_DEFINITIONS,
    RAG_EVALUATION_THRESHOLD_PROFILE_VERSION,
    EvaluationMetricDefinition,
    EvaluationMetricEngine,
    intelligence_evaluation_metric_specs,
    intelligence_threshold_profile,
    rag_evaluation_metric_specs,
    rag_threshold_profile,
)

__all__ = [
    "ApplicationEvaluationsDIProvider",
    "EvaluationCaseBuildRequest",
    "EvaluationCaseBuilder",
    "EvaluationDatasetRegistrationRequest",
    "EvaluationDatasetSeedResult",
    "EvaluationDatasetSeedRequest",
    "EvaluationDatasetSeedItem",
    "EvaluationDatasetService",
    "canonical_evaluation_dataset_registration_requests",
    "canonical_evaluation_dataset_definitions",
    "canonical_evaluation_dataset_definition_by_name",
    "canonical_evaluation_dataset_slice_definitions",
    "canonical_evaluation_dataset_slice_definition_by_name",
    "EvaluationDatasetDefinition",
    "EvaluationDatasetSliceDefinition",
    "EvaluationDatasetSliceMembership",
    "EVALUATION_DATASET_VERSION",
    "CANONICAL_EVALUATION_DATASET_DEFINITIONS",
    "CANONICAL_EVALUATION_DATASET_SLICE_DEFINITIONS",
    "EvaluationJobBatchResult",
    "EvaluationJobProcessor",
    "EvaluationJobRequest",
    "EvaluationJobResult",
    "EvaluationJobStatus",
    "EvaluationJobType",
    "EvaluationLangfuseProjectionRequest",
    "EvaluationLangfuseProjectionResult",
    "EvaluationLangfuseProjectionService",
    "EvaluationResultBundle",
    "EvaluationResultService",
    "EvaluationTelemetry",
    "EvaluationRunService",
    "EvaluationRunServiceRequest",
    "EvaluationRunServiceResult",
    "EvaluationMetricDefinition",
    "EvaluationMetricEngine",
    "INTELLIGENCE_EVALUATION_METRIC_DEFINITIONS",
    "INTELLIGENCE_EVALUATION_THRESHOLD_PROFILE_VERSION",
    "intelligence_evaluation_metric_specs",
    "intelligence_threshold_profile",
    "RAG_BUILTIN_METRIC_DEFINITIONS",
    "RAG_CUSTOM_METRIC_DEFINITIONS",
    "RAG_EVALUATION_METRIC_DEFINITIONS",
    "RAG_EVALUATION_THRESHOLD_PROFILE_VERSION",
    "rag_evaluation_metric_specs",
    "rag_threshold_profile",
]
