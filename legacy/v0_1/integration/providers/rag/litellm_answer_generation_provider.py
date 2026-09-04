from __future__ import annotations

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.llm import LITELLM_PROVIDER_NAME, LiteLlmGatewayClient
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationProvider,
    RagAnswerGenerationRequest,
    RagAnswerGenerationResult,
)


class LiteLlmRagAnswerGenerationProvider(RagAnswerGenerationProvider):
    """RAG answer-generation provider backed by the LiteLLM gateway."""

    def __init__(
        self,
        client: LiteLlmGatewayClient,
        model: str,
        telemetry: IntegrationTelemetry | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model cannot be empty.")
        if max_tokens is not None and max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0.")
        self._client = client
        self._model = model
        self._telemetry = telemetry
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult:
        return await record_provider_call(
            self._telemetry,
            LITELLM_PROVIDER_NAME,
            "generate_answer",
            lambda: self._generate_answer(request),
            attributes={
                "semantic_operation": "generate_answer",
                "configured_model": self._model,
                "model": self._model,
                "rag_request_id": request.request_id,
            },
        )

    async def _generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult:
        result = await self._client.generate_text(
            prompt=_answer_prompt(request),
            model=self._model,
            system_prompt=request.policy_instructions,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            metadata={
                "request_id": request.request_id,
                "query": request.query,
                "request_metadata": dict(request.metadata),
                "citation_ids": list(request.citation_ids),
            },
        )
        return RagAnswerGenerationResult(
            answer_text=result.text,
            model=self._model,
            provider_name=LITELLM_PROVIDER_NAME,
            metadata={
                "request_metadata": dict(request.metadata),
                "citation_ids": list(request.citation_ids),
                "gateway_metadata": dict(result.metadata),
            },
        )


def _answer_prompt(request: RagAnswerGenerationRequest) -> str:
    return (
        f"{request.user_prompt}\n\n"
        "Retrieved context JSON payload:\n"
        f"{request.context_payload}"
    )
