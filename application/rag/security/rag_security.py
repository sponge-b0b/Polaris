from __future__ import annotations

import re
from dataclasses import dataclass, replace
from html import unescape
from time import perf_counter

from application.rag.contracts.rag_context import RagRetrievedContext
from application.rag.contracts.rag_request import RagRequest
from core.telemetry.emitters.application_rag_telemetry import ApplicationRagTelemetry
from domain.llm.reasoning_trace_safety import sanitize_reasoning_trace_text

_SAFE_FAILURE_ANSWER = (
    "Unable to produce a sufficiently grounded answer from the available curated "
    "context."
)
_EXECUTABLE_BLOCK = re.compile(
    r"(?is)<(?:script|style|noscript|template|iframe|system|developer)\b[^>]*>.*?</(?:script|style|noscript|template|iframe|system|developer)\s*>"
)
_HTML_TAG = re.compile(r"(?is)</?[!a-z][^>]*>")
_SEGMENT_BOUNDARY = re.compile(r"(?<=[.!?])\s+|[\r\n]+")
_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"(?i)\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|system|developer)\s+(?:instructions?|messages?|rules?|prompts?)\b"
        ),
    ),
    (
        "prompt_exfiltration",
        re.compile(
            r"(?i)\b(?:reveal|show|print|return|expose|repeat)\s+(?:your\s+)?(?:system\s+prompt|developer\s+message|(?:hidden\s+)?(?:instructions?|credentials?|secrets?))\b"
        ),
    ),
    (
        "role_override",
        re.compile(
            r"(?i)\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:the\s+)?(?:system|developer|administrator|admin)\b"
        ),
    ),
    (
        "policy_bypass",
        re.compile(
            r"(?i)\b(?:bypass|disable|evade)\s+(?:the\s+)?(?:safety|security|policy|guardrails?|restrictions?)\b"
        ),
    ),
)
_SUSPICIOUS_OUTPUT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    *_INJECTION_PATTERNS,
    (
        "instruction_disclosure",
        re.compile(
            r"(?i)\b(?:system\s+prompt|developer\s+message|hidden\s+instructions?)\s*(?:is|are|:)"
        ),
    ),
    (
        "credential_disclosure",
        re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|password)\s*[:=]"),
    ),
)


@dataclass(
    frozen=True,
    slots=True,
)
class RagSecurityInspection:
    """Deterministic security assessment for one untrusted text value."""

    detected: bool
    signals: tuple[str, ...] = ()


@dataclass(
    frozen=True,
    slots=True,
)
class SanitizedRagText:
    """Sanitized untrusted text and the evidence removed from it."""

    text: str
    injection_detected: bool
    executable_markup_detected: bool
    signals: tuple[str, ...] = ()
    removed_segment_count: int = 0


@dataclass(
    frozen=True,
    slots=True,
)
class RagContextSanitizationResult:
    """Typed result for sanitizing all retrieved contexts in one branch."""

    contexts: tuple[RagRetrievedContext, ...]
    input_count: int
    sanitized_count: int
    dropped_count: int
    injection_count: int
    executable_markup_count: int


class RagSecurityGuard:
    """Canonical application guard for RAG input, evidence, and output text."""

    def __init__(
        self,
        telemetry: ApplicationRagTelemetry | None = None,
    ) -> None:
        self._telemetry = telemetry

    async def inspect_input(self, request: RagRequest) -> RagSecurityInspection:
        started_at = perf_counter()
        inspection = inspect_prompt_injection(request.normalized_query)
        await self._emit(
            request=request,
            operation="rag.security.input_guard",
            duration_seconds=perf_counter() - started_at,
            degraded=inspection.detected,
            attributes={
                "injection_detected": inspection.detected,
                "signal_count": len(inspection.signals),
                "signals": list(inspection.signals),
            },
        )
        return inspection

    async def sanitize_contexts(
        self,
        *,
        request: RagRequest,
        contexts: tuple[RagRetrievedContext, ...],
    ) -> RagContextSanitizationResult:
        started_at = perf_counter()
        sanitized_contexts: list[RagRetrievedContext] = []
        sanitized_count = 0
        injection_count = 0
        executable_markup_count = 0
        for context in contexts:
            text_result = sanitize_untrusted_text(context.text)
            if text_result.injection_detected:
                injection_count += 1
            if text_result.executable_markup_detected:
                executable_markup_count += 1
            sanitized = _context_from_sanitized_text(context, text_result)
            if sanitized is None:
                continue
            sanitized_contexts.append(sanitized)
            if sanitized.metadata.get("security_sanitized") is True:
                sanitized_count += 1
        result = RagContextSanitizationResult(
            contexts=tuple(sanitized_contexts),
            input_count=len(contexts),
            sanitized_count=sanitized_count,
            dropped_count=len(contexts) - len(sanitized_contexts),
            injection_count=injection_count,
            executable_markup_count=executable_markup_count,
        )
        await self._emit(
            request=request,
            operation="rag.security.context_sanitization",
            duration_seconds=perf_counter() - started_at,
            degraded=bool(
                result.sanitized_count
                or result.dropped_count
                or result.injection_count
                or result.executable_markup_count
            ),
            attributes={
                "input_count": result.input_count,
                "output_count": len(result.contexts),
                "sanitized_count": result.sanitized_count,
                "dropped_count": result.dropped_count,
                "injection_count": result.injection_count,
                "executable_markup_count": result.executable_markup_count,
            },
        )
        return result

    async def inspect_output(
        self,
        *,
        request: RagRequest,
        answer_text: str,
    ) -> RagSecurityInspection:
        started_at = perf_counter()
        inspection = inspect_suspicious_output(answer_text)
        await self._emit(
            request=request,
            operation="rag.security.output_guard",
            duration_seconds=perf_counter() - started_at,
            degraded=inspection.detected,
            attributes={
                "suspicious_output_detected": inspection.detected,
                "signal_count": len(inspection.signals),
                "signals": list(inspection.signals),
            },
        )
        return inspection

    async def emit_grounding_failure(
        self,
        *,
        request: RagRequest,
        reason: str,
    ) -> None:
        await self._emit(
            request=request,
            operation="rag.security.grounding_failure",
            duration_seconds=0.0,
            degraded=True,
            attributes={"failed_grounding": True, "reason": reason},
        )

    async def _emit(
        self,
        *,
        request: RagRequest,
        operation: str,
        duration_seconds: float,
        attributes: dict[str, object],
        degraded: bool = False,
    ) -> None:
        if self._telemetry is None:
            return
        emit = (
            self._telemetry.emit_operation_degraded
            if degraded
            else self._telemetry.emit_operation_completed
        )
        await emit(
            self.__class__.__name__,
            operation,
            duration_seconds=duration_seconds,
            correlation_id=request.request_id,
            attributes=attributes,
        )


