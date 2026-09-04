from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any

from core.telemetry.sanitization import sanitize_telemetry_value

MAX_TELEMETRY_EXCEPTION_TYPE_CHARACTERS = 256
MAX_TELEMETRY_EXCEPTION_MESSAGE_CHARACTERS = 4 * 1024
MAX_TELEMETRY_STACK_TRACE_CHARACTERS = 32 * 1024
TELEMETRY_EXCEPTION_TEXT_TRUNCATION_MARKER = "...[telemetry text truncated]"
TELEMETRY_STACK_TRACE_TRUNCATION_MARKER = "\n...[telemetry stack trace truncated]"


@dataclass(frozen=True, slots=True)
class TelemetryExceptionDetails:
    """Sanitized, bounded exception details for canonical telemetry events."""

    exception_type: str
    message: str
    stack_trace: str
    stack_trace_truncated: bool = False

    def __post_init__(self) -> None:
        exception_type = _sanitize_and_bound_text(
            self.exception_type,
            max_characters=MAX_TELEMETRY_EXCEPTION_TYPE_CHARACTERS,
            truncation_marker=TELEMETRY_EXCEPTION_TEXT_TRUNCATION_MARKER,
        )
        message = _sanitize_and_bound_text(
            self.message,
            max_characters=MAX_TELEMETRY_EXCEPTION_MESSAGE_CHARACTERS,
            truncation_marker=TELEMETRY_EXCEPTION_TEXT_TRUNCATION_MARKER,
        )
        stack_trace, truncated = _sanitize_and_bound_stack_trace(
            self.stack_trace,
            max_characters=MAX_TELEMETRY_STACK_TRACE_CHARACTERS,
        )
        object.__setattr__(self, "exception_type", exception_type or "Exception")
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "stack_trace", stack_trace)
        object.__setattr__(
            self,
            "stack_trace_truncated",
            self.stack_trace_truncated or truncated,
        )

    @classmethod
    def from_exception(
        cls,
        error: BaseException,
        *,
        max_stack_trace_characters: int = MAX_TELEMETRY_STACK_TRACE_CHARACTERS,
    ) -> TelemetryExceptionDetails:
        stack_trace = "".join(
            traceback.format_exception(
                type(error),
                error,
                error.__traceback__,
            )
        )
        bounded_stack_trace, truncated = _sanitize_and_bound_stack_trace(
            stack_trace,
            max_characters=max_stack_trace_characters,
        )
        return cls(
            exception_type=type(error).__name__,
            message=_sanitize_text(str(error)),
            stack_trace=bounded_stack_trace,
            stack_trace_truncated=truncated,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "exception_type": self.exception_type,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "stack_trace_truncated": self.stack_trace_truncated,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        max_stack_trace_characters: int = MAX_TELEMETRY_STACK_TRACE_CHARACTERS,
    ) -> TelemetryExceptionDetails:
        stack_trace, truncated = _sanitize_and_bound_stack_trace(
            str(data.get("stack_trace", "")),
            max_characters=max_stack_trace_characters,
        )
        return cls(
            exception_type=_sanitize_text(str(data.get("exception_type", "Exception"))),
            message=_sanitize_text(str(data.get("message", ""))),
            stack_trace=stack_trace,
            stack_trace_truncated=(
                bool(data.get("stack_trace_truncated", False)) or truncated
            ),
        )


def _sanitize_text(value: str) -> str:
    sanitized = sanitize_telemetry_value(value)
    return str(sanitized)


def _sanitize_and_bound_text(
    value: str,
    *,
    max_characters: int,
    truncation_marker: str,
) -> str:
    if max_characters <= len(truncation_marker):
        raise ValueError("max_characters must exceed the truncation marker length.")

    sanitized = _sanitize_text(value)
    if len(sanitized) <= max_characters:
        return sanitized

    retained_characters = max_characters - len(truncation_marker)
    return sanitized[:retained_characters] + truncation_marker


def _sanitize_and_bound_stack_trace(
    stack_trace: str,
    *,
    max_characters: int,
) -> tuple[str, bool]:
    if max_characters <= len(TELEMETRY_STACK_TRACE_TRUNCATION_MARKER):
        raise ValueError(
            "max_stack_trace_characters must exceed the truncation marker length."
        )

    sanitized = _sanitize_text(stack_trace)
    if len(sanitized) <= max_characters:
        return sanitized, False

    return (
        _sanitize_and_bound_text(
            sanitized,
            max_characters=max_characters,
            truncation_marker=TELEMETRY_STACK_TRACE_TRUNCATION_MARKER,
        ),
        True,
    )


__all__ = [
    "MAX_TELEMETRY_EXCEPTION_MESSAGE_CHARACTERS",
    "MAX_TELEMETRY_EXCEPTION_TYPE_CHARACTERS",
    "MAX_TELEMETRY_STACK_TRACE_CHARACTERS",
    "TELEMETRY_EXCEPTION_TEXT_TRUNCATION_MARKER",
    "TELEMETRY_STACK_TRACE_TRUNCATION_MARKER",
    "TelemetryExceptionDetails",
]
