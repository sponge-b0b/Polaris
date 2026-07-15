from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Protocol
from typing import TypeVar

from pydantic import BaseModel

from config.settings import Settings
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.llm_structured_output.structured_output_provider import (
    StructuredLlmProvider,
)
from integration.providers.llm_structured_output.structured_output_provider import (
    StructuredLlmProviderExecutor,
)
from integration.providers.llm_structured_output.structured_output_provider import (
    StructuredLlmRequest,
)
from integration.providers.llm_structured_output.structured_output_provider import (
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
    ollama_base_url: str
    provider_name: str = "instructor"
    temperature: float = 0.2
    strict: bool = True

    def __post_init__(self) -> None:
        _require_non_empty(self.model, "model")
        _require_non_empty(self.ollama_base_url, "ollama_base_url")
        _require_non_empty(self.provider_name, "provider_name")


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

        instructor_model = _instructor_model_name(settings.STRUCTURED_OUTPUT_MODEL)
        kwargs: dict[str, Any] = {}
        if _uses_ollama_provider(instructor_model):
            kwargs["base_url"] = _ollama_openai_base_url(settings.OLLAMA_HOST)

        native_client = instructor.from_provider(
            instructor_model,
            async_client=True,
            **kwargs,
        )
        return cls(
            client=_InstructorNativeClientAdapter(native_client),
            config=InstructorStructuredOutputProviderConfig(
                model=settings.STRUCTURED_OUTPUT_MODEL,
                ollama_base_url=settings.OLLAMA_HOST,
                provider_name=settings.STRUCTURED_OUTPUT_PROVIDER,
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


def _messages_for(
    request: StructuredLlmRequest[ResponseModelT],
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if request.system_prompt is not None:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.prompt})
    return messages


def _instructor_model_name(model: str) -> str:
    stripped = model.strip()
    if "/" in stripped:
        return stripped
    return f"ollama/{stripped}"


def _instructor_model_completion_name(model: str) -> str:
    stripped = model.strip()
    if "/" in stripped:
        return stripped.split("/", 1)[1]
    return stripped


def _uses_ollama_provider(instructor_model: str) -> bool:
    return instructor_model.split("/", 1)[0].strip().lower() == "ollama"


def _ollama_openai_base_url(base_url: str) -> str:
    stripped = base_url.strip().rstrip("/")
    _require_non_empty(stripped, "ollama_base_url")
    if stripped.endswith("/v1"):
        return stripped
    return f"{stripped}/v1"


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
