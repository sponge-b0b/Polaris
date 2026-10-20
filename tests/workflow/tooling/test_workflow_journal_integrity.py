from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import workflow_journal as journal


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/workflow_journal.py"


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    (path / "README.md").write_text("x\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "init")
    return path


def manifest(number: int = 407) -> dict[str, object]:
    return {
        "schema": journal.START_SCHEMA,
        "skill": "implement-ticket",
        "repository": {"identity": "sponge-b0b/Polaris"},
        "subject": {
            "kind": "github-issue",
            "number": number,
            "url": f"https://github.com/sponge-b0b/Polaris/issues/{number}",
        },
        "lifecycle_scope": {
            "kind": "github-issue",
            "number": 359,
            "url": "https://github.com/sponge-b0b/Polaris/issues/359",
        },
    }


def test_empty_events_file_is_degraded(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    (loaded.path / "events.jsonl").write_bytes(b"")

    reread = journal.load_invocation(loaded.path)

    assert reread.health is journal.JournalHealth.DEGRADED
    assert reread.events == ()
    assert reread.reason == "missing invocation_started event"


def test_event_after_terminal_uses_only_terminal_prefix(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    loaded = journal.append_event(
        loaded.path,
        {
            "type": "invocation_completed",
            "candidate_state": None,
            "data": {"outcome": "success"},
        },
        cwd=repo,
    )
    event = {
        "schema": journal.EVENT_SCHEMA,
        "sequence": 3,
        "event_id": "f" * 32,
        "recorded_at": "2026-10-20T00:00:00Z",
        "invocation_id": loaded.metadata["invocation_id"],
        "type": "work_completed",
        "candidate_state": None,
        "data": {"work_id": "illegal-after-terminal"},
        "previous_event_sha256": loaded.events[-1]["event_sha256"],
    }
    event["event_sha256"] = journal._event_hash(event)
    with (loaded.path / "events.jsonl").open("ab") as handle:
        handle.write(journal._canonical(event) + b"\n")

    reread = journal.load_invocation(loaded.path)

    assert reread.health is journal.JournalHealth.DEGRADED
    assert len(reread.events) == 2
    assert "event follows terminal event" in (reread.reason or "")


def test_unreadable_sibling_disables_automatic_reuse(repo: Path) -> None:
    good = journal.start_invocation(manifest(), cwd=repo)
    unreadable = journal.start_invocation(manifest(408), cwd=repo)
    (unreadable.path / "metadata.json").write_text("{bad", encoding="utf-8")

    result = journal.locate_resumable(
        skill="implement-ticket",
        repository="sponge-b0b/Polaris",
        subject_url="https://github.com/sponge-b0b/Polaris/issues/407",
        cwd=repo,
    )

    assert result.status is journal.LocateStatus.DEGRADED
    assert result.matches == ()
    assert "automatic reuse skipped" in (result.reason or "")
    assert good.path.exists()


def test_directory_metadata_identity_mismatch_is_unusable(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    moved = loaded.path.parent / "wrong-name"
    loaded.path.rename(moved)

    with pytest.raises(journal.JournalError, match="directory does not match invocation_id"):
        journal.load_invocation(moved)


def test_cli_operational_degradation_is_exit_zero_outside_git(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "locate",
            "--skill",
            "implement-ticket",
            "--repository",
            "sponge-b0b/Polaris",
            "--subject-url",
            "https://github.com/sponge-b0b/Polaris/issues/407",
        ],
        cwd=tmp_path,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert "WORKFLOW JOURNAL: DEGRADED" in result.stdout
    assert "Fallback: workflow execution remains authoritative" in result.stdout


def test_gc_failure_is_nonthrowing(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    journal.start_invocation(manifest(), cwd=repo)

    def fail_remove(_path: Path) -> None:
        raise OSError("simulated permission failure")

    monkeypatch.setattr(journal.shutil, "rmtree", fail_remove)
    result = journal.gc_lifecycle_scope(
        "https://github.com/sponge-b0b/Polaris/issues/359",
        cwd=repo,
    )

    assert result.matched == 1
    assert result.removed == 0
    assert result.failed == 1
    assert "simulated permission failure" in result.failures[0]
