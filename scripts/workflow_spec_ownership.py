from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts import spec_contract, workflow_to_specs

SCHEMA = workflow_to_specs.SCHEMA
CONTROL_PLANE_PATHS = (
    ".agents/skills/to-specs/SKILL.md",
    ".agents/skills/to-specs/RETAINED_SKILL.md",
    ".agents/skills/to-specs/PROCEDURE.md",
    "scripts/workflow_spec_ownership.py",
)


class OwnershipError(RuntimeError):
    pass


def _need(ok: bool, message: str) -> None:
    if not ok:
        raise OwnershipError(message)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OwnershipError(f"{path}: {exc}") from exc
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise OwnershipError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"git {' '.join(args)} failed"
        )
    return result.stdout.strip()


def preflight(repo: Path, main_ref: str) -> str:
    _git(repo, "rev-parse", "--verify", main_ref)
    stale = [
        path
        for path in CONTROL_PLANE_PATHS
        if _git(repo, "rev-parse", f"HEAD:{path}")
        != _git(repo, "rev-parse", f"{main_ref}:{path}")
    ]
    _need(
        not stale,
        "ownership control-plane bytes are stale relative to current main: "
        + ", ".join(stale),
    )
    return "\n".join(
        [
            "TO-SPECS OWNERSHIP PREFLIGHT: VALID",
            f"Control-plane ref: {main_ref}",
            f"Control-plane paths current: {len(CONTROL_PLANE_PATHS)}",
        ]
    )


