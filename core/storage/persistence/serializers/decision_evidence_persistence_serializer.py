from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from core.database.models.decision_evidence import DecisionEvidencePacketModel
from core.storage.persistence.decision_evidence import (
    DecisionEvidenceJsonObject,
    DecisionEvidencePacketRecord,
)
from core.storage.persistence.serializers.completed_run_serializer import (
    sanitize_json_value,
)
from domain.authority import (
    RiskTier,
    SourceOfTruthCategory,
    risk_authority_contract_from_metadata,
)
from domain.decision_evidence import (
    ClaimEvidenceBinding,
    DecisionEvidencePacket,
    EvidenceConstraint,
    EvidenceLimitation,
    EvidenceReference,
    EvidenceReferenceKind,
    EvidenceRetentionRequirement,
    EvidenceUncertainty,
    MaterialClaim,
    ReconstructionReference,
    ReconstructionReferenceKind,
)


class DecisionEvidencePacketPersistenceSerializer:
    """Serialize decision evidence packets at the PostgreSQL JSONB boundary."""

    @staticmethod
    def record_from_packet(
        packet: DecisionEvidencePacket,
    ) -> DecisionEvidencePacketRecord:
        """Create a durable audit record without copying source evidence content."""

        return DecisionEvidencePacketRecord(
            packet_id=packet.packet_id,
            output_id=packet.output_id,
            schema_version=packet.schema_version,
            risk_tier=packet.risk_tier,
            authority_metadata=_json_object(packet.authority.to_metadata()),
            retention_metadata=_retention_values(packet.retention),
            reconstruction_reference_ids=packet.reconstruction_reference_ids,
            claim_audit=tuple(_claim_values(claim) for claim in packet.claims),
            evidence_references=tuple(
                _evidence_reference_values(evidence) for evidence in packet.evidence
            ),
            reconstruction_references=tuple(
                _reconstruction_reference_values(reference)
                for reference in packet.reconstruction_references
            ),
            constraints=tuple(
                _constraint_values(constraint) for constraint in packet.constraints
            ),
            uncertainties=tuple(
                _uncertainty_values(uncertainty) for uncertainty in packet.uncertainties
            ),
            limitations=tuple(
                _limitation_values(limitation) for limitation in packet.limitations
            ),
        )

    @staticmethod
    def packet_from_record(
        record: DecisionEvidencePacketRecord,
    ) -> DecisionEvidencePacket:
        """Rehydrate a typed packet from persisted audit fields."""

        _validate_record_reconstruction_reference_ids(record)
        return DecisionEvidencePacket(
            packet_id=record.packet_id,
            output_id=record.output_id,
            authority=risk_authority_contract_from_metadata(
                cast(Mapping[str, object], record.authority_metadata),
            ),
            claims=tuple(_claim_from_values(values) for values in record.claim_audit),
            evidence=tuple(
                _evidence_reference_from_values(values)
                for values in record.evidence_references
            ),
            reconstruction_references=tuple(
                _reconstruction_reference_from_values(values)
                for values in record.reconstruction_references
            ),
            retention=_retention_from_values(record.retention_metadata),
            constraints=tuple(
                _constraint_from_values(values) for values in record.constraints
            ),
            uncertainties=tuple(
                _uncertainty_from_values(values) for values in record.uncertainties
            ),
            limitations=tuple(
                _limitation_from_values(values) for values in record.limitations
            ),
            schema_version=record.schema_version,
        )

    @staticmethod
    def packet_values(
        record: DecisionEvidencePacketRecord,
    ) -> dict[str, Any]:
        """Serialize a packet record into ORM column values."""

        return {
            "packet_id": record.packet_id,
            "output_id": record.output_id,
            "schema_version": record.schema_version,
            "risk_tier": record.risk_tier.value,
            "authority_metadata": dict(record.authority_metadata),
            "retention_metadata": dict(record.retention_metadata),
            "reconstruction_reference_ids": list(record.reconstruction_reference_ids),
            "claim_audit": [dict(value) for value in record.claim_audit],
            "evidence_references": [
                dict(value) for value in record.evidence_references
            ],
            "reconstruction_references": [
                dict(value) for value in record.reconstruction_references
            ],
            "constraints": [dict(value) for value in record.constraints],
            "uncertainties": [dict(value) for value in record.uncertainties],
            "limitations": [dict(value) for value in record.limitations],
        }

    @staticmethod
    def record_from_model(
        model: DecisionEvidencePacketModel,
    ) -> DecisionEvidencePacketRecord:
        """Deserialize an ORM model into a typed packet audit record."""

        return DecisionEvidencePacketRecord(
            packet_id=model.packet_id,
            output_id=model.output_id,
            schema_version=model.schema_version,
            risk_tier=RiskTier(model.risk_tier),
            authority_metadata=cast(
                DecisionEvidenceJsonObject, model.authority_metadata
            ),
            retention_metadata=cast(
                DecisionEvidenceJsonObject, model.retention_metadata
            ),
            reconstruction_reference_ids=_string_sequence(
                model.reconstruction_reference_ids,
                "reconstruction reference ids",
            ),
            claim_audit=_json_object_sequence(model.claim_audit, "claim audit"),
            evidence_references=_json_object_sequence(
                model.evidence_references,
                "evidence references",
            ),
            reconstruction_references=_json_object_sequence(
                model.reconstruction_references,
                "reconstruction references",
            ),
            constraints=_json_object_sequence(model.constraints, "constraints"),
            uncertainties=_json_object_sequence(model.uncertainties, "uncertainties"),
            limitations=_json_object_sequence(model.limitations, "limitations"),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


def _claim_values(claim: MaterialClaim) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "claim_id": claim.claim_id,
            "text": claim.text,
            "material": claim.material,
            "evidence": {
                "supporting_evidence_ids": claim.evidence.supporting_evidence_ids,
                "conflicting_evidence_ids": claim.evidence.conflicting_evidence_ids,
                "constraint_ids": claim.evidence.constraint_ids,
                "uncertainty_ids": claim.evidence.uncertainty_ids,
                "limitation_ids": claim.evidence.limitation_ids,
            },
        }
    )


