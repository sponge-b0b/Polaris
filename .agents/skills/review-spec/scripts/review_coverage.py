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

SCHEMA = "polaris.review-coverage/v1"
_HEAD = re.compile(r"^[0-9a-f]{40}$")
_FINDING = re.compile(r"^RF-[0-9]+$")
_SURFACE_ID = re.compile(r"^S[1-9][0-9]*$")
_PROBE_ID = re.compile(r"^P[1-9][0-9]*$")
_ALLOWED_ROLES = frozenset({"production", "proof", "composition", "authority"})
_ALLOWED_STATUS = frozenset({"covered", "not-applicable"})
_REQUIRED_LENSES = {
    "material-contract": ("positive", "negative", "composition", "proof"),
    "implementation": ("implementation", "composition", "proof"),
    "testing": ("proof", "negative"),
    "exclusion": ("exclusion",),
}


class ReviewCoverageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReviewCoverageReceipt:
    reviewed_head: str
    spec_contract_hash: str
    reviewed_cells: int
    total_cells: int
    surface_count: int
    probe_count: int
    coverage_sha256: str


@dataclass(frozen=True)
class CellCoverageCounts:
    surfaces: int
    probes: int


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewCoverageError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _contract_index(
    contract: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    _need(
        contract.get("schema") == "polaris.spec-contract/v1",
        "contract: wrong schema",
    )
    cells = contract.get("cells")
    _need(isinstance(cells, list), "contract: cells must be a list")
    index: dict[str, dict[str, Any]] = {}
    for cell in cells:
        _need(isinstance(cell, dict), "contract: invalid cell row")
        cell_id = cell.get("cell")
        _need(isinstance(cell_id, str) and cell_id, "contract: cell missing id")
        _need(cell_id not in index, f"contract: duplicate cell {cell_id}")
        index[cell_id] = cell
    return cells, index


def _validate_surfaces(cell_id: str, surfaces: Any) -> set[str]:
    _need(
        isinstance(surfaces, list) and bool(surfaces),
        f"{cell_id}: review surfaces required",
    )
    surface_ids: set[str] = set()
    for surface in surfaces:
        _need(isinstance(surface, dict), f"{cell_id}: invalid surface row")
        _need(
            set(surface) == {"surface_id", "role", "evidence"},
            f"{cell_id}: unsupported surface fields",
        )
        surface_id = surface.get("surface_id")
        _need(
            isinstance(surface_id, str)
            and _SURFACE_ID.fullmatch(surface_id) is not None,
            f"{cell_id}: invalid surface_id",
        )
        _need(
            surface_id not in surface_ids,
            f"{cell_id}: duplicate surface {surface_id}",
        )
        surface_ids.add(surface_id)
        _need(
            surface.get("role") in _ALLOWED_ROLES,
            f"{cell_id}: invalid surface role",
        )
        evidence = surface.get("evidence")
        _need(
            isinstance(evidence, str) and bool(evidence.strip()),
            f"{cell_id}: surface evidence required",
        )
    return surface_ids


def _validate_lenses(
    cell_id: str,
    kind: str,
    lenses: Any,
) -> dict[str, dict[str, Any]]:
    required = _REQUIRED_LENSES[kind]
    _need(isinstance(lenses, list), f"{cell_id}: lenses must be a list")
    lens_rows: dict[str, dict[str, Any]] = {}
    for lens_row in lenses:
        _need(isinstance(lens_row, dict), f"{cell_id}: invalid lens row")
        _need(
            set(lens_row) == {"lens", "status", "rationale"},
            f"{cell_id}: unsupported lens fields",
        )
        lens = lens_row.get("lens")
        _need(lens in required, f"{cell_id}: unexpected lens {lens}")
        _need(lens not in lens_rows, f"{cell_id}: duplicate lens {lens}")
        status = lens_row.get("status")
        _need(status in _ALLOWED_STATUS, f"{cell_id}: invalid lens status")
        rationale = lens_row.get("rationale")
        _need(
            isinstance(rationale, str),
            f"{cell_id}: lens rationale must be text",
        )
        if status == "not-applicable":
            _need(
                bool(rationale.strip()),
                f"{cell_id}: not-applicable lens requires rationale",
            )
        lens_rows[lens] = lens_row
    _need(
        tuple(lens_rows) == required,
        f"{cell_id}: required lenses must appear once in canonical order",
    )
    return lens_rows


def _validate_probe_shape(cell_id: str, probe: Any) -> None:
    _need(isinstance(probe, dict), f"{cell_id}: invalid probe row")
    _need(
        set(probe)
        == {
            "probe_id",
            "lens",
            "surface_ids",
            "falsifier",
            "evidence",
            "finding_ids",
        },
        f"{cell_id}: unsupported probe fields",
    )


def _validate_finding_ids(cell_id: str, finding_ids: Any) -> None:
    _need(
        isinstance(finding_ids, list),
        f"{cell_id}: finding_ids must be a list",
    )
    valid = all(
        isinstance(item, str) and _FINDING.fullmatch(item) is not None
        for item in finding_ids
    )
    _need(valid, f"{cell_id}: invalid finding ID")
    _need(
        len(finding_ids) == len(set(finding_ids)),
        f"{cell_id}: duplicate finding ID",
    )


def _validate_probes(
    cell_id: str,
    probes: Any,
    surface_ids: set[str],
    lens_rows: dict[str, dict[str, Any]],
) -> int:
    _need(
        isinstance(probes, list) and bool(probes),
        f"{cell_id}: adversarial probes required",
    )
    probe_ids: set[str] = set()
    referenced_surfaces: set[str] = set()
    covered_lenses: set[str] = set()
    for probe in probes:
        _validate_probe_shape(cell_id, probe)
        probe_id = probe.get("probe_id")
        _need(
            isinstance(probe_id, str)
            and _PROBE_ID.fullmatch(probe_id) is not None,
            f"{cell_id}: invalid probe_id",
        )
        _need(probe_id not in probe_ids, f"{cell_id}: duplicate probe {probe_id}")
        probe_ids.add(probe_id)
        lens = probe.get("lens")
        _need(lens in lens_rows, f"{cell_id}: probe uses unknown lens {lens}")
        _need(
            lens_rows[lens]["status"] == "covered",
            f"{cell_id}: probe cannot target not-applicable lens {lens}",
        )
        covered_lenses.add(lens)
        refs = probe.get("surface_ids")
        _need(
            isinstance(refs, list) and bool(refs),
            f"{cell_id}: probe surfaces required",
        )
        valid_refs = all(
            isinstance(ref, str) and ref in surface_ids for ref in refs
        )
        _need(valid_refs, f"{cell_id}: probe references unknown surface")
        _need(len(refs) == len(set(refs)), f"{cell_id}: duplicate probe surface")
        referenced_surfaces.update(refs)
        for field in ("falsifier", "evidence"):
            value = probe.get(field)
            _need(
                isinstance(value, str) and bool(value.strip()),
                f"{cell_id}: probe {field} required",
            )
        _validate_finding_ids(cell_id, probe.get("finding_ids"))

    _need(
        referenced_surfaces == surface_ids,
        f"{cell_id}: every declared review surface must be exercised by a probe",
    )
    for lens, lens_row in lens_rows.items():
        if lens_row["status"] == "covered":
            _need(
                lens in covered_lenses,
                f"{cell_id}: covered lens {lens} has no probe",
            )
        else:
            _need(
                lens not in covered_lenses,
                f"{cell_id}: not-applicable lens {lens} has a probe",
            )
    return len(probes)


def _validate_cell_row(
    row: Any,
    expected_cell: dict[str, Any],
    contract_index: dict[str, dict[str, Any]],
    seen: set[str],
) -> CellCoverageCounts:
    _need(isinstance(row, dict), "coverage: invalid cell row")
    _need(
        set(row) == {"cell", "cell_hash", "kind", "surfaces", "lenses", "probes"},
        "coverage: unsupported cell row fields",
    )
    cell_id = row.get("cell")
    _need(
        isinstance(cell_id, str) and cell_id in contract_index,
        f"coverage: unknown cell {cell_id}",
    )
    _need(cell_id not in seen, f"coverage: duplicate cell {cell_id}")
    seen.add(cell_id)
    _need(
        cell_id == expected_cell.get("cell"),
        f"coverage: cell order mismatch at {cell_id}",
    )
    contract_cell = contract_index[cell_id]
    _need(
        row.get("cell_hash") == contract_cell.get("cell_hash"),
        f"coverage: stale cell hash {cell_id}",
    )
    kind = row.get("kind")
    _need(kind == contract_cell.get("kind"), f"coverage: wrong kind for {cell_id}")
    _need(kind in _REQUIRED_LENSES, f"coverage: unsupported cell kind {kind}")

    surface_ids = _validate_surfaces(cell_id, row.get("surfaces"))
    lens_rows = _validate_lenses(cell_id, kind, row.get("lenses"))
    probe_count = _validate_probes(
        cell_id,
        row.get("probes"),
        surface_ids,
        lens_rows,
    )
    return CellCoverageCounts(surfaces=len(surface_ids), probes=probe_count)


def validate_coverage(
    contract: dict[str, Any], coverage: dict[str, Any]
) -> ReviewCoverageReceipt:
    contract_cells, contract_index = _contract_index(contract)
    contract_hash = contract.get("spec_contract_hash")
    _need(
        isinstance(contract_hash, str) and bool(contract_hash),
        "contract: missing spec contract hash",
    )
    _need(coverage.get("schema") == SCHEMA, f"coverage: schema must be {SCHEMA}")
    _need(
        set(coverage) == {"schema", "spec_contract_hash", "reviewed_head", "cells"},
        "coverage: unsupported top-level fields",
    )
    _need(
        coverage.get("spec_contract_hash") == contract_hash,
        "coverage: stale Spec Contract Hash",
    )
    reviewed_head = coverage.get("reviewed_head")
    _need(
        isinstance(reviewed_head, str) and _HEAD.fullmatch(reviewed_head) is not None,
        "coverage: reviewed_head must be one full lowercase commit SHA",
    )
    rows = coverage.get("cells")
    _need(isinstance(rows, list), "coverage: cells must be a list")
    _need(
        len(rows) == len(contract_cells),
        "coverage: cell count does not match Spec contract",
    )

    seen: set[str] = set()
    surface_total = 0
    probe_total = 0
    for row, expected_cell in zip(rows, contract_cells, strict=True):
        counts = _validate_cell_row(row, expected_cell, contract_index, seen)
        surface_total += counts.surfaces
        probe_total += counts.probes

    _need(seen == set(contract_index), "coverage: unchecked contract cell remains")
    return ReviewCoverageReceipt(
        reviewed_head=reviewed_head,
        spec_contract_hash=contract_hash,
        reviewed_cells=len(seen),
        total_cells=len(contract_cells),
        surface_count=surface_total,
        probe_count=probe_total,
        coverage_sha256=sha256_canonical_json(coverage),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("spec_contract", type=Path)
    validate.add_argument("coverage", type=Path)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        contract = _read_json(args.spec_contract)
        coverage = _read_json(args.coverage)
        receipt = validate_coverage(contract, coverage)
    except (ReviewCoverageError, json.JSONDecodeError, OSError) as exc:
        parser.error(str(exc))

    print("REVIEW COVERAGE: VALID")
    print(f"Reviewed HEAD: {receipt.reviewed_head}")
    print(f"Spec Contract Hash: {receipt.spec_contract_hash}")
    print(f"Contract cells reviewed: {receipt.reviewed_cells}/{receipt.total_cells}")
    print("Unchecked contract cells: 0")
    print(f"Declared review surfaces: {receipt.surface_count}")
    print(f"Adversarial probes: {receipt.probe_count}")
    print(f"Review Coverage SHA-256: {receipt.coverage_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