def _strings(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    _need(isinstance(value, list), f"{label}: list required")
    _need(allow_empty or bool(value), f"{label}: non-empty list required")
    _need(
        all(isinstance(item, str) and item.strip() for item in value),
        f"{label}: non-empty strings required",
    )
    result = [item.strip() for item in value]
    _need(len(result) == len(set(result)), f"{label}: duplicates are not allowed")
    return result


def _entry_path(base: Path, entry: dict[str, Any]) -> Path:
    value = entry.get("issue_json")
    _need(isinstance(value, str) and value.strip(), "manifest: issue_json required")
    path = Path(value)
    return path if path.is_absolute() else base / path


def _body(issue: dict[str, Any], number: int) -> str:
    body = issue.get("body")
    _need(isinstance(body, str), f"spec #{number}: issue snapshot missing body")
    return body


def _contract_and_topology(
    issue: dict[str, Any], number: int
) -> tuple[dict[str, Any], dict[str, Any]]:
    body = _body(issue, number)
    try:
        contract = spec_contract.build_contract(body)
        topology = spec_contract.build_execution_topology(body, contract)
    except spec_contract.SpecContractError as exc:
        raise OwnershipError(f"spec #{number}: {exc}") from exc
    return contract, topology


def _unit_maps(
    topology: dict[str, Any],
) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    owners: dict[str, str] = {}
    graph: dict[str, tuple[str, ...]] = {}
    for unit in topology["units"]:
        unit_id = unit["unit_id"]
        graph[unit_id] = tuple(unit["depends_on"])
        for cell in unit["cells"]:
            owners[cell] = unit_id
    return owners, graph


def _analysis_by_unit(entry: dict[str, Any], spec: int) -> dict[str, dict[str, Any]]:
    rows = entry.get("unit_analysis")
    _need(isinstance(rows, list), f"spec #{spec}: unit_analysis list required")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _need(isinstance(row, dict), f"spec #{spec}: unit_analysis row must be object")
        unit = row.get("unit_id")
        _need(isinstance(unit, str), f"spec #{spec}: unit_analysis unit_id required")
        _need(unit not in result, f"spec #{spec}: duplicate unit_analysis {unit}")
        result[unit] = row
    return result


def _provider_declared(row: dict[str, Any], provider: int) -> bool:
    requirements = row.get("provider_requirements")
    if not isinstance(requirements, list):
        return False
    return any(
        isinstance(item, dict) and item.get("provider_spec") == provider
        for item in requirements
    )


def _material_rows(
    value: Any, expected: set[str], spec: int
) -> dict[str, dict[str, Any]]:
    _need(isinstance(value, list), f"spec #{spec}: ownership material list required")
    result: dict[str, dict[str, Any]] = {}
    for row in value:
        _need(
            isinstance(row, dict),
            f"spec #{spec}: material ownership row must be object",
        )
        cell = row.get("cell")
        _need(isinstance(cell, str), f"spec #{spec}: material ownership cell required")
        _need(cell not in result, f"spec #{spec}: duplicate material ownership {cell}")
        result[cell] = row
    _need(
        set(result) == expected,
        f"spec #{spec}: material ownership must cover every and only current OBL; "
        f"missing={sorted(expected - set(result))} "
        f"extra={sorted(set(result) - expected)}",
    )
    return result


def _planning_rows(
    value: Any, expected: set[str], spec: int
) -> dict[str, dict[str, Any]]:
    _need(isinstance(value, list), f"spec #{spec}: ownership planning list required")
    result: dict[str, dict[str, Any]] = {}
    for row in value:
        _need(
            isinstance(row, dict),
            f"spec #{spec}: planning ownership row must be object",
        )
        cell = row.get("cell")
        _need(isinstance(cell, str), f"spec #{spec}: planning ownership cell required")
        _need(cell not in result, f"spec #{spec}: duplicate planning ownership {cell}")
        result[cell] = row
    _need(
        set(result) == expected,
        f"spec #{spec}: planning ownership must cover every and only current IMP/TEST; "
        f"missing={sorted(expected - set(result))} "
        f"extra={sorted(set(result) - expected)}",
    )
    return result


def _text_evidence(row: dict[str, Any], label: str) -> None:
    reason = row.get("reason")
    _need(isinstance(reason, str) and reason.strip(), f"{label}: reason required")
    _strings(row.get("basis"), f"{label} basis")


def _check_consumed(
    *,
    spec: int,
    cell: str,
    row: dict[str, Any],
    cells: dict[str, dict[str, Any]],
    cell_units: dict[str, str],
    analyses: dict[str, dict[str, Any]],
    snapshots: dict[int, workflow_to_specs.SpecSnapshot],
    issues: dict[int, dict[str, Any]],
    spec_graph: dict[int, tuple[int, ...]],
    errors: list[str],
) -> None:
    label = f"spec #{spec} {cell}"
    provider = row.get("provider_spec")
    if not isinstance(provider, int) or provider <= 0 or provider == spec:
        errors.append(
            f"{label}: consumed-boundary provider_spec must be another Spec"
        )
        return
    provider_snapshot = snapshots.get(provider)
    if provider_snapshot is None:
        errors.append(f"{label}: provider Spec #{provider} absent from bounded set")
        return
    try:
        provider_cells = _strings(
            row.get("provider_cells"),
            f"{label} provider_cells",
            allow_empty=True,
        )
    except OwnershipError as exc:
        errors.append(str(exc))
        return
    if provider_snapshot.is_legacy_completed:
        if provider_cells:
            errors.append(
                f"{label}: legacy provider must not invent provider cells"
            )
    else:
        _check_provider_cells(
            label=label,
            cell=cell,
            provider=provider,
            provider_cells=provider_cells,
            cells=cells,
            issues=issues,
            errors=errors,
        )
    if provider_snapshot.state == "OPEN" and not workflow_to_specs._reachable(
        spec_graph, spec, provider
    ):
        errors.append(
            f"{label}: open provider #{provider} is downstream/unrelated; "
            "no native prerequisite path protects the consumer"
        )
    unit = cell_units[cell]
    if not _provider_declared(analyses.get(unit, {}), provider):
        errors.append(
            f"{label}: provider #{provider} is not declared in {unit} "
            "unit_analysis.provider_requirements"
        )


def _check_provider_cells(
    *,
    label: str,
    cell: str,
    provider: int,
    provider_cells: list[str],
    cells: dict[str, dict[str, Any]],
    issues: dict[int, dict[str, Any]],
    errors: list[str],
) -> None:
    try:
        provider_contract, _ = _contract_and_topology(issues[provider], provider)
    except OwnershipError as exc:
        errors.append(str(exc))
        return
    provider_by_cell = {item["cell"]: item for item in provider_contract["cells"]}
    if not provider_cells:
        errors.append(f"{label}: topology-bearing provider_cells required")
    covered: set[str] = set()
    for provider_cell in provider_cells:
        item = provider_by_cell.get(provider_cell)
        if item is None or item["kind"] != "material-contract":
            errors.append(
                f"{label}: invalid provider material cell {provider_cell}"
            )
            continue
        covered.update(item["ccl"])
    missing = set(cells[cell]["ccl"]) - covered
    if missing:
        errors.append(
            f"{label}: provider cells do not cover CCL refs {sorted(missing)}"
        )


def _check_material(
    *,
    spec: int,
    rows: dict[str, dict[str, Any]],
    cells: dict[str, dict[str, Any]],
    cell_units: dict[str, str],
    analyses: dict[str, dict[str, Any]],
    snapshots: dict[int, workflow_to_specs.SpecSnapshot],
    issues: dict[int, dict[str, Any]],
    spec_graph: dict[int, tuple[int, ...]],
    errors: list[str],
) -> dict[str, str]:
    dispositions: dict[str, str] = {}
    for cell, row in rows.items():
        label = f"spec #{spec} {cell}"
        try:
            _text_evidence(row, label)
        except OwnershipError as exc:
            errors.append(str(exc))
        disposition = row.get("disposition")
        dispositions[cell] = str(disposition)
        if disposition == "owned":
            role = row.get("role")
            if not isinstance(role, str) or not role.strip():
                errors.append(f"{label}: owned material requires role")
            if "provider_spec" in row or "provider_cells" in row:
                errors.append(f"{label}: owned material must not name a provider")
        elif disposition == "consumed-boundary":
            _check_consumed(
                spec=spec,
                cell=cell,
                row=row,
                cells=cells,
                cell_units=cell_units,
                analyses=analyses,
                snapshots=snapshots,
                issues=issues,
                spec_graph=spec_graph,
                errors=errors,
            )
        else:
            errors.append(
                f"{label}: disposition must be owned/consumed-boundary"
            )
    return dispositions


def _check_planning(
    *,
    spec: int,
    rows: dict[str, dict[str, Any]],
    dispositions: dict[str, str],
    cell_units: dict[str, str],
    unit_graph: dict[str, tuple[str, ...]],
    errors: list[str],
) -> None:
    material = set(dispositions)
    for cell, row in rows.items():
        label = f"spec #{spec} {cell}"
        try:
            _text_evidence(row, label)
            supports = _strings(row.get("supports"), f"{label} supports")
        except OwnershipError as exc:
            errors.append(str(exc))
            continue
        unknown = set(supports) - material
        if unknown:
            errors.append(f"{label}: supports unknown OBL cells {sorted(unknown)}")
            continue
        if not any(dispositions[item] == "owned" for item in supports):
            errors.append(
                f"{label}: planning cell has no locally owned material outcome"
            )
        unit = cell_units[cell]
        for support in supports:
            support_unit = cell_units[support]
            if support_unit != unit and not workflow_to_specs._reachable(
                unit_graph, unit, support_unit
            ):
                errors.append(
                    f"{label}: supports {support} in downstream/unrelated "
                    f"{support_unit}"
                )


def validate_manifest(path: Path) -> dict[str, Any]:
    manifest = _load(path)
    _need(manifest.get("schema") == SCHEMA, f"manifest schema must be {SCHEMA}")
    raw_entries = manifest.get("specs")
    _need(isinstance(raw_entries, list) and raw_entries, "manifest: specs required")
    base = path.parent
    entries: dict[int, dict[str, Any]] = {}
    issues: dict[int, dict[str, Any]] = {}
    snapshots: dict[int, workflow_to_specs.SpecSnapshot] = {}
    for raw in raw_entries:
        _need(isinstance(raw, dict), "manifest: spec entry must be object")
        issue_path = _entry_path(base, raw)
        issue = _load(issue_path)
        snapshot = workflow_to_specs._load_snapshot(issue_path)
        _need(snapshot.number not in entries, "manifest: duplicate spec snapshot")
        entries[snapshot.number] = raw
        issues[snapshot.number] = issue
        snapshots[snapshot.number] = snapshot
    spec_graph = {number: snap.blocked_by for number, snap in snapshots.items()}
    errors: list[str] = []
    owned_units = 0
    consumed_count = 0
    for spec, snapshot in snapshots.items():
        if snapshot.is_legacy_completed:
            continue
        entry = entries[spec]
        ownership = entry.get("ownership_analysis")
        if not isinstance(ownership, dict):
            errors.append(f"spec #{spec}: ownership_analysis object required")
            continue
        try:
            contract, topology = _contract_and_topology(issues[spec], spec)
            cell_units, unit_graph = _unit_maps(topology)
            analyses = _analysis_by_unit(entry, spec)
            cells = {item["cell"]: item for item in contract["cells"]}
            material_ids = {
                cell
                for cell, item in cells.items()
                if item["kind"] == "material-contract"
            }
            planning_ids = {
                cell
                for cell, item in cells.items()
                if item["kind"] in {"implementation", "testing"}
            }
            material_rows = _material_rows(
                ownership.get("material"), material_ids, spec
            )
            planning_rows = _planning_rows(
                ownership.get("planning"), planning_ids, spec
            )
        except OwnershipError as exc:
            errors.append(str(exc))
            continue
        dispositions = _check_material(
            spec=spec,
            rows=material_rows,
            cells=cells,
            cell_units=cell_units,
            analyses=analyses,
            snapshots=snapshots,
            issues=issues,
            spec_graph=spec_graph,
            errors=errors,
        )
        consumed_count += sum(
            value == "consumed-boundary" for value in dispositions.values()
        )
        _check_planning(
            spec=spec,
            rows=planning_rows,
            dispositions=dispositions,
            cell_units=cell_units,
            unit_graph=unit_graph,
            errors=errors,
        )
        for unit in topology["units"]:
            material_in_unit = [
                cell for cell in unit["cells"] if cell in material_ids
            ]
            if material_in_unit and not any(
                dispositions.get(cell) == "owned" for cell in material_in_unit
            ):
                errors.append(
                    f"spec #{spec} {unit['unit_id']}: execution unit has no "
                    "locally owned material OBL"
                )
            elif material_in_unit:
                owned_units += 1
    if errors:
        raise OwnershipError("\n".join(errors))
    manifest_hash = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "specs": len(snapshots),
        "consumed": consumed_count,
        "owned_units": owned_units,
        "hash": manifest_hash,
    }


def check_ownership(path: Path) -> str:
    result = validate_manifest(path)
    return "\n".join(
        [
            "TO-SPECS CROSS-SPEC OWNERSHIP: VALID",
            f"Specs analyzed: {result['specs']}",
            f"Consumed-boundary obligations analyzed: {result['consumed']}",
            "Unprotected consumed-boundary requirements: 0",
            "Execution units without local material ownership: 0",
            f"Ownership manifest SHA-256: {result['hash']}",
        ]
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument("--repo", type=Path, default=Path("."))
    pre.add_argument("--main-ref", default="origin/main")
    check = sub.add_parser("check")
    check.add_argument("--manifest", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "preflight":
            print(preflight(args.repo, args.main_ref))
        else:
            print(check_ownership(args.manifest))
        return 0
    except OwnershipError as exc:
        header = (
            "TO-SPECS OWNERSHIP PREFLIGHT: INVALID"
            if args.command == "preflight"
            else "TO-SPECS CROSS-SPEC OWNERSHIP: INVALID"
        )
        print(f"{header}\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
