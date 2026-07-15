from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal
from typing import Protocol

LLMChatResponseFormat = Literal["text", "json"]
LLMMessage = Mapping[str, str]
LLMMetadata = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class LLMTextResult:
    """Typed text response returned by the canonical LLM gateway boundary."""

    text: str
    model: str
    provider_name: str
    metadata: LLMMetadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMJsonResult:
    """Typed JSON-object response returned by the canonical LLM gateway boundary."""

    payload: Mapping[str, Any]
    model: str
    provider_name: str
    metadata: LLMMetadata = field(default_factory=dict)


class LLMGateway(Protocol):
    """Core protocol for async LLM gateway implementations."""

    async def generate_text(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        metadata: LLMMetadata | None = None,
    ) -> LLMTextResult: ...

    async def generate_json(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        metadata: LLMMetadata | None = None,
    ) -> LLMJsonResult: ...

    async def chat(
        self,
        *,
        messages: Sequence[LLMMessage],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        response_format: LLMChatResponseFormat = "text",
        metadata: LLMMetadata | None = None,
    ) -> LLMTextResult | LLMJsonResult: ...
