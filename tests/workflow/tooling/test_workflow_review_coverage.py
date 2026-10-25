from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / ".agents/skills/review-spec/scripts/review_coverage.py"
SPEC = importlib.util.spec_from_file_location("review_spec_coverage", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
ReviewCoverageError = MODULE.ReviewCoverageError
validate_coverage = MODULE.validate_coverage

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
            },
            {
                "cell": "TEST-001",
                "kind": "testing",
                "requirement": "Prove it.",
                "cell_hash": "2" * 64,
            },
            {
                "cell": "EXC-001",
                "kind": "exclusion",
                "requirement": "Do not broaden.",
                "cell_hash": "3" * 64,
            },
        ],
    }


def _row(cell: str, cell_hash: str, kind: str, lenses: list[str]) -> dict:
    return {
        "cell": cell,
        "cell_hash": cell_hash,
        "kind": kind,
        "surfaces": [
            {
                "surface_id": "S1",
                "role": "production" if kind != "testing" else "proof",
                "evidence": (
                    "src/example.py:example"
                    if kind != "testing"
                    else "tests/test_example.py:test_example"
                ),
            }
        ],
        "lenses": [
            {"lens": lens, "status": "covered", "rationale": ""}
            for lens in lenses
        ],
        "probes": [
            {
                "probe_id": f"P{index}",
                "lens": lens,
                "surface_ids": ["S1"],
                "falsifier": f"Concrete falsifier for {lens}.",
                "evidence": f"Concrete evidence for {lens}.",
                "finding_ids": [],
            }
            for index, lens in enumerate(lenses, start=1)
        ],
    }


def _coverage() -> dict:
    return {
        "schema": "polaris.review-coverage/v1",
        "spec_contract_hash": SPEC_HASH,
        "reviewed_head": HEAD,
        "cells": [
            _row(
                "OBL-001",
                "1" * 64,
                "material-contract",
                ["positive", "negative", "composition", "proof"],
            ),
            _row("TEST-001", "2" * 64, "testing", ["proof", "negative"]),
            _row("EXC-001", "3" * 64, "exclusion", ["exclusion"]),
        ],
    }


def test_complete_coverage_is_valid() -> None:
    receipt = validate_coverage(_contract(), _coverage())
    assert receipt.reviewed_cells == 3
    assert receipt.total_cells == 3
    assert receipt.surface_count == 3
    assert receipt.probe_count == 7


def test_missing_cell_is_rejected() -> None:
    coverage = _coverage()
    coverage["cells"].pop()
    with pytest.raises(ReviewCoverageError, match="cell count"):
        validate_coverage(_contract(), coverage)


def test_duplicate_cell_is_rejected() -> None:
    coverage = _coverage()
    coverage["cells"][1] = deepcopy(coverage["cells"][0])
    with pytest.raises(ReviewCoverageError, match="duplicate cell|cell order mismatch"):
        validate_coverage(_contract(), coverage)


def test_stale_cell_hash_is_rejected() -> None:
    coverage = _coverage()
    coverage["cells"][0]["cell_hash"] = "f" * 64
    with pytest.raises(ReviewCoverageError, match="stale cell hash OBL-001"):
        validate_coverage(_contract(), coverage)


def test_required_lens_cannot_be_silently_omitted() -> None:
    coverage = _coverage()
    coverage["cells"][0]["lenses"].pop(1)
    coverage["cells"][0]["probes"] = [
        probe for probe in coverage["cells"][0]["probes"] if probe["lens"] != "negative"
    ]
    with pytest.raises(ReviewCoverageError, match="required lenses"):
        validate_coverage(_contract(), coverage)


def test_not_applicable_lens_requires_rationale() -> None:
    coverage = _coverage()
    coverage["cells"][0]["lenses"][1] = {
        "lens": "negative",
        "status": "not-applicable",
        "rationale": "",
    }
    coverage["cells"][0]["probes"] = [
        probe for probe in coverage["cells"][0]["probes"] if probe["lens"] != "negative"
    ]
    with pytest.raises(ReviewCoverageError, match="requires rationale"):
        validate_coverage(_contract(), coverage)


def test_not_applicable_lens_with_rationale_is_valid() -> None:
    coverage = _coverage()
    coverage["cells"][0]["lenses"][1] = {
        "lens": "negative",
        "status": "not-applicable",
        "rationale": "The exact obligation has no failure-state branch.",
    }
    coverage["cells"][0]["probes"] = [
        probe for probe in coverage["cells"][0]["probes"] if probe["lens"] != "negative"
    ]
    receipt = validate_coverage(_contract(), coverage)
    assert receipt.probe_count == 6


def test_covered_lens_requires_probe() -> None:
    coverage = _coverage()
    coverage["cells"][0]["probes"] = [
        probe
        for probe in coverage["cells"][0]["probes"]
        if probe["lens"] != "composition"
    ]
    with pytest.raises(
        ReviewCoverageError, match="covered lens composition has no probe"
    ):
        validate_coverage(_contract(), coverage)


def test_every_declared_surface_must_be_exercised() -> None:
    coverage = _coverage()
    coverage["cells"][0]["surfaces"].append(
        {"surface_id": "S2", "role": "production", "evidence": "src/other.py:other"}
    )
    with pytest.raises(ReviewCoverageError, match="every declared review surface"):
        validate_coverage(_contract(), coverage)


def test_probe_rejects_unknown_surface() -> None:
    coverage = _coverage()
    coverage["cells"][0]["probes"][0]["surface_ids"] = ["S9"]
    with pytest.raises(ReviewCoverageError, match="unknown surface"):
        validate_coverage(_contract(), coverage)


def test_reviewed_head_must_be_full_sha() -> None:
    coverage = _coverage()
    coverage["reviewed_head"] = "abc123"
    with pytest.raises(ReviewCoverageError, match="full lowercase commit SHA"):
        validate_coverage(_contract(), coverage)


def test_cli_emits_machine_complete_receipt(tmp_path: Path) -> None:
    contract_path = tmp_path / "contract.json"
    coverage_path = tmp_path / "coverage.json"
    contract_path.write_text(json.dumps(_contract()), encoding="utf-8")
    coverage_path.write_text(json.dumps(_coverage()), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "validate",
            str(contract_path),
            str(coverage_path),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    lines = completed.stdout.splitlines()
    assert lines[0] == "REVIEW COVERAGE: VALID"
    assert lines[1] == f"Reviewed HEAD: {HEAD}"
    assert lines[2] == f"Spec Contract Hash: {SPEC_HASH}"
    assert lines[3] == "Contract cells reviewed: 3/3"
    assert lines[4] == "Unchecked contract cells: 0"
    assert lines[5] == "Declared review surfaces: 3"
    assert lines[6] == "Adversarial probes: 7"
    assert lines[7].startswith("Review Coverage SHA-256: ")


def test_review_spec_skill_requires_machine_coverage_and_full_failed_sweep() -> None:
    skill = (ROOT / ".agents/skills/review-spec/SKILL.md").read_text(encoding="utf-8")
    assert "review-spec-coverage:v1" in skill
    assert (
        "python .agents/skills/review-spec/scripts/review_coverage.py validate" in skill
    )
    assert "REVIEW COVERAGE: VALID" in skill
    assert "A Blocking finding does not terminate the sweep" in skill
    assert "coverage challenger" in skill.lower()
