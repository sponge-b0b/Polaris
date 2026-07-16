from __future__ import annotations

from time import perf_counter

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.clients.llm import LITELLM_PROVIDER_NAME
from integration.clients.llm import LiteLlmGatewayClient
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.quality_evaluation_provider import RagQualityModelConfig
from integration.providers.rag.quality_evaluation_provider import (
    RagQualityModelProvider,
)
from integration.providers.rag.quality_evaluation_provider import RagQualityModelRequest
from integration.providers.rag.quality_evaluation_provider import RagQualityModelResult


class LiteLlmRagQualityModelProvider(RagQualityModelProvider):
    """Structured CRAG and Self-RAG provider backed by the LiteLLM gateway."""

    def __init__(
        self,
        client: LiteLlmGatewayClient,
        model_config: RagQualityModelConfig,
        telemetry: IntegrationTelemetry | None = None,
        temperature: float = 0.0,
    ) -> None:
        self._client = client
        self._model_config = model_config
        self._telemetry = telemetry
        self._temperature = temperature

    async def generate_structured(
        self,
        request: RagQualityModelRequest,
    ) -> RagQualityModelResult:
        model = self._model_config.model_for(request.operation)
        return await record_provider_call(
            self._telemetry,
            LITELLM_PROVIDER_NAME,
            request.operation.value,
            lambda: self._generate_structured(request, model),
            attributes={
                "semantic_operation": request.operation.value,
                "configured_model": model,
                "model": model,
                "rag_request_id": request.request_id,
            },
        )

    async def _generate_structured(
        self,
        request: RagQualityModelRequest,
        model: str,
    ) -> RagQualityModelResult:
        started_at = perf_counter()
        result = await self._client.generate_json(
            prompt=request.user_prompt,
            model=model,
            system_prompt=request.system_prompt,
            temperature=self._temperature,
            max_tokens=self._model_config.max_tokens_for(request.operation),
            metadata={
                "request_id": request.request_id,
                "operation": request.operation.value,
                "request_metadata": dict(request.metadata),
            },
        )
        return RagQualityModelResult(
            operation=request.operation,
            payload=result.payload,
            model=model,
            provider_name=LITELLM_PROVIDER_NAME,
            duration_ms=(perf_counter() - started_at) * 1000.0,
            success=True,
        )
