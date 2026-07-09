from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True, slots=True)
class CliSettings:
    completed_run_retention_max_age_days: int | None = None
    completed_run_retention_max_count: int | None = None
    checkpoint_dir: str = "storage/checkpoints"
    artifact_dir: str = "storage/artifacts/runtime"
    telemetry_jsonl_path: str = "storage/telemetry/runtime_telemetry.jsonl"
    plugin_dirs: tuple[str, ...] = ()
    autoload_plugins: bool = False
    enable_observability: bool = False
    enable_opentelemetry: bool = False
    enable_prometheus_metrics: bool = False
    prometheus_metrics_host: str = "0.0.0.0"
    prometheus_metrics_port: int = 9464
    prometheus_metrics_path: str = "/metrics"

    @classmethod
    def from_env(
        cls,
        *,
        plugin_dirs: tuple[Path, ...] | tuple[str, ...] = (),
        autoload_plugins: bool = False,
        environ: Mapping[str, str] | None = None,
    ) -> CliSettings:
        values = os.environ if environ is None else environ

        return cls(
            plugin_dirs=parse_plugin_dirs(
                plugin_dirs,
            ),
            autoload_plugins=autoload_plugins,
            completed_run_retention_max_age_days=_read_optional_int(
                values,
                "POLARIS_COMPLETED_RUN_RETENTION_MAX_AGE_DAYS",
            ),
            completed_run_retention_max_count=_read_optional_int(
                values,
                "POLARIS_COMPLETED_RUN_RETENTION_MAX_COUNT",
            ),
            enable_observability=_read_bool(
                values,
                "POLARIS_ENABLE_OBSERVABILITY",
                default=False,
            ),
            enable_opentelemetry=_read_bool(
                values,
                "POLARIS_ENABLE_OPENTELEMETRY",
                default=False,
            ),
            enable_prometheus_metrics=_read_bool(
                values,
                "POLARIS_ENABLE_PROMETHEUS_METRICS",
                default=False,
            ),
            prometheus_metrics_host=_read_text(
                values,
                "POLARIS_PROMETHEUS_METRICS_HOST",
                default="0.0.0.0",
            ),
            prometheus_metrics_port=_read_int(
                values,
                "POLARIS_PROMETHEUS_METRICS_PORT",
                default=9464,
            ),
            prometheus_metrics_path=_read_text(
                values,
                "POLARIS_PROMETHEUS_METRICS_PATH",
                default="/metrics",
            ),
        )


def parse_plugin_dirs(
    plugin_dirs: tuple[Path, ...] | tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(str(plugin_dir) for plugin_dir in plugin_dirs)


def _read_bool(
    values: Mapping[str, str],
    name: str,
    *,
    default: bool,
) -> bool:
    value = values.get(
        name,
    )
    if value is None or not value.strip():
        return default

    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False

    raise ValueError(f"Invalid boolean CLI environment value: {name}")


def _read_text(
    values: Mapping[str, str],
    name: str,
    *,
    default: str,
) -> str:
    value = values.get(
        name,
    )
    if value is None or not value.strip():
        return default

    return value.strip()


def _read_int(
    values: Mapping[str, str],
    name: str,
    *,
    default: int,
) -> int:
    value = values.get(
        name,
    )
    if value is None or not value.strip():
        return default

    try:
        return int(
            value.strip(),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid integer CLI environment value: {name}") from exc


def _read_optional_int(
    values: Mapping[str, str],
    name: str,
) -> int | None:
    value = values.get(
        name,
    )
    if value is None or not value.strip():
        return None

    try:
        parsed = int(
            value.strip(),
        )
    except ValueError as exc:
        raise ValueError(f"Invalid integer CLI environment value: {name}") from exc

    if parsed < 0:
        raise ValueError(f"Invalid negative CLI environment value: {name}")

    return parsed
