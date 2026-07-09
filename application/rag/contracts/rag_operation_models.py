from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class RagProjectionConfig:
    collection_name: str
    vector_size: int
    embedding_model: str

    def __post_init__(self) -> None:
        _require_non_empty(self.collection_name, "collection_name")
        _require_non_empty(self.embedding_model, "embedding_model")
        if self.vector_size <= 0:
            raise ValueError("vector_size must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagOperationDetail:
    name: str
    value: str

    def __post_init__(self) -> None:
        _require_non_empty(self.name, "name")


@dataclass(
    frozen=True,
    slots=True,
)
class RagOperationResult:
    success: bool
    operation: str
    status: str
    message: str
    records_processed: int = 0
    dry_run: bool = False
    details: tuple[RagOperationDetail, ...] = ()
    error: str | None = None

    @classmethod
    def succeeded(
        cls,
        *,
        operation: str,
        message: str,
        records_processed: int = 0,
        dry_run: bool = False,
        details: tuple[RagOperationDetail, ...] = (),
    ) -> RagOperationResult:
        return cls(
            success=True,
            operation=operation,
            status="succeeded",
            message=message,
            records_processed=records_processed,
            dry_run=dry_run,
            details=details,
        )

    @classmethod
    def failed(
        cls,
        *,
        operation: str,
        error: str,
        dry_run: bool = False,
        details: tuple[RagOperationDetail, ...] = (),
    ) -> RagOperationResult:
        return cls(
            success=False,
            operation=operation,
            status="failed",
            message=error,
            dry_run=dry_run,
            details=details,
            error=error,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class RagIngestOperationRequest:
    source: str
    limit: int | None = None
    queue_embedding_jobs: bool = True
    queue_graph_jobs: bool = True
    dry_run: bool = False

    def __post_init__(self) -> None:
        _require_non_empty(self.source, "source")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagProcessEmbeddingsOperationRequest:
    batch_size: int | None = None
    dry_run: bool = False

    def __post_init__(self) -> None:
        if self.batch_size is not None and self.batch_size <= 0:
            raise ValueError("batch_size must be positive.")


@dataclass(
    frozen=True,
    slots=True,
)
class RagProcessGraphOperationRequest:
    dry_run: bool = True


@dataclass(
    frozen=True,
    slots=True,
)
class RagRebuildProjectionOperationRequest:
    projection: str
    dry_run: bool = True
    confirm_delete: bool = False

    def __post_init__(self) -> None:
        _require_non_empty(self.projection, "projection")


@dataclass(
    frozen=True,
    slots=True,
)
class RagStatusOperationRequest:
    include_details: bool = True


@dataclass(
    frozen=True,
    slots=True,
)
class RagProjectionReadinessConfig:
    collection_name: str
    vector_size: int
    embedding_model: str
    reranker_model: str

    def __post_init__(self) -> None:
        _require_non_empty(self.collection_name, "collection_name")
        _require_non_empty(self.embedding_model, "embedding_model")
        _require_non_empty(self.reranker_model, "reranker_model")
        if self.vector_size <= 0:
            raise ValueError("vector_size must be positive.")


@dataclass(frozen=True, slots=True)
class RagCanonicalProjectionReadiness:
    available: bool
    document_count: int | None
    chunk_count: int | None
    embedding_job_count: int | None
    graph_job_count: int | None
    pending_embedding_jobs: int | None
    retryable_embedding_jobs: int | None
    failed_embedding_jobs: int | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RagVectorProjectionReadiness:
    collection_name: str
    exists: bool
    healthy: bool
    dense_vector_present: bool
    sparse_vector_present: bool
    configured_vector_size: int
    actual_vector_size: int | None
    vector_size_compatible: bool
    points_count: int
    status: str | None = None
    error: str | None = None

    @property
    def ready(self) -> bool:
        return (
            self.exists
            and self.healthy
            and self.dense_vector_present
            and self.sparse_vector_present
            and self.vector_size_compatible
        )


@dataclass(frozen=True, slots=True)
class RagGraphProjectionReadiness:
    connected: bool
    healthy: bool
    entity_count: int | None
    error: str | None = None

    @property
    def ready(self) -> bool:
        return self.connected and self.healthy


@dataclass(frozen=True, slots=True)
class RagModelReadiness:
    component: str
    model: str
    ready: bool
    dimensions: int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RagProjectionReadinessResult:
    operation: str
    status: str
    message: str
    canonical: RagCanonicalProjectionReadiness
    vector: RagVectorProjectionReadiness
    graph: RagGraphProjectionReadiness
    embedding: RagModelReadiness
    reranker: RagModelReadiness

    @property
    def success(self) -> bool:
        return self.status == "ready"

    @property
    def ready(self) -> bool:
        return self.success


def require_non_empty(value: str | None, field_name: str) -> None:
    _require_non_empty(value, field_name)


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
