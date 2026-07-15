from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from integration.clients.llm import LITELLM_PROVIDER_NAME
from integration.clients.llm import LiteLlmGatewayChatRequest
from integration.clients.llm import LiteLlmGatewayClient
from integration.clients.llm import LiteLlmGatewayMessage
from integration.clients.llm import LiteLlmGatewayResponseError
from integration.clients.llm import LiteLlmGatewayTimeoutError


class _FakeCompletionClient:
    def __init__(
        self, response: Any | None = None, error: Exception | None = None
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


def _response(
    *,
    content: str,
    model: str = "qwen3.5:4b",
    response_id: str = "chatcmpl-test",
    finish_reason: str = "stop",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=response_id,
        model=model,
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(content=content),
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=7,
            completion_tokens=11,
            total_tokens=18,
        ),
    )


@pytest.mark.asyncio
async def test_generate_text_maps_request_and_sanitized_result() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content=" Gateway answer. ")
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    result = await client.generate_text(
        prompt="What changed?",
        system_prompt="Answer concisely.",
        temperature=0.3,
        max_tokens=256,
        metadata={"request_id": "rag-1"},
    )

    assert result.text == "Gateway answer."
    assert result.model == "qwen3.5:4b"
    assert result.provider_name == LITELLM_PROVIDER_NAME
    assert result.metadata == {
        "requested_model": "qwen3.5:4b",
        "response_format": "text",
        "request_metadata": {"request_id": "rag-1"},
        "response_id": "chatcmpl-test",
        "finish_reason": "stop",
        "usage": {
            "prompt_tokens": 7,
            "completion_tokens": 11,
            "total_tokens": 18,
        },
    }
    assert completion_client.calls == [
        {
            "model": "qwen3.5:4b",
            "messages": [
                {"role": "system", "content": "Answer concisely."},
                {"role": "user", "content": "What changed?"},
            ],
            "temperature": 0.3,
            "max_tokens": 256,
        }
    ]


@pytest.mark.asyncio
async def test_generate_json_requests_json_object_and_parses_payload() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content=' {"route": "vector", "confidence": 0.8} ')
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    result = await client.generate_json(prompt="Classify this query.")

    assert result.payload == {"route": "vector", "confidence": 0.8}
    assert result.model == "qwen3.5:4b"
    assert completion_client.calls[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_generate_json_rejects_invalid_json_object_content() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content='["not-object"]')
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    with pytest.raises(
        LiteLlmGatewayResponseError, match="JSON response must be an object"
    ):
        await client.generate_json(prompt="Return JSON.")


@pytest.mark.asyncio
async def test_chat_normalizes_timeout_errors() -> None:
    completion_client = _FakeCompletionClient(error=TimeoutError("boom"))
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    with pytest.raises(LiteLlmGatewayTimeoutError, match="timed out"):
        await client.chat(
            LiteLlmGatewayChatRequest(
                model="qwen3.5:4b",
                messages=(LiteLlmGatewayMessage(role="user", content="hello"),),
            )
        )


@pytest.mark.asyncio
async def test_chat_failure_message_does_not_leak_provider_secret() -> None:
    completion_client = _FakeCompletionClient(
        error=RuntimeError("provider failed with token sensitive-test-value")
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    with pytest.raises(RuntimeError) as exc_info:
        await client.chat(
            LiteLlmGatewayChatRequest(
                model="qwen3.5:4b",
                messages=(LiteLlmGatewayMessage(role="user", content="hello"),),
            )
        )

    assert str(exc_info.value) == "LiteLLM gateway chat completion failed."
    assert "sensitive-test-value" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_chat_rejects_missing_choice_content_without_raw_response_leak() -> None:
    completion_client = _FakeCompletionClient(
        response=SimpleNamespace(
            id="chatcmpl-test",
            model="qwen3.5:4b",
            choices=[SimpleNamespace(message=SimpleNamespace(content=""))],
        )
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    with pytest.raises(LiteLlmGatewayResponseError, match="text content"):
        await client.generate_text(prompt="hello")


@pytest.mark.asyncio
async def test_chat_request_validates_model_messages_and_max_tokens() -> None:
    with pytest.raises(ValueError, match="model"):
        LiteLlmGatewayChatRequest(
            model=" ",
            messages=(LiteLlmGatewayMessage(role="user", content="hello"),),
        )

    with pytest.raises(ValueError, match="messages"):
        LiteLlmGatewayChatRequest(model="qwen3.5:4b", messages=())

    with pytest.raises(ValueError, match="max_tokens"):
        LiteLlmGatewayChatRequest(
            model="qwen3.5:4b",
            messages=(LiteLlmGatewayMessage(role="user", content="hello"),),
            max_tokens=0,
        )
