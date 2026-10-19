from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "polaris.to-specs-execution-feasibility/v1"
HANDOFF_SCHEMA = "polaris.workflow-handoff/v1"
TOPOLOGY_PATTERN = re.compile(
    r"<!--\s*spec-execution-topology:v1\s*(\{.*?\})\s*-->", re.DOTALL
)
CONTROL_PLANE_PATHS = (
    ".agents/skills/to-specs/SKILL.md",
    ".agents/skills/to-specs/PROCEDURE.md",
    "scripts/workflow_to_specs.py",
    "scripts/workflow_handoff.py",
)


class ToSpecsError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpecSnapshot:
    number: int
    title: str
    url: str
    state: str
    blocked_by: tuple[int, ...]
    topology_units: tuple[str, ...] | None

    @property
    def is_legacy_completed(self) -> bool:
        return self.state == "CLOSED" and self.topology_units is None


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ToSpecsError(message)


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ToSpecsError(f"{path}: {exc}") from exc
    _need(isinstance(value, dict), f"{path}: expected JSON object")
    return value


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _extract_blockers(issue: dict[str, Any], number: int) -> tuple[int, ...]:
    _need("blockedBy" in issue, f"spec #{number}: issue snapshot must include blockedBy")
    blocked = issue["blockedBy"]
    if isinstance(blocked, dict):
        nodes = blocked.get("nodes")
        _need(isinstance(nodes, list), f"spec #{number}: blockedBy.nodes must be a list")
    elif isinstance(blocked, list):
        nodes = blocked
    else:
        raise ToSpecsError(f"spec #{number}: unsupported blockedBy shape")

    result: list[int] = []
    for node in nodes:
        _need(isinstance(node, dict), f"spec #{number}: blockedBy node must be object")
        blocker = node.get("number")
        _need(
            isinstance(blocker, int) and blocker > 0,
            f"spec #{number}: blocker number invalid",
        )
        result.append(blocker)
    _need(len(set(result)) == len(result), f"spec #{number}: duplicate native blocker")
    return tuple(result)


def _extract_topology(
    issue: dict[str, Any], number: int, state: str
) -> tuple[str, ...] | None:
    body = issue.get("body")
    _need(isinstance(body, str), f"spec #{number}: issue snapshot missing body")
    match = TOPOLOGY_PATTERN.search(body)
    if match is None:
        _need(
            state == "CLOSED",
            f"spec #{number}: open spec missing spec-execution-topology:v1",
        )
        return None
    try:
        topology = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ToSpecsError(
            f"spec #{number}: invalid execution topology JSON: {exc}"
        ) from exc
    _need(
        topology.get("schema") == "polaris.spec-execution-topology/v1",
        f"spec #{number}: wrong execution topology schema",
    )
    units = topology.get("units")
    _need(isinstance(units, list) and units, f"spec #{number}: topology units required")
    ids: list[str] = []
    for unit in units:
        _need(isinstance(unit, dict), f"spec #{number}: topology unit must be object")
        unit_id = unit.get("unit_id")
        _need(
            isinstance(unit_id, str)
            and re.fullmatch(r"EU-\d{3}", unit_id) is not None,
            f"spec #{number}: invalid unit id",
        )
        ids.append(unit_id)
    _need(len(set(ids)) == len(ids), f"spec #{number}: duplicate execution unit")
    return tuple(ids)


def _load_snapshot(path: Path) -> SpecSnapshot:
    issue = _json(path)
    number = issue.get("number")
    title = issue.get("title")
    url = issue.get("url")
    state = issue.get("state")
    _need(isinstance(number, int) and number > 0, f"{path}: invalid issue number")
    _need(
        isinstance(title, str) and title.strip() != "",
        f"spec #{number}: title required",
    )
    _need(
        isinstance(url, str) and url.startswith("https://github.com/"),
        f"spec #{number}: canonical GitHub URL required",
    )
    _need(
        isinstance(state, str) and state.upper() in {"OPEN", "CLOSED"},
        f"spec #{number}: state must be OPEN/CLOSED",
    )
    normalized_state = state.upper()
    return SpecSnapshot(
        number=number,
        title=title.strip(),
        url=url.strip(),
        state=normalized_state,
        blocked_by=_extract_blockers(issue, number),
        topology_units=_extract_topology(issue, number, normalized_state),
    )


