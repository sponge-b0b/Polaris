from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

FINDINGS_SCRIPT = ROOT / ".agents/skills/review-spec/scripts/review_findings.py"
HANDOFF_SCRIPT = ROOT / ".agents/skills/review-spec/scripts/review_spec_handoff.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FINDINGS = _load("review_spec_findings", FINDINGS_SCRIPT)
HANDOFF = _load("review_spec_handoff", HANDOFF_SCRIPT)

ReviewFindingError = FINDINGS.ReviewFindingError
validate_review_findings = FINDINGS.validate_review_findings
sha256_canonical_json = FINDINGS.sha256_canonical_json

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
        ],
    }


def _probe(probe_id: str, finding_ids: list[str]) -> dict:
    return {
        "probe_id": probe_id,
        "lens": "proof",
        "surface_ids": ["S1"],
        "falsifier": "Concrete falsifier.",
        "evidence": "Concrete proof evidence.",
        "finding_ids": finding_ids,
    }


def _coverage() -> dict:
    return {
        "schema": "polaris.review-coverage/v1",
        "spec_contract_hash": SPEC_HASH,
        "reviewed_head": HEAD,
        "cells": [
            {
                "cell": "OBL-001",
                "cell_hash": "1" * 64,
                "kind": "material-contract",
                "surfaces": [
                    {
                        "surface_id": "S1",
                        "role": "production",
                        "evidence": "src/example.py:10-20",
                    }
                ],
                "lenses": [],
                "probes": [_probe("P1", ["RF-1"])],
            },
            {
                "cell": "TEST-001",
                "cell_hash": "2" * 64,
                "kind": "testing",
                "surfaces": [
                    {
                        "surface_id": "S1",
                        "role": "proof",
                        "evidence": "tests/test_example.py:30-40",
                    }
                ],
                "lenses": [],
                "probes": [_probe("P1", ["RF-1"])],
            },
        ],
    }


def _finding() -> dict:
    return {
        "finding_id": "RF-1",
        "axis": "Spec",
        "severity": "Blocking",
        "classification": "test/proof-defect",
        "cells": [
            {"cell": "OBL-001", "cell_hash": "1" * 64},
            {"cell": "TEST-001", "cell_hash": "2" * 64},
        ],
        "standard_refs": [],
        "falsifier": "The frozen behavior can regress without proof.",
        "evidence": (
            "src/example.py:10-20 defines the behavior; "
            "tests/test_example.py:30-40 omits the negative proof."
        ),
        "owner": "$to-tickets",
        "status": "open",
    }


def _ledger() -> dict:
    return {
        "schema": "polaris.review-findings/v2",
        "spec": "#1",
        "spec_contract_hash": SPEC_HASH,
        "findings": [_finding()],
    }


def _adjudication() -> dict:
    finding = _finding()
    return {
        "schema": "polaris.review-finding-adjudication/v1",
        "spec_contract_hash": SPEC_HASH,
        "reviewed_head": HEAD,
        "findings": [
            {
                "finding_id": "RF-1",
                "finding_sha256": sha256_canonical_json(finding),
                "verdict": "confirmed",
                "evidence_checks": [
                    {
                        "locator": "src/example.py:10-20",
                        "claim": "Production behavior exists at this boundary.",
                        "observed": "The cited implementation defines the behavior.",
                        "result": "supports",
                    },
                    {
                        "locator": "tests/test_example.py:30-40",
                        "claim": "The frozen negative proof is absent.",
                        "observed": "The cited test covers only the positive path.",
                        "result": "supports",
                    },
                ],
                "cell_scope_checks": [
                    {
                        "cell": "OBL-001",
                        "cell_hash": "1" * 64,
                        "rationale": "The missing proof is for this obligation.",
                    },
                    {
                        "cell": "TEST-001",
                        "cell_hash": "2" * 64,
                        "rationale": "This testing cell explicitly requires the proof.",
                    },
                ],
                "falsifier_check": (
                    "The falsifier is bounded to the frozen obligation and proof cell."
                ),
            }
        ],
    }


def test_final_finding_cross_validation_passes() -> None:
    receipt = validate_review_findings(
        _contract(),
        _coverage(),
        _ledger(),
        _adjudication(),
    )
    assert receipt.finding_count == 1
    assert receipt.link_count == 2


def test_missing_coverage_finding_cell_link_fails_closed() -> None:
    coverage = _coverage()
    coverage["cells"][0]["probes"][0]["finding_ids"] = []
    with pytest.raises(ReviewFindingError, match="coverage/finding cell mismatch"):
        validate_review_findings(
            _contract(),
            coverage,
            _ledger(),
            _adjudication(),
        )


