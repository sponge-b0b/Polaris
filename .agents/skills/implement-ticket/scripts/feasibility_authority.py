from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.workflow_hashing import sha256_canonical_json  # noqa: E402

SCHEMA = "polaris.implement-feasibility/v1"
CONTRACT_SCHEMAS = {
    "polaris.ticket-contract/v1",
    "polaris.review-remediation-contract/v1",
}
_HEAD = re.compile(r"^[0-9a-f]{40}$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_CELL = re.compile(r"^[A-Z]+-[0-9]{3}$")

OWNERSHIP = {
    "PRESENT_UPSTREAM",
    "OWNED_BY_CURRENT_TICKET",
    "DEFERRED_COMPOSITION",
    "MISSING_UPSTREAM",
    "AMBIGUOUS_OWNER",
}
AUTHORITY = {
    "FIXED_UPSTREAM",
    "FIXED_IMPLEMENTATION_LOCAL",
    "FIXED_DEFERRED",
    "UNRESOLVED_MATERIAL_CHOICE",
}
EXPECTED_AUTHORITY = {
    "PRESENT_UPSTREAM": "FIXED_UPSTREAM",
    "OWNED_BY_CURRENT_TICKET": "FIXED_IMPLEMENTATION_LOCAL",
    "DEFERRED_COMPOSITION": "FIXED_DEFERRED",
}
BLOCKED_CLASSIFICATIONS = {
    "cell-routing-defect",
    "planning-cell-gap",
    "contract-authority-gap",
    "hard-blocker",
}
PRIOR_DISPOSITIONS = {
    "RESOLVED_UPSTREAM",
    "OWNED_BY_CURRENT_TICKET",
    "ROUTING_OR_PLANNING_GAP",
    "NO_LONGER_APPLICABLE",
    "AMBIGUOUS",
}


class FeasibilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeasibilityReceipt:
    ticket: int
    contract_schema: str
    contract_hash: str
    outcome: str
    seam_count: int
    evidence_count: int
    artifact_sha256: str


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise FeasibilityError(message)


def _str_list(value: Any, field: str, *, nonempty: bool = False) -> list[str]:
    _need(isinstance(value, list), f"feasibility: {field} must be a list")
    _need(
        all(isinstance(item, str) and item.strip() for item in value),
        f"feasibility: {field} contains invalid item",
    )
    _need(
        value == sorted(set(value)),
        f"feasibility: {field} must be sorted and unique",
    )
    if nonempty:
        _need(bool(value), f"feasibility: {field} must not be empty")
    return value


def validate_feasibility(value: dict[str, Any]) -> FeasibilityReceipt:
    _need(value.get("schema") == SCHEMA, f"feasibility: schema must be {SCHEMA}")
    _need(
        set(value)
        == {
            "schema",
            "ticket",
            "contract_schema",
            "contract_hash",
            "branch",
            "execution_head",
            "evidence_sources",
            "seams",
            "prior_findings",
            "outcome",
            "blocked",
        },
        "feasibility: unsupported top-level fields",
    )
    ticket = value.get("ticket")
    _need(isinstance(ticket, int) and ticket > 0, "feasibility: invalid ticket")
    contract_schema = value.get("contract_schema")
    _need(
        contract_schema in CONTRACT_SCHEMAS,
        "feasibility: unsupported contract schema",
    )
    assert isinstance(contract_schema, str)
    contract_hash = value.get("contract_hash")
    _need(
        isinstance(contract_hash, str) and _HASH.fullmatch(contract_hash) is not None,
        "feasibility: invalid contract hash",
    )
    branch = value.get("branch")
    _need(isinstance(branch, str) and branch.strip(), "feasibility: invalid branch")
    head = value.get("execution_head")
    _need(
        isinstance(head, str) and _HEAD.fullmatch(head) is not None,
        "feasibility: invalid execution head",
    )
    evidence = _str_list(
        value.get("evidence_sources"), "evidence_sources", nonempty=True
    )
    evidence_set = set(evidence)

    seams = value.get("seams")
    _need(
        isinstance(seams, list) and seams,
        "feasibility: seams must be a non-empty list",
    )
    seam_ids: set[str] = set()
    unresolved = False
    infeasible_ownership = False
    for row in seams:
        _need(isinstance(row, dict), "feasibility: invalid seam row")
        _need(
            set(row)
            == {
                "seam_id",
                "required_cells",
                "ownership_status",
                "authority_status",
                "authority_basis",
                "realization_basis",
            },
            "feasibility: unsupported seam fields",
        )
        seam_id = row.get("seam_id")
        _need(
            isinstance(seam_id, str) and seam_id.strip(),
            "feasibility: invalid seam_id",
        )
        _need(seam_id not in seam_ids, "feasibility: duplicate seam_id")
        seam_ids.add(seam_id)
        cells = _str_list(
            row.get("required_cells"), f"{seam_id}.required_cells", nonempty=True
        )
        _need(
            all(_CELL.fullmatch(cell) for cell in cells),
            f"feasibility: {seam_id} has invalid required cell",
        )
        ownership = row.get("ownership_status")
        authority = row.get("authority_status")
        _need(
            ownership in OWNERSHIP,
            f"feasibility: {seam_id} invalid ownership status",
        )
        _need(
            authority in AUTHORITY,
            f"feasibility: {seam_id} invalid authority status",
        )
        authority_basis = _str_list(
            row.get("authority_basis"), f"{seam_id}.authority_basis", nonempty=True
        )
        realization_basis = _str_list(
            row.get("realization_basis"),
            f"{seam_id}.realization_basis",
            nonempty=True,
        )
        _need(
            set(authority_basis) <= evidence_set,
            f"feasibility: {seam_id} authority basis missing from evidence_sources",
        )
        _need(
            set(realization_basis) <= evidence_set,
            f"feasibility: {seam_id} realization basis missing from evidence_sources",
        )
        if authority == "UNRESOLVED_MATERIAL_CHOICE":
            unresolved = True
        if ownership in {"MISSING_UPSTREAM", "AMBIGUOUS_OWNER"}:
            infeasible_ownership = True
        expected = EXPECTED_AUTHORITY.get(ownership)
        if expected is not None:
            _need(
                authority in {expected, "UNRESOLVED_MATERIAL_CHOICE"},
                f"feasibility: {seam_id} authority status does not match ownership status",
            )

    prior = value.get("prior_findings")
    _need(isinstance(prior, list), "feasibility: prior_findings must be a list")
    prior_ids: set[str] = set()
    prior_open = False
    for row in prior:
        _need(isinstance(row, dict), "feasibility: invalid prior finding row")
        _need(
            set(row) == {"finding_id", "disposition", "basis"},
            "feasibility: unsupported prior finding fields",
        )
        finding_id = row.get("finding_id")
        _need(
            isinstance(finding_id, str) and finding_id.strip(),
            "feasibility: invalid prior finding id",
        )
        _need(finding_id not in prior_ids, "feasibility: duplicate prior finding id")
        prior_ids.add(finding_id)
        disposition = row.get("disposition")
        _need(
            disposition in PRIOR_DISPOSITIONS,
            "feasibility: invalid prior finding disposition",
        )
        basis = _str_list(row.get("basis"), f"{finding_id}.basis", nonempty=True)
        _need(
            set(basis) <= evidence_set,
            f"feasibility: {finding_id} basis missing from evidence_sources",
        )
        if disposition in {"ROUTING_OR_PLANNING_GAP", "AMBIGUOUS"}:
            prior_open = True

    outcome = value.get("outcome")
    _need(
        outcome in {"PASS", "BLOCKED"},
        "feasibility: outcome must be PASS or BLOCKED",
    )
    blocked = value.get("blocked")
    if outcome == "PASS":
        _need(blocked is None, "feasibility: PASS must not contain blocked payload")
        _need(
            not unresolved,
            "feasibility: PASS forbidden with unresolved material authority choice",
        )
        _need(
            not infeasible_ownership,
            "feasibility: PASS forbidden with missing/ambiguous ownership",
        )
        _need(
            not prior_open,
            "feasibility: PASS forbidden with unresolved prior finding disposition",
        )
    else:
        _need(
            isinstance(blocked, dict),
            "feasibility: BLOCKED requires blocked payload",
        )
        _need(
            set(blocked)
            == {
                "classification",
                "seam_id",
                "required_cells",
                "durable_owner",
                "reason",
                "route",
            },
            "feasibility: unsupported blocked fields",
        )
        classification = blocked.get("classification")
        _need(
            classification in BLOCKED_CLASSIFICATIONS,
            "feasibility: invalid blocked classification",
        )
        _need(
            isinstance(blocked.get("reason"), str) and blocked["reason"].strip(),
            "feasibility: blocked reason required",
        )
        _need(
            isinstance(blocked.get("route"), str) and blocked["route"].strip(),
            "feasibility: blocked route required",
        )
        _need(
            isinstance(blocked.get("durable_owner"), str)
            and blocked["durable_owner"].strip(),
            "feasibility: blocked durable owner required",
        )
        seam_id = blocked.get("seam_id")
        _need(
            seam_id is None or seam_id in seam_ids,
            "feasibility: blocked seam_id must name a declared seam or null",
        )
        cells = _str_list(blocked.get("required_cells"), "blocked.required_cells")
        _need(
            all(_CELL.fullmatch(cell) for cell in cells),
            "feasibility: invalid blocked required cell",
        )
        if classification == "contract-authority-gap":
            _need(
                unresolved,
                "feasibility: contract-authority-gap requires an unresolved material authority seam",
            )

    return FeasibilityReceipt(
        ticket=ticket,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
        outcome=outcome,
        seam_count=len(seams),
        evidence_count=len(evidence),
        artifact_sha256=sha256_canonical_json(value),
    )


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _print(receipt: FeasibilityReceipt) -> None:
    print(f"IMPLEMENT TICKET FEASIBILITY: {receipt.outcome}")
    print(f"Ticket: #{receipt.ticket}")
    print(f"Contract Schema: {receipt.contract_schema}")
    print(f"Contract Hash: {receipt.contract_hash}")
    print(f"Required production seams: {receipt.seam_count}")
    print(f"Authority/realization evidence sources: {receipt.evidence_count}")
    print(f"Feasibility Artifact SHA-256: {receipt.artifact_sha256}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("feasibility", type=Path)
    args = parser.parse_args()
    try:
        receipt = validate_feasibility(_read(args.feasibility))
    except (FeasibilityError, json.JSONDecodeError, OSError, ValueError) as exc:
        parser.error(str(exc))
    _print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
