from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TO_TICKETS = ROOT / ".agents/skills/to-tickets/SKILL.md"
IMPLEMENT = ROOT / ".agents/skills/implement-ticket/SKILL.md"
RECOVERY = ROOT / ".agents/skills/to-tickets/TICKET_RESLICE_RECOVERY.md"
SCRIPT = ROOT / "scripts/workflow_reslice_recovery.py"


def test_shared_reslice_contract_is_composed_by_both_workflows() -> None:
    for path in (TO_TICKETS, IMPLEMENT):
        text = path.read_text(encoding="utf-8")
        assert "TICKET_RESLICE_RECOVERY.md" in text
        assert "scripts.workflow_reslice_recovery validate" in text


def test_recovery_contract_covers_all_execution_modes() -> None:
    text = RECOVERY.read_text(encoding="utf-8")
    for phrase in (
        "### Source-first",
        "### Destination-first",
        "### Destination-only after Source retirement",
        "pending-prerequisite",
        "source-complete",
        "prerequisite-complete",
        "pending-source-retirement",
        "source-retired",
        "source-reconciled",
        "Source disposition",
        "destination-only",
        "Source completion commit:** Not applicable",
    ):
        assert phrase in text


def test_machine_validator_exists() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "TICKET RESLICE RECOVERY: VALID" in text
    assert "Execution order contradicts Native execution order" in text
    assert "source-complete is valid only for source-first recovery" in text
    assert "prerequisite-complete is valid only for destination-first recovery" in text
    assert "retired-source Execution order must be destination-only" in text
    assert "Source completion commit" in text
    assert '"Not applicable"' in text
