from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from domain.authority import RiskTier
from domain.decision_evidence.packets import (
    DecisionEvidencePacket,
    DecisionEvidencePacketValidationError,
    EvidenceReference,
    MaterialClaim,
    UnsupportedMaterialClaimError,
)

DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY: Final = (
    "decision_evidence_claim_references"
)
DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION: Final[int] = 1
_DECISION_EVIDENCE_REQUIRED_RISK_TIERS: Final[frozenset[RiskTier]] = frozenset(
    {RiskTier.ENHANCED, RiskTier.VIGILANT}
)


@dataclass(frozen=True, slots=True)
class EvidenceClaimReference:
    """Reference-only binding from one presentation claim to a packet claim.

    Recommendation explanations and report narrative may repeat claim text for
    readers, but they must not copy canonical evidence payloads. This contract
    carries only durable packet, evidence, uncertainty, limitation, and
    reconstruction identifiers that can rebuild the authoritative packet.
    """

    packet_id: str
    output_id: str
    claim_id: str
    risk_tier: RiskTier
    supporting_evidence_ids: tuple[str, ...]
    reconstruction_reference_ids: tuple[str, ...]
    uncertainty_ids: tuple[str, ...] = ()
    limitation_ids: tuple[str, ...] = ()
    material: bool = True
    schema_version: int = DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "packet_id", _clean_string(self.packet_id, "packet_id")
        )
        object.__setattr__(
            self, "output_id", _clean_string(self.output_id, "output_id")
        )
        object.__setattr__(self, "claim_id", _clean_string(self.claim_id, "claim_id"))
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        object.__setattr__(
            self,
            "supporting_evidence_ids",
            _clean_string_tuple(self.supporting_evidence_ids, "supporting_evidence_id"),
        )
        object.__setattr__(
            self,
            "reconstruction_reference_ids",
            _clean_string_tuple(
                self.reconstruction_reference_ids,
                "reconstruction_reference_id",
            ),
        )
        object.__setattr__(
            self,
            "uncertainty_ids",
            _clean_string_tuple(self.uncertainty_ids, "uncertainty_id"),
        )
        object.__setattr__(
            self,
            "limitation_ids",
            _clean_string_tuple(self.limitation_ids, "limitation_id"),
        )
        if self.schema_version != DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION:
            raise DecisionEvidencePacketValidationError(
                "decision evidence claim reference schema_version is unsupported."
            )
        if self.material and self.risk_tier in _DECISION_EVIDENCE_REQUIRED_RISK_TIERS:
            if not self.supporting_evidence_ids:
                raise UnsupportedMaterialClaimError(
                    f"material claim {self.claim_id!r} lacks supporting evidence."
                )
            if not self.reconstruction_reference_ids:
                raise UnsupportedMaterialClaimError(
                    f"material claim {self.claim_id!r} lacks reconstruction references."
                )

    def as_metadata(self) -> dict[str, object]:
        """Serialize this reference as persistence-safe metadata."""

        return {
            "schema_version": self.schema_version,
            "packet_id": self.packet_id,
            "output_id": self.output_id,
            "claim_id": self.claim_id,
            "risk_tier": self.risk_tier.value,
            "material": self.material,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "reconstruction_reference_ids": list(self.reconstruction_reference_ids),
            "uncertainty_ids": list(self.uncertainty_ids),
            "limitation_ids": list(self.limitation_ids),
        }


@dataclass(frozen=True, slots=True)
class EvidenceClaimReferenceSet:
    """Packet claim references attached to one recommendation/report boundary."""

    claim_references: tuple[EvidenceClaimReference, ...]
    schema_version: int = DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "claim_references",
            tuple(self.claim_references),
        )
        if self.schema_version != DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION:
            raise DecisionEvidencePacketValidationError(
                "decision evidence claim reference set schema_version is unsupported."
            )
        for reference in self.claim_references:
            if not isinstance(reference, EvidenceClaimReference):
                raise DecisionEvidencePacketValidationError(
                    "claim reference set entries must be "
                    "EvidenceClaimReference instances."
                )

    @property
    def packet_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(reference.packet_id for reference in self.claim_references)
        )

    @property
    def reconstruction_reference_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                reconstruction_id
                for reference in self.claim_references
                for reconstruction_id in reference.reconstruction_reference_ids
            )
        )

    def as_metadata(self) -> dict[str, object]:
        """Serialize the set without duplicating canonical evidence payloads."""

        return {
            "schema_version": self.schema_version,
            "packet_ids": list(self.packet_ids),
            "reconstruction_reference_ids": list(self.reconstruction_reference_ids),
            "claim_references": [
                reference.as_metadata() for reference in self.claim_references
            ],
        }


def evidence_claim_references_from_packet(
    packet: DecisionEvidencePacket,
    *,
    claim_ids: Iterable[str] | None = None,
) -> EvidenceClaimReferenceSet:
    """Create reference-only claim bindings from a canonical evidence packet."""

    selected_claim_ids = None if claim_ids is None else set(claim_ids)
    evidence_by_id = {evidence.evidence_id: evidence for evidence in packet.evidence}
    references: list[EvidenceClaimReference] = []
    for claim in packet.claims:
        if selected_claim_ids is not None and claim.claim_id not in selected_claim_ids:
            continue
        references.append(
            _claim_reference_from_packet_claim(
                packet=packet,
                claim=claim,
                evidence_by_id=evidence_by_id,
            )
        )
    return EvidenceClaimReferenceSet(claim_references=tuple(references))


