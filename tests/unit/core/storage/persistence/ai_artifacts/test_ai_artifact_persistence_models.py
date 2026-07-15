from __future__ import annotations

from datetime import datetime
from datetime import timezone
import hashlib

import pytest

from core.storage.persistence.ai_artifacts import AiArtifactApprovalStatus
from core.storage.persistence.ai_artifacts import AiArtifactType
from core.storage.persistence.ai_artifacts import AiPromptProgramArtifactRecord
from core.storage.persistence.ai_artifacts import JsonObject
from core.storage.persistence.ai_artifacts import new_ai_prompt_program_artifact_id


def test_ai_prompt_program_artifact_record_normalizes_required_fields() -> None:
    record = _record(
        artifact_type="langfuse_prompt",
        approval_status="approved",
        approved_by=" ai-reviewer ",
        approved_at=datetime(2026, 7, 15, tzinfo=timezone.utc),
        active=True,
    )

    assert record.artifact_type is AiArtifactType.LANGFUSE_PROMPT
    assert record.approval_status is AiArtifactApprovalStatus.APPROVED
    assert record.approved_by == "ai-reviewer"
    assert record.prompt_hash == _hash().lower()


def test_approved_artifact_requires_identity_and_timestamp() -> None:
    with pytest.raises(ValueError, match="approved artifacts require"):
        _record(approval_status=AiArtifactApprovalStatus.APPROVED)


def test_active_artifact_must_be_approved() -> None:
    with pytest.raises(ValueError, match="active artifacts must be approved"):
        _record(active=True)


def test_prompt_hash_requires_sha256_digest() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        _record(prompt_hash="not-a-digest")


def test_prompt_reference_rejects_authenticated_urls() -> None:
    with pytest.raises(ValueError, match="authenticated URL"):
        _record(
            prompt_reference="https://username:credential@example.invalid/prompts/rag"
        )


def test_score_summary_rejects_secret_like_keys() -> None:
    with pytest.raises(ValueError, match="secret material"):
        _record(deepeval_score_summary={"api_key": "redacted", "score": 0.9})


def test_new_artifact_id_has_stable_prefix() -> None:
    assert new_ai_prompt_program_artifact_id().startswith("ai_prompt_program_artifact_")


def _record(
    *,
    artifact_type: AiArtifactType | str = AiArtifactType.SOURCE_CONTROLLED_PROMPT,
    approval_status: AiArtifactApprovalStatus | str = AiArtifactApprovalStatus.DRAFT,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
    active: bool = False,
    prompt_reference: str = "prompts/rag/answer_generation.md",
    prompt_hash: str | None = None,
    deepeval_score_summary: JsonObject | None = None,
) -> AiPromptProgramArtifactRecord:
    return AiPromptProgramArtifactRecord(
        artifact_id="artifact-1",
        artifact_type=artifact_type,
        artifact_name="rag-answer-prompt",
        artifact_version="2026.07.15",
        target_component="application.rag.answer_generation",
        model_name="qwen3.5:4b",
        provider_name="ollama",
        prompt_reference=prompt_reference,
        prompt_hash=prompt_hash or _hash(),
        source="source_control",
        approval_status=approval_status,
        approved_by=approved_by,
        approved_at=approved_at,
        active=active,
        deepeval_score_summary=deepeval_score_summary,
    )


def _hash() -> str:
    return hashlib.sha256(b"canonical prompt fixture").hexdigest()
