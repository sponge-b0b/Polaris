from __future__ import annotations

from time import perf_counter
from typing import Protocol

from application.rag.contracts.rag_operation_models import (
    RagOperationDetail,
    RagOperationResult,
    RagProcessEmbeddingsOperationRequest,
)
from application.rag.operations.rag_ingestion_operations import apply_limit
from application.rag.operations.rag_operation_telemetry import RagOperationTelemetry
from core.storage.persistence.rag import RagPersistenceRepository
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry


class EmbeddingJobProcessorPort(Protocol):
    async def process_queued_jobs(
        self,
        *,
        batch_size: int | None = None,
    ) -> object: ...


class RagEmbeddingJobOperationsService:
    """Processes canonical PostgreSQL embedding jobs."""

    def __init__(
        self,
        *,
        rag_repository: RagPersistenceRepository,
        embedding_job_processor: EmbeddingJobProcessorPort | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._rag_repository = rag_repository
        self._embedding_job_processor = embedding_job_processor
        self._telemetry = RagOperationTelemetry(self.__class__.__name__, telemetry)

    async def process_embeddings(
        self,
        request: RagProcessEmbeddingsOperationRequest,
    ) -> RagOperationResult:
        operation = "rag.process_embeddings"
        queued_jobs = await self._rag_repository.list_embedding_jobs(status="queued")
        limited_jobs = apply_limit(queued_jobs, request.batch_size)
        if request.dry_run:
            return RagOperationResult.succeeded(
                operation=operation,
                message="Dry run complete; queued embedding jobs were not processed.",
                records_processed=len(limited_jobs),
                dry_run=True,
                details=(
                    RagOperationDetail(
                        "queued_embedding_jobs",
                        str(len(queued_jobs)),
                    ),
                ),
            )
        if self._embedding_job_processor is None:
            return RagOperationResult.failed(
                operation=operation,
                error="Embedding job processor is not configured.",
            )

        started_at = perf_counter()
        await self._telemetry.emit_started(
            operation,
            details=(
                RagOperationDetail("queued_embedding_jobs", str(len(queued_jobs))),
            ),
        )
        try:
            processor_result = await self._embedding_job_processor.process_queued_jobs(
                batch_size=request.batch_size,
            )
        except Exception as exc:
            await self._telemetry.emit_failed(
                operation,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            return RagOperationResult.failed(operation=operation, error=str(exc))

        result = RagOperationResult.succeeded(
            operation=operation,
            message="Embedding job processing complete.",
            records_processed=safe_int_attr(processor_result, "processed_count"),
            details=(
                RagOperationDetail(
                    "completed_count",
                    str(safe_int_attr(processor_result, "completed_count")),
                ),
                RagOperationDetail(
                    "retryable_failure_count",
                    str(safe_int_attr(processor_result, "retryable_failure_count")),
                ),
                RagOperationDetail(
                    "terminal_failure_count",
                    str(safe_int_attr(processor_result, "terminal_failure_count")),
                ),
                RagOperationDetail(
                    "retryable_job_ids",
                    ",".join(
                        safe_string_sequence_attr(
                            processor_result,
                            "retryable_job_ids",
                        )
                    ),
                ),
                RagOperationDetail(
                    "terminal_failure_job_ids",
                    ",".join(
                        safe_string_sequence_attr(
                            processor_result,
                            "terminal_failure_job_ids",
                        )
                    ),
                ),
                RagOperationDetail(
                    "failure_summaries",
                    " | ".join(
                        safe_string_sequence_attr(
                            processor_result,
                            "failure_summaries",
                        )
                    ),
                ),
            ),
        )
        await self._telemetry.emit_completed(
            operation,
            result=result,
            duration_seconds=perf_counter() - started_at,
        )
        return result


def safe_int_attr(value: object, attribute: str) -> int:
    attr_value = getattr(value, attribute, 0)
    return attr_value if isinstance(attr_value, int) else 0


def safe_string_sequence_attr(value: object, attribute: str) -> tuple[str, ...]:
    attr_value = getattr(value, attribute, ())
    if not isinstance(attr_value, tuple | list):
        return ()
    return tuple(item for item in attr_value if isinstance(item, str))
