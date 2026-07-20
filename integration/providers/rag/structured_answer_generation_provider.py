from __future__ import annotations

from dataclasses import dataclass

from application.rag.contracts.rag_structured_answer import RagStructuredAnswer
from core.storage.persistence.rag import JsonObject
from integration.providers.llm_structured_output import (
    StructuredLlmProvider,
    StructuredLlmRequest,
    StructuredOutputRetryPolicy,
    StructuredOutputSchemaRef,
)
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationProvider,
    RagAnswerGenerationRequest,
    RagAnswerGenerationResult,
)

STRUCTURED_RAG_ANSWER_SCHEMA_VERSION = "v1"
STRUCTURED_RAG_ANSWER_SCHEMA_NAME = "RagStructuredAnswer"


@dataclass(frozen=True, slots=True)
class StructuredRagAnswerGenerationProviderConfig:
    """Configuration for schema-enforced RAG answer generation."""

    model: str
    provider_name: str = "instructor"
    retry_policy: StructuredOutputRetryPolicy = StructuredOutputRetryPolicy()

    def __post_init__(self) -> None:
        _require_non_empty(self.model, "model")
        _require_non_empty(self.provider_name, "provider_name")


class StructuredRagAnswerGenerationProvider(RagAnswerGenerationProvider):
    """RAG answer provider backed by the canonical structured-output boundary."""

    def __init__(
        self,
        structured_output_provider: StructuredLlmProvider,
        config: StructuredRagAnswerGenerationProviderConfig,
    ) -> None:
        self._structured_output_provider = structured_output_provider
        self._config = config

    async def generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult:
        structured_request = StructuredLlmRequest[RagStructuredAnswer](
            request_id=request.request_id,
            prompt=_structured_prompt(request),
            system_prompt=_structured_system_prompt(request.policy_instructions),
            response_model=RagStructuredAnswer,
            schema_ref=StructuredOutputSchemaRef(
                STRUCTURED_RAG_ANSWER_SCHEMA_NAME,
                STRUCTURED_RAG_ANSWER_SCHEMA_VERSION,
            ),
            model=self._config.model,
            provider_name=self._config.provider_name,
            retry_policy=self._config.retry_policy,
            metadata={
                "request_metadata": dict(request.metadata),
                "citation_ids": list(request.citation_ids),
            },
        )
        structured_result = (
            await self._structured_output_provider.generate_structured_output(
                structured_request
            )
        )
        if not structured_result.success or structured_result.output is None:
            error_message = (
                structured_result.error_message or "structured RAG answer failed"
            )
            raise RuntimeError(error_message)

        structured_answer = structured_result.output
        _validate_structured_citations(
            structured_answer=structured_answer,
            allowed_citation_ids=request.citation_ids,
        )
        return RagAnswerGenerationResult(
            answer_text=structured_answer.answer_text,
            model=structured_result.model,
            provider_name=structured_result.provider_name,
            confidence_score=structured_answer.quality.confidence_score,
            metadata=_provider_metadata(
                request=request,
                structured_answer=structured_answer,
                attempts=structured_result.attempts,
                duration_seconds=structured_result.duration_seconds,
                result_metadata=structured_result.metadata,
            ),
        )


def _structured_system_prompt(policy_instructions: str) -> str:
    return (
        "/no_think\n"
        f"{policy_instructions}\n\n"
        "Return only a schema-valid JSON object matching RagStructuredAnswer. "
        "Do not include chain-of-thought, scratchpad, markdown, or analysis. "
        "Explain retrieved evidence; do not calculate authoritative scores, "
        "portfolio values, or risk decisions. "
        "Use citation ids only from the provided context payload. "
        "If the context is insufficient, explain the limitation and set "
        "quality.refusal_reason. Do not repeat raw context payloads. "
        "Keep answer_text concise unless the user explicitly asks for a long answer."
    )


def _structured_prompt(request: RagAnswerGenerationRequest) -> str:
    return (
        f"{request.user_prompt}\n\n"
        "Retrieved context JSON payload:\n"
        f"{request.context_payload}\n\n"
        "Required output fields:\n"
        "- answer_text: concise complete answer with supported inline citations "
        "such as [C1]; do not quote or dump the raw context payload\n"
        "- citations: objects with citation_id and claim_summary\n"
        "- quality.confidence_score: number from 0.0 to 1.0\n"
        "- quality.grounding_summary: concise grounding explanation\n"
        "- quality.limitations: relevant limitations, if any\n"
        "- quality.refusal_reason: reason if you cannot answer, otherwise null"
    )


def _validate_structured_citations(
    *,
    structured_answer: RagStructuredAnswer,
    allowed_citation_ids: tuple[str, ...],
) -> None:
    allowed = set(allowed_citation_ids)
    invalid = tuple(
        citation.citation_id
        for citation in structured_answer.citations
        if citation.citation_id not in allowed
    )
    if invalid:
        invalid_text = ", ".join(sorted(set(invalid)))
        raise ValueError(
            f"structured RAG answer cited unknown context ids: {invalid_text}."
        )


def _provider_metadata(
    *,
    request: RagAnswerGenerationRequest,
    structured_answer: RagStructuredAnswer,
    attempts: int,
    duration_seconds: float | None,
    result_metadata: JsonObject,
) -> JsonObject:
    return {
        "request_metadata": dict(request.metadata),
        "citation_ids": list(request.citation_ids),
        "structured_output_schema": STRUCTURED_RAG_ANSWER_SCHEMA_NAME,
        "structured_output_schema_version": STRUCTURED_RAG_ANSWER_SCHEMA_VERSION,
        "structured_output_attempts": attempts,
        "structured_output_duration_seconds": duration_seconds,
        "structured_answer": _structured_answer_metadata(structured_answer),
        "structured_output_metadata": dict(result_metadata),
    }


def _structured_answer_metadata(
    structured_answer: RagStructuredAnswer,
) -> JsonObject:
    return {
        "citations": [
            {
                "citation_id": citation.citation_id,
                "claim_summary": citation.claim_summary,
            }
            for citation in structured_answer.citations
        ],
        "grounding_summary": structured_answer.quality.grounding_summary,
        "limitations": list(structured_answer.quality.limitations),
        "refusal_reason": structured_answer.quality.refusal_reason,
    }


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
