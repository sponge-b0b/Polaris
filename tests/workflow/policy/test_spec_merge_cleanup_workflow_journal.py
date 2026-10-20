from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / ".agents/skills/spec-merge-cleanup/SKILL.md"


def test_spec_merge_cleanup_owns_final_best_effort_journal_gc() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert "Final best-effort Workflow Invocation Journal GC" in text
    assert "python -m scripts.workflow_journal gc" in text
    assert "--lifecycle-scope-url <canonical Spec issue URL>" in text
    assert "WORKFLOW JOURNAL GC: DEGRADED" in text
    assert "Do not roll back authoritative Spec completion" in text
    assert "WIJ garbage collection is best-effort housekeeping" in text
    assert "not a success criterion" in text
    assert text.index("Reconstruct Project projection once") < text.index(
        "Final best-effort Workflow Invocation Journal GC"
    )
