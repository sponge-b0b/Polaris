from __future__ import annotations

from pathlib import Path


def test_claim_evidence_link_migration_defines_authoritative_tables() -> None:
    source = _migration_source()

    assert 'revision: str = "a65d90e0190"' in source
    assert 'down_revision: str | None = "9d1e2f3a4b5c"' in source
    assert '"report_claim_evidence_links"' in source
    assert '"recommendation_claim_evidence_links"' in source
    assert "ck_report_claim_evidence_links_material_has_support" in source
    assert "ck_recommendation_claim_evidence_links_material_has_support" in source
    assert '"decision_evidence_packets.packet_id"' in source
    assert '"reports.report_id"' in source
    assert '"recommendations.recommendation_id"' in source
    assert "idx_report_claim_evidence_links_report_claim" in source
    assert "idx_recommendation_claim_evidence_links_recommendation_claim" in source


def test_claim_evidence_link_migration_drops_links_before_packets_dependency() -> None:
    source = _migration_source()

    assert 'op.drop_table("recommendation_claim_evidence_links")' in source
    assert 'op.drop_table("report_claim_evidence_links")' in source
    recommendation_drop = source.index(
        'op.drop_table("recommendation_claim_evidence_links")'
    )
    report_drop = source.index('op.drop_table("report_claim_evidence_links")')
    packet_drop = source.index('op.drop_table("decision_evidence_packets")')

    assert recommendation_drop < packet_drop
    assert report_drop < packet_drop


def _migration_source() -> str:
    return Path(
        "migrations/versions/20260725_000001_add_decision_evidence_packets.py"
    ).read_text()