def _require_nonempty_strings(value: Any, label: str) -> tuple[str, ...]:
    _need(
        isinstance(value, list) and len(value) > 0,
        f"{label}: non-empty list required",
    )
    normalized: list[str] = []
    for item in value:
        _need(
            isinstance(item, str) and item.strip() != "",
            f"{label}: non-empty strings required",
        )
        normalized.append(item.strip())
    return tuple(normalized)


def _validate_legacy_completed(
    snapshot: SpecSnapshot, entry: dict[str, Any], analyses: Any
) -> None:
    legacy = entry.get("legacy_completed")
    _need(
        isinstance(legacy, dict),
        f"spec #{snapshot.number}: closed legacy spec without topology requires "
        "legacy_completed attestation",
    )
    _need(
        legacy.get("result") is True,
        f"spec #{snapshot.number}: legacy_completed.result must be true",
    )
    reason = legacy.get("reason")
    _need(
        isinstance(reason, str) and reason.strip() != "",
        f"spec #{snapshot.number}: legacy_completed reason required",
    )
    _require_nonempty_strings(
        legacy.get("completion_basis"),
        f"spec #{snapshot.number} legacy_completed completion_basis",
    )
    _need(
        analyses in (None, []),
        f"spec #{snapshot.number}: legacy completed spec without topology must not "
        "invent unit_analysis",
    )


def _reachable(graph: dict[int, tuple[int, ...]], start: int, target: int) -> bool:
    todo = list(graph.get(start, ()))
    seen: set[int] = set()
    while todo:
        current = todo.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        todo.extend(graph.get(current, ()))
    return False


