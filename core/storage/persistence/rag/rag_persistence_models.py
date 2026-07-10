from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Mapping
from typing import Sequence
from typing import TypeAlias
from uuid import uuid4

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]


@dataclass(
    frozen=True,
    slots=True,
)
class RagCanonicalRecordCounts:
    """Canonical PostgreSQL RAG record counts used by readiness diagnostics."""

    document_count: int
    chunk_count: int
    embedding_job_count: int
    graph_job_count: int

    def __post_init__(self) -> None:
        for field_name in self.__dataclass_fields__:
            _require_non_negative(getattr(self, field_name), field_name)


@dataclass(
    frozen=True,
    slots=True,
)
class RagDocumentRecord:
    """
    Typed persistence-boundary record for a curated RAG source document.

    RAG/vector stores are downstream projections. This record preserves the
    canonical PostgreSQL source lineage before any vector-store write occurs.
    """

    document_id: str
    source_table: str
    source_id: str
    source_type: str
    title: str
    content_text: str
    generated_at: datetime
    content_hash: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        for field_name in (
            "document_id",
            "source_table",
            "source_id",
            "source_type",
            "title",
            "content_text",
        ):
            _require_non_empty(
                getattr(
                    self,
                    field_name,
                ),
                field_name,
            )


@dataclass(
    frozen=True,
    slots=True,
)
class RagChunkRecord:
    """
    Typed persistence-boundary record for a curated RAG chunk.
    """

    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    token_count: int | None = None
    content_hash: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.chunk_id,
            "chunk_id",
        )
        _require_non_empty(
            self.document_id,
            "document_id",
        )
        _require_non_empty(
            self.chunk_text,
            "chunk_text",
        )
        _require_non_negative(
            self.chunk_index,
            "chunk_index",
        )
        if self.token_count is not None:
            _require_non_negative(
                self.token_count,
                "token_count",
            )


