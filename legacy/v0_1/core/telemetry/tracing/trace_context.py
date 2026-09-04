from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class TraceContext:
    """
    Immutable vendor-neutral identity for one bounded operation span.

    A TraceContext is not a generic correlation scope. Its ``span_id`` belongs
    to exactly one timed operation; child operations must call ``child()``.

    PURPOSE
    ============================================================
    Provides platform-neutral correlation metadata across:
    - runtime execution
    - workflow orchestration
    - plugins
    - LLM calls
    - storage operations
    - external integrations

    This is intentionally independent from OpenTelemetry so the core
    platform remains vendor-neutral.
    """

    trace_id: str = field(default_factory=lambda: uuid4().hex)

    span_id: str = field(default_factory=lambda: uuid4().hex[:16])

    parent_span_id: str | None = None

    correlation_id: str | None = None

    workflow_id: str | None = None

    execution_id: str | None = None

    runtime_id: str | None = None

    node_name: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    attributes: dict[str, Any] = field(
        default_factory=dict,
    )

    def child(
        self,
        node_name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceContext:
        """
        Create the trace context for one distinct child operation.
        """

        return TraceContext(
            trace_id=self.trace_id,
            span_id=uuid4().hex[:16],
            parent_span_id=self.span_id,
            correlation_id=self.correlation_id,
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            runtime_id=self.runtime_id,
            node_name=node_name or self.node_name,
            attributes={
                **deepcopy(self.attributes),
                **deepcopy(attributes or {}),
            },
        )

    def with_attributes(
        self,
        attributes: dict[str, Any],
    ) -> TraceContext:
        return TraceContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            correlation_id=self.correlation_id,
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            runtime_id=self.runtime_id,
            node_name=self.node_name,
            created_at=self.created_at,
            attributes={
                **deepcopy(self.attributes),
                **deepcopy(attributes),
            },
        )

    def telemetry_attributes(
        self,
    ) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
        }

        if self.parent_span_id is not None:
            attributes["parent_span_id"] = self.parent_span_id

        return attributes

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "correlation_id": self.correlation_id,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "node_name": self.node_name,
            "created_at": self.created_at.isoformat(),
            "attributes": deepcopy(self.attributes),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> TraceContext:
        created_at_raw = data.get(
            "created_at",
        )

        created_at = (
            datetime.fromisoformat(created_at_raw)
            if created_at_raw
            else datetime.now(UTC)
        )

        return cls(
            trace_id=str(data.get("trace_id") or uuid4().hex),
            span_id=str(data.get("span_id") or uuid4().hex[:16]),
            parent_span_id=data.get("parent_span_id"),
            correlation_id=data.get("correlation_id"),
            workflow_id=data.get("workflow_id"),
            execution_id=data.get("execution_id"),
            runtime_id=data.get("runtime_id"),
            node_name=data.get("node_name"),
            created_at=created_at,
            attributes=deepcopy(data.get("attributes", {})),
        )