def _manifest_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_manifest(
    path: Path,
) -> tuple[dict[str, Any], list[SpecSnapshot], list[int]]:
    manifest = _json(path)
    _need(manifest.get("schema") == SCHEMA, f"manifest schema must be {SCHEMA}")
    planning_source = manifest.get("planning_source")
    _need(
        isinstance(planning_source, str)
        and planning_source.startswith("https://github.com/"),
        "manifest: canonical planning_source URL required",
    )

    specs_raw = manifest.get("specs")
    _need(isinstance(specs_raw, list) and specs_raw, "manifest: specs required")
    base = path.parent

    snapshots: list[SpecSnapshot] = []
    analyses_by_spec: dict[int, list[dict[str, Any]]] = {}
    for entry in specs_raw:
        _need(isinstance(entry, dict), "manifest: spec entry must be object")
        issue_json = entry.get("issue_json")
        _need(
            isinstance(issue_json, str) and issue_json.strip() != "",
            "manifest: issue_json required",
        )
        snapshot = _load_snapshot(_resolve(base, issue_json))
        snapshots.append(snapshot)
        analyses = entry.get("unit_analysis")
        if snapshot.is_legacy_completed:
            _validate_legacy_completed(snapshot, entry, analyses)
            analyses_by_spec[snapshot.number] = []
            continue

        _need(
            "legacy_completed" not in entry,
            f"spec #{snapshot.number}: legacy_completed is allowed only for a CLOSED "
            "spec that lacks spec-execution-topology:v1",
        )
        _need(
            isinstance(analyses, list),
            f"spec #{snapshot.number}: unit_analysis list required",
        )
        analyses_by_spec[snapshot.number] = analyses

    numbers = [item.number for item in snapshots]
    _need(len(set(numbers)) == len(numbers), "manifest: duplicate spec snapshot")
    snapshot_by_number = {item.number: item for item in snapshots}

    order = manifest.get("spec_order")
    _need(
        isinstance(order, list) and all(isinstance(x, int) for x in order),
        "manifest: spec_order integer list required",
    )
    _need(len(order) == len(set(order)), "manifest: duplicate spec_order entry")
    _need(
        set(order) == set(numbers),
        "manifest: spec_order must contain every and only supplied spec",
    )

    graph = {item.number: item.blocked_by for item in snapshots}
    errors: list[str] = []

    for snapshot in snapshots:
        if snapshot.is_legacy_completed:
            continue

        analyses = analyses_by_spec[snapshot.number]
        unit_ids: list[str] = []
        for analysis in analyses:
            if not isinstance(analysis, dict):
                errors.append(
                    f"spec #{snapshot.number}: unit_analysis entry must be object"
                )
                continue
            unit_id = analysis.get("unit_id")
            if not isinstance(unit_id, str):
                errors.append(f"spec #{snapshot.number}: unit_analysis missing unit_id")
                continue
            unit_ids.append(unit_id)
            try:
                _require_nonempty_strings(
                    analysis.get("completion_basis"),
                    f"spec #{snapshot.number} {unit_id} completion_basis",
                )
            except ToSpecsError as exc:
                errors.append(str(exc))

            requirements = analysis.get("provider_requirements")
            if not isinstance(requirements, list):
                errors.append(
                    f"spec #{snapshot.number} {unit_id}: provider_requirements list required"
                )
                continue

            if not requirements:
                attestation = analysis.get("local_completion_attestation")
                if not isinstance(attestation, dict) or attestation.get("result") is not True:
                    errors.append(
                        f"spec #{snapshot.number} {unit_id}: empty provider_requirements "
                        "requires explicit local_completion_attestation"
                    )
                else:
                    reason = attestation.get("reason")
                    basis = attestation.get("basis")
                    if not isinstance(reason, str) or reason.strip() == "":
                        errors.append(
                            f"spec #{snapshot.number} {unit_id}: local attestation reason required"
                        )
                    try:
                        _require_nonempty_strings(
                            basis,
                            f"spec #{snapshot.number} {unit_id} local attestation basis",
                        )
                    except ToSpecsError as exc:
                        errors.append(str(exc))

            for requirement in requirements:
                if not isinstance(requirement, dict):
                    errors.append(
                        f"spec #{snapshot.number} {unit_id}: provider requirement must be object"
                    )
                    continue
                provider = requirement.get("provider_spec")
                reason = requirement.get("reason")
                if not isinstance(provider, int) or provider <= 0:
                    errors.append(
                        f"spec #{snapshot.number} {unit_id}: provider_spec must be positive integer"
                    )
                    continue
                if provider == snapshot.number:
                    errors.append(
                        f"spec #{snapshot.number} {unit_id}: provider_spec cannot be self"
                    )
                    continue
                if not isinstance(reason, str) or reason.strip() == "":
                    errors.append(
                        f"spec #{snapshot.number} {unit_id} -> #{provider}: reason required"
                    )
                try:
                    _require_nonempty_strings(
                        requirement.get("basis"),
                        f"spec #{snapshot.number} {unit_id} -> #{provider} basis",
                    )
                except ToSpecsError as exc:
                    errors.append(str(exc))
                provider_snapshot = snapshot_by_number.get(provider)
                if provider_snapshot is None:
                    errors.append(
                        f"spec #{snapshot.number} {unit_id}: provider #{provider} snapshot "
                        "absent from bounded sibling/provider set"
                    )
                    continue
                if provider_snapshot.state == "OPEN" and not _reachable(
                    graph, snapshot.number, provider
                ):
                    errors.append(
                        f"spec #{snapshot.number} {unit_id}: open provider #{provider} is "
                        "required for completion but no native prerequisite path protects "
                        "the consumer"
                    )

        if len(set(unit_ids)) != len(unit_ids):
            errors.append(f"spec #{snapshot.number}: duplicate unit_analysis unit_id")
        topology_units = snapshot.topology_units
        assert topology_units is not None
        if set(unit_ids) != set(topology_units):
            missing = sorted(set(topology_units) - set(unit_ids))
            extra = sorted(set(unit_ids) - set(topology_units))
            errors.append(
                f"spec #{snapshot.number}: unit_analysis must exactly cover current topology; "
                f"missing={missing} extra={extra}"
            )

    if errors:
        raise ToSpecsError("\n".join(errors))

    frontier: list[int] = []
    for number in order:
        snapshot = snapshot_by_number[number]
        if snapshot.state != "OPEN":
            continue
        open_blockers = [
            blocker
            for blocker in snapshot.blocked_by
            if blocker not in snapshot_by_number
            or snapshot_by_number[blocker].state == "OPEN"
        ]
        if not open_blockers:
            frontier.append(number)

    return manifest, snapshots, frontier


