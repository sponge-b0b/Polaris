from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.storage.persistence.ai_artifacts import AiArtifactApprovalStatus
from core.storage.persistence.ai_artifacts import AiArtifactPersistenceRepository
from core.storage.persistence.ai_artifacts import AiArtifactType
from core.storage.persistence.ai_artifacts import AiPromptProgramArtifactRecord
from core.storage.persistence.ai_artifacts import approval_status_value
from core.storage.persistence.ai_artifacts import artifact_type_value

RAG_ANSWER_GENERATION_ARTIFACT_TARGET = "rag_answer_generation"


@dataclass(frozen=True, slots=True)
class ResolvedAiPromptArtifact:
    """Approved prompt/program artifact selected for runtime generation."""

    artifact_id: str
    artifact_type: str
    artifact_name: str
    artifact_version: str
    target_component: str
    model_name: str
    provider_name: str
    prompt_reference: str
    prompt_hash: str
    source: str
    evaluation_dataset_id: str | None = None
    evaluation_run_id: str | None = None
    langfuse_trace_id: str | None = None

    @classmethod
    def from_record(
        cls,
        record: AiPromptProgramArtifactRecord,
    ) -> ResolvedAiPromptArtifact:
        return cls(
            artifact_id=record.artifact_id,
            artifact_type=artifact_type_value(record.artifact_type),
            artifact_name=record.artifact_name,
            artifact_version=record.artifact_version,
            target_component=record.target_component,
            model_name=record.model_name,
            provider_name=record.provider_name,
            prompt_reference=record.prompt_reference,
            prompt_hash=record.prompt_hash,
            source=record.source,
            evaluation_dataset_id=record.evaluation_dataset_id,
            evaluation_run_id=record.evaluation_run_id,
            langfuse_trace_id=record.langfuse_trace_id,
        )

    def to_metadata(self) -> dict[str, str]:
        metadata = {
            "ai_artifact_id": self.artifact_id,
            "ai_artifact_type": self.artifact_type,
            "ai_artifact_target_component": self.target_component,
            "ai_artifact_prompt_reference": self.prompt_reference,
            "ai_artifact_model": self.model_name,
            "ai_artifact_provider": self.provider_name,
            "prompt_name": self.artifact_name,
            "prompt_version": self.artifact_version,
            "prompt_hash": self.prompt_hash,
            "prompt_source": self.source,
        }
        for key, value in (
            ("ai_artifact_evaluation_dataset_id", self.evaluation_dataset_id),
            ("ai_artifact_evaluation_run_id", self.evaluation_run_id),
            ("ai_artifact_langfuse_trace_id", self.langfuse_trace_id),
        ):
            if value is not None:
                metadata[key] = value
        return metadata


class AiPromptArtifactResolver(Protocol):
    """Runtime boundary for resolving an approved prompt/program artifact."""

    async def resolve_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> ResolvedAiPromptArtifact | None: ...


@dataclass(frozen=True, slots=True)
class ActiveAiPromptArtifactResolver:
    """Resolve approved active prompt/program artifacts from persistence."""

    repository: AiArtifactPersistenceRepository

    async def resolve_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> ResolvedAiPromptArtifact | None:
        record = await self.repository.get_active_artifact(
            target_component,
            artifact_type=artifact_type,
        )
        if record is None:
            return None
        if not record.active:
            return None
        if (
            approval_status_value(record.approval_status)
            != AiArtifactApprovalStatus.APPROVED.value
        ):
            return None
        return ResolvedAiPromptArtifact.from_record(record)
