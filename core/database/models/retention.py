from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class PersistenceRetentionPolicyModel(Base):
    """
    Persistence-boundary table for domain retention policy metadata.

    This model stores lifecycle policy records only. It does not execute archive
    or deletion behavior and does not imply automatic mutation of canonical
    PostgreSQL records.
    """

    __tablename__ = "persistence_retention_policies"
    __table_args__ = (
        CheckConstraint(
            "retention_period_days > 0",
            name="ck_persistence_retention_policies_period_positive",
        ),
        UniqueConstraint(
            "domain",
            name="uq_persistence_retention_policies_domain",
        ),
    )

    policy_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    domain: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    retention_period_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    archive_before_delete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    deletion_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
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


Index(
    "idx_persistence_retention_policies_domain_enabled",
    PersistenceRetentionPolicyModel.domain,
    PersistenceRetentionPolicyModel.enabled,
)

Index(
    "idx_persistence_retention_policies_lifecycle_flags",
    PersistenceRetentionPolicyModel.enabled,
    PersistenceRetentionPolicyModel.archive_before_delete,
    PersistenceRetentionPolicyModel.deletion_eligible,
)
