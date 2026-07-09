from __future__ import annotations

import asyncio

from core.llm.ollama_client import OllamaClient
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationProvider,
)
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationRequest,
)
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationResult,
)


class OllamaRagAnswerGenerationProvider(RagAnswerGenerationProvider):
    """
    Platform-facing RAG answer provider backed by the canonical Ollama client.
    """

    def __init__(
        self,
        client: OllamaClient,
        telemetry: IntegrationTelemetry | None = None,
        temperature: float = 0.2,
    ) -> None:
        self._client = client
        self._telemetry = telemetry
        self._temperature = temperature

    async def generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult:
        return await record_provider_call(
            self._telemetry,
            self.__class__.__name__,
            "generate_answer",
            lambda: self._generate_answer(
                request,
            ),
        )

    async def _generate_answer(
        self,
        request: RagAnswerGenerationRequest,
    ) -> RagAnswerGenerationResult:
        prompt = (
            f"{request.user_prompt}\n\n"
            "Retrieved context JSON payload:\n"
            f"{request.context_payload}"
        )
        answer_text = await asyncio.to_thread(
            self._client.generate,
            prompt=prompt,
            system_prompt=request.policy_instructions,
            temperature=self._temperature,
        )
        return RagAnswerGenerationResult(
            answer_text=answer_text,
            model=self._client.llm_model,
            provider_name="ollama",
            metadata={
                "request_metadata": dict(request.metadata),
                "citation_ids": list(request.citation_ids),
            },
        )
