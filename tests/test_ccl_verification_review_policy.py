from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFY = (ROOT / ".agents/skills/verify-spec/SKILL.md").read_text(encoding="utf-8")
CLOSURE = (ROOT / ".agents/skills/verify-spec-closure/SKILL.md").read_text(encoding="utf-8")
REVIEW = (ROOT / ".agents/skills/review-spec/SKILL.md").read_text(encoding="utf-8")


def test_verification_consumes_finite_contract_cells() -> None:
    for text in (VERIFY, CLOSURE, REVIEW):
        for token in ("OBL-*", "IMP-*", "TEST-*", "EXC-*"):
            assert token in text
        assert "Source Unit Inventory" not in text or "Do not" in text
        assert "ARCHSRC-*" not in text or "Do not" in text


def test_verify_parent_requires_deterministic_contract_and_v2_coverage() -> None:
    assert "python -m scripts.spec_contract build" in VERIFY
    assert "python -m scripts.spec_contract check-coverage" in VERIFY
    assert "Semantic prose classification performed: 0" in VERIFY
    assert "ticket-coverage-manifest:v2" in VERIFY


def test_independent_closure_cannot_redefine_contract() -> None:
    assert "Do not:" in CLOSURE
    assert "add/remove a cell" in CLOSURE
    assert "contract-gap candidate" in CLOSURE
    assert "SPEC CLOSURE: PASS" in CLOSURE
    assert "SPEC CLOSURE: FAIL" in CLOSURE


def test_review_preserves_three_axes_and_exit_receipt() -> None:
    for heading in ("## Standards", "## Spec", "## Architecture"):
        assert heading in REVIEW
    assert "<!-- review-spec-finding-ledger:v1 -->" in REVIEW
    assert "## Spec Review Exit Receipt" in REVIEW
    assert "**Unresolved decomposition defects:** 0" in REVIEW
    assert "**Review coverage:** complete" in REVIEW


def test_review_routes_gaps_upstream_instead_of_inventing_obligations() -> None:
    assert "contract-authority-gap" in REVIEW
    assert "planning-cell-gap" in REVIEW
    assert "Do not create `ARCHSRC-*`" in REVIEW
    assert "does not:" in REVIEW
