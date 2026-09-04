from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar

ResultPayloadT = TypeVar("ResultPayloadT")


@dataclass(
    frozen=True,
    slots=True,
)
class ServiceDegradation:
    """
    Typed description of a recoverable partial-service failure.
    """

    code: str
    component: str
    summary: str
    error_type: str | None = None

    def to_dict(
        self,
    ) -> dict[str, str | None]:
        return {
            "code": self.code,
            "component": self.component,
            "summary": self.summary,
            "error_type": self.error_type,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ServiceResult[ResultPayloadT]:
    """
    Canonical application-service result envelope.
    """

    request_id: str
    request_name: str
    success: bool
    result: ResultPayloadT | None = None
    error_message: str | None = None
    error_type: str | None = None
    validation_errors: tuple[str, ...] = ()
    degradations: tuple[ServiceDegradation, ...] = ()
    attempts: int = 1
    duration_seconds: float | None = None
    completed_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    @classmethod
    def ok(
        cls,
        *,
        request_id: str,
        request_name: str,
        result: ResultPayloadT,
        degradations: tuple[ServiceDegradation, ...] = (),
        attempts: int = 1,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult[ResultPayloadT]:
        return cls(
            request_id=request_id,
            request_name=request_name,
            success=True,
            result=result,
            degradations=degradations,
            attempts=attempts,
            duration_seconds=duration_seconds,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def failed(
        cls,
        *,
        request_id: str,
        request_name: str,
        error: BaseException | str,
        attempts: int = 1,
        duration_seconds: float | None = None,
        validation_errors: tuple[str, ...] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult[ResultPayloadT]:
        error_message = str(error) if isinstance(error, BaseException) else error
        error_type = (
            type(error).__name__ if isinstance(error, BaseException) else "ServiceError"
        )

        return cls(
            request_id=request_id,
            request_name=request_name,
            success=False,
            error_message=error_message,
            error_type=error_type,
            validation_errors=validation_errors,
            attempts=attempts,
            duration_seconds=duration_seconds,
            metadata=dict(metadata or {}),
        )

    def raise_if_failed(
        self,
    ) -> None:
        if self.success:
            return

        raise RuntimeError(self.error_message or "Service execution failed.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_name": self.request_name,
            "success": self.success,
            "result": deepcopy(self.result),
            "error_message": self.error_message,
            "error_type": self.error_type,
            "validation_errors": list(self.validation_errors),
            "degradations": [
                degradation.to_dict() for degradation in self.degradations
            ],
            "attempts": self.attempts,
            "duration_seconds": self.duration_seconds,
            "completed_at": self.completed_at.isoformat(),
            "metadata": deepcopy(self.metadata),
        }
