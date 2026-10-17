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


def test_351_withholding_contract_is_valid() -> None:
    transaction = _load("351-recommendation-withholding.json")
    validate_transaction(transaction)


def test_display_and_examples_do_not_change_semantic_hash() -> None:
    transaction = _load("351-recommendation-withholding.json")
    changed = copy.deepcopy(transaction)
    revision = changed["revisions"][0]
    revision["display"]["title"] = "Different human title"
    revision["display"]["summary"] = "Different explanatory prose."
    revision["assertions"][0]["display"]["description"] = "Different description."
    revision["annotations"]["examples"] = ["different example"]
    revision["annotations"]["notes"] = ["different note"]

    assert proposal_hash(changed) == transaction["proposal_hash"]


def test_human_readable_rendering_is_generated_from_typed_assertions() -> None:
    transaction = _load("351-recommendation-withholding.json")
    rendered = render_transaction(transaction)

    assert "Summary (non-authoritative)" in rendered
    assert "withholding.not-recommendation" in rendered
    assert "semantically distinct from investment_recommendation" in rendered
    assert "insufficient Evidence" not in rendered


def test_351_reason_taxonomy_cannot_be_invented_downstream() -> None:
    transaction = _load("351-recommendation-withholding.json")
    projection = _load("351-overstrengthened-reason-taxonomy.json")

    with pytest.raises(CclValidationError, match="unknown CCL assertion"):
        validate_projection(projection, [transaction])


def test_351_exact_typed_projection_is_accepted() -> None:
    transaction = _load("351-recommendation-withholding.json")
    projection = _load("351-valid-projection.json")

    validate_projection(projection, [transaction])


def test_352_required_vs_optional_is_a_source_conflict() -> None:
    check = _load("352-required-vs-optional-source-conflict.json")

    assert authority_conflicts(check) == [
        "portfolio-risk.projected-consequence#alternative.consequence-presence: "
        "decision-352-resolution != adr-0008"
    ]


def test_equal_governing_source_claims_do_not_conflict() -> None:
    check = _load("352-required-vs-optional-source-conflict.json")
    required = copy.deepcopy(check["source_claims"][0]["normalized"])
    check["source_claims"][1]["normalized"] = required

    assert authority_conflicts(check) == []


def test_transaction_rejects_proposal_hash_drift() -> None:
    transaction = _load("351-recommendation-withholding.json")
    transaction["revisions"][0]["assertions"][0]["constraint"]["mode"] = "derived"

    with pytest.raises(CclValidationError, match="proposal_hash"):
        validate_transaction(transaction)
