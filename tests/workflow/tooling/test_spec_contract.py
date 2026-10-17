from __future__ import annotations

import pytest

from scripts.spec_contract import (
    SpecContractError,
    build_contract,
    build_execution_topology,
    derive_decomposition,
    validate_coverage,
    validate_decomposition,
    validate_execution_closure,
)

REF_PERSIST = "workflow-demo.recording@1#record.persistence"
REF_DISTINCT = "workflow-demo.recording@1#record.not-command"
R = "OBL-007 through OBL-009"

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

CLOSURE_BODY = f'''<!-- spec-contract-ccl:v1
{{
  "schema": "polaris.spec-ccl/v1",
  "obligations": [
    {{"obligation_id":"OBL-007","source_ref":"Decision #201","ccl":["demo@1#a"]}},
    {{"obligation_id":"OBL-008","source_ref":"Decision #201","ccl":["demo@1#b"]}},
    {{"obligation_id":"OBL-009","source_ref":"Decision #201","ccl":["demo@1#c"]}}
  ]
}}
-->

## Problem Statement
Synthetic execution-closure fixture.

## Canonical Contract Obligations
Generated elsewhere.

## Implementation Decisions
- `IMP-002` — Implement only the target-owner side of {R} against the shared boundary.

## Testing Decisions
- `TEST-007` — Prove OBL-009 exact-basis capture.

## Out of Scope
- `EXC-001` — Widening the synthetic contract.
'''

