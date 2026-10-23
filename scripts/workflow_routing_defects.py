from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

INVENTORY_SCHEMA = "polaris.workflow-routing-defect-inventory/v1"
MARKER_SCHEMA = "polaris.workflow-routing-defect/v1"
FEASIBILITY_SCHEMA = "polaris.to-specs-execution-feasibility/v1"
MARKER_PATTERN = re.compile(
    r"<!--\s*workflow-routing-defect:v1\s*(\{.*?\})\s*-->", re.DOTALL
)
TOPOLOGY_PATTERN = re.compile(
    r"<!--\s*spec-execution-topology:v1\s*(\{.*?\})\s*-->", re.DOTALL
)
CELL_PATTERN = re.compile(r"(?:OBL|IMP|TEST)-\d{3}")
CONTROL_PLANE_PATHS = (
    ".agents/skills/to-specs/SKILL.md",
    ".agents/skills/implement-ticket/SKILL.md",
    "scripts/workflow_routing_defects.py",
)


class RoutingDefectError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise RoutingDefectError(message)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoutingDefectError(f"{path}: {exc}") from exc
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
        raise RoutingDefectError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"git {' '.join(args)} failed"
        )
    return result.stdout.strip()


def preflight(repo: Path, main_ref: str) -> str:
    _git(repo, "rev-parse", "--verify", main_ref)
    stale: list[str] = []
    for path in CONTROL_PLANE_PATHS:
        head_blob = _git(repo, "rev-parse", f"HEAD:{path}")
        main_blob = _git(repo, "rev-parse", f"{main_ref}:{path}")
        if head_blob != main_blob:
            stale.append(path)
    _need(
        not stale,
        "routing-defect control-plane bytes are stale relative to current main: "
        + ", ".join(stale),
    )
    return "\n".join(
        [
            "TO-SPECS ROUTING DEFECT PREFLIGHT: VALID",
            f"Control-plane ref: {main_ref}",
            f"Control-plane paths current: {len(CONTROL_PLANE_PATHS)}",
        ]
    )


def _repo_parts(repo: str) -> tuple[str, str]:
    parts = repo.split("/")
    _need(len(parts) == 2 and all(parts), "repo must be owner/name")
    return parts[0], parts[1]