def inspect_prompt_injection(text: str) -> RagSecurityInspection:
    return _inspect(text, _INJECTION_PATTERNS)


def inspect_suspicious_output(text: str) -> RagSecurityInspection:
    inspection = _inspect(text, _SUSPICIOUS_OUTPUT_PATTERNS)
    reasoning_trace = sanitize_reasoning_trace_text(text)
    if not reasoning_trace.detected:
        return inspection
    return RagSecurityInspection(
        detected=True,
        signals=tuple(dict.fromkeys((*inspection.signals, "model_internal_reasoning"))),
    )


def sanitize_untrusted_text(text: str) -> SanitizedRagText:
    normalized = text.strip()
    if not normalized:
        return SanitizedRagText(
            text="",
            injection_detected=False,
            executable_markup_detected=False,
        )
    without_executable, executable_count = _EXECUTABLE_BLOCK.subn(" ", normalized)
    executable_markup_detected = executable_count > 0
    without_tags, tag_count = _HTML_TAG.subn(" ", without_executable)
    normalized = " ".join(unescape(without_tags).split())
    segments = tuple(
        segment.strip()
        for segment in _SEGMENT_BOUNDARY.split(normalized)
        if segment.strip()
    )
    safe_segments: list[str] = []
    signals: list[str] = []
    removed_segment_count = 0
    for segment in segments:
        inspection = inspect_prompt_injection(segment)
        if inspection.detected:
            removed_segment_count += 1
            signals.extend(inspection.signals)
            continue
        safe_segments.append(segment)
    return SanitizedRagText(
        text=" ".join(safe_segments),
        injection_detected=bool(signals),
        executable_markup_detected=executable_markup_detected,
        signals=tuple(dict.fromkeys(signals)),
        removed_segment_count=removed_segment_count,
    )


def sanitize_retrieved_context(
    context: RagRetrievedContext,
) -> RagRetrievedContext | None:
    return _context_from_sanitized_text(
        context,
        sanitize_untrusted_text(context.text),
    )


def _context_from_sanitized_text(
    context: RagRetrievedContext,
    sanitized: SanitizedRagText,
) -> RagRetrievedContext | None:
    if not sanitized.text:
        return None
    changed = sanitized.text != context.text.strip()
    if (
        not changed
        and not sanitized.injection_detected
        and not sanitized.executable_markup_detected
    ):
        return context
    return replace(
        context,
        text=sanitized.text,
        metadata={
            **dict(context.metadata),
            "security_sanitized": changed,
            "security_injection_detected": sanitized.injection_detected,
            "security_executable_markup_detected": (
                sanitized.executable_markup_detected
            ),
            "security_signals": list(sanitized.signals),
            "security_removed_segment_count": sanitized.removed_segment_count,
        },
    )


def safe_grounding_failure_answer() -> str:
    return _SAFE_FAILURE_ANSWER


def _inspect(
    text: str,
    patterns: tuple[tuple[str, re.Pattern[str]], ...],
) -> RagSecurityInspection:
    signals = tuple(name for name, pattern in patterns if pattern.search(text))
    return RagSecurityInspection(
        detected=bool(signals),
        signals=signals,
    )
