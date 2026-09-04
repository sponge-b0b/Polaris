from __future__ import annotations

from collections.abc import Iterable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import urlparse

from core.telemetry.integrations.prometheus.prometheus_config import (
    PrometheusMetricsConfig,
)
from core.telemetry.metrics.metrics_store import MetricKind, MetricPoint, MetricsStore

_LABEL_VALUE_TYPES = (str, bool, int, float)


class PrometheusMetricsExporter:
    """
    Native Prometheus text exporter for MetricsStore.

    This adapter sits at the observability boundary. It serializes the
    platform's typed in-memory metric points into Prometheus exposition text
    without changing the canonical internal metrics model.
    """

    def __init__(
        self,
        metrics_store: MetricsStore,
        config: PrometheusMetricsConfig | None = None,
    ) -> None:
        self.metrics_store = metrics_store
        self.config = config or PrometheusMetricsConfig()
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    @property
    def running(
        self,
    ) -> bool:
        return self._server is not None and self._thread is not None

    @property
    def server_address(
        self,
    ) -> tuple[str, int] | None:
        if self._server is None:
            return None

        host, port = self._server.server_address[:2]
        return (
            str(host),
            int(port),
        )

    def start(
        self,
    ) -> None:
        if self.running:
            return

        exporter = self

        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(
                self,
            ) -> None:
                request_path = urlparse(self.path).path

                if request_path != exporter.config.path:
                    self.send_response(
                        HTTPStatus.NOT_FOUND,
                    )
                    self.end_headers()
                    return

                body = exporter.render().encode("utf-8")

                self.send_response(
                    HTTPStatus.OK,
                )
                self.send_header(
                    "Content-Type",
                    "text/plain; version=0.0.4; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(body)),
                )
                self.end_headers()
                self.wfile.write(body)

            def log_message(
                self,
                format: str,
                *args: Any,
            ) -> None:
                return

        server = ThreadingHTTPServer(
            (
                self.config.host,
                self.config.port,
            ),
            MetricsHandler,
        )
        thread = Thread(
            target=server.serve_forever,
            daemon=True,
            name="polaris-prometheus-metrics-exporter",
        )
        thread.start()

        self._server = server
        self._thread = thread

    def stop(
        self,
    ) -> None:
        if self._server is None:
            return

        self._server.shutdown()
        self._server.server_close()

        if self._thread is not None:
            self._thread.join(timeout=5.0)

        self._server = None
        self._thread = None

    def render(
        self,
    ) -> str:
        points = self.metrics_store.points()
        lines: list[str] = [
            "# HELP polaris_prometheus_exporter_up Polaris Prometheus exporter health.",
            "# TYPE polaris_prometheus_exporter_up gauge",
            "polaris_prometheus_exporter_up 1.0",
        ]

        for metric_name in sorted(
            {
                self._metric_name(point.name)
                for point in points
                if point.kind is not MetricKind.HISTOGRAM
            }
        ):
            metric_points = [
                point
                for point in points
                if self._metric_name(point.name) == metric_name
                and point.kind is not MetricKind.HISTOGRAM
            ]
            if not metric_points:
                continue

            kind = metric_points[-1].kind
            lines.extend(
                self._render_scalar_metric(
                    metric_name=metric_name,
                    kind=kind,
                    points=metric_points,
                )
            )

        for metric_name in sorted(
            {
                self._metric_name(point.name)
                for point in points
                if point.kind is MetricKind.HISTOGRAM
            }
        ):
            metric_points = [
                point
                for point in points
                if self._metric_name(point.name) == metric_name
                and point.kind is MetricKind.HISTOGRAM
            ]
            if not metric_points:
                continue

            lines.extend(
                self._render_histogram_metric(
                    metric_name=metric_name,
                    points=metric_points,
                )
            )

        return "\n".join(lines) + "\n"

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "exporter": self.__class__.__name__,
            "running": self.running,
            "server_address": self.server_address,
            "config": self.config.to_dict(),
        }

    def _render_scalar_metric(
        self,
        metric_name: str,
        kind: MetricKind,
        points: Iterable[MetricPoint],
    ) -> list[str]:
        latest_points: dict[tuple[tuple[str, str], ...], MetricPoint] = {}

        for point in points:
            labels = self._labels(point)
            latest_points[labels] = point

        lines = [
            f"# HELP {metric_name} Polaris metric {metric_name}.",
            f"# TYPE {metric_name} {kind.value}",
        ]

        for labels, point in sorted(latest_points.items()):
            lines.append(f"{metric_name}{self._format_labels(labels)} {point.value}")

        return lines

    def _render_histogram_metric(
        self,
        metric_name: str,
        points: Iterable[MetricPoint],
    ) -> list[str]:
        observations: dict[tuple[tuple[str, str], ...], list[float]] = {}

        for point in points:
            labels = self._labels(point)
            observations.setdefault(
                labels,
                [],
            ).append(point.value)

        lines = [
            f"# HELP {metric_name} Polaris metric {metric_name}.",
            f"# TYPE {metric_name} histogram",
        ]

        for labels, values in sorted(observations.items()):
            for bucket in self.config.histogram_buckets:
                bucket_labels = labels + (("le", self._format_bucket(bucket)),)
                count = sum(1 for value in values if value <= bucket)
                lines.append(
                    f"{metric_name}_bucket{self._format_labels(bucket_labels)} "
                    f"{float(count)}"
                )

            infinity_labels = labels + (("le", "+Inf"),)
            lines.append(
                f"{metric_name}_bucket{self._format_labels(infinity_labels)} "
                f"{float(len(values))}"
            )
            lines.append(
                f"{metric_name}_count{self._format_labels(labels)} {float(len(values))}"
            )
            lines.append(
                f"{metric_name}_sum{self._format_labels(labels)} {sum(values)}"
            )

        return lines

    def _labels(
        self,
        point: MetricPoint,
    ) -> tuple[tuple[str, str], ...]:
        labels: dict[str, str] = {}

        for key in self.config.label_allowlist:
            value = point.attributes.get(key)
            if isinstance(value, _LABEL_VALUE_TYPES):
                labels[self._label_name(key)] = self._label_value(value)

        if point.tags and "source" in self.config.label_allowlist:
            labels.setdefault(
                "source",
                self._label_value(point.tags[0]),
            )

        if len(point.tags) > 1 and "level" in self.config.label_allowlist:
            labels.setdefault(
                "level",
                self._label_value(point.tags[1]),
            )

        return tuple(sorted(labels.items()))

    def _format_labels(
        self,
        labels: tuple[tuple[str, str], ...],
    ) -> str:
        if not labels:
            return ""

        label_parts = [
            f'{name}="{self._escape_label_value(value)}"' for name, value in labels
        ]
        return "{" + ",".join(label_parts) + "}"

    def _metric_name(
        self,
        name: str,
    ) -> str:
        return self._normalize_identifier(
            value=name,
            allow_colon=True,
            default="polaris_metric",
            prefix="polaris_",
        )

    def _label_name(
        self,
        name: str,
    ) -> str:
        return self._normalize_identifier(
            value=name,
            allow_colon=False,
            default="label",
            prefix="label_",
        )

    def _normalize_identifier(
        self,
        value: str,
        allow_colon: bool,
        default: str,
        prefix: str,
    ) -> str:
        normalized_chars: list[str] = []

        for index, char in enumerate(value.strip()):
            if char.isalnum() or char == "_" or (allow_colon and char == ":"):
                if index == 0 and char.isdigit():
                    normalized_chars.append(prefix)
                normalized_chars.append(char)
            else:
                normalized_chars.append("_")

        normalized = "".join(normalized_chars).strip("_")
        while "__" in normalized:
            normalized = normalized.replace("__", "_")

        return normalized or default

    def _label_value(
        self,
        value: str | bool | int | float,
    ) -> str:
        if isinstance(value, bool):
            return str(value).lower()

        return str(value)

    def _escape_label_value(
        self,
        value: str,
    ) -> str:
        return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

    def _format_bucket(
        self,
        bucket: float,
    ) -> str:
        return f"{bucket:g}"
