from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".agents/skills/implement-ticket/scripts/attention_gate.py"
SPEC = importlib.util.spec_from_file_location("implement_ticket_attention_guarded", SCRIPT)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        text=True,
    ).strip()


def _setup_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "-C", str(repo), "init", "-b", "spec-1"],
        check=True,
        capture_output=True,
    )
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    protected = repo / ".agents/skills/example/SKILL.md"
    protected.parent.mkdir(parents=True)
    protected.write_text("base\n", encoding="utf-8")
    product = repo / "src/product.py"
    product.parent.mkdir(parents=True)
    product.write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


class _Chdir:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous: str | None = None

    def __enter__(self) -> None:
        self.previous = os.getcwd()
        os.chdir(self.path)

    def __exit__(self, *_: object) -> None:
        assert self.previous is not None
        os.chdir(self.previous)


def test_preclosure_machine_gate_rejects_protected_candidate(
    tmp_path: Path,
) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / ".agents/skills/example/SKILL.md").write_text(
        "unauthorized\n", encoding="utf-8"
    )
    args = argparse.Namespace(execution_anchor=anchor)

    with _Chdir(repo), pytest.raises(
        GATE.AttentionGateError,
        match="protected workflow/control-plane path",
    ):
        GATE.record_pre_closure(args)


def test_preclosure_wrapper_allows_product_candidate_to_reach_retained_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, anchor = _setup_repo(tmp_path)
    (repo / "src/product.py").write_text("VALUE = 2\n", encoding="utf-8")
    sentinel = {"ok": True}
    monkeypatch.setattr(GATE, "_original_record_pre_closure", lambda _args: sentinel)
    args = argparse.Namespace(execution_anchor=anchor)

    with _Chdir(repo):
        assert GATE.record_pre_closure(args) is sentinel
