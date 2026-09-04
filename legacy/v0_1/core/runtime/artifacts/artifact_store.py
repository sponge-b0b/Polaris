from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.runtime.artifacts.artifact_ref import ArtifactKind, ArtifactRef


class ArtifactStore(ABC):
    """
    Canonical artifact storage contract.
    """

    @abstractmethod
    def save_bytes(
        self,
        data: bytes,
        kind: ArtifactKind,
        name: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        raise NotImplementedError

    @abstractmethod
    def save_json(
        self,
        payload: dict[str, Any] | list[Any],
        name: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        raise NotImplementedError

    @abstractmethod
    def save_text(
        self,
        text: str,
        kind: ArtifactKind = ArtifactKind.TEXT,
        name: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        raise NotImplementedError

    @abstractmethod
    def load_bytes(
        self,
        artifact_ref: ArtifactRef,
    ) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def load_json(
        self,
        artifact_ref: ArtifactRef,
    ) -> dict[str, Any] | list[Any]:
        raise NotImplementedError

    @abstractmethod
    def load_text(
        self,
        artifact_ref: ArtifactRef,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        artifact_ref: ArtifactRef,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        artifact_ref: ArtifactRef,
    ) -> None:
        raise NotImplementedError


class LocalArtifactStore(ArtifactStore):
    """
    Local filesystem artifact store.
    """

    def __init__(
        self,
        base_path: str = "storage/artifacts/runtime",
    ) -> None:
        self.base_path = Path(base_path)

        self.base_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save_bytes(
        self,
        data: bytes,
        kind: ArtifactKind,
        name: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        content_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        artifact_id = uuid4().hex

        safe_workflow = self._safe_path_part(
            workflow_id or "unscoped_workflow",
        )

        safe_execution = self._safe_path_part(
            execution_id or "unscoped_execution",
        )

        extension = self._extension_for_kind(
            kind=kind,
            name=name,
            content_type=content_type,
        )

        file_name = f"{artifact_id}{extension}"

        artifact_dir = self.base_path / safe_workflow / safe_execution

        artifact_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = artifact_dir / file_name
        tmp_path = artifact_dir / f"{file_name}.tmp"

        with open(
            tmp_path,
            "wb",
        ) as file:
            file.write(data)

        tmp_path.replace(
            file_path,
        )

        checksum = self._sha256(
            data,
        )

        final_content_type = (
            content_type
            or mimetypes.guess_type(str(file_path))[0]
            or "application/octet-stream"
        )

        artifact_ref = ArtifactRef(
            artifact_id=artifact_id,
            kind=kind,
            uri=str(file_path),
            workflow_id=workflow_id,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            name=name,
            content_type=final_content_type,
            size_bytes=len(data),
            checksum=checksum,
            metadata=metadata or {},
        )

        artifact_ref.validate()

        return artifact_ref

    def save_json(
        self,
        payload: dict[str, Any] | list[Any],
        name: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        data = json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8")

        return self.save_bytes(
            data=data,
            kind=ArtifactKind.JSON,
            name=name,
            workflow_id=workflow_id,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            content_type="application/json",
            metadata=metadata,
        )

    def save_text(
        self,
        text: str,
        kind: ArtifactKind = ArtifactKind.TEXT,
        name: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
        runtime_id: str | None = None,
        node_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRef:
        return self.save_bytes(
            data=text.encode("utf-8"),
            kind=kind,
            name=name,
            workflow_id=workflow_id,
            execution_id=execution_id,
            runtime_id=runtime_id,
            node_name=node_name,
            content_type=self._content_type_for_kind(
                kind,
            ),
            metadata=metadata,
        )

    def load_bytes(
        self,
        artifact_ref: ArtifactRef,
    ) -> bytes:
        file_path = Path(
            artifact_ref.uri,
        )

        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {file_path}")

        data = file_path.read_bytes()

        checksum = self._sha256(
            data,
        )

        if artifact_ref.checksum and checksum != artifact_ref.checksum:
            raise ValueError(f"Artifact checksum mismatch: {artifact_ref.artifact_id}")

        return data

    def load_json(
        self,
        artifact_ref: ArtifactRef,
    ) -> dict[str, Any] | list[Any]:
        data = self.load_bytes(
            artifact_ref,
        )

        return json.loads(
            data.decode("utf-8"),
        )

    def load_text(
        self,
        artifact_ref: ArtifactRef,
    ) -> str:
        return self.load_bytes(
            artifact_ref,
        ).decode("utf-8")

    def exists(
        self,
        artifact_ref: ArtifactRef,
    ) -> bool:
        return Path(
            artifact_ref.uri,
        ).exists()

    def delete(
        self,
        artifact_ref: ArtifactRef,
    ) -> None:
        file_path = Path(
            artifact_ref.uri,
        )

        if file_path.exists():
            file_path.unlink()

    def _safe_path_part(
        self,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            return "unknown"

        return re.sub(
            r"[^a-zA-Z0-9_.-]+",
            "_",
            value,
        )

    def _sha256(
        self,
        data: bytes,
    ) -> str:
        return hashlib.sha256(
            data,
        ).hexdigest()

    def _extension_for_kind(
        self,
        kind: ArtifactKind,
        name: str | None,
        content_type: str | None,
    ) -> str:
        if name and "." in name:
            suffix = Path(name).suffix

            if suffix:
                return suffix

        if content_type:
            guessed = mimetypes.guess_extension(
                content_type,
            )

            if guessed:
                return guessed

        return {
            ArtifactKind.JSON: ".json",
            ArtifactKind.TEXT: ".txt",
            ArtifactKind.MARKDOWN: ".md",
            ArtifactKind.HTML: ".html",
            ArtifactKind.PDF: ".pdf",
            ArtifactKind.CSV: ".csv",
            ArtifactKind.PARQUET: ".parquet",
            ArtifactKind.IMAGE: ".img",
            ArtifactKind.CHART: ".json",
            ArtifactKind.EMBEDDING: ".json",
            ArtifactKind.VECTOR_INDEX: ".index",
            ArtifactKind.MODEL_OUTPUT: ".json",
            ArtifactKind.REPORT: ".json",
            ArtifactKind.DATASET: ".json",
            ArtifactKind.BINARY: ".bin",
            ArtifactKind.OTHER: ".artifact",
        }[kind]

    def _content_type_for_kind(
        self,
        kind: ArtifactKind,
    ) -> str:
        return {
            ArtifactKind.JSON: "application/json",
            ArtifactKind.TEXT: "text/plain",
            ArtifactKind.MARKDOWN: "text/markdown",
            ArtifactKind.HTML: "text/html",
            ArtifactKind.PDF: "application/pdf",
            ArtifactKind.CSV: "text/csv",
            ArtifactKind.PARQUET: "application/octet-stream",
            ArtifactKind.IMAGE: "application/octet-stream",
            ArtifactKind.CHART: "application/json",
            ArtifactKind.EMBEDDING: "application/json",
            ArtifactKind.VECTOR_INDEX: "application/octet-stream",
            ArtifactKind.MODEL_OUTPUT: "application/json",
            ArtifactKind.REPORT: "application/json",
            ArtifactKind.DATASET: "application/json",
            ArtifactKind.BINARY: "application/octet-stream",
            ArtifactKind.OTHER: "application/octet-stream",
        }[kind]
