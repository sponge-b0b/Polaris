from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.clients.llm import LiteLlmGatewayClient
from integration.providers.rag.litellm_query_routing_provider import (
    LiteLlmRagQueryModelProvider,
)
from integration.providers.rag.query_routing_provider import RagQueryModelConfig
from integration.providers.rag.query_routing_provider import RagQueryModelOperation
from integration.providers.rag.query_routing_provider import RagQueryModelRequest

_MODEL_CONFIG = RagQueryModelConfig(
    query_rewrite_model="rewrite-model",
    adaptive_triage_model="triage-model",
    route_selection_model="router-model",
    hyde_model="hyde-model",
    structured_max_tokens=384,
    hyde_max_tokens=640,
)


class _FakeCompletionClient:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            id="chatcmpl-query",
            model=kwargs["model"],
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=' {"result": "ok"} '),
                )
            ],
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_model"),
    [
        (RagQueryModelOperation.REWRITE, "rewrite-model"),
        (RagQueryModelOperation.ADAPTIVE_TRIAGE, "triage-model"),
        (RagQueryModelOperation.ROUTE_SELECTION, "router-model"),
        (RagQueryModelOperation.HYDE, "hyde-model"),
    ],
)
async def test_litellm_query_provider_uses_explicit_operation_model(
    operation: RagQueryModelOperation,
    expected_model: str,
) -> None:
    completion_client = _FakeCompletionClient()
    provider = LiteLlmRagQueryModelProvider(
        LiteLlmGatewayClient(
            completion_client=completion_client,
            default_model="default-model",
        ),
        model_config=_MODEL_CONFIG,
    )

    result = await provider.generate_structured(_request(operation))

    assert result.operation is operation
    assert result.payload == {"result": "ok"}
    assert result.model == expected_model
    assert result.provider_name == "litellm"
    assert result.duration_ms >= 0.0
    assert result.success is True
    assert completion_client.calls == [
        {
            "model": expected_model,
            "messages": [
                {"role": "system", "content": "Return strict JSON."},
                {"role": "user", "content": "Process this query."},
            ],
            "temperature": 0.0,
            "max_tokens": 640 if operation is RagQueryModelOperation.HYDE else 384,
            "response_format": {"type": "json_object"},
        }
    ]


@pytest.mark.asyncio
async def test_litellm_query_provider_records_gateway_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    provider = LiteLlmRagQueryModelProvider(
        LiteLlmGatewayClient(
            completion_client=_FakeCompletionClient(),
            default_model="default-model",
        ),
        model_config=_MODEL_CONFIG,
        telemetry=IntegrationTelemetry(observability_manager=observability),
    )

    await provider.generate_structured(_request(RagQueryModelOperation.ROUTE_SELECTION))

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.success is True
    assert event.attributes["provider_name"] == "litellm"
    assert event.attributes["operation"] == "route_selection"
    assert event.attributes["semantic_operation"] == "route_selection"
    assert event.attributes["configured_model"] == "router-model"
    assert event.attributes["model"] == "router-model"
    assert event.attributes["query_request_id"] == "query-provider-1"


@pytest.mark.asyncio
async def test_litellm_query_provider_records_failed_gateway_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    provider = LiteLlmRagQueryModelProvider(
        LiteLlmGatewayClient(
            completion_client=_FakeCompletionClient(error=RuntimeError("gateway down")),
            default_model="default-model",
        ),
        model_config=_MODEL_CONFIG,
        telemetry=IntegrationTelemetry(observability_manager=observability),
    )

    with pytest.raises(RuntimeError, match="LiteLLM gateway chat completion failed"):
        await provider.generate_structured(_request(RagQueryModelOperation.HYDE))

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.success is False
    assert event.attributes["provider_name"] == "litellm"
    assert event.attributes["operation"] == "hyde"
    assert event.payload["error_type"] == "LiteLlmGatewayError"


def _request(operation: RagQueryModelOperation) -> RagQueryModelRequest:
    return RagQueryModelRequest(
        request_id="query-provider-1",
        operation=operation,
        system_prompt="Return strict JSON.",
        user_prompt="Process this query.",
    )
