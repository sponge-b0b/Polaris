from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any

from core.telemetry.events.telemetry_event import TelemetryEvent


@dataclass(frozen=True, slots=True)
class TelemetryAttribution:
    """
    Immutable attribution metadata for telemetry events.

    PURPOSE
    ============================================================
    Provides consistent attribution across:
    - workflows
    - runtime nodes
    - plugins
    - agents
    - tools
    - external integrations
    - model/provider calls
    """

    source: str

    component: str | None = None

    actor: str | None = None

    owner: str | None = None

    workflow_id: str | None = None

    execution_id: str | None = None

    runtime_id: str | None = None

    node_name: str | None = None

    plugin_name: str | None = None

    provider: str | None = None

    model: str | None = None

    strategy_id: str | None = None

    account_id: str | None = None

    correlation_id: str | None = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    attributes: dict[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "source": self.source,
            "component": self.component,
            "actor": self.actor,
            "owner": self.owner,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "node_name": self.node_name,
            "plugin_name": self.plugin_name,
            "provider": self.provider,
            "model": self.model,
            "strategy_id": self.strategy_id,
            "account_id": self.account_id,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
            "attributes": deepcopy(self.attributes),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> TelemetryAttribution:
        created_at_raw = data.get(
            "created_at",
        )

        created_at = (
            datetime.fromisoformat(created_at_raw)
            if created_at_raw
            else datetime.now(timezone.utc)
        )

        return cls(
            source=str(data["source"]),
            component=data.get("component"),
            actor=data.get("actor"),
            owner=data.get("owner"),
            workflow_id=data.get("workflow_id"),
            execution_id=data.get("execution_id"),
            runtime_id=data.get("runtime_id"),
            node_name=data.get("node_name"),
            plugin_name=data.get("plugin_name"),
            provider=data.get("provider"),
            model=data.get("model"),
            strategy_id=data.get("strategy_id"),
            account_id=data.get("account_id"),
            correlation_id=data.get("correlation_id"),
            created_at=created_at,
            attributes=deepcopy(data.get("attributes", {})),
        )


class TelemetryAttributionManager:
    """
    Applies attribution metadata to TelemetryEvent objects.
    """

    def __init__(
        self,
        default_attribution: TelemetryAttribution | None = None,
    ) -> None:
        self.default_attribution = default_attribution

    def apply(
        self,
        event: TelemetryEvent,
        attribution: TelemetryAttribution | None = None,
    ) -> TelemetryEvent:
        final_attribution = attribution or self.default_attribution

        if final_attribution is None:
            return event

        attribution_data = final_attribution.to_dict()

        return TelemetryEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            source=event.source,
            timestamp=event.timestamp,
            level=event.level,
            workflow_id=event.workflow_id or final_attribution.workflow_id,
            execution_id=event.execution_id or final_attribution.execution_id,
            runtime_id=event.runtime_id or final_attribution.runtime_id,
            node_name=event.node_name or final_attribution.node_name,
            correlation_id=(event.correlation_id or final_attribution.correlation_id),
            trace_id=event.trace_id,
            span_id=event.span_id,
            parent_span_id=event.parent_span_id,
            duration_seconds=event.duration_seconds,
            success=event.success,
            error_count=event.error_count,
            exception_details=event.exception_details,
            tags=event.tags,
            attributes={
                **deepcopy(attribution_data),
                **deepcopy(event.attributes),
            },
            payload=deepcopy(event.payload),
        )

    def with_default(
        self,
        attribution: TelemetryAttribution,
    ) -> TelemetryAttributionManager:
        return TelemetryAttributionManager(
            default_attribution=attribution,
        )
