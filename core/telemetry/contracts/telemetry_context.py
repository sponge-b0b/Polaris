from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.telemetry.tracing.trace_context import TraceContext


@dataclass(
    frozen=True,
    slots=True,
)
class TelemetryContext:
    """
    Immutable attribution context shared by telemetry emitters.

    Carries platform-neutral trace identity alongside runtime/workflow
    attribution. OpenTelemetry remains a sink boundary concern; these fields
    are the canonical internal trace contract.
    """

    workflow_id: str | None = None
    execution_id: str | None = None
    runtime_id: str | None = None
    node_name: str | None = None
    correlation_id: str | None = None
    tags: tuple[str, ...] = ()
    attributes: dict[str, Any] | None = None
    trace_id: str | None = None
    span_id: str | None = None
    parent_span_id: str | None = None

    @classmethod
    def from_trace_context(
        cls,
        trace_context: TraceContext,
        *,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> TelemetryContext:
        return cls(
            workflow_id=trace_context.workflow_id,
            execution_id=trace_context.execution_id,
            runtime_id=trace_context.runtime_id,
            node_name=trace_context.node_name,
            correlation_id=trace_context.correlation_id,
            tags=tags,
            attributes={
                **dict(trace_context.attributes),
                **dict(attributes or {}),
            },
            trace_id=trace_context.trace_id,
            span_id=trace_context.span_id,
            parent_span_id=trace_context.parent_span_id,
        )

    def with_trace_context(
        self,
        trace_context: TraceContext,
    ) -> TelemetryContext:
        return TelemetryContext(
            workflow_id=self.workflow_id or trace_context.workflow_id,
            execution_id=self.execution_id or trace_context.execution_id,
            runtime_id=self.runtime_id or trace_context.runtime_id,
            node_name=self.node_name or trace_context.node_name,
            correlation_id=self.correlation_id or trace_context.correlation_id,
            tags=self.tags,
            attributes={
                **dict(trace_context.attributes),
                **dict(self.attributes or {}),
            },
            trace_id=trace_context.trace_id,
            span_id=trace_context.span_id,
            parent_span_id=trace_context.parent_span_id,
        )

    def to_trace_context(
        self,
    ) -> TraceContext | None:
        if self.trace_id is None or self.span_id is None:
            return None

        return TraceContext(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            correlation_id=self.correlation_id,
            workflow_id=self.workflow_id,
            execution_id=self.execution_id,
            runtime_id=self.runtime_id,
            node_name=self.node_name,
            attributes=dict(self.attributes or {}),
        )

    def child_operation(
        self,
        *,
        node_name: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TelemetryContext:
        """Create the telemetry context for one bounded child operation."""

        trace_context = self.to_trace_context()
        if trace_context is None:
            operation_context = TraceContext(
                correlation_id=self.correlation_id,
                workflow_id=self.workflow_id,
                execution_id=self.execution_id,
                runtime_id=self.runtime_id,
                node_name=node_name or self.node_name,
                attributes={
                    **dict(self.attributes or {}),
                    **dict(attributes or {}),
                },
            )
        else:
            operation_context = trace_context.child(
                node_name=node_name,
                attributes=attributes,
            )

        return TelemetryContext.from_trace_context(
            operation_context,
            tags=self.tags,
        )

    def trace_attributes(
        self,
    ) -> dict[str, Any]:
        attributes: dict[str, Any] = {}

        if self.trace_id is not None:
            attributes["trace_id"] = self.trace_id

        if self.span_id is not None:
            attributes["span_id"] = self.span_id

        if self.parent_span_id is not None:
            attributes["parent_span_id"] = self.parent_span_id

        return attributes

    def merged_attributes(
        self,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            **dict(self.attributes or {}),
            **dict(attributes or {}),
            **self.trace_attributes(),
        }
