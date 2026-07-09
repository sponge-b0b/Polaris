from __future__ import annotations

from typing import Any
from typing import cast

import pytest

from core.llm.ollama_client import OllamaClient
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.providers.rag.ollama_query_routing_provider import (
    OllamaRagQueryModelProvider,
)
from integration.providers.rag.query_routing_provider import RagQueryModelConfig
from integration.providers.rag.query_routing_provider import RagQueryModelOperation
from integration.providers.rag.query_routing_provider import RagQueryModelRequest

_MODEL_CONFIG = RagQueryModelConfig(
    query_rewrite_model="rewrite-model",
    adaptive_triage_model="triage-model",
    route_selection_model="router-model",
    hyde_model="hyde-model",
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
async def test_ollama_query_provider_uses_explicit_operation_model(
    operation: RagQueryModelOperation,
    expected_model: str,
) -> None:
    client = FakeOllamaClient()
    provider = OllamaRagQueryModelProvider(
        cast(OllamaClient, client),
        model_config=_MODEL_CONFIG,
    )
    request = _request(operation)

    result = await provider.generate_structured(request)

    assert result.operation is operation
    assert result.payload == {"result": "ok"}
    assert result.model == expected_model
    assert result.provider_name == "ollama"
    assert result.duration_ms >= 0.0
    assert result.success is True
    assert client.calls == [
        {
            "prompt": "Process this query.",
            "model": expected_model,
            "system_prompt": "Return strict JSON.",
            "temperature": 0.0,
        }
    ]


@pytest.mark.asyncio
async def test_ollama_query_provider_records_actual_model_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    telemetry = IntegrationTelemetry(observability_manager=observability)
    provider = OllamaRagQueryModelProvider(
        cast(OllamaClient, FakeOllamaClient()),
        model_config=_MODEL_CONFIG,
        telemetry=telemetry,
    )

    await provider.generate_structured(_request(RagQueryModelOperation.ROUTE_SELECTION))

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.success is True
    assert event.duration_seconds is not None
    assert event.duration_seconds >= 0.0
    assert event.attributes["provider_name"] == "ollama"
    assert event.attributes["operation"] == "route_selection"
    assert event.attributes["semantic_operation"] == "route_selection"
    assert event.attributes["configured_model"] == "router-model"
    assert event.attributes["model"] == "router-model"
    assert event.attributes["query_request_id"] == "query-provider-1"


@pytest.mark.asyncio
async def test_ollama_query_provider_records_failed_model_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    telemetry = IntegrationTelemetry(observability_manager=observability)
    provider = OllamaRagQueryModelProvider(
        cast(OllamaClient, FakeOllamaClient(error=RuntimeError("model unavailable"))),
        model_config=_MODEL_CONFIG,
        telemetry=telemetry,
    )

    with pytest.raises(RuntimeError, match="model unavailable"):
        await provider.generate_structured(_request(RagQueryModelOperation.HYDE))

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.event_type == "integration.provider.call"
    assert event.success is False
    assert event.duration_seconds is not None
    assert event.duration_seconds >= 0.0
    assert event.attributes["provider_name"] == "ollama"
    assert event.attributes["operation"] == "hyde"
    assert event.attributes["semantic_operation"] == "hyde"
    assert event.attributes["configured_model"] == "hyde-model"
    assert event.payload["error_type"] == "RuntimeError"
    assert event.payload["error_message"] == "model unavailable"


@pytest.mark.parametrize(
    "field_name",
    [
        "query_rewrite_model",
        "adaptive_triage_model",
        "route_selection_model",
        "hyde_model",
    ],
)
def test_query_model_config_rejects_empty_model_names(field_name: str) -> None:
    values = {
        "query_rewrite_model": "rewrite-model",
        "adaptive_triage_model": "triage-model",
        "route_selection_model": "router-model",
        "hyde_model": "hyde-model",
    }
    values[field_name] = " "

    with pytest.raises(ValueError, match=field_name):
        RagQueryModelConfig(**values)


def _request(operation: RagQueryModelOperation) -> RagQueryModelRequest:
    return RagQueryModelRequest(
        request_id="query-provider-1",
        operation=operation,
        system_prompt="Return strict JSON.",
        user_prompt="Process this query.",
    )


class FakeOllamaClient:
    llm_model = "implicit-default-must-not-be-used"

    def __init__(self, *, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._error = error

    def generate_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return {"result": "ok"}
