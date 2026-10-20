from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
SCRIPT = ROOT / ".agents/skills/wayfinder/scripts/decision_closure.py"
SPEC = importlib.util.spec_from_file_location("decision_closure", SCRIPT)
assert SPEC and SPEC.loader
decision_closure = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decision_closure)

COMMIT = "1" * 40
PROPOSAL = "sha256:" + ("2" * 64)
TRANSACTION = f"contracts/ccl/transactions/{'2' * 64}.json"
ADR_PATH = "docs/adr/0099-test.md"


def _write_repo_files(tmp_path: Path) -> None:
    transaction = tmp_path / TRANSACTION
    transaction.parent.mkdir(parents=True, exist_ok=True)
    transaction.write_text(
        json.dumps(
            {
                "proposal_hash": PROPOSAL,
                "origin": {"mode": "wayfinder-decision"},
                "acceptance": {"accepted": True},
            }
        ),
        encoding="utf-8",
    )
    adr = tmp_path / ADR_PATH
    adr.parent.mkdir(parents=True, exist_ok=True)
    adr.write_text(
        "---\n"
        "status: accepted\n"
        f"ccl_proposal: {PROPOSAL}\n"
        f"ccl_transaction: {TRANSACTION}\n"
        "---\n",
        encoding="utf-8",
    )


def _receipt(*, wiki_disposition: str = "NO_DURABLE_KNOWLEDGE_CHANGED") -> dict:
    return {
        "schema": "polaris.wayfinder-decision-closure/v1",
        "decision": {
            "number": 417,
            "url": "https://github.com/sponge-b0b/Polaris/issues/417",
        },
        "canonical_commit": COMMIT,
        "semantic_mode": "ccl-backed",
        "ccl_proposal": PROPOSAL,
        "ccl_transaction": TRANSACTION,
        "adr": {
            "disposition": "CREATED",
            "path": ADR_PATH,
            "projection_check": "PASS",
        },
        "wiki_sync": {
            "disposition": wiki_disposition,
            "affected_knowledge_routing": [
                {
                    "candidate": "WK-1",
                    "changed_surface_authority": ADR_PATH,
                    "candidate_entity_claim": "evidence / sufficiency count unit",
                    "routing_basis": "inline citation and changed authority",
                    "disposition": "not-affected",
                    "reason_evidence": "Existing invariant already states observation identity.",
                }
            ],
            "mutations": [],
        },
    }


def _write_receipt(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "closure.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _stub_repo(monkeypatch: pytest.MonkeyPatch, *, clean: bool = True, head: str = COMMIT) -> None:
    monkeypatch.setattr(decision_closure, "_repo_head", lambda _root: head)
    monkeypatch.setattr(decision_closure, "_repo_clean", lambda _root: clean)


def test_ccl_backed_noop_wiki_receipt_allows_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch)
    output = decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, _receipt()))
    assert output.splitlines()[0] == "WAYFINDER DECISION CLOSURE: ALLOWED"
    assert "Decision: #417" in output
    assert "Wiki sync: NO_DURABLE_KNOWLEDGE_CHANGED" in output


def test_noop_wiki_receipt_rejects_affected_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch)
    receipt = _receipt()
    receipt["wiki_sync"]["affected_knowledge_routing"][0]["disposition"] = "affected"
    with pytest.raises(decision_closure.ClosureError, match="affected candidate"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, receipt))


def test_wiki_receipt_rejects_unresolved_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch)
    receipt = _receipt()
    receipt["wiki_sync"]["affected_knowledge_routing"][0]["disposition"] = "unresolved"
    with pytest.raises(decision_closure.ClosureError, match="unresolved/unsupported"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, receipt))


def test_ccl_backed_decision_rejects_missing_wiki_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch)
    receipt = _receipt()
    receipt["wiki_sync"] = {"disposition": "NOT-APPLICABLE"}
    with pytest.raises(decision_closure.ClosureError, match="CCL-backed decisions require"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, receipt))


def test_updated_wiki_receipt_requires_log_and_existing_mutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch)
    receipt = _receipt(wiki_disposition="UPDATED")
    receipt["wiki_sync"]["affected_knowledge_routing"][0]["disposition"] = "affected"
    receipt["wiki_sync"]["mutations"] = ["wiki/entities/evidence.md"]
    with pytest.raises(decision_closure.ClosureError, match="wiki/log.md"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, receipt))


def test_adr_receipt_must_bind_proposal_and_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch)
    (tmp_path / ADR_PATH).write_text("---\nstatus: accepted\n---\n", encoding="utf-8")
    with pytest.raises(decision_closure.ClosureError, match="accepted proposal"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, _receipt()))


def test_canonical_commit_and_clean_worktree_are_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_repo_files(tmp_path)
    _stub_repo(monkeypatch, head="3" * 40)
    with pytest.raises(decision_closure.ClosureError, match="HEAD is not canonical commit"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, _receipt()))

    _stub_repo(monkeypatch, clean=False)
    with pytest.raises(decision_closure.ClosureError, match="clean worktree"):
        decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, _receipt()))


def test_non_material_decision_allows_explicit_not_applicable_children(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_repo(monkeypatch)
    receipt = {
        "schema": "polaris.wayfinder-decision-closure/v1",
        "decision": {
            "number": 500,
            "url": "https://github.com/sponge-b0b/Polaris/issues/500",
        },
        "canonical_commit": COMMIT,
        "semantic_mode": "non-material",
        "ccl_proposal": None,
        "ccl_transaction": None,
        "adr": {"disposition": "NOT-APPLICABLE"},
        "wiki_sync": {"disposition": "NOT-APPLICABLE"},
    }
    output = decision_closure.validate_closure(tmp_path, _write_receipt(tmp_path, receipt))
    assert "ADR: NOT-APPLICABLE" in output
    assert "Wiki sync: NOT-APPLICABLE" in output
