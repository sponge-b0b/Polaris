from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any


class ArtifactKind(str, Enum):
    """
    Canonical artifact kind taxonomy.
    """

    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    PARQUET = "parquet"
    IMAGE = "image"
    CHART = "chart"
    EMBEDDING = "embedding"
    VECTOR_INDEX = "vector_index"
    MODEL_OUTPUT = "model_output"
    REPORT = "report"
    DATASET = "dataset"
    BINARY = "binary"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """
    Immutable artifact reference.

    PURPOSE
    ============================================================
    Stores metadata and location for persisted runtime artifacts.

    IMPORTANT
    ============================================================
    ArtifactRef does NOT contain the artifact payload.
    It only references where the artifact lives.
    """

    artifact_id: str

    kind: ArtifactKind

    uri: str

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    workflow_id: str | None = None

    execution_id: str | None = None

    runtime_id: str | None = None

    node_name: str | None = None

    name: str | None = None

    content_type: str | None = None

    size_bytes: int | None = None

    checksum: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    def validate(
        self,
    ) -> None:
        if not self.artifact_id.strip():
            raise ValueError("artifact_id cannot be empty.")

        if not self.uri.strip():
            raise ValueError("artifact uri cannot be empty.")

        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative.")

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind.value,
            "uri": self.uri,
            "created_at": self.created_at.isoformat(),
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "runtime_id": self.runtime_id,
            "node_name": self.node_name,
            "name": self.name,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ArtifactRef:
        created_at_raw = data.get("created_at")

        created_at = (
            datetime.fromisoformat(created_at_raw)
            if created_at_raw
            else datetime.now(timezone.utc)
        )

        artifact_ref = cls(
            artifact_id=str(data["artifact_id"]),
            kind=ArtifactKind(data.get("kind", ArtifactKind.OTHER.value)),
            uri=str(data["uri"]),
            created_at=created_at,
            workflow_id=data.get("workflow_id"),
            execution_id=data.get("execution_id"),
            runtime_id=data.get("runtime_id"),
            node_name=data.get("node_name"),
            name=data.get("name"),
            content_type=data.get("content_type"),
            size_bytes=data.get("size_bytes"),
            checksum=data.get("checksum"),
            metadata=deepcopy(data.get("metadata", {})),
        )

        artifact_ref.validate()

        return artifact_ref
