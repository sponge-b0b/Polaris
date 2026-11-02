"""Persist minimum authority regimes and immutable Human Investment Decisions.

Revision ID: 0016_governance_human_decisions
Revises: 0015_intelligence_judgments
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_governance_human_decisions"
down_revision: str | None = "0015_intelligence_judgments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "governance_authority_regimes",
        sa.Column("regime_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("power", sa.String(length=48), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "power = 'human-investment-decision'",
            name=op.f("ck_governance_authority_regimes_r3_human_decision_power"),
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name=op.f("ck_governance_authority_regimes_valid_authority_interval"),
        ),
    )
    op.create_table(
        "authority_regime_corrections",
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operation_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True
        ),
        sa.Column("regime_id", postgresql.UUID(as_uuid=True), nullable=False),
        # duplicate-code: This frozen migration repeats independent authority and target
        # foreign-key DDL; sharing with other revisions or tables would couple their
        # historical schemas.
        # arid: disable
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("draft", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["regime_id"],
            ["governance_authority_regimes.regime_id"],
            ondelete="RESTRICT",
        ),
        # arid: enable
        sa.UniqueConstraint(
            "regime_id", "sequence", name="uq_authority_regime_sequence"
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name=op.f(
                "ck_authority_regime_corrections_positive_authority_regime_sequence"
            ),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(draft) = 'object'",
            name=op.f("ck_authority_regime_corrections_authority_regime_draft_object"),
        ),
    )
    op.create_index(
        "ix_authority_regime_history",
        "authority_regime_corrections",
        ["regime_id", "sequence"],
    )
    op.create_table(
        "human_investment_decisions",
        sa.Column("decision_ref", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operation_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True
        ),
        sa.Column(
            "investment_decision_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("regime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("made_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("choice", sa.String(length=16), nullable=False),
        sa.Column("effect", sa.String(length=32), nullable=False),
        sa.Column("recommendations", postgresql.JSONB(), nullable=False),
        sa.Column("material_rationale", sa.Text()),
        sa.Column("expected_decision_version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["investment_decision_id"],
            ["investment_decisions.decision_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["regime_id"],
            ["governance_authority_regimes.regime_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "choice IN ('increase', 'hold', 'reduce', 'deferral')",
            name=op.f("ck_human_investment_decisions_closed_human_choice"),
        ),
        sa.CheckConstraint(
            "(choice = 'deferral' AND effect = 'deferring') OR "
            "(choice <> 'deferral' AND effect = 'substantively_resolving')",
            name=op.f("ck_human_investment_decisions_human_choice_effect"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(recommendations) = 'array'",
            name=op.f("ck_human_investment_decisions_recommendation_links_array"),
        ),
        sa.CheckConstraint(
            "material_rationale IS NULL OR btrim(material_rationale) <> ''",
            name=op.f("ck_human_investment_decisions_material_rationale_nonempty"),
        ),
        sa.CheckConstraint(
            "expected_decision_version > 0",
            name=op.f("ck_human_investment_decisions_positive_decision_version"),
        ),
    )
    op.create_index(
        "ix_human_decision_history",
        "human_investment_decisions",
        ["investment_decision_id", "recorded_at"],
    )
    op.create_table(
        "human_decision_target_corrections",
        # duplicate-code: A frozen Governance migration must retain its own column
        # definition rather than depend on Intelligence's earlier schema snapshot.
        # arid: disable
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_ref", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("draft", postgresql.JSONB(), nullable=False),
        # arid: enable
        # duplicate-code: Target correction and catalog foreign keys constrain separate
        # frozen tables; keep their local DDL independently reviewable.
        # arid: disable
        sa.ForeignKeyConstraint(
            ["decision_ref"],
            ["human_investment_decisions.decision_ref"],
            ondelete="RESTRICT",
        ),
        # arid: enable
        sa.UniqueConstraint("operation_id"),
        sa.UniqueConstraint(
            "decision_ref", "sequence", name="uq_human_target_sequence"
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name=op.f(
                "ck_human_decision_target_corrections_positive_human_target_sequence"
            ),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(draft) = 'object'",
            name=op.f("ck_human_decision_target_corrections_human_target_draft_object"),
        ),
    )
    op.create_index(
        "ix_human_target_history",
        "human_decision_target_corrections",
        ["decision_ref", "sequence"],
    )
    op.create_table(
        "human_decision_claim_catalogs",
        sa.Column("decision_ref", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_version", sa.Integer(), nullable=False),
        sa.Column(
            "source_act_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("catalog", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("decision_ref", "catalog_version"),
        sa.ForeignKeyConstraint(
            ["decision_ref"],
            ["human_investment_decisions.decision_ref"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "catalog_version > 0",
            name=op.f("ck_human_decision_claim_catalogs_positive_human_claim_version"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(catalog) = 'object'",
            name=op.f("ck_human_decision_claim_catalogs_human_claim_catalog_object"),
        ),
    )
    op.create_table(
        "human_decision_act_publications",
        sa.Column("act_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('root', 'correction', 'regime', 'regime-correction')",
            name=op.f("ck_human_decision_act_publications_human_publication_kind"),
        ),
    )
    op.execute(
        "CREATE FUNCTION polaris_reject_governance_fact_mutation() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ "
        "BEGIN RAISE EXCEPTION 'immutable Governance fact cannot be changed'; END $$"
    )
    # duplicate-code: This immutable trigger list is a frozen migration snapshot;
    # runtime table registration evolves independently.
    # arid: disable
    for table in (
        "governance_authority_regimes",
        "authority_regime_corrections",
        "human_investment_decisions",
        "human_decision_target_corrections",
        "human_decision_claim_catalogs",
        "human_decision_act_publications",
    ):
        # arid: enable
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable "
            f"BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION polaris_reject_governance_fact_mutation()"
        )
    op.execute(
        "DO $$ DECLARE slot_name text := 'polaris_ga_' || "
        "substr(md5(current_database() || ':' || current_schema()), 1, 32); "
        "BEGIN EXECUTE format('CREATE PUBLICATION %I', slot_name); END $$"
    )
    op.execute(
        "CREATE FUNCTION polaris_governance_act_commit_message() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE expected_slot text := 'polaris_ga_' || "
        "substr(md5(current_database() || ':' || TG_TABLE_SCHEMA), 1, 32); "
        "act_id uuid; act_kind text; "
        "BEGIN "
        "IF TG_TABLE_NAME = 'human_investment_decisions' THEN "
        "act_id := NEW.decision_ref; act_kind := 'root'; "
        "ELSIF TG_TABLE_NAME = 'human_decision_target_corrections' THEN "
        "act_id := NEW.correction_id; act_kind := 'correction'; "
        "ELSIF TG_TABLE_NAME = 'governance_authority_regimes' THEN "
        "act_id := NEW.regime_id; act_kind := 'regime'; "
        "ELSE act_id := NEW.correction_id; act_kind := 'regime-correction'; END IF; "
        # duplicate-code: The historical Governance trigger owns its own durable
        # slot check; sharing another migration's PL/pgSQL changes old history.
        # arid: disable
        "IF NOT EXISTS (SELECT 1 FROM pg_replication_slots AS s "
        "WHERE s.slot_name = expected_slot AND s.plugin = 'pgoutput' "
        "AND s.database = current_database() AND NOT s.temporary "
        "AND s.wal_status IN ('reserved', 'extended') "
        "AND s.invalidation_reason IS NULL) THEN "
        # arid: enable
        "RAISE EXCEPTION 'Governance commit slot is unavailable'; "
        "END IF; "
        "PERFORM pg_logical_emit_message(true, expected_slot, "
        "act_kind || ':' || act_id::text); "
        "RETURN NEW; END $$"
    )
    for table in (
        # duplicate-code: Migration trigger inventory and live metadata inventory are
        # separate historical and current representations.
        # arid: disable
        "governance_authority_regimes",
        "authority_regime_corrections",
        "human_investment_decisions",
        "human_decision_target_corrections",
        # arid: enable
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_commit_message "
            f"AFTER INSERT ON {table} FOR EACH ROW "
            "EXECUTE FUNCTION polaris_governance_act_commit_message()"
        )


def downgrade() -> None:
    for table in (
        "human_decision_target_corrections",
        "human_investment_decisions",
        "authority_regime_corrections",
        "governance_authority_regimes",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_commit_message ON {table}")
    op.execute("DROP FUNCTION polaris_governance_act_commit_message()")
    # duplicate-code: This downgrade belongs to a frozen Governance migration;
    # reusing Intelligence's rollback would couple distinct historical revisions.
    # arid: disable
    op.execute(
        "DO $$ DECLARE expected_slot text := 'polaris_ga_' || "
        "substr(md5(current_database() || ':' || current_schema()), 1, 32); "
        "BEGIN IF EXISTS (SELECT 1 FROM pg_replication_slots AS s "
        "WHERE s.slot_name = expected_slot) THEN "
        "PERFORM pg_drop_replication_slot(expected_slot); END IF; END $$"
    )
    op.execute(
        "DO $$ DECLARE slot_name text := 'polaris_ga_' || "
        "substr(md5(current_database() || ':' || current_schema()), 1, 32); "
        "BEGIN EXECUTE format('DROP PUBLICATION %I', slot_name); END $$"
    )
    # arid: enable
    for table in (
        "human_decision_act_publications",
        "human_decision_claim_catalogs",
        # duplicate-code: Rollback ordering and trigger removal are separate migration
        # operations; sharing their table lists would obscure dependency order.
        # arid: disable
        "human_decision_target_corrections",
        "human_investment_decisions",
        "authority_regime_corrections",
        "governance_authority_regimes",
    ):
        # arid: enable
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION polaris_reject_governance_fact_mutation()")
    op.drop_table("human_decision_act_publications")
    op.drop_table("human_decision_claim_catalogs")
    op.drop_index(
        "ix_human_target_history", table_name="human_decision_target_corrections"
    )
    op.drop_table("human_decision_target_corrections")
    op.drop_index("ix_human_decision_history", table_name="human_investment_decisions")
    op.drop_table("human_investment_decisions")
    op.drop_index(
        "ix_authority_regime_history", table_name="authority_regime_corrections"
    )
    op.drop_table("authority_regime_corrections")
    op.drop_table("governance_authority_regimes")
