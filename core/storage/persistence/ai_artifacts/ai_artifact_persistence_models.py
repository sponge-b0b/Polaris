from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | Mapping[str, "JsonValue"] | Sequence["JsonValue"]
type JsonObject = Mapping[str, JsonValue]

_PROMPT_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
_AUTHENTICATED_URL_PATTERN = re.compile(
    r"^[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@", re.IGNORECASE
)
_SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
    "connection_string",
    "credential",
    "database_url",
    "password",
    "passwd",
    "private_key",
    "secret",
    "token",
)


class AiArtifactType(StrEnum):
    """Durable AI prompt/program artifact categories."""

    SOURCE_CONTROLLED_PROMPT = "source_controlled_prompt"
    LANGFUSE_PROMPT = "langfuse_prompt"
    DSPY_PROGRAM = "dspy_program"
    DSPY_COMPILED_PROMPT = "dspy_compiled_prompt"


class AiArtifactApprovalStatus(StrEnum):
    """Approval lifecycle for AI prompt/program artifacts."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True)
class AiPromptProgramArtifactRecord:
    """Persistence-boundary record for an approved AI prompt/program artifact."""

    artifact_id: str
    artifact_type: AiArtifactType | str
    artifact_name: str
    artifact_version: str
    target_component: str
    model_name: str
    provider_name: str
    prompt_reference: str
    prompt_hash: str
    source: str
    approval_status: AiArtifactApprovalStatus | str = AiArtifactApprovalStatus.DRAFT
    evaluation_dataset_id: str | None = None
    evaluation_run_id: str | None = None
    deepeval_score_summary: JsonObject | None = None
    langfuse_trace_id: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    active: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "artifact_id", _require_non_empty(self.artifact_id, "artifact_id")
        )
        object.__setattr__(
            self, "artifact_type", _coerce_artifact_type(self.artifact_type)
        )
        for field_name in (
            "artifact_name",
            "artifact_version",
            "target_component",
            "model_name",
            "provider_name",
            "source",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty(getattr(self, field_name), field_name),
            )
        object.__setattr__(
            self,
            "prompt_reference",
            _clean_prompt_reference(self.prompt_reference, "prompt_reference"),
        )
        object.__setattr__(
            self, "prompt_hash", _clean_prompt_hash(self.prompt_hash, "prompt_hash")
        )
        object.__setattr__(
            self, "approval_status", _coerce_approval_status(self.approval_status)
        )
        for field_name in (
            "evaluation_dataset_id",
            "evaluation_run_id",
            "langfuse_trace_id",
            "approved_by",
        ):
            object.__setattr__(
                self, field_name, _clean_optional(getattr(self, field_name), field_name)
            )
        _validate_json_object_safety(
            self.deepeval_score_summary,
            "deepeval_score_summary",
        )
        _validate_approval_state(self)


def new_ai_prompt_program_artifact_id() -> str:
    return f"ai_prompt_program_artifact_{uuid4().hex}"


def artifact_type_value(value: AiArtifactType | str) -> str:
    if isinstance(value, AiArtifactType):
        return value.value
    return value


def approval_status_value(value: AiArtifactApprovalStatus | str) -> str:
    if isinstance(value, AiArtifactApprovalStatus):
        return value.value
    return value


def _coerce_artifact_type(value: AiArtifactType | str) -> AiArtifactType:
    if isinstance(value, AiArtifactType):
        return value
    return AiArtifactType(value)


def _coerce_approval_status(
    value: AiArtifactApprovalStatus | str,
) -> AiArtifactApprovalStatus:
    if isinstance(value, AiArtifactApprovalStatus):
        return value
    return AiArtifactApprovalStatus(value)


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


def _clean_optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty when provided.")
    _reject_authenticated_url(cleaned, field_name)
    return cleaned


def _clean_prompt_reference(value: str, field_name: str) -> str:
    cleaned = _require_non_empty(value, field_name)
    if "\n" in cleaned or "\r" in cleaned:
        raise ValueError(f"{field_name} must be a single-line reference.")
    if len(cleaned) > 1024:
        raise ValueError(f"{field_name} must not exceed 1024 characters.")
    _reject_authenticated_url(cleaned, field_name)
    return cleaned


def _clean_prompt_hash(value: str, field_name: str) -> str:
    cleaned = _require_non_empty(value, field_name)
    if not _PROMPT_HASH_PATTERN.fullmatch(cleaned):
        raise ValueError(f"{field_name} must be a 64-character SHA-256 hex digest.")
    return cleaned.lower()


def _validate_approval_state(record: AiPromptProgramArtifactRecord) -> None:
    if record.approval_status is AiArtifactApprovalStatus.APPROVED:
        if record.approved_by is None or record.approved_at is None:
            raise ValueError("approved artifacts require approved_by and approved_at.")
    if (
        record.active
        and record.approval_status is not AiArtifactApprovalStatus.APPROVED
    ):
        raise ValueError("active artifacts must be approved.")


def _validate_json_object_safety(value: JsonObject | None, field_path: str) -> None:
    if value is None:
        return
    _validate_no_secret_material(value, field_path)


def _validate_no_secret_material(value: JsonValue, field_path: str) -> None:
    if isinstance(value, str):
        _reject_authenticated_url(value, field_path)
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = key.lower().replace("-", "_")
            if any(part in normalized_key for part in _SECRET_KEY_PARTS):
                raise ValueError(f"{field_path}.{key} cannot contain secret material.")
            _validate_no_secret_material(nested, f"{field_path}.{key}")
        return
    if isinstance(value, Sequence):
        for index, nested in enumerate(value):
            _validate_no_secret_material(nested, f"{field_path}[{index}]")


def _reject_authenticated_url(value: str, field_name: str) -> None:
    if _AUTHENTICATED_URL_PATTERN.match(value):
        raise ValueError(f"{field_name} must not contain an authenticated URL.")
