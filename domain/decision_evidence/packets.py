from __future__ import annotations

from collections.abc import Iterable
from dataclasses import InitVar, dataclass, field
from enum import StrEnum
from typing import Final

from domain.authority import RiskAuthorityContract, RiskTier, SourceOfTruthCategory

DECISION_EVIDENCE_PACKET_SCHEMA_VERSION: Final[int] = 1
_ALLOWED_PACKET_RISK_TIERS: Final[frozenset[RiskTier]] = frozenset(
    {RiskTier.ENHANCED, RiskTier.VIGILANT}
)
_RAW_PAYLOAD_UNSET: Final = object()


class DecisionEvidencePacketValidationError(ValueError):
    """Raised when a decision evidence packet violates canonical invariants."""


class UnsupportedMaterialClaimError(DecisionEvidencePacketValidationError):
    """Raised when a material claim lacks required supporting evidence."""


class EvidenceReferenceKind(StrEnum):
    """Canonical evidence families that may support a packet claim."""

    WORKFLOW_RUN = "workflow_run"
    WORKFLOW_NODE_OUTPUT = "workflow_node_output"
    CANONICAL_RECORD = "canonical_record"
    RAG_RETRIEVAL_CONTEXT = "rag_retrieval_context"
    RAG_CITATION_CONTEXT = "rag_citation_context"
    EVALUATION_RUN = "evaluation_run"
    EVALUATION_METRIC_RESULT = "evaluation_metric_result"
    OBSERVABILITY_CORRELATION = "observability_correlation"
    LINKED_ARTIFACT = "linked_artifact"


class ReconstructionReferenceKind(StrEnum):
    """Durable identifier families used to reconstruct packet evidence."""

    COMPLETED_WORKFLOW_RUN = "completed_workflow_run"
    WORKFLOW_NODE_OUTPUT = "workflow_node_output"
    CANONICAL_DOMAIN_RECORD = "canonical_domain_record"
    RAG_RETRIEVAL_CONTEXT = "rag_retrieval_context"
    RAG_CITATION_CONTEXT = "rag_citation_context"
    EVALUATION_RUN = "evaluation_run"
    EVALUATION_METRIC_RESULT = "evaluation_metric_result"
    TRACE_CONTEXT = "trace_context"
    LINKED_ARTIFACT = "linked_artifact"


@dataclass(frozen=True, slots=True)
class ClaimEvidenceBinding:
    """Evidence, conflict, constraint, uncertainty, and limitation links for a claim."""

    supporting_evidence_ids: tuple[str, ...] = ()
    conflicting_evidence_ids: tuple[str, ...] = ()
    constraint_ids: tuple[str, ...] = ()
    uncertainty_ids: tuple[str, ...] = ()
    limitation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _set_clean_tuple(self, "supporting_evidence_ids")
        _set_clean_tuple(self, "conflicting_evidence_ids")
        _set_clean_tuple(self, "constraint_ids")
        _set_clean_tuple(self, "uncertainty_ids")
        _set_clean_tuple(self, "limitation_ids")

    @property
    def has_support(self) -> bool:
        """Whether the claim has at least one positive supporting evidence link."""

        return bool(self.supporting_evidence_ids)


@dataclass(frozen=True, slots=True)
class MaterialClaim:
    """One claim whose decision relevance must be auditable."""

    claim_id: str
    text: str
    evidence: ClaimEvidenceBinding = field(default_factory=ClaimEvidenceBinding)
    material: bool = True

    def __post_init__(self) -> None:
        _set_clean_string(self, "claim_id")
        _set_clean_string(self, "text")
        if not isinstance(self.evidence, ClaimEvidenceBinding):
            raise DecisionEvidencePacketValidationError(
                "claim evidence must be a ClaimEvidenceBinding."
            )


