from __future__ import annotations

import asyncio

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any
from typing import cast

import pytest
from pydantic import BaseModel

from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from integration.providers.llm_structured_output import StructuredLlmProvider
from integration.providers.llm_structured_output import StructuredLlmProviderExecutor
from integration.providers.llm_structured_output import StructuredLlmRequest
from integration.providers.llm_structured_output import StructuredLlmResult
from integration.providers.llm_structured_output import StructuredOutputRetryPolicy
from integration.providers.llm_structured_output import StructuredOutputSchemaRef
from integration.providers.llm_structured_output import StructuredOutputStatus
from integration.providers.llm_structured_output import structured_output_provider


class ExampleStructuredAnswer(BaseModel):
    answer_text: str
    confidence_score: float


class ScriptedStructuredLlmProvider:
    def __init__(
        self,
        outputs: list[object],
        *,
        captured_telemetry: list[dict[str, Any]] | None = None,
    ) -> None:
        self._outputs = outputs
        self._executor = StructuredLlmProviderExecutor(
            telemetry=cast(IntegrationTelemetry, object())
            if captured_telemetry is not None
            else None,
        )

    async def generate_structured_output(
        self,
        request: StructuredLlmRequest[ExampleStructuredAnswer],
    ) -> StructuredLlmResult[ExampleStructuredAnswer]:
        return await self._executor.execute(request, self._call)

    async def _call(
        self,
        _request: StructuredLlmRequest[ExampleStructuredAnswer],
    ) -> object:
        return self._outputs.pop(0)


class SlowStructuredLlmProvider:
    def __init__(self) -> None:
        self._executor = StructuredLlmProviderExecutor(
            telemetry=cast(IntegrationTelemetry, object())
        )

    async def generate_structured_output(
        self,
        request: StructuredLlmRequest[ExampleStructuredAnswer],
    ) -> StructuredLlmResult[ExampleStructuredAnswer]:
        return await self._executor.execute(request, self._call)

    async def _call(
        self,
        _request: StructuredLlmRequest[ExampleStructuredAnswer],
    ) -> object:
        await asyncio.sleep(0.01)
        return {"answer_text": "too late", "confidence_score": 0.8}


def _request(
    *,
    retry_policy: StructuredOutputRetryPolicy | None = None,
) -> StructuredLlmRequest[ExampleStructuredAnswer]:
    return StructuredLlmRequest(
        request_id="request-1",
        prompt="Return a structured answer.",
        response_model=ExampleStructuredAnswer,
        schema_ref=StructuredOutputSchemaRef(
            schema_name="ExampleStructuredAnswer",
            schema_version="v1",
        ),
        model="qwen3.5:4b",
        provider_name="fake-structured-provider",
        retry_policy=retry_policy or StructuredOutputRetryPolicy(max_retries=2),
        metadata={"workflow": "unit-test"},
    )


