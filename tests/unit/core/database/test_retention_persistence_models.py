from __future__ import annotations

from typing import cast

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import JSONB

from core.database.base import Base
from core.database.models.retention import PersistenceRetentionPolicyModel


def test_retention_policy_model_is_imported_into_base_metadata() -> None:
    assert "persistence_retention_policies" in Base.metadata.tables


def test_retention_policy_model_stores_lifecycle_metadata_only() -> None:
    table = cast(
        Table,
        PersistenceRetentionPolicyModel.__table__,
    )
    columns = table.c
    primary_keys = {column.name for column in table.primary_key}
    unique_constraints = {constraint.name for constraint in table.constraints}
    check_constraints = {constraint.name for constraint in table.constraints}

    assert primary_keys == {"policy_id"}
    assert columns.domain.nullable is False
    assert columns.retention_period_days.nullable is False
    assert columns.archive_before_delete.nullable is False
    assert columns.deletion_eligible.nullable is False
    assert columns.enabled.nullable is False
    assert columns.description.nullable is True
    assert columns.created_at.server_default is not None
    assert columns.updated_at.server_default is not None
    assert "uq_persistence_retention_policies_domain" in unique_constraints
    assert "ck_persistence_retention_policies_period_positive" in check_constraints


def test_retention_policy_model_has_lifecycle_lookup_indexes() -> None:
    table = cast(
        Table,
        PersistenceRetentionPolicyModel.__table__,
    )
    index_columns = {
        str(index.name): tuple(column.name for column in index.columns)
        for index in table.indexes
    }

    assert index_columns["ix_persistence_retention_policies_domain"] == ("domain",)
    assert index_columns["ix_persistence_retention_policies_enabled"] == ("enabled",)
    assert index_columns["ix_persistence_retention_policies_deletion_eligible"] == (
        "deletion_eligible",
    )
    assert index_columns["idx_persistence_retention_policies_domain_enabled"] == (
        "domain",
        "enabled",
    )
    assert index_columns["idx_persistence_retention_policies_lifecycle_flags"] == (
        "enabled",
        "archive_before_delete",
        "deletion_eligible",
    )


def test_retention_policy_model_uses_jsonb_at_persistence_boundary() -> None:
    assert isinstance(
        PersistenceRetentionPolicyModel.__table__.c.metadata.type,
        JSONB,
    )
