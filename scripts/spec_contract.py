"""Build deterministic Spec and ticket contracts from one CCL-backed Polaris Spec."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

_CCL_MARKER = "spec-contract-ccl:v1"
_CONTRACT_DOMAIN = b"POLARIS-SPEC-CONTRACT-V3\0"
_CELL_DOMAIN = b"POLARIS-SPEC-CELL-V1\0"
_TICKET_DOMAIN = b"POLARIS-TICKET-CONTRACT-V1\0"
_OBL_ID = re.compile(r"^OBL-[0-9]{3,}$")
_PLAN_ITEM = re.compile(
    r"^- `(?P<id>(?P<prefix>IMP|TEST|EXC)-[0-9]{3,})` — (?P<text>\S(?:.*\S)?)$"
)


class SpecContractError(ValueError):
    """Raised when a Spec cannot produce one deterministic contract."""


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise SpecContractError(message)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _extract_ccl_manifest(body: str) -> dict[str, Any]:
    pattern = re.compile(
        rf"<!--\s*{re.escape(_CCL_MARKER)}\s*\n(?P<payload>.*?)\n-->",
        re.DOTALL,
    )
    matches = list(pattern.finditer(body))
    _need(len(matches) == 1, f"Spec: expected exactly one {_CCL_MARKER} manifest")
    try:
        manifest = json.loads(matches[0].group("payload"))
    except json.JSONDecodeError as exc:
        raise SpecContractError(f"Spec CCL manifest: invalid JSON: {exc}") from exc
    _need(isinstance(manifest, dict), "Spec CCL manifest: expected object")
    _need(
        manifest.get("schema") == "polaris.spec-ccl/v1",
        "Spec CCL manifest: wrong schema",
    )
    obligations = manifest.get("obligations")
    _need(
        isinstance(obligations, list) and obligations,
        "Spec CCL manifest: no obligations",
    )
    return manifest


def _section(body: str, title: str) -> str:
    heading = re.search(rf"(?m)^##\s+{re.escape(title)}\s*$", body)
    _need(heading is not None, f"Spec: missing ## {title}")
    assert heading is not None
    tail = body[heading.end() :]
    next_heading = re.search(r"(?m)^##\s+", tail)
    end = next_heading.start() if next_heading else len(tail)
    return tail[:end].strip()


def _plan_cells(
    body: str,
    section: str,
    prefix: str,
    kind: str,
) -> list[dict[str, Any]]:
    content = _section(body, section)
    if content == "None.":
        return []
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    _need(lines, f"Spec: ## {section} must contain stable-ID bullets or None.")
    cells: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        match = _PLAN_ITEM.fullmatch(line)
        _need(match is not None, f"Spec: invalid ## {section} row: {line}")
        assert match is not None
        _need(
            match.group("prefix") == prefix,
            f"Spec: ## {section} requires {prefix}-* IDs",
        )
        cell_id = match.group("id")
        _need(cell_id not in seen, f"Spec: duplicate contract cell {cell_id}")
        seen.add(cell_id)
        text = match.group("text")
        cells.append(
            {
                "cell": cell_id,
                "kind": kind,
                "source": f"{section} / {cell_id}",
                "requirement": text,
                "ccl": [],
            }
        )
    return cells


def _material_cells(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, obligation in enumerate(manifest["obligations"]):
        where = f"Spec CCL manifest obligation {index}"
        _need(isinstance(obligation, dict), f"{where}: expected object")
        cell_id = obligation.get("obligation_id")
        _need(
            isinstance(cell_id, str) and _OBL_ID.fullmatch(cell_id) is not None,
            f"{where}: invalid obligation_id",
        )
        _need(cell_id not in seen, f"Spec: duplicate contract cell {cell_id}")
        seen.add(cell_id)
        source_ref = obligation.get("source_ref")
        refs = obligation.get("ccl")
        _need(
            isinstance(source_ref, str) and source_ref.strip(),
            f"{where}: invalid source_ref",
        )
        _need(
            isinstance(refs, list)
            and refs
            and all(isinstance(ref, str) and ref for ref in refs),
            f"{where}: invalid ccl",
        )
        _need(len(refs) == len(set(refs)), f"{where}: duplicate ccl reference")
        cells.append(
            {
                "cell": cell_id,
                "kind": "material-contract",
                "source": f"Canonical Contract Obligations / {cell_id}",
                "requirement": "Exact CCL assertions: " + ", ".join(refs),
                "ccl": refs,
                "planning_source": source_ref,
            }
        )
    return cells


def _cell_hash(cell: dict[str, Any]) -> str:
    if cell["kind"] == "material-contract":
        semantic = {
            "cell": cell["cell"],
            "kind": cell["kind"],
            "ccl": cell["ccl"],
        }
    else:
        semantic = {
            "cell": cell["cell"],
            "kind": cell["kind"],
            "requirement": cell["requirement"],
        }
    return _sha256_bytes(_CELL_DOMAIN + _canonical(semantic))


def build_cells(body: str) -> list[dict[str, Any]]:
    manifest = _extract_ccl_manifest(body)
    cells = _material_cells(manifest)
    cells.extend(_plan_cells(body, "Implementation Decisions", "IMP", "implementation"))
    cells.extend(_plan_cells(body, "Testing Decisions", "TEST", "testing"))
    cells.extend(_plan_cells(body, "Out of Scope", "EXC", "exclusion"))
    ids = [cell["cell"] for cell in cells]
    _need(len(ids) == len(set(ids)), "Spec: duplicate contract cell ID across sections")
    for cell in cells:
        cell["cell_hash"] = _cell_hash(cell)
    return cells


def build_contract(body: str) -> dict[str, Any]:
    cells = build_cells(body)
    body_hash = _sha256_bytes(body.encode("utf-8"))
    identity_rows = [[cell["cell"], cell["kind"], cell["cell_hash"]] for cell in cells]
    contract_hash = _sha256_bytes(_CONTRACT_DOMAIN + _canonical(identity_rows))
    return {
        "schema": "polaris.spec-contract/v1",
        "spec_body_hash": body_hash,
        "spec_contract_hash": contract_hash,
        "cells": cells,
    }


def validate_coverage(contract: dict[str, Any], coverage: dict[str, Any]) -> None:
    """Validate exhaustive deterministic ticket coverage for one Spec contract."""
    _need(
        contract.get("schema") == "polaris.spec-contract/v1",
        "contract: wrong schema",
    )
    _need(
        coverage.get("schema") == "polaris.ticket-coverage/v2",
        "coverage: wrong schema",
    )
    _need(
        coverage.get("spec_contract_hash") == contract.get("spec_contract_hash"),
        "coverage: stale spec contract hash",
    )
    cells = {cell["cell"]: cell for cell in contract["cells"]}
    routes = coverage.get("routes")
    exclusions = coverage.get("exclusions")
    _need(isinstance(routes, list), "coverage.routes: expected list")
    _need(isinstance(exclusions, list), "coverage.exclusions: expected list")
    seen: set[str] = set()
    for row in routes:
        _need(isinstance(row, dict), "coverage.routes: invalid row")
        _need(
            set(row) == {"cell", "cell_hash", "destination"},
            "coverage.routes: unsupported row",
        )
        cell_id = row["cell"]
        _need(cell_id in cells, f"coverage.routes: unknown cell {cell_id}")
        cell = cells[cell_id]
        _need(
            cell["kind"] != "exclusion",
            f"coverage.routes: exclusion {cell_id} cannot route to a ticket",
        )
        _need(cell_id not in seen, f"coverage: duplicate cell {cell_id}")
        _need(
            row["cell_hash"] == cell["cell_hash"],
            f"coverage: stale cell hash {cell_id}",
        )
        _need(
            isinstance(row["destination"], str) and row["destination"].strip(),
            f"coverage.routes: missing destination for {cell_id}",
        )
        seen.add(cell_id)
    for row in exclusions:
        _need(isinstance(row, dict), "coverage.exclusions: invalid row")
        _need(
            set(row) == {"cell", "cell_hash"},
            "coverage.exclusions: unsupported row",
        )
        cell_id = row["cell"]
        _need(cell_id in cells, f"coverage.exclusions: unknown cell {cell_id}")
        cell = cells[cell_id]
        _need(
            cell["kind"] == "exclusion",
            f"coverage.exclusions: non-exclusion {cell_id}",
        )
        _need(cell_id not in seen, f"coverage: duplicate cell {cell_id}")
        _need(
            row["cell_hash"] == cell["cell_hash"],
            f"coverage: stale cell hash {cell_id}",
        )
        seen.add(cell_id)
    missing = set(cells) - seen
    _need(not missing, "coverage: missing cells " + ", ".join(sorted(missing)))


def build_ticket_contract(
    contract: dict[str, Any],
    coverage: dict[str, Any],
    destination: str,
) -> dict[str, Any]:
    """Build one deterministic ordinary-ticket contract from Spec coverage."""
    _need(
        isinstance(destination, str) and destination.strip(),
        "ticket: missing destination",
    )
    validate_coverage(contract, coverage)
    cells = {cell["cell"]: cell for cell in contract["cells"]}
    assigned_ids = [
        row["cell"]
        for row in coverage["routes"]
        if row["destination"] == destination
    ]
    _need(assigned_ids, f"ticket: no cells routed to {destination}")
    assigned = [cells[cell_id] for cell_id in assigned_ids]
    exclusions = [cell for cell in contract["cells"] if cell["kind"] == "exclusion"]
    identity = {
        "spec_contract_hash": contract["spec_contract_hash"],
        "destination": destination,
        "assigned": [[cell["cell"], cell["cell_hash"]] for cell in assigned],
        "exclusions": [[cell["cell"], cell["cell_hash"]] for cell in exclusions],
    }
    return {
        "schema": "polaris.ticket-contract/v1",
        "spec_contract_hash": contract["spec_contract_hash"],
        "destination": destination,
        "ticket_contract_hash": _sha256_bytes(_TICKET_DOMAIN + _canonical(identity)),
        "assigned_cells": assigned,
        "exclusion_guardrails": exclusions,
    }


def _ticket_contract_lines(ticket_contract: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for cell in ticket_contract["assigned_cells"]:
        cell_id = cell["cell"]
        if cell["kind"] == "material-contract":
            refs = ", ".join(f"`{ref}`" for ref in cell["ccl"])
            lines.append(f"- `{cell_id}` — exact CCL: {refs}")
        else:
            lines.append(f"- `{cell_id}` — {cell['requirement']}")
    return lines


def validate_ticket_body(body: str, ticket_contract: dict[str, Any]) -> None:
    """Require a published ticket body to be an exact projection of its route."""
    hashes = re.findall(r"(?m)^Spec Contract Hash:\s*(\S+)\s*$", body)
    _need(len(hashes) == 1, "ticket body: expected one Spec Contract Hash")
    _need(
        hashes[0] == ticket_contract["spec_contract_hash"],
        "ticket body: stale Spec Contract Hash",
    )
    section = _section(body, "Contract cells")
    actual = [line.strip() for line in section.splitlines() if line.strip()]
    expected = _ticket_contract_lines(ticket_contract)
    _need(
        actual == expected,
        "ticket body: Contract cells do not match routed contract",
    )


def _load_issue_body(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(
        isinstance(value, dict) and isinstance(value.get("body"), str),
        "issue JSON: missing body",
    )
    return value["body"]


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("issue_json")
    build.add_argument("output")
    validate = sub.add_parser("validate")
    validate.add_argument("issue_json")
    validate.add_argument("expected")
    coverage = sub.add_parser("check-coverage")
    coverage.add_argument("contract")
    coverage.add_argument("coverage")
    ticket = sub.add_parser("build-ticket")
    ticket.add_argument("contract")
    ticket.add_argument("coverage")
    ticket.add_argument("destination")
    ticket.add_argument("ticket_body")
    ticket.add_argument("output")
    check_ticket = sub.add_parser("check-ticket")
    check_ticket.add_argument("contract")
    check_ticket.add_argument("coverage")
    check_ticket.add_argument("destination")
    check_ticket.add_argument("ticket_body")
    args = parser.parse_args()
    try:
        if args.command in {"check-coverage", "build-ticket", "check-ticket"}:
            contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
            coverage_value = json.loads(Path(args.coverage).read_text(encoding="utf-8"))
            _need(isinstance(contract, dict), "contract: expected object")
            _need(isinstance(coverage_value, dict), "coverage: expected object")
            if args.command == "check-coverage":
                validate_coverage(contract, coverage_value)
                print("TICKET COVERAGE: VALID")
                return 0
            ticket_contract = build_ticket_contract(
                contract, coverage_value, args.destination
            )
            ticket_body = Path(args.ticket_body).read_text(encoding="utf-8")
            validate_ticket_body(ticket_body, ticket_contract)
            if args.command == "build-ticket":
                _write(Path(args.output), ticket_contract)
            print("TICKET CONTRACT: VALID")
            print(f"Ticket Contract Hash: {ticket_contract['ticket_contract_hash']}")
            print(f"Assigned cells: {len(ticket_contract['assigned_cells'])}")
            print(
                "Exclusion guardrails: "
                f"{len(ticket_contract['exclusion_guardrails'])}"
            )
            return 0
        current = build_contract(_load_issue_body(Path(args.issue_json)))
        if args.command == "build":
            _write(Path(args.output), current)
            print("SPEC CONTRACT: VALID")
            print("Semantic prose classification performed: 0")
            print(f"Spec Body Hash: {current['spec_body_hash']}")
            print(f"Spec Contract Hash: {current['spec_contract_hash']}")
        else:
            expected = json.loads(Path(args.expected).read_text(encoding="utf-8"))
            _need(isinstance(expected, dict), "expected contract: expected object")
            _need(
                expected.get("spec_body_hash") == current["spec_body_hash"],
                "SPEC CONTRACT: STALE body hash",
            )
            _need(
                expected.get("spec_contract_hash") == current["spec_contract_hash"],
                "SPEC CONTRACT: STALE contract hash",
            )
            _need(
                expected.get("cells") == current["cells"],
                "SPEC CONTRACT: STALE cell universe",
            )
            print("SPEC CONTRACT: VALID")
            print("Semantic prose classification performed: 0")
    except (SpecContractError, json.JSONDecodeError, OSError) as exc:
        print(exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
