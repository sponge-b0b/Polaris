from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from time import perf_counter
from typing import Any, Protocol, cast, runtime_checkable

from pydantic import BaseModel, ValidationError

from core.storage.persistence.rag import JsonObject
from core.telemetry.emitters.integration_telemetry import IntegrationTelemetry
from domain.llm import ReasoningTraceViolationError, reject_reasoning_trace
from integration.providers.provider_telemetry import record_provider_call

logger = logging.getLogger(__name__)

type StructuredOutputCall[ResponseModelT: BaseModel] = Callable[
    ["StructuredLlmRequest[ResponseModelT]"], Awaitable[object]
]


class StructuredOutputStatus(StrEnum):
    """Canonical status for one structured LLM provider call."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StructuredOutputSchemaRef:
    """Provider-neutral reference to the expected structured response schema."""

    schema_name: str
    schema_version: str = "v1"

    def __post_init__(self) -> None:
        _require_non_empty(self.schema_name, "schema_name")
        _require_non_empty(self.schema_version, "schema_version")


@dataclass(frozen=True, slots=True)
class StructuredOutputRetryPolicy:
    """Retry and timeout policy for structured output validation."""

    max_retries: int = 2
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to 0.")
        if self.timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be greater than 0.0.")

    @property
    def maximum_attempts(self) -> int:
        return self.max_retries + 1


@dataclass(frozen=True, slots=True)
class StructuredLlmRequest[ResponseModelT: BaseModel]:
    """Provider-bound request for schema-validated LLM output."""

    request_id: str
    prompt: str
    response_model: type[ResponseModelT]
    schema_ref: StructuredOutputSchemaRef
    model: str
    provider_name: str
    system_prompt: str | None = None
    retry_policy: StructuredOutputRetryPolicy = field(
        default_factory=StructuredOutputRetryPolicy
    )
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.request_id, "request_id")
        _require_non_empty(self.prompt, "prompt")
        _require_non_empty(self.model, "model")
        _require_non_empty(self.provider_name, "provider_name")
        if self.system_prompt is not None:
            _require_non_empty(self.system_prompt, "system_prompt")


@dataclass(frozen=True, slots=True)
class StructuredLlmResult[ResponseModelT: BaseModel]:
    """Provider-neutral result from a structured LLM output operation."""

    request_id: str
    status: StructuredOutputStatus
    provider_name: str
    model: str
    schema_ref: StructuredOutputSchemaRef
    attempts: int
    output: ResponseModelT | None = None
    error_type: str | None = None
    error_message: str | None = None
    duration_seconds: float | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_empty(self.request_id, "request_id")
        _require_non_empty(self.provider_name, "provider_name")
        _require_non_empty(self.model, "model")
        if self.attempts <= 0:
            raise ValueError("attempts must be greater than 0.")
        if self.status is StructuredOutputStatus.SUCCEEDED and self.output is None:
            raise ValueError("successful structured output results require output.")
        if self.status is StructuredOutputStatus.FAILED and not self.error_type:
            raise ValueError("failed structured output results require error_type.")

    @property
    def success(self) -> bool:
        return self.status is StructuredOutputStatus.SUCCEEDED


@runtime_checkable
class StructuredLlmProvider(Protocol):
    """Canonical async provider interface for schema-validated LLM output."""

    async def generate_structured_output[ResponseModelT: BaseModel](
        self,
        request: StructuredLlmRequest[ResponseModelT],
    ) -> StructuredLlmResult[ResponseModelT]: ...


class StructuredLlmProviderExecutor:
    """
    Shared executor for structured LLM providers.

    Concrete providers own vendor calls. This executor owns canonical retry,
    Pydantic schema validation, result mapping, and provider-call telemetry.
    """

    def __init__(
        self,
        telemetry: IntegrationTelemetry | None = None,
    ) -> None:
        self._telemetry = telemetry

    async def execute[ResponseModelT: BaseModel](
        self,
        request: StructuredLlmRequest[ResponseModelT],
        call: StructuredOutputCall[ResponseModelT],
        *,
        operation: str = "generate_structured_output",
    ) -> StructuredLlmResult[ResponseModelT]:
        attributes = _telemetry_attributes(request)
        payload = {
            **attributes,
            "request_id": request.request_id,
            "status": StructuredOutputStatus.FAILED.value,
            "attempt_count": 0,
            "retry_count": 0,
            "maximum_attempts": request.retry_policy.maximum_attempts,
        }

        try:
            return await record_provider_call(
                self._telemetry,
                request.provider_name,
                operation,
                lambda: self._execute_or_raise(request, call, payload),
                attributes=attributes,
                payload=payload,
            )
        except _StructuredOutputRetryExhausted as exc:
            return cast(StructuredLlmResult[ResponseModelT], exc.result)

    async def _execute_or_raise[ResponseModelT: BaseModel](
        self,
        request: StructuredLlmRequest[ResponseModelT],
        call: StructuredOutputCall[ResponseModelT],
        telemetry_payload: dict[str, object],
    ) -> StructuredLlmResult[ResponseModelT]:
        started_at = perf_counter()
        last_error_type = "ValidationError"
        last_error_message = "Structured output validation failed."

        for attempt in range(1, request.retry_policy.maximum_attempts + 1):
            telemetry_payload["attempt_count"] = attempt
            telemetry_payload["retry_count"] = attempt - 1
            try:
                async with asyncio.timeout(request.retry_policy.timeout_seconds):
                    raw_output = await call(request)
                _reject_reasoning_trace_payload(
                    raw_output,
                    boundary_name=(
                        f"structured LLM output {request.schema_ref.schema_name}"
                    ),
                )
                output = _validate_structured_output(
                    request.response_model,
                    raw_output,
                )
                _reject_reasoning_trace_payload(
                    output,
                    boundary_name=(
                        "validated structured LLM output "
                        f"{request.schema_ref.schema_name}"
                    ),
                )
            except TimeoutError as exc:
                logger.debug(
                    "Structured output provider timed out.",
                    extra={
                        "provider_name": request.provider_name,
                        "model": request.model,
                        "schema_name": request.schema_ref.schema_name,
                        "attempt": attempt,
                    },
                    exc_info=True,
                )
                result = _failure_result(
                    request,
                    attempts=attempt,
                    started_at=started_at,
                    error_type=type(exc).__name__,
                    error_message="Structured output provider timed out.",
                )
                telemetry_payload.update(_result_telemetry_payload(result))
                raise _StructuredOutputRetryExhausted(result) from exc
            except (ValidationError, ReasoningTraceViolationError) as exc:
                last_error_type = type(exc).__name__
                last_error_message = _structured_output_validation_error_message(exc)
                if attempt < request.retry_policy.maximum_attempts:
                    continue
                logger.debug(
                    last_error_message,
                    extra={
                        "provider_name": request.provider_name,
                        "model": request.model,
                        "schema_name": request.schema_ref.schema_name,
                        "attempt": attempt,
                    },
                    exc_info=True,
                )
                result = _failure_result(
                    request,
                    attempts=attempt,
                    started_at=started_at,
                    error_type=last_error_type,
                    error_message=last_error_message,
                )
                telemetry_payload.update(_result_telemetry_payload(result))
                raise _StructuredOutputRetryExhausted(result) from exc
            except Exception as exc:
                logger.debug(
                    "Structured output provider call failed.",
                    extra={
                        "provider_name": request.provider_name,
                        "model": request.model,
                        "schema_name": request.schema_ref.schema_name,
                        "attempt": attempt,
                    },
                    exc_info=True,
                )
                result = _failure_result(
                    request,
                    attempts=attempt,
                    started_at=started_at,
                    error_type=type(exc).__name__,
                    error_message="Structured output provider call failed.",
                )
                telemetry_payload.update(_result_telemetry_payload(result))
                raise _StructuredOutputRetryExhausted(result) from exc

            result = StructuredLlmResult(
                request_id=request.request_id,
                status=StructuredOutputStatus.SUCCEEDED,
                provider_name=request.provider_name,
                model=request.model,
                schema_ref=request.schema_ref,
                attempts=attempt,
                output=output,
                duration_seconds=perf_counter() - started_at,
                metadata={"request_metadata": dict(request.metadata)},
            )
            telemetry_payload.update(_result_telemetry_payload(result))
            return result

        result = _failure_result(
            request,
            attempts=request.retry_policy.maximum_attempts,
            started_at=started_at,
            error_type=last_error_type,
            error_message=last_error_message,
        )
        telemetry_payload.update(_result_telemetry_payload(result))
        raise _StructuredOutputRetryExhausted(result)


class _StructuredOutputRetryExhausted(Exception):
    def __init__(self, result: StructuredLlmResult[Any]) -> None:
        super().__init__("Structured output generation failed after retry exhaustion.")
        self.result = result


def _validate_structured_output[ResponseModelT: BaseModel](
    response_model: type[ResponseModelT],
    raw_output: object,
) -> ResponseModelT:
    if isinstance(raw_output, response_model):
        return raw_output
    return response_model.model_validate(raw_output)


def _structured_output_validation_error_message(exc: Exception) -> str:
    if isinstance(exc, ReasoningTraceViolationError):
        return "Structured output contained model-internal reasoning."
    return "Structured output validation failed."


def _reject_reasoning_trace_payload(
    value: object,
    *,
    boundary_name: str,
) -> None:
    if isinstance(value, str):
        reject_reasoning_trace(value, boundary_name=boundary_name)
        return
    if isinstance(value, BaseModel):
        _reject_reasoning_trace_payload(
            value.model_dump(mode="json"),
            boundary_name=boundary_name,
        )
        return
    if isinstance(value, dict):
        for key, nested_value in value.items():
            _reject_reasoning_trace_payload(
                nested_value,
                boundary_name=f"{boundary_name}.{key}",
            )
        return
    if isinstance(value, (list, tuple)):
        for index, nested_value in enumerate(value):
            _reject_reasoning_trace_payload(
                nested_value,
                boundary_name=f"{boundary_name}[{index}]",
            )


def _failure_result[ResponseModelT: BaseModel](
    request: StructuredLlmRequest[ResponseModelT],
    *,
    attempts: int,
    started_at: float,
    error_type: str,
    error_message: str,
) -> StructuredLlmResult[ResponseModelT]:
    return StructuredLlmResult(
        request_id=request.request_id,
        status=StructuredOutputStatus.FAILED,
        provider_name=request.provider_name,
        model=request.model,
        schema_ref=request.schema_ref,
        attempts=attempts,
        error_type=error_type,
        error_message=error_message,
        duration_seconds=perf_counter() - started_at,
        metadata={"request_metadata": dict(request.metadata)},
    )


def _telemetry_attributes[ResponseModelT: BaseModel](
    request: StructuredLlmRequest[ResponseModelT],
) -> dict[str, object]:
    return {
        "provider_name": request.provider_name,
        "model": request.model,
        "schema_name": request.schema_ref.schema_name,
        "schema_version": request.schema_ref.schema_version,
        "max_retries": request.retry_policy.max_retries,
    }


def _result_telemetry_payload[ResponseModelT: BaseModel](
    result: StructuredLlmResult[ResponseModelT],
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": result.status.value,
        "attempt_count": result.attempts,
        "retry_count": result.attempts - 1,
        "duration_seconds": result.duration_seconds,
    }
    if result.error_type is not None:
        payload["error_type"] = result.error_type
    if result.error_message is not None:
        payload["error_message"] = result.error_message
    return payload


def _require_non_empty(value: str | None, field_name: str) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
