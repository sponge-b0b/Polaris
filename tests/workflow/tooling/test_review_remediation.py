from __future__ import annotations

import copy

import pytest

from scripts.review_remediation import (
    ReviewRemediationError,
    build_remediation_contract,
    validate_ledger,
    validate_ticket_body,
)

CONTRACT = {
    "spec_contract_hash": "spec-hash",
    "cells": [
        {
            "cell": "OBL-001",
            "kind": "material-contract",
            "cell_hash": "h-obl",
            "requirement": "Exact CCL assertions: x@1#a",
            "ccl": ["x@1#a"],
        },
        {
            "cell": "IMP-001",
            "kind": "implementation",
            "cell_hash": "h-imp",
            "requirement": "Use existing repository seam.",
            "ccl": [],
        },
        {
            "cell": "TEST-001",
            "kind": "testing",
            "cell_hash": "h-test",
            "requirement": "Prove negative behavior.",
            "ccl": [],
        },
        {
            "cell": "EXC-001",
            "kind": "exclusion",
            "cell_hash": "h-exc",
            "requirement": "Do not add public taxonomy.",
            "ccl": [],
        },
    ],
}

LEDGER = {
    "schema": "polaris.review-findings/v2",
    "spec": "#358",
    "spec_contract_hash": "spec-hash",
    "findings": [
        {
            "finding_id": "RF-1",
            "axis": "Spec",
            "severity": "Blocking",
            "classification": "implementation-defect",
            "cells": [{"cell": "OBL-001", "cell_hash": "h-obl"}],
            "standard_refs": [],
            "falsifier": "Withholding is persisted as a Recommendation.",
            "evidence": "Observed on current candidate.",
            "owner": "$to-tickets",
            "status": "open",
        },
        {
            "finding_id": "RF-2",
            "axis": "Standards",
            "severity": "Blocking",
            "classification": "standards-defect",
            "cells": [],
            "standard_refs": ["AGENTS.md#Coding-Conduct"],
            "falsifier": "Changed Python violates the applicable typing rule.",
            "evidence": "Current source violates the rule.",
            "owner": "$to-tickets",
            "status": "open",
        },
        {
            "finding_id": "RF-3",
            "axis": "Architecture",
            "severity": "Blocking",
            "classification": "contract-authority-gap",
            "cells": [],
            "standard_refs": [],
            "falsifier": "Required semantic behavior is absent from CCL.",
            "evidence": "Current authority proves a gap.",
            "owner": "$to-specs",
            "status": "open",
        },
    ],
}


def test_ledger_validates_exact_cell_hashes() -> None:
    checked = validate_ledger(CONTRACT, LEDGER)
    assert checked["findings"][0]["finding_hash"]
    stale = copy.deepcopy(LEDGER)
    stale["findings"][0]["cells"][0]["cell_hash"] = "stale"
    with pytest.raises(ReviewRemediationError, match="stale cell hash OBL-001"):
        validate_ledger(CONTRACT, stale)


def test_remediation_contract_uses_finding_not_root() -> None:
    value = build_remediation_contract(CONTRACT, LEDGER, ["RF-1"])
    assert value["schema"] == "polaris.review-remediation-contract/v1"
    assert [row["finding_id"] for row in value["findings"]] == ["RF-1"]
    assert [cell["cell"] for cell in value["affected_cells"]] == ["OBL-001"]
    assert [cell["cell"] for cell in value["preservation_guardrails"]] == [
        "IMP-001",
        "TEST-001",
        "EXC-001",
    ]


def test_standards_only_finding_is_valid_remediation() -> None:
    value = build_remediation_contract(CONTRACT, LEDGER, ["RF-2"])
    assert value["affected_cells"] == []
    assert len(value["preservation_guardrails"]) == 4


def test_gap_findings_cannot_become_remediation_contract() -> None:
    with pytest.raises(
        ReviewRemediationError,
        match="RF-3: not review-remediation owned",
    ):
        build_remediation_contract(CONTRACT, LEDGER, ["RF-3"])


def test_closed_finding_cannot_be_ticketed() -> None:
    ledger = copy.deepcopy(LEDGER)
    ledger["findings"][0]["status"] = "resolved"
    with pytest.raises(ReviewRemediationError, match="RF-1: not open"):
        build_remediation_contract(CONTRACT, ledger, ["RF-1"])


def test_falsifier_change_changes_contract_hash() -> None:
    first = build_remediation_contract(CONTRACT, LEDGER, ["RF-1"])
    ledger = copy.deepcopy(LEDGER)
    ledger["findings"][0]["falsifier"] = "Different exact falsifier."
    second = build_remediation_contract(CONTRACT, ledger, ["RF-1"])
    assert first["remediation_contract_hash"] != second["remediation_contract_hash"]


def test_unrelated_spec_cell_change_changes_preservation_contract() -> None:
    first = build_remediation_contract(CONTRACT, LEDGER, ["RF-1"])
    contract = copy.deepcopy(CONTRACT)
    contract["cells"][1]["cell_hash"] = "changed"
    contract["spec_contract_hash"] = "new-spec-hash"
    ledger = copy.deepcopy(LEDGER)
    ledger["spec_contract_hash"] = "new-spec-hash"
    second = build_remediation_contract(contract, ledger, ["RF-1"])
    assert first["remediation_contract_hash"] != second["remediation_contract_hash"]


def test_ticket_body_is_exact_projection() -> None:
    remediation = build_remediation_contract(CONTRACT, LEDGER, ["RF-1"])
    body = f"""Parent Spec: #358
Spec Contract Hash: spec-hash
Review Remediation Contract Hash: {remediation['remediation_contract_hash']}

## Review findings

- `RF-1` — implementation-defect — Withholding is persisted as a Recommendation.

## Contract cells

- `OBL-001` — exact CCL: `x@1#a`

## Preservation guardrails

- `IMP-001` — `h-imp`
- `TEST-001` — `h-test`
- `EXC-001` — `h-exc`
"""
    validate_ticket_body(body, remediation)
    with pytest.raises(ReviewRemediationError, match="Review findings do not match"):
        validate_ticket_body(body.replace("persisted", "stored"), remediation)
