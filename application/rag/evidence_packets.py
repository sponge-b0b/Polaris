from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from typing import Final, cast

from application.rag.authority import (
    RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY,
    RagAuthorityFailureMode,
    classify_rag_result_authority,
)
from application.rag.contracts.rag_context import RagRetrievedContext, RagSource
from application.rag.contracts.rag_generated_claims import RagGeneratedClaim
from application.rag.contracts.rag_request import RagRequest
from application.rag.contracts.rag_result import RagResult
from core.storage.persistence.rag import JsonObject
from domain.authority import (
    RISK_AUTHORITY_METADATA_KEY,
    RiskTier,
    SourceOfTruthCategory,
    coerce_risk_authority_contract,
)
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
    UnsupportedMaterialClaimError,
)

DECISION_EVIDENCE_PACKET_METADATA_KEY: Final = "decision_evidence_packet"
DECISION_EVIDENCE_PACKET_FAILURE_METADATA_KEY: Final = (
    "decision_evidence_packet_failure"
)
_RAG_ANSWER_PACKET_POLICY_ID: Final = "rag-answer-enhanced-provenance-5y"


class RagEvidencePacketAssemblyError(DecisionEvidencePacketValidationError):
    """Raised when a RAG answer cannot be backed by an evidence packet."""


class MissingRagCitationContextError(RagEvidencePacketAssemblyError):
    """Raised when answer text cites a missing packaged RAG citation context."""


class UnsupportedRagAnswerClaimError(UnsupportedMaterialClaimError):
    """Raised when a material RAG answer claim lacks supporting citations."""


def attach_rag_answer_evidence_packet(
    *,
    request: RagRequest,
    result: RagResult,
) -> RagResult:
    """Attach a canonical decision evidence packet to supported RAG answers.

    Enhanced and Vigilant RAG answers must carry durable reconstruction
    references for the retrieval and citation contexts that support their
    material claims. If packet assembly cannot prove support, the answer is
    reclassified as fail-closed instead of being presented as grounded.
    """

    if result.status != "answered":
        return result

    try:
        packet = assemble_rag_answer_evidence_packet(
            result=result,
        )
    except DecisionEvidencePacketValidationError as exc:
        return classify_rag_result_authority(
            request=request,
            result=replace(
                result,
                evidence_packet=None,
                metadata={
                    **result.metadata,
                    RAG_AUTHORITY_FAILURE_MODE_METADATA_KEY: (
                        RagAuthorityFailureMode.UNSUPPORTED_EVIDENCE.value
                    ),
                    DECISION_EVIDENCE_PACKET_FAILURE_METADATA_KEY: str(exc),
                },
            ),
        )

    return replace(
        result,
        evidence_packet=packet,
        metadata={
            **result.metadata,
            DECISION_EVIDENCE_PACKET_METADATA_KEY: _packet_reference_metadata(packet),
        },
    )


def assemble_rag_answer_evidence_packet(
    *,
    result: RagResult,
) -> DecisionEvidencePacket:
    """Build the canonical evidence packet for an already-classified RAG answer."""

    if result.status != "answered":
        raise RagEvidencePacketAssemblyError(
            "only answered RAG results can be packeted."
        )
    authority = coerce_risk_authority_contract(
        result.metadata.get(RISK_AUTHORITY_METADATA_KEY),
    )
    if authority.risk_tier not in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        raise RagEvidencePacketAssemblyError(
            "RAG answer evidence packets require Enhanced or Vigilant authority."
        )

    citation_contexts = _citation_context_map(result)
    if not citation_contexts:
        raise MissingRagCitationContextError(
            "RAG answer evidence packet requires citation context identifiers."
        )

    reconstruction_references: list[ReconstructionReference] = []
    evidence: list[EvidenceReference] = []
    limitations: list[EvidenceLimitation] = []
    evidence_by_citation_id: dict[str, str] = {}
    limitation_ids_by_context_id: dict[str, list[str]] = {}

    for citation_id, context in citation_contexts.items():
        retrieval_reference_id = _retrieval_reference_id(context)
        citation_reference_id = _citation_reference_id(citation_id)
        reconstruction_references.extend(
            (
                ReconstructionReference(
                    reference_id=retrieval_reference_id,
                    kind=ReconstructionReferenceKind.RAG_RETRIEVAL_CONTEXT,
                    record_id=context.context_id,
                    source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                    snapshot_id=result.query_id,
                    content_digest=_context_digest(context),
                ),
                ReconstructionReference(
                    reference_id=citation_reference_id,
                    kind=ReconstructionReferenceKind.RAG_CITATION_CONTEXT,
                    record_id=_source_record_id(context.source),
                    source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                    snapshot_id=citation_id,
                    content_digest=_source_digest(context.source),
                ),
            )
        )
        evidence_id = _evidence_id(citation_id)
        evidence_summary = _evidence_summary(citation_id, context)
        evidence_by_citation_id[citation_id] = evidence_id
        evidence.append(
            EvidenceReference(
                evidence_id=evidence_id,
                kind=EvidenceReferenceKind.RAG_CITATION_CONTEXT,
                reconstruction_reference_ids=(
                    retrieval_reference_id,
                    citation_reference_id,
                ),
                summary=evidence_summary,
                source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                support_snapshot=_support_snapshot(
                    citation_id=citation_id,
                    context=context,
                    summary=evidence_summary,
                ),
            )
        )
        if _context_was_sanitized(context):
            limitation = EvidenceLimitation(
                limitation_id=f"rag-context-sanitized:{context.context_id}",
                summary=_sanitized_context_summary(citation_id, context),
                evidence_ids=(evidence_id,),
            )
            limitations.append(limitation)
            limitation_ids_by_context_id.setdefault(context.context_id, []).append(
                limitation.limitation_id,
            )

    rejected_limitations, rejected_limitation_ids_by_context_id = (
        _rejected_context_limitations(
            result.metadata,
            known_evidence_ids=tuple(evidence_by_citation_id.values()),
        )
    )
    limitations.extend(rejected_limitations)
    for context_id, limitation_id in rejected_limitation_ids_by_context_id.items():
        limitation_ids_by_context_id.setdefault(context_id, []).append(limitation_id)

    claims = tuple(
        _material_claim_from_generated_claim(
            generated_claim=generated_claim,
            evidence_by_citation_id=evidence_by_citation_id,
            limitation_ids_by_context_id=limitation_ids_by_context_id,
        )
        for generated_claim in result.generated_claims
    )
    if not claims:
        raise UnsupportedRagAnswerClaimError(
            "RAG answer did not include typed generated claims."
        )

    return DecisionEvidencePacket(
        packet_id=f"decision-evidence-packet:{result.query_id}",
        output_id=result.query_id,
        authority=authority,
        claims=claims,
        evidence=tuple(evidence),
        reconstruction_references=tuple(reconstruction_references),
        retention=_retention_requirement(result.generated_at, authority.risk_tier),
        limitations=tuple(limitations),
    )


