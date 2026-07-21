from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

_REASONING_BLOCK_TAG_NAMES = (
    "think",
    "thinking",
    "reasoning",
    "chain_of_thought",
    "chain-of-thought",
    "scratchpad",
)
_REASONING_TAG_NAMES_PATTERN = "|".join(
    re.escape(name) for name in _REASONING_BLOCK_TAG_NAMES
)
_COMPLETE_TAGGED_REASONING_PATTERN = re.compile(
    rf"(?is)<\s*(?:{_REASONING_TAG_NAMES_PATTERN})\s*>.*?"
    rf"<\s*/\s*(?:{_REASONING_TAG_NAMES_PATTERN})\s*>"
)
_UNCLOSED_TAGGED_REASONING_PATTERN = re.compile(
    rf"(?is)<\s*(?:{_REASONING_TAG_NAMES_PATTERN})\s*>"
)
_REASONING_FENCE_PATTERN = re.compile(
    r"(?is)```\s*(?:thinking|reasoning|scratchpad|chain[-_ ]?of[-_ ]?thought)\s+.*?```"
)
_PREFIXED_REASONING_PATTERN = re.compile(
    r"(?is)^\s*(?:chain[-_ ]?of[-_ ]?thought|scratchpad|internal\s+reasoning|"
    r"hidden\s+reasoning|reasoning\s+trace|thinking)\s*:\s*.*?"
    r"(?:\n\s*(?:final\s+answer|answer|response)\s*:\s*)"
)
_REASONING_MARKER_PATTERN = re.compile(
    r"(?is)<\s*/?\s*(?:think|thinking|reasoning|chain[_-]?of[_-]?thought|scratchpad)\b|"
    r"```\s*(?:thinking|reasoning|scratchpad|chain[-_ ]?of[-_ ]?thought)\b|"
    r"^\s*(?:chain[-_ ]?of[-_ ]?thought|scratchpad|internal\s+reasoning|"
    r"hidden\s+reasoning|reasoning\s+trace|thinking)\s*:",
    re.MULTILINE,
)
_MODEL_INTERNAL_REASONING_KEYS = frozenset(
    {
        "chain_of_thought",
        "hidden_reasoning",
        "internal_reasoning",
        "model_reasoning",
        "reasoning_trace",
        "scratchpad",
        "think",
        "thinking",
    }
)
_REASONING_KEY_SEPARATOR_PATTERN = re.compile(r"[\s-]+")


class ReasoningTracePolicy(StrEnum):
    """Publication policy for model-internal reasoning traces."""

    STRIP_TEXT_REJECT_JSON = "strip_text_reject_json"
    REJECT = "reject"


class ReasoningTraceViolationError(ValueError):
    """Raised when model-internal reasoning contaminates a boundary payload."""


@dataclass(frozen=True, slots=True)
class ReasoningTraceSanitizationResult:
    """Result of inspecting text for model-internal reasoning artifacts."""

    text: str
    detected: bool
    stripped: bool
    unsafe: bool
    marker_count: int

    @property
    def action(self) -> str:
        if self.unsafe:
            return "rejected"
        if self.stripped:
            return "stripped"
        return "none"


def sanitize_reasoning_trace_text(value: str) -> ReasoningTraceSanitizationResult:
    """
    Remove safely delimited reasoning traces from publishable text.

    The sanitizer only removes high-signal, model-internal reasoning formats such
    as thinking tags, reasoning fences, or labeled scratchpad prefixes. Ambiguous
    or unclosed markers are marked unsafe so callers can fail closed instead of
    publishing hidden deliberation.
    """

    marker_count = len(_REASONING_MARKER_PATTERN.findall(value))
    if marker_count == 0:
        return ReasoningTraceSanitizationResult(
            text=value.strip(),
            detected=False,
            stripped=False,
            unsafe=False,
            marker_count=0,
        )

    sanitized = value
    sanitized = _COMPLETE_TAGGED_REASONING_PATTERN.sub("", sanitized)
    sanitized = _REASONING_FENCE_PATTERN.sub("", sanitized)
    sanitized = _PREFIXED_REASONING_PATTERN.sub("", sanitized)
    sanitized = sanitized.strip()
    unsafe = bool(_REASONING_MARKER_PATTERN.search(sanitized))
    if _UNCLOSED_TAGGED_REASONING_PATTERN.search(sanitized):
        unsafe = True
    if not sanitized:
        unsafe = True

    return ReasoningTraceSanitizationResult(
        text=sanitized,
        detected=True,
        stripped=sanitized != value.strip(),
        unsafe=unsafe,
        marker_count=marker_count,
    )


def sanitize_reasoning_trace_text_for_boundary(
    value: str,
    *,
    boundary_name: str,
    allow_empty: bool = True,
    strip_safe_text: bool = True,
) -> str:
    """
    Return publishable text for a typed or durable boundary.

    Safely delimited reasoning traces are stripped. Ambiguous, unclosed, or
    reasoning-only content fails closed with a generic error that identifies the
    boundary without echoing the hidden text.
    """

    result = sanitize_reasoning_trace_text(value)
    if result.unsafe or (not allow_empty and not result.text):
        _raise_reasoning_trace_violation(boundary_name)

    if not strip_safe_text and not result.detected:
        return value

    return result.text


def sanitize_reasoning_trace_payload(
    value: object,
    *,
    boundary_name: str,
) -> object:
    """
    Remove model-internal reasoning artifacts from nested boundary payloads.

    Explicit reasoning-key fields are excluded entirely because their values are
    model-private by contract. Other string values are sanitized like publishable
    text and fail closed if contaminated by unsafe markers.
    """

    if isinstance(value, str):
        return sanitize_reasoning_trace_text_for_boundary(
            value,
            boundary_name=boundary_name,
        )

    if isinstance(value, Mapping):
        sanitized: dict[str, object] = {}
        for key, item in value.items():
            key_text = str(key)
            if is_model_internal_reasoning_key(key_text):
                continue
            sanitized[key_text] = sanitize_reasoning_trace_payload(
                item,
                boundary_name=f"{boundary_name}.{key_text}",
            )
        return sanitized

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return tuple(
            sanitize_reasoning_trace_payload(
                item,
                boundary_name=f"{boundary_name}[]",
            )
            for item in value
        )

    return value


def is_model_internal_reasoning_key(key: str) -> bool:
    """Return True for payload keys reserved for model-private deliberation."""

    normalized = _REASONING_KEY_SEPARATOR_PATTERN.sub("_", key.strip().lower())
    return normalized in _MODEL_INTERNAL_REASONING_KEYS


def reject_reasoning_trace(value: str, *, boundary_name: str) -> None:
    """Fail closed when a boundary payload contains a reasoning trace marker."""

    result = sanitize_reasoning_trace_text(value)
    if result.detected:
        _raise_reasoning_trace_violation(boundary_name)


def _raise_reasoning_trace_violation(boundary_name: str) -> None:
    raise ReasoningTraceViolationError(
        "Model-internal reasoning trace detected at "
        f"{boundary_name}; refusing to publish or parse contaminated content."
    )