@dataclass(frozen=True, slots=True)
class ReconstructionReference:
    """Durable identifier for reconstructing canonical evidence."""

    reference_id: str
    kind: ReconstructionReferenceKind
    record_id: str
    source_of_truth: SourceOfTruthCategory | None = None
    snapshot_id: str | None = None
    content_digest: str | None = None

    def __post_init__(self) -> None:
        _set_clean_string(self, "reference_id")
        _set_clean_string(self, "record_id")
        _set_optional_clean_string(self, "snapshot_id")
        _set_optional_clean_string(self, "content_digest")
        if not isinstance(self.kind, ReconstructionReferenceKind):
            raise DecisionEvidencePacketValidationError(
                "reconstruction reference kind must be a ReconstructionReferenceKind."
            )
        if self.source_of_truth is not None and not isinstance(
            self.source_of_truth,
            SourceOfTruthCategory,
        ):
            raise DecisionEvidencePacketValidationError(
                "reconstruction source_of_truth must be a SourceOfTruthCategory."
            )


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """Canonical evidence pointer; source payloads stay in authoritative stores."""

    evidence_id: str
    kind: EvidenceReferenceKind
    reconstruction_reference_ids: tuple[str, ...]
    summary: str = ""
    source_of_truth: SourceOfTruthCategory | None = None
    raw_payload: InitVar[object] = _RAW_PAYLOAD_UNSET

    def __post_init__(self, raw_payload: object) -> None:
        if raw_payload is not _RAW_PAYLOAD_UNSET:
            raise DecisionEvidencePacketValidationError(
                "raw_payload is not part of the canonical evidence packet contract; "
                "store canonical reconstruction identifiers instead."
            )
        _set_clean_string(self, "evidence_id")
        _set_clean_tuple(self, "reconstruction_reference_ids")
        if not self.reconstruction_reference_ids:
            raise DecisionEvidencePacketValidationError(
                f"evidence {self.evidence_id!r} must reference at least one "
                "reconstruction identifier."
            )
        _set_optional_clean_string(self, "summary", allow_empty=True)
        if not isinstance(self.kind, EvidenceReferenceKind):
            raise DecisionEvidencePacketValidationError(
                "evidence kind must be an EvidenceReferenceKind."
            )
        if self.source_of_truth is not None and not isinstance(
            self.source_of_truth,
            SourceOfTruthCategory,
        ):
            raise DecisionEvidencePacketValidationError(
                "evidence source_of_truth must be a SourceOfTruthCategory."
            )


@dataclass(frozen=True, slots=True)
class EvidenceConstraint:
    """Typed constraint that limits how one or more claims may be interpreted."""

    constraint_id: str
    summary: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _set_clean_string(self, "constraint_id")
        _set_clean_string(self, "summary")
        _set_clean_tuple(self, "evidence_ids")


@dataclass(frozen=True, slots=True)
class EvidenceUncertainty:
    """Typed uncertainty preserved with packet evidence."""

    uncertainty_id: str
    summary: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _set_clean_string(self, "uncertainty_id")
        _set_clean_string(self, "summary")
        _set_clean_tuple(self, "evidence_ids")


@dataclass(frozen=True, slots=True)
class EvidenceLimitation:
    """Typed limitation preserved with packet evidence."""

    limitation_id: str
    summary: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _set_clean_string(self, "limitation_id")
        _set_clean_string(self, "summary")
        _set_clean_tuple(self, "evidence_ids")


