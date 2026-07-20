from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any, cast

from application.ai_optimization.runtime_artifacts import (
    RAG_ANSWER_GENERATION_ARTIFACT_TARGET,
    AiPromptArtifactResolver,
    ResolvedAiPromptArtifact,
)
from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from application.rag.generation.secure_prompt_builder import (
    RAG_ANSWER_GENERATION_PROMPT_HASH,
    RAG_ANSWER_GENERATION_PROMPT_NAME,
    RAG_ANSWER_GENERATION_PROMPT_SOURCE,
    RAG_ANSWER_GENERATION_PROMPT_VERSION,
    SecureRagContextPackage,
    SecureRagPromptBuilder,
)
from application.rag.security.rag_security import safe_grounding_failure_answer
from core.storage.persistence.ai_artifacts import AiArtifactType
from core.storage.persistence.rag import JsonObject, JsonValue
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from domain.llm.reasoning_trace_safety import (
    ReasoningTraceViolationError,
    reject_reasoning_trace,
    sanitize_reasoning_trace_text,
)
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationProvider,
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
        prompt_artifact_resolver: AiPromptArtifactResolver | None = None,
    ) -> None:
        self._answer_provider = answer_provider
        self._prompt_builder = prompt_builder or SecureRagPromptBuilder()
        self._telemetry = telemetry
        self._config = config or RagAnswerGeneratorConfig()
        self._prompt_artifact_resolver = prompt_artifact_resolver

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

            prompt_artifact = await self._resolve_prompt_artifact()

            stage_started_at = perf_counter()
            provider_result = await self._answer_provider.generate_answer(
                _provider_request_from_package(
                    package,
                    prompt_artifact=prompt_artifact,
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
                    "ai_artifact_id": None
                    if prompt_artifact is None
                    else prompt_artifact.artifact_id,
                    "prompt_version": RAG_ANSWER_GENERATION_PROMPT_VERSION
                    if prompt_artifact is None
                    else prompt_artifact.artifact_version,
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

        try:
            reject_reasoning_trace(
                provider_result.answer_text,
                boundary_name="RAG answer generation result",
            )
        except ReasoningTraceViolationError:
            await self._emit_stage_completed(
                request=request,
                operation="rag.generation.reasoning_trace_guard",
                duration_seconds=0.0,
                attributes={
                    "reasoning_trace_detected": True,
                    "fail_closed": True,
                },
            )
            result = RagResult.no_results(
                request=request,
                answer_text=safe_grounding_failure_answer(),
            )
            await self._emit_completed(
                request=request,
                result=result,
                context_count=len(contexts),
                duration_seconds=perf_counter() - started_at,
            )
            return result

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
                prompt_artifact=prompt_artifact,
            ),
        )
        await self._emit_completed(
            request=request,
            result=result,
            context_count=len(contexts),
            duration_seconds=perf_counter() - started_at,
        )
        return result

    async def _resolve_prompt_artifact(
        self,
    ) -> ResolvedAiPromptArtifact | None:
        if self._prompt_artifact_resolver is None:
            return None
        return await self._prompt_artifact_resolver.resolve_active_artifact(
            RAG_ANSWER_GENERATION_ARTIFACT_TARGET,
            artifact_type=AiArtifactType.DSPY_COMPILED_PROMPT,
        )

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
    *,
    prompt_artifact: ResolvedAiPromptArtifact | None = None,
) -> RagAnswerGenerationRequest:
    metadata: JsonObject = {
        "package_id": package.package_id,
        "route": package.request.route,
        "context_count": len(package.blocks),
    }
    if prompt_artifact is not None:
        metadata = {
            **metadata,
            **prompt_artifact.to_metadata(),
        }

    return RagAnswerGenerationRequest(
        request_id=package.request.request_id,
        query=package.request.normalized_query,
        policy_instructions=package.policy_instructions,
        user_prompt=package.user_prompt,
        context_payload=package.context_payload,
        citation_ids=package.citation_ids,
        metadata=metadata,
    )


def _result_metadata(
    *,
    package: SecureRagContextPackage,
    provider_name: str | None,
    model: str | None,
    provider_metadata: JsonObject,
    prompt_artifact: ResolvedAiPromptArtifact | None = None,
) -> JsonObject:
    prompt_metadata: JsonObject = (
        {
            "prompt_name": RAG_ANSWER_GENERATION_PROMPT_NAME,
            "prompt_version": RAG_ANSWER_GENERATION_PROMPT_VERSION,
            "prompt_hash": RAG_ANSWER_GENERATION_PROMPT_HASH,
            "prompt_source": RAG_ANSWER_GENERATION_PROMPT_SOURCE,
        }
        if prompt_artifact is None
        else prompt_artifact.to_metadata()
    )
    return {
        "context_package_id": package.package_id,
        "citation_ids": list(
            package.citation_ids,
        ),
        "generation_provider": provider_name,
        "generation_model": model,
        **prompt_metadata,
        "provider_metadata": _safe_provider_metadata(
            provider_metadata,
        ),
    }


_REASONING_METADATA_KEYS = frozenset(
    {
        "chain_of_thought",
        "hidden_reasoning",
        "internal_reasoning",
        "model_reasoning",
        "reasoning",
        "reasoning_trace",
        "scratchpad",
        "thinking",
        "thoughts",
    }
)
_REASONING_METADATA_KEY_ALLOWLIST = frozenset(
    {
        "reasoning_trace_safety",
    }
)


def _safe_provider_metadata(
    provider_metadata: JsonObject,
) -> JsonObject:
    sanitized: dict[str, JsonValue] = {}
    for key, value in provider_metadata.items():
        keep, sanitized_value = _safe_metadata_value(
            value,
            key_path=(key,),
        )
        if keep:
            sanitized[key] = sanitized_value
    return sanitized


def _safe_metadata_value(
    value: JsonValue,
    *,
    key_path: tuple[str, ...],
) -> tuple[bool, JsonValue]:
    if key_path and _is_model_reasoning_metadata_key(key_path[-1]):
        return False, None
    if isinstance(value, str):
        sanitized = sanitize_reasoning_trace_text(value)
        if sanitized.detected:
            return False, None
        return True, value
    if isinstance(value, Mapping):
        safe_mapping: dict[str, JsonValue] = {}
        for nested_key, nested_value in value.items():
            keep, safe_value = _safe_metadata_value(
                cast(JsonValue, nested_value),
                key_path=(*key_path, str(nested_key)),
            )
            if keep:
                safe_mapping[str(nested_key)] = safe_value
        return True, safe_mapping
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        safe_items: list[JsonValue] = []
        for item in value:
            keep, safe_item = _safe_metadata_value(
                cast(JsonValue, item),
                key_path=key_path,
            )
            if keep:
                safe_items.append(safe_item)
        return True, safe_items
    return True, value


def _is_model_reasoning_metadata_key(
    key: str,
) -> bool:
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in _REASONING_METADATA_KEY_ALLOWLIST:
        return False
    return normalized in _REASONING_METADATA_KEYS
