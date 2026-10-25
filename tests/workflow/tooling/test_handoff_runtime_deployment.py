from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
RUNTIME_RESOLVER = ROOT / ".agents/skills/shared_handoff_runtime.py"
SHARED_GATE = ROOT / "scripts/workflow_handoff.py"
REVIEW_FINALIZER = ROOT / ".agents/skills/review-spec/scripts/review_spec_handoff.py"
VERIFY_FINALIZER = ROOT / ".agents/skills/verify-spec/scripts/verify_spec_handoff.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolver = _load("shared_handoff_runtime", RUNTIME_RESOLVER)
shared = _load("workflow_handoff_contract", SHARED_GATE)


def test_shared_handoff_runtime_has_versioned_contract() -> None:
    assert shared.RUNTIME_CONTRACT == "polaris.workflow-handoff-runtime/v2"
    assert resolver.REQUIRED_RUNTIME_CONTRACT == shared.RUNTIME_CONTRACT


def test_shared_handoff_contract_cli_is_exact() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.workflow_handoff", "contract"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stdout.strip() == (
        "WORKFLOW HANDOFF RUNTIME: polaris.workflow-handoff-runtime/v2"
    )


def test_resolver_uses_local_runtime_when_contract_is_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "output.txt"
    manifest.write_text("{}", encoding="utf-8")
    called: list[Path] = []

    monkeypatch.setattr(resolver, "_require_contract", lambda root: None)
    monkeypatch.setattr(
        resolver,
        "_fetch_default",
        lambda root: pytest.fail("current local runtime must not fetch default"),
    )

    def fake_finalize(runtime_root: Path, manifest_path: Path, output_path: Path) -> str:
        called.append(runtime_root)
        output_path.write_text("ok\n", encoding="utf-8")
        return resolver.VALID

    monkeypatch.setattr(resolver, "_finalize_with_runtime", fake_finalize)
    assert resolver.finalize(manifest, output, repo_root=repo) == resolver.VALID
    assert called == [repo.resolve()]


def test_resolver_falls_back_to_current_default_when_local_contract_is_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "output.txt"
    manifest.write_text("{}", encoding="utf-8")
    fetched: list[Path] = []
    finalized: list[Path] = []

    def fake_require(runtime_root: Path) -> None:
        if runtime_root == repo.resolve():
            raise resolver.HandoffRuntimeError("legacy runtime")

    monkeypatch.setattr(resolver, "_require_contract", fake_require)
    monkeypatch.setattr(resolver, "_fetch_default", lambda root: fetched.append(root))
    monkeypatch.setattr(
        resolver,
        "_materialize_default_runtime",
        lambda root, target: (target / "scripts").mkdir(parents=True),
    )

    def fake_finalize(runtime_root: Path, manifest_path: Path, output_path: Path) -> str:
        finalized.append(runtime_root)
        output_path.write_text("ok\n", encoding="utf-8")
        return resolver.VALID

    monkeypatch.setattr(resolver, "_finalize_with_runtime", fake_finalize)
    assert resolver.finalize(manifest, output, repo_root=repo) == resolver.VALID
    assert fetched == [repo.resolve()]
    assert len(finalized) == 1
    assert finalized[0] != repo.resolve()


def test_lifecycle_finalizers_use_shared_runtime_resolver() -> None:
    for path in (REVIEW_FINALIZER, VERIFY_FINALIZER):
        text = path.read_text(encoding="utf-8")
        assert ".agents/skills/shared_handoff_runtime.py" in text
        assert "scripts/workflow_handoff.py" not in text