def evidence_claim_references_from_metadata(value: object) -> EvidenceClaimReferenceSet:
    """Parse persisted or workflow-supplied claim reference metadata."""

    if isinstance(value, EvidenceClaimReferenceSet):
        return value
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return EvidenceClaimReferenceSet(
            claim_references=tuple(
                _claim_reference_from_mapping(item) for item in value
            )
        )
    if not isinstance(value, Mapping):
        raise DecisionEvidencePacketValidationError(
            "decision evidence claim references metadata must be an object or list."
        )
    schema_version = _int_value(
        value.get("schema_version", DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION),
        "schema_version",
    )
    claim_values = value.get("claim_references", ())
    if not isinstance(claim_values, Sequence) or isinstance(
        claim_values,
        str | bytes | bytearray,
    ):
        raise DecisionEvidencePacketValidationError(
            "decision evidence claim_references must be a list."
        )
    return EvidenceClaimReferenceSet(
        claim_references=tuple(
            _claim_reference_from_mapping(item) for item in claim_values
        ),
        schema_version=schema_version,
    )


def evidence_claim_references_metadata(
    references: Iterable[EvidenceClaimReference],
) -> dict[str, object]:
    """Build metadata for attached claim references."""

    return EvidenceClaimReferenceSet(claim_references=tuple(references)).as_metadata()


def _claim_reference_from_packet_claim(
    *,
    packet: DecisionEvidencePacket,
    claim: MaterialClaim,
    evidence_by_id: Mapping[str, EvidenceReference],
) -> EvidenceClaimReference:
    reconstruction_ids: list[str] = []
    for evidence_id in (
        *claim.evidence.supporting_evidence_ids,
        *claim.evidence.conflicting_evidence_ids,
    ):
        evidence = evidence_by_id[evidence_id]
        reconstruction_ids.extend(evidence.reconstruction_reference_ids)
    return EvidenceClaimReference(
        packet_id=packet.packet_id,
        output_id=packet.output_id,
        claim_id=claim.claim_id,
        risk_tier=packet.risk_tier,
        material=claim.material,
        supporting_evidence_ids=claim.evidence.supporting_evidence_ids,
        reconstruction_reference_ids=tuple(dict.fromkeys(reconstruction_ids)),
        uncertainty_ids=claim.evidence.uncertainty_ids,
        limitation_ids=claim.evidence.limitation_ids,
    )


def _claim_reference_from_mapping(value: object) -> EvidenceClaimReference:
    if not isinstance(value, Mapping):
        raise DecisionEvidencePacketValidationError(
            "decision evidence claim reference entries must be objects."
        )
    return EvidenceClaimReference(
        packet_id=_required_string(value, "packet_id"),
        output_id=_required_string(value, "output_id"),
        claim_id=_required_string(value, "claim_id"),
        risk_tier=_coerce_risk_tier(_required_string(value, "risk_tier")),
        material=_bool_value(value.get("material", True), "material"),
        supporting_evidence_ids=_string_tuple(
            value.get("supporting_evidence_ids", ()),
            "supporting_evidence_ids",
        ),
        reconstruction_reference_ids=_string_tuple(
            value.get("reconstruction_reference_ids", ()),
            "reconstruction_reference_ids",
        ),
        uncertainty_ids=_string_tuple(
            value.get("uncertainty_ids", ()), "uncertainty_ids"
        ),
        limitation_ids=_string_tuple(value.get("limitation_ids", ()), "limitation_ids"),
        schema_version=_int_value(
            value.get(
                "schema_version",
                DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION,
            ),
            "schema_version",
        ),
    )


def _required_string(value: Mapping[object, object], key: str) -> str:
    return _clean_string(value.get(key), key)


def _clean_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise DecisionEvidencePacketValidationError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise DecisionEvidencePacketValidationError(f"{label} cannot be empty.")
    return cleaned


def _clean_string_tuple(values: Iterable[object], label: str) -> tuple[str, ...]:
    return tuple(_clean_string(value, label) for value in values)


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise DecisionEvidencePacketValidationError(f"{label} must be a list.")
    return _clean_string_tuple(value, label)


def _coerce_risk_tier(value: object) -> RiskTier:
    if isinstance(value, RiskTier):
        return value
    if isinstance(value, str):
        try:
            return RiskTier(value.strip().lower())
        except ValueError as exc:
            raise DecisionEvidencePacketValidationError(
                "risk_tier must be a supported RiskTier."
            ) from exc
    raise DecisionEvidencePacketValidationError("risk_tier must be a RiskTier.")


def _bool_value(value: object, label: str) -> bool:
    if isinstance(value, bool):
        return value
    raise DecisionEvidencePacketValidationError(f"{label} must be a boolean.")


def _int_value(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DecisionEvidencePacketValidationError(f"{label} must be an integer.")
    return value


__all__ = [
    "DECISION_EVIDENCE_CLAIM_REFERENCE_SCHEMA_VERSION",
    "DECISION_EVIDENCE_CLAIM_REFERENCES_METADATA_KEY",
    "EvidenceClaimReference",
    "EvidenceClaimReferenceSet",
    "evidence_claim_references_from_metadata",
    "evidence_claim_references_from_packet",
    "evidence_claim_references_metadata",
]
