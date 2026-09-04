from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NoReturn

from application.decision_evidence._reconstruction_contracts import (
    MalformedDecisionEvidenceReconstructionIdentifierError,
    MissingDecisionEvidenceSourceError,
    RagEvidenceSourceRepository,
    StaleDecisionEvidenceSourceError,
    SubstitutedDecisionEvidenceSourceError,
)
from core.storage.persistence.rag import RagChunkRecord, RagDocumentRecord
from domain.authority import SourceOfTruthCategory
from domain.decision_evidence import ReconstructionReference


async def validate_rag_retrieval_context(
    *,
    repository: RagEvidenceSourceRepository | None,
    reference: ReconstructionReference,
) -> None:
    _validate_rag_retrieval_context_reference(reference)
    if repository is None:
        raise MissingDecisionEvidenceSourceError(
            "RAG repository is required to reconstruct retrieval context "
            f"source record '{reference.record_id}'."
        )

    query_log = await repository.get_query_log(reference.snapshot_id or "")
    if query_log is None:
        raise MissingDecisionEvidenceSourceError(
            f"RAG query source record '{reference.snapshot_id}' was not found."
        )
    if query_log.query_id != reference.snapshot_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "RAG retrieval context evidence does not belong to query "
            f"'{reference.snapshot_id}'."
        )

    context_payload = _find_rag_context_payload(
        query_log.metadata,
        context_id=reference.record_id,
    )
    if context_payload is None:
        raise MissingDecisionEvidenceSourceError(
            "RAG retrieval context source record "
            f"'{reference.record_id}' was not retained with query "
            f"'{query_log.query_id}'."
        )

    content_digest = calculate_rag_retrieval_context_evidence_digest(
        context_payload=context_payload,
    )
    if content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "RAG retrieval context evidence content digest is stale for "
            f"'{reference.record_id}'."
        )


async def validate_rag_citation_context(
    *,
    repository: RagEvidenceSourceRepository | None,
    reference: ReconstructionReference,
) -> None:
    _validate_rag_citation_context_reference(reference)
    if repository is None:
        raise MissingDecisionEvidenceSourceError(
            "RAG repository is required to reconstruct citation context "
            f"source record '{reference.record_id}'."
        )

    source_identity = _parse_rag_source_record_id(reference.record_id)
    document = await repository.get_document(source_identity.document_id)
    if document is None:
        raise MissingDecisionEvidenceSourceError(
            f"RAG document source record '{source_identity.document_id}' was not found."
        )
    _validate_rag_document_identity(
        document=document,
        source_identity=source_identity,
        reference=reference,
    )

    chunk: RagChunkRecord | None = None
    if source_identity.chunk_id is not None:
        chunk = await repository.get_chunk(source_identity.chunk_id)
        if chunk is None:
            raise MissingDecisionEvidenceSourceError(
                f"RAG chunk source record '{source_identity.chunk_id}' was not found."
            )
        if chunk.document_id != document.document_id:
            raise SubstitutedDecisionEvidenceSourceError(
                "RAG citation chunk evidence does not belong to document "
                f"'{document.document_id}'."
            )

    content_digest = calculate_rag_citation_source_evidence_digest(
        document=document,
        chunk=chunk,
    )
    if content_digest != reference.content_digest:
        raise StaleDecisionEvidenceSourceError(
            "RAG citation context evidence content digest is stale for "
            f"'{reference.record_id}'."
        )


def calculate_rag_retrieval_context_evidence_digest(
    *,
    context_payload: Mapping[str, object],
) -> str:
    """Calculate a stable digest for a retained canonical RAG context payload."""

    source = _required_mapping(context_payload, "source")
    digest_payload = "|".join(
        (
            _required_string(context_payload, "context_id"),
            _required_string(context_payload, "retrieval_route"),
            _required_string(source, "source_table"),
            _required_string(source, "source_id"),
            _required_string(source, "document_id"),
            _optional_string(source.get("chunk_id")) or "",
            _required_string(context_payload, "text"),
        )
    )
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


