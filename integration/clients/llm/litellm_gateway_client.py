from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, cast

from config.settings import Settings
from core.storage.persistence.rag import JsonObject

LiteLlmGatewayRole = Literal["system", "user", "assistant"]
LiteLlmResponseFormat = Literal["text", "json_object"]

LITELLM_PROVIDER_NAME = "litellm"
_LOCAL_DEVELOPMENT_API_KEY = "polaris-local-dev-key"
_TIMEOUT_ERROR_NAMES = frozenset(
    {
        "APITimeoutError",
        "ReadTimeout",
        "Timeout",
        "TimeoutError",
        "TimeoutException",
    }
)


class LiteLlmGatewayError(RuntimeError):
    """Base error raised by the LiteLLM gateway client boundary."""


class LiteLlmGatewayTimeoutError(LiteLlmGatewayError):
    """Raised when the LiteLLM gateway call times out."""


class LiteLlmGatewayResponseError(LiteLlmGatewayError):
    """Raised when LiteLLM returns an unusable or malformed response."""


class LiteLlmGatewayModelFallbackError(LiteLlmGatewayError):
    """Raised when LiteLLM returns a different model than requested."""


class LiteLlmGatewayRequestBudgetError(LiteLlmGatewayError):
    """Raised when a LiteLLM request exceeds the configured token budget."""


class LiteLlmChatCompletionClient(Protocol):
    """Minimal async OpenAI-compatible chat-completions surface."""

    async def create(self, **kwargs: Any) -> Any: ...


@dataclass(frozen=True, slots=True)
class LiteLlmGatewayMessage:
    """Typed chat message sent to the LiteLLM OpenAI-compatible endpoint."""

    role: LiteLlmGatewayRole
    content: str

    def __post_init__(self) -> None:
        _require_non_empty(self.content, "content")

    def to_payload(self) -> JsonObject:
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass(frozen=True, slots=True)
class LiteLlmGatewayChatRequest:
    """Typed text or JSON chat-completion request for the LiteLLM gateway."""

    model: str
    messages: tuple[LiteLlmGatewayMessage, ...]
    temperature: float = 0.2
    max_tokens: int | None = None
    response_format: LiteLlmResponseFormat = "text"
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.model, "model")
        if not self.messages:
            raise ValueError("messages cannot be empty.")
        if self.max_tokens is not None and self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0.")


@dataclass(frozen=True, slots=True)
class LiteLlmGatewayOperationsPolicy:
    """Local LiteLLM execution policy for bounded model operations."""

    max_concurrency: int = 1
    timeout_seconds: float = 60.0
    request_budget_tokens: int = 4096
    reject_model_fallback: bool = True

    def __post_init__(self) -> None:
        if self.max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than 0.")
        if self.request_budget_tokens <= 0:
            raise ValueError("request_budget_tokens must be greater than 0.")

    def to_metadata(self) -> JsonObject:
        """Return sanitized policy settings for observability metadata."""

        return {
            "max_concurrency": self.max_concurrency,
            "timeout_seconds": self.timeout_seconds,
            "request_budget_tokens": self.request_budget_tokens,
            "model_fallback_policy": (
                "reject" if self.reject_model_fallback else "report"
            ),
        }


@dataclass(frozen=True, slots=True)
class LiteLlmGatewayChatResult:
    """Typed text response returned from the LiteLLM gateway."""

    text: str
    model: str
    provider_name: str = LITELLM_PROVIDER_NAME
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.text, "text")
        _require_non_empty(self.model, "model")
        _require_non_empty(self.provider_name, "provider_name")


@dataclass(frozen=True, slots=True)
class LiteLlmGatewayJsonResult:
    """Typed JSON-object response returned from the LiteLLM gateway."""

    payload: JsonObject
    model: str
    provider_name: str = LITELLM_PROVIDER_NAME
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.model, "model")
        _require_non_empty(self.provider_name, "provider_name")


