from pathlib import Path

from scripts.spec_contract import build_contract

ROOT = Path(__file__).resolve().parents[3]

LIFECYCLE_FILES = [
    ROOT / "AGENTS.md",
    ROOT / ".agents/skills/README.md",
    ROOT / ".agents/skills/architecture-remediation/SKILL.md",
    ROOT / ".agents/skills/contract-ledger/SKILL.md",
    ROOT / ".agents/skills/implement-ticket/SKILL.md",
    ROOT / ".agents/skills/project-delivery-management/SKILL.md",
    ROOT / ".agents/skills/project-tracking/SKILL.md",
    ROOT / ".agents/skills/project-tracking/WIRING.md",
    ROOT / ".agents/skills/review-spec/SKILL.md",
    ROOT / ".agents/skills/spec-contract/SKILL.md",
    ROOT / ".agents/skills/spec-merge-cleanup/SKILL.md",
    ROOT / ".agents/skills/to-adr-doc/SKILL.md",
    ROOT / ".agents/skills/to-specs/SKILL.md",
    ROOT / ".agents/skills/to-tickets/SKILL.md",
    ROOT / ".agents/skills/verify-ticket-closure/SKILL.md",
    ROOT / ".agents/skills/wayfinder/SKILL.md",
]

FORBIDDEN_TRANSITION_PHRASES = [
    "$to-remediation-specs",
    "Legacy Spec migration",
    "Legacy Decision Compatibility",
    "staged migration",
    "not-yet-migrated",
    "Legacy checkpoint migration",
    "legacy ordinary tickets",
    "migration input only",
    "temporary compatibility",
    "Existing v2/root checkpoints are compatibility history",
    "historical Root Blocker",
    "legacy Root Blocker",
    (
        "compatibility projections for existing verification/review consumers "
        "during migration"
    ),
    "Bootstrap/migration",
    "pre-bootstrap",
    "bootstrap activation",
    "Awaiting Root Verification",
]


def _sample_spec() -> str:
    manifest = (
        '{"schema":"polaris.spec-ccl/v1","obligations":['
        '{"obligation_id":"OBL-001","source_ref":"Decision #1",'
        '"ccl":["demo.contract@1#behavior"]}]}'
    )
    return f'''<!-- spec-contract-ccl:v1
{manifest}
-->

## Canonical Contract Obligations
Generated projection.

## Implementation Decisions
- `IMP-001` — Use the existing repository boundary.

## Testing Decisions
- `TEST-001` — Prove the public behavior through an executable test.

## Out of Scope
- `EXC-001` — Do not redesign unrelated storage.
'''


def test_transition_adapters_are_not_permanent_skills() -> None:
    skill = ROOT / ".agents/skills/to-remediation-specs/SKILL.md"
    metadata = ROOT / ".agents/skills/to-remediation-specs/agents/openai.yaml"
    assert not skill.exists()
    assert not metadata.exists()


def test_lifecycle_skills_have_no_known_migration_only_handlers() -> None:
    for path in LIFECYCLE_FILES:
        text = path.read_text(encoding="utf-8")
        for phrase in FORBIDDEN_TRANSITION_PHRASES:
            assert phrase not in text, (
                f"{path}: transition-only phrase remains: {phrase}"
            )


def test_governance_requires_out_of_band_repository_transition_work() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme = (ROOT / ".agents/skills/README.md").read_text(encoding="utf-8")
    assert "Permanent Workflow / Out-of-Band Transition Rule" in agents
    assert "out of band" in agents
    assert "Do not embed one-time repository transition procedures" in readme


def test_spec_contract_emits_current_schema_only() -> None:
    contract = build_contract(_sample_spec())
    assert set(contract) == {
        "schema",
        "spec_body_hash",
        "spec_contract_hash",
        "cells",
    }
    assert contract["schema"] == "polaris.spec-contract/v1"
    assert [cell["cell"] for cell in contract["cells"]] == [
        "OBL-001",
        "IMP-001",
        "TEST-001",
        "EXC-001",
    ]


def test_architecture_remediation_routes_to_canonical_semantic_owners() -> None:
    path = ROOT / ".agents/skills/architecture-remediation/SKILL.md"
    text = path.read_text(encoding="utf-8")
    assert "$contract-ledger existing-authority" in text
    assert "$contract-ledger owner-decision" in text
    assert "$wayfinder" in text
    assert "does not conduct a parallel owner-decision protocol" in text


def test_current_reconciliation_is_general_not_migration_specific() -> None:
    root = ROOT / ".agents/skills/to-specs"
    entrypoint = (root / "SKILL.md").read_text(encoding="utf-8")
    procedure = (root / "PROCEDURE.md").read_text(encoding="utf-8")

    assert "`.agents/skills/to-specs/PROCEDURE.md`" in entrypoint
    assert "## Permanent reconciliation rule" in procedure
    assert "existing open Spec" in procedure
    for text in (entrypoint, procedure):
        assert "Legacy Spec migration" not in text
        assert "$to-remediation-specs" not in text