def calculate_rag_citation_source_evidence_digest(
    *,
    document: RagDocumentRecord,
    chunk: RagChunkRecord | None = None,
) -> str:
    """Calculate the RAG citation digest from canonical source document lineage."""

    section_name = _optional_string(document.metadata.get("section_name"))
    if chunk is not None:
        section_name = (
            _optional_string(chunk.metadata.get("section_name")) or section_name
        )
    digest_payload = "|".join(
        (
            document.source_table,
            document.source_id,
            document.source_type,
            document.document_id,
            "" if chunk is None else chunk.chunk_id,
            section_name or "",
            document.generated_at.isoformat(),
        )
    )
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class _RagSourceRecordIdentity:
    source_table: str | None
    source_id: str | None
    document_id: str
    chunk_id: str | None


def _find_rag_context_payload(
    metadata: Mapping[str, object],
    *,
    context_id: str,
) -> Mapping[str, object] | None:
    for key in (
        "retrieved_contexts",
        "retrieval_contexts",
        "contexts",
        "citation_contexts",
    ):
        raw_contexts = metadata.get(key)
        if not isinstance(raw_contexts, Sequence) or isinstance(raw_contexts, str):
            continue
        for raw_context in raw_contexts:
            if not isinstance(raw_context, Mapping):
                continue
            raw_context_id = raw_context.get("context_id") or raw_context.get("id")
            if raw_context_id == context_id:
                return raw_context
    return None


def _parse_rag_source_record_id(record_id: str) -> _RagSourceRecordIdentity:
    parts = record_id.split(":")
    if len(parts) == 2 and all(parts):
        return _RagSourceRecordIdentity(
            source_table=None,
            source_id=None,
            document_id=parts[0],
            chunk_id=None if parts[1] == "document" else parts[1],
        )
    if len(parts) < 4 or not all(parts):
        _raise_malformed_rag_source_record_id()

    chunk_or_document = parts[-1]
    if chunk_or_document == "document":
        parsed_document_identity = _parse_rag_document_source_identity(parts)
        if parsed_document_identity is not None:
            return parsed_document_identity

    parsed_chunk_identity = _parse_rag_chunk_source_identity(parts)
    if parsed_chunk_identity is not None:
        return parsed_chunk_identity

    _raise_malformed_rag_source_record_id()


def _parse_rag_document_source_identity(
    parts: Sequence[str],
) -> _RagSourceRecordIdentity | None:
    for document_start_index in _rag_document_start_candidates(
        parts,
        max_index=len(parts) - 2,
    ):
        source_id_parts = parts[1:document_start_index]
        document_id_parts = parts[document_start_index:-1]
        if not source_id_parts or not document_id_parts:
            continue
        return _RagSourceRecordIdentity(
            source_table=parts[0],
            source_id=":".join(source_id_parts),
            document_id=":".join(document_id_parts),
            chunk_id=None,
        )
    return None


def _parse_rag_chunk_source_identity(
    parts: Sequence[str],
) -> _RagSourceRecordIdentity | None:
    if len(parts) == 4:
        return _RagSourceRecordIdentity(
            source_table=parts[0],
            source_id=parts[1],
            document_id=parts[2],
            chunk_id=parts[3],
        )

    if len(parts) >= 6 and parts[-2] == "chunk":
        for document_start_index in _rag_document_start_candidates(
            parts,
            max_index=len(parts) - 4,
        ):
            source_id_parts = parts[1:document_start_index]
            duplicated_document_parts = parts[document_start_index:-2]
            if not source_id_parts or len(duplicated_document_parts) % 2 != 0:
                continue
            document_part_count = len(duplicated_document_parts) // 2
            document_id_parts = duplicated_document_parts[:document_part_count]
            chunk_document_id_parts = duplicated_document_parts[document_part_count:]
            if not document_id_parts or document_id_parts != chunk_document_id_parts:
                continue
            chunk_id_parts = (*chunk_document_id_parts, parts[-2], parts[-1])
            return _RagSourceRecordIdentity(
                source_table=parts[0],
                source_id=":".join(source_id_parts),
                document_id=":".join(document_id_parts),
                chunk_id=":".join(chunk_id_parts),
            )

    for document_start_index in _rag_document_start_candidates(
        parts,
        max_index=len(parts) - 2,
    ):
        source_id_parts = parts[1:document_start_index]
        document_id_parts = parts[document_start_index:-1]
        if not source_id_parts or not document_id_parts:
            continue
        return _RagSourceRecordIdentity(
            source_table=parts[0],
            source_id=":".join(source_id_parts),
            document_id=":".join(document_id_parts),
            chunk_id=parts[-1],
        )
    return None


