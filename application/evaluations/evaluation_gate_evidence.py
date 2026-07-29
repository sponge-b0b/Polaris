from __future__ import annotations

from collections.abc import Sequence

from domain.authority import RiskAuthorityContract, RiskTier
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
)
from domain.evaluation import EvaluationCase

_EVALUATION_READINESS_RETENTION_UNTIL = "2031-07-29T00:00:00Z"
_EVALUATION_READINESS_RETENTION_POLICY_ID = "evaluation-readiness-5y"


def canonical_evaluation_readiness_packet(
    *,
    authority: RiskAuthorityContract,
    packet_id: str,
    output_id: str,
    claim_id: str,
    claim_text: str,
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
    )


def _canonical_evidence_references_for_cases(
    cases: Sequence[EvaluationCase],
) -> tuple[EvidenceReference, ...]:
    evidence_by_id: dict[str, EvidenceReference] = {}
    for case in cases:
        for source_record_id in case.source_record_ids:
            evidence_by_id.setdefault(
                f"canonical_record:{source_record_id}",
                EvidenceReference(
                    evidence_id=f"canonical_record:{source_record_id}",
                    kind=EvidenceReferenceKind.CANONICAL_RECORD,
                    reconstruction_reference_ids=(
                        f"canonical_record:{source_record_id}",
                    ),
                    summary=(
                        "Canonical source record used to construct an evaluation case."
                    ),
                ),
            )
        for citation_context_id in case.citation_context_ids:
            evidence_by_id.setdefault(
                f"rag_citation_context:{citation_context_id}",
                EvidenceReference(
                    evidence_id=f"rag_citation_context:{citation_context_id}",
                    kind=EvidenceReferenceKind.RAG_CITATION_CONTEXT,
                    reconstruction_reference_ids=(
                        f"rag_citation_context:{citation_context_id}",
                    ),
                    summary=(
                        "Curated RAG citation context used to construct an "
                        "evaluation case."
                    ),
                ),
            )
        if case.workflow_execution_id is not None:
            workflow_execution_id = case.workflow_execution_id
            evidence_by_id.setdefault(
                f"completed_workflow_run:{workflow_execution_id}",
                EvidenceReference(
                    evidence_id=f"completed_workflow_run:{workflow_execution_id}",
                    kind=EvidenceReferenceKind.WORKFLOW_RUN,
                    reconstruction_reference_ids=(
                        f"completed_workflow_run:{workflow_execution_id}",
                    ),
                    summary=(
                        "Completed workflow run used to construct an evaluation case."
                    ),
                ),
            )
    return tuple(evidence_by_id.values())


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
    return ReconstructionReference(
        reference_id=reconstruction_id,
        kind=kind,
        record_id=reconstruction_id.split(":", maxsplit=1)[1],
    )


__all__ = ["canonical_evaluation_readiness_packet"]