class LiteLlmGatewayClient:
    """Async OpenAI-compatible client boundary for the LiteLLM proxy."""

    def __init__(
        self,
        *,
        completion_client: LiteLlmChatCompletionClient,
        default_model: str,
        operations_policy: LiteLlmGatewayOperationsPolicy | None = None,
    ) -> None:
        _require_non_empty(default_model, "default_model")
        self._completion_client = completion_client
        self._default_model = default_model
        self._operations_policy = operations_policy or LiteLlmGatewayOperationsPolicy()
        self._semaphore = asyncio.Semaphore(self._operations_policy.max_concurrency)

    @property
    def default_model(self) -> str:
        """Logical default model sent to the LiteLLM gateway."""

        return self._default_model

    @property
    def operations_policy(self) -> LiteLlmGatewayOperationsPolicy:
        """Conservative local execution policy enforced by this client."""

        return self._operations_policy

    @classmethod
    def from_settings(cls, settings: Settings) -> LiteLlmGatewayClient:
        """Build the native OpenAI-compatible client for the LiteLLM proxy."""

        settings.validate_litellm_gateway()

        from openai import AsyncOpenAI

        native_client = AsyncOpenAI(
            api_key=settings.LITELLM_API_KEY or _LOCAL_DEVELOPMENT_API_KEY,
            base_url=settings.LITELLM_BASE_URL,
            timeout=settings.LITELLM_TIMEOUT_SECONDS,
        )
        return cls(
            completion_client=cast(
                LiteLlmChatCompletionClient,
                native_client.chat.completions,
            ),
            default_model=settings.DEFAULT_MODEL,
            operations_policy=LiteLlmGatewayOperationsPolicy(
                max_concurrency=settings.LITELLM_MAX_CONCURRENCY,
                timeout_seconds=settings.LITELLM_TIMEOUT_SECONDS,
                request_budget_tokens=settings.LITELLM_REQUEST_BUDGET_TOKENS,
                reject_model_fallback=settings.LITELLM_REJECT_MODEL_FALLBACK,
            ),
        )

    async def generate_text(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        metadata: JsonObject | None = None,
    ) -> LiteLlmGatewayChatResult:
        """Generate plain text through LiteLLM without exposing SDK responses."""

        request = LiteLlmGatewayChatRequest(
            model=_resolve_request_model(model, default_model=self._default_model),
            messages=_prompt_messages(prompt=prompt, system_prompt=system_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="text",
            metadata=metadata or {},
        )
        return await self.chat(request)

    async def generate_json(
        self,
        *,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        metadata: JsonObject | None = None,
    ) -> LiteLlmGatewayJsonResult:
        """Generate and parse one JSON object through LiteLLM."""

        request = LiteLlmGatewayChatRequest(
            model=_resolve_request_model(model, default_model=self._default_model),
            messages=_prompt_messages(prompt=prompt, system_prompt=system_prompt),
            temperature=temperature,
            max_tokens=max_tokens,
            response_format="json_object",
            metadata=metadata or {},
        )
        result = await self.chat(request)
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError as exc:
            raise LiteLlmGatewayResponseError(
                "LiteLLM gateway returned invalid JSON content."
            ) from exc
        if not isinstance(payload, dict):
            raise LiteLlmGatewayResponseError(
                "LiteLLM gateway JSON response must be an object."
            )
        return LiteLlmGatewayJsonResult(
            payload=payload,
            model=result.model,
            provider_name=result.provider_name,
            metadata=result.metadata,
        )

    async def chat(
        self,
        request: LiteLlmGatewayChatRequest,
    ) -> LiteLlmGatewayChatResult:
        """Execute a typed chat-completion request against LiteLLM."""

        effective_max_tokens = self._effective_max_tokens(request)
        response = await self._create_completion(
            request,
            effective_max_tokens=effective_max_tokens,
        )
        text = _extract_text(response)
        response_model = _response_model(response) or request.model
        model_fallback_detected = response_model != request.model
        if model_fallback_detected and self._operations_policy.reject_model_fallback:
            raise LiteLlmGatewayModelFallbackError(
                "LiteLLM gateway returned model "
                f"'{response_model}' for requested model alias/capability "
                f"'{request.model}'; silent model fallback is disabled."
            )
        return LiteLlmGatewayChatResult(
            text=text,
            model=response_model,
            provider_name=LITELLM_PROVIDER_NAME,
            metadata=_response_metadata(
                response,
                request=request,
                response_model=response_model,
                model_fallback_detected=model_fallback_detected,
                effective_max_tokens=effective_max_tokens,
                operations_policy=self._operations_policy,
            ),
        )

    async def _create_completion(
        self,
        request: LiteLlmGatewayChatRequest,
        *,
        effective_max_tokens: int,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": [message.to_payload() for message in request.messages],
            "temperature": request.temperature,
        }
        kwargs["max_tokens"] = effective_max_tokens
        if request.response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            async with self._semaphore:
                return await self._completion_client.create(**kwargs)
        except Exception as exc:
            if _is_timeout_error(exc):
                raise LiteLlmGatewayTimeoutError(
                    "LiteLLM gateway chat completion timed out for model "
                    f"alias/capability '{request.model}' after "
                    f"{self._operations_policy.timeout_seconds:g} seconds."
                ) from exc
            raise LiteLlmGatewayError(
                "LiteLLM gateway chat completion failed for model "
                f"alias/capability '{request.model}'."
            ) from exc

    def _effective_max_tokens(self, request: LiteLlmGatewayChatRequest) -> int:
        requested_tokens = request.max_tokens
        budget_tokens = self._operations_policy.request_budget_tokens
        if requested_tokens is not None and requested_tokens > budget_tokens:
            raise LiteLlmGatewayRequestBudgetError(
                "LiteLLM request for model alias/capability "
                f"'{request.model}' requested max_tokens={requested_tokens}, "
                f"which exceeds configured request_budget_tokens={budget_tokens}."
            )
        return requested_tokens if requested_tokens is not None else budget_tokens


def _resolve_request_model(model: str | None, *, default_model: str) -> str:
    if model is None:
        return default_model
    _require_non_empty(model, "model")
    return model.strip()


def _prompt_messages(
    *,
    prompt: str,
    system_prompt: str | None,
) -> tuple[LiteLlmGatewayMessage, ...]:
    _require_non_empty(prompt, "prompt")
    messages: list[LiteLlmGatewayMessage] = []
    if system_prompt is not None and system_prompt.strip():
        messages.append(
            LiteLlmGatewayMessage(
                role="system",
                content=system_prompt,
            )
        )
    messages.append(
        LiteLlmGatewayMessage(
            role="user",
            content=prompt,
        )
    )
    return tuple(messages)


def _extract_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        raise LiteLlmGatewayResponseError("LiteLLM response did not include choices.")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise LiteLlmGatewayResponseError(
            "LiteLLM response did not include text content."
        )
    return content.strip()


def _response_model(response: Any) -> str | None:
    model = getattr(response, "model", None)
    if isinstance(model, str) and model.strip():
        return model.strip()
    return None


def _response_metadata(
    response: Any,
    *,
    request: LiteLlmGatewayChatRequest,
    response_model: str,
    model_fallback_detected: bool,
    effective_max_tokens: int,
    operations_policy: LiteLlmGatewayOperationsPolicy,
) -> JsonObject:
    metadata: dict[str, Any] = {
        "requested_model": request.model,
        "response_model": response_model,
        "response_format": request.response_format,
        "request_metadata": dict(request.metadata),
        "effective_max_tokens": effective_max_tokens,
        "model_fallback_detected": model_fallback_detected,
        "operations_policy": operations_policy.to_metadata(),
    }

    response_id = getattr(response, "id", None)
    if isinstance(response_id, str) and response_id.strip():
        metadata["response_id"] = response_id

    choices = getattr(response, "choices", None)
    if choices:
        finish_reason = getattr(choices[0], "finish_reason", None)
        if isinstance(finish_reason, str) and finish_reason.strip():
            metadata["finish_reason"] = finish_reason

    usage_metadata = _usage_metadata(getattr(response, "usage", None))
    if usage_metadata:
        metadata["usage"] = usage_metadata

    return metadata


def _usage_metadata(usage: Any) -> JsonObject:
    if usage is None:
        return {}
    if isinstance(usage, Mapping):
        return dict(usage)
    model_dump = getattr(usage, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(exclude_none=True)
        if isinstance(dumped, dict):
            return dumped

    metadata: dict[str, Any] = {}
    for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = getattr(usage, name, None)
        if isinstance(value, int):
            metadata[name] = value
    return metadata


def _is_timeout_error(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    return exc.__class__.__name__ in _TIMEOUT_ERROR_NAMES


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
