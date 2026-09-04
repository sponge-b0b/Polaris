from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from application.observability.ai_observability_contracts import (
    AiMetadata,
    AiMetadataValue,
    AiObservabilityCapturePolicy,
)
from domain.llm import sanitize_reasoning_trace_text

REDACTED_VALUE = "[redacted]"
SENSITIVE_KEY_FRAGMENTS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "cookie",
        "credential",
        "password",
        "private_key",
        "secret",
        "session",
        "token",
    }
)
IDENTIFIER_KEY_FRAGMENTS = frozenset(
    {
        "account",
        "broker_account",
        "customer_id",
        "user_id",
        "client_id",
    }
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(authorization)\s*[:=]\s*bearer\s+[a-z0-9._\-~+/=]+"),
    re.compile(r"(?i)\b(bearer)\s+[a-z0-9._\-~+/=]+"),
    re.compile(
        r"(?i)\b(password|secret|token|api[_-]?key|authorization)\s*[:=]\s*([^\s,;]+)"
    ),
    re.compile(r"://([^\s:/@]+):([^\s/@]+)@"),
)


@dataclass(slots=True)
class AiObservabilityRedactionReport:
    """Mutable redaction accounting for one Langfuse projection payload."""

    redacted_fields: list[str]
    truncated_fields: list[str]
    dropped_fields: list[str]

    @classmethod
    def empty(cls) -> AiObservabilityRedactionReport:
        return cls(redacted_fields=[], truncated_fields=[], dropped_fields=[])

    def record_redacted(self, field_path: str) -> None:
        if field_path not in self.redacted_fields:
            self.redacted_fields.append(field_path)

    def record_truncated(self, field_path: str) -> None:
        if field_path not in self.truncated_fields:
            self.truncated_fields.append(field_path)

    def record_dropped(self, field_path: str) -> None:
        if field_path not in self.dropped_fields:
            self.dropped_fields.append(field_path)

    def to_payload(self) -> dict[str, object]:
        return {
            "redacted_field_count": len(self.redacted_fields),
            "truncated_field_count": len(self.truncated_fields),
            "dropped_field_count": len(self.dropped_fields),
            "redacted_fields": tuple(self.redacted_fields),
            "truncated_fields": tuple(self.truncated_fields),
            "dropped_fields": tuple(self.dropped_fields),
        }


def sanitize_metadata(
    metadata: AiMetadata,
    *,
    policy: AiObservabilityCapturePolicy,
    report: AiObservabilityRedactionReport,
) -> dict[str, AiMetadataValue]:
    """Sanitize scalar metadata before it crosses the Langfuse projection boundary."""

    sanitized: dict[str, AiMetadataValue] = {}
    for key, value in metadata.items():
        field_path = f"metadata.{key}"
        key_normalized = _normalize_key(key)
        if _is_sensitive_key(key_normalized):
            sanitized[key] = REDACTED_VALUE
            report.record_redacted(field_path)
            continue
        if _is_identifier_key(key_normalized) and value is not None:
            sanitized[key] = _hash_identifier(value)
            report.record_redacted(field_path)
            continue
        sanitized[key] = sanitize_metadata_value(
            value,
            field_path=field_path,
            policy=policy,
            report=report,
        )
    return sanitized


def sanitize_metadata_value(
    value: AiMetadataValue,
    *,
    field_path: str,
    policy: AiObservabilityCapturePolicy,
    report: AiObservabilityRedactionReport,
) -> AiMetadataValue:
    if not isinstance(value, str):
        return value
    sanitized = sanitize_text(
        value, field_path=field_path, policy=policy, report=report
    )
    if len(sanitized) > policy.max_metadata_value_characters:
        report.record_truncated(field_path)
        return sanitized[: policy.max_metadata_value_characters]
    return sanitized


def sanitize_text(
    value: str,
    *,
    field_path: str,
    policy: AiObservabilityCapturePolicy,
    report: AiObservabilityRedactionReport,
) -> str:
    sanitized = value
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(_replacement, sanitized)
    if sanitized != value:
        report.record_redacted(field_path)

    reasoning_result = sanitize_reasoning_trace_text(sanitized)
    if reasoning_result.detected:
        report.record_redacted(field_path)
        sanitized = REDACTED_VALUE if reasoning_result.unsafe else reasoning_result.text

    if len(sanitized) > policy.max_payload_characters:
        report.record_truncated(field_path)
        return sanitized[: policy.max_payload_characters]
    return sanitized


def _replacement(match: re.Match[str]) -> str:
    if match.re.pattern.startswith("://"):
        return "://[redacted]@"
    first = match.group(1)
    if first.lower() == "bearer":
        return f"{first} {REDACTED_VALUE}"
    return f"{first}={REDACTED_VALUE}"


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_").replace(".", "_")


def _is_sensitive_key(normalized_key: str) -> bool:
    return any(fragment in normalized_key for fragment in SENSITIVE_KEY_FRAGMENTS)


def _is_identifier_key(normalized_key: str) -> bool:
    return any(fragment in normalized_key for fragment in IDENTIFIER_KEY_FRAGMENTS)


def _hash_identifier(value: object) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
