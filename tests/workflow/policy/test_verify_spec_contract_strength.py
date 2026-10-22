from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VERIFY = (ROOT / ".agents/skills/verify-spec/SKILL.md").read_text(encoding="utf-8")
CLOSURE = (ROOT / ".agents/skills/verify-spec-closure/SKILL.md").read_text(
    encoding="utf-8"
)


def test_verify_spec_rejects_verifier_contract_strengthening() -> None:
    for phrase in (
        "Contract-strength preservation for verifier-owned repairs",
        "inadmissible verifier strengthening",
        "state that the frozen contract explicitly permits",
        "audit verification-owned test/proof repairs",
        "Contract-permitted states rejected by verification-owned tests: 0",
        "finding whose supposed falsifier is still permitted by the frozen contract",
    ):
        assert phrase in VERIFY


def test_closure_requires_forbidden_state_falsifiers() -> None:
    for phrase in (
        "Falsifier admissibility and permitted-state challenge",
        "Presence is not authority",
        "The mere existence of that permitted feature",
        "Contract violation: <exact cell/CCL address + condition violated>",
        "Permitted-state challenge: PASS",
        "A TEST cell is not an independent semantic prohibition",
        "permitted-state challenges failed = 0",
    ):
        assert phrase in CLOSURE


def test_legacy_source_unit_verify_spec_helper_is_removed() -> None:
    scripts = ROOT / ".agents/skills/verify-spec/scripts"
    assert not (scripts / "verify_spec_artifacts.py").exists()
    assert not (scripts / "verify_spec_artifacts_impl.py").exists()
