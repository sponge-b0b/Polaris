from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import BaseModel

from config.settings import Settings
from integration.providers.llm_structured_output import (
    InstructorChatCompletionClient,
    InstructorStructuredOutputProvider,
    InstructorStructuredOutputProviderConfig,
    StructuredLlmRequest,
    StructuredOutputRetryPolicy,
    StructuredOutputSchemaRef,
    StructuredOutputStatus,
    instructor_structured_output_provider,
)

STRUCTURED_MODEL_ALIAS = "polaris-local-structured"


class ExampleInstructorAnswer(BaseModel):
    answer_text: str
    confidence_score: float


class FakeInstructorClient:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, Any]] = []

    async def create(
        self,
        *,
        response_model: type[ExampleInstructorAnswer],
        messages: list[dict[str, str]],
        max_retries: int,
        strict: bool,
        **kwargs: Any,
    ) -> object:
        self.calls.append(
            {
                "response_model": response_model,
                "messages": messages,
                "max_retries": max_retries,
                "strict": strict,
                "kwargs": kwargs,
            }
        )
        output = self.outputs.pop(0)
        if isinstance(output, BaseException):
            raise output
        return output


class SlowInstructorClient:
    def __init__(self) -> None:
        self.calls = 0

    async def create(
        self,
        *,
        response_model: type[ExampleInstructorAnswer],
        messages: list[dict[str, str]],
        max_retries: int,
        strict: bool,
        **kwargs: Any,
    ) -> object:
        del response_model, messages, max_retries, strict, kwargs
        self.calls += 1
        await asyncio.sleep(0.01)
        return {"answer_text": "too late", "confidence_score": 0.8}


def _provider(
    client: FakeInstructorClient | SlowInstructorClient,
) -> InstructorStructuredOutputProvider:
    return InstructorStructuredOutputProvider(
        client=cast(InstructorChatCompletionClient, client),
        config=InstructorStructuredOutputProviderConfig(
            model=STRUCTURED_MODEL_ALIAS,
            gateway_base_url="http://localhost:4000/v1",
        ),
    )


def _request(
    *,
    retry_policy: StructuredOutputRetryPolicy | None = None,
) -> StructuredLlmRequest[ExampleInstructorAnswer]:
    return StructuredLlmRequest(
        request_id="instructor-request-1",
        prompt="Return a structured answer.",
        system_prompt="You return only schema-valid output.",
        response_model=ExampleInstructorAnswer,
        schema_ref=StructuredOutputSchemaRef("ExampleInstructorAnswer"),
        model=STRUCTURED_MODEL_ALIAS,
        provider_name="instructor",
        retry_policy=retry_policy or StructuredOutputRetryPolicy(max_retries=2),
    )


def test_instructor_provider_maps_successful_structured_output() -> None:
    client = FakeInstructorClient(
        [ExampleInstructorAnswer(answer_text="structured", confidence_score=0.92)]
    )

    result = asyncio.run(_provider(client).generate_structured_output(_request()))

    assert result.status is StructuredOutputStatus.SUCCEEDED
    assert result.output == ExampleInstructorAnswer(
        answer_text="structured",
        confidence_score=0.92,
    )
    assert result.provider_name == "instructor"
    assert result.model == STRUCTURED_MODEL_ALIAS
    assert result.attempts == 1
    assert client.calls == [
        {
            "response_model": ExampleInstructorAnswer,
            "messages": [
                {"role": "system", "content": "You return only schema-valid output."},
                {"role": "user", "content": "Return a structured answer."},
            ],
            "max_retries": 1,
            "strict": False,
            "kwargs": {
                "model": STRUCTURED_MODEL_ALIAS,
                "temperature": 0.2,
                "max_tokens": 4096,
            },
        }
    ]


def test_instructor_provider_retries_malformed_output() -> None:
    client = FakeInstructorClient(
        [
            {"answer_text": "missing confidence"},
            {"answer_text": "valid", "confidence_score": 0.81},
        ]
    )

    result = asyncio.run(
        _provider(client).generate_structured_output(
            _request(retry_policy=StructuredOutputRetryPolicy(max_retries=1))
        )
    )

    assert result.success is True
    assert result.attempts == 2
    assert result.output == ExampleInstructorAnswer(
        answer_text="valid",
        confidence_score=0.81,
    )
    assert len(client.calls) == 2


