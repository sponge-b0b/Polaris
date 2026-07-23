from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import uuid4

from core.telemetry.contracts.telemetry_context import TelemetryContext

RequestPayloadT = TypeVar("RequestPayloadT")


@dataclass(
    frozen=True,
    slots=True,
)
class ServiceRequest[RequestPayloadT]:
    """
    Canonical application-service request envelope.
    """

    payload: RequestPayloadT
    request_name: str = field(default="")

    def __post_init__(self) -> None:
        # If no request name was passed, infer it at runtime from the actual
        # object instance.
        if not self.request_name:
            # object.__setattr__ is required to bypass frozen=True
            object.__setattr__(self, "request_name", type(self.payload).__name__)

    request_id: str = field(
        default_factory=lambda: str(uuid4()),
    )
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC),
    )
    correlation_id: str | None = None
    telemetry_context: TelemetryContext | None = None
    policy_names: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def validate(
        self,
    ) -> tuple[str, ...]:
        errors: list[str] = []

        if not self.payload:
            errors.append(
                "payload is required.",
            )

        if not self.request_id.strip():
            errors.append(
                "request_id is required.",
            )

        return tuple(errors)

    def policy_context(
        self,
    ) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_name": self.request_name,
            "correlation_id": self.correlation_id,
            "metadata": deepcopy(self.metadata),
            "telemetry_context": self._telemetry_context_to_dict(),
        }

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_name": self.request_name,
            "created_at": self.created_at.isoformat(),
            "correlation_id": self.correlation_id,
            "policy_names": list(self.policy_names),
            "metadata": deepcopy(self.metadata),
            "telemetry_context": self._telemetry_context_to_dict(),
            "payload": deepcopy(self.payload),
        }

    def _telemetry_context_to_dict(
        self,
    ) -> dict[str, Any] | None:
        if self.telemetry_context is None:
            return None

        return {
            "workflow_id": self.telemetry_context.workflow_id,
            "execution_id": self.telemetry_context.execution_id,
            "runtime_id": self.telemetry_context.runtime_id,
            "node_name": self.telemetry_context.node_name,
            "correlation_id": self.telemetry_context.correlation_id,
            "trace_id": self.telemetry_context.trace_id,
            "span_id": self.telemetry_context.span_id,
            "parent_span_id": self.telemetry_context.parent_span_id,
            "tags": list(self.telemetry_context.tags),
            "attributes": deepcopy(
                dict(self.telemetry_context.attributes or {}),
            ),
        }
