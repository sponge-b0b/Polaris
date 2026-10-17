from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.ccl import CclValidationError, proposal_hash
from scripts.ccl_ledger import (
    admission_state,
    load_ledger,
    lookup_assertion,
    lookup_contract,
    persist_transaction,
    validate_ledger,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ccl"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _refresh_hashes(transaction: dict) -> None:
    transaction["proposal_hash"] = proposal_hash(transaction)
    acceptance = transaction["acceptance"]
    if acceptance is not None:
        acceptance["proposal_hash"] = transaction["proposal_hash"]


def _revision(
    source: dict,
    revision: int,
    operation: str,
    supersedes: int | None,
) -> dict:
    transaction = copy.deepcopy(source)
    item = transaction["revisions"][0]
    item["revision"] = revision
    item["operation"] = operation
    item["supersedes_revision"] = supersedes
    if operation == "retire":
        item["assertions"] = []
    _refresh_hashes(transaction)
    return transaction


def test_empty_ledger_admits_first_contract_revision() -> None:
    transaction = _load("351-recommendation-withholding.json")

    assert admission_state(transaction, []) == "ready"


def test_persistence_is_idempotent_and_lookup_uses_exact_addresses(
    tmp_path: Path,
) -> None:
    transaction = _load("351-recommendation-withholding.json")
    directory = tmp_path / "transactions"

    first = persist_transaction(directory, transaction)
    second = persist_transaction(directory, transaction)
    ledger = load_ledger(directory)

    assert first == second
    assert len(list(directory.glob("*.json"))) == 1
    assert lookup_contract(
        ledger,
        "investment-intelligence.recommendation-withholding",
    )["revision"] == 1
    assert lookup_assertion(
        ledger,
        "investment-intelligence.recommendation-withholding",
        "withholding.not-recommendation",
    )["constraint"] == {"target": "investment_recommendation"}


def test_ledger_rejects_revision_gap() -> None:
    first = _load("351-recommendation-withholding.json")
    third = _revision(first, 3, "revise", 2)

    with pytest.raises(CclValidationError, match="expected revision 2"):
        validate_ledger([first, third])


def test_ledger_accepts_contiguous_revision_then_retirement() -> None:
    first = _load("351-recommendation-withholding.json")
    second = _revision(first, 2, "revise", 1)
    third = _revision(first, 3, "retire", 2)

    validate_ledger([first, second, third])


def test_retirement_is_terminal_in_v1() -> None:
    first = _load("351-recommendation-withholding.json")
    second = _revision(first, 2, "revise", 1)
    third = _revision(first, 3, "retire", 2)
    fourth = _revision(first, 4, "revise", 3)

    with pytest.raises(CclValidationError, match="after retirement"):
        validate_ledger([first, second, third, fourth])


def test_one_transaction_cannot_contain_two_revisions_of_same_contract() -> None:
    transaction = _load("351-recommendation-withholding.json")
    second = _revision(transaction, 2, "revise", 1)
    transaction["revisions"].append(second["revisions"][0])
    _refresh_hashes(transaction)

    with pytest.raises(CclValidationError, match="duplicate contract"):
        validate_ledger([transaction])


def test_ledger_filename_is_bound_to_proposal_hash(tmp_path: Path) -> None:
    transaction = _load("351-recommendation-withholding.json")
    directory = tmp_path / "transactions"
    path = persist_transaction(directory, transaction)
    wrong = directory / "wrong.json"
    path.rename(wrong)

    with pytest.raises(CclValidationError, match="expected filename"):
        load_ledger(directory)


def test_owner_decision_requires_exact_hash_acceptance() -> None:
    transaction = _load("351-recommendation-withholding.json")
    transaction["origin"]["mode"] = "owner-decision"
    transaction["origin"].pop("wayfinder")
    transaction["acceptance"] = {
        "proposal_hash": transaction["proposal_hash"],
        "artifact": {
            "kind": "github_issue_comment",
            "ref": "issue:358#comment:123",
        },
    }

    assert admission_state(transaction, []) == "ready"

    transaction["acceptance"]["proposal_hash"] = "sha256:" + "0" * 64
    with pytest.raises(CclValidationError, match="acceptance.proposal_hash"):
        admission_state(transaction, [])


def test_wayfinder_decision_requires_wayfinder_identity() -> None:
    transaction = _load("351-recommendation-withholding.json")
    transaction["origin"]["mode"] = "wayfinder-decision"
    transaction["origin"].pop("wayfinder")
    transaction["acceptance"] = {
        "proposal_hash": transaction["proposal_hash"],
        "artifact": {
            "kind": "github_issue_comment",
            "ref": "issue:351#comment:5883743931",
        },
    }

    with pytest.raises(CclValidationError, match="origin.wayfinder"):
        admission_state(transaction, [])

    transaction["origin"]["wayfinder"] = {"map": 348, "decision": 351}
    assert admission_state(transaction, []) == "ready"
