from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Any, Protocol

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from domain.authority import RiskTier

ENFORCED_CLAIM_EVIDENCE_LINK_RISK_TIERS = frozenset(
    (RiskTier.ENHANCED, RiskTier.VIGILANT),
)

_COMMON_CLAIM_EVIDENCE_LINK_VALUE_COLUMNS = (
    "link_id",
    "claim_target_id",
    "packet_id",
    "packet_claim_id",
    "risk_tier",
    "material",
    "supporting_evidence_ids",
    "reconstruction_reference_ids",
    "uncertainty_ids",
    "limitation_ids",
)
_COMMON_CLAIM_EVIDENCE_LINK_UPSERT_COLUMNS = (
    "claim_target_id",
    "packet_id",
    "packet_claim_id",
    "risk_tier",
    "material",
    "supporting_evidence_ids",
    "reconstruction_reference_ids",
    "uncertainty_ids",
    "limitation_ids",
)


class ClaimEvidenceLinkRecordProtocol(Protocol):
    """Common typed surface for persisted claim-evidence link records."""

    @property
    def link_id(self) -> str: ...

    @property
    def claim_target_id(self) -> str: ...

    @property
    def packet_id(self) -> str: ...

    @property
    def packet_claim_id(self) -> str: ...

    @property
    def risk_tier(self) -> RiskTier: ...

    @property
    def material(self) -> bool: ...

    @property
    def supporting_evidence_ids(self) -> tuple[str, ...]: ...

    @property
    def reconstruction_reference_ids(self) -> tuple[str, ...]: ...

    @property
    def uncertainty_ids(self) -> tuple[str, ...]: ...

    @property
    def limitation_ids(self) -> tuple[str, ...]: ...


def claim_evidence_link_common_model_kwargs(model: Any) -> dict[str, Any]:
    """Return constructor kwargs shared by report and recommendation links."""

    return {
        "link_id": model.link_id,
        "claim_target_id": model.claim_target_id,
        "packet_id": model.packet_id,
        "packet_claim_id": model.packet_claim_id,
        "risk_tier": model.risk_tier,
        "material": model.material,
        "supporting_evidence_ids": string_tuple(model.supporting_evidence_ids),
        "reconstruction_reference_ids": string_tuple(
            model.reconstruction_reference_ids,
        ),
        "uncertainty_ids": string_tuple(model.uncertainty_ids),
        "limitation_ids": string_tuple(model.limitation_ids),
    }


def claim_evidence_link_common_values(
    record: ClaimEvidenceLinkRecordProtocol,
) -> dict[str, Any]:
    """Return database values shared by report and recommendation links."""

    values = {
        column: getattr(record, column)
        for column in _COMMON_CLAIM_EVIDENCE_LINK_VALUE_COLUMNS
    }
    values["risk_tier"] = record.risk_tier.value
    values["supporting_evidence_ids"] = list(record.supporting_evidence_ids)
    values["reconstruction_reference_ids"] = list(record.reconstruction_reference_ids)
    values["uncertainty_ids"] = list(record.uncertainty_ids)
    values["limitation_ids"] = list(record.limitation_ids)
    return values


async def execute_claim_evidence_link_upserts[LinkRecordT](
    session: AsyncSession,
    links: Iterable[LinkRecordT],
    statement_factory: Callable[[LinkRecordT], Any],
) -> None:
    """Execute claim-evidence link upserts for an owning repository."""

    for link in links:
        await session.execute(statement_factory(link))


def claim_evidence_link_upsert_set_values(
    excluded: Any,
    *,
    owner_columns: tuple[str, ...],
) -> dict[str, Any]:
    """Return shared ``ON CONFLICT`` values for claim-evidence link tables."""

    return {
        **{
            column: getattr(excluded, column)
            for column in (*owner_columns, *_COMMON_CLAIM_EVIDENCE_LINK_UPSERT_COLUMNS)
        },
        "updated_at": func.now(),
    }


