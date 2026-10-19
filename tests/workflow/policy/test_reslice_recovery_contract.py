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


def test_recovery_contract_covers_both_execution_orders() -> None:
    text = RECOVERY.read_text(encoding="utf-8")
    for phrase in (
        "### Source-first",
        "### Destination-first",
        "pending-prerequisite",
        "source-complete",
        "prerequisite-complete",
        "source-reconciled",
        "second participating closer terminalizes",
    ):
        assert phrase in text


def test_machine_validator_exists() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "TICKET RESLICE RECOVERY: VALID" in text
    assert "Execution order contradicts Native execution order" in text
    assert "source-complete is valid only for source-first recovery" in text
    assert "prerequisite-complete is valid only for destination-first recovery" in text
