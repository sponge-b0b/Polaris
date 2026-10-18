from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.workflow_candidate_guard import (  # noqa: E402
    CandidateGuardError,
    protected_candidate_paths,
    restore_protected,
    validate_candidate,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def _setup_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-b", "main"],
        check=True,
        capture_output=True,
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    files = {
        "src/product.py": "VALUE = 1\n",
        ".agents/skills/example/SKILL.md": "base\n",
        "scripts/workflow_attention.py": "base\n",
        "scripts/project_delivery.py": "base\n",
        "tests/workflow/test_example.py": "base\n",
        "contracts/ccl/example.json": "{}\n",
        "docs/adr/0001-example.md": "base\n",
        "docs/process/example.md": "base\n",
        "AGENTS.md": "base\n",
    }
    for relative, content in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


class _Chdir:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous: Path | None = None

    def __enter__(self) -> None:
        self.previous = Path.cwd()
        import os

        os.chdir(self.path)

    def __exit__(self, *_: object) -> None:
        assert self.previous is not None
        import os

        os.chdir(self.previous)


def test_product_candidate_is_admissible(tmp_path: Path) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / "src/product.py").write_text("VALUE = 2\n", encoding="utf-8")

    with _Chdir(repo):
        paths = validate_candidate(anchor)

    assert paths == ("src/product.py",)


@pytest.mark.parametrize(
    "relative",
    [
        ".agents/skills/example/SKILL.md",
        "scripts/workflow_attention.py",
        "scripts/project_delivery.py",
        "tests/workflow/test_example.py",
        "contracts/ccl/example.json",
        "docs/adr/0001-example.md",
        "docs/process/example.md",
        "AGENTS.md",
    ],
)
def test_protected_control_plane_change_is_rejected(
    tmp_path: Path, relative: str
) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / relative).write_text("changed\n", encoding="utf-8")

    with _Chdir(repo), pytest.raises(
        CandidateGuardError,
        match="protected workflow/control-plane path",
    ):
        validate_candidate(anchor)


def test_untracked_protected_file_is_rejected_and_restorable(tmp_path: Path) -> None:
    repo, anchor = _setup_repo(tmp_path)
    path = repo / ".agents/skills/example/NEW.md"
    path.write_text("unauthorized\n", encoding="utf-8")

    with _Chdir(repo):
        assert protected_candidate_paths(anchor)
        restored = restore_protected(anchor)
        validate_candidate(anchor)

    assert restored == (".agents/skills/example/NEW.md",)
    assert not path.exists()


def test_restore_protected_preserves_product_candidate(tmp_path: Path) -> None:
    repo, anchor = _setup_repo(tmp_path)
    product = repo / "src/product.py"
    protected = repo / "scripts/workflow_attention.py"
    product.write_text("VALUE = 2\n", encoding="utf-8")
    protected.write_text("unauthorized\n", encoding="utf-8")

    with _Chdir(repo):
        restored = restore_protected(anchor)
        paths = validate_candidate(anchor)

    assert restored == ("scripts/workflow_attention.py",)
    assert protected.read_text(encoding="utf-8") == "base\n"
    assert product.read_text(encoding="utf-8") == "VALUE = 2\n"
    assert paths == ("src/product.py",)


def test_cli_reports_valid_candidate(tmp_path: Path) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / "src/product.py").write_text("VALUE = 2\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/workflow_candidate_guard.py"),
            "check",
            "--anchor",
            anchor,
        ],
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines()[0] == "WORKFLOW CANDIDATE GUARD: VALID"
    assert "Protected control-plane paths: 0" in completed.stdout
