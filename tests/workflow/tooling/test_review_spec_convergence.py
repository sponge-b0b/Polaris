from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / ".agents/skills/review-spec/scripts"
CONVERGENCE_SCRIPT = SCRIPTS / "review_convergence.py"
HANDOFF_SCRIPT = SCRIPTS / "review_spec_handoff.py"


def _load(name: str, path: Path):
    script_dir = str(path.parent)
    inserted = script_dir not in sys.path
    if inserted:
        sys.path.insert(0, script_dir)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted:
            sys.path.remove(script_dir)


CONVERGENCE = _load("review_spec_convergence", CONVERGENCE_SCRIPT)
HANDOFF = _load("review_spec_convergence_handoff", HANDOFF_SCRIPT)

HEAD = "a" * 40
SPEC_HASH = "b" * 64


def _contract() -> dict:
    return {
        "schema": "polaris.spec-contract/v1",
        "spec_body_hash": "c" * 64,
        "spec_contract_hash": SPEC_HASH,
        "cells": [
            {
                "cell": "OBL-001",
                "kind": "material-contract",
                "ccl": ["x@1#y"],
                "cell_hash": "1" * 64,
            }
        ],
    }


def _coverage(
    *,
    surface_ids: tuple[str, ...] = ("S1",),
    probe_start: int = 1,
    extra_surface: bool = False,
) -> dict:
    surfaces = [
        {
            "surface_id": surface_ids[0],
            "role": "production",
            "evidence": "src/example.py:10-20",
        }
    ]
    if extra_surface:
        surfaces.append(
            {
                "surface_id": surface_ids[1],
                "role": "production",
                "evidence": "src/sibling.py:5-9",
            }
        )
    refs = [item["surface_id"] for item in surfaces]
    lenses = ["positive", "negative", "composition", "proof"]
    probes = []
    for offset, lens in enumerate(lenses):
        probes.append(
            {
                "probe_id": f"P{probe_start + offset}",
                "lens": lens,
                "surface_ids": refs if lens == "negative" else [refs[0]],
                "falsifier": f"{lens} falsifier",
                "evidence": f"{lens} evidence",
                "finding_ids": ["RF-1"] if lens == "negative" else [],
            }
        )
    return {
        "schema": "polaris.review-coverage/v1",
        "spec_contract_hash": SPEC_HASH,
        "reviewed_head": HEAD,
        "cells": [
            {
                "cell": "OBL-001",
                "cell_hash": "1" * 64,
                "kind": "material-contract",
                "surfaces": surfaces,
                "lenses": [
                    {"lens": lens, "status": "covered", "rationale": ""}
                    for lens in lenses
                ],
                "probes": probes,
            }
        ],
    }


def _manifest(source_count: int = 5) -> dict:
    return {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "outcome": "warning",
        "durability": {
            "verified": True,
            "sources": [
                f"https://github.com/o/r/issues/1#issuecomment-{index}"
                for index in range(1, source_count + 1)
            ],
        },
        "handoffs": [
            {
                "destination": "$to-tickets",
                "artifact": {
                    "title": "Spec Review: Example",
                    "url": "https://github.com/o/r/issues/1",
                },
            }
        ],
    }


def test_two_stable_complete_rounds_converge() -> None:
    first = _coverage(surface_ids=("S1",), probe_start=1)
    second = _coverage(surface_ids=("S2",), probe_start=5)
    artifact = CONVERGENCE.build_convergence(_contract(), [first, second])
    receipt = CONVERGENCE.validate_convergence(artifact)
    assert receipt.rounds == 2
    assert receipt.surface_count == 1
    assert receipt.probe_count == 4
    assert receipt.finding_link_count == 1


def test_final_challenger_expansion_blocks_convergence() -> None:
    first = _coverage(surface_ids=("S1",), probe_start=1)
    expanded = _coverage(
        surface_ids=("S1", "S2"), probe_start=5, extra_surface=True
    )
    artifact = CONVERGENCE.build_convergence(_contract(), [first, expanded])
    with pytest.raises(
        CONVERGENCE.ReviewConvergenceError,
        match="final challenger changed the material review universe",
    ):
        CONVERGENCE.validate_convergence(artifact)


def test_expansion_then_fresh_stable_challenger_converges() -> None:
    first = _coverage(surface_ids=("S1",), probe_start=1)
    expanded = _coverage(
        surface_ids=("S1", "S2"), probe_start=5, extra_surface=True
    )
    stable = _coverage(
        surface_ids=("S3", "S4"), probe_start=9, extra_surface=True
    )
    artifact = CONVERGENCE.build_convergence(
        _contract(), [first, expanded, stable]
    )
    receipt = CONVERGENCE.validate_convergence(artifact)
    assert receipt.rounds == 3
    assert receipt.surface_count == 2


def test_handoff_requires_convergence_durability_source(tmp_path: Path) -> None:
    first = _coverage(surface_ids=("S1",), probe_start=1)
    second = _coverage(surface_ids=("S2",), probe_start=5)
    convergence = CONVERGENCE.build_convergence(_contract(), [first, second])
    manifest = tmp_path / "manifest.json"
    coverage = tmp_path / "coverage.json"
    convergence_path = tmp_path / "convergence.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(_manifest(4)), encoding="utf-8")
    coverage.write_text(json.dumps(second), encoding="utf-8")
    convergence_path.write_text(json.dumps(convergence), encoding="utf-8")

    with pytest.raises(RuntimeError, match="convergence"):
        HANDOFF.finalize_converged(manifest, coverage, convergence_path, output)
    assert not output.exists()


def test_handoff_rejects_convergence_bound_to_other_final_coverage(
    tmp_path: Path,
) -> None:
    first = _coverage(surface_ids=("S1",), probe_start=1)
    second = _coverage(surface_ids=("S2",), probe_start=5)
    convergence = CONVERGENCE.build_convergence(_contract(), [first, second])
    changed_final = _coverage(
        surface_ids=("S3", "S4"), probe_start=9, extra_surface=True
    )
    manifest = tmp_path / "manifest.json"
    coverage = tmp_path / "coverage.json"
    convergence_path = tmp_path / "convergence.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")
    coverage.write_text(json.dumps(changed_final), encoding="utf-8")
    convergence_path.write_text(json.dumps(convergence), encoding="utf-8")

    with pytest.raises(RuntimeError, match="not bound to the final review coverage"):
        HANDOFF.finalize_converged(manifest, coverage, convergence_path, output)
    assert not output.exists()


def test_convergence_policy_names_missed_prior_finding_recovery() -> None:
    policy = (ROOT / ".agents/skills/review-spec/CONVERGENCE.md").read_text(
        encoding="utf-8"
    )
    assert "review completeness regression" in policy
    assert "Cross-cutting family saturation" in policy
    assert "fresh non-mutating challenger" in policy
    assert "fixed point" in policy
    assert "Neither PASS nor remediation handoff is allowed until convergence is valid" in policy