def _citation_context_map(
    result: RagResult,
) -> dict[str, RagRetrievedContext]:
    citation_ids = result.metadata.get("citation_ids")
    if isinstance(citation_ids, Sequence) and not isinstance(
        citation_ids,
        str | bytes | bytearray,
    ):
        ids = tuple(str(value).strip() for value in citation_ids if str(value).strip())
    else:
        ids = tuple(f"C{index}" for index, _ in enumerate(result.contexts, start=1))
    if len(ids) != len(result.contexts):
        raise MissingRagCitationContextError(
            "RAG answer citation identifiers do not match packaged contexts."
        )
    return dict(zip(ids, result.contexts, strict=True))


def _material_claim_from_generated_claim(
    *,
    generated_claim: RagGeneratedClaim,
    evidence_by_citation_id: Mapping[str, str],
    limitation_ids_by_context_id: Mapping[str, Sequence[str]],
) -> MaterialClaim:
    citation_ids = tuple(
        dict.fromkeys(
            (
                *generated_claim.citation_ids,
                *generated_claim.supporting_citation_ids,
            )
        )
    )
    for citation_id in citation_ids:
        if citation_id not in evidence_by_citation_id:
            raise MissingRagCitationContextError(
                f"generated RAG claim {generated_claim.claim_id!r} "
                f"cites missing context {citation_id!r}."
            )

    supporting_evidence_ids = tuple(
        dict.fromkeys(
            evidence_by_citation_id[citation_id]
            for citation_id in generated_claim.supporting_citation_ids
        )
    )
    if generated_claim.gates_readiness and not supporting_evidence_ids:
        raise UnsupportedRagAnswerClaimError(
            f"material RAG answer claim {generated_claim.claim_id!r} "
            "lacks supporting citations."
        )

    limitation_ids = tuple(
        dict.fromkeys(
            limitation_id
            for context_id in (
                *generated_claim.sanitized_context_ids,
                *generated_claim.rejected_context_ids,
            )
            for limitation_id in limitation_ids_by_context_id.get(context_id, ())
        )
    )
    return MaterialClaim(
        claim_id=generated_claim.claim_id,
        text=generated_claim.text,
        materiality=generated_claim.materiality,
        evidence=ClaimEvidenceBinding(
            supporting_evidence_ids=supporting_evidence_ids,
            limitation_ids=limitation_ids,
        ),
    )


def _retrieval_reference_id(context: RagRetrievedContext) -> str:
    return f"rag-retrieval-context:{context.context_id}"


def _citation_reference_id(citation_id: str) -> str:
    return f"rag-citation-context:{citation_id}"


def _evidence_id(citation_id: str) -> str:
    return f"rag-citation:{citation_id}"


def _source_record_id(source: RagSource) -> str:
    parts = (
        source.source_table,
        source.source_id,
        source.document_id,
        source.chunk_id or "document",
    )
    return ":".join(part for part in parts if part)


def _support_snapshot(
    *,
    citation_id: str,
    context: RagRetrievedContext,
    summary: str,
) -> SupportingEvidenceSnapshot:
    return SupportingEvidenceSnapshot(
        snapshot_id=f"rag-support-snapshot:{citation_id}:{context.context_id}",
        summary=summary,
        redacted_content=context.text,
        source_label=_source_record_id(context.source),
    )


