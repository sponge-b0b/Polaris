from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FINALIZER = ROOT / ".agents/skills/verify-spec/scripts/verify_spec_handoff.py"
SHARED = ROOT / "scripts/workflow_handoff.py"

spec = importlib.util.spec_from_file_location("workflow_handoff", SHARED)
assert spec is not None and spec.loader is not None
workflow_handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow_handoff)


def _manifest() -> dict[str, object]:
    return {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "outcome": "success",
        "durability": {
            "verified": True,
            "sources": [
                "https://github.com/sponge-b0b/Polaris/issues/359",
                "https://github.com/sponge-b0b/Polaris/issues/359#issuecomment-1",
            ],
        },
        "handoffs": [
            {
                "destination": "$review-spec",
                "artifact": {
                    "title": (
                        "Spec: Implement R3 Portfolio consequence and "
                        "Portfolio Risk semantics"
                    ),
                    "url": "https://github.com/sponge-b0b/Polaris/issues/359",
                },
            }
        ],
    }


def _run(manifest: Path, output: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [
            sys.executable,
            str(FINALIZER),
            "finalize",
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_finalizer_publishes_only_shared_gate_validated_output(tmp_path: Path) -> None:
    manifest_value = _manifest()
    manifest = tmp_path / "handoff.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(manifest_value), encoding="utf-8")

    result = _run(manifest, output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "WORKFLOW HANDOFF: VALID"
    rendered = output.read_text(encoding="utf-8")
    assert rendered.startswith("✅ WORKFLOW HANDOFF: READY\n")
    assert (
        workflow_handoff.validate_output(manifest_value, rendered)
        == "WORKFLOW HANDOFF: VALID"
    )


def test_finalizer_preserves_warning_outcome(tmp_path: Path) -> None:
    manifest_value = _manifest()
    manifest_value["outcome"] = "warning"
    handoffs = manifest_value["handoffs"]
    assert isinstance(handoffs, list)
    handoff_item = handoffs[0]
    assert isinstance(handoff_item, dict)
    handoff_item["destination"] = "$to-tickets"
    manifest = tmp_path / "handoff.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(manifest_value), encoding="utf-8")

    result = _run(manifest, output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "WORKFLOW HANDOFF: VALID"
    rendered = output.read_text(encoding="utf-8")
    assert rendered.startswith("⚠️ WORKFLOW HANDOFF: READY\n")
    assert (
        workflow_handoff.validate_output(manifest_value, rendered)
        == "WORKFLOW HANDOFF: VALID"
    )


def test_finalizer_removes_stale_ready_output_when_validation_fails(
    tmp_path: Path,
) -> None:
    invalid = _manifest()
    invalid["schema"] = "polaris.workflow-handoff/invalid"
    manifest = tmp_path / "handoff.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(invalid), encoding="utf-8")
    output.write_text("WORKFLOW HANDOFF: READY\nstale\n", encoding="utf-8")

    result = _run(manifest, output)

    assert result.returncode != 0
    assert result.stdout.startswith("WORKFLOW HANDOFF: INVALID\n")
    assert not output.exists()