def check_feasibility(path: Path) -> str:
    manifest, snapshots, frontier = validate_manifest(path)
    unit_count = sum(len(item.topology_units or ()) for item in snapshots)
    legacy_count = sum(item.is_legacy_completed for item in snapshots)
    frontier_text = ", ".join(f"#{number}" for number in frontier) or "none"
    return "\n".join(
        [
            "SPEC EXECUTION FEASIBILITY: VALID",
            f"Specs analyzed: {len(snapshots)}",
            f"Execution units analyzed: {unit_count}",
            f"Legacy completed Specs: {legacy_count}",
            "Unprotected pending provider requirements: 0",
            f"Actionable frontier: {frontier_text}",
            f"Feasibility manifest SHA-256: {_manifest_hash(manifest)}",
        ]
    )


def build_handoff_manifest(feasibility_path: Path, output: Path) -> str:
    manifest, snapshots, frontier = validate_manifest(feasibility_path)
    _need(frontier, "handoff: no actionable frontier; do not create an empty handoff")
    by_number = {item.number: item for item in snapshots}
    planning_source = manifest["planning_source"].strip()
    sources = [planning_source]
    handoffs: list[dict[str, Any]] = []
    for number in frontier:
        snapshot = by_number[number]
        if snapshot.url not in sources:
            sources.append(snapshot.url)
        handoffs.append(
            {
                "destination": "$to-tickets",
                "artifact": {"title": snapshot.title, "url": snapshot.url},
            }
        )
    handoff = {
        "schema": HANDOFF_SCHEMA,
        "boundary": "human-lifecycle",
        "durability": {"verified": True, "sources": sources},
        "handoffs": handoffs,
    }
    output.write_text(
        json.dumps(handoff, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return "TO-SPECS HANDOFF MANIFEST: VALID"


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
        raise ToSpecsError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"git {' '.join(args)} failed"
        )
    return result.stdout.strip()


def preflight(repo: Path, main_ref: str) -> str:
    dirty = _git(repo, "status", "--porcelain")
    _need(
        dirty == "",
        "preflight: worktree is dirty; use a separate clean planning worktree",
    )
    _git(repo, "rev-parse", "--verify", main_ref)
    stale: list[str] = []
    for path in CONTROL_PLANE_PATHS:
        head_blob = _git(repo, "rev-parse", f"HEAD:{path}")
        main_blob = _git(repo, "rev-parse", f"{main_ref}:{path}")
        if head_blob != main_blob:
            stale.append(path)
    _need(
        not stale,
        "preflight: to-specs control-plane bytes are stale relative to current main: "
        + ", ".join(stale),
    )
    return "\n".join(
        [
            "TO-SPECS PREFLIGHT: VALID",
            "Worktree: clean",
            f"Control-plane ref: {main_ref}",
            f"Control-plane paths current: {len(CONTROL_PLANE_PATHS)}",
        ]
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight")
    pre.add_argument("--repo", type=Path, default=Path("."))
    pre.add_argument("--main-ref", default="origin/main")

    check = sub.add_parser("check-feasibility")
    check.add_argument("--manifest", type=Path, required=True)

    handoff = sub.add_parser("build-handoff")
    handoff.add_argument("--manifest", type=Path, required=True)
    handoff.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "preflight":
            print(preflight(args.repo, args.main_ref))
        elif args.command == "check-feasibility":
            print(check_feasibility(args.manifest))
        elif args.command == "build-handoff":
            print(build_handoff_manifest(args.manifest, args.output))
        else:
            raise ToSpecsError(f"unsupported command: {args.command}")
        return 0
    except ToSpecsError as exc:
        header = {
            "preflight": "TO-SPECS PREFLIGHT: INVALID",
            "check-feasibility": "SPEC EXECUTION FEASIBILITY: INVALID",
            "build-handoff": "TO-SPECS HANDOFF MANIFEST: INVALID",
        }[args.command]
        print(f"{header}\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