def normalize_claim_evidence_link_fields(
    record: object,
    *,
    risk_tier: object,
    material: object,
    supporting_evidence_ids: Sequence[str],
    reconstruction_reference_ids: Sequence[str],
    uncertainty_ids: Sequence[str],
    limitation_ids: Sequence[str],
) -> None:
    """Normalize and validate fields common to claim-evidence link records."""

    normalized_risk_tier = coerce_claim_evidence_link_risk_tier(risk_tier)
    if not isinstance(material, bool):
        raise ValueError("material must be a boolean.")
    normalized_supporting_evidence_ids = clean_identifier_tuple(
        supporting_evidence_ids,
        "supporting_evidence_id",
    )
    normalized_reconstruction_reference_ids = clean_identifier_tuple(
        reconstruction_reference_ids,
        "reconstruction_reference_id",
    )
    object.__setattr__(record, "risk_tier", normalized_risk_tier)
    object.__setattr__(
        record,
        "supporting_evidence_ids",
        normalized_supporting_evidence_ids,
    )
    object.__setattr__(
        record,
        "reconstruction_reference_ids",
        normalized_reconstruction_reference_ids,
    )
    object.__setattr__(
        record,
        "uncertainty_ids",
        clean_identifier_tuple(uncertainty_ids, "uncertainty_id"),
    )
    object.__setattr__(
        record,
        "limitation_ids",
        clean_identifier_tuple(limitation_ids, "limitation_id"),
    )
    validate_material_claim_evidence_link(
        material=material,
        risk_tier=normalized_risk_tier,
        supporting_evidence_ids=normalized_supporting_evidence_ids,
        reconstruction_reference_ids=normalized_reconstruction_reference_ids,
    )


def normalize_claim_evidence_link_record(
    record: ClaimEvidenceLinkRecordProtocol,
) -> None:
    """Normalize and validate common fields on a claim-evidence link record."""

    normalize_claim_evidence_link_fields(
        record,
        risk_tier=record.risk_tier,
        material=record.material,
        supporting_evidence_ids=record.supporting_evidence_ids,
        reconstruction_reference_ids=record.reconstruction_reference_ids,
        uncertainty_ids=record.uncertainty_ids,
        limitation_ids=record.limitation_ids,
    )


def clean_identifier_tuple(values: Sequence[str], label: str) -> tuple[str, ...]:
    """Validate and normalize a tuple/list of non-empty string identifiers."""

    return tuple(_clean_identifier(value, label) for value in values)


def coerce_claim_evidence_link_risk_tier(value: object) -> RiskTier:
    """Normalize and validate risk tiers allowed for material claim links."""

    if isinstance(value, RiskTier):
        risk_tier = value
    elif isinstance(value, str):
        risk_tier = RiskTier(value.strip().lower())
    else:
        raise ValueError("risk_tier must be a RiskTier.")
    if risk_tier not in ENFORCED_CLAIM_EVIDENCE_LINK_RISK_TIERS:
        raise ValueError(
            "claim evidence links require enhanced or vigilant risk tiers."
        )
    return risk_tier


def string_tuple(values: object) -> tuple[str, ...]:
    """Extract string identifiers from JSON values read from persistence."""

    if not isinstance(values, list):
        return ()
    return tuple(value for value in values if isinstance(value, str))


def validate_material_claim_evidence_link(
    *,
    material: bool,
    risk_tier: RiskTier,
    supporting_evidence_ids: tuple[str, ...],
    reconstruction_reference_ids: tuple[str, ...],
) -> None:
    """Ensure enforced material claim links are reconstructable."""

    if not material or risk_tier not in ENFORCED_CLAIM_EVIDENCE_LINK_RISK_TIERS:
        return
    if not supporting_evidence_ids:
        raise ValueError(
            "material enhanced and vigilant claim evidence links require "
            "supporting evidence identifiers."
        )
    if not reconstruction_reference_ids:
        raise ValueError(
            "material enhanced and vigilant claim evidence links require "
            "reconstruction reference identifiers."
        )


def _clean_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty.")
    return cleaned


__all__ = [
    "ClaimEvidenceLinkRecordProtocol",
    "execute_claim_evidence_link_upserts",
    "claim_evidence_link_common_model_kwargs",
    "claim_evidence_link_common_values",
    "claim_evidence_link_upsert_set_values",
    "normalize_claim_evidence_link_fields",
    "normalize_claim_evidence_link_record",
    "clean_identifier_tuple",
    "coerce_claim_evidence_link_risk_tier",
    "string_tuple",
    "validate_material_claim_evidence_link",
]
