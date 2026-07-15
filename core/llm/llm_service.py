from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from typing import Any

from core.llm.llm_gateway import LLMChatResponseFormat
from core.llm.llm_gateway import LLMGateway
from core.llm.llm_gateway import LLMJsonResult
from core.llm.llm_gateway import LLMTextResult


class LLMService:
    """Canonical async LLM application service boundary."""

    def __init__(
        self,
        gateway: LLMGateway,
        model: str,
        temperature: float = 0.2,
    ) -> None:
        self.gateway = gateway
        self.model = model
        self.temperature = temperature

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate a standard text response through the configured gateway."""

        result = await self.gateway.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=self.temperature,
        )
        return result.text

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Generate a structured JSON-object response through the gateway."""

        result = await self.gateway.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            temperature=self.temperature,
        )
        return dict(result.payload)

    async def chat(
        self,
        messages: Sequence[Mapping[str, str]],
        system_prompt: str | None = None,
        response_format: str | None = None,
    ) -> str | dict[str, Any]:
        """Run a chat completion and return text or JSON payload."""

        format_name: LLMChatResponseFormat = (
            "json" if response_format == "json" else "text"
        )
        result = await self.gateway.chat(
            messages=messages,
            system_prompt=system_prompt,
            model=self.model,
            temperature=self.temperature,
            response_format=format_name,
        )
        if isinstance(result, LLMJsonResult):
            return dict(result.payload)
        if isinstance(result, LLMTextResult):
            return result.text
        raise TypeError("LLM gateway returned an unsupported result type.")
