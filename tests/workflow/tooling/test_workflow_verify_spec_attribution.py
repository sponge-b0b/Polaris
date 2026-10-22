from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[3] / "scripts/workflow_verify_spec_attribution.py"
)
spec = importlib.util.spec_from_file_location(
    "workflow_verify_spec_attribution", MODULE_PATH
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def test_default_equivalent_branch_changes_are_not_candidate_attributable(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    _write(repo, "src/product.py", "VALUE = 1\n")
    _write(repo, "scripts/workflow_tool.py", "VALUE = 'old'\n")
    _write(repo, "tests/workflow/test_tool.py", "VALUE = 'old'\n")
    baseline = _commit(repo, "baseline")

    _write(repo, "scripts/workflow_tool.py", "VALUE = 'current'\n")
    _write(repo, "tests/workflow/test_tool.py", "VALUE = 'current'\n")
    policy_commit = _commit(repo, "workflow update")
    default_head = _git(repo, "rev-parse", "HEAD")

    # Model a long-lived Spec branch that diverged before absorbing the exact
    # current default-branch workflow bytes. The product commit first ensures
    # the cherry-pick is not identical to the original default-branch commit.
    _git(repo, "switch", "-c", "spec-1", baseline)
    _write(repo, "src/product.py", "VALUE = 2\n")
    _commit(repo, "spec product change")
    _git(repo, "cherry-pick", policy_commit)

    manifest = module.build_manifest(repo, default_head, "HEAD")

    assert manifest["candidate_attributable_paths"] == ["src/product.py"]
    assert manifest["inherited_default_equivalent_paths"] == [
        "scripts/workflow_tool.py",
        "tests/workflow/test_tool.py",
    ]

    _write(repo, "scripts/workflow_tool.py", "VALUE = 'spec-only'\n")
    _commit(repo, "spec workflow divergence")
    manifest = module.build_manifest(repo, default_head, "HEAD")

    assert manifest["candidate_attributable_paths"] == [
        "scripts/workflow_tool.py",
        "src/product.py",
    ]
    assert manifest["inherited_default_equivalent_paths"] == [
        "tests/workflow/test_tool.py"
    ]


def test_default_equivalent_deletion_is_inherited(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")

    _write(repo, "src/product.py", "VALUE = 1\n")
    _write(repo, "scripts/retired_workflow_tool.py", "VALUE = 'old'\n")
    baseline = _commit(repo, "baseline")

    _git(repo, "rm", "scripts/retired_workflow_tool.py")
    policy_commit = _commit(repo, "remove workflow tool")
    default_head = _git(repo, "rev-parse", "HEAD")

    _git(repo, "switch", "-c", "spec-1", baseline)
    _write(repo, "src/product.py", "VALUE = 2\n")
    _commit(repo, "spec product change")
    _git(repo, "cherry-pick", policy_commit)

    manifest = module.build_manifest(repo, default_head, "HEAD")

    assert manifest["candidate_attributable_paths"] == ["src/product.py"]
    assert manifest["inherited_default_equivalent_paths"] == [
        "scripts/retired_workflow_tool.py"
    ]
