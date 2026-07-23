from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType

AiMetadataValue = str | int | float | bool | None
AiMetadata = Mapping[str, AiMetadataValue]
_EMPTY_METADATA: AiMetadata = MappingProxyType({})


class AiObservationFamily(StrEnum):
    RAG = "rag"
    INTELLIGENCE = "intelligence"


class AiObservationType(StrEnum):
    RAG_QUERY = "rag.query"
    RAG_ROUTING = "rag.routing"
    RAG_RETRIEVAL_VECTOR = "rag.retrieval.vector"
    RAG_RETRIEVAL_GRAPH = "rag.retrieval.graph"
    RAG_RETRIEVAL_FUSION = "rag.retrieval.fusion"
    RAG_PARENT_EXPANSION = "rag.parent_expansion"
    RAG_RERANKING = "rag.reranking"
    RAG_CRAG = "rag.crag"
    RAG_SELF_RAG = "rag.self_rag"
    RAG_GENERATION = "rag.generation"
    RAG_SECURITY = "rag.security"
    RAG_ANSWER_QUALITY = "rag.answer_quality"
    INTELLIGENCE_AGENT_REASONING = "intelligence.agent_reasoning"
    INTELLIGENCE_STRATEGY_SYNTHESIS = "intelligence.strategy_synthesis"
    INTELLIGENCE_REPORT_GENERATION = "intelligence.report_generation"
    INTELLIGENCE_RECOMMENDATION_EXPLANATION = "intelligence.recommendation_explanation"

    @property
    def family(self) -> AiObservationFamily:
        if self.value.startswith("rag."):
            return AiObservationFamily.RAG
        if self.value.startswith("intelligence."):
            return AiObservationFamily.INTELLIGENCE
        raise ValueError(f"Unsupported AI observation type: {self.value}.")


class AiObservationStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    DEGRADED = "degraded"
    SKIPPED = "skipped"


class AiObservabilityExportStatus(StrEnum):
    EXPORTED = "exported"
    PENDING = "pending"
    FAILED = "failed"
    SKIPPED = "skipped"


class AiRedactionMode(StrEnum):
    STRICT = "strict"
    METADATA_ONLY = "metadata_only"
    PERMISSIVE = "permissive"


class AiScoreResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AiPromptVersionReference:
    prompt_name: str
    prompt_version: str
    prompt_hash: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.prompt_name, "prompt_name")
        _require_non_empty(self.prompt_version, "prompt_version")
        _validate_optional_non_empty(self.prompt_hash, "prompt_hash")
        _validate_optional_non_empty(self.source, "source")

    def key_parts(self) -> tuple[str, ...]:
        return _drop_none(
            (
                self.prompt_name,
                self.prompt_version,
                self.prompt_hash,
                self.source,
            )
        )


@dataclass(frozen=True, slots=True)
class AiObservabilityCorrelationIds:
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    observation_id: str | None = None
    parent_observation_id: str | None = None
    dataset_id: str | None = None
    case_id: str | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "trace_id",
            "span_id",
            "parent_span_id",
            "workflow_name",
            "execution_id",
            "runtime_id",
            "node_name",
            "observation_id",
            "parent_observation_id",
            "dataset_id",
            "case_id",
            "run_id",
        ):
            _validate_optional_non_empty(getattr(self, field_name), field_name)

    def key_parts(self) -> tuple[str, ...]:
        return _drop_none(
            (
                self.trace_id,
                self.span_id,
                self.workflow_name,
                self.execution_id,
                self.runtime_id,
                self.node_name,
                self.observation_id,
                self.parent_observation_id,
                self.dataset_id,
                self.case_id,
                self.run_id,
            )
        )


@dataclass(frozen=True, slots=True)
class AiObservabilityCapturePolicy:
    capture_prompts: bool = False
    capture_responses: bool = False
    capture_contexts: bool = False
    capture_user_input: bool = False
    redaction_mode: AiRedactionMode = AiRedactionMode.STRICT
    max_payload_characters: int = 8_000
    max_metadata_value_characters: int = 512
    retention_days: int = 90

    def __post_init__(self) -> None:
        if self.max_payload_characters <= 0:
            raise ValueError("max_payload_characters must be positive.")
        if self.max_metadata_value_characters <= 0:
            raise ValueError("max_metadata_value_characters must be positive.")
        if self.retention_days <= 0:
            raise ValueError("retention_days must be positive.")


