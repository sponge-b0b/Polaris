from __future__ import annotations

import json
from collections.abc import Mapping
from collections.abc import Sequence
from typing import cast

from core.llm.llm_gateway import LLMChatResponseFormat
from core.llm.llm_gateway import LLMGateway
from core.llm.llm_gateway import LLMJsonResult
from core.llm.llm_gateway import LLMMessage
from core.llm.llm_gateway import LLMMetadata
from core.llm.llm_gateway import LLMTextResult
from integration.clients.llm.litellm_gateway_client import LiteLlmGatewayChatRequest
from integration.clients.llm.litellm_gateway_client import LiteLlmGatewayClient
from integration.clients.llm.litellm_gateway_client import LiteLlmGatewayMessage
from integration.clients.llm.litellm_gateway_client import LiteLlmGatewayRole

_ALLOWED_ROLES = frozenset({"system", "user", "assistant"})


class LiteLlmCoreGatewayAdapter(LLMGateway):
    """Adapts the LiteLLM gateway client to the core LLMGateway protocol."""

    def __init__(self, client: LiteLlmGatewayClient) -> None:
        self._client = client

    async def generate_text(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        metadata: LLMMetadata | None = None,
    ) -> LLMTextResult:
        result = await self._client.generate_text(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            metadata=dict(metadata or {}),
        )
        return LLMTextResult(
            text=result.text,
            model=result.model,
            provider_name=result.provider_name,
            metadata=result.metadata,
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
        result = await self._client.generate_json(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            metadata=dict(metadata or {}),
        )
        return LLMJsonResult(
            payload=result.payload,
            model=result.model,
            provider_name=result.provider_name,
            metadata=result.metadata,
        )

    async def chat(
        self,
        *,
        messages: Sequence[LLMMessage],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        response_format: LLMChatResponseFormat = "text",
        metadata: LLMMetadata | None = None,
    ) -> LLMTextResult | LLMJsonResult:
        chat_messages = _to_litellm_messages(
            messages=messages,
            system_prompt=system_prompt,
        )
        request = LiteLlmGatewayChatRequest(
            model=model or self._client.default_model,
            messages=chat_messages,
            temperature=temperature,
            response_format="json_object" if response_format == "json" else "text",
            metadata=dict(metadata or {}),
        )
        result = await self._client.chat(request)
        if response_format == "json":
            payload = json.loads(result.text)
            if not isinstance(payload, dict):
                raise ValueError("LLM JSON chat response must be an object.")
            return LLMJsonResult(
                payload=payload,
                model=result.model,
                provider_name=result.provider_name,
                metadata=result.metadata,
            )

        return LLMTextResult(
            text=result.text,
            model=result.model,
            provider_name=result.provider_name,
            metadata=result.metadata,
        )


def _to_litellm_messages(
    *,
    messages: Sequence[Mapping[str, str]],
    system_prompt: str | None,
) -> tuple[LiteLlmGatewayMessage, ...]:
    converted: list[LiteLlmGatewayMessage] = []
    if system_prompt is not None and system_prompt.strip():
        converted.append(LiteLlmGatewayMessage(role="system", content=system_prompt))
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role not in _ALLOWED_ROLES:
            raise ValueError(f"Unsupported LLM message role: {role!r}.")
        if content is None or not content.strip():
            raise ValueError("LLM message content cannot be empty.")
        converted.append(
            LiteLlmGatewayMessage(
                role=cast(LiteLlmGatewayRole, role),
                content=content,
            )
        )
    if not converted:
        raise ValueError("messages cannot be empty.")
    return tuple(converted)
