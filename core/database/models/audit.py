from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from core.database.base import Base


class PersistenceAuditEventModel(Base):
    """
    Append-only audit event table for curated persistence records.

    This model is a persistence-boundary representation of
    ``PersistenceAuditEventRecord``. It intentionally stores generic entity
    identifiers so audit trails can span all platform persistence domains
    without introducing cross-domain foreign-key coupling.
    """

    __tablename__ = "persistence_audit_events"

    audit_event_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    system_source: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    actor_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
    "idx_persistence_audit_events_entity",
    PersistenceAuditEventModel.entity_type,
    PersistenceAuditEventModel.entity_id,
)

Index(
    "idx_persistence_audit_events_action_timestamp",
    PersistenceAuditEventModel.action,
    PersistenceAuditEventModel.timestamp,
)

Index(
    "idx_persistence_audit_events_entity_action_timestamp",
    PersistenceAuditEventModel.entity_type,
    PersistenceAuditEventModel.entity_id,
    PersistenceAuditEventModel.action,
    PersistenceAuditEventModel.timestamp,
)

Index(
    "idx_persistence_audit_events_workflow_execution",
    PersistenceAuditEventModel.workflow_name,
    PersistenceAuditEventModel.execution_id,
)

Index(
    "idx_persistence_audit_events_runtime_node",
    PersistenceAuditEventModel.runtime_id,
    PersistenceAuditEventModel.node_name,
)
