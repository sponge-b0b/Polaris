from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.ccl import CclValidationError
from scripts.ccl_adr import decision_block, transaction_path, validate_adr

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ccl"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _accepted_wayfinder_transaction() -> dict:
    transaction = _load("demo-recording.json")
    transaction = copy.deepcopy(transaction)
    transaction["origin"]["mode"] = "wayfinder-decision"
    transaction["origin"]["wayfinder"] = {"map": 101, "decision": 102}
    transaction["acceptance"] = {
        "proposal_hash": transaction["proposal_hash"],
        "artifact": {
            "kind": "github_issue_comment",
            "ref": "issue:102#comment:3",
        },
    }
    return transaction


def _adr(transaction: dict) -> str:
    return (
        "---\n"
        "status: accepted\n"
        f"ccl_proposal: {transaction['proposal_hash']}\n"
        f"ccl_transaction: {transaction_path(transaction)}\n"
        "---\n\n"
        "# Persist Workflow Record\n\n"
        "## Context\n\n"
        "The decision needs durable historical meaning.\n\n"
        "## Decision\n\n"
        f"{decision_block(transaction)}\n\n"
        "## Rationale\n\n"
        "This preserves the accepted trade-off.\n"
    )


def test_ccl_backed_adr_projection_is_valid() -> None:
    transaction = _accepted_wayfinder_transaction()

    validate_adr(_adr(transaction), transaction)


def test_ccl_backed_adr_rejects_decision_semantic_drift() -> None:
    transaction = _accepted_wayfinder_transaction()
    adr = _adr(transaction).replace(
        "persistence is durable.",
        "persistence is derived.",
        1,
    )

    with pytest.raises(CclValidationError, match="CCL projection drift"):
        validate_adr(adr, transaction)


def test_ccl_backed_adr_rejects_extra_decision_prose() -> None:
    transaction = _accepted_wayfinder_transaction()
    adr = _adr(transaction).replace(
        "## Decision\n\n",
        "## Decision\n\nA second semantic interpretation.\n\n",
        1,
    )

    with pytest.raises(CclValidationError, match="CCL projection drift"):
        validate_adr(adr, transaction)


def test_ccl_backed_adr_rejects_wrong_transaction_frontmatter() -> None:
    transaction = _accepted_wayfinder_transaction()
    adr = _adr(transaction).replace(
        "ccl_transaction: contracts/ccl/transactions/",
        "ccl_transaction: contracts/ccl/transactions/wrong-",
        1,
    )

    with pytest.raises(CclValidationError, match="frontmatter"):
        validate_adr(adr, transaction)
