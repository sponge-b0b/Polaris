from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import workflow_journal as journal


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
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


def manifest(number: int = 407, scope: int = 359) -> dict[str, object]:
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
            "number": scope,
            "url": f"https://github.com/sponge-b0b/Polaris/issues/{scope}",
        },
    }


def locate(repo: Path) -> journal.LocateResult:
    return journal.locate_resumable(
        skill="implement-ticket",
        repository="sponge-b0b/Polaris",
        subject_url="https://github.com/sponge-b0b/Polaris/issues/407",
        cwd=repo,
    )


def test_start_is_git_admin_only(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)

    assert loaded.health is journal.JournalHealth.HEALTHY
    assert len(loaded.events) == 1
    assert loaded.events[0]["type"] == "invocation_started"
    assert git(repo, "status", "--porcelain") == ""
    git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir"))
    assert loaded.path.is_relative_to(git_dir)


def test_normal_branch_switch_keeps_same_root(repo: Path) -> None:
    first = journal.journal_root(repo)
    git(repo, "switch", "-c", "spec-359")
    assert journal.journal_root(repo) == first


def test_linked_worktree_gets_isolated_root(repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    git(repo, "worktree", "add", "--detach", str(worktree))

    assert journal.journal_root(repo) != journal.journal_root(worktree)
    first = journal.start_invocation(manifest(407), cwd=repo)
    second = journal.start_invocation(manifest(408), cwd=worktree)
    assert first.path != second.path
    assert second.metadata["checkout"]["initial_branch"] is None


def test_append_hash_chain_and_partial_tail_use_valid_prefix(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    loaded = journal.append_event(
        loaded.path,
        {
            "type": "check_result",
            "candidate_state": "a" * 64,
            "data": {"check_id": "mypy", "result": "pass"},
        },
        cwd=repo,
    )

    assert loaded.events[1]["previous_event_sha256"] == loaded.events[0]["event_sha256"]
    with (loaded.path / "events.jsonl").open("ab") as handle:
        handle.write(b'{"schema":"broken"')

    degraded = journal.load_invocation(loaded.path)
    assert degraded.health is journal.JournalHealth.DEGRADED
    assert len(degraded.events) == 2
    assert degraded.reason == "partial final event ignored"

    with pytest.raises(journal.JournalError, match="journal is degraded"):
        journal.append_event(
            loaded.path,
            {
                "type": "work_completed",
                "candidate_state": None,
                "data": {"work_id": "x"},
            },
            cwd=repo,
        )


def test_interior_hash_corruption_uses_only_prior_prefix(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    loaded = journal.append_event(
        loaded.path,
        {
            "type": "work_completed",
            "candidate_state": None,
            "data": {"work_id": "one"},
        },
        cwd=repo,
    )
    path = loaded.path / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    second = json.loads(lines[1])
    second["data"]["work_id"] = "tampered"
    lines[1] = json.dumps(second, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    degraded = journal.load_invocation(loaded.path)
    assert degraded.health is journal.JournalHealth.DEGRADED
    assert len(degraded.events) == 1
    assert degraded.reason is not None
    assert "hash mismatch" in degraded.reason


def test_locate_none_found_ambiguous_and_terminal(repo: Path) -> None:
    assert locate(repo).status is journal.LocateStatus.NONE

    first = journal.start_invocation(manifest(), cwd=repo)
    assert locate(repo).status is journal.LocateStatus.FOUND

    second = journal.start_invocation(manifest(), cwd=repo)
    assert locate(repo).status is journal.LocateStatus.AMBIGUOUS

    journal.append_event(
        first.path,
        {
            "type": "invocation_abandoned",
            "candidate_state": None,
            "data": {"reason": "superseded"},
        },
        cwd=repo,
    )
    found = locate(repo)
    assert found.status is journal.LocateStatus.FOUND
    assert found.matches[0].path == second.path


def test_secret_bearing_event_is_rejected_without_mutating_journal(
    repo: Path,
) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    before = (loaded.path / "events.jsonl").read_bytes()

    with pytest.raises(journal.JournalError, match="secret-bearing"):
        journal.append_event(
            loaded.path,
            {
                "type": "work_completed",
                "candidate_state": None,
                "data": {"api_token": "not-even-a-real-token"},
            },
            cwd=repo,
        )

    assert (loaded.path / "events.jsonl").read_bytes() == before


def test_gc_exact_lifecycle_scope_across_worktrees(
    repo: Path,
    tmp_path: Path,
) -> None:
    worktree = tmp_path / "worktree"
    git(repo, "worktree", "add", "--detach", str(worktree))
    first = journal.start_invocation(manifest(407, 359), cwd=repo)
    second = journal.start_invocation(manifest(408, 359), cwd=worktree)
    unrelated = journal.start_invocation(manifest(500, 499), cwd=repo)

    result = journal.gc_lifecycle_scope(
        "https://github.com/sponge-b0b/Polaris/issues/359",
        cwd=repo,
    )

    assert result.matched == 2
    assert result.removed == 2
    assert result.failed == 0
    assert not first.path.exists()
    assert not second.path.exists()
    assert unrelated.path.exists()


def test_delete_all_wij_files_degrades_to_current_none_behavior(repo: Path) -> None:
    journal.start_invocation(manifest(), cwd=repo)
    shutil.rmtree(journal.journal_root(repo))
    assert locate(repo).status is journal.LocateStatus.NONE
