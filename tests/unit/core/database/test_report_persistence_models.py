from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.reports import ReportArtifactModel
from core.database.models.reports import ReportModel
from core.database.models.reports import ReportPublicationModel
from core.database.models.reports import ReportSectionModel
from core.database.models.reports import ReportVersionModel


def test_report_models_are_imported_into_base_metadata() -> None:
    assert "reports" in Base.metadata.tables
    assert "report_sections" in Base.metadata.tables
    assert "report_artifacts" in Base.metadata.tables
    assert "report_versions" in Base.metadata.tables
    assert "report_publications" in Base.metadata.tables


def test_report_model_persists_human_readable_report_lineage() -> None:
    columns = ReportModel.__table__.c
    primary_keys = {column.name for column in ReportModel.__table__.primary_key}

    assert primary_keys == {"report_id"}
    assert columns.report_type.nullable is False
    assert columns.title.nullable is False
    assert columns.generated_at.nullable is False
    assert columns.markdown_body.nullable is False
    assert columns.workflow_name.nullable is True
    assert columns.execution_id.nullable is True
    assert columns.runtime_id.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_report_section_model_persists_ordered_section_content() -> None:
    columns = ReportSectionModel.__table__.c
    primary_keys = {column.name for column in ReportSectionModel.__table__.primary_key}
    foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.report_id.foreign_keys
    }

    assert primary_keys == {"section_id"}
    assert columns.report_id.nullable is False
    assert columns.section_key.nullable is False
    assert columns.title.nullable is False
    assert columns.display_order.nullable is False
    assert foreign_keys == {"reports.report_id"}
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_report_artifact_model_persists_artifact_references() -> None:
    columns = ReportArtifactModel.__table__.c
    primary_keys = {column.name for column in ReportArtifactModel.__table__.primary_key}
    report_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.report_id.foreign_keys
    }
    section_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.section_id.foreign_keys
    }

    assert primary_keys == {"artifact_id"}
    assert columns.report_id.nullable is False
    assert columns.section_id.nullable is True
    assert columns.artifact_type.nullable is False
    assert columns.artifact_uri.nullable is False
    assert report_foreign_keys == {"reports.report_id"}
    assert section_foreign_keys == {"report_sections.section_id"}
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None


def test_report_version_model_persists_versioned_report_content() -> None:
    table = cast(Table, ReportVersionModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    report_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.report_id.foreign_keys
    }
    unique_constraints = {constraint.name for constraint in table.constraints}
    check_constraints = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert primary_keys == {"version_id"}
    assert columns.report_id.nullable is False
    assert columns.version_number.nullable is False
    assert columns.created_at.nullable is False
    assert columns.markdown_body.nullable is False
    assert columns.title.nullable is True
    assert columns.subtitle.nullable is True
    assert columns.change_summary.nullable is True
    assert columns.created_by.nullable is True
    assert report_foreign_keys == {"reports.report_id"}
    assert "uq_report_versions_report_version_number" in unique_constraints
    assert "ck_report_versions_version_number_positive" in check_constraints
    assert "idx_report_versions_report_created_at" in index_names
    assert "idx_report_versions_report_version_number" in index_names
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_report_publication_model_persists_publication_state() -> None:
    table = cast(Table, ReportPublicationModel.__table__)
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    report_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.report_id.foreign_keys
    }
    version_foreign_keys = {
        foreign_key.target_fullname for foreign_key in columns.version_id.foreign_keys
    }
    check_constraints = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert primary_keys == {"publication_id"}
    assert columns.report_id.nullable is False
    assert columns.version_id.nullable is True
    assert columns.publication_target.nullable is False
    assert columns.publication_status.nullable is False
    assert columns.requested_at.nullable is False
    assert columns.published_at.nullable is True
    assert columns.artifact_uri.nullable is True
    assert columns.error.nullable is True
    assert report_foreign_keys == {"reports.report_id"}
    assert version_foreign_keys == {"report_versions.version_id"}
    assert (
        "ck_report_publications_published_at_not_before_requested_at"
        in check_constraints
    )
    assert "idx_report_publications_report_requested_at" in index_names
    assert "idx_report_publications_target_status" in index_names
    assert "idx_report_publications_version_requested_at" in index_names
    assert columns.row_created_at.server_default is not None
    assert columns.row_updated_at.server_default is not None


def test_report_models_use_jsonb_at_persistence_boundaries() -> None:
    assert isinstance(
        ReportModel.__table__.c.structured_payload.type,
        JSONB,
    )
    assert isinstance(
        ReportModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        ReportSectionModel.__table__.c.content_payload.type,
        JSONB,
    )
    assert isinstance(
        ReportSectionModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        ReportArtifactModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        ReportVersionModel.__table__.c.structured_payload.type,
        JSONB,
    )
    assert isinstance(
        ReportVersionModel.__table__.c.metadata.type,
        JSONB,
    )
    assert isinstance(
        ReportPublicationModel.__table__.c.metadata.type,
        JSONB,
    )
