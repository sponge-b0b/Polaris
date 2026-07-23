from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from typer.testing import CliRunner

from core.storage.persistence.ai_artifacts import (
    AiArtifactApprovalStatus,
    AiArtifactType,
    AiPromptProgramArtifactRecord,
)
from interfaces.cli.app import create_app
from interfaces.cli.commands import ai_command
from interfaces.cli.services.ai_command_service import (
    AiArtifactCommandResult,
    AiArtifactListCommandResult,
    AiOptimizeCommandResult,
)


@dataclass(slots=True)
class FakeAiCommandService:
    async def optimize(
        self,
        *,
        target: str,
        dataset: str,
        model: str | None = None,
        prompt_name: str | None = None,
        prompt_version: str = "v1",
        artifact_name: str | None = None,
        artifact_version: str = "v1",
        max_cases: int | None = None,
        timeout_seconds: float | None = None,
    ) -> AiOptimizeCommandResult:
        return AiOptimizeCommandResult(
            success=target == "rag_answer_generation"
            and dataset == "golden_rag_questions",
            message="AI optimization completed.",
        )

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: str | None = None,
        active: bool | None = None,
        limit: int | None = 20,
    ) -> AiArtifactListCommandResult:
        return AiArtifactListCommandResult(
            success=True,
            artifacts=(_artifact("artifact-1", active=bool(active)),),
        )

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str = "cli",
    ) -> AiArtifactCommandResult:
        return AiArtifactCommandResult(
            success=True,
            message="AI artifact approved. Activate it explicitly before runtime use.",
            artifact=_artifact(artifact_id, approved_by=approved_by),
        )

    async def activate_artifact(self, artifact_id: str) -> AiArtifactCommandResult:
        if artifact_id == "draft-1":
            return AiArtifactCommandResult(
                success=False,
                message="AI artifact activation was denied.",
                error="Only approved AI artifacts can be activated.",
                artifact=_artifact("draft-1"),
            )
        return AiArtifactCommandResult(
            success=True,
            message="AI artifact activated.",
            artifact=_artifact(artifact_id, active=True),
        )

    async def deactivate_artifact(self, artifact_id: str) -> AiArtifactCommandResult:
        return AiArtifactCommandResult(
            success=True,
            message="AI artifact deactivated.",
            artifact=_artifact(artifact_id, active=False),
        )


def test_ai_optimize_command_renders_result(monkeypatch) -> None:
    monkeypatch.setattr(ai_command, "AiCommandService", FakeAiCommandService)
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        [
            "ai",
            "optimize",
            "--target",
            "rag_answer_generation",
            "--dataset",
            "golden_rag_questions",
        ],
    )

    assert result.exit_code == 0
    assert "AI Optimization" in result.output
    assert "Status: succeeded" in result.output


def test_ai_artifacts_list_command_renders_artifacts(monkeypatch) -> None:
    monkeypatch.setattr(ai_command, "AiCommandService", FakeAiCommandService)
    runner = CliRunner()

    result = runner.invoke(create_app(), ["ai", "artifacts", "list", "--active"])

    assert result.exit_code == 0
    assert "AI Artifacts" in result.output
    assert "artifact-1" in result.output
    assert "Active: yes" in result.output


def test_ai_artifact_approve_command_renders_explicit_activation_message(
    monkeypatch,
) -> None:
    monkeypatch.setattr(ai_command, "AiCommandService", FakeAiCommandService)
    runner = CliRunner()

    result = runner.invoke(
        create_app(),
        ["ai", "artifacts", "approve", "artifact-1", "--approved-by", "reviewer"],
    )

    assert result.exit_code == 0
    assert "AI artifact approved" in result.output
    assert "Activate it explicitly" in result.output
    assert "Approved by: reviewer" in result.output


def test_ai_artifact_activate_command_exits_nonzero_when_denied(monkeypatch) -> None:
    monkeypatch.setattr(ai_command, "AiCommandService", FakeAiCommandService)
    runner = CliRunner()

    result = runner.invoke(create_app(), ["ai", "artifacts", "activate", "draft-1"])

    assert result.exit_code == 1
    assert "activation was denied" in result.output
    assert "Only approved AI artifacts can be activated" in result.output


def test_ai_artifact_deactivate_command_renders_success(monkeypatch) -> None:
    monkeypatch.setattr(ai_command, "AiCommandService", FakeAiCommandService)
    runner = CliRunner()

    result = runner.invoke(
        create_app(), ["ai", "artifacts", "deactivate", "artifact-1"]
    )

    assert result.exit_code == 0
    assert "AI artifact deactivated" in result.output


def _artifact(
    artifact_id: str,
    *,
    approved_by: str | None = None,
    active: bool = False,
) -> AiPromptProgramArtifactRecord:
    approval_status = (
        AiArtifactApprovalStatus.APPROVED
        if approved_by is not None or active
        else AiArtifactApprovalStatus.DRAFT
    )
    return AiPromptProgramArtifactRecord(
        artifact_id=artifact_id,
        artifact_type=AiArtifactType.DSPY_COMPILED_PROMPT,
        artifact_name="rag_answer_generation_dspy",
        artifact_version="v1",
        target_component="rag_answer_generation",
        model_name="qwen2.5:7b",
        provider_name="dspy",
        prompt_reference=f"dspy://rag_answer_generation/{artifact_id}",
        prompt_hash=hashlib.sha256(artifact_id.encode("utf-8")).hexdigest(),
        source="tests",
        approval_status=approval_status,
        approved_by=approved_by or ("reviewer" if active else None),
        approved_at=datetime(2026, 7, 15, tzinfo=UTC)
        if approved_by is not None or active
        else None,
        active=active,
    )
