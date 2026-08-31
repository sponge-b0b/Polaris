#!/usr/bin/env python3
"""Deterministic checkpoint and persistence artifacts for ``$review-spec``."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
CELL_RE = re.compile(r"^(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?$")
VERIFY_HEADER = "## Spec Verification Receipt"
EXIT_HEADER = "## Spec Review Exit Receipt"
SOURCE_LABELS = {
    "User Stories": "user_stories",
    "Implementation Decisions": "implementation_decisions",
    "Testing Decisions": "testing_decisions",
    "Out of Scope": "out_of_scope",
    "Other normative source items": "other_normative",
}


class ArtifactError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def _text(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and bool(value.strip()),
        f"{label} must be non-empty",
    )
    return value.strip()


def _sha(value: Any, label: str) -> str:
    value = _text(value, label)
    _require(bool(SHA_RE.fullmatch(value)), f"{label} must be a 40-char SHA")
    return value


def _digest(value: Any, label: str) -> str:
    value = _text(value, label)
    _require(bool(DIGEST_RE.fullmatch(value)), f"{label} must be a SHA-256 digest")
    return value


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _field(lines: list[str], label: str) -> str:
    prefix = f"**{label}:** "
    matches = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    _require(len(matches) == 1, f"receipt must contain exactly one {label} field")
    return matches[0].strip()


def _split_table_row(line: str) -> list[str]:
    text = line.strip()
    _require(text.startswith("|") and text.endswith("|"), "invalid manifest table row")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in text[1:-1]:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip().replace("<br>", "\n"))
            current = []
        else:
            current.append(char)
    current.append("\\" if escaped else "")
    cells.append("".join(current).strip().replace("<br>", "\n"))
    return cells


def _section(lines: list[str], header: str) -> list[str]:
    _require(header in lines, f"receipt missing {header}")
    start = lines.index(header) + 1
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("### "):
            end = index
            break
    return lines[start:end]


def _manifest(lines: list[str]) -> list[dict[str, str]]:
    section = _section(lines, "### Spec Contract Manifest")
    rows = [line for line in section if line.startswith("|")]
    _require(len(rows) >= 3, "verification receipt manifest is empty")
    _require(
        _split_table_row(rows[0]) == ["Cell", "Source", "Requirement"],
        "invalid manifest header",
    )
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows[2:]:
        cells = _split_table_row(row)
        _require(len(cells) == 3, "manifest row must have three columns")
        cell, source, requirement = cells
        _require(bool(CELL_RE.fullmatch(cell)), f"invalid manifest cell {cell}")
        _require(cell not in seen, f"duplicate manifest cell {cell}")
        _require(
            bool(source) and bool(requirement),
            f"manifest cell {cell} is incomplete",
        )
        seen.add(cell)
        result.append({"cell": cell, "source": source, "requirement": requirement})
    _require(bool(result), "verification receipt manifest is empty")
    return result


def _coverage(
    lines: list[str],
    manifest_cells: list[str],
) -> dict[str, list[str]]:
    section = _section(lines, "### Spec Contract Coverage")
    result: dict[str, list[str]] = {}
    for state in ("proven", "not-applicable", "unresolved"):
        prefix = f"- {state}: "
        matches = [
            line[len(prefix) :].strip()
            for line in section
            if line.startswith(prefix)
        ]
        _require(len(matches) == 1, f"coverage must contain exactly one {state} row")
        result[state] = (
            []
            if matches[0] == "None"
            else [item.strip() for item in matches[0].split(",")]
        )
    mapped = result["proven"] + result["not-applicable"] + result["unresolved"]
    _require(len(mapped) == len(set(mapped)), "coverage contains duplicate cells")
    _require(
        mapped == manifest_cells or set(mapped) == set(manifest_cells),
        "coverage does not match manifest",
    )
    _require(not result["unresolved"], "verification receipt has unresolved cells")
    return result


def _source_counts(lines: list[str]) -> dict[str, int]:
    section = _section(lines, "### Spec Contract Integrity")
    result: dict[str, int] = {}
    for label, key in SOURCE_LABELS.items():
        prefix = f"- {label}: "
        matches = [
            line[len(prefix) :].strip()
            for line in section
            if line.startswith(prefix)
        ]
        _require(len(matches) == 1, f"receipt must contain exactly one {label} count")
        _require(matches[0].isdigit(), f"{label} count must be numeric")
        result[key] = int(matches[0])
    return result


def checkpoint(
    summary: Any,
    body_text: str,
    spec: int,
    head: str,
    branch: str,
) -> dict[str, Any]:
    _require(isinstance(summary, dict), "comments summary must be an object")
    baseline = _sha(summary.get("baseline_commit"), "baseline")
    receipt = summary.get("latest_receipt")
    _require(isinstance(receipt, dict), "latest verification receipt is missing")
    receipt_body = _text(receipt.get("body"), "latest verification receipt body")
    lines = receipt_body.splitlines()
    _require(
        VERIFY_HEADER in lines,
        "latest receipt is not a Spec Verification Receipt",
    )
    _require(
        _field(lines, "Status") == "passed",
        "verification receipt status is not passed",
    )
    _require(
        _field(lines, "Spec") == f"#{spec}",
        "verification receipt Spec mismatch",
    )
    _require(
        _sha(_field(lines, "Verified HEAD"), "verified HEAD") == head,
        "verification receipt HEAD is stale",
    )
    _require(
        _sha(_field(lines, "Verified Baseline"), "verified baseline") == baseline,
        "verification receipt baseline mismatch",
    )
    _require(
        _field(lines, "Branch") == branch,
        "verification receipt branch mismatch",
    )

    body_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()
    _require(
        _digest(_field(lines, "Spec Body Hash"), "Spec Body Hash") == body_hash,
        "Spec body changed after verification",
    )
    contract_hash = _digest(
        _field(lines, "Spec Contract Hash"),
        "Spec Contract Hash",
    )
    verification_hash = _digest(
        _field(lines, "Verification Hash"),
        "Verification Hash",
    )
    ownership = _field(lines, "Default ownership point")
    _require("@" in ownership, "invalid default ownership point")
    default_branch, default_head = ownership.rsplit("@", 1)
    _sha(default_head, "default ownership HEAD")

    manifest = _manifest(lines)
    manifest_cells = [row["cell"] for row in manifest]
    integrity = _section(lines, "### Spec Contract Integrity")
    for label, expected in (
        ("Manifest cells", len(manifest)),
        ("Unmapped source items", 0),
        ("Duplicate source mappings", 0),
        ("Ambiguous source items", 0),
    ):
        prefix = f"- {label}: "
        matches = [
            line[len(prefix) :].strip()
            for line in integrity
            if line.startswith(prefix)
        ]
        _require(len(matches) == 1, f"receipt must contain one {label} row")
        _require(matches[0].isdigit(), f"{label} must be numeric")
        _require(int(matches[0]) == expected, f"receipt {label} is invalid")
    coverage = _coverage(lines, manifest_cells)
    source_counts = _source_counts(lines)

    return {
        "spec_issue": spec,
        "head": head,
        "baseline": baseline,
        "branch": branch,
        "spec_body_hash": body_hash,
        "spec_contract_hash": contract_hash,
        "verification_hash": verification_hash,
        "default_branch_at_verification": default_branch,
        "default_head_at_verification": default_head,
        "source_counts": source_counts,
        "manifest": manifest,
        "coverage": coverage,
        "receipt_id": receipt.get("id"),
        "receipt_url": receipt.get("html_url"),
    }


def _list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    _require(isinstance(value, list), f"{label} must be a list")
    return [_text(item, label) for item in value]


def _bullets(items: list[str]) -> list[str]:
    if not items:
        return ["None"]
    lines: list[str] = []
    for item in items:
        parts = item.splitlines() or [item]
        lines.append(f"- {parts[0]}")
        lines.extend(f"  {part}" for part in parts[1:])
    return lines


def render_pending(raw: Any) -> str:
    _require(isinstance(raw, dict), "pending input must be an object")
    head = _sha(raw.get("head"), "reviewed HEAD")
    baseline = _sha(raw.get("baseline"), "reviewed baseline")
    branch = _text(raw.get("branch"), "branch")
    body_hash = _digest(raw.get("spec_body_hash"), "Spec Body Hash")
    contract_hash = _digest(raw.get("spec_contract_hash"), "Spec Contract Hash")
    execution = _text(raw.get("reviewer_execution"), "reviewer execution")
    override = _text(
        raw.get("reviewer_execution_override"),
        "reviewer execution override",
    )
    timestamp = _text(raw.get("timestamp"), "timestamp")
    sections = {
        "Standards": _list(raw.get("standards"), "Standards finding"),
        "Spec": _list(raw.get("spec"), "Spec finding"),
        "Architecture": _list(raw.get("architecture"), "Architecture finding"),
        "Root Mappings": _list(raw.get("root_mappings"), "root mapping"),
        "Root State": _list(raw.get("root_state"), "root state"),
        "Provenance": _list(raw.get("provenance"), "provenance"),
        "Scope Corrections": _list(raw.get("scope_corrections"), "scope correction"),
        "Saturation": _list(raw.get("saturation"), "saturation"),
    }
    coverage = raw.get("coverage")
    effectiveness = raw.get("effectiveness")
    _require(isinstance(coverage, dict), "coverage must be an object")
    _require(isinstance(effectiveness, dict), "effectiveness must be an object")

    lines = [
        f"## Pending Review Remediation [{timestamp}]",
        "",
        "**Status:** pending",
        f"**Reviewed HEAD:** {head}",
        f"**Reviewed Baseline:** {baseline}",
        f"**Branch:** {branch}",
        f"**Spec Body Hash:** {body_hash}",
        f"**Spec Contract Hash:** {contract_hash}",
        f"**Reviewer execution:** {execution}",
        f"**Reviewer execution override:** {override}",
    ]
    for name in ("Standards", "Spec", "Architecture"):
        lines += ["", f"### {name}", *_bullets(sections[name])]
    lines += [
        "",
        "### Review Coverage",
        f"- Standards: {_text(coverage.get('standards'), 'Standards coverage')}",
        f"- Spec: {_text(coverage.get('spec'), 'Spec coverage')}",
        (
            "- Architecture: "
            f"{_text(coverage.get('architecture'), 'Architecture coverage')}"
        ),
        (
            "- Saturation challengers: "
            f"{int(coverage.get('saturation_challengers', 0))}"
        ),
        "",
        "### Reviewer Effectiveness",
        f"- Primary validated findings: {int(effectiveness.get('primary', 0))}",
        (
            "- Targeted challenger-only validated findings: "
            f"{int(effectiveness.get('targeted', 0))}"
        ),
        (
            "- Saturation-only validated findings: "
            f"{int(effectiveness.get('saturation', 0))}"
        ),
    ]
    for name in (
        "Root Mappings",
        "Root State",
        "Provenance",
        "Scope Corrections",
        "Saturation",
    ):
        lines += ["", f"### {name}", *_bullets(sections[name])]
    return "\n".join(lines) + "\n"


def render_exit(raw: Any) -> str:
    _require(isinstance(raw, dict), "exit input must be an object")
    head = _sha(raw.get("head"), "reviewed HEAD")
    baseline = _sha(raw.get("baseline"), "reviewed baseline")
    branch = _text(raw.get("branch"), "branch")
    body_hash = _digest(raw.get("spec_body_hash"), "Spec Body Hash")
    contract_hash = _digest(raw.get("spec_contract_hash"), "Spec Contract Hash")
    lines = [
        EXIT_HEADER,
        "",
        "**Status:** passed",
        f"**Reviewed HEAD:** {head}",
        f"**Reviewed Baseline:** {baseline}",
        f"**Branch:** {branch}",
        f"**Spec Body Hash:** {body_hash}",
        f"**Spec Contract Hash:** {contract_hash}",
        "**Blocking findings:** 0",
        "**Root blockers:** satisfied/owner-overridden/scope-retired",
        "**Candidate new roots:** 0",
        "**Review coverage:** complete",
        (
            "**Primary reviewers:** "
            f"{_text(raw.get('primary_reviewers'), 'primary reviewers')}"
        ),
        f"**Targeted challengers:** {int(raw.get('targeted_challengers', 0))}",
        f"**Saturation challengers:** {int(raw.get('saturation_challengers', 0))}",
        "**Unchecked coverage cells:** 0",
        (
            "**Reviewer execution:** "
            f"{_text(raw.get('reviewer_execution'), 'reviewer execution')}"
        ),
        (
            "**Reviewer execution override:** "
            f"{_text(
                raw.get('reviewer_execution_override'),
                'reviewer execution override',
            )}"
        ),
    ]
    return "\n".join(lines) + "\n"


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("checkpoint")
    check.add_argument("--comments-summary", required=True)
    check.add_argument("--spec-body", required=True)
    check.add_argument("--spec", required=True, type=int)
    check.add_argument("--head", required=True)
    check.add_argument("--branch", required=True)
    pending = sub.add_parser("render-pending")
    pending.add_argument("--input", required=True)
    pending.add_argument("--output", required=True)
    exit_parser = sub.add_parser("render-exit")
    exit_parser.add_argument("--input", required=True)
    exit_parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        if args.command == "checkpoint":
            result = checkpoint(
                _read_json(args.comments_summary),
                Path(args.spec_body).read_text(encoding="utf-8"),
                args.spec,
                args.head,
                args.branch,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "render-pending":
            Path(args.output).write_text(
                render_pending(_read_json(args.input)),
                encoding="utf-8",
            )
        elif args.command == "render-exit":
            Path(args.output).write_text(
                render_exit(_read_json(args.input)),
                encoding="utf-8",
            )
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (OSError, json.JSONDecodeError, ArtifactError, ValueError) as exc:
        print(f"REVIEW-SPEC ARTIFACT ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
