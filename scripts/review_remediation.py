"""Validate review finding ledgers and build deterministic remediation contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

_REMEDIATION_DOMAIN = b"POLARIS-REVIEW-REMEDIATION-V1\0"
_FINDING_DOMAIN = b"POLARIS-REVIEW-FINDING-V2\0"
_RF_ID = re.compile(r"^RF-[0-9]+$")
_ALLOWED_AXIS = {"Standards", "Spec", "Architecture"}
_ALLOWED_CLASS = {
    "implementation-defect",
    "standards-defect",
    "test/proof-defect",
    "cell-routing-defect",
    "contract-authority-gap",
    "planning-cell-gap",
}
_REMEDIATION_CLASS = {
    "implementation-defect",
    "standards-defect",
    "test/proof-defect",
}
_ALLOWED_STATUS = {"open", "resolved", "owner-overridden", "scope-retired"}


class ReviewRemediationError(ValueError):
    """Raised when review remediation state is invalid."""


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise ReviewRemediationError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(value: Any, domain: bytes) -> str:
    return hashlib.sha256(domain + _canonical(value)).hexdigest()


def _cell_index(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cells = contract.get("cells")
    _need(isinstance(cells, list), "spec contract: cells must be a list")
    index: dict[str, dict[str, Any]] = {}
    for cell in cells:
        _need(isinstance(cell, dict), "spec contract: invalid cell row")
        cell_id = cell.get("cell")
        _need(isinstance(cell_id, str) and cell_id, "spec contract: cell missing id")
        _need(cell_id not in index, f"spec contract: duplicate cell {cell_id}")
        index[cell_id] = cell
    return index


def _semantic_finding(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": row["finding_id"],
        "axis": row["axis"],
        "severity": row["severity"],
        "classification": row["classification"],
        "cells": row["cells"],
        "standard_refs": row["standard_refs"],
        "falsifier": row["falsifier"],
    }


def validate_ledger(
    contract: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    """Validate one v2 finding ledger against the exact current Spec contract."""
    _need(
        ledger.get("schema") == "polaris.review-findings/v2",
        "finding ledger: wrong schema",
    )
    _need(
        ledger.get("spec_contract_hash") == contract.get("spec_contract_hash"),
        "finding ledger: stale Spec Contract Hash",
    )
    findings = ledger.get("findings")
    _need(isinstance(findings, list), "finding ledger: findings must be a list")
    cells = _cell_index(contract)
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []

    for row in findings:
        _need(isinstance(row, dict), "finding ledger: invalid finding row")
        required = {
            "finding_id",
            "axis",
            "severity",
            "classification",
            "cells",
            "standard_refs",
            "falsifier",
            "evidence",
            "owner",
            "status",
        }
        _need(set(row) == required, "finding ledger: unsupported finding fields")
        finding_id = row["finding_id"]
        _need(
            isinstance(finding_id, str) and _RF_ID.fullmatch(finding_id) is not None,
            "finding ledger: invalid finding_id",
        )
        _need(finding_id not in seen, f"finding ledger: duplicate {finding_id}")
        seen.add(finding_id)
        _need(row["axis"] in _ALLOWED_AXIS, f"{finding_id}: invalid axis")
        _need(
            row["severity"] in {"Blocking", "Advisory"},
            f"{finding_id}: invalid severity",
        )
        _need(
            row["classification"] in _ALLOWED_CLASS,
            f"{finding_id}: invalid classification",
        )
        _need(row["status"] in _ALLOWED_STATUS, f"{finding_id}: invalid status")
        _need(
            isinstance(row["falsifier"], str) and row["falsifier"].strip(),
            f"{finding_id}: missing falsifier",
        )
        _need(
            isinstance(row["evidence"], str) and row["evidence"].strip(),
            f"{finding_id}: missing evidence",
        )
        _need(
            isinstance(row["owner"], str) and row["owner"].strip(),
            f"{finding_id}: missing owner",
        )
        refs = row["standard_refs"]
        _need(
            isinstance(refs, list)
            and all(isinstance(ref, str) and ref.strip() for ref in refs),
            f"{finding_id}: invalid standard_refs",
        )
        _need(len(refs) == len(set(refs)), f"{finding_id}: duplicate standard_refs")

        finding_cells = row["cells"]
        _need(isinstance(finding_cells, list), f"{finding_id}: cells must be a list")
        cell_ids: set[str] = set()
        for cell_ref in finding_cells:
            _need(
                isinstance(cell_ref, dict)
                and set(cell_ref) == {"cell", "cell_hash"},
                f"{finding_id}: invalid cell reference",
            )
            cell_id = cell_ref["cell"]
            _need(cell_id in cells, f"{finding_id}: unknown cell {cell_id}")
            _need(cell_id not in cell_ids, f"{finding_id}: duplicate cell {cell_id}")
            cell_ids.add(cell_id)
            _need(
                cell_ref["cell_hash"] == cells[cell_id].get("cell_hash"),
                f"{finding_id}: stale cell hash {cell_id}",
            )

        if row["classification"] in {"implementation-defect", "test/proof-defect"}:
            _need(finding_cells, f"{finding_id}: remediation defect requires cells")
        if row["classification"] == "standards-defect":
            _need(
                bool(finding_cells) or bool(refs),
                f"{finding_id}: standards defect needs cells or standard_refs",
            )

        semantic = _semantic_finding(row)
        out = dict(row)
        out["finding_hash"] = _sha(semantic, _FINDING_DOMAIN)
        normalized.append(out)

    return {
        "schema": ledger["schema"],
        "spec": ledger.get("spec"),
        "spec_contract_hash": ledger["spec_contract_hash"],
        "findings": normalized,
    }


def build_remediation_contract(
    contract: dict[str, Any],
    ledger: dict[str, Any],
    finding_ids: list[str],
) -> dict[str, Any]:
    """Build one deterministic review-remediation contract."""
    checked = validate_ledger(contract, ledger)
    _need(bool(finding_ids), "remediation: no findings selected")
    _need(
        len(finding_ids) == len(set(finding_ids)),
        "remediation: duplicate finding ID",
    )
    by_id = {row["finding_id"]: row for row in checked["findings"]}
    selected: list[dict[str, Any]] = []
    affected_ids: set[str] = set()

    for finding_id in finding_ids:
        _need(finding_id in by_id, f"remediation: unknown finding {finding_id}")
        row = by_id[finding_id]
        _need(row["severity"] == "Blocking", f"{finding_id}: not Blocking")
        _need(row["status"] == "open", f"{finding_id}: not open")
        _need(
            row["classification"] in _REMEDIATION_CLASS,
            f"{finding_id}: not review-remediation owned",
        )
        selected.append(row)
        affected_ids.update(ref["cell"] for ref in row["cells"])

    cells = _cell_index(contract)
    affected = [cell for cell in contract["cells"] if cell["cell"] in affected_ids]
    preservation = [
        cell for cell in contract["cells"] if cell["cell"] not in affected_ids
    ]
    semantic_findings = [
        {
            "finding_id": row["finding_id"],
            "finding_hash": row["finding_hash"],
            "axis": row["axis"],
            "classification": row["classification"],
            "cells": row["cells"],
            "standard_refs": row["standard_refs"],
            "falsifier": row["falsifier"],
        }
        for row in selected
    ]
    identity = {
        "spec_contract_hash": contract["spec_contract_hash"],
        "findings": [
            [row["finding_id"], row["finding_hash"]] for row in semantic_findings
        ],
        "affected": [[cell["cell"], cell["cell_hash"]] for cell in affected],
        "preservation": [
            [cell["cell"], cell["cell_hash"]] for cell in preservation
        ],
    }
    return {
        "schema": "polaris.review-remediation-contract/v1",
        "spec_contract_hash": contract["spec_contract_hash"],
        "remediation_contract_hash": _sha(identity, _REMEDIATION_DOMAIN),
        "findings": semantic_findings,
        "affected_cells": affected,
        "preservation_guardrails": preservation,
    }


def _section(body: str, title: str) -> str:
    heading = re.search(rf"(?m)^##\s+{re.escape(title)}\s*$", body)
    _need(heading is not None, f"ticket body: missing ## {title}")
    assert heading is not None
    tail = body[heading.end() :]
    next_heading = re.search(r"(?m)^##\s+", tail)
    end = next_heading.start() if next_heading else len(tail)
    return tail[:end].strip()


def _finding_ids_from_body(body: str) -> list[str]:
    section = _section(body, "Review findings")
    matches = re.findall(r"(?m)^- `(RF-[0-9]+)`(?:\s+—.*)?$", section)
    _need(matches, "ticket body: no Review findings")
    lines = [line for line in section.splitlines() if line.strip()]
    _need(
        len(lines) == len(matches),
        "ticket body: unsupported Review findings row",
    )
    return matches


def _cell_line(cell: dict[str, Any]) -> str:
    if cell["kind"] == "material-contract":
        refs = ", ".join(f"`{ref}`" for ref in cell["ccl"])
        return f"- `{cell['cell']}` — exact CCL: {refs}"
    return f"- `{cell['cell']}` — {cell['requirement']}"


def validate_ticket_body(
    body: str,
    remediation: dict[str, Any],
) -> None:
    hashes = re.findall(
        r"(?m)^Review Remediation Contract Hash:\s*(\S+)\s*$",
        body,
    )
    _need(len(hashes) == 1, "ticket body: expected one remediation contract hash")
    _need(
        hashes[0] == remediation["remediation_contract_hash"],
        "ticket body: stale remediation contract hash",
    )
    spec_hashes = re.findall(r"(?m)^Spec Contract Hash:\s*(\S+)\s*$", body)
    _need(len(spec_hashes) == 1, "ticket body: expected one Spec Contract Hash")
    _need(
        spec_hashes[0] == remediation["spec_contract_hash"],
        "ticket body: stale Spec Contract Hash",
    )

    finding_section = _section(body, "Review findings")
    actual_findings = [
        line.strip() for line in finding_section.splitlines() if line.strip()
    ]
    expected_findings = [
        (
            f"- `{row['finding_id']}` — {row['classification']} — "
            f"{row['falsifier']}"
        )
        for row in remediation["findings"]
    ]
    _need(
        actual_findings == expected_findings,
        "ticket body: Review findings do not match remediation contract",
    )

    affected_section = _section(body, "Contract cells")
    actual_cells = [
        line.strip() for line in affected_section.splitlines() if line.strip()
    ]
    expected_cells = [_cell_line(cell) for cell in remediation["affected_cells"]]
    if not expected_cells:
        expected_cells = ["None."]
    _need(
        actual_cells == expected_cells,
        "ticket body: Contract cells do not match remediation contract",
    )

    preservation_section = _section(body, "Preservation guardrails")
    actual_preservation = [
        line.strip() for line in preservation_section.splitlines() if line.strip()
    ]
    expected_preservation = [
        f"- `{cell['cell']}` — `{cell['cell_hash']}`"
        for cell in remediation["preservation_guardrails"]
    ]
    if not expected_preservation:
        expected_preservation = ["None."]
    _need(
        actual_preservation == expected_preservation,
        "ticket body: Preservation guardrails do not match remediation contract",
    )


def _read_json(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _write(path: str, value: dict[str, Any]) -> None:
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-ledger")
    validate.add_argument("spec_contract")
    validate.add_argument("ledger")

    build = sub.add_parser("build")
    build.add_argument("spec_contract")
    build.add_argument("ledger")
    build.add_argument("finding_ids")
    build.add_argument("output")

    ticket = sub.add_parser("validate-ticket")
    ticket.add_argument("spec_contract")
    ticket.add_argument("ledger")
    ticket.add_argument("ticket_body")
    ticket.add_argument("output")

    args = parser.parse_args()
    try:
        contract = _read_json(args.spec_contract)
        ledger = _read_json(args.ledger)
        if args.command == "validate-ledger":
            checked = validate_ledger(contract, ledger)
            print("REVIEW FINDING LEDGER: VALID")
            print(f"Findings: {len(checked['findings'])}")
            return 0
        if args.command == "build":
            finding_ids = [
                part.strip()
                for part in args.finding_ids.split(",")
                if part.strip()
            ]
            remediation = build_remediation_contract(contract, ledger, finding_ids)
            _write(args.output, remediation)
            print("REVIEW REMEDIATION CONTRACT: VALID")
            print(
                "Review Remediation Contract Hash: "
                + remediation["remediation_contract_hash"]
            )
            return 0
        body = Path(args.ticket_body).read_text(encoding="utf-8")
        finding_ids = _finding_ids_from_body(body)
        remediation = build_remediation_contract(contract, ledger, finding_ids)
        validate_ticket_body(body, remediation)
        _write(args.output, remediation)
        print("REVIEW REMEDIATION CONTRACT: VALID")
        print(
            "Review Remediation Contract Hash: "
            + remediation["remediation_contract_hash"]
        )
        return 0
    except (ReviewRemediationError, json.JSONDecodeError, OSError) as exc:
        print(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())