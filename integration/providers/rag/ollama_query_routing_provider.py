from __future__ import annotations

import asyncio

from time import perf_counter

from core.llm.ollama_client import OllamaClient
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.provider_telemetry import record_provider_call
from integration.providers.rag.query_routing_provider import RagQueryModelConfig
from integration.providers.rag.query_routing_provider import RagQueryModelProvider
from integration.providers.rag.query_routing_provider import RagQueryModelRequest
from integration.providers.rag.query_routing_provider import RagQueryModelResult


class OllamaRagQueryModelProvider(RagQueryModelProvider):
    """Structured query-intelligence provider backed by the canonical Ollama client."""

    def __init__(
        self,
        client: OllamaClient,
        model_config: RagQueryModelConfig,
        telemetry: IntegrationTelemetry | None = None,
        temperature: float = 0.0,
    ) -> None:
        self._client = client
        self._model_config = model_config
        self._telemetry = telemetry
        self._temperature = temperature

    async def generate_structured(
        self,
        request: RagQueryModelRequest,
    ) -> RagQueryModelResult:
        model = self._model_config.model_for(request.operation)
        return await record_provider_call(
            self._telemetry,
            "ollama",
            request.operation.value,
            lambda: self._generate_structured(request, model),
            attributes={
                "semantic_operation": request.operation.value,
                "configured_model": model,
                "model": model,
                "query_request_id": request.request_id,
            },
        )

    async def _generate_structured(
        self,
        request: RagQueryModelRequest,
        model: str,
    ) -> RagQueryModelResult:
        started_at = perf_counter()
        payload = await asyncio.to_thread(
            self._client.generate_json,
            prompt=request.user_prompt,
            model=model,
            system_prompt=request.system_prompt,
            temperature=self._temperature,
        )
        return RagQueryModelResult(
            operation=request.operation,
            payload=payload,
            model=model,
            provider_name="ollama",
            duration_ms=(perf_counter() - started_at) * 1000.0,
            success=True,
        )