def _evidence_reference_values(
    evidence: EvidenceReference,
) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "evidence_id": evidence.evidence_id,
            "kind": evidence.kind.value,
            "reconstruction_reference_ids": evidence.reconstruction_reference_ids,
            "summary": evidence.summary,
            "source_of_truth": _optional_enum_value(evidence.source_of_truth),
        }
    )


def _reconstruction_reference_values(
    reference: ReconstructionReference,
) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "reference_id": reference.reference_id,
            "kind": reference.kind.value,
            "record_id": reference.record_id,
            "source_of_truth": _optional_enum_value(reference.source_of_truth),
            "snapshot_id": reference.snapshot_id,
            "content_digest": reference.content_digest,
        }
    )


def _constraint_values(constraint: EvidenceConstraint) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "constraint_id": constraint.constraint_id,
            "summary": constraint.summary,
            "evidence_ids": constraint.evidence_ids,
        }
    )


def _uncertainty_values(uncertainty: EvidenceUncertainty) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "uncertainty_id": uncertainty.uncertainty_id,
            "summary": uncertainty.summary,
            "evidence_ids": uncertainty.evidence_ids,
        }
    )


def _limitation_values(limitation: EvidenceLimitation) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "limitation_id": limitation.limitation_id,
            "summary": limitation.summary,
            "evidence_ids": limitation.evidence_ids,
        }
    )


def _retention_values(
    retention: EvidenceRetentionRequirement,
) -> DecisionEvidenceJsonObject:
    return _json_object(
        {
            "retain_until": retention.retain_until,
            "policy_id": retention.policy_id,
            "legal_hold": retention.legal_hold,
        }
    )


def _claim_from_values(values: DecisionEvidenceJsonObject) -> MaterialClaim:
    evidence_values = _required_mapping(values, "evidence")
    return MaterialClaim(
        claim_id=_required_string(values, "claim_id"),
        text=_required_string(values, "text"),
        evidence=ClaimEvidenceBinding(
            supporting_evidence_ids=_string_tuple(
                evidence_values,
                "supporting_evidence_ids",
            ),
            conflicting_evidence_ids=_string_tuple(
                evidence_values,
                "conflicting_evidence_ids",
            ),
            constraint_ids=_string_tuple(evidence_values, "constraint_ids"),
            uncertainty_ids=_string_tuple(evidence_values, "uncertainty_ids"),
            limitation_ids=_string_tuple(evidence_values, "limitation_ids"),
        ),
        material=_optional_bool(values, "material", default=True),
    )


def _evidence_reference_from_values(
    values: DecisionEvidenceJsonObject,
) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=_required_string(values, "evidence_id"),
        kind=EvidenceReferenceKind(_required_string(values, "kind")),
        reconstruction_reference_ids=_string_tuple(
            values,
            "reconstruction_reference_ids",
        ),
        summary=_optional_string(values, "summary") or "",
        source_of_truth=_optional_source_of_truth(values, "source_of_truth"),
    )


