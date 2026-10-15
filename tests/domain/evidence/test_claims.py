from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.domain.evidence import (
    ClaimCatalog,
    ClaimCatalogVersion,
    ClaimId,
    InvalidClaimCatalog,
    InvalidClaimCatalogHistory,
    InvestmentRecommendationRef,
)

TARGET_ID = UUID("00000000-0000-4000-8000-000000000401")
NEW_TARGET_ID = UUID("00000000-0000-4000-8000-000000000402")
CLAIM_ID = UUID("00000000-0000-4000-8000-000000000403")
SECOND_CLAIM_ID = UUID("00000000-0000-4000-8000-000000000404")
THIRD_CLAIM_ID = UUID("00000000-0000-4000-8000-000000000405")
EFFECTIVE_AT = datetime(2026, 9, 1, tzinfo=UTC)
RECORDED_AT = datetime(2026, 9, 2, tzinfo=UTC)


def _formed() -> ClaimCatalog:
    return ClaimCatalog.form(
        InvestmentRecommendationRef(TARGET_ID),
        (ClaimId(CLAIM_ID),),
        effective_at=EFFECTIVE_AT,
        recorded_at=RECORDED_AT,
    )


def _corrected() -> ClaimCatalog:
    return _formed().correct_same_proposition(
        ClaimId(CLAIM_ID),
        effective_at=EFFECTIVE_AT,
        recorded_at=RECORDED_AT + timedelta(days=1),
    )


def test_formation_starts_complete_catalog_at_version_one() -> None:
    catalog = _formed()

    assert catalog.current.version == ClaimCatalogVersion(1)
    assert catalog.current.claim_ids == frozenset({ClaimId(CLAIM_ID)})


def test_same_proposition_correction_retains_identity_and_advances_version() -> None:
    catalog = _corrected()

    assert catalog.current.version == ClaimCatalogVersion(2)
    assert catalog.current.claim_ids == frozenset({ClaimId(CLAIM_ID)})


def test_reconstructed_history_rejects_revisions_out_of_version_order() -> None:
    catalog = _corrected()

    with pytest.raises(InvalidClaimCatalogHistory, match="ordered by version"):
        ClaimCatalog(tuple(reversed(catalog.revisions)))

    advanced = catalog.correct_same_proposition(
        ClaimId(CLAIM_ID),
        effective_at=EFFECTIVE_AT,
        recorded_at=RECORDED_AT + timedelta(days=2),
    )
    assert advanced.current.version == ClaimCatalogVersion(3)


def test_material_proposition_change_requires_fresh_identity() -> None:
    catalog = _formed().replace_material_proposition(
        ClaimId(CLAIM_ID),
        ClaimId(SECOND_CLAIM_ID),
        effective_at=EFFECTIVE_AT + timedelta(days=1),
        recorded_at=RECORDED_AT + timedelta(days=1),
    )

    assert catalog.current.version == ClaimCatalogVersion(2)
    assert catalog.current.claim_ids == frozenset({ClaimId(SECOND_CLAIM_ID)})
    assert ClaimId(CLAIM_ID) in catalog.revisions[0].claim_ids

    with pytest.raises(InvalidClaimCatalog, match="fresh ClaimId"):
        catalog.replace_material_proposition(
            ClaimId(SECOND_CLAIM_ID),
            ClaimId(CLAIM_ID),
            effective_at=EFFECTIVE_AT + timedelta(days=2),
            recorded_at=RECORDED_AT + timedelta(days=2),
        )


def test_new_target_root_starts_at_one_and_cannot_reuse_claim_identity() -> None:
    catalog = _formed()

    new_root = catalog.start_new_root(
        InvestmentRecommendationRef(NEW_TARGET_ID),
        (ClaimId(THIRD_CLAIM_ID),),
        effective_at=EFFECTIVE_AT + timedelta(days=1),
        recorded_at=RECORDED_AT + timedelta(days=1),
    )
    assert new_root.current.version == ClaimCatalogVersion(1)
    assert new_root.current.claim_ids == frozenset({ClaimId(THIRD_CLAIM_ID)})

    with pytest.raises(InvalidClaimCatalog, match="fresh ClaimId"):
        catalog.start_new_root(
            InvestmentRecommendationRef(NEW_TARGET_ID),
            (ClaimId(CLAIM_ID),),
            effective_at=EFFECTIVE_AT + timedelta(days=1),
            recorded_at=RECORDED_AT + timedelta(days=1),
        )


def test_retraction_removes_current_membership_without_deleting_history() -> None:
    catalog = _formed().retract_claim(
        ClaimId(CLAIM_ID),
        effective_at=EFFECTIVE_AT + timedelta(days=2),
        recorded_at=RECORDED_AT + timedelta(days=2),
    )

    assert catalog.current.version == ClaimCatalogVersion(2)
    assert not catalog.current.claim_ids
    assert ClaimId(CLAIM_ID) in catalog.revisions[0].claim_ids
