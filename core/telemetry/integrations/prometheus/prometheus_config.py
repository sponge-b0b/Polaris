from __future__ import annotations

from dataclasses import dataclass


DEFAULT_PROMETHEUS_LABEL_ALLOWLIST: tuple[str, ...] = (
    "source",
    "event_type",
    "level",
    "workflow_name",
    "node_name",
    "service_name",
    "component_name",
    "provider_name",
    "operation",
    "outcome",
    "success",
)

SAFE_PROMETHEUS_LABELS: frozenset[str] = frozenset(
    {
        "agent_name",
        "component_name",
        "event_type",
        "level",
        "node_name",
        "operation",
        "outcome",
        "provider_name",
        "service_name",
        "signal_name",
        "source",
        "success",
        "workflow_name",
    }
)


DEFAULT_PROMETHEUS_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


@dataclass(frozen=True, slots=True)
class PrometheusMetricsConfig:
    """
    Configuration for the native Prometheus metrics exporter.

    The exporter intentionally uses a constrained label allowlist to avoid
    leaking high-cardinality runtime identifiers into Prometheus.
    """

    host: str = "0.0.0.0"
    port: int = 9464
    path: str = "/metrics"
    label_allowlist: tuple[str, ...] = DEFAULT_PROMETHEUS_LABEL_ALLOWLIST
    histogram_buckets: tuple[float, ...] = DEFAULT_PROMETHEUS_HISTOGRAM_BUCKETS

    def __post_init__(
        self,
    ) -> None:
        if not self.host.strip():
            raise ValueError("Prometheus metrics host cannot be empty.")

        if self.port < 0 or self.port > 65535:
            raise ValueError("Prometheus metrics port must be between 0 and 65535.")

        if not self.path.startswith("/") or not self.path.strip():
            raise ValueError("Prometheus metrics path must start with '/'.")

        if any(char.isspace() for char in self.path):
            raise ValueError("Prometheus metrics path cannot contain whitespace.")

        if not self.label_allowlist:
            raise ValueError("Prometheus label allowlist cannot be empty.")

        unsafe_labels = tuple(
            label
            for label in self.label_allowlist
            if label not in SAFE_PROMETHEUS_LABELS
        )
        if unsafe_labels:
            raise ValueError(
                "Prometheus labels must use the bounded platform allowlist; "
                f"unsupported labels: {', '.join(unsafe_labels)}."
            )

        if not self.histogram_buckets:
            raise ValueError("Prometheus histogram buckets cannot be empty.")

        if tuple(sorted(self.histogram_buckets)) != self.histogram_buckets:
            raise ValueError("Prometheus histogram buckets must be sorted ascending.")

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "path": self.path,
            "label_allowlist": list(self.label_allowlist),
            "histogram_buckets": list(self.histogram_buckets),
        }