def _reconstruction_reference_from_values(
    values: DecisionEvidenceJsonObject,
) -> ReconstructionReference:
    return ReconstructionReference(
        reference_id=_required_string(values, "reference_id"),
        kind=ReconstructionReferenceKind(_required_string(values, "kind")),
        record_id=_required_string(values, "record_id"),
        source_of_truth=_optional_source_of_truth(values, "source_of_truth"),
        snapshot_id=_optional_string(values, "snapshot_id"),
        content_digest=_optional_string(values, "content_digest"),
    )


def _constraint_from_values(values: DecisionEvidenceJsonObject) -> EvidenceConstraint:
    return EvidenceConstraint(
        constraint_id=_required_string(values, "constraint_id"),
        summary=_required_string(values, "summary"),
        evidence_ids=_string_tuple(values, "evidence_ids"),
    )


def _uncertainty_from_values(values: DecisionEvidenceJsonObject) -> EvidenceUncertainty:
    return EvidenceUncertainty(
        uncertainty_id=_required_string(values, "uncertainty_id"),
        summary=_required_string(values, "summary"),
        evidence_ids=_string_tuple(values, "evidence_ids"),
    )


def _limitation_from_values(values: DecisionEvidenceJsonObject) -> EvidenceLimitation:
    return EvidenceLimitation(
        limitation_id=_required_string(values, "limitation_id"),
        summary=_required_string(values, "summary"),
        evidence_ids=_string_tuple(values, "evidence_ids"),
    )


def _retention_from_values(
    values: DecisionEvidenceJsonObject,
) -> EvidenceRetentionRequirement:
    return EvidenceRetentionRequirement(
        retain_until=_required_string(values, "retain_until"),
        policy_id=_required_string(values, "policy_id"),
        legal_hold=_optional_bool(values, "legal_hold", default=False),
    )


def _validate_record_reconstruction_reference_ids(
    record: DecisionEvidencePacketRecord,
) -> None:
    reference_ids = tuple(
        _required_string(reference, "reference_id")
        for reference in record.reconstruction_references
    )
    if record.reconstruction_reference_ids != reference_ids:
        raise ValueError(
            "decision evidence packet reconstruction reference ids do not match "
            "reconstruction references."
        )


def _json_object(value: Mapping[str, object]) -> DecisionEvidenceJsonObject:
    sanitized = sanitize_json_value(value)
    if not isinstance(sanitized, Mapping):
        raise ValueError("decision evidence packet value must be a JSON object.")
    return cast(DecisionEvidenceJsonObject, sanitized)


def _required_mapping(
    values: DecisionEvidenceJsonObject,
    key: str,
) -> DecisionEvidenceJsonObject:
    value = values.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"decision evidence packet field {key!r} must be an object.")
    return cast(DecisionEvidenceJsonObject, value)


def _required_string(values: DecisionEvidenceJsonObject, key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str):
        raise ValueError(f"decision evidence packet field {key!r} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"decision evidence packet field {key!r} cannot be empty.")
    return cleaned


def _optional_string(
    values: DecisionEvidenceJsonObject,
    key: str,
) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"decision evidence packet field {key!r} must be a string.")
    cleaned = value.strip()
    return cleaned or None


def _optional_bool(
    values: DecisionEvidenceJsonObject,
    key: str,
    *,
    default: bool,
) -> bool:
    value = values.get(key, default)
    if isinstance(value, bool):
        return value
    raise ValueError(f"decision evidence packet field {key!r} must be a boolean.")


def _optional_source_of_truth(
    values: DecisionEvidenceJsonObject,
    key: str,
) -> SourceOfTruthCategory | None:
    value = _optional_string(values, key)
    if value is None:
        return None
    return SourceOfTruthCategory(value)


def _string_tuple(values: DecisionEvidenceJsonObject, key: str) -> tuple[str, ...]:
    value = values.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValueError(
            f"decision evidence packet field {key!r} must be a string list."
        )
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"decision evidence packet field {key!r} must be a string list."
            )
        output.append(item)
    return tuple(output)


def _string_sequence(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValueError(f"decision evidence packet {label} must be a string list.")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"decision evidence packet {label} must be a string list.")
        output.append(item)
    return tuple(output)


def _json_object_sequence(
    value: object,
    label: str,
) -> tuple[DecisionEvidenceJsonObject, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ValueError(f"decision evidence packet {label} must be an object list.")
    output: list[DecisionEvidenceJsonObject] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(
                f"decision evidence packet {label} must be an object list."
            )
        output.append(cast(DecisionEvidenceJsonObject, item))
    return tuple(output)


def _optional_enum_value(value: SourceOfTruthCategory | None) -> str | None:
    if value is None:
        return None
    return value.value


__all__ = ["DecisionEvidencePacketPersistenceSerializer"]
