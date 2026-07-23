from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from config.settings import Settings
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.llm_structured_output.structured_output_provider import (
    StructuredLlmProvider,
    StructuredLlmProviderExecutor,
    StructuredLlmRequest,
    StructuredLlmResult,
)

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class InstructorChatCompletionClient(Protocol):
    """Minimal async Instructor client surface used by Polaris."""

    async def create(
        self,
        *,
        response_model: type[ResponseModelT],
        messages: list[dict[str, str]],
        max_retries: int,
        strict: bool,
        **kwargs: Any,
    ) -> ResponseModelT: ...


@dataclass(frozen=True, slots=True)
class InstructorStructuredOutputProviderConfig:
    """Configuration for the Instructor-backed structured-output provider."""

    model: str
    gateway_base_url: str
    provider_name: str = "instructor"
    temperature: float = 0.2
    strict: bool = False
    max_tokens: int = 4096
    instructor_mode: str = "json"

    def __post_init__(self) -> None:
        _require_non_empty(self.model, "model")
        _require_non_empty(self.gateway_base_url, "gateway_base_url")
        _require_non_empty(self.provider_name, "provider_name")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than 0.")


class InstructorStructuredOutputProvider(StructuredLlmProvider):
    """Structured-output provider backed by Instructor."""

    def __init__(
        self,
        client: InstructorChatCompletionClient,
        config: InstructorStructuredOutputProviderConfig,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._client = client
        self._config = config
        self._executor = StructuredLlmProviderExecutor(telemetry=telemetry)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        telemetry: IntegrationTelemetry | None = None,
    ) -> InstructorStructuredOutputProvider:
        """Build the native Instructor client from Polaris settings."""

        import instructor
        from openai import AsyncOpenAI

        settings.validate_litellm_gateway()
        openai_client = AsyncOpenAI(
            api_key=settings.LITELLM_API_KEY or "polaris-local-dev-key",
            base_url=settings.LITELLM_BASE_URL,
            timeout=settings.LITELLM_TIMEOUT_SECONDS,
        )
        native_client = instructor.from_openai(
            openai_client,
            mode=_instructor_mode(settings.STRUCTURED_OUTPUT_INSTRUCTOR_MODE),
        )
        return cls(
            client=_InstructorNativeClientAdapter(native_client),
            config=InstructorStructuredOutputProviderConfig(
                model=settings.STRUCTURED_OUTPUT_MODEL,
                gateway_base_url=settings.LITELLM_BASE_URL,
                provider_name=settings.STRUCTURED_OUTPUT_PROVIDER,
                strict=settings.STRUCTURED_OUTPUT_STRICT,
                max_tokens=settings.STRUCTURED_OUTPUT_MAX_TOKENS,
                instructor_mode=settings.STRUCTURED_OUTPUT_INSTRUCTOR_MODE,
            ),
            telemetry=telemetry,
        )

    async def generate_structured_output(
        self,
        request: StructuredLlmRequest[ResponseModelT],
    ) -> StructuredLlmResult[ResponseModelT]:
        return await self._executor.execute(request, self._generate_with_instructor)

    async def _generate_with_instructor(
        self,
        request: StructuredLlmRequest[ResponseModelT],
    ) -> ResponseModelT:
        messages = _messages_for(request)
        return await self._client.create(
            response_model=request.response_model,
            messages=messages,
            max_retries=1,
            strict=self._config.strict,
            model=_instructor_model_completion_name(request.model),
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )


class _InstructorNativeClientAdapter:
    def __init__(self, native_client: Any) -> None:
        self._native_client = native_client

    async def create(
        self,
        *,
        response_model: type[ResponseModelT],
        messages: list[dict[str, str]],
        max_retries: int,
        strict: bool,
        **kwargs: Any,
    ) -> ResponseModelT:
        return await self._native_client.chat.completions.create(
            response_model=response_model,
            messages=messages,
            max_retries=max_retries,
            strict=strict,
            **kwargs,
        )


def _messages_for[ResponseModelT: BaseModel](
    request: StructuredLlmRequest[ResponseModelT],
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if request.system_prompt is not None:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.prompt})
    return messages


def _instructor_model_completion_name(model: str) -> str:
    stripped = model.strip()
    if "/" in stripped:
        return stripped.split("/", 1)[1]
    return stripped


def _instructor_mode(mode: str) -> Any:
    import instructor

    normalized = mode.strip().lower()
    if normalized == "json":
        return instructor.Mode.JSON
    if normalized == "tools":
        return instructor.Mode.TOOLS
    if normalized == "tools_strict":
        return instructor.Mode.TOOLS_STRICT
    raise ValueError(f"Unsupported Instructor mode: {mode}.")


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