@dataclass(frozen=True, slots=True)
class AiScoreProjection:
    metric_name: str
    score: float
    result: AiScoreResult = AiScoreResult.UNKNOWN
    threshold: float | None = None
    reason: str | None = None
    evaluator_model: str | None = None
    evaluator_provider: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.metric_name, "metric_name")
        _validate_score(self.score, "score")
        if self.threshold is not None:
            _validate_score(self.threshold, "threshold")
        _validate_optional_non_empty(self.reason, "reason")
        _validate_optional_non_empty(self.evaluator_model, "evaluator_model")
        _validate_optional_non_empty(self.evaluator_provider, "evaluator_provider")

    def key_parts(self) -> tuple[str, ...]:
        return _drop_none(
            (
                self.metric_name,
                str(self.score),
                self.result.value,
                None if self.threshold is None else str(self.threshold),
                self.reason,
                self.evaluator_model,
                self.evaluator_provider,
            )
        )


AiEvaluationScore = AiScoreProjection


@dataclass(frozen=True, slots=True)
class AiObservation:
    observation_type: AiObservationType
    name: str
    correlation_ids: AiObservabilityCorrelationIds = field(
        default_factory=AiObservabilityCorrelationIds
    )
    status: AiObservationStatus = AiObservationStatus.SUCCESS
    model_name: str | None = None
    provider_name: str | None = None
    latency_ms: float | None = None
    prompt: str | None = None
    response: str | None = None
    input_shape: str | None = None
    output_shape: str | None = None
    prompt_reference: AiPromptVersionReference | None = None
    metadata: AiMetadata = field(default_factory=lambda: _EMPTY_METADATA)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_non_empty(self.name, "name")
        if self.latency_ms is not None and self.latency_ms < 0.0:
            raise ValueError("latency_ms cannot be negative.")
        for field_name in (
            "model_name",
            "provider_name",
            "prompt",
            "response",
            "input_shape",
            "output_shape",
        ):
            _validate_optional_non_empty(getattr(self, field_name), field_name)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def family(self) -> AiObservationFamily:
        return self.observation_type.family

    def idempotency_key(self) -> str:
        payload = (
            self.observation_type.value,
            self.name,
            self.status.value,
            self.model_name,
            self.provider_name,
            self.correlation_ids.key_parts(),
            () if self.prompt_reference is None else self.prompt_reference.key_parts(),
        )
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return f"aiobs:{digest}"


@dataclass(frozen=True, slots=True)
class AiGenerationObservation(AiObservation):
    token_count_input: int | None = None
    token_count_output: int | None = None
    cost_usd: float | None = None

    def __post_init__(self) -> None:
        AiObservation.__post_init__(self)
        _validate_optional_non_negative_int(
            self.token_count_input,
            "token_count_input",
        )
        _validate_optional_non_negative_int(
            self.token_count_output,
            "token_count_output",
        )
        if self.cost_usd is not None and self.cost_usd < 0.0:
            raise ValueError("cost_usd cannot be negative.")


@dataclass(frozen=True, slots=True)
class AiRetrievalObservation(AiObservation):
    retrieved_count: int = 0
    selected_context_ids: tuple[str, ...] = ()
    retrieval_scores: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        AiObservation.__post_init__(self)
        if self.retrieved_count < 0:
            raise ValueError("retrieved_count cannot be negative.")
        object.__setattr__(
            self,
            "selected_context_ids",
            _clean_tuple(self.selected_context_ids),
        )
        object.__setattr__(
            self,
            "retrieval_scores",
            tuple(float(score) for score in self.retrieval_scores),
        )


