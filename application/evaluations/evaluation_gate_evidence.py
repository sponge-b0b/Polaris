from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import replace

from application.decision_evidence import DecisionEvidencePacketPersistenceService
from application.evaluations.risk_authority_gate import RiskAuthorityGateEvidence
from domain.authority import RiskAuthorityContract, RiskTier, SourceOfTruthCategory
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
    SupportingEvidenceSnapshot,
)
from domain.evaluation import EvaluationCase

_EVALUATION_READINESS_RETENTION_UNTIL = "2031-07-29T00:00:00Z"
_EVALUATION_READINESS_RETENTION_POLICY_ID = "evaluation-readiness-5y"
logger = logging.getLogger(__name__)


def canonical_evaluation_readiness_packet(
    *,
    authority: RiskAuthorityContract,
    packet_id: str,
    output_id: str,
    claim_id: str,
    claim_text: str,
    workflow_name: str,
    workflow_definition_fingerprint: str,
    execution_id: str,
    cases: Sequence[EvaluationCase],
) -> DecisionEvidencePacket | None:
    """Build canonical packet evidence from reconstructable evaluation inputs.

    Evaluation case IDs remain provenance for the evaluation run/gate. They are
    intentionally not used as claim support or reconstruction records here; only
    platform records that can reconstruct the evaluated output are promoted into
    the canonical packet.
    """

    if authority.risk_tier not in {RiskTier.ENHANCED, RiskTier.VIGILANT}:
        return None
    evidence = _canonical_evidence_references_for_cases(cases)
    if not evidence:
        return None
    return DecisionEvidencePacket(
        packet_id=packet_id,
        output_id=output_id,
        authority=authority,
        claims=(
            MaterialClaim(
                claim_id=claim_id,
                text=claim_text,
                evidence=ClaimEvidenceBinding(
                    supporting_evidence_ids=tuple(
                        reference.evidence_id for reference in evidence
                    ),
                ),
            ),
        ),
        evidence=evidence,
        reconstruction_references=_reconstruction_references_for_evidence(evidence),
        retention=EvidenceRetentionRequirement(
            retain_until=_EVALUATION_READINESS_RETENTION_UNTIL,
            policy_id=_EVALUATION_READINESS_RETENTION_POLICY_ID,
        ),
        workflow_name=workflow_name,
        workflow_definition_fingerprint=workflow_definition_fingerprint,
        execution_id=execution_id,
    )