def _rag_document_start_candidates(
    parts: Sequence[str],
    *,
    max_index: int,
) -> tuple[int, ...]:
    if max_index < 2:
        return ()

    candidates: list[int] = []
    known_document_id_prefixes = {"rag_document", "structured", "web_document"}
    for index in range(2, max_index + 1):
        if parts[index] in known_document_id_prefixes:
            candidates.append(index)

    if not candidates:
        candidates.append(2 if len(parts) == 4 else max_index)
    fallback_indexes = (2, max_index)
    for index in fallback_indexes:
        if 2 <= index <= max_index and index not in candidates:
            candidates.append(index)
    return tuple(candidates)


def _raise_malformed_rag_source_record_id() -> NoReturn:
    raise MalformedDecisionEvidenceReconstructionIdentifierError(
        "RAG citation context reconstruction identifier must be "
        "'<source_table>:<source_id>:<document_id>:<chunk_id|document>'."
    )


def _validate_rag_document_identity(
    *,
    document: RagDocumentRecord,
    source_identity: _RagSourceRecordIdentity,
    reference: ReconstructionReference,
) -> None:
    if document.document_id != source_identity.document_id:
        raise SubstitutedDecisionEvidenceSourceError(
            "RAG citation document evidence does not match reconstruction "
            f"identifier '{reference.record_id}'."
        )
    if source_identity.source_table is not None and (
        document.source_table != source_identity.source_table
        or document.source_id != source_identity.source_id
    ):
        raise SubstitutedDecisionEvidenceSourceError(
            "RAG citation document evidence source lineage does not match "
            f"reconstruction identifier '{reference.record_id}'."
        )


def _validate_rag_retrieval_context_reference(
    reference: ReconstructionReference,
) -> None:
    label = "RAG retrieval context reconstruction reference"
    _require_source_of_truth(reference, label=label)
    _require_snapshot_id(reference, label=label)
    _require_content_digest(reference, label=label)


def _validate_rag_citation_context_reference(
    reference: ReconstructionReference,
) -> None:
    label = "RAG citation context reconstruction reference"
    _require_source_of_truth(reference, label=label)
    _require_snapshot_id(reference, label=label)
    _require_content_digest(reference, label=label)


def _require_source_of_truth(
    reference: ReconstructionReference,
    *,
    label: str,
) -> None:
    if reference.source_of_truth is not SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must identify canonical_domain_record as its source of truth."
        )


def _require_snapshot_id(reference: ReconstructionReference, *, label: str) -> None:
    if reference.snapshot_id is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must include a snapshot_id."
        )


def _require_content_digest(reference: ReconstructionReference, *, label: str) -> None:
    if reference.content_digest is None:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"{label} must include a content digest."
        )


def _required_mapping(
    payload: Mapping[str, object],
    key: str,
) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"RAG context payload must include mapping field '{key}'."
        )
    return value


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise MalformedDecisionEvidenceReconstructionIdentifierError(
            f"RAG context payload must include string field '{key}'."
        )
    return value


def _optional_string(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
