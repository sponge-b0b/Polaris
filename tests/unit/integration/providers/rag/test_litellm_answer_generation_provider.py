from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from core.telemetry.observability.observability_manager import ObservabilityManager
from core.telemetry.sinks.telemetry_sink import InMemoryTelemetrySink
from integration.clients.llm import LiteLlmGatewayClient
from integration.providers.rag.answer_generation_provider import (
    RagAnswerGenerationRequest,
)
from integration.providers.rag.litellm_answer_generation_provider import (
    LiteLlmRagAnswerGenerationProvider,
)


class _FakeCompletionClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            model=kwargs["model"],
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content="Breadth improved [C1]."),
                )
            ],
        )


@pytest.mark.asyncio
async def test_litellm_answer_provider_generates_text_with_context_payload() -> None:
    completion_client = _FakeCompletionClient()
    provider = LiteLlmRagAnswerGenerationProvider(
        LiteLlmGatewayClient(
            completion_client=completion_client,
            default_model="default-model",
        ),
        model="synthesis-model",
        max_tokens=1536,
    )

    result = await provider.generate_answer(_request())

    assert result.answer_text == "Breadth improved [C1]."
    assert result.model == "synthesis-model"
    assert result.provider_name == "litellm"
    assert result.metadata["citation_ids"] == ["C1"]
    assert completion_client.calls == [
        {
            "model": "synthesis-model",
            "messages": [
                {"role": "system", "content": "Use retrieved context only."},
                {
                    "role": "user",
                    "content": (
                        "Answer using citations.\n\n"
                        "Retrieved context JSON payload:\n"
                        '{"contexts": [{"citation_id": "C1"}]}'
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": 1536,
        }
    ]


@pytest.mark.asyncio
async def test_litellm_answer_provider_records_gateway_telemetry() -> None:
    sink = InMemoryTelemetrySink()
    observability = ObservabilityManager()
    observability.add_sink(sink)
    provider = LiteLlmRagAnswerGenerationProvider(
        LiteLlmGatewayClient(
            completion_client=_FakeCompletionClient(),
            default_model="default-model",
        ),
        model="synthesis-model",
        telemetry=IntegrationTelemetry(observability_manager=observability),
    )

    await provider.generate_answer(_request())

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.success is True
    assert event.attributes["provider_name"] == "litellm"
    assert event.attributes["operation"] == "generate_answer"
    assert event.attributes["configured_model"] == "synthesis-model"
    assert event.attributes["model"] == "synthesis-model"
    assert event.attributes["rag_request_id"] == "rag-answer-1"


def _request() -> RagAnswerGenerationRequest:
    return RagAnswerGenerationRequest(
        request_id="rag-answer-1",
        query="How is breadth?",
        policy_instructions="Use retrieved context only.",
        user_prompt="Answer using citations.",
        context_payload='{"contexts": [{"citation_id": "C1"}]}',
        citation_ids=("C1",),
        metadata={"source": "unit-test"},
    )