@dataclass(
    frozen=True,
    slots=True,
)
class RagEmbeddingJobRecord:
    """
    Typed persistence-boundary record for a queued embedding projection job.
    """

    job_id: str
    document_id: str
    target_store: str
    embedding_model: str
    status: str
    queued_at: datetime
    chunk_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.job_id,
            "job_id",
        )
        _require_non_empty(
            self.document_id,
            "document_id",
        )
        _require_non_empty(
            self.target_store,
            "target_store",
        )
        _require_non_empty(
            self.embedding_model,
            "embedding_model",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        _require_non_negative(
            self.attempts,
            "attempts",
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagGraphJobRecord:
    """
    Typed persistence-boundary record for a queued graph projection job.
    """

    job_id: str
    document_id: str
    target_store: str
    graph_model: str
    status: str
    queued_at: datetime
    chunk_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.job_id,
            "job_id",
        )
        _require_non_empty(
            self.document_id,
            "document_id",
        )
        _require_non_empty(
            self.target_store,
            "target_store",
        )
        _require_non_empty(
            self.graph_model,
            "graph_model",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        _require_non_negative(
            self.attempts,
            "attempts",
        )


MAX_RAG_QUERY_MODEL_EXECUTIONS = 32


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryModelExecutionRecord:
    """Typed persistence value for one ordered RAG model invocation."""

    operation: str
    configured_model: str
    provider_name: str
    duration_ms: float
    success: bool

    def __post_init__(self) -> None:
        for field_name in (
            "operation",
            "configured_model",
            "provider_name",
        ):
            _require_non_empty(
                getattr(self, field_name),
                field_name,
            )
        _require_non_negative_float(
            self.duration_ms,
            "duration_ms",
        )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "operation": self.operation,
            "configured_model": self.configured_model,
            "provider_name": self.provider_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object],
    ) -> RagQueryModelExecutionRecord:
        return cls(
            operation=_required_mapping_string(payload, "operation"),
            configured_model=_required_mapping_string(payload, "configured_model"),
            provider_name=_required_mapping_string(payload, "provider_name"),
            duration_ms=_required_mapping_float(payload, "duration_ms"),
            success=_required_mapping_bool(payload, "success"),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryReflectionScores:
    """Typed persistence value for Self-RAG reflection scores."""

    retrieval_necessity: float
    source_relevance: float
    answer_support: float
    usefulness: float

    def __post_init__(self) -> None:
        for field_name in (
            "retrieval_necessity",
            "source_relevance",
            "answer_support",
            "usefulness",
        ):
            _require_ratio(
                getattr(self, field_name),
                field_name,
            )

    def as_dict(self) -> dict[str, JsonValue]:
        return {
            "retrieval_necessity": self.retrieval_necessity,
            "source_relevance": self.source_relevance,
            "answer_support": self.answer_support,
            "usefulness": self.usefulness,
        }

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, object],
    ) -> RagQueryReflectionScores:
        return cls(
            retrieval_necessity=_required_mapping_float(
                payload,
                "retrieval_necessity",
            ),
            source_relevance=_required_mapping_float(
                payload,
                "source_relevance",
            ),
            answer_support=_required_mapping_float(
                payload,
                "answer_support",
            ),
            usefulness=_required_mapping_float(
                payload,
                "usefulness",
            ),
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagQueryLogRecord:
    """
    Typed persistence-boundary record for a RAG retrieval request.
    """

    query_id: str
    query_text: str
    retrieval_route: str
    top_k: int
    status: str
    started_at: datetime
    normalized_query: str | None = None
    requester: str | None = None
    workflow_name: str | None = None
    execution_id: str | None = None
    filters: JsonObject = field(default_factory=dict)
    model_executions: tuple[RagQueryModelExecutionRecord, ...] = field(
        default_factory=tuple
    )
    context_count: int = 0
    citation_count: int = 0
    grounding_score: float | None = None
    utility_score: float | None = None
    injection_detected: bool = False
    reflection_scores: RagQueryReflectionScores | None = None
    corrective_actions: tuple[str, ...] = field(default_factory=tuple)
    completed_at: datetime | None = None
    duration_ms: float | None = None
    error: str | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.query_id,
            "query_id",
        )
        _require_non_empty(
            self.query_text,
            "query_text",
        )
        _require_non_empty(
            self.retrieval_route,
            "retrieval_route",
        )
        _require_positive(
            self.top_k,
            "top_k",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        if len(self.model_executions) > MAX_RAG_QUERY_MODEL_EXECUTIONS:
            raise ValueError(
                "model_executions cannot contain more than "
                f"{MAX_RAG_QUERY_MODEL_EXECUTIONS} records."
            )
        _require_non_negative(
            self.context_count,
            "context_count",
        )
        _require_non_negative(
            self.citation_count,
            "citation_count",
        )
        for field_name in (
            "grounding_score",
            "utility_score",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _require_ratio(
                    value,
                    field_name,
                )
        for action in self.corrective_actions:
            _require_non_empty(
                action,
                "corrective_actions item",
            )
        if self.duration_ms is not None:
            _require_non_negative_float(
                self.duration_ms,
                "duration_ms",
            )


@dataclass(
    frozen=True,
    slots=True,
)
class RagAnswerLogRecord:
    """
    Typed persistence-boundary record for a generated RAG answer.
    """

    answer_id: str
    query_id: str
    answer_text: str
    status: str
    completed_at: datetime
    answer_hash: str | None = None
    generation_model: str | None = None
    confidence_score: float | None = None
    source_count: int = 0
    citations: JsonObject = field(default_factory=dict)
    sources: JsonObject = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        _require_non_empty(
            self.answer_id,
            "answer_id",
        )
        _require_non_empty(
            self.query_id,
            "query_id",
        )
        _require_non_empty(
            self.answer_text,
            "answer_text",
        )
        _require_non_empty(
            self.status,
            "status",
        )
        _require_non_negative(
            self.source_count,
            "source_count",
        )
        if self.confidence_score is not None:
            _require_ratio(
                self.confidence_score,
                "confidence_score",
            )


@dataclass(
    frozen=True,
    slots=True,
)
class RagPersistenceBundle:
    """
    Atomic RAG source persistence payload.
    """

    document: RagDocumentRecord
    chunks: tuple[RagChunkRecord, ...] = ()
    embedding_jobs: tuple[RagEmbeddingJobRecord, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class RagPersistenceResult:
    """
    Typed result returned by RAG source persistence adapters.
    """

    success: bool
    records_persisted: int = 0
    document_id: str | None = None
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")

        if self.success:
            _require_non_empty(
                self.document_id,
                "document_id",
            )

        if not self.success:
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        document_id: str,
        records_persisted: int = 1,
    ) -> RagPersistenceResult:
        return cls(
            success=True,
            records_persisted=records_persisted,
            document_id=document_id,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> RagPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagRecordPersistenceResult:
    """
    Generic typed result for single-record RAG persistence operations.
    """

    success: bool
    record_id: str | None = None
    records_persisted: int = 0
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )
        if self.success and self.error is not None:
            raise ValueError("successful persistence results cannot include an error.")
        if self.success:
            _require_non_empty(
                self.record_id,
                "record_id",
            )
        if not self.success:
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        record_id: str,
        records_persisted: int = 1,
    ) -> RagRecordPersistenceResult:
        return cls(
            success=True,
            record_id=record_id,
            records_persisted=records_persisted,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> RagRecordPersistenceResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagSourceEligibilityRecord:
    """
    Metadata-only eligibility decision for a canonical PostgreSQL RAG source.

    RAG/vector/graph stores are downstream rebuildable projections. This record
    only marks whether a curated PostgreSQL source record is eligible to become
    a future RAG source; it does not represent an embedding, chunk, vector-store
    write, graph-store write, or ingestion job.
    """

    eligibility_id: str
    source_table: str
    source_id: str
    source_type: str
    eligible: bool
    reason: str
    quality_score: float
    reviewed_timestamp: datetime
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(
        self,
    ) -> None:
        object.__setattr__(
            self,
            "eligibility_id",
            _clean_non_empty(
                self.eligibility_id,
                "eligibility_id",
            ),
        )
        object.__setattr__(
            self,
            "source_table",
            _clean_non_empty(
                self.source_table,
                "source_table",
            ),
        )
        object.__setattr__(
            self,
            "source_id",
            _clean_non_empty(
                self.source_id,
                "source_id",
            ),
        )
        object.__setattr__(
            self,
            "source_type",
            _clean_non_empty(
                self.source_type,
                "source_type",
            ),
        )
        object.__setattr__(
            self,
            "reason",
            _clean_non_empty(
                self.reason,
                "reason",
            ),
        )
        _require_ratio(
            self.quality_score,
            "quality_score",
        )
        object.__setattr__(
            self,
            "metadata",
            dict(
                self.metadata,
            ),
        )

    @property
    def source_key(
        self,
    ) -> tuple[str, str, str]:
        return (
            self.source_table,
            self.source_type,
            self.source_id,
        )

    def as_dict(
        self,
    ) -> dict[str, JsonValue]:
        return {
            "eligibility_id": self.eligibility_id,
            "source_table": self.source_table,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "eligible": self.eligible,
            "reason": self.reason,
            "quality_score": self.quality_score,
            "reviewed_timestamp": self.reviewed_timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class RagSourceEligibilityResult:
    """
    Typed result returned by future RAG eligibility persistence adapters.
    """

    success: bool
    eligibility_id: str | None = None
    records_persisted: int = 0
    error: str | None = None

    def __post_init__(
        self,
    ) -> None:
        _require_non_negative(
            self.records_persisted,
            "records_persisted",
        )

        if self.success and self.error is not None:
            raise ValueError("successful eligibility results cannot include an error.")

        if self.success:
            _require_non_empty(
                self.eligibility_id,
                "eligibility_id",
            )

        if not self.success:
            _require_non_empty(
                self.error,
                "error",
            )

    @classmethod
    def succeeded(
        cls,
        *,
        eligibility_id: str,
        records_persisted: int = 1,
    ) -> RagSourceEligibilityResult:
        return cls(
            success=True,
            eligibility_id=eligibility_id,
            records_persisted=records_persisted,
        )

    @classmethod
    def failed(
        cls,
        error: str,
    ) -> RagSourceEligibilityResult:
        return cls(
            success=False,
            records_persisted=0,
            error=error,
        )


def new_rag_document_id(
    *,
    source_table: str,
    source_id: str,
    source_type: str,
) -> str:
    _require_non_empty(
        source_table,
        "source_table",
    )
    _require_non_empty(
        source_id,
        "source_id",
    )
    _require_non_empty(
        source_type,
        "source_type",
    )

    return (
        f"rag_document:{source_table.strip()}:{source_type.strip()}:{source_id.strip()}"
    )


def new_rag_source_eligibility_id(
    *,
    source_table: str,
    source_id: str,
    source_type: str,
) -> str:
    return "rag_source_eligibility:" + ":".join(
        (
            _clean_non_empty(
                source_table,
                "source_table",
            ),
            _clean_non_empty(
                source_type,
                "source_type",
            ),
            _clean_non_empty(
                source_id,
                "source_id",
            ),
        )
    )


def new_rag_chunk_id(
    *,
    document_id: str,
    chunk_index: int,
) -> str:
    _require_non_empty(
        document_id,
        "document_id",
    )
    _require_non_negative(
        chunk_index,
        "chunk_index",
    )

    return f"{document_id}:chunk:{chunk_index}"


def new_rag_embedding_job_id(
    *,
    document_id: str,
    chunk_id: str | None = None,
    target_store: str,
    embedding_model: str,
) -> str:
    _require_non_empty(
        document_id,
        "document_id",
    )
    _require_non_empty(
        target_store,
        "target_store",
    )
    _require_non_empty(
        embedding_model,
        "embedding_model",
    )

    if chunk_id is not None and chunk_id.strip():
        return f"rag_embedding_job:{target_store.strip()}:{embedding_model.strip()}:{chunk_id.strip()}"

    return f"rag_embedding_job:{target_store.strip()}:{embedding_model.strip()}:{document_id.strip()}:{uuid4().hex}"


def new_rag_graph_job_id(
    *,
    document_id: str,
    chunk_id: str | None = None,
    target_store: str,
    graph_model: str,
) -> str:
    _require_non_empty(
        document_id,
        "document_id",
    )
    _require_non_empty(
        target_store,
        "target_store",
    )
    _require_non_empty(
        graph_model,
        "graph_model",
    )

    if chunk_id is not None and chunk_id.strip():
        return f"rag_graph_job:{target_store.strip()}:{graph_model.strip()}:{chunk_id.strip()}"

    return f"rag_graph_job:{target_store.strip()}:{graph_model.strip()}:{document_id.strip()}:{uuid4().hex}"


def new_rag_query_log_id() -> str:
    return f"rag_query_log:{uuid4().hex}"


def new_rag_answer_log_id(
    *,
    query_id: str,
) -> str:
    _require_non_empty(
        query_id,
        "query_id",
    )

    return f"rag_answer_log:{query_id.strip()}:{uuid4().hex}"


def _require_non_empty(
    value: str | None,
    field_name: str,
) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")


def _clean_non_empty(
    value: str | None,
    field_name: str,
) -> str:
    _require_non_empty(
        value,
        field_name,
    )
    assert value is not None
    return value.strip()


def _require_ratio(
    value: float,
    field_name: str,
) -> None:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")


def _require_non_negative(
    value: int,
    field_name: str,
) -> None:
    if value < 0:
        raise ValueError(f"{field_name} cannot be negative.")


def _require_positive(
    value: int,
    field_name: str,
) -> None:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive.")


def _required_mapping_string(
    payload: Mapping[str, object],
    key: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{key} must be a non-empty string.")
    return value


def _required_mapping_float(
    payload: Mapping[str, object],
    key: str,
) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{key} must be numeric.")
    return float(value)


def _required_mapping_bool(
    payload: Mapping[str, object],
    key: str,
) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be a boolean.")
    return value


def _require_non_negative_float(
    value: float,
    field_name: str,
) -> None:
    if value < 0.0:
        raise ValueError(f"{field_name} cannot be negative.")
