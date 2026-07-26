from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class ClaimEvidenceLinkColumnsMixin:
    """Shared database columns for report/recommendation claim evidence links."""

    link_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    claim_target_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    packet_id: Mapped[str] = mapped_column(
        ForeignKey(
            "decision_evidence_packets.packet_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    packet_claim_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    risk_tier: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    material: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    supporting_evidence_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    reconstruction_reference_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    uncertainty_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    limitation_ids: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def claim_evidence_link_table_args(table_name: str) -> tuple[CheckConstraint, ...]:
    """Return check constraints shared by claim evidence link tables."""

    return (
        CheckConstraint(
            "risk_tier IN ('enhanced', 'vigilant')",
            name=f"ck_{table_name}_risk_tier",
        ),
        CheckConstraint(
            "jsonb_typeof(supporting_evidence_ids) = 'array'",
            name=f"ck_{table_name}_supporting_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(reconstruction_reference_ids) = 'array'",
            name=f"ck_{table_name}_reconstruction_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(uncertainty_ids) = 'array'",
            name=f"ck_{table_name}_uncertainty_ids_array",
        ),
        CheckConstraint(
            "jsonb_typeof(limitation_ids) = 'array'",
            name=f"ck_{table_name}_limitation_ids_array",
        ),
        CheckConstraint(
            "NOT (material AND (jsonb_array_length(supporting_evidence_ids) = 0 "
            "OR jsonb_array_length(reconstruction_reference_ids) = 0))",
            name=f"ck_{table_name}_material_has_support",
        ),
    )


__all__ = [
    "ClaimEvidenceLinkColumnsMixin",
    "claim_evidence_link_table_args",
]
