from __future__ import annotations

import pytest

from scripts.spec_contract import (
    SpecContractError,
    build_contract,
    build_ticket_contract,
    validate_ticket_body,
)
from tests.workflow.tooling.test_spec_contract import (
    BODY,
    REF_DISTINCT,
    REF_PERSIST,
    _coverage,
)


def _ticket_body(contract_hash: str) -> str:
    return f'''Parent Spec: #358
Spec branch: spec-358
Ticket baseline: Pending
Spec Contract Hash: {contract_hash}

## Contract cells

- `OBL-001` — exact CCL: `{REF_PERSIST}`, `{REF_DISTINCT}`
- `IMP-001` — Persist through the established repository seam.
- `TEST-001` — Prove withholding is distinct from a Recommendation.

## Acceptance

Implement the assigned cells without changing their semantics.
'''


def test_ticket_contract_is_exact_route_plus_parent_exclusions() -> None:
    contract = build_contract(BODY)
    coverage = _coverage(contract)
    ticket = build_ticket_contract(contract, coverage, "T1")
    assert [cell["cell"] for cell in ticket["assigned_cells"]] == [
        "OBL-001",
        "IMP-001",
        "TEST-001",
    ]
    assert [cell["cell"] for cell in ticket["exclusion_guardrails"]] == ["EXC-001"]
    validate_ticket_body(_ticket_body(contract["spec_contract_hash"]), ticket)


def test_ticket_contract_hash_changes_when_assigned_cell_changes() -> None:
    contract = build_contract(BODY)
    coverage = _coverage(contract)
    first = build_ticket_contract(contract, coverage, "T1")
    changed = build_contract(BODY.replace("established repository seam", "new seam"))
    changed_coverage = _coverage(changed)
    second = build_ticket_contract(changed, changed_coverage, "T1")
    assert first["ticket_contract_hash"] != second["ticket_contract_hash"]


def test_ticket_contract_hash_changes_when_exclusion_changes() -> None:
    contract = build_contract(BODY)
    first = build_ticket_contract(contract, _coverage(contract), "T1")
    changed = build_contract(
        BODY.replace("public withholding-reason taxonomy", "closed reason taxonomy")
    )
    second = build_ticket_contract(changed, _coverage(changed), "T1")
    assert first["ticket_contract_hash"] != second["ticket_contract_hash"]


def test_ticket_body_rejects_stale_spec_hash() -> None:
    contract = build_contract(BODY)
    ticket = build_ticket_contract(contract, _coverage(contract), "T1")
    with pytest.raises(SpecContractError, match="stale Spec Contract Hash"):
        validate_ticket_body(_ticket_body("0" * 64), ticket)


def test_ticket_body_rejects_missing_assigned_cell() -> None:
    contract = build_contract(BODY)
    ticket = build_ticket_contract(contract, _coverage(contract), "T1")
    body = _ticket_body(contract["spec_contract_hash"]).replace(
        "- `TEST-001` — Prove withholding is distinct from a Recommendation.\n", ""
    )
    with pytest.raises(SpecContractError, match="Contract cells do not match"):
        validate_ticket_body(body, ticket)


def test_ticket_contract_rejects_unknown_destination() -> None:
    contract = build_contract(BODY)
    with pytest.raises(SpecContractError, match="no cells routed"):
        build_ticket_contract(contract, _coverage(contract), "#999")
