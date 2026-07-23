from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from core.storage.persistence.ai_artifacts.ai_artifact_persistence_models import (
    AiArtifactType,
    AiPromptProgramArtifactRecord,
)


class AiArtifactPersistenceRepository(Protocol):
    """Async repository contract for durable AI prompt/program artifacts."""

    async def upsert_artifact(
        self,
        record: AiPromptProgramArtifactRecord,
    ) -> AiPromptProgramArtifactRecord: ...

    async def get_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None: ...

    async def list_artifacts(
        self,
        *,
        target_component: str | None = None,
        artifact_type: AiArtifactType | str | None = None,
        active: bool | None = None,
        limit: int | None = None,
    ) -> Sequence[AiPromptProgramArtifactRecord]: ...

    async def get_active_artifact(
        self,
        target_component: str,
        *,
        artifact_type: AiArtifactType | str | None = None,
    ) -> AiPromptProgramArtifactRecord | None: ...

    async def approve_artifact(
        self,
        artifact_id: str,
        *,
        approved_by: str,
        approved_at: datetime,
    ) -> AiPromptProgramArtifactRecord | None: ...

    async def deactivate_artifact(
        self,
        artifact_id: str,
    ) -> AiPromptProgramArtifactRecord | None: ...
