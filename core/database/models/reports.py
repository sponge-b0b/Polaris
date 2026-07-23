from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base


class ReportModel(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    report_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    subtitle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    markdown_body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    structured_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    "idx_reports_type_generated_at",
    ReportModel.report_type,
    ReportModel.generated_at,
)

Index(
    "idx_reports_workflow_execution",
    ReportModel.workflow_name,
    ReportModel.execution_id,
)


class ReportSectionModel(Base):
    __tablename__ = "report_sections"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "section_key",
            name="uq_report_sections_report_section_key",
        ),
    )

    section_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    report_id: Mapped[str] = mapped_column(
        ForeignKey(
            "reports.report_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    markdown_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    content_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    "idx_report_sections_report_order",
    ReportSectionModel.report_id,
    ReportSectionModel.display_order,
)


class ReportArtifactModel(Base):
    __tablename__ = "report_artifacts"

    artifact_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    report_id: Mapped[str] = mapped_column(
        ForeignKey(
            "reports.report_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    section_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "report_sections.section_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    artifact_uri: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    mime_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
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
    "idx_report_artifacts_report_type",
    ReportArtifactModel.report_id,
    ReportArtifactModel.artifact_type,
)


class ReportVersionModel(Base):
    __tablename__ = "report_versions"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "version_number",
            name="uq_report_versions_report_version_number",
        ),
        CheckConstraint(
            "version_number > 0",
            name="ck_report_versions_version_number_positive",
        ),
    )

    version_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    report_id: Mapped[str] = mapped_column(
        ForeignKey(
            "reports.report_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    subtitle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    markdown_body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    change_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )
    structured_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
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
    "idx_report_versions_report_created_at",
    ReportVersionModel.report_id,
    ReportVersionModel.created_at,
)

Index(
    "idx_report_versions_report_version_number",
    ReportVersionModel.report_id,
    ReportVersionModel.version_number,
)


class ReportPublicationModel(Base):
    __tablename__ = "report_publications"
    __table_args__ = (
        CheckConstraint(
            "published_at IS NULL OR published_at >= requested_at",
            name="ck_report_publications_published_at_not_before_requested_at",
        ),
    )

    publication_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )
    report_id: Mapped[str] = mapped_column(
        ForeignKey(
            "reports.report_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    version_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "report_versions.version_id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    publication_target: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    publication_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    artifact_uri: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
    "idx_report_publications_report_requested_at",
    ReportPublicationModel.report_id,
    ReportPublicationModel.requested_at,
)

Index(
    "idx_report_publications_target_status",
    ReportPublicationModel.publication_target,
    ReportPublicationModel.publication_status,
)

Index(
    "idx_report_publications_version_requested_at",
    ReportPublicationModel.version_id,
    ReportPublicationModel.requested_at,
)