TOPOLOGY_BODY = '''<!-- spec-contract-ccl:v1
{
  "schema": "polaris.spec-ccl/v1",
  "obligations": [
    {"obligation_id":"OBL-001","source_ref":"Decision #201","ccl":["demo@1#a"]},
    {"obligation_id":"OBL-002","source_ref":"Decision #201","ccl":["demo@1#b"]},
    {"obligation_id":"OBL-003","source_ref":"Decision #201","ccl":["demo@1#c"]}
  ]
}
-->
<!-- spec-execution-topology:v1
{
  "schema": "polaris.spec-execution-topology/v1",
  "units": [
    {"unit_id":"EU-001","cells":["OBL-001","IMP-001","TEST-001"],"depends_on":[]},
    {
      "unit_id":"EU-002",
      "cells":["OBL-002","IMP-002","TEST-002"],
      "depends_on":["EU-001"]
    },
    {"unit_id":"EU-003","cells":["OBL-003","TEST-003"],"depends_on":["EU-002"]}
  ]
}
-->

## Problem Statement
Synthetic deterministic-decomposition fixture.

## Canonical Contract Obligations
Generated elsewhere.

## Implementation Decisions
- `IMP-001` — Implement OBL-001.
- `IMP-002` — Implement OBL-001 through OBL-002.

## Testing Decisions
- `TEST-001` — Prove OBL-001.
- `TEST-002` — Prove OBL-002.
- `TEST-003` — Prove OBL-003.

## Out of Scope
- `EXC-001` — Other work.
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


def _routed_coverage(contract: dict, routes: dict[str, str]) -> dict:
    value = _coverage(contract)
    for row in value["routes"]:
        row["destination"] = routes[row["cell"]]
    return value


def _dependencies(contract: dict, graph: dict[str, list[str]]) -> dict:
    return {
        "schema": "polaris.ticket-dependencies/v1",
        "spec_contract_hash": contract["spec_contract_hash"],
        "tickets": [
            {"destination": destination, "depends_on": depends_on}
            for destination, depends_on in graph.items()
        ],
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


def test_execution_closure_accepts_same_or_upstream_current_cell_references() -> None:
    contract = build_contract(CLOSURE_BODY)
    coverage = _routed_coverage(
        contract,
        {
            "OBL-007": "T1",
            "OBL-008": "T2",
            "OBL-009": "T2",
            "IMP-002": "T2",
            "TEST-007": "T3",
        },
    )
    dependencies = _dependencies(
        contract,
        {"T1": [], "T2": ["T1"], "T3": ["T2"]},
    )
    assert validate_execution_closure(contract, coverage, dependencies) == 4


def test_execution_closure_rejects_downstream_cell_hidden_inside_range() -> None:
    contract = build_contract(CLOSURE_BODY)
    coverage = _routed_coverage(
        contract,
        {
            "OBL-007": "T1",
            "OBL-008": "T2",
            "OBL-009": "T3",
            "IMP-002": "T2",
            "TEST-007": "T3",
        },
    )
    dependencies = _dependencies(
        contract,
        {"T1": [], "T2": ["T1"], "T3": ["T2"]},
    )
    with pytest.raises(
        SpecContractError,
        match=r"IMP-002 in T2 references OBL-009 in T3",
    ):
        validate_execution_closure(contract, coverage, dependencies)


def test_execution_closure_requires_dependency_plan_for_every_destination() -> None:
    contract = build_contract(CLOSURE_BODY)
    coverage = _routed_coverage(
        contract,
        {
            "OBL-007": "T1",
            "OBL-008": "T2",
            "OBL-009": "T2",
            "IMP-002": "T2",
            "TEST-007": "T3",
        },
    )
    dependencies = _dependencies(contract, {"T1": [], "T2": ["T1"]})
    with pytest.raises(
        SpecContractError,
        match="ticket set does not match coverage destinations",
    ):
        validate_execution_closure(contract, coverage, dependencies)


def test_execution_closure_rejects_dependency_cycle() -> None:
    contract = build_contract(CLOSURE_BODY)
    coverage = _routed_coverage(
        contract,
        {
            "OBL-007": "T1",
            "OBL-008": "T2",
            "OBL-009": "T2",
            "IMP-002": "T2",
            "TEST-007": "T3",
        },
    )
    dependencies = _dependencies(
        contract,
        {"T1": ["T3"], "T2": ["T1"], "T3": ["T2"]},
    )
    with pytest.raises(SpecContractError, match="cycle detected"):
        validate_execution_closure(contract, coverage, dependencies)


def test_decomposition_derives_each_atomic_unit_as_one_ticket() -> None:
    contract = build_contract(TOPOLOGY_BODY)
    topology, coverage, dependencies, checked = derive_decomposition(
        TOPOLOGY_BODY,
        contract,
    )
    assert [unit["unit_id"] for unit in topology["units"]] == [
        "EU-001",
        "EU-002",
        "EU-003",
    ]
    route = {row["cell"]: row["destination"] for row in coverage["routes"]}
    assert route["OBL-001"] == "T1"
    assert route["OBL-002"] == "T2"
    assert route["OBL-003"] == "T3"
    assert dependencies["tickets"] == [
        {"destination": "T1", "depends_on": []},
        {"destination": "T2", "depends_on": ["T1"]},
        {"destination": "T3", "depends_on": ["T2"]},
    ]
    assert checked >= 1


def test_decomposition_rejects_overmerged_valid_partition() -> None:
    contract = build_contract(TOPOLOGY_BODY)
    _, coverage, dependencies, _ = derive_decomposition(TOPOLOGY_BODY, contract)
    for row in coverage["routes"]:
        if row["destination"] == "T3":
            row["destination"] = "T2"
    dependencies["tickets"] = [
        {"destination": "T1", "depends_on": []},
        {"destination": "T2", "depends_on": ["T1"]},
    ]
    with pytest.raises(
        SpecContractError,
        match="coverage does not match atomic execution topology",
    ):
        validate_decomposition(TOPOLOGY_BODY, contract, coverage, dependencies)


def test_decomposition_rejects_split_atomic_unit() -> None:
    contract = build_contract(TOPOLOGY_BODY)
    _, coverage, dependencies, _ = derive_decomposition(TOPOLOGY_BODY, contract)
    for row in coverage["routes"]:
        if row["cell"] == "TEST-002":
            row["destination"] = "T9"
    dependencies["tickets"].append(
        {"destination": "T9", "depends_on": ["T1"]}
    )
    with pytest.raises(
        SpecContractError,
        match="coverage does not match atomic execution topology",
    ):
        validate_decomposition(TOPOLOGY_BODY, contract, coverage, dependencies)


def test_decomposition_fails_closed_without_topology() -> None:
    start = TOPOLOGY_BODY.index("<!-- spec-execution-topology:v1")
    end = TOPOLOGY_BODY.index("-->", start) + 3
    body = TOPOLOGY_BODY[:start] + TOPOLOGY_BODY[end:]
    contract = build_contract(body)
    with pytest.raises(
        SpecContractError,
        match="expected exactly one spec-execution-topology:v1 manifest",
    ):
        derive_decomposition(body, contract)


def test_topology_must_cover_every_executable_cell() -> None:
    changed = TOPOLOGY_BODY.replace(
        '"cells":["OBL-003","TEST-003"]',
        '"cells":["OBL-003"]',
    )
    contract = build_contract(changed)
    with pytest.raises(SpecContractError, match="missing executable cells TEST-003"):
        build_execution_topology(changed, contract)


def test_topology_unit_requires_material_obligation() -> None:
    changed = TOPOLOGY_BODY.replace(
        '{"unit_id":"EU-003","cells":["OBL-003","TEST-003"],"depends_on":["EU-002"]}',
        '{"unit_id":"EU-003","cells":["OBL-003"],"depends_on":["EU-002"]},'
        '{"unit_id":"EU-004","cells":["TEST-003"],"depends_on":["EU-003"]}',
    )
    contract = build_contract(changed)
    with pytest.raises(SpecContractError, match="requires at least one OBL"):
        build_execution_topology(changed, contract)


def test_topology_rejects_dependency_cycle() -> None:
    changed = TOPOLOGY_BODY.replace(
        '{"unit_id":"EU-001","cells":["OBL-001","IMP-001","TEST-001"],"depends_on":[]}',
        (
            '{"unit_id":"EU-001","cells":["OBL-001","IMP-001","TEST-001"],'
            '"depends_on":["EU-003"]}'
        ),
    )
    contract = build_contract(changed)
    with pytest.raises(SpecContractError, match="cycle detected"):
        build_execution_topology(changed, contract)


def test_topology_rejects_noncanonical_or_zero_unit_identity() -> None:
    for invalid in ("EU-000", "EU-0001", "EU-1"):
        changed = TOPOLOGY_BODY.replace("EU-001", invalid)
        contract = build_contract(changed)
        with pytest.raises(SpecContractError, match="unit_id: invalid|EU-000"):
            build_execution_topology(changed, contract)


def test_topology_rejects_invalid_dependency_identity_cleanly() -> None:
    changed = TOPOLOGY_BODY.replace(
        '"depends_on":["EU-001"]',
        '"depends_on":["not-a-unit"]',
        1,
    )
    contract = build_contract(changed)
    with pytest.raises(SpecContractError, match="invalid unit id not-a-unit"):
        build_execution_topology(changed, contract)


def test_topology_change_preserves_material_contract_hash() -> None:
    contract = build_contract(TOPOLOGY_BODY)
    first = build_execution_topology(TOPOLOGY_BODY, contract)
    changed = TOPOLOGY_BODY.replace(
        '{"unit_id":"EU-003","cells":["OBL-003","TEST-003"],"depends_on":["EU-002"]}',
        '{"unit_id":"EU-003","cells":["OBL-003","TEST-003"],"depends_on":["EU-001"]}',
    )
    revised_contract = build_contract(changed)
    revised = build_execution_topology(changed, revised_contract)
    assert contract["spec_contract_hash"] == revised_contract["spec_contract_hash"]
    assert contract["spec_body_hash"] != revised_contract["spec_body_hash"]
    assert first["topology_hash"] != revised["topology_hash"]


def test_topology_still_enforces_plan_cell_execution_closure() -> None:
    changed = TOPOLOGY_BODY.replace(
        "- `IMP-002` — Implement OBL-001 through OBL-002.",
        "- `IMP-002` — Implement OBL-001 through OBL-003.",
    )
    contract = build_contract(changed)
    with pytest.raises(
        SpecContractError,
        match=r"IMP-002 in T2 references OBL-003 in T3",
    ):
        derive_decomposition(changed, contract)