def test_instructor_provider_returns_typed_failure_after_retry_exhaustion() -> None:
    client = FakeInstructorClient(
        [
            {"answer_text": "missing confidence"},
            {"answer_text": "still missing confidence"},
        ]
    )

    result = asyncio.run(
        _provider(client).generate_structured_output(
            _request(retry_policy=StructuredOutputRetryPolicy(max_retries=1))
        )
    )

    assert result.success is False
    assert result.status is StructuredOutputStatus.FAILED
    assert result.output is None
    assert result.attempts == 2
    assert result.error_type == "ValidationError"
    assert result.error_message == "Structured output validation failed."


def test_instructor_provider_returns_typed_timeout() -> None:
    client = SlowInstructorClient()

    result = asyncio.run(
        _provider(client).generate_structured_output(
            _request(
                retry_policy=StructuredOutputRetryPolicy(
                    max_retries=2,
                    timeout_seconds=0.001,
                )
            )
        )
    )

    assert result.success is False
    assert result.attempts == 1
    assert result.error_type == "TimeoutError"
    assert result.error_message == "Structured output provider timed out."
    assert client.calls == 1


def test_instructor_provider_returns_typed_provider_error() -> None:
    client = FakeInstructorClient([RuntimeError("provider exploded")])

    result = asyncio.run(_provider(client).generate_structured_output(_request()))

    assert result.success is False
    assert result.attempts == 1
    assert result.error_type == "RuntimeError"
    assert result.error_message == "Structured output provider call failed."


def test_from_settings_builds_litellm_gateway_instructor_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    openai_calls: list[dict[str, Any]] = []
    instructor_calls: list[dict[str, Any]] = []
    native_client = object()

    class FakeNativeAdapter:
        def __init__(self, received_native_client: object) -> None:
            self.received_native_client = received_native_client

        async def create(
            self,
            *,
            response_model: type[ExampleInstructorAnswer],
            messages: list[dict[str, str]],
            max_retries: int,
            strict: bool,
            **kwargs: Any,
        ) -> ExampleInstructorAnswer:
            del response_model, messages, max_retries, strict, kwargs
            return ExampleInstructorAnswer(answer_text="ok", confidence_score=0.8)

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            openai_calls.append(kwargs)

    def fake_from_openai(
        received_openai_client: object,
        **kwargs: Any,
    ) -> object:
        instructor_calls.append({"client": received_openai_client, "kwargs": kwargs})
        return native_client

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("POLARIS_STRUCTURED_OUTPUT_MODEL", STRUCTURED_MODEL_ALIAS)
    monkeypatch.setenv("POLARIS_STRUCTURED_OUTPUT_PROVIDER", "instructor")
    monkeypatch.setenv("POLARIS_STRUCTURED_OUTPUT_MAX_TOKENS", "8192")
    monkeypatch.setenv("POLARIS_STRUCTURED_OUTPUT_STRICT", "false")
    monkeypatch.setenv("POLARIS_STRUCTURED_OUTPUT_INSTRUCTOR_MODE", "json")
    monkeypatch.setenv("POLARIS_LITELLM_BASE_URL", "http://litellm.local:4000/v1")
    monkeypatch.setenv("POLARIS_LITELLM_API_KEY", "test-key")
    monkeypatch.setattr(
        instructor_structured_output_provider,
        "_InstructorNativeClientAdapter",
        FakeNativeAdapter,
    )

    import instructor
    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(instructor, "from_openai", fake_from_openai)

    provider = InstructorStructuredOutputProvider.from_settings(Settings())

    assert isinstance(provider, InstructorStructuredOutputProvider)
    assert openai_calls == [
        {
            "api_key": "test-key",
            "base_url": "http://litellm.local:4000/v1",
            "timeout": 60.0,
        }
    ]
    assert len(instructor_calls) == 1
    assert isinstance(instructor_calls[0]["client"], FakeAsyncOpenAI)
    assert instructor_calls[0]["kwargs"] == {
        "mode": instructor_structured_output_provider._instructor_mode("json"),
    }


def test_instructor_model_completion_helper_supports_prefixed_models() -> None:
    assert (
        instructor_structured_output_provider._instructor_model_completion_name(
            "openai/gpt-4.1"
        )
        == "gpt-4.1"
    )
    assert (
        instructor_structured_output_provider._instructor_model_completion_name(
            STRUCTURED_MODEL_ALIAS
        )
        == STRUCTURED_MODEL_ALIAS
    )