def _gh_json(*args: str) -> Any:
    result = subprocess.run(
        ["gh", "api", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RoutingDefectError(
            result.stderr.strip() or result.stdout.strip() or "gh api failed"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RoutingDefectError(f"gh api returned invalid JSON: {exc}") from exc


def _paged(endpoint: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        separator = "&" if "?" in endpoint else "?"
        value = _gh_json(f"{endpoint}{separator}per_page=100&page={page}")
        _need(isinstance(value, list), f"{endpoint}: expected JSON list")
        for row in value:
            _need(isinstance(row, dict), f"{endpoint}: expected object rows")
            rows.append(row)
        if len(value) < 100:
            return rows
        page += 1


def _cell_list(value: Any, label: str, *, allow_empty: bool) -> list[str]:
    _need(isinstance(value, list), f"{label}: list required")
    if not allow_empty:
        _need(value, f"{label}: non-empty list required")
    result: list[str] = []
    for item in value:
        _need(
            isinstance(item, str) and CELL_PATTERN.fullmatch(item) is not None,
            f"{label}: invalid cell id",
        )
        result.append(item)
    _need(len(result) == len(set(result)), f"{label}: duplicate cell id")
    return result


def validate_marker(
    marker: dict[str, Any], *, ticket: int | None = None, spec: int | None = None
) -> dict[str, Any]:
    _need(
        marker.get("schema") == MARKER_SCHEMA,
        f"marker schema must be {MARKER_SCHEMA}",
    )
    defect_id = marker.get("defect_id")
    _need(
        isinstance(defect_id, str) and defect_id.strip(),
        "marker defect_id required",
    )
    _need(
        marker.get("status") in {"open", "resolved"},
        "marker status must be open/resolved",
    )
    _need(
        marker.get("classification") == "cell-routing-defect",
        "marker classification must be cell-routing-defect",
    )
    source_ticket = marker.get("source_ticket")
    parent_spec = marker.get("parent_spec")
    _need(
        isinstance(source_ticket, int) and source_ticket > 0,
        "marker source_ticket must be positive integer",
    )
    _need(
        isinstance(parent_spec, int) and parent_spec > 0,
        "marker parent_spec must be positive integer",
    )
    if ticket is not None:
        _need(
            source_ticket == ticket,
            f"marker source_ticket #{source_ticket} does not match child ticket #{ticket}",
        )
    if spec is not None:
        _need(
            parent_spec == spec,
            f"marker parent_spec #{parent_spec} does not match scanned Spec #{spec}",
        )
    _cell_list(
        marker.get("affected_cells"), "marker affected_cells", allow_empty=False
    )
    _cell_list(
        marker.get("required_local_provider_cells"),
        "marker required_local_provider_cells",
        allow_empty=True,
    )
    reason = marker.get("reason")
    _need(isinstance(reason, str) and reason.strip(), "marker reason required")
    basis = marker.get("basis")
    _need(
        isinstance(basis, list) and basis,
        "marker basis non-empty list required",
    )
    _need(
        all(isinstance(item, str) and item.strip() for item in basis),
        "marker basis non-empty strings required",
    )
    return marker


def validate_marker_file(path: Path) -> str:
    marker = validate_marker(_load_json(path))
    return "\n".join(
        [
            "WORKFLOW ROUTING DEFECT MARKER: VALID",
            f"Defect: {marker['defect_id']}",
            f"Marker SHA-256: {_canonical_hash(marker)}",
        ]
    )


def _markers_from_comment(body: str) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for match in MARKER_PATTERN.finditer(body):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise RoutingDefectError(
                f"invalid workflow-routing-defect:v1 marker JSON: {exc}"
            ) from exc
        _need(
            isinstance(value, dict),
            "workflow-routing-defect:v1 marker must be object",
        )
        markers.append(value)
    return markers


def collect_inventory(repo: str, specs: list[int], output: Path) -> str:
    owner, name = _repo_parts(repo)
    _need(
        specs and all(number > 0 for number in specs),
        "at least one positive --spec required",
    )
    _need(len(specs) == len(set(specs)), "duplicate --spec")
    defects: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for spec in sorted(specs):
        children = _paged(f"repos/{owner}/{name}/issues/{spec}/sub_issues")
        for child in children:
            ticket = child.get("number")
            state = child.get("state")
            _need(
                isinstance(ticket, int) and ticket > 0,
                f"spec #{spec}: child issue number invalid",
            )
            _need(isinstance(state, str), f"ticket #{ticket}: state required")
            comments = _paged(f"repos/{owner}/{name}/issues/{ticket}/comments")
            for comment in comments:
                body = comment.get("body")
                url = comment.get("html_url")
                comment_id = comment.get("id")
                _need(
                    isinstance(body, str), f"ticket #{ticket}: comment body required"
                )
                for raw_marker in _markers_from_comment(body):
                    marker = validate_marker(raw_marker, ticket=ticket, spec=spec)
                    defect_id = marker["defect_id"]
                    _need(
                        defect_id not in seen_ids,
                        f"duplicate routing defect id: {defect_id}",
                    )
                    seen_ids.add(defect_id)
                    defects.append(
                        {
                            **marker,
                            "comment_id": comment_id,
                            "comment_url": url,
                            "ticket_state": state.upper(),
                            "marker_sha256": _canonical_hash(marker),
                        }
                    )
    inventory = {
        "schema": INVENTORY_SCHEMA,
        "repository": repo,
        "specs_scanned": sorted(specs),
        "defects": sorted(
            defects,
            key=lambda item: (
                item["parent_spec"],
                item["source_ticket"],
                item["defect_id"],
            ),
        ),
    }
    output.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return "\n".join(
        [
            "TO-SPECS ROUTING DEFECT INVENTORY: VALID",
            f"Specs scanned: {len(specs)}",
            f"Durable routing defects discovered: {len(defects)}",
            f"Routing defect inventory SHA-256: {_canonical_hash(inventory)}",
        ]
    )


def _extract_topology(
    issue: dict[str, Any], number: int
) -> tuple[dict[str, tuple[str, ...]], dict[str, str]]:
    body = issue.get("body")
    _need(isinstance(body, str), f"spec #{number}: issue snapshot missing body")
    match = TOPOLOGY_PATTERN.search(body)
    _need(
        match is not None,
        f"spec #{number}: routing-defect check requires execution topology",
    )
    try:
        topology = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RoutingDefectError(
            f"spec #{number}: invalid execution topology JSON: {exc}"
        ) from exc
    _need(
        topology.get("schema") == "polaris.spec-execution-topology/v1",
        f"spec #{number}: wrong execution topology schema",
    )
    units = topology.get("units")
    _need(
        isinstance(units, list) and units,
        f"spec #{number}: topology units required",
    )
    graph: dict[str, tuple[str, ...]] = {}
    cell_owner: dict[str, str] = {}
    for unit in units:
        _need(
            isinstance(unit, dict),
            f"spec #{number}: topology unit must be object",
        )
        unit_id = unit.get("unit_id")
        depends_on = unit.get("depends_on")
        cells = unit.get("cells")
        _need(
            isinstance(unit_id, str)
            and re.fullmatch(r"EU-\d{3}", unit_id) is not None,
            f"spec #{number}: invalid unit id",
        )
        _need(
            isinstance(depends_on, list)
            and all(isinstance(x, str) for x in depends_on),
            f"spec #{number} {unit_id}: depends_on list required",
        )
        _need(
            isinstance(cells, list) and all(isinstance(x, str) for x in cells),
            f"spec #{number} {unit_id}: cells list required",
        )
        graph[unit_id] = tuple(depends_on)
        for cell in cells:
            _need(
                cell not in cell_owner,
                f"spec #{number}: duplicate topology cell {cell}",
            )
            cell_owner[cell] = unit_id
    return graph, cell_owner


def _reachable(
    graph: dict[str, tuple[str, ...]], start: str, target: str
) -> bool:
    todo = list(graph.get(start, ()))
    seen: set[str] = set()
    while todo:
        current = todo.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        todo.extend(graph.get(current, ()))
    return False


def check_inventory(inventory_path: Path, manifest_path: Path) -> str:
    inventory = _load_json(inventory_path)
    _need(
        inventory.get("schema") == INVENTORY_SCHEMA,
        f"inventory schema must be {INVENTORY_SCHEMA}",
    )
    manifest = _load_json(manifest_path)
    _need(
        manifest.get("schema") == FEASIBILITY_SCHEMA,
        f"manifest schema must be {FEASIBILITY_SCHEMA}",
    )
    specs_raw = manifest.get("specs")
    _need(isinstance(specs_raw, list) and specs_raw, "manifest: specs required")
    base = manifest_path.parent
    snapshots: dict[int, dict[str, Any]] = {}
    for entry in specs_raw:
        _need(isinstance(entry, dict), "manifest: spec entry must be object")
        issue_json = entry.get("issue_json")
        _need(
            isinstance(issue_json, str) and issue_json.strip(),
            "manifest: issue_json required",
        )
        path = Path(issue_json)
        if not path.is_absolute():
            path = base / path
        issue = _load_json(path)
        number = issue.get("number")
        _need(
            isinstance(number, int) and number > 0,
            f"{path}: invalid issue number",
        )
        snapshots[number] = issue
    scanned = inventory.get("specs_scanned")
    _need(
        isinstance(scanned, list) and all(isinstance(x, int) for x in scanned),
        "inventory specs_scanned integer list required",
    )
    _need(
        set(scanned) == set(snapshots),
        "routing defect inventory must scan every and only feasibility Spec",
    )
    defects = inventory.get("defects")
    _need(isinstance(defects, list), "inventory defects list required")
    errors: list[str] = []
    open_count = 0
    for defect in defects:
        if not isinstance(defect, dict):
            errors.append("inventory defect must be object")
            continue
        try:
            validate_marker(defect)
        except RoutingDefectError as exc:
            errors.append(str(exc))
            continue
        if defect.get("status") != "open":
            continue
        open_count += 1
        spec = defect["parent_spec"]
        issue = snapshots.get(spec)
        if issue is None:
            errors.append(
                f"routing defect {defect['defect_id']}: parent Spec #{spec} absent from feasibility set"
            )
            continue
        try:
            graph, cell_owner = _extract_topology(issue, spec)
        except RoutingDefectError as exc:
            errors.append(str(exc))
            continue
        affected = defect["affected_cells"]
        providers = defect["required_local_provider_cells"]
        if not providers:
            errors.append(
                f"routing defect {defect['defect_id']}: open defect has no machine-resolvable local provider cells and remains blocking"
            )
            continue
        for cell in affected:
            consumer_unit = cell_owner.get(cell)
            if consumer_unit is None:
                errors.append(
                    f"routing defect {defect['defect_id']}: affected cell {cell} absent from current Spec #{spec} topology"
                )
                continue
            for provider_cell in providers:
                provider_unit = cell_owner.get(provider_cell)
                if provider_unit is None:
                    errors.append(
                        f"routing defect {defect['defect_id']}: provider cell {provider_cell} absent from current Spec #{spec} topology"
                    )
                    continue
                if provider_unit == consumer_unit:
                    continue
                if not _reachable(graph, consumer_unit, provider_unit):
                    errors.append(
                        f"routing defect {defect['defect_id']}: {cell} in {consumer_unit} requires provider cell {provider_cell} in {provider_unit}, but {provider_unit} is not a transitive prerequisite of {consumer_unit}"
                    )
    if errors:
        raise RoutingDefectError("\n".join(errors))
    return "\n".join(
        [
            "TO-SPECS ROUTING DEFECT COVERAGE: VALID",
            f"Durable routing defects analyzed: {len(defects)}",
            f"Open routing defects analyzed: {open_count}",
            "Unprotected routing defect requirements: 0",
            f"Routing defect inventory SHA-256: {_canonical_hash(inventory)}",
        ]
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight")
    pre.add_argument("--repo", type=Path, default=Path("."))
    pre.add_argument("--main-ref", default="origin/main")

    marker = sub.add_parser("validate-marker")
    marker.add_argument("--file", type=Path, required=True)

    collect = sub.add_parser("collect")
    collect.add_argument("--repo", required=True)
    collect.add_argument("--spec", type=int, action="append", required=True)
    collect.add_argument("--output", type=Path, required=True)

    check = sub.add_parser("check")
    check.add_argument("--inventory", type=Path, required=True)
    check.add_argument("--manifest", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "preflight":
            print(preflight(args.repo, args.main_ref))
        elif args.command == "validate-marker":
            print(validate_marker_file(args.file))
        elif args.command == "collect":
            print(collect_inventory(args.repo, args.spec, args.output))
        elif args.command == "check":
            print(check_inventory(args.inventory, args.manifest))
        else:
            raise RoutingDefectError(f"unsupported command: {args.command}")
        return 0
    except RoutingDefectError as exc:
        header = {
            "preflight": "TO-SPECS ROUTING DEFECT PREFLIGHT: INVALID",
            "validate-marker": "WORKFLOW ROUTING DEFECT MARKER: INVALID",
            "collect": "TO-SPECS ROUTING DEFECT INVENTORY: INVALID",
            "check": "TO-SPECS ROUTING DEFECT COVERAGE: INVALID",
        }[args.command]
        print(f"{header}\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
