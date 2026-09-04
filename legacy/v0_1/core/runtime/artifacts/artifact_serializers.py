from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from core.runtime.artifacts.artifact_ref import ArtifactKind


class SerializedArtifact:
    """
    Lightweight serialized artifact payload.
    """

    def __init__(
        self,
        data: bytes,
        kind: ArtifactKind,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.data = data
        self.kind = kind
        self.content_type = content_type
        self.metadata = metadata or {}


class ArtifactSerializer(Protocol):
    """
    Artifact serializer contract.
    """

    def can_serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> bool: ...

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact: ...


class JsonArtifactSerializer:
    """
    Serializes dict/list/dataclass/Pydantic payloads to JSON.
    """

    def can_serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> bool:
        return isinstance(payload, dict | list | BaseModel) or (
            is_dataclass(payload) and not isinstance(payload, type)
        )

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact:
        if isinstance(payload, BaseModel):
            json_payload = payload.model_dump(
                mode="json",
            )
        elif is_dataclass(payload) and not isinstance(payload, type):
            json_payload = asdict(payload)
        else:
            json_payload = payload

        return SerializedArtifact(
            data=json.dumps(
                json_payload,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8"),
            kind=ArtifactKind.JSON,
            content_type="application/json",
            metadata={
                "serializer": self.__class__.__name__,
            },
        )


class TextArtifactSerializer:
    """
    Serializes string payloads.
    """

    def can_serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> bool:
        return isinstance(payload, str)

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact:
        lower_name = (name or "").lower()

        if lower_name.endswith(".md"):
            kind = ArtifactKind.MARKDOWN
            content_type = "text/markdown"
        elif lower_name.endswith(".html"):
            kind = ArtifactKind.HTML
            content_type = "text/html"
        else:
            kind = ArtifactKind.TEXT
            content_type = "text/plain"

        return SerializedArtifact(
            data=payload.encode("utf-8"),
            kind=kind,
            content_type=content_type,
            metadata={
                "serializer": self.__class__.__name__,
            },
        )


class BytesArtifactSerializer:
    """
    Pass-through serializer for bytes.
    """

    def can_serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> bool:
        return isinstance(payload, bytes)

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact:
        return SerializedArtifact(
            data=payload,
            kind=_infer_binary_kind(name),
            content_type="application/octet-stream",
            metadata={
                "serializer": self.__class__.__name__,
            },
        )


class CsvArtifactSerializer:
    """
    Serializes list[dict] payloads to CSV when filename ends with .csv.
    """

    def can_serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> bool:
        return (
            name is not None
            and name.lower().endswith(".csv")
            and isinstance(payload, list)
            and all(isinstance(row, dict) for row in payload)
        )

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact:
        output = io.StringIO()

        rows: list[dict[str, Any]] = payload

        fieldnames = sorted({key for row in rows for key in row.keys()})

        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)

        return SerializedArtifact(
            data=output.getvalue().encode("utf-8"),
            kind=ArtifactKind.CSV,
            content_type="text/csv",
            metadata={
                "serializer": self.__class__.__name__,
                "row_count": len(rows),
                "columns": fieldnames,
            },
        )


class FallbackArtifactSerializer:
    """
    Last-resort string serializer.
    """

    def can_serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> bool:
        return True

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact:
        return SerializedArtifact(
            data=str(payload).encode("utf-8"),
            kind=ArtifactKind.TEXT,
            content_type="text/plain",
            metadata={
                "serializer": self.__class__.__name__,
                "fallback": True,
            },
        )


class ArtifactSerializerRegistry:
    """
    Ordered artifact serializer registry.

    First matching serializer wins.
    """

    def __init__(
        self,
        serializers: list[ArtifactSerializer] | None = None,
    ) -> None:
        self.serializers = serializers or [
            CsvArtifactSerializer(),
            JsonArtifactSerializer(),
            TextArtifactSerializer(),
            BytesArtifactSerializer(),
            FallbackArtifactSerializer(),
        ]

    def serialize(
        self,
        payload: Any,
        name: str | None = None,
    ) -> SerializedArtifact:
        for serializer in self.serializers:
            if serializer.can_serialize(
                payload=payload,
                name=name,
            ):
                return serializer.serialize(
                    payload=payload,
                    name=name,
                )

        raise ValueError(f"No artifact serializer found for payload: {type(payload)}")

    def register(
        self,
        serializer: ArtifactSerializer,
        prepend: bool = False,
    ) -> None:
        if prepend:
            self.serializers.insert(
                0,
                serializer,
            )
        else:
            self.serializers.append(
                serializer,
            )


def _infer_binary_kind(
    name: str | None,
) -> ArtifactKind:
    lower_name = (name or "").lower()

    if lower_name.endswith(".pdf"):
        return ArtifactKind.PDF

    if lower_name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return ArtifactKind.IMAGE

    if lower_name.endswith(".parquet"):
        return ArtifactKind.PARQUET

    return ArtifactKind.BINARY