def test_extra_coverage_finding_cell_link_fails_closed() -> None:
    ledger = _ledger()
    ledger["findings"][0]["cells"].pop()
    adjudication = _adjudication()
    adjudication["findings"][0]["finding_sha256"] = sha256_canonical_json(
        ledger["findings"][0]
    )
    adjudication["findings"][0]["cell_scope_checks"].pop()
    with pytest.raises(ReviewFindingError, match="coverage/finding cell mismatch"):
        validate_review_findings(
            _contract(),
            _coverage(),
            ledger,
            adjudication,
        )


def test_stale_final_finding_hash_is_rejected() -> None:
    adjudication = _adjudication()
    adjudication["findings"][0]["finding_sha256"] = "f" * 64
    with pytest.raises(ReviewFindingError, match="stale final finding hash"):
        validate_review_findings(
            _contract(),
            _coverage(),
            _ledger(),
            adjudication,
        )


def test_every_cited_code_locator_must_be_adjudicated() -> None:
    adjudication = _adjudication()
    adjudication["findings"][0]["evidence_checks"].pop()
    with pytest.raises(ReviewFindingError, match="every cited code evidence locator"):
        validate_review_findings(
            _contract(),
            _coverage(),
            _ledger(),
            adjudication,
        )


def test_final_finding_must_be_confirmed() -> None:
    adjudication = _adjudication()
    adjudication["findings"][0]["verdict"] = "corrected"
    with pytest.raises(ReviewFindingError, match="independently confirmed"):
        validate_review_findings(
            _contract(),
            _coverage(),
            _ledger(),
            adjudication,
        )


def test_cli_emits_final_finding_receipt(tmp_path: Path) -> None:
    values = {
        "contract.json": _contract(),
        "coverage.json": _coverage(),
        "findings.json": _ledger(),
        "adjudication.json": _adjudication(),
    }
    for name, value in values.items():
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")

    completed = __import__("subprocess").run(
        [
            sys.executable,
            str(FINDINGS_SCRIPT),
            "validate",
            str(tmp_path / "contract.json"),
            str(tmp_path / "coverage.json"),
            str(tmp_path / "findings.json"),
            str(tmp_path / "adjudication.json"),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert completed.stdout.splitlines()[0] == "REVIEW FINDINGS: VALID"
    assert "Coverage/finding cell links: VALID" in completed.stdout
    assert "Unchecked cited code evidence locators: 0" in completed.stdout


def _manifest(outcome: str = "warning") -> dict:
    destination = "$to-tickets" if outcome == "warning" else "$spec-merge-cleanup"
    return {
        "schema": "polaris.workflow-handoff/v1",
        "boundary": "human-lifecycle",
        "outcome": outcome,
        "durability": {
            "verified": True,
            "sources": [
                "https://github.com/o/r/issues/1#issuecomment-1",
                "https://github.com/o/r/issues/1#issuecomment-2",
                "https://github.com/o/r/issues/1#issuecomment-3",
                "https://github.com/o/r/issues/2#issuecomment-4",
            ],
        },
        "handoffs": [
            {
                "destination": destination,
                "artifact": {
                    "title": "Spec Review: Example",
                    "url": "https://github.com/o/r/issues/1",
                },
            }
        ],
    }


def test_review_handoff_finalizer_requires_warning_outcome(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")

    assert HANDOFF.finalize(manifest, output) == "WORKFLOW HANDOFF: VALID"
    assert output.read_text(encoding="utf-8").startswith(
        "⚠️ WORKFLOW HANDOFF: READY\n"
    )


def test_review_handoff_rejects_missing_outcome(tmp_path: Path) -> None:
    value = _manifest()
    del value["outcome"]
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(RuntimeError, match="outcome must be success or warning"):
        HANDOFF.finalize(manifest, output)
    assert not output.exists()


def test_review_handoff_rejects_success_to_remediation(tmp_path: Path) -> None:
    value = _manifest("success")
    value["handoffs"][0]["destination"] = "$to-tickets"
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "handoff.txt"
    manifest.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(RuntimeError, match="success must hand off"):
        HANDOFF.finalize(manifest, output)


def test_review_spec_skill_requires_finding_adjudication_and_gated_handoff() -> None:
    skill = (ROOT / ".agents/skills/review-spec/SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "polaris.review-finding-adjudication/v1" in skill
    assert "confirmed\ncorrected\nrejected" in skill
    assert "re-open **every concrete cited code/test evidence locator**" in skill
    assert "Coverage/finding cell links: VALID" in skill
    assert "review_spec_handoff.py finalize" in skill
    assert "A bare lifecycle invocation" in skill
    assert "reconcile the managed ChatGPT Session Ledger" in skill
