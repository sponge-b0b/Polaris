from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any


class MetricKind(str, Enum):
    """
    Supported metric kinds.
    """

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass(frozen=True, slots=True)
class MetricPoint:
    """
    Immutable metric point.
    """

    name: str

    kind: MetricKind

    value: float

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    tags: tuple[str, ...] = ()

    attributes: dict[str, Any] = field(
        default_factory=dict,
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": list(self.tags),
            "attributes": deepcopy(self.attributes),
        }


class MetricsStore:
    """
    Lightweight in-memory metrics store.

    PURPOSE
    ============================================================
    Provides platform-local metric accumulation before forwarding to
    external systems such as OpenTelemetry, Prometheus, Datadog, etc.

    This is intentionally simple:
    - counters accumulate
    - gauges overwrite
    - histograms store observed values
    """

    def __init__(
        self,
    ) -> None:
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._points: list[MetricPoint] = []

    # ========================================================
    # RECORDING
    # ========================================================

    def increment(
        self,
        name: str,
        value: float = 1.0,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> MetricPoint:
        self._validate_name(
            name,
        )

        key = self._metric_key(
            name=name,
            tags=tags,
            attributes=attributes or {},
        )

        self._counters[key] = (
            self._counters.get(
                key,
                0.0,
            )
            + value
        )

        point = MetricPoint(
            name=name,
            kind=MetricKind.COUNTER,
            value=self._counters[key],
            tags=tags,
            attributes=deepcopy(attributes or {}),
        )

        self._points.append(
            point,
        )

        return point

    def gauge(
        self,
        name: str,
        value: float,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> MetricPoint:
        self._validate_name(
            name,
        )

        key = self._metric_key(
            name=name,
            tags=tags,
            attributes=attributes or {},
        )

        self._gauges[key] = value

        point = MetricPoint(
            name=name,
            kind=MetricKind.GAUGE,
            value=value,
            tags=tags,
            attributes=deepcopy(attributes or {}),
        )

        self._points.append(
            point,
        )

        return point

    def observe(
        self,
        name: str,
        value: float,
        tags: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
    ) -> MetricPoint:
        self._validate_name(
            name,
        )

        key = self._metric_key(
            name=name,
            tags=tags,
            attributes=attributes or {},
        )

        self._histograms.setdefault(
            key,
            [],
        ).append(
            value,
        )

        point = MetricPoint(
            name=name,
            kind=MetricKind.HISTOGRAM,
            value=value,
            tags=tags,
            attributes=deepcopy(attributes or {}),
        )

        self._points.append(
            point,
        )

        return point

    # ========================================================
    # ACCESS
    # ========================================================

    def points(
        self,
    ) -> tuple[MetricPoint, ...]:
        return tuple(
            self._points,
        )

    def clear(
        self,
    ) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._points.clear()

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                key: list(values) for key, values in self._histograms.items()
            },
            "points": [point.to_dict() for point in self._points],
        }

    # ========================================================
    # INTERNALS
    # ========================================================

    def _validate_name(
        self,
        name: str,
    ) -> None:
        if not name.strip():
            raise ValueError("Metric name cannot be empty.")

    def _metric_key(
        self,
        name: str,
        tags: tuple[str, ...],
        attributes: dict[str, Any],
    ) -> str:
        attribute_parts = [f"{key}={attributes[key]}" for key in sorted(attributes)]

        return "|".join(
            [
                name,
                ",".join(sorted(tags)),
                ",".join(attribute_parts),
            ]
        )