async def reacquire_authority_gate_decision_evidence(
    *,
    evidence: RiskAuthorityGateEvidence | None,
    persistence_service: DecisionEvidencePacketPersistenceService | None,
) -> RiskAuthorityGateEvidence | None:
    """Persist and reconstruct authority-gate packets before gate evaluation."""

    if evidence is None or not evidence.decision_evidence_packets:
        return evidence
    if persistence_service is None:
        logger.warning(
            "Authority gate decision evidence persistence is not configured.",
            extra={"decision_evidence_ids": evidence.decision_evidence_ids},
        )
        return _reject_decision_evidence_packets(evidence)

    reconstructed_packets = []
    try:
        for packet in evidence.decision_evidence_packets:
            persistence = await persistence_service.persist_packet(packet)
            if (
                not persistence.success
                or persistence.records_persisted < 1
                or persistence.packet_id != packet.packet_id
            ):
                raise ValueError(
                    "authority gate decision evidence packet was not persisted."
                )
            reconstructed = await persistence_service.reconstruct_packet(
                packet.packet_id
            )
            if reconstructed != packet:
                raise ValueError(
                    "authority gate decision evidence changed during reconstruction."
                )
            reconstructed_packets.append(reconstructed)
    except Exception as exc:
        logger.warning(
            "Authority gate decision evidence reconstruction failed closed.",
            extra={
                "decision_evidence_ids": evidence.decision_evidence_ids,
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        return _reject_decision_evidence_packets(evidence)

    return replace(
        evidence,
        decision_evidence_packets=tuple(reconstructed_packets),
        decision_evidence_ids=tuple(
            packet.packet_id for packet in reconstructed_packets
        ),
    )


def _reject_decision_evidence_packets(
    evidence: RiskAuthorityGateEvidence,
) -> RiskAuthorityGateEvidence:
    return replace(
        evidence,
        decision_evidence_packets=(),
        decision_evidence_ids=(),
        rejected_evidence_ids=tuple(
            dict.fromkeys(
                (*evidence.rejected_evidence_ids, *evidence.decision_evidence_ids)
            )
        ),
    )


def _canonical_evidence_references_for_cases(
    cases: Sequence[EvaluationCase],
) -> tuple[EvidenceReference, ...]:
    evidence_by_id: dict[str, EvidenceReference] = {}
    for case in cases:
        for source_record_id in case.source_record_ids:
            evidence_id = f"canonical_record:{source_record_id}"
            evidence_by_id.setdefault(
                evidence_id,
                _case_evidence_reference(
                    case=case,
                    evidence_id=evidence_id,
                    kind=EvidenceReferenceKind.CANONICAL_RECORD,
                    reconstruction_id=evidence_id,
                    summary=(
                        "Canonical source record used to construct an evaluation case."
                    ),
                    source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                    source_identifier=source_record_id,
                ),
            )
        for citation_context_id in case.citation_context_ids:
            evidence_id = f"rag_citation_context:{citation_context_id}"
            evidence_by_id.setdefault(
                evidence_id,
                _case_evidence_reference(
                    case=case,
                    evidence_id=evidence_id,
                    kind=EvidenceReferenceKind.RAG_CITATION_CONTEXT,
                    reconstruction_id=evidence_id,
                    summary=(
                        "Curated RAG citation context used to construct an "
                        "evaluation case."
                    ),
                    source_of_truth=SourceOfTruthCategory.CANONICAL_DOMAIN_RECORD,
                    source_identifier=citation_context_id,
                ),
            )
        if case.workflow_execution_id is not None:
            workflow_execution_id = case.workflow_execution_id
            evidence_id = f"completed_workflow_run:{workflow_execution_id}"
            evidence_by_id.setdefault(
                evidence_id,
                _case_evidence_reference(
                    case=case,
                    evidence_id=evidence_id,
                    kind=EvidenceReferenceKind.WORKFLOW_RUN,
                    reconstruction_id=evidence_id,
                    summary=(
                        "Completed workflow run used to construct an evaluation case."
                    ),
                    source_of_truth=SourceOfTruthCategory.RUNTIME_EVIDENCE,
                    source_identifier=workflow_execution_id,
                ),
            )
    return tuple(evidence_by_id.values())


def _case_evidence_reference(
    *,
    case: EvaluationCase,
    evidence_id: str,
    kind: EvidenceReferenceKind,
    reconstruction_id: str,
    summary: str,
    source_of_truth: SourceOfTruthCategory,
    source_identifier: str,
) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        kind=kind,
        reconstruction_reference_ids=(reconstruction_id,),
        summary=summary,
        source_of_truth=source_of_truth,
        support_snapshot=_case_support_snapshot(
            case=case,
            evidence_id=evidence_id,
            kind=kind,
            reconstruction_id=reconstruction_id,
            summary=summary,
            source_identifier=source_identifier,
        ),
    )


def _case_support_snapshot(
    *,
    case: EvaluationCase,
    evidence_id: str,
    kind: EvidenceReferenceKind,
    reconstruction_id: str,
    summary: str,
    source_identifier: str,
) -> SupportingEvidenceSnapshot:
    return SupportingEvidenceSnapshot(
        snapshot_id=f"{evidence_id}:support-snapshot",
        summary=summary,
        redacted_content=_case_support_snapshot_content(
            case=case,
            evidence_id=evidence_id,
            kind=kind,
            reconstruction_id=reconstruction_id,
            source_identifier=source_identifier,
        ),
        source_label=f"{kind.value}:{source_identifier}",
    )


def _case_support_snapshot_content(
    *,
    case: EvaluationCase,
    evidence_id: str,
    kind: EvidenceReferenceKind,
    reconstruction_id: str,
    source_identifier: str,
) -> str:
    dataset = None if case.dataset is None else case.dataset.to_dict()
    payload = {
        "case_id": case.case_id,
        "target_type": case.target_type.value,
        "evidence_id": evidence_id,
        "evidence_kind": kind.value,
        "source_identifier": source_identifier,
        "reconstruction_reference_ids": (reconstruction_id,),
        "dataset": dataset,
        "rubric_digest": _optional_text_digest(case.rubric),
        "rubric_present": case.rubric is not None,
        "expected_output_digest": _optional_text_digest(case.expected_output),
        "input_text_digest": _text_digest(case.input_text),
        "actual_output_digest": _text_digest(case.actual_output),
        "source_record_ids": case.source_record_ids,
        "citation_context_ids": case.citation_context_ids,
        "workflow_execution_id": case.workflow_execution_id,
        "created_at": case.created_at.isoformat(),
        "snapshot_schema_version": 1,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_text_digest(value: str | None) -> str | None:
    if value is None:
        return None
    return _text_digest(value)


def _reconstruction_references_for_evidence(
    evidence: tuple[EvidenceReference, ...],
) -> tuple[ReconstructionReference, ...]:
    reconstruction_by_id: dict[str, ReconstructionReference] = {}
    for reference in evidence:
        for reconstruction_id in reference.reconstruction_reference_ids:
            reconstruction_by_id.setdefault(
                reconstruction_id,
                _reconstruction_reference_for_evidence(
                    reconstruction_id=reconstruction_id,
                    evidence=reference,
                ),
            )
    return tuple(reconstruction_by_id.values())


def _reconstruction_reference_for_evidence(
    *,
    reconstruction_id: str,
    evidence: EvidenceReference,
) -> ReconstructionReference:
    if evidence.kind is EvidenceReferenceKind.RAG_CITATION_CONTEXT:
        kind = ReconstructionReferenceKind.RAG_CITATION_CONTEXT
    elif evidence.kind is EvidenceReferenceKind.WORKFLOW_RUN:
        kind = ReconstructionReferenceKind.COMPLETED_WORKFLOW_RUN
    else:
        kind = ReconstructionReferenceKind.CANONICAL_DOMAIN_RECORD
    snapshot = evidence.support_snapshot
    return ReconstructionReference(
        reference_id=reconstruction_id,
        kind=kind,
        record_id=reconstruction_id.split(":", maxsplit=1)[1],
        source_of_truth=evidence.source_of_truth,
        snapshot_id=None if snapshot is None else snapshot.snapshot_id,
        content_digest=None if snapshot is None else snapshot.content_digest,
    )


__all__ = ["canonical_evaluation_readiness_packet"]
