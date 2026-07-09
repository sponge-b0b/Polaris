from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class PersistenceLineageLinkModel(Base):
    __tablename__ = "persistence_lineage_links"
    __table_args__ = (
        UniqueConstraint(
            "source_record_type",
            "source_record_id",
            "relationship_type",
            "target_record_type",
            "target_record_id",
            name="uq_persistence_lineage_links_natural_key",
        ),
    )

    link_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    source_record_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    source_record_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    target_record_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    target_record_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    workflow_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    execution_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    runtime_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    node_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    row_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    row_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "idx_persistence_lineage_links_source",
    PersistenceLineageLinkModel.source_record_type,
    PersistenceLineageLinkModel.source_record_id,
)

Index(
    "idx_persistence_lineage_links_target",
    PersistenceLineageLinkModel.target_record_type,
    PersistenceLineageLinkModel.target_record_id,
)

Index(
    "idx_persistence_lineage_links_relationship",
    PersistenceLineageLinkModel.relationship_type,
    PersistenceLineageLinkModel.source_record_type,
    PersistenceLineageLinkModel.target_record_type,
)

Index(
    "idx_persistence_lineage_links_workflow_execution",
    PersistenceLineageLinkModel.workflow_name,
    PersistenceLineageLinkModel.execution_id,
)
