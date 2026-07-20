from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest

from integration.clients.llm import (
    LITELLM_PROVIDER_NAME,
    LiteLlmGatewayChatRequest,
    LiteLlmGatewayClient,
    LiteLlmGatewayMessage,
    LiteLlmGatewayModelFallbackError,
    LiteLlmGatewayOperationsPolicy,
    LiteLlmGatewayReasoningTraceError,
    LiteLlmGatewayRequestBudgetError,
    LiteLlmGatewayResponseError,
    LiteLlmGatewayTimeoutError,
)


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
        "response_model": "qwen3.5:4b",
        "response_format": "text",
        "request_metadata": {"request_id": "rag-1"},
        "effective_max_tokens": 256,
        "model_fallback_detected": False,
        "operations_policy": {
            "max_concurrency": 1,
            "timeout_seconds": 60.0,
            "request_budget_tokens": 4096,
            "model_fallback_policy": "reject",
        },
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
async def test_generate_text_strips_model_internal_reasoning_before_publication() -> (
    None
):
    completion_client = _FakeCompletionClient(
        response=_response(
            content="<think>hidden deliberation</think>\nPublished answer."
        )
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    result = await client.generate_text(prompt="Return a concise answer.")

    assert result.text == "Published answer."
    assert "hidden deliberation" not in result.text
    assert "hidden deliberation" not in str(result.metadata)
    safety = cast(dict[str, Any], result.metadata["reasoning_trace_safety"])
    assert safety["detected"] is True
    assert safety["action"] == "stripped"
    assert safety["published_text_changed"] is True


@pytest.mark.asyncio
async def test_generate_text_fails_closed_on_unsafe_reasoning_trace() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content="<think>hidden deliberation without closure")
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    with pytest.raises(LiteLlmGatewayReasoningTraceError) as exc_info:
        await client.generate_text(prompt="Return a concise answer.")

    assert "hidden deliberation" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_generate_json_fails_closed_when_reasoning_precedes_json() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content='<think>hidden</think>\n{"ok": true}')
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    with pytest.raises(LiteLlmGatewayReasoningTraceError) as exc_info:
        await client.generate_json(prompt="Return JSON only.")

    assert "hidden" not in str(exc_info.value)


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

    assert str(exc_info.value) == (
        "LiteLLM gateway chat completion failed for model "
        "alias/capability 'qwen3.5:4b'."
    )
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


@pytest.mark.asyncio
async def test_generate_text_rejects_empty_model_without_fallback() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content="should not be called", model="default-model")
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="default-model",
    )

    with pytest.raises(ValueError, match="model cannot be empty"):
        await client.generate_text(prompt="hello", model=" ")

    assert completion_client.calls == []


@pytest.mark.asyncio
async def test_chat_rejects_silent_model_fallback_by_default() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content="answer", model="unexpected-model")
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="requested-alias",
    )

    with pytest.raises(
        LiteLlmGatewayModelFallbackError,
        match="requested model alias/capability 'requested-alias'",
    ):
        await client.generate_text(prompt="hello")


@pytest.mark.asyncio
async def test_chat_can_report_model_fallback_when_policy_allows_it() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content="answer", model="backend-model")
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="requested-alias",
        operations_policy=LiteLlmGatewayOperationsPolicy(
            reject_model_fallback=False,
        ),
    )

    result = await client.generate_text(prompt="hello")

    assert result.model == "backend-model"
    assert result.metadata["requested_model"] == "requested-alias"
    assert result.metadata["response_model"] == "backend-model"
    assert result.metadata["model_fallback_detected"] is True
    operations_policy = cast(dict[str, Any], result.metadata["operations_policy"])
    assert operations_policy["model_fallback_policy"] == "report"


@pytest.mark.asyncio
async def test_chat_rejects_request_over_configured_budget() -> None:
    completion_client = _FakeCompletionClient(response=_response(content="unused"))
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
        operations_policy=LiteLlmGatewayOperationsPolicy(request_budget_tokens=128),
    )

    with pytest.raises(
        LiteLlmGatewayRequestBudgetError,
        match="requested max_tokens=256",
    ):
        await client.generate_text(prompt="hello", max_tokens=256)

    assert completion_client.calls == []


@pytest.mark.asyncio
async def test_gateway_applies_default_budget_when_max_tokens_is_missing() -> None:
    completion_client = _FakeCompletionClient(
        response=_response(content='{"ok": true}')
    )
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
        operations_policy=LiteLlmGatewayOperationsPolicy(request_budget_tokens=777),
    )

    result = await client.generate_json(prompt="Return JSON.")

    assert result.metadata["effective_max_tokens"] == 777
    assert completion_client.calls[0]["max_tokens"] == 777


class _ConcurrencyTrackingCompletionClient:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def create(self, **kwargs: Any) -> Any:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return _response(content="answer", model=kwargs["model"])


@pytest.mark.asyncio
async def test_gateway_defaults_to_serial_local_model_execution() -> None:
    completion_client = _ConcurrencyTrackingCompletionClient()
    client = LiteLlmGatewayClient(
        completion_client=completion_client,
        default_model="qwen3.5:4b",
    )

    await asyncio.gather(
        client.generate_text(prompt="one"),
        client.generate_text(prompt="two"),
    )

    assert client.operations_policy.max_concurrency == 1
    assert completion_client.max_active == 1