@pytest.fixture
def captured_provider_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict[str, Any]]:
    captured: list[dict[str, Any]] = []

    async def fake_record_provider_call(
        telemetry: IntegrationTelemetry | None,
        provider_name: str,
        operation: str,
        call: Callable[[], Awaitable[Any]],
        context: object | None = None,
        attributes: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        del telemetry, context
        try:
            result = await call()
        except Exception:
            captured.append(
                {
                    "provider_name": provider_name,
                    "operation": operation,
                    "success": False,
                    "attributes": dict(attributes or {}),
                    "payload": dict(payload or {}),
                }
            )
            raise
        captured.append(
            {
                "provider_name": provider_name,
                "operation": operation,
                "success": True,
                "attributes": dict(attributes or {}),
                "payload": dict(payload or {}),
            }
        )
        return result

    monkeypatch.setattr(
        structured_output_provider,
        "record_provider_call",
        fake_record_provider_call,
    )
    return captured


def test_structured_provider_protocol_accepts_fake_provider() -> None:
    provider = ScriptedStructuredLlmProvider(
        [{"answer_text": "ok", "confidence_score": 0.9}]
    )

    assert isinstance(provider, StructuredLlmProvider)


def test_structured_output_executor_validates_successful_mapping_response(
    captured_provider_telemetry: list[dict[str, Any]],
) -> None:
    provider = ScriptedStructuredLlmProvider(
        [{"answer_text": "validated answer", "confidence_score": 0.91}],
        captured_telemetry=captured_provider_telemetry,
    )

    result = asyncio.run(provider.generate_structured_output(_request()))

    assert result.success is True
    assert result.status is StructuredOutputStatus.SUCCEEDED
    assert result.output == ExampleStructuredAnswer(
        answer_text="validated answer",
        confidence_score=0.91,
    )
    assert result.attempts == 1
    assert result.metadata == {"request_metadata": {"workflow": "unit-test"}}
    assert captured_provider_telemetry[-1]["success"] is True
    assert captured_provider_telemetry[-1]["attributes"] == {
        "provider_name": "fake-structured-provider",
        "model": "qwen3.5:4b",
        "schema_name": "ExampleStructuredAnswer",
        "schema_version": "v1",
        "max_retries": 2,
    }
    assert captured_provider_telemetry[-1]["payload"]["status"] == "succeeded"
    assert captured_provider_telemetry[-1]["payload"]["retry_count"] == 0


def test_validation_failures_are_retried_and_counted(
    captured_provider_telemetry: list[dict[str, Any]],
) -> None:
    provider = ScriptedStructuredLlmProvider(
        [
            {"answer_text": "missing confidence"},
            {"answer_text": "validated answer", "confidence_score": 0.83},
        ],
        captured_telemetry=captured_provider_telemetry,
    )

    result = asyncio.run(
        provider.generate_structured_output(
            _request(retry_policy=StructuredOutputRetryPolicy(max_retries=1))
        )
    )

    assert result.success is True
    assert result.attempts == 2
    assert result.output == ExampleStructuredAnswer(
        answer_text="validated answer",
        confidence_score=0.83,
    )
    assert captured_provider_telemetry[-1]["payload"]["status"] == "succeeded"
    assert captured_provider_telemetry[-1]["payload"]["retry_count"] == 1
    assert captured_provider_telemetry[-1]["payload"]["attempt_count"] == 2


def test_retry_exhaustion_returns_typed_failure_result(
    captured_provider_telemetry: list[dict[str, Any]],
) -> None:
    provider = ScriptedStructuredLlmProvider(
        [
            {"answer_text": "missing confidence"},
            {"answer_text": "still missing confidence"},
        ],
        captured_telemetry=captured_provider_telemetry,
    )

    result = asyncio.run(
        provider.generate_structured_output(
            _request(retry_policy=StructuredOutputRetryPolicy(max_retries=1))
        )
    )

    assert result.success is False
    assert result.status is StructuredOutputStatus.FAILED
    assert result.output is None
    assert result.attempts == 2
    assert result.error_type == "ValidationError"
    assert result.error_message == "Structured output validation failed."
    assert captured_provider_telemetry[-1]["success"] is False
    assert captured_provider_telemetry[-1]["payload"]["status"] == "failed"
    assert captured_provider_telemetry[-1]["payload"]["retry_count"] == 1
    assert captured_provider_telemetry[-1]["payload"]["error_type"] == "ValidationError"


def test_timeout_returns_typed_failure_result(
    captured_provider_telemetry: list[dict[str, Any]],
) -> None:
    provider = SlowStructuredLlmProvider()

    result = asyncio.run(
        provider.generate_structured_output(
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
    assert captured_provider_telemetry[-1]["success"] is False
    assert captured_provider_telemetry[-1]["payload"]["status"] == "failed"
    assert captured_provider_telemetry[-1]["payload"]["attempt_count"] == 1


def test_request_and_retry_policy_validate_required_fields() -> None:
    with pytest.raises(ValueError, match="schema_name cannot be empty"):
        StructuredOutputSchemaRef(schema_name=" ")
    with pytest.raises(ValueError, match="max_retries"):
        StructuredOutputRetryPolicy(max_retries=-1)
    with pytest.raises(ValueError, match="timeout_seconds"):
        StructuredOutputRetryPolicy(timeout_seconds=0.0)
    with pytest.raises(ValueError, match="prompt cannot be empty"):
        StructuredLlmRequest(
            request_id="request-1",
            prompt=" ",
            response_model=ExampleStructuredAnswer,
            schema_ref=StructuredOutputSchemaRef(schema_name="ExampleStructuredAnswer"),
            model="qwen3.5:4b",
            provider_name="fake-structured-provider",
        )
