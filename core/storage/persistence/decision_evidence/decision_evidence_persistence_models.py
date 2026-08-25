from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from domain.authority import RiskTier
from domain.decision_evidence import DECISION_EVIDENCE_PACKET_SCHEMA_VERSION

type DecisionEvidenceJsonScalar = str | int | float | bool | None
type DecisionEvidenceJsonValue = (
    DecisionEvidenceJsonScalar
    | Mapping[str, DecisionEvidenceJsonValue]
    | Sequence[DecisionEvidenceJsonValue]
)
type DecisionEvidenceJsonObject = Mapping[str, DecisionEvidenceJsonValue]
type DecisionEvidenceJsonArray = Sequence[DecisionEvidenceJsonValue]


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacketRecord:
    """Durable packet audit record with canonical reconstruction identifiers."""

    packet_id: str
    output_id: str
    schema_version: int
    risk_tier: RiskTier
    workflow_name: str
    workflow_definition_fingerprint: str
    execution_id: str
    authority_metadata: DecisionEvidenceJsonObject
    retention_metadata: DecisionEvidenceJsonObject
    reconstruction_reference_ids: tuple[str, ...]
    claim_audit: tuple[DecisionEvidenceJsonObject, ...]
    evidence_references: tuple[DecisionEvidenceJsonObject, ...]
    reconstruction_references: tuple[DecisionEvidenceJsonObject, ...]
    constraints: tuple[DecisionEvidenceJsonObject, ...] = ()
    uncertainties: tuple[DecisionEvidenceJsonObject, ...] = ()
    limitations: tuple[DecisionEvidenceJsonObject, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "packet_id", _clean_identifier(self.packet_id, "packet_id")
        )
        object.__setattr__(
            self, "output_id", _clean_identifier(self.output_id, "output_id")
        )
        object.__setattr__(self, "risk_tier", _coerce_risk_tier(self.risk_tier))
        if self.schema_version < DECISION_EVIDENCE_PACKET_SCHEMA_VERSION:
            raise ValueError("decision evidence packet schema_version is unsupported.")
        object.__setattr__(
            self,
            "reconstruction_reference_ids",
            tuple(
                _clean_identifier(reference_id, "reconstruction_reference_id")
                for reference_id in self.reconstruction_reference_ids
            ),
        )
        object.__setattr__(self, "authority_metadata", dict(self.authority_metadata))
        object.__setattr__(self, "retention_metadata", dict(self.retention_metadata))
        object.__setattr__(self, "claim_audit", _tuple_of_mappings(self.claim_audit))
        object.__setattr__(
            self,
            "evidence_references",
            _tuple_of_mappings(self.evidence_references),
        )
        object.__setattr__(
            self,
            "reconstruction_references",
            _tuple_of_mappings(self.reconstruction_references),
        )
        object.__setattr__(self, "constraints", _tuple_of_mappings(self.constraints))
        object.__setattr__(
            self, "uncertainties", _tuple_of_mappings(self.uncertainties)
        )
        object.__setattr__(self, "limitations", _tuple_of_mappings(self.limitations))
        for field_name in (
            "workflow_name",
            "workflow_definition_fingerprint",
            "execution_id",
        ):
            object.__setattr__(
                self,
                field_name,
                _clean_identifier(getattr(self, field_name), field_name),
            )

    def with_reconstruction_reference_ids(
        self,
        reconstruction_reference_ids: tuple[str, ...],
    ) -> DecisionEvidencePacketRecord:
        """Return a copy with alternate reconstruction ids for corruption tests."""

        return replace(
            self,
            reconstruction_reference_ids=reconstruction_reference_ids,
        )


@dataclass(frozen=True, slots=True)
class DecisionEvidencePacketPersistenceResult:
    """Result of persisting one decision evidence packet audit record."""

    success: bool
    packet_id: str | None = None
    records_persisted: int = 0
    errors: tuple[str, ...] = ()

    @classmethod
    def succeeded(
        cls,
        packet_id: str,
        *,
        records_persisted: int = 1,
    ) -> DecisionEvidencePacketPersistenceResult:
        return cls(
            success=True,
            packet_id=packet_id,
            records_persisted=records_persisted,
        )

    @classmethod
    def failed(
        cls,
        error: str,
        *,
        packet_id: str | None = None,
    ) -> DecisionEvidencePacketPersistenceResult:
        return cls(
            success=False,
            packet_id=packet_id,
            errors=(_clean_identifier(error, "error"),),
        )


def _tuple_of_mappings(
    values: Sequence[DecisionEvidenceJsonObject],
) -> tuple[DecisionEvidenceJsonObject, ...]:
    return tuple(dict(value) for value in values)


def _coerce_risk_tier(value: object) -> RiskTier:
    if isinstance(value, RiskTier):
        return value
    if isinstance(value, str):
        return RiskTier(value.strip().lower())
    raise ValueError("risk_tier must be a RiskTier.")


def _clean_identifier(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} cannot be empty.")
    return cleaned
