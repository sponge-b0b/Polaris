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


def manifest() -> dict[str, object]:
    return {
        "schema": journal.START_SCHEMA,
        "skill": "implement-ticket",
        "repository": {"identity": "sponge-b0b/Polaris"},
        "subject": {
            "kind": "github-issue",
            "number": 407,
            "url": "https://github.com/sponge-b0b/Polaris/issues/407",
        },
        "lifecycle_scope": {
            "kind": "github-issue",
            "number": 359,
            "url": "https://github.com/sponge-b0b/Polaris/issues/359",
        },
    }


def test_cli_operational_degradation_is_exit_zero(tmp_path: Path) -> None:
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
        capture_output=True,
    )

    assert result.returncode == 0
    assert "WORKFLOW JOURNAL: DEGRADED" in result.stdout
    assert "Fallback: workflow execution remains authoritative" in result.stdout


def test_cli_malformed_manifest_degrades_without_stopping(
    repo: Path,
    tmp_path: Path,
) -> None:
    source = tmp_path / "bad.json"
    source.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "start", "--manifest", str(source)],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert "WORKFLOW JOURNAL: DEGRADED" in result.stdout


def test_unsupported_metadata_schema_is_not_reused(repo: Path) -> None:
    loaded = journal.start_invocation(manifest(), cwd=repo)
    metadata_path = loaded.path / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["schema"] = "polaris.workflow-invocation/v999"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    result = journal.locate_resumable(
        skill="implement-ticket",
        repository="sponge-b0b/Polaris",
        subject_url="https://github.com/sponge-b0b/Polaris/issues/407",
        cwd=repo,
    )

    assert result.status is journal.LocateStatus.DEGRADED
    assert result.matches == ()


def test_gc_failure_is_reported_without_becoming_workflow_failure(
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
