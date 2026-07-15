from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

import pytest

from core.llm.llm_gateway import LLMChatResponseFormat
from core.llm.llm_gateway import LLMJsonResult
from core.llm.llm_gateway import LLMMessage
from core.llm.llm_gateway import LLMMetadata
from core.llm.llm_gateway import LLMTextResult
from core.llm.llm_service import LLMService


class _Gateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        metadata: LLMMetadata | None = None,
    ) -> LLMTextResult:
        self.calls.append(
            {
                "method": "generate_text",
                "prompt": prompt,
                "model": model,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "metadata": metadata,
            }
        )
        return LLMTextResult(
            text="text answer",
            model=model or "missing",
            provider_name="litellm",
        )

    async def generate_json(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        metadata: LLMMetadata | None = None,
    ) -> LLMJsonResult:
        self.calls.append(
            {
                "method": "generate_json",
                "prompt": prompt,
                "model": model,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "metadata": metadata,
            }
        )
        return LLMJsonResult(
            payload={"answer": "json answer"},
            model=model or "missing",
            provider_name="litellm",
        )

    async def chat(
        self,
        *,
        messages: Sequence[LLMMessage],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        response_format: LLMChatResponseFormat = "text",
        metadata: Mapping[str, Any] | None = None,
    ) -> LLMTextResult | LLMJsonResult:
        self.calls.append(
            {
                "method": "chat",
                "messages": tuple(messages),
                "model": model,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "response_format": response_format,
                "metadata": metadata,
            }
        )
        if response_format == "json":
            return LLMJsonResult(
                payload={"classification": "risk_on"},
                model=model or "missing",
                provider_name="litellm",
            )
        return LLMTextResult(
            text="chat answer",
            model=model or "missing",
            provider_name="litellm",
        )


@pytest.mark.asyncio
async def test_llm_service_generates_text_through_gateway() -> None:
    gateway = _Gateway()
    service = LLMService(gateway=gateway, model="qwen3.5:4b", temperature=0.3)

    result = await service.generate_text("Explain market risk.", "system")

    assert result == "text answer"
    assert gateway.calls == [
        {
            "method": "generate_text",
            "prompt": "Explain market risk.",
            "model": "qwen3.5:4b",
            "system_prompt": "system",
            "temperature": 0.3,
            "metadata": None,
        }
    ]


@pytest.mark.asyncio
async def test_llm_service_generates_json_through_gateway() -> None:
    gateway = _Gateway()
    service = LLMService(gateway=gateway, model="qwen3.5:4b")

    result = await service.generate_json("Return JSON.")

    assert result == {"answer": "json answer"}
    assert gateway.calls[0]["method"] == "generate_json"
    assert gateway.calls[0]["model"] == "qwen3.5:4b"


@pytest.mark.asyncio
async def test_llm_service_chat_supports_text_and_json_formats() -> None:
    gateway = _Gateway()
    service = LLMService(gateway=gateway, model="qwen3.5:4b")

    text_result = await service.chat([{"role": "user", "content": "hello"}])
    json_result = await service.chat(
        [{"role": "user", "content": "classify"}],
        response_format="json",
    )

    assert text_result == "chat answer"
    assert json_result == {"classification": "risk_on"}
    assert gateway.calls[0]["response_format"] == "text"
    assert gateway.calls[1]["response_format"] == "json"