@dataclass(frozen=True, slots=True)
class EvidenceRetentionRequirement:
    """Risk-tiered retention instruction required for packet reconstruction."""

    retain_until: str
    policy_id: str
    legal_hold: bool = False

    def __post_init__(self) -> None:
        _set_clean_string(self, "retain_until")
        _set_clean_string(self, "policy_id")


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacket:
    """Canonical decision/evidence packet for Enhanced and Vigilant outputs."""

    packet_id: str
    output_id: str
    authority: RiskAuthorityContract
    claims: tuple[MaterialClaim, ...]
    evidence: tuple[EvidenceReference, ...]
    reconstruction_references: tuple[ReconstructionReference, ...]
    retention: EvidenceRetentionRequirement
    constraints: tuple[EvidenceConstraint, ...] = ()
    uncertainties: tuple[EvidenceUncertainty, ...] = ()
    limitations: tuple[EvidenceLimitation, ...] = ()
    schema_version: int = DECISION_EVIDENCE_PACKET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _set_clean_string(self, "packet_id")
        _set_clean_string(self, "output_id")
        _validate_authority(self.authority)
        _validate_retention(self.retention)
        _set_tuple(self, "claims")
        _set_tuple(self, "evidence")
        _set_tuple(self, "reconstruction_references")
        _set_tuple(self, "constraints")
        _set_tuple(self, "uncertainties")
        _set_tuple(self, "limitations")
        self._validate_packet_references()

    @property
    def risk_tier(self) -> RiskTier:
        """Risk tier supplied by the canonical authority contract."""

        return self.authority.risk_tier

    @property
    def material_claims(self) -> tuple[MaterialClaim, ...]:
        """Claims that must satisfy material evidence requirements."""

        return tuple(claim for claim in self.claims if claim.material)

    @property
    def reconstruction_reference_ids(self) -> tuple[str, ...]:
        """Durable reconstruction identifiers indexed by this packet."""

        return tuple(
            reference.reference_id for reference in self.reconstruction_references
        )

    def _validate_packet_references(self) -> None:
        evidence_ids = _unique_ids(
            self.evidence,
            id_attribute="evidence_id",
            label="evidence",
        )
        reconstruction_ids = _unique_ids(
            self.reconstruction_references,
            id_attribute="reference_id",
            label="reconstruction reference",
        )
        constraint_ids = _unique_ids(
            self.constraints,
            id_attribute="constraint_id",
            label="constraint",
        )
        uncertainty_ids = _unique_ids(
            self.uncertainties,
            id_attribute="uncertainty_id",
            label="uncertainty",
        )
        limitation_ids = _unique_ids(
            self.limitations,
            id_attribute="limitation_id",
            label="limitation",
        )
        claim_ids = _unique_ids(
            self.claims,
            id_attribute="claim_id",
            label="claim",
        )
        if not claim_ids:
            raise DecisionEvidencePacketValidationError(
                "decision evidence packet must contain at least one claim."
            )
        if not evidence_ids:
            raise DecisionEvidencePacketValidationError(
                "decision evidence packet must contain at least one evidence reference."
            )
        if not reconstruction_ids:
            raise DecisionEvidencePacketValidationError(
                "decision evidence packet must contain at least one reconstruction "
                "reference."
            )
        for evidence in self.evidence:
            _ensure_known_ids(
                owner=f"evidence {evidence.evidence_id}",
                relationship="reconstruction reference",
                referenced_ids=evidence.reconstruction_reference_ids,
                known_ids=reconstruction_ids,
            )
        for constraint in self.constraints:
            _ensure_known_ids(
                owner=f"constraint {constraint.constraint_id}",
                relationship="evidence",
                referenced_ids=constraint.evidence_ids,
                known_ids=evidence_ids,
            )
        for uncertainty in self.uncertainties:
            _ensure_known_ids(
                owner=f"uncertainty {uncertainty.uncertainty_id}",
                relationship="evidence",
                referenced_ids=uncertainty.evidence_ids,
                known_ids=evidence_ids,
            )
        for limitation in self.limitations:
            _ensure_known_ids(
                owner=f"limitation {limitation.limitation_id}",
                relationship="evidence",
                referenced_ids=limitation.evidence_ids,
                known_ids=evidence_ids,
            )
        for claim in self.claims:
            self._validate_claim_relationships(
                claim=claim,
                evidence_ids=evidence_ids,
                constraint_ids=constraint_ids,
                uncertainty_ids=uncertainty_ids,
                limitation_ids=limitation_ids,
            )

    def _validate_claim_relationships(
        self,
        *,
        claim: MaterialClaim,
        evidence_ids: frozenset[str],
        constraint_ids: frozenset[str],
        uncertainty_ids: frozenset[str],
        limitation_ids: frozenset[str],
    ) -> None:
        if claim.material and not claim.evidence.has_support:
            raise UnsupportedMaterialClaimError(
                f"material claim {claim.claim_id!r} lacks supporting evidence."
            )
        _ensure_known_ids(
            owner=claim.claim_id,
            relationship="supporting evidence",
            referenced_ids=claim.evidence.supporting_evidence_ids,
            known_ids=evidence_ids,
        )
        _ensure_known_ids(
            owner=claim.claim_id,
            relationship="conflicting evidence",
            referenced_ids=claim.evidence.conflicting_evidence_ids,
            known_ids=evidence_ids,
        )
        _ensure_known_ids(
            owner=claim.claim_id,
            relationship="constraint",
            referenced_ids=claim.evidence.constraint_ids,
            known_ids=constraint_ids,
        )
        _ensure_known_ids(
            owner=claim.claim_id,
            relationship="uncertainty",
            referenced_ids=claim.evidence.uncertainty_ids,
            known_ids=uncertainty_ids,
        )
        _ensure_known_ids(
            owner=claim.claim_id,
            relationship="limitation",
            referenced_ids=claim.evidence.limitation_ids,
            known_ids=limitation_ids,
        )


