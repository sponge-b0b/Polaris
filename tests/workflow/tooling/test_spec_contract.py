from __future__ import annotations

import pytest

from scripts.spec_contract import SpecContractError, build_contract, validate_coverage

REF_PERSIST = "workflow-demo.recording@1#record.persistence"
REF_DISTINCT = "workflow-demo.recording@1#record.not-command"

BODY = f'''<!-- spec-contract-ccl:v1
{{
  "schema": "polaris.spec-ccl/v1",
  "obligations": [
    {{
      "obligation_id": "OBL-001",
      "source_ref": "Decision #102",
      "ccl": ["{REF_PERSIST}", "{REF_DISTINCT}"]
    }}
  ]
}}
-->

## Problem Statement
Explanation only.

## Canonical Contract Obligations
Generated elsewhere.

## Implementation Decisions
- `IMP-001` — Persist through the established workflow repository seam.

## Testing Decisions
- `TEST-001` — Prove the workflow record is distinct from a command.

## Out of Scope
- `EXC-001` — Defining a public workflow-record taxonomy.
'''


def test_build_contract_is_deterministic_and_ccl_anchored() -> None:
    first = build_contract(BODY)
    second = build_contract(BODY)
    assert first == second
    assert set(first) == {
        "schema",
        "spec_body_hash",
        "spec_contract_hash",
        "cells",
    }
    assert [cell["cell"] for cell in first["cells"]] == [
        "OBL-001",
        "IMP-001",
        "TEST-001",
        "EXC-001",
    ]
    obligation = first["cells"][0]
    assert obligation["kind"] == "material-contract"
    assert obligation["ccl"] == [REF_PERSIST, REF_DISTINCT]


def test_explanatory_prose_does_not_change_contract_hash() -> None:
    changed = BODY.replace("Explanation only.", "A much longer explanation for humans.")
    original = build_contract(BODY)
    revised = build_contract(changed)
    assert original["spec_body_hash"] != revised["spec_body_hash"]
    assert original["spec_contract_hash"] == revised["spec_contract_hash"]
    assert original["cells"] == revised["cells"]


def test_private_plan_change_changes_contract_hash() -> None:
    changed = BODY.replace(
        "established workflow repository seam",
        "new workflow adapter seam",
    )
    assert (
        build_contract(BODY)["spec_contract_hash"]
        != build_contract(changed)["spec_contract_hash"]
    )


def test_ccl_revision_change_changes_contract_hash() -> None:
    changed = BODY.replace("@1#record.persistence", "@2#record.persistence")
    assert (
        build_contract(BODY)["spec_contract_hash"]
        != build_contract(changed)["spec_contract_hash"]
    )


def test_requires_stable_plan_ids() -> None:
    changed = BODY.replace("- `IMP-001` —", "- Persist")
    with pytest.raises(
        SpecContractError,
        match="invalid ## Implementation Decisions row",
    ):
        build_contract(changed)


def test_contract_hash_tracks_exclusion() -> None:
    changed = BODY.replace(
        "public workflow-record taxonomy",
        "closed workflow-record taxonomy",
    )
    assert (
        build_contract(BODY)["spec_contract_hash"]
        != build_contract(changed)["spec_contract_hash"]
    )


def _coverage(contract: dict) -> dict:
    routes = []
    exclusions = []
    for cell in contract["cells"]:
        if cell["kind"] == "exclusion":
            exclusions.append(
                {"cell": cell["cell"], "cell_hash": cell["cell_hash"]}
            )
        else:
            routes.append(
                {
                    "cell": cell["cell"],
                    "cell_hash": cell["cell_hash"],
                    "destination": "T1",
                }
            )
    return {
        "schema": "polaris.ticket-coverage/v2",
        "spec_contract_hash": contract["spec_contract_hash"],
        "routes": routes,
        "exclusions": exclusions,
    }


def test_coverage_requires_every_exact_cell_once() -> None:
    contract = build_contract(BODY)
    coverage = _coverage(contract)
    validate_coverage(contract, coverage)
    coverage["routes"].pop()
    with pytest.raises(SpecContractError, match="missing cells"):
        validate_coverage(contract, coverage)


def test_coverage_rejects_stale_cell_hash() -> None:
    contract = build_contract(BODY)
    coverage = _coverage(contract)
    coverage["routes"][0]["cell_hash"] = "0" * 64
    with pytest.raises(SpecContractError, match="stale cell hash OBL-001"):
        validate_coverage(contract, coverage)


def test_coverage_keeps_exclusions_out_of_tickets() -> None:
    contract = build_contract(BODY)
    coverage = _coverage(contract)
    exclusion = coverage["exclusions"].pop()
    coverage["routes"].append({**exclusion, "destination": "T2"})
    with pytest.raises(SpecContractError, match="cannot route to a ticket"):
        validate_coverage(contract, coverage)
