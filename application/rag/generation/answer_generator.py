from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from application.rag.generation.secure_prompt_builder import (
    RAG_ANSWER_GENERATION_PROMPT_HASH,
)
from application.rag.generation.secure_prompt_builder import (
    RAG_ANSWER_GENERATION_PROMPT_NAME,
)
from application.rag.generation.secure_prompt_builder import (
    RAG_ANSWER_GENERATION_PROMPT_SOURCE,
)
from application.rag.generation.secure_prompt_builder import (
    RAG_ANSWER_GENERATION_PROMPT_VERSION,
)
from application.rag.generation.secure_prompt_builder import SecureRagContextPackage
from application.rag.generation.secure_prompt_builder import SecureRagPromptBuilder
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.storage.persistence.rag import JsonObject
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationProvider,
)
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationRequest,
)


@dataclass(
    frozen=True,
    slots=True,
)
class RagAnswerGeneratorConfig:
    """
    Runtime controls for secure RAG answer generation.
    """

    operation_name: str = "rag.generation.answer"

    def __post_init__(
        self,
    ) -> None:
        if not self.operation_name.strip():
            raise ValueError("operation_name cannot be empty.")


class RagAnswerGenerator:
    """
    Generates RAG answers from securely packaged retrieved context.

    The provider is responsible for calling a model. This generator owns the
    platform policy boundary, final citation provenance, and telemetry around
    the generation use case.
    """

    def __init__(
        self,
        *,
        answer_provider: RagAnswerGenerationProvider,
        prompt_builder: SecureRagPromptBuilder | None = None,
        telemetry: ApplicationRagTelemetry | None = None,
        config: RagAnswerGeneratorConfig | None = None,
    ) -> None:
        self._answer_provider = answer_provider
        self._prompt_builder = prompt_builder or SecureRagPromptBuilder()
        self._telemetry = telemetry
        self._config = config or RagAnswerGeneratorConfig()

    async def generate(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> RagResult:
        started_at = perf_counter()
        await self._emit_started(
            request=request,
            context_count=len(contexts),
        )
        if not contexts:
            result = RagResult.no_results(
                request=request,
            )
            await self._emit_completed(
                request=request,
                result=result,
                context_count=0,
                duration_seconds=perf_counter() - started_at,
            )
            return result

        try:
            stage_started_at = perf_counter()
            package = self._prompt_builder.build(
                request=request,
                contexts=contexts,
            )
            await self._emit_stage_completed(
                request=request,
                operation="rag.generation.context_packaging",
                duration_seconds=perf_counter() - stage_started_at,
                attributes={
                    "context_count": len(contexts),
                    "citation_count": len(package.citation_ids),
                },
            )

            stage_started_at = perf_counter()
            provider_result = await self._answer_provider.generate_answer(
                _provider_request_from_package(
                    package,
                )
            )
            await self._emit_stage_completed(
                request=request,
                operation="rag.generation.provider_call",
                duration_seconds=perf_counter() - stage_started_at,
                attributes={
                    "context_count": len(contexts),
                    "provider_name": provider_result.provider_name,
                    "generation_model": provider_result.model,
                    "confidence_score": provider_result.confidence_score,
                },
            )
        except Exception as exc:
            await self._emit_failed(
                request=request,
                error=exc,
                duration_seconds=perf_counter() - started_at,
            )
            return RagResult.failed(
                request=request,
                error=str(exc),
            )

        result = RagResult.answered(
            request=request,
            answer_text=provider_result.answer_text,
            contexts=package.contexts,
            confidence_score=provider_result.confidence_score,
            metadata=_result_metadata(
                package=package,
                provider_name=provider_result.provider_name,
                model=provider_result.model,
                provider_metadata=provider_result.metadata,
            ),
        )
        await self._emit_completed(
            request=request,
            result=result,
            context_count=len(contexts),
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def _emit_started(
        self,
        *,
        request: RagRequest,
        context_count: int,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_started(
            "RagAnswerGenerator",
            self._config.operation_name,
            correlation_id=request.request_id,
            attributes={
                "route": request.route,
                "context_count": context_count,
            },
        )

    async def _emit_completed(
        self,
        *,
        request: RagRequest,
        result: RagResult,
        context_count: int,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "RagAnswerGenerator",
            self._config.operation_name,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes={
                "route": request.route,
                "context_count": context_count,
                "citation_count": len(result.citations),
            },
        )

    async def _emit_failed(
        self,
        *,
        request: RagRequest,
        error: Exception,
        duration_seconds: float,
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_failed(
            "RagAnswerGenerator",
            self._config.operation_name,
            error=error,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
        )

    async def _emit_stage_completed(
        self,
        *,
        request: RagRequest,
        operation: str,
        duration_seconds: float,
        attributes: dict[str, Any],
    ) -> None:
        if self._telemetry is None:
            return
        await self._telemetry.emit_operation_completed(
            "RagAnswerGenerator",
            operation,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes={
                **attributes,
                "route": request.route,
            },
        )


def _provider_request_from_package(
    package: SecureRagContextPackage,
) -> RagAnswerGenerationRequest:
    return RagAnswerGenerationRequest(
        request_id=package.request.request_id,
        query=package.request.normalized_query,
        policy_instructions=package.policy_instructions,
        user_prompt=package.user_prompt,
        context_payload=package.context_payload,
        citation_ids=package.citation_ids,
        metadata={
            "package_id": package.package_id,
            "route": package.request.route,
            "context_count": len(package.blocks),
        },
    )


def _result_metadata(
    *,
    package: SecureRagContextPackage,
    provider_name: str | None,
    model: str | None,
    provider_metadata: JsonObject,
) -> JsonObject:
    return {
        "context_package_id": package.package_id,
        "citation_ids": list(
            package.citation_ids,
        ),
        "generation_provider": provider_name,
        "generation_model": model,
        "prompt_name": RAG_ANSWER_GENERATION_PROMPT_NAME,
        "prompt_version": RAG_ANSWER_GENERATION_PROMPT_VERSION,
        "prompt_hash": RAG_ANSWER_GENERATION_PROMPT_HASH,
        "prompt_source": RAG_ANSWER_GENERATION_PROMPT_SOURCE,
        "provider_metadata": dict(
            provider_metadata,
        ),
    }
