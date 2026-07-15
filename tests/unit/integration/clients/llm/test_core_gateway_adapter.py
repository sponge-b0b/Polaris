from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from core.llm.llm_gateway import LLMJsonResult
from core.llm.llm_gateway import LLMTextResult
from integration.clients.llm import LiteLlmCoreGatewayAdapter
from integration.clients.llm import LiteLlmGatewayClient


class _FakeCompletionClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return SimpleNamespace(
            id="chatcmpl-core",
            model=kwargs["model"],
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content=self.content),
                )
            ],
        )


@pytest.mark.asyncio
async def test_adapter_maps_text_chat_to_litellm_client() -> None:
    completion_client = _FakeCompletionClient(" Answer text. ")
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )
    adapter = LiteLlmCoreGatewayAdapter(client)

    result = await adapter.chat(
        messages=[{"role": "user", "content": "What changed?"}],
        system_prompt="Answer professionally.",
        model="qwen3.5:4b",
        temperature=0.4,
    )

    assert isinstance(result, LLMTextResult)
    assert result.text == "Answer text."
    assert result.provider_name == "litellm"
    assert completion_client.calls == [
        {
            "model": "qwen3.5:4b",
            "messages": [
                {"role": "system", "content": "Answer professionally."},
                {"role": "user", "content": "What changed?"},
            ],
            "temperature": 0.4,
        }
    ]


@pytest.mark.asyncio
async def test_adapter_maps_json_chat_to_typed_json_result() -> None:
    completion_client = _FakeCompletionClient('{"route": "hybrid", "confidence": 0.9}')
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )
    adapter = LiteLlmCoreGatewayAdapter(client)

    result = await adapter.chat(
        messages=[{"role": "user", "content": "Route query."}],
        response_format="json",
    )

    assert isinstance(result, LLMJsonResult)
    assert result.payload == {"route": "hybrid", "confidence": 0.9}
    assert completion_client.calls[0]["response_format"] == {"type": "json_object"}
    assert completion_client.calls[0]["model"] == "qwen3.5:4b"


@pytest.mark.asyncio
async def test_adapter_rejects_invalid_chat_message_role() -> None:
    client = LiteLlmGatewayClient(
        completion_client=_FakeCompletionClient("unused"),
        default_model="qwen3.5:4b",
    )
    adapter = LiteLlmCoreGatewayAdapter(client)

    with pytest.raises(ValueError, match="Unsupported LLM message role"):
        await adapter.chat(messages=[{"role": "tool", "content": "bad"}])
