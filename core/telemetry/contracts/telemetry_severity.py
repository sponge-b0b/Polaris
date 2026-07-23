from __future__ import annotations

from enum import StrEnum


class TelemetrySeverity(StrEnum):
    """
    Platform telemetry severity levels.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
