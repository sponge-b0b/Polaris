from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.ccl import (
    CclValidationError,
    authority_conflicts,
    proposal_hash,
    render_transaction,
    validate_projection,
    validate_transaction,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ccl"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_demo_recording_contract_is_valid() -> None:
    transaction = _load("demo-recording.json")
    validate_transaction(transaction)


def test_display_and_examples_do_not_change_semantic_hash() -> None:
    transaction = _load("demo-recording.json")
    changed = copy.deepcopy(transaction)
    revision = changed["revisions"][0]
    revision["display"]["title"] = "Different human title"
    revision["display"]["summary"] = "Different explanatory prose."
    revision["assertions"][0]["display"]["description"] = "Different description."
    revision["annotations"]["examples"] = ["different example"]
    revision["annotations"]["notes"] = ["different note"]

    assert proposal_hash(changed) == transaction["proposal_hash"]


def test_human_readable_rendering_is_generated_from_typed_assertions() -> None:
    transaction = _load("demo-recording.json")
    rendered = render_transaction(transaction)

    assert "Summary (non-authoritative)" in rendered
    assert "record.not-command" in rendered
    assert "semantically distinct from workflow_command" in rendered
    assert "sample-only explanation" not in rendered


def test_unknown_taxonomy_cannot_be_invented_downstream() -> None:
    transaction = _load("demo-recording.json")
    projection = _load("demo-overstrengthened-taxonomy.json")

    with pytest.raises(CclValidationError, match="unknown CCL assertion"):
        validate_projection(projection, [transaction])


def test_exact_typed_projection_is_accepted() -> None:
    transaction = _load("demo-recording.json")
    projection = _load("demo-valid-projection.json")

    validate_projection(projection, [transaction])


def test_required_vs_optional_is_a_source_conflict() -> None:
    check = _load("demo-authority-conflict.json")

    assert authority_conflicts(check) == [
        "workflow-demo.relationship#record.related-presence: "
        "decision-103-resolution != adr-demo-0001"
    ]


def test_equal_governing_source_claims_do_not_conflict() -> None:
    check = _load("demo-authority-conflict.json")
    required = copy.deepcopy(check["source_claims"][0]["normalized"])
    check["source_claims"][1]["normalized"] = required

    assert authority_conflicts(check) == []


def test_transaction_rejects_proposal_hash_drift() -> None:
    transaction = _load("demo-recording.json")
    transaction["revisions"][0]["assertions"][0]["constraint"]["mode"] = "derived"

    with pytest.raises(CclValidationError, match="proposal_hash"):
        validate_transaction(transaction)
