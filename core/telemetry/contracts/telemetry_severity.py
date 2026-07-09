from __future__ import annotations

from enum import Enum


class TelemetrySeverity(str, Enum):
    """
    Platform telemetry severity levels.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