def _evidence_summary(citation_id: str, context: RagRetrievedContext) -> str:
    source = context.source
    return (
        f"Citation {citation_id} from curated RAG source "
        f"{source.source_table}:{source.source_id}; "
        f"document {source.document_id}, context {context.context_id}."
    )


def _context_was_sanitized(context: RagRetrievedContext) -> bool:
    return any(
        bool(context.metadata.get(key))
        for key in (
            "security_sanitized",
            "security_injection_detected",
            "security_executable_markup_detected",
        )
    )


def _sanitized_context_summary(citation_id: str, context: RagRetrievedContext) -> str:
    signals = context.metadata.get("security_signals")
    signal_text = ""
    if isinstance(signals, Sequence) and not isinstance(
        signals, str | bytes | bytearray
    ):
        cleaned_signals = tuple(
            str(signal) for signal in signals if str(signal).strip()
        )
        if cleaned_signals:
            signal_text = f" Signals: {', '.join(cleaned_signals)}."
    removed_count = context.metadata.get("security_removed_segment_count")
    removed_text = ""
    if isinstance(removed_count, int) and removed_count > 0:
        removed_text = f" Removed segments: {removed_count}."
    return (
        f"Retrieved context for citation {citation_id} was sanitized before answer "
        f"generation; original unsafe text is excluded from this packet."
        f"{signal_text}{removed_text}"
    )


def _rejected_context_limitations(
    metadata: Mapping[str, object],
    *,
    known_evidence_ids: tuple[str, ...],
) -> tuple[tuple[EvidenceLimitation, ...], dict[str, str]]:
    context_audit = metadata.get("context_audit")
    if not isinstance(context_audit, Mapping):
        return (), {}
    rejected_contexts = context_audit.get("rejected_contexts")
    if not isinstance(rejected_contexts, Sequence) or isinstance(
        rejected_contexts,
        str | bytes | bytearray,
    ):
        return (), {}
    linked_evidence_ids = known_evidence_ids[:1]
    limitations: list[EvidenceLimitation] = []
    limitation_ids_by_context_id: dict[str, str] = {}
    for rejected in rejected_contexts:
        if not isinstance(rejected, Mapping):
            continue
        context_id = rejected.get("context_id")
        reason = rejected.get("reason")
        if not isinstance(context_id, str) or not context_id.strip():
            continue
        reason_text = (
            reason if isinstance(reason, str) and reason.strip() else "rejected"
        )
        limitation_id = f"rag-context-rejected:{context_id}"
        limitations.append(
            EvidenceLimitation(
                limitation_id=limitation_id,
                summary=(
                    f"Retrieved context {context_id!r} was rejected before answer "
                    f"generation ({reason_text}); original unsafe text is excluded "
                    "from this packet."
                ),
                evidence_ids=linked_evidence_ids,
            )
        )
        limitation_ids_by_context_id[context_id] = limitation_id
    return tuple(limitations), limitation_ids_by_context_id


def _context_digest(context: RagRetrievedContext) -> str:
    digest_payload = "|".join(
        (
            context.context_id,
            context.retrieval_route,
            context.source.source_table,
            context.source.source_id,
            context.source.document_id,
            context.source.chunk_id or "",
            context.text,
        )
    )
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


def _source_digest(source: RagSource) -> str:
    digest_payload = "|".join(
        (
            source.source_table,
            source.source_id,
            source.source_type,
            source.document_id,
            source.chunk_id or "",
            source.section_name or "",
            "" if source.generated_at is None else source.generated_at.isoformat(),
        )
    )
    return hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()


def _retention_requirement(
    generated_at: datetime,
    risk_tier: RiskTier,
) -> EvidenceRetentionRequirement:
    years = 7 if risk_tier is RiskTier.VIGILANT else 5
    try:
        retain_until = generated_at.replace(year=generated_at.year + years)
    except ValueError:
        retain_until = generated_at.replace(
            year=generated_at.year + years,
            day=28,
        )
    return EvidenceRetentionRequirement(
        retain_until=retain_until.isoformat(),
        policy_id=_RAG_ANSWER_PACKET_POLICY_ID,
        legal_hold=False,
    )


def _packet_reference_metadata(packet: DecisionEvidencePacket) -> JsonObject:
    return cast(
        JsonObject,
        {
            "packet_id": packet.packet_id,
            "output_id": packet.output_id,
            "risk_tier": packet.risk_tier.value,
            "schema_version": packet.schema_version,
            "claim_ids": [claim.claim_id for claim in packet.claims],
            "evidence_ids": [evidence.evidence_id for evidence in packet.evidence],
            "reconstruction_reference_ids": list(packet.reconstruction_reference_ids),
        },
    )


__all__ = [
    "DECISION_EVIDENCE_PACKET_FAILURE_METADATA_KEY",
    "DECISION_EVIDENCE_PACKET_METADATA_KEY",
    "MissingRagCitationContextError",
    "RagEvidencePacketAssemblyError",
    "UnsupportedRagAnswerClaimError",
    "assemble_rag_answer_evidence_packet",
    "attach_rag_answer_evidence_packet",
]
