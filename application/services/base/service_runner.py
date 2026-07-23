from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any, TypeVar

from application.services.base.application_service import (
    ApplicationService,
    ValidatingApplicationService,
)
from application.services.base.service_request import ServiceRequest
from application.services.base.service_result import ServiceResult
from core.runtime.policies.policy_engine import PolicyEngine
from core.telemetry.context import get_active_telemetry_context, telemetry_context_scope
from core.telemetry.contracts.telemetry_context import TelemetryContext
from core.telemetry.emitters.application_service_telemetry import (
    ApplicationServiceTelemetry,
)

RequestPayloadT = TypeVar("RequestPayloadT")
ResultPayloadT = TypeVar("ResultPayloadT")


@dataclass(
    frozen=True,
    slots=True,
)
class ServiceRunnerConfig:
    """
    Runtime controls for canonical service execution.
    """

    max_attempts: int = 1
    retry_backoff_seconds: float = 0.0
    emit_telemetry: bool = True
    enforce_policy: bool = True

    def validate(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if self.max_attempts < 1:
            errors.append(
                "max_attempts must be at least 1.",
            )

        if self.retry_backoff_seconds < 0:
            errors.append(
                "retry_backoff_seconds cannot be negative.",
            )

        return tuple(errors)


class ServiceRunner[RequestPayloadT, ResultPayloadT]:
    """
    Canonical application-service orchestrator.
    """

    def __init__(
        self,
        *,
        telemetry: ApplicationServiceTelemetry,
        policy_engine: PolicyEngine | None = None,
        config: ServiceRunnerConfig | None = None,
    ) -> None:
        self.telemetry = telemetry
        self.policy_engine = policy_engine
        self.config = config or ServiceRunnerConfig()

    async def run(
        self,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
    ) -> ServiceResult[ResultPayloadT]:
        parent_context = (
            request.telemetry_context
            or get_active_telemetry_context()
            or TelemetryContext(correlation_id=request.correlation_id)
        )
        if parent_context.to_trace_context() is None:
            parent_context = parent_context.child_operation(
                attributes={
                    "operation_kind": "application_service",
                    "service_name": service.service_name,
                    "request_name": request.request_name,
                    "request_id": request.request_id,
                },
            )
        return await self._run_in_context(
            service=service,
            request=request,
            parent_context=parent_context,
        )

    async def _run_in_context(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        parent_context: TelemetryContext,
    ) -> ServiceResult[ResultPayloadT]:
        first_attempt_context = self._attempt_context(
            service=service,
            request=request,
            parent_context=parent_context,
            attempt=1,
        )
        with telemetry_context_scope(first_attempt_context):
            config_errors = self.config.validate()
            if config_errors:
                await self._emit_configuration_failed(
                    service=service,
                    request=request,
                    context=first_attempt_context,
                    validation_errors=config_errors,
                )
                return ServiceResult.failed(
                    request_id=request.request_id,
                    request_name=request.request_name,
                    error="Invalid service runner configuration.",
                    validation_errors=config_errors,
                    metadata={
                        "service_name": service.service_name,
                    },
                )

            started_at = perf_counter()
            validation_errors = await self._validate_request(
                service=service,
                request=request,
            )

            if validation_errors:
                result: ServiceResult[ResultPayloadT] = ServiceResult.failed(
                    request_id=request.request_id,
                    request_name=request.request_name,
                    error="Service request validation failed.",
                    validation_errors=validation_errors,
                    duration_seconds=perf_counter() - started_at,
                    metadata={
                        "service_name": service.service_name,
                    },
                )
                await self._emit_failed(
                    service=service,
                    request=request,
                    context=first_attempt_context,
                    result=result,
                )
                return result

            if self.policy_engine and self._should_enforce_policy():
                policy_result = await self.policy_engine.evaluate(
                    subject=request,
                    context=request.policy_context(),
                    policy_names=list(request.policy_names) or None,
                )
                if policy_result.denied:
                    result = ServiceResult.failed(
                        request_id=request.request_id,
                        request_name=request.request_name,
                        error="Service request denied by policy.",
                        duration_seconds=perf_counter() - started_at,
                        metadata={
                            "service_name": service.service_name,
                            "policy": policy_result.to_dict(),
                        },
                    )
                    await self._emit_failed(
                        service=service,
                        request=request,
                        context=first_attempt_context,
                        result=result,
                    )
                    return result

            return await self._run_with_retries(
                service=service,
                request=request,
                started_at=started_at,
                first_attempt_context=first_attempt_context,
                parent_context=parent_context,
            )

    async def _run_with_retries(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        started_at: float,
        first_attempt_context: TelemetryContext,
        parent_context: TelemetryContext,
    ) -> ServiceResult[ResultPayloadT]:
        last_result: ServiceResult[ResultPayloadT] | None = None

        for attempt in range(1, self.config.max_attempts + 1):
            attempt_context = (
                first_attempt_context
                if attempt == 1
                else self._attempt_context(
                    service=service,
                    request=request,
                    parent_context=parent_context,
                    attempt=attempt,
                )
            )
            attempt_started_at = perf_counter()
            with telemetry_context_scope(attempt_context):
                await self._emit_started(
                    service=service,
                    request=request,
                    context=attempt_context,
                )

                caught_error: BaseException | str | None = None
                try:
                    result = await service.run(request)
                    attempt_result = self._with_runtime_metadata(
                        result=result,
                        service_name=service.service_name,
                        attempt=attempt,
                        duration_seconds=perf_counter() - attempt_started_at,
                    )
                except asyncio.CancelledError:
                    await self._emit_cancelled(
                        service=service,
                        request=request,
                        context=attempt_context,
                        duration_seconds=perf_counter() - attempt_started_at,
                        attempt=attempt,
                    )
                    raise
                except Exception as exc:
                    caught_error = exc
                    attempt_result = ServiceResult.failed(
                        request_id=request.request_id,
                        request_name=request.request_name,
                        error=exc,
                        attempts=attempt,
                        duration_seconds=perf_counter() - attempt_started_at,
                        metadata={
                            "service_name": service.service_name,
                        },
                    )

                if attempt_result.success:
                    if attempt_result.degradations:
                        await self._emit_degraded(
                            service=service,
                            request=request,
                            context=attempt_context,
                            result=attempt_result,
                        )
                    await self._emit_completed(
                        service=service,
                        request=request,
                        context=attempt_context,
                        result=attempt_result,
                    )
                    return self._with_runtime_metadata(
                        result=attempt_result,
                        service_name=service.service_name,
                        attempt=attempt,
                        duration_seconds=perf_counter() - started_at,
                    )

                last_result = attempt_result
                await self._emit_failed(
                    service=service,
                    request=request,
                    context=attempt_context,
                    result=attempt_result,
                    error=caught_error,
                )

                if attempt < self.config.max_attempts:
                    await self._emit_retry_scheduled(
                        service=service,
                        request=request,
                        context=attempt_context,
                        attempt=attempt,
                        error=(
                            caught_error
                            or attempt_result.error_message
                            or "Service execution failed."
                        ),
                        error_type=(
                            type(caught_error).__name__
                            if isinstance(caught_error, BaseException)
                            else attempt_result.error_type or "ServiceError"
                        ),
                    )
                    await asyncio.sleep(self.config.retry_backoff_seconds)

        if last_result is None:
            last_result = ServiceResult.failed(
                request_id=request.request_id,
                request_name=request.request_name,
                error="Service execution failed.",
                attempts=self.config.max_attempts,
                metadata={
                    "service_name": service.service_name,
                },
            )

        return self._with_runtime_metadata(
            result=last_result,
            service_name=service.service_name,
            attempt=self.config.max_attempts,
            duration_seconds=perf_counter() - started_at,
        )

    def _attempt_context(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        parent_context: TelemetryContext,
        attempt: int,
    ) -> TelemetryContext:
        return parent_context.child_operation(
            attributes={
                "operation_kind": "application_service_attempt",
                "service_name": service.service_name,
                "request_name": request.request_name,
                "request_id": request.request_id,
                "attempt": attempt,
                "max_attempts": self.config.max_attempts,
            },
        )

    def _should_enforce_policy(
        self,
    ) -> bool:
        return self.config.enforce_policy and self.policy_engine is not None

    async def _validate_request(
        self,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
    ) -> tuple[str, ...]:
        request_errors = request.validate()

        if not isinstance(service, ValidatingApplicationService):
            return request_errors

        service_errors = await service.validate_request(
            request,
        )

        return (
            *request_errors,
            *service_errors,
        )

    def _with_runtime_metadata(
        self,
        *,
        result: ServiceResult[ResultPayloadT],
        service_name: str,
        attempt: int,
        duration_seconds: float,
    ) -> ServiceResult[ResultPayloadT]:
        metadata: dict[str, Any] = {
            **result.metadata,
            "service_name": service_name,
        }

        return ServiceResult(
            request_id=result.request_id,
            request_name=result.request_name,
            success=result.success,
            result=result.result,
            error_message=result.error_message,
            error_type=result.error_type,
            validation_errors=result.validation_errors,
            degradations=result.degradations,
            attempts=attempt,
            duration_seconds=duration_seconds,
            completed_at=result.completed_at,
            metadata=metadata,
        )

    async def _emit_configuration_failed(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
        validation_errors: tuple[str, ...],
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_configuration_failed(
            service_name=service.service_name,
            request_name=request.request_name,
            validation_errors=validation_errors,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
                "max_attempts": self.config.max_attempts,
                "retry_backoff_seconds": self.config.retry_backoff_seconds,
            },
        )

    async def _emit_retry_scheduled(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
        attempt: int,
        error: BaseException | str,
        error_type: str,
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_retry_scheduled(
            service_name=service.service_name,
            request_name=request.request_name,
            attempt=attempt,
            next_attempt=attempt + 1,
            maximum_attempts=self.config.max_attempts,
            backoff_seconds=self.config.retry_backoff_seconds,
            reason=str(error),
            error_type=error_type,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
            },
        )

    async def _emit_started(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_started(
            service_name=service.service_name,
            request_name=request.request_name,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
            },
        )

    async def _emit_completed(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
        result: ServiceResult[ResultPayloadT],
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_completed(
            service_name=service.service_name,
            request_name=request.request_name,
            duration_seconds=result.duration_seconds,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
                "attempts": result.attempts,
            },
        )

    async def _emit_degraded(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
        result: ServiceResult[ResultPayloadT],
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_degraded(
            service_name=service.service_name,
            request_name=request.request_name,
            duration_seconds=result.duration_seconds,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
                "attempts": result.attempts,
                "degradation_count": len(result.degradations),
            },
            payload={
                "degradations": [
                    degradation.to_dict() for degradation in result.degradations
                ],
            },
        )

    async def _emit_cancelled(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
        duration_seconds: float,
        attempt: int,
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_cancelled(
            service_name=service.service_name,
            request_name=request.request_name,
            duration_seconds=duration_seconds,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
                "attempts": attempt,
            },
        )

    async def _emit_failed(
        self,
        *,
        service: ApplicationService[RequestPayloadT, ResultPayloadT],
        request: ServiceRequest[RequestPayloadT],
        context: TelemetryContext,
        result: ServiceResult[ResultPayloadT],
        error: BaseException | str | None = None,
    ) -> None:
        if not self._can_emit():
            return

        await self.telemetry.emit_service_failed(
            service_name=service.service_name,
            request_name=request.request_name,
            error=(
                error
                if error is not None
                else result.error_message or "Service execution failed."
            ),
            duration_seconds=result.duration_seconds,
            correlation_id=request.correlation_id,
            context=context,
            attributes={
                "request_id": request.request_id,
                "attempts": result.attempts,
            },
            payload={
                "error_type": result.error_type,
                "validation_errors": list(result.validation_errors),
            },
        )

    def _can_emit(
        self,
    ) -> bool:
        return self.config.emit_telemetry and self.telemetry is not None
