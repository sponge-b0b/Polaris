#!/usr/bin/env python3
"""Deterministic checkpoint and persistence artifacts for ``$review-spec``."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
CELL_RE = re.compile(r"^(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?$")
RF_RE = re.compile(r"^RF-\d+$")
VERIFY_HEADER = "## Spec Verification Receipt"
EXIT_HEADER = "## Spec Review Exit Receipt"
FINDING_LEDGER_MARKER = "<!-- review-spec-finding-ledger:v1 -->"
FINDING_LEDGER_HEADER = "## Review Finding Continuity Ledger"
FINDING_STATUSES = {"open", "satisfied", "invalidated", "owner-overridden", "scope-retired"}
TERMINAL_FINDING_STATUSES = FINDING_STATUSES - {"open"}
FINDING_SEVERITIES = {"blocking", "advisory"}
FINDING_ROUTINGS = {"ordinary-remediation", "decomposition-defect", "architecture-remediation", "advisory"}
RECEIPT_FORMAT_V2 = "manifest-table-v2"
SPEC_CONTRACT_ENCODING = "V2"
TCM_HEADER = "## Ticket Coverage Manifest"
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


def _contract_encoding(value: Any, label: str = "Spec Contract Encoding") -> str:
    encoding = _text(value, label)
    _require(
        encoding == SPEC_CONTRACT_ENCODING,
        f"{label} must be {SPEC_CONTRACT_ENCODING}",
    )
    return encoding


def _persisted_contract_encoding(lines: list[str], label: str) -> str:
    encoding = _optional_field(lines, "Spec Contract Encoding")
    if encoding is None:
        return "legacy-unversioned"
    return _contract_encoding(encoding, label)


def _plain_field(lines: list[str], label: str) -> str:
    prefix = f"{label}: "
    matches = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    _require(len(matches) == 1, f"TCM must contain exactly one {label} field")
    return matches[0].strip()


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _field(lines: list[str], label: str) -> str:
    prefix = f"**{label}:** "
    matches = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    _require(len(matches) == 1, f"receipt must contain exactly one {label} field")
    return matches[0].strip()


def _optional_field(lines: list[str], label: str) -> str | None:
    prefix = f"**{label}:** "
    matches = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    _require(len(matches) <= 1, f"receipt must contain at most one {label} field")
    return matches[0].strip() if matches else None


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


def _split_table_row_v2(line: str) -> list[str]:
    text = line.strip()
    _require(text.startswith("|") and text.endswith("|"), "invalid manifest table row")
    return [
        html.unescape(cell.strip().replace("<br>", "\n"))
        for cell in text[1:-1].split("|")
    ]


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
    format_version = _optional_field(lines, "Receipt format")
    if format_version is None:
        splitter = _split_table_row
    else:
        _require(
            format_version == RECEIPT_FORMAT_V2,
            f"unsupported receipt format: {format_version}",
        )
        splitter = _split_table_row_v2

    section = _section(lines, "### Spec Contract Manifest")
    rows = [line for line in section if line.startswith("|")]
    _require(len(rows) >= 3, "verification receipt manifest is empty")
    _require(
        splitter(rows[0]) == ["Cell", "Source", "Requirement"],
        "invalid manifest header",
    )
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows[2:]:
        cells = splitter(row)
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


def parse_verification_manifest(receipt_body: str) -> list[dict[str, str]]:
    lines = receipt_body.splitlines()
    _require(VERIFY_HEADER in lines, "receipt is not a Spec Verification Receipt")
    return _manifest(lines)


def _coverage(
    lines: list[str],
    manifest_cells: list[str],
) -> dict[str, list[str]]:
    section = _section(lines, "### Spec Contract Coverage")
    result: dict[str, list[str]] = {}
    for state in ("proven", "not-applicable", "unresolved"):
        prefix = f"- {state}: "
        matches = [
            line[len(prefix) :].strip() for line in section if line.startswith(prefix)
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
            line[len(prefix) :].strip() for line in section if line.startswith(prefix)
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
    contract_encoding = _contract_encoding(
        _field(lines, "Spec Contract Encoding"),
        "verification receipt Spec Contract Encoding",
    )
    contract_hash = _digest(
        _field(lines, "Spec Contract Hash"),
        "Spec Contract Hash",
    )

    tcm = summary.get("ticket_coverage_manifest")
    _require(isinstance(tcm, dict), "current Ticket Coverage Manifest is missing")
    tcm_body = _text(tcm.get("body"), "Ticket Coverage Manifest body")
    tcm_lines = tcm_body.splitlines()
    _require(TCM_HEADER in tcm_lines, "invalid Ticket Coverage Manifest")
    _require(
        _digest(_plain_field(tcm_lines, "Spec Body Hash"), "TCM Spec Body Hash")
        == body_hash,
        "Ticket Coverage Manifest Spec Body Hash mismatch",
    )
    _require(
        _contract_encoding(
            _plain_field(tcm_lines, "Spec Contract Encoding"),
            "TCM Spec Contract Encoding",
        )
        == contract_encoding,
        "Ticket Coverage Manifest Spec Contract Encoding mismatch",
    )
    _require(
        _digest(_plain_field(tcm_lines, "Spec Contract Hash"), "TCM Spec Contract Hash")
        == contract_hash,
        "Ticket Coverage Manifest Spec Contract Hash mismatch",
    )
    verification_hash = _digest(
        _field(lines, "Verification Hash"),
        "Verification Hash",
    )
    ownership = _field(lines, "Default ownership point")
    _require("@" in ownership, "invalid default ownership point")
    default_branch, default_head = ownership.rsplit("@", 1)
    _sha(default_head, "default ownership HEAD")

    manifest = parse_verification_manifest(receipt_body)
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
            line[len(prefix) :].strip() for line in integrity if line.startswith(prefix)
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
        "spec_contract_encoding": contract_encoding,
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




def _positive_int(value: Any, label: str) -> int:
    _require(type(value) is int and value > 0, f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    _require(type(value) is int and value >= 0, f"{label} must be a non-negative integer")
    return value


def _finding_rows(value: Any) -> list[dict[str, Any]]:
    _require(isinstance(value, list), "findings must be a list")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        _require(isinstance(raw, dict), "finding row must be an object")
        finding_id = _text(raw.get("id"), "finding id")
        _require(bool(RF_RE.fullmatch(finding_id)), f"invalid finding id {finding_id}")
        _require(finding_id not in seen, f"duplicate finding id {finding_id}")
        seen.add(finding_id)
        severity = _text(raw.get("severity"), f"{finding_id} severity")
        _require(severity in FINDING_SEVERITIES, f"invalid {finding_id} severity")
        axes = _list(raw.get("axes"), f"{finding_id} axes")
        _require(bool(axes), f"{finding_id} axes must be non-empty")
        _require(
            all(axis in {"Standards", "Spec", "Architecture"} for axis in axes),
            f"invalid {finding_id} axis",
        )
        status = _text(raw.get("status"), f"{finding_id} status")
        _require(status in FINDING_STATUSES, f"invalid {finding_id} status")
        routing = _text(raw.get("routing"), f"{finding_id} routing")
        _require(routing in FINDING_ROUTINGS, f"invalid {finding_id} routing")
        boundary = _list(raw.get("invalidation_boundary"), f"{finding_id} invalidation boundary")
        if severity == "blocking":
            _require(bool(boundary), f"{finding_id} Blocking finding requires invalidation boundary")
        disposition = str(raw.get("disposition_evidence") or "").strip()
        if status in TERMINAL_FINDING_STATUSES:
            _require(bool(disposition), f"{finding_id} terminal status requires disposition evidence")
        rows.append(
            {
                "id": finding_id,
                "severity": severity,
                "axes": axes,
                "invariant": _text(raw.get("invariant"), f"{finding_id} invariant"),
                "status": status,
                "routing": routing,
                "authority": _text(raw.get("authority"), f"{finding_id} authority"),
                "evidence": _text(raw.get("evidence"), f"{finding_id} evidence"),
                "invalidation_boundary": boundary,
                "origin": _text(raw.get("origin"), f"{finding_id} origin"),
                "disposition_evidence": disposition,
            }
        )
    return sorted(rows, key=lambda row: int(row["id"].split("-", 1)[1]))


def parse_finding_ledger(body: str) -> dict[str, Any]:
    lines = body.splitlines()
    _require(FINDING_LEDGER_MARKER in lines, "finding ledger marker missing")
    _require(FINDING_LEDGER_HEADER in lines, "finding ledger header missing")
    parent = _text(_field(lines, "Parent Spec"), "Parent Spec")
    review = _text(_field(lines, "Spec Review"), "Spec Review")
    _require(parent.startswith("#") and parent[1:].isdigit(), "invalid Parent Spec")
    _require(review.startswith("#") and review[1:].isdigit(), "invalid Spec Review")
    head = _sha(_field(lines, "Reviewed HEAD"), "finding ledger Reviewed HEAD")
    body_hash = _digest(_field(lines, "Spec Body Hash"), "finding ledger Spec Body Hash")
    contract_encoding = _persisted_contract_encoding(
        lines,
        "finding ledger Spec Contract Encoding",
    )
    contract_hash = _digest(_field(lines, "Spec Contract Hash"), "finding ledger Spec Contract Hash")
    try:
        start = lines.index("```json") + 1
        end = lines.index("```", start)
    except ValueError as exc:
        raise ArtifactError("finding ledger JSON block missing") from exc
    payload = json.loads("\n".join(lines[start:end]))
    rows = _finding_rows(payload)
    return {
        "parent_spec": int(parent[1:]),
        "spec_review": int(review[1:]),
        "head": head,
        "spec_body_hash": body_hash,
        "spec_contract_encoding": contract_encoding,
        "spec_contract_hash": contract_hash,
        "findings": rows,
    }


def render_finding_ledger(raw: Any, prior_body: str | None = None) -> str:
    _require(isinstance(raw, dict), "finding ledger input must be an object")
    parent_spec = _positive_int(raw.get("parent_spec"), "parent_spec")
    spec_review = _positive_int(raw.get("spec_review"), "spec_review")
    head = _sha(raw.get("head"), "finding ledger reviewed HEAD")
    body_hash = _digest(raw.get("spec_body_hash"), "finding ledger Spec Body Hash")
    contract_encoding = _contract_encoding(raw.get("spec_contract_encoding"), "finding ledger Spec Contract Encoding")
    contract_hash = _digest(raw.get("spec_contract_hash"), "finding ledger Spec Contract Hash")
    rows = _finding_rows(raw.get("findings"))

    if prior_body is not None:
        prior = parse_finding_ledger(prior_body)
        _require(prior["parent_spec"] == parent_spec, "finding ledger Parent Spec changed")
        _require(prior["spec_review"] == spec_review, "finding ledger Spec Review changed")
        _require(
            prior["spec_body_hash"] == body_hash,
            "finding ledger Spec Body Hash changed",
        )
        _require(
            prior["spec_contract_hash"] == contract_hash,
            "finding ledger Spec Contract Hash changed",
        )
        _require(
            prior["spec_contract_encoding"] in {
                "legacy-unversioned",
                SPEC_CONTRACT_ENCODING,
            },
            "finding ledger Spec Contract Encoding is incompatible",
        )
        current_by_id = {row["id"]: row for row in rows}
        prior_rows = prior["findings"]
        prior_max = max((int(row["id"].split("-", 1)[1]) for row in prior_rows), default=0)
        for old in prior_rows:
            _require(old["id"] in current_by_id, f"prior finding omitted: {old['id']}")
            new = current_by_id[old["id"]]
            for stable in ("severity", "axes", "invariant", "origin"):
                _require(new[stable] == old[stable], f"{old['id']} changed stable field {stable}")
            if old["status"] in TERMINAL_FINDING_STATUSES:
                _require(new["status"] == old["status"], f"terminal finding reopened: {old['id']}")
        for row in rows:
            number = int(row["id"].split("-", 1)[1])
            if row["id"] not in {old["id"] for old in prior_rows}:
                _require(number > prior_max, f"new finding ID reuses historical range: {row['id']}")

    lines = [
        FINDING_LEDGER_MARKER,
        FINDING_LEDGER_HEADER,
        "",
        f"**Parent Spec:** #{parent_spec}",
        f"**Spec Review:** #{spec_review}",
        f"**Reviewed HEAD:** {head}",
        f"**Spec Body Hash:** {body_hash}",
        f"**Spec Contract Encoding:** {contract_encoding}",
        f"**Spec Contract Hash:** {contract_hash}",
        "",
        "```json",
        json.dumps(rows, indent=2, sort_keys=True),
        "```",
    ]
    return "\n".join(lines) + "\n"

def render_pending(raw: Any) -> str:
    _require(isinstance(raw, dict), "pending input must be an object")
    head = _sha(raw.get("head"), "reviewed HEAD")
    baseline = _sha(raw.get("baseline"), "reviewed baseline")
    branch = _text(raw.get("branch"), "branch")
    body_hash = _digest(raw.get("spec_body_hash"), "Spec Body Hash")
    contract_encoding = _contract_encoding(raw.get("spec_contract_encoding"))
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
        f"**Spec Contract Encoding:** {contract_encoding}",
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
        (f"- Saturation challengers: {int(coverage.get('saturation_challengers', 0))}"),
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


def render_exit(raw: Any, finding_ledger_body: str) -> str:
    _require(isinstance(raw, dict), "exit input must be an object")
    head = _sha(raw.get("head"), "reviewed HEAD")
    baseline = _sha(raw.get("baseline"), "reviewed baseline")
    branch = _text(raw.get("branch"), "branch")
    body_hash = _digest(raw.get("spec_body_hash"), "Spec Body Hash")
    contract_encoding = _contract_encoding(raw.get("spec_contract_encoding"))
    contract_hash = _digest(raw.get("spec_contract_hash"), "Spec Contract Hash")
    parent_spec = _positive_int(raw.get("parent_spec"), "parent_spec")
    spec_review = _positive_int(raw.get("spec_review"), "spec_review")
    ledger = parse_finding_ledger(finding_ledger_body)
    _require(ledger["parent_spec"] == parent_spec, "finding ledger Parent Spec mismatch")
    _require(ledger["spec_review"] == spec_review, "finding ledger Spec Review mismatch")
    _require(ledger["head"] == head, "finding ledger HEAD mismatch")
    _require(ledger["spec_body_hash"] == body_hash, "finding ledger Spec Body Hash mismatch")
    _require(ledger["spec_contract_encoding"] == contract_encoding, "finding ledger Spec Contract Encoding mismatch")
    _require(ledger["spec_contract_hash"] == contract_hash, "finding ledger Spec Contract Hash mismatch")

    open_blocking = [
        row for row in ledger["findings"]
        if row["severity"] == "blocking" and row["status"] == "open"
    ]
    open_decomposition = [
        row for row in open_blocking if row["routing"] == "decomposition-defect"
    ]
    _require(not open_blocking, "open Blocking findings prevent Exit Receipt")
    _require(not open_decomposition, "unresolved decomposition defects prevent Exit Receipt")

    unaccounted = _nonnegative_int(raw.get("unaccounted_prior_findings"), "unaccounted prior findings")
    unresolved_continuity = _nonnegative_int(raw.get("unresolved_continuity_cells"), "unresolved continuity cells")
    active_roots = _nonnegative_int(raw.get("active_root_blockers"), "active root blockers")
    candidate_roots = _nonnegative_int(raw.get("candidate_new_roots"), "candidate new roots")
    unchecked = _nonnegative_int(raw.get("unchecked_coverage_cells"), "unchecked coverage cells")
    unresolved_challenges = _nonnegative_int(raw.get("unresolved_challenges"), "unresolved challenges")
    _require(unaccounted == 0, "unaccounted prior findings prevent Exit Receipt")
    _require(unresolved_continuity == 0, "unresolved continuity cells prevent Exit Receipt")
    _require(active_roots == 0, "active root blockers prevent Exit Receipt")
    _require(candidate_roots == 0, "candidate new roots prevent Exit Receipt")
    _require(unchecked == 0, "unchecked coverage cells prevent Exit Receipt")
    _require(unresolved_challenges == 0, "unresolved challenges prevent Exit Receipt")
    _require(_text(raw.get("review_coverage"), "review coverage") == "complete", "review coverage is incomplete")

    ledger_hash = hashlib.sha256(finding_ledger_body.encode("utf-8")).hexdigest()
    lines = [
        EXIT_HEADER,
        "",
        "**Status:** passed",
        f"**Spec Review:** #{spec_review}",
        f"**Reviewed HEAD:** {head}",
        f"**Reviewed Baseline:** {baseline}",
        f"**Branch:** {branch}",
        f"**Spec Body Hash:** {body_hash}",
        f"**Spec Contract Encoding:** {contract_encoding}",
        f"**Spec Contract Hash:** {contract_hash}",
        f"**Finding Ledger Hash:** {ledger_hash}",
        "**Blocking findings:** 0",
        "**Open blocking findings:** 0",
        "**Unaccounted prior findings:** 0",
        "**Unresolved continuity cells:** 0",
        "**Unresolved decomposition defects:** 0",
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
            f"{_text(raw.get('reviewer_execution_override'), 'reviewer execution override')}"
        ),
    ]
    return "\n".join(lines) + "\n"

def self_test() -> None:
    legacy = "\n".join(
        [
            VERIFY_HEADER,
            "",
            "### Spec Contract Manifest",
            "| Cell | Source | Requirement |",
            "| --- | --- | --- |",
            r"| ID-7 | Implementation Decisions 7 | NO_CANDIDATES \| EXPLICIT_CREATE_NEW |",
        ]
    )
    assert parse_verification_manifest(legacy)[0]["requirement"] == (
        "NO_CANDIDATES | EXPLICIT_CREATE_NEW"
    )

    v2 = "\n".join(
        [
            VERIFY_HEADER,
            f"**Receipt format:** {RECEIPT_FORMAT_V2}",
            "",
            "### Spec Contract Manifest",
            "| Cell | Source | Requirement |",
            "| --- | --- | --- |",
            (
                "| ID-7 | Implementation Decisions &#124; 7 | "
                "NO_CANDIDATES &#124; EXPLICIT_CREATE_NEW \\ literal<br>"
                "line two &lt;br&gt; &amp; markup |"
            ),
        ]
    )
    parsed = parse_verification_manifest(v2)[0]
    assert parsed["source"] == "Implementation Decisions | 7"
    assert parsed["requirement"] == (
        "NO_CANDIDATES | EXPLICIT_CREATE_NEW \\ literal\nline two <br> & markup"
    )

    malformed = legacy.replace(r"\|", r"\\|")
    try:
        parse_verification_manifest(malformed)
    except ArtifactError:
        pass
    else:
        raise AssertionError("double-escaped legacy manifest row was accepted")

    spec_body = "## Problem\nContract coherence regression"
    body_hash = hashlib.sha256(spec_body.encode("utf-8")).hexdigest()
    contract_hash = "c" * 64
    receipt = "\n".join(
        [
            VERIFY_HEADER,
            "",
            "**Status:** passed",
            f"**Receipt format:** {RECEIPT_FORMAT_V2}",
            "**Spec:** #1",
            f"**Verified HEAD:** {'a' * 40}",
            f"**Verified Baseline:** {'d' * 40}",
            "**Branch:** spec-1",
            f"**Spec Body Hash:** {body_hash}",
            f"**Spec Contract Encoding:** {SPEC_CONTRACT_ENCODING}",
            f"**Spec Contract Hash:** {contract_hash}",
            f"**Verification Hash:** {'f' * 64}",
            f"**Default ownership point:** main@{'e' * 40}",
            "",
            "### Spec Contract Integrity",
            "- User Stories: 1",
            "- Implementation Decisions: 0",
            "- Testing Decisions: 0",
            "- Out of Scope: 0",
            "- Other normative source items: 0",
            "- Manifest cells: 1",
            "- Unmapped source items: 0",
            "- Duplicate source mappings: 0",
            "- Ambiguous source items: 0",
            "",
            "### Spec Contract Manifest",
            "| Cell | Source | Requirement |",
            "| --- | --- | --- |",
            "| US-1 | User Stories 1 | coherent contract |",
            "",
            "### Spec Contract Coverage",
            "- proven: US-1",
            "- not-applicable: None",
            "- unresolved: None",
        ]
    )
    tcm = "\n".join(
        [
            TCM_HEADER,
            f"Spec Body Hash: {body_hash}",
            f"Spec Contract Encoding: {SPEC_CONTRACT_ENCODING}",
            f"Spec Contract Hash: {contract_hash}",
            "US-1 -> implementation ticket #1",
        ]
    )
    summary = {
        "baseline_commit": "d" * 40,
        "latest_receipt": {"id": 7, "html_url": "https://example.test/7", "body": receipt},
        "ticket_coverage_manifest": {"id": 8, "body": tcm},
    }
    coherent = checkpoint(summary, spec_body, 1, "a" * 40, "spec-1")
    assert coherent["spec_contract_encoding"] == SPEC_CONTRACT_ENCODING

    for incoherent_tcm in (
        tcm.replace(f"Spec Contract Hash: {contract_hash}", f"Spec Contract Hash: {'9' * 64}"),
        tcm.replace(f"Spec Contract Encoding: {SPEC_CONTRACT_ENCODING}\n", ""),
    ):
        broken = json.loads(json.dumps(summary))
        broken["ticket_coverage_manifest"]["body"] = incoherent_tcm
        try:
            checkpoint(broken, spec_body, 1, "a" * 40, "spec-1")
        except ArtifactError:
            pass
        else:
            raise AssertionError(
                "contract-incoherent TCM was accepted despite matching Spec body/cell universe"
            )


    ledger_input = {
        "parent_spec": 1,
        "spec_review": 2,
        "head": "a" * 40,
        "spec_body_hash": "b" * 64,
        "spec_contract_encoding": SPEC_CONTRACT_ENCODING,
        "spec_contract_hash": "c" * 64,
        "findings": [
            {
                "id": "RF-1",
                "severity": "blocking",
                "axes": ["Spec"],
                "invariant": "required behavior remains intact",
                "status": "open",
                "routing": "ordinary-remediation",
                "authority": "Spec ID-1",
                "evidence": "current implementation violates the invariant",
                "invalidation_boundary": ["src/example.py", "Spec ID-1"],
                "origin": "review comment 1",
                "disposition_evidence": "",
            }
        ],
    }
    open_ledger = render_finding_ledger(ledger_input)
    legacy_open_ledger = open_ledger.replace(
        f"**Spec Contract Encoding:** {SPEC_CONTRACT_ENCODING}\n",
        "",
    )
    migrated_open_ledger = render_finding_ledger(ledger_input, legacy_open_ledger)
    assert f"**Spec Contract Encoding:** {SPEC_CONTRACT_ENCODING}" in migrated_open_ledger

    advanced_input = json.loads(json.dumps(ledger_input))
    advanced_input["head"] = "e" * 40
    advanced_open_ledger = render_finding_ledger(advanced_input, open_ledger)
    assert f"**Reviewed HEAD:** {'e' * 40}" in advanced_open_ledger

    mismatched_legacy = legacy_open_ledger.replace(
        f"**Spec Contract Hash:** {'c' * 64}",
        f"**Spec Contract Hash:** {'9' * 64}",
    )
    try:
        render_finding_ledger(ledger_input, mismatched_legacy)
    except ArtifactError:
        pass
    else:
        raise AssertionError("legacy finding ledger with a different hash was migrated")

    exit_input = {
        "parent_spec": 1,
        "spec_review": 2,
        "head": "a" * 40,
        "baseline": "d" * 40,
        "branch": "spec-1",
        "spec_body_hash": "b" * 64,
        "spec_contract_encoding": SPEC_CONTRACT_ENCODING,
        "spec_contract_hash": "c" * 64,
        "unaccounted_prior_findings": 0,
        "unresolved_continuity_cells": 0,
        "active_root_blockers": 0,
        "candidate_new_roots": 0,
        "unchecked_coverage_cells": 0,
        "unresolved_challenges": 0,
        "review_coverage": "complete",
        "primary_reviewers": "1",
        "targeted_challengers": 0,
        "saturation_challengers": 0,
        "reviewer_execution": "test",
        "reviewer_execution_override": "None",
    }
    try:
        render_exit(exit_input, open_ledger)
    except ArtifactError:
        pass
    else:
        raise AssertionError("Exit Receipt accepted an open Blocking finding")

    closed_input = json.loads(json.dumps(ledger_input))
    closed_input["findings"][0]["status"] = "satisfied"
    closed_input["findings"][0]["disposition_evidence"] = "current proof excludes the falsifier"
    closed_ledger = render_finding_ledger(closed_input, open_ledger)
    receipt = render_exit(exit_input, closed_ledger)
    assert "**Open blocking findings:** 0" in receipt
    assert "**Spec Review:** #2" in receipt

    omitted_input = dict(closed_input)
    omitted_input["findings"] = []
    try:
        render_finding_ledger(omitted_input, closed_ledger)
    except ArtifactError:
        pass
    else:
        raise AssertionError("finding ledger accepted omitted prior row")

    reopened_input = json.loads(json.dumps(closed_input))
    reopened_input["findings"][0]["status"] = "open"
    reopened_input["findings"][0]["disposition_evidence"] = ""
    try:
        render_finding_ledger(reopened_input, closed_ledger)
    except ArtifactError:
        pass
    else:
        raise AssertionError("finding ledger reopened terminal row")


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
    finding = sub.add_parser("render-finding-ledger")
    finding.add_argument("--input", required=True)
    finding.add_argument("--output", required=True)
    finding.add_argument("--prior-ledger")
    exit_parser = sub.add_parser("render-exit")
    exit_parser.add_argument("--input", required=True)
    exit_parser.add_argument("--finding-ledger", required=True)
    exit_parser.add_argument("--output", required=True)
    sub.add_parser("self-test")
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
        elif args.command == "render-finding-ledger":
            prior_body = (
                Path(args.prior_ledger).read_text(encoding="utf-8")
                if args.prior_ledger
                else None
            )
            Path(args.output).write_text(
                render_finding_ledger(_read_json(args.input), prior_body),
                encoding="utf-8",
            )
        elif args.command == "render-exit":
            Path(args.output).write_text(
                render_exit(
                    _read_json(args.input),
                    Path(args.finding_ledger).read_text(encoding="utf-8"),
                ),
                encoding="utf-8",
            )
        elif args.command == "self-test":
            self_test()
            print("REVIEW-SPEC ARTIFACT SELF-TEST: PASS")
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (OSError, json.JSONDecodeError, ArtifactError, ValueError) as exc:
        print(f"REVIEW-SPEC ARTIFACT ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