@dataclass(frozen=True, slots=True)
class AiRerankingObservation(AiObservation):
    candidate_count: int = 0
    selected_count: int = 0
    reranking_scores: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        AiObservation.__post_init__(self)
        _validate_non_negative_int(self.candidate_count, "candidate_count")
        _validate_non_negative_int(self.selected_count, "selected_count")
        if self.selected_count > self.candidate_count:
            raise ValueError("selected_count cannot exceed candidate_count.")
        object.__setattr__(
            self,
            "reranking_scores",
            tuple(float(score) for score in self.reranking_scores),
        )


@dataclass(frozen=True, slots=True)
class AiEvaluationObservation(AiObservation):
    scores: tuple[AiScoreProjection, ...] = ()
    evaluated_observation_id: str | None = None

    def __post_init__(self) -> None:
        AiObservation.__post_init__(self)
        object.__setattr__(self, "scores", tuple(self.scores))
        _validate_optional_non_empty(
            self.evaluated_observation_id,
            "evaluated_observation_id",
        )

    def idempotency_key(self) -> str:
        payload = (
            AiObservation.idempotency_key(self),
            tuple(score.key_parts() for score in self.scores),
            self.evaluated_observation_id,
        )
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return f"aievaluation:{digest}"


@dataclass(frozen=True, slots=True)
class AiObservabilityExportResult:
    status: AiObservabilityExportStatus
    idempotency_key: str
    observation_id: str | None = None
    external_trace_id: str | None = None
    external_observation_id: str | None = None
    dataset_id: str | None = None
    case_id: str | None = None
    run_id: str | None = None
    error_message: str | None = None
    retry_after_seconds: float | None = None
    exported_at: datetime | None = None

    def __post_init__(self) -> None:
        _require_non_empty(self.idempotency_key, "idempotency_key")
        for field_name in (
            "observation_id",
            "external_trace_id",
            "external_observation_id",
            "dataset_id",
            "case_id",
            "run_id",
            "error_message",
        ):
            _validate_optional_non_empty(getattr(self, field_name), field_name)
        if self.retry_after_seconds is not None and self.retry_after_seconds < 0.0:
            raise ValueError("retry_after_seconds cannot be negative.")

    @classmethod
    def exported(
        cls,
        *,
        idempotency_key: str,
        observation_id: str | None = None,
        external_trace_id: str | None = None,
        external_observation_id: str | None = None,
        dataset_id: str | None = None,
        case_id: str | None = None,
        run_id: str | None = None,
    ) -> AiObservabilityExportResult:
        return cls(
            status=AiObservabilityExportStatus.EXPORTED,
            idempotency_key=idempotency_key,
            observation_id=observation_id,
            external_trace_id=external_trace_id,
            external_observation_id=external_observation_id,
            dataset_id=dataset_id,
            case_id=case_id,
            run_id=run_id,
            exported_at=datetime.now(UTC),
        )

    @classmethod
    def failed(
        cls,
        *,
        idempotency_key: str,
        error_message: str,
        retry_after_seconds: float | None = None,
    ) -> AiObservabilityExportResult:
        return cls(
            status=AiObservabilityExportStatus.FAILED,
            idempotency_key=idempotency_key,
            error_message=error_message,
            retry_after_seconds=retry_after_seconds,
        )


def _freeze_metadata(metadata: AiMetadata) -> AiMetadata:
    clean: dict[str, AiMetadataValue] = {}
    for key, value in metadata.items():
        _require_non_empty(key, "metadata key")
        if isinstance(value, str | int | float | bool) or value is None:
            clean[key] = value
        else:
            raise TypeError(
                "metadata values must be strings, numbers, booleans, or None."
            )
    return MappingProxyType(clean)


def _clean_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(value.strip() for value in values if value.strip())


def _drop_none(values: tuple[str | None, ...]) -> tuple[str, ...]:
    return tuple(value for value in values if value is not None)


def _validate_score(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be numeric.")
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _validate_non_negative_int(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _validate_optional_non_negative_int(
    value: int | None,
    field_name: str,
) -> None:
    if value is None:
        return
    _validate_non_negative_int(value, field_name)


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _validate_optional_non_empty(value: str | None, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name)