def _validate_authority(authority: object) -> None:
    if not isinstance(authority, RiskAuthorityContract):
        raise DecisionEvidencePacketValidationError(
            "authority must be a RiskAuthorityContract."
        )
    if authority.risk_tier not in _ALLOWED_PACKET_RISK_TIERS:
        allowed = ", ".join(sorted(tier.value for tier in _ALLOWED_PACKET_RISK_TIERS))
        raise DecisionEvidencePacketValidationError(
            "decision evidence packets are only valid for enhanced or vigilant "
            f"outputs; got {authority.risk_tier.value!r}. Allowed tiers: {allowed}."
        )


def _validate_retention(retention: object) -> None:
    if not isinstance(retention, EvidenceRetentionRequirement):
        raise DecisionEvidencePacketValidationError(
            "retention must be an EvidenceRetentionRequirement."
        )


def _set_tuple(instance: object, attribute: str) -> None:
    value = getattr(instance, attribute)
    if value is None:
        raise DecisionEvidencePacketValidationError(f"{attribute} cannot be None.")
    object.__setattr__(instance, attribute, tuple(value))


def _set_clean_tuple(instance: object, attribute: str) -> None:
    values = getattr(instance, attribute)
    object.__setattr__(
        instance,
        attribute,
        tuple(_clean_identifier(value, attribute) for value in values),
    )


def _set_clean_string(
    instance: object,
    attribute: str,
    *,
    allow_empty: bool = False,
) -> None:
    object.__setattr__(
        instance,
        attribute,
        _clean_identifier(
            getattr(instance, attribute),
            attribute,
            allow_empty=allow_empty,
        ),
    )


def _set_optional_clean_string(
    instance: object,
    attribute: str,
    *,
    allow_empty: bool = False,
) -> None:
    value = getattr(instance, attribute)
    if value is None:
        return
    object.__setattr__(
        instance,
        attribute,
        _clean_identifier(value, attribute, allow_empty=allow_empty),
    )


def _clean_identifier(
    value: object,
    label: str,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise DecisionEvidencePacketValidationError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned and not allow_empty:
        raise DecisionEvidencePacketValidationError(f"{label} cannot be empty.")
    return cleaned


def _unique_ids(
    values: Iterable[object],
    *,
    id_attribute: str,
    label: str,
) -> frozenset[str]:
    seen: set[str] = set()
    for value in values:
        identifier = getattr(value, id_attribute)
        if identifier in seen:
            raise DecisionEvidencePacketValidationError(
                f"duplicate {label} id {identifier!r}."
            )
        seen.add(identifier)
    return frozenset(seen)


def _ensure_known_ids(
    *,
    owner: str,
    relationship: str,
    referenced_ids: tuple[str, ...],
    known_ids: frozenset[str],
) -> None:
    for referenced_id in referenced_ids:
        if referenced_id not in known_ids:
            raise DecisionEvidencePacketValidationError(
                f"{owner} references unknown {relationship} {referenced_id!r}."
            )
