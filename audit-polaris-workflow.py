#!/usr/bin/env python3
"""
Polaris workflow consistency auditor.

Read-only by design:
- reads the local Git repository and workflow skill contracts;
- reads GitHub Issues, comments, hierarchy, native blockers, and Project v2;
- never mutates GitHub, repository files, issue state, dependencies, focus, or Project fields;
- writes only a local JSON audit report.

Exit codes:
  0 = all encoded invariants passed
  1 = one or more workflow/projection invariants failed
  2 = audit could not complete deterministically (unsupported contract/read failure)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

CONTRACT_BASE = "90e7ec92167c847db9d2b9e13b4adf24a9d1e8af"
EXPECTED_REPO = "sponge-b0b/Polaris"
PROJECT_TITLE = "Polaris"
MIN_GH_VERSION = (2, 97, 0)

FORMAL_TYPES = {
    "Wayfinder Map",
    "Wayfinder Decision",
    "Spec",
    "Implementation Ticket",
    "Spec Review",
    "Review Remediation Ticket",
}

PROJECT_FIELDS = [
    "Artifact Type",
    "Workflow State",
    "Delivery State",
    "Next Skill",
    "Work Status",
    "Intake State",
    "Priority",
    "Area",
    "Root Blocker",
    "Completed On",
]

EXPECTED_DELIVERY_OPTIONS = [
    "In Focus",
    "Eligible",
    "Denied",
    "Independent",
    "Released",
]

EXPECTED_ARTIFACT_OPTIONS = [
    "Idea",
    "Wayfinder Map",
    "Wayfinder Decision",
    "Spec",
    "Implementation Ticket",
    "Spec Review",
    "Review Remediation Ticket",
]

REQUIRED_WORKFLOW_OPTIONS = {
    "Intake",
    "Architecture Decision",
    "Ready to Spec",
    "Spec Delivery",
    "Ready to Ticket",
    "Ready to Implement",
    "Ready to Verify",
    "Ready to Review",
    "Review Remediation",
    "Awaiting Root Verification",
    "Architecture Remediation",
    "Ready to Merge",
    "Blocked",
    "Complete",
}

EXPECTED_WORK_STATUS_OPTIONS = [
    "Ready",
    "In Progress",
    "Blocked",
    "Done",
]

EXPECTED_NEXT_SKILL_OPTIONS = [
    "None",
    "$wayfinder",
    "$to-specs",
    "$to-tickets",
    "$implement-ticket",
    "$verify-spec",
    "$review-spec",
    "$architecture-remediation",
    "$verify-root-closure",
    "$spec-merge-cleanup",
    "$project-delivery-management",
]

# Exact base lifecycle route table understood by this audit contract.
EXPECTED_ROUTE_TABLE: dict[tuple[str, str], str] = {
    ("Wayfinder Map", "Architecture Decision"): "$wayfinder",
    ("Wayfinder Map", "Ready to Spec"): "$to-specs",
    ("Wayfinder Map", "Spec Delivery"): "None",
    ("Wayfinder Map", "Architecture Remediation"): "$wayfinder",
    ("Wayfinder Map", "Blocked"): "None",
    ("Wayfinder Map", "Complete"): "None",

    ("Wayfinder Decision", "Architecture Decision"): "$wayfinder",
    ("Wayfinder Decision", "Blocked"): "None",
    ("Wayfinder Decision", "Complete"): "None",

    ("Spec", "Ready to Ticket"): "$to-tickets",
    ("Spec", "Ready to Implement"): "None",
    ("Spec", "Ready to Verify"): "$verify-spec",
    ("Spec", "Ready to Review"): "$review-spec",
    ("Spec", "Review Remediation"): "None",
    ("Spec", "Architecture Remediation"): "$architecture-remediation",
    ("Spec", "Ready to Merge"): "$spec-merge-cleanup",
    ("Spec", "Blocked"): "None",
    ("Spec", "Complete"): "None",

    ("Implementation Ticket", "Ready to Implement"): "$implement-ticket",
    ("Implementation Ticket", "Architecture Remediation"): "$architecture-remediation",
    ("Implementation Ticket", "Blocked"): "None",
    ("Implementation Ticket", "Complete"): "None",

    ("Spec Review", "Review Remediation"): "$to-tickets or None",
    ("Spec Review", "Architecture Remediation"): "$architecture-remediation",
    ("Spec Review", "Blocked"): "None",
    ("Spec Review", "Complete"): "None",

    ("Review Remediation Ticket", "Ready to Implement"): "$implement-ticket",
    ("Review Remediation Ticket", "Awaiting Root Verification"): "$verify-root-closure",
    ("Review Remediation Ticket", "Architecture Remediation"): "$architecture-remediation",
    ("Review Remediation Ticket", "Blocked"): "None",
    ("Review Remediation Ticket", "Complete"): "None",
}

STATIC_FILES = [
    ".agents/skills/README.md",
    ".agents/skills/project-tracking/SKILL.md",
    ".agents/skills/project-delivery-management/SKILL.md",
    ".agents/skills/wayfinder/SKILL.md",
    ".agents/skills/to-specs/SKILL.md",
    ".agents/skills/to-tickets/SKILL.md",
    ".agents/skills/implement-ticket/SKILL.md",
    ".agents/skills/verify-spec/SKILL.md",
    ".agents/skills/review-spec/SKILL.md",
    ".agents/skills/review-spec-remediation/SKILL.md",
    ".agents/skills/verify-root-closure/SKILL.md",
    ".agents/skills/spec-merge-cleanup/SKILL.md",
    ".agents/skills/spec-contract/SKILL.md",
    ".agents/skills/architecture-remediation/SKILL.md",
]

STATIC_FORBIDDEN_PHRASES = {
    # Retired delivery vocabulary/semantics.
    "Wayfinder Delivery Overlay Sync": "retired overlay-sync mode name",
    "Focused Stalled": "retired Delivery State vocabulary",
    "descendants governed only by unfocused Wayfinders suppress `Next Skill`":
        "retired descendant Next Skill suppression rule",

    # Retired review producer/consumer contract. Current review state belongs
    # on one conventional Spec Review issue, including clean review.
    "create no Spec Review issue when none exists":
        "retired clean-review contract: no review issue",
    "persist Spec Review Exit Receipt on the Spec":
        "retired review receipt ownership: parent Spec",
    "No Spec Review issue is required on this path.":
        "retired clean-review contract: no review issue",
    "A **Spec Review issue is created only when Blocking findings remain":
        "retired conditional Spec Review issue contract",
    "A missing Spec Review issue is valid on a clean-review lifecycle":
        "retired cleanup contract allowing missing review issue",
    "persist Spec Review Exit Receipt on parent Spec":
        "retired review receipt ownership: parent Spec",
    "a Spec Review issue is **conditional remediation state**, not a mandatory stage":
        "retired conditional Spec Review artifact contract",
    "Do not create a `Spec Review:` issue simply because `$review-spec` ran.":
        "retired clean-review contract: review issue omitted",
    "Clean review records its Exit Receipt directly on the parent Spec.":
        "retired review receipt ownership: parent Spec",
    "do not create a Spec Review issue on a clean review":
        "retired clean-review contract: review issue omitted",
}

PROJECT_REVIEW_OWNER_MARKER = "**Parent Spec:** #"

WAYFINDER_SOURCE_RE = re.compile(r"wayfinder-source:\s*#(\d+)", re.IGNORECASE)
WAYFINDER_REMEDIATION_RE = re.compile(r"wayfinder-remediation:\s*#(\d+)", re.IGNORECASE)
DERIVED_SPEC_RE = re.compile(r"(?:\*\*)?Derived Spec:(?:\*\*)?\s*#(\d+)", re.IGNORECASE)
REMEDIATION_SPEC_RE = re.compile(r"(?:\*\*)?Remediation Spec:(?:\*\*)?\s*#(\d+)", re.IGNORECASE)
PARENT_SPEC_RE = re.compile(r"^Parent Spec:\s*#(\d+)\s*$", re.MULTILINE)
BOLD_PARENT_SPEC_RE = re.compile(r"^\*\*Parent Spec:\*\*\s*#(\d+)\s*$", re.MULTILINE)
PARENT_WAYFINDER_RE = re.compile(
    r"^(?:\*\*)?Parent Wayfinder:(?:\*\*)?\s*#(\d+)\s*$",
    re.MULTILINE,
)
REMEDIATION_PARENT_RE = re.compile(
    r"^Remediation parent:\s*Spec Review\s*#(\d+)\s*$",
    re.MULTILINE,
)
EXPLICIT_INDEPENDENT_RE = re.compile(
    r"(?:<!--\s*project-delivery:\s*independent\s*-->|"
    r"\*\*Project Delivery:\*\*\s*Independent)",
    re.IGNORECASE,
)

PASS_RECEIPT_STATUS_RE = re.compile(r"\*\*Status:\*\*\s*passed", re.IGNORECASE)


class AuditExecutionError(RuntimeError):
    pass


@dataclass
class Finding:
    severity: str  # FAIL | WARN | INFO
    layer: str
    check: str
    subject: str
    message: str
    expected: Any = None
    actual: Any = None
    evidence: Any = None


class Audit:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.metrics: dict[str, Any] = {}
        self.contract_files: dict[str, str] = {}

    def add(
        self,
        severity: str,
        layer: str,
        check: str,
        subject: str,
        message: str,
        *,
        expected: Any = None,
        actual: Any = None,
        evidence: Any = None,
    ) -> None:
        self.findings.append(
            Finding(
                severity=severity,
                layer=layer,
                check=check,
                subject=subject,
                message=message,
                expected=expected,
                actual=actual,
                evidence=evidence,
            )
        )

    def fail(self, *args: Any, **kwargs: Any) -> None:
        self.add("FAIL", *args, **kwargs)

    def warn(self, *args: Any, **kwargs: Any) -> None:
        self.add("WARN", *args, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        self.add("INFO", *args, **kwargs)

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "FAIL"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "WARN"]


def run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AuditExecutionError(f"required command not found: {cmd[0]}") from exc

    if proc.returncode != 0:
        rendered = " ".join(cmd)
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit={proc.returncode}"
        raise AuditExecutionError(f"command failed: {rendered}\n{detail}")
    return proc.stdout


def run_json(cmd: list[str], cwd: Path | None = None) -> Any:
    text = run(cmd, cwd=cwd)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuditExecutionError(
            f"command returned invalid JSON: {' '.join(cmd)}"
        ) from exc


def flatten_slurp(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise AuditExecutionError("expected paginated --slurp JSON array")
    out: list[dict[str, Any]] = []
    for page in value:
        if isinstance(page, list):
            out.extend(x for x in page if isinstance(x, dict))
        elif isinstance(page, dict):
            out.append(page)
        else:
            raise AuditExecutionError("unexpected element in paginated JSON")
    return out


def labels(issue: dict[str, Any]) -> set[str]:
    raw = issue.get("labels") or []
    out: set[str] = set()
    for item in raw:
        if isinstance(item, dict) and item.get("name"):
            out.add(str(item["name"]))
        elif isinstance(item, str):
            out.add(item)
    return out


def parent_number(issue: dict[str, Any]) -> int | None:
    parent = issue.get("parent")
    if isinstance(parent, dict) and parent.get("number") is not None:
        return int(parent["number"])
    return None


def blocker_snapshot(
    issue: dict[str, Any],
    audit: Audit,
    *,
    subject: str,
    fail_if_incomplete: bool = True,
) -> tuple[list[dict[str, Any]], bool]:
    raw = issue.get("blockedBy")
    if not isinstance(raw, dict):
        if fail_if_incomplete:
            audit.fail(
                "LIVE AUTHORITY",
                "native blocker completeness",
                subject,
                "blockedBy data is missing or not a complete connection object",
                actual=raw,
            )
        return [], False

    nodes = raw.get("nodes")
    total = raw.get("totalCount")
    if not isinstance(nodes, list) or not isinstance(total, int):
        if fail_if_incomplete:
            audit.fail(
                "LIVE AUTHORITY",
                "native blocker completeness",
                subject,
                "blockedBy nodes/totalCount are unreadable",
                actual=raw,
            )
        return [], False

    if len(nodes) != total:
        if fail_if_incomplete:
            audit.fail(
                "LIVE AUTHORITY",
                "native blocker completeness",
                subject,
                "blockedBy connection is truncated",
                expected=total,
                actual=len(nodes),
            )
        return nodes, False

    return [n for n in nodes if isinstance(n, dict)], True


def open_blocker_numbers(issue: dict[str, Any], audit: Audit, subject: str) -> list[int]:
    nodes, complete = blocker_snapshot(issue, audit, subject=subject)
    if not complete:
        return []
    result: list[int] = []
    for n in nodes:
        if str(n.get("state", "")).upper() == "OPEN":
            if n.get("number") is None:
                audit.fail(
                    "LIVE AUTHORITY",
                    "native blocker identity",
                    subject,
                    "open blocker is missing an issue number",
                    actual=n,
                )
                continue
            result.append(int(n["number"]))
    return sorted(set(result))


def normalize_route_cell(text: str) -> str:
    return text.strip().replace("`", "")


def parse_project_tracking_route_table(text: str) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    in_table = False
    for line in text.splitlines():
        if line.strip() == "| Artifact Type | Workflow State | Allowed base `Next Skill` |":
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("Context-sensitive `None` cases:"):
            break
        if not line.strip().startswith("|"):
            if result:
                break
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 3:
            continue
        if cells[0].startswith("---"):
            continue
        artifact, workflow, next_skill = map(normalize_route_cell, cells)
        result[(artifact, workflow)] = next_skill
    return result


def static_contract_audit(repo_root: Path, audit: Audit) -> dict[str, str]:
    contents: dict[str, str] = {}

    for rel in STATIC_FILES:
        path = repo_root / rel
        if not path.is_file():
            audit.fail(
                "STATIC CONTRACT",
                "required workflow file",
                rel,
                "required contract file is missing",
            )
            continue
        text = path.read_text(encoding="utf-8")
        contents[rel] = text
        audit.contract_files[rel] = hashlib.sha256(text.encode("utf-8")).hexdigest()

    all_skill_text = ""
    skills_root = repo_root / ".agents" / "skills"
    if skills_root.is_dir():
        chunks = []
        for path in sorted(skills_root.rglob("*.md")):
            try:
                chunks.append(f"\n<!-- {path.relative_to(repo_root)} -->\n")
                chunks.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                audit.fail(
                    "STATIC CONTRACT",
                    "UTF-8 skill source",
                    str(path.relative_to(repo_root)),
                    "skill Markdown is not valid UTF-8",
                )
        all_skill_text = "\n".join(chunks)

    stale_review_occurrences: list[dict[str, object]] = []
    review_phrases = {
        phrase: explanation
        for phrase, explanation in STATIC_FORBIDDEN_PHRASES.items()
        if "review" in explanation.lower()
    }
    for rel, text in contents.items():
        for phrase, explanation in review_phrases.items():
            for match in re.finditer(re.escape(phrase), text):
                line = text.count("\n", 0, match.start()) + 1
                stale_review_occurrences.append(
                    {
                        "file": rel,
                        "line": line,
                        "phrase": phrase,
                        "reason": explanation,
                    }
                )

    if stale_review_occurrences:
        audit.fail(
            "STATIC CONTRACT",
            "stale Spec Review cross-skill architecture",
            ".agents/skills",
            "retired clean-review/receipt-ownership semantics remain in cross-skill documentation",
            expected="one conventional Spec Review owns durable review state and final Exit Receipt",
            actual="retired conditional-review/parent-Spec receipt semantics still present",
            evidence=stale_review_occurrences,
        )

    tracking = contents.get(".agents/skills/project-tracking/SKILL.md", "")
    pdm = contents.get(".agents/skills/project-delivery-management/SKILL.md", "")
    readme = contents.get(".agents/skills/README.md", "")
    review = contents.get(".agents/skills/review-spec/SKILL.md", "")
    cleanup = contents.get(".agents/skills/spec-merge-cleanup/SKILL.md", "")

    required_tracking_phrases = [
        "### Delivery Overlay Sync",
        "one or more open native blockers → base `Work Status = Blocked`",
        "Delivery authorization never suppresses a descendant's lifecycle route.",
        "`blocked` | Blocked | preserve base | Denied",
    ]
    for phrase in required_tracking_phrases:
        if phrase not in tracking:
            audit.fail(
                "STATIC CONTRACT",
                "project-tracking delivery overlay",
                ".agents/skills/project-tracking/SKILL.md",
                f"required current contract phrase is missing: {phrase}",
            )

    required_pdm_phrases = [
        "every affected open Wayfinder-managed formal artifact",
        "every open Wayfinder-managed formal artifact under every open canonical Wayfinder",
        "derive its current authoritative `Project Delivery State` from **all** governing Wayfinders",
    ]
    for phrase in required_pdm_phrases:
        if phrase not in pdm:
            audit.fail(
                "STATIC CONTRACT",
                "project-delivery reconciliation scope",
                ".agents/skills/project-delivery-management/SKILL.md",
                f"required current contract phrase is missing: {phrase}",
            )

    # Producer/consumer review ownership must agree.
    review_required = [
        "conventional Spec Review issue",
        "final **Spec Review Exit Receipt** all belong on that one review issue",
    ]
    for phrase in review_required:
        if phrase not in review:
            audit.fail(
                "STATIC CONTRACT",
                "review producer ownership",
                ".agents/skills/review-spec/SKILL.md",
                f"review producer contract is missing: {phrase}",
            )

    cleanup_required = [
        "one conventional Spec Review issue",
        "recover the latest **Spec Review Exit Receipt** from that review issue",
        "Require exactly one match.",
    ]
    for phrase in cleanup_required:
        if phrase not in cleanup:
            audit.fail(
                "STATIC CONTRACT",
                "review consumer ownership",
                ".agents/skills/spec-merge-cleanup/SKILL.md",
                f"cleanup consumer contract is missing: {phrase}",
            )

    to_specs = contents.get(".agents/skills/to-specs/SKILL.md", "")
    area_contract = {
        ".agents/skills/README.md":
            "Area and Priority are presentation metadata, not workflow authority.",
        ".agents/skills/project-tracking/SKILL.md":
            "`Area` only when the caller intentionally owns an Area presentation change",
        ".agents/skills/to-specs/SKILL.md":
            "Preserve existing Project `Area`/`Priority` presentation unless this invocation "
            "has separate authority to change them",
    }
    for rel, phrase in area_contract.items():
        text = contents.get(rel, "")
        if phrase not in text:
            audit.fail(
                "STATIC CONTRACT",
                "Area projection ownership",
                rel,
                "required optional/preserved Area ownership rule is missing",
                expected=phrase,
            )

    tracking_area_rules = [
        "`Area` and `Priority` are preserved when omitted; either may be blank;",
        "`Area` → preserve unless caller supplied it; then set only when different;",
        "`Area` and `Priority` equal supplied values when supplied and otherwise equal their pre-mutation values;",
    ]
    for phrase in tracking_area_rules:
        if phrase not in tracking:
            audit.fail(
                "STATIC CONTRACT",
                "Area projection preservation",
                ".agents/skills/project-tracking/SKILL.md",
                f"required Area preservation rule is missing: {phrase}",
            )

    if "* `Area`;" in tracking:
        audit.fail(
            "STATIC CONTRACT",
            "Area projection ownership",
            ".agents/skills/project-tracking/SKILL.md",
            "Area is still required unconditionally by Formal Artifact Projection",
            expected="Area optional and preserved when omitted",
            actual="unconditional caller-supplied Area",
        )

    review_current_phrases = [
        "every reviewed Spec has exactly one conventional Spec Review issue",
        "persist Spec Review Exit Receipt on that review issue",
        "Duplicate or Parent-Owned Spec Review State",
    ]
    for phrase in review_current_phrases:
        if phrase not in readme:
            audit.fail(
                "STATIC CONTRACT",
                "current Spec Review cross-skill architecture",
                ".agents/skills/README.md",
                f"required current review contract is missing: {phrase}",
            )

    # Cross-skill README review ownership is covered by the localized stale
    # review architecture finding above to avoid counting one defect repeatedly.

    actual_routes = parse_project_tracking_route_table(tracking)
    missing_routes = sorted(set(EXPECTED_ROUTE_TABLE) - set(actual_routes))
    extra_routes = sorted(set(actual_routes) - set(EXPECTED_ROUTE_TABLE))
    changed_routes = sorted(
        key for key in set(actual_routes) & set(EXPECTED_ROUTE_TABLE)
        if actual_routes[key] != EXPECTED_ROUTE_TABLE[key]
    )
    if missing_routes or extra_routes or changed_routes:
        audit.fail(
            "STATIC CONTRACT",
            "base route table",
            ".agents/skills/project-tracking/SKILL.md",
            "base lifecycle route table differs from the contract bound to this auditor",
            expected={
                f"{a} / {w}": n
                for (a, w), n in sorted(EXPECTED_ROUTE_TABLE.items())
            },
            actual={
                f"{a} / {w}": n
                for (a, w), n in sorted(actual_routes.items())
            },
            evidence={
                "missing": [f"{a} / {w}" for a, w in missing_routes],
                "extra": [f"{a} / {w}" for a, w in extra_routes],
                "changed": [f"{a} / {w}" for a, w in changed_routes],
            },
        )

    # Best-effort scan for explicit Project projection blocks in lifecycle skills.
    # This is intentionally conservative: only compare when Artifact Type,
    # Workflow State, and Next Skill are all explicitly present in a short block.
    projection_re = re.compile(
        r"Artifact Type:\s*(?P<artifact>[^\n]+)\n"
        r"(?:.*\n){0,4}?"
        r"Workflow State:\s*(?P<workflow>[^\n]+)\n"
        r"(?:.*\n){0,4}?"
        r"Next Skill:\s*(?P<next>[^\n]+)",
        re.MULTILINE,
    )
    for rel, text in contents.items():
        if not rel.endswith("/SKILL.md"):
            continue
        for match in projection_re.finditer(text):
            artifact = normalize_route_cell(match.group("artifact"))
            workflow = normalize_route_cell(match.group("workflow"))
            next_skill = normalize_route_cell(match.group("next"))
            key = (artifact, workflow)
            if key not in EXPECTED_ROUTE_TABLE:
                continue
            expected = EXPECTED_ROUTE_TABLE[key]
            if expected == "$to-tickets or None":
                if next_skill not in {"$to-tickets", "None", "$to-tickets or None"}:
                    audit.fail(
                        "STATIC CONTRACT",
                        "lifecycle producer route",
                        rel,
                        f"explicit projection block contradicts route table for {artifact} / {workflow}",
                        expected=expected,
                        actual=next_skill,
                    )
            elif next_skill != expected:
                audit.fail(
                    "STATIC CONTRACT",
                    "lifecycle producer route",
                    rel,
                    f"explicit projection block contradicts route table for {artifact} / {workflow}",
                    expected=expected,
                    actual=next_skill,
                )

    return contents


def artifact_type_from_tracker(
    issue: dict[str, Any],
    issues: dict[int, dict[str, Any]],
) -> tuple[str | None, str]:
    number = int(issue["number"])
    body = issue.get("body") or ""
    title = issue.get("title") or ""
    issue_labels = labels(issue)
    parent = parent_number(issue)

    if "wayfinder:map" in issue_labels:
        return "Wayfinder Map", "canonical wayfinder:map label"

    if title.startswith("Spec Review:") and BOLD_PARENT_SPEC_RE.search(body):
        return "Spec Review", "conventional Spec Review title + Parent Spec marker"

    remediation = REMEDIATION_PARENT_RE.search(body)
    if remediation and parent is not None and parent == int(remediation.group(1)):
        parent_issue = issues.get(parent)
        if parent_issue and str(parent_issue.get("title", "")).startswith("Spec Review:"):
            return (
                "Review Remediation Ticket",
                "native Spec Review parent + matching Remediation parent marker",
            )

    declared_spec = PARENT_SPEC_RE.search(body)
    if parent is not None:
        parent_issue = issues.get(parent)
        ticket_branch = re.search(
            r"^## Ticket branch\s*$", body, re.MULTILINE | re.IGNORECASE
        )
        ticket_baseline = re.search(
            r"^## Ticket baseline\s*$", body, re.MULTILINE | re.IGNORECASE
        )
        current_parent_link = (
            re.search(r"^## Parent\s*$", body, re.MULTILINE | re.IGNORECASE)
            and re.search(
                rf"https://github\.com/[^/]+/[^/]+/issues/{parent}(?:\)|\s|$)",
                body,
            )
        )
        legacy_parent_marker = (
            declared_spec is not None
            and parent == int(declared_spec.group(1))
        )
        if (
            parent_issue
            and str(parent_issue.get("title", "")).startswith("Spec:")
            and ticket_branch
            and ticket_baseline
            and (current_parent_link or legacy_parent_marker)
        ):
            evidence = (
                "native Spec parent + Parent issue link + Ticket branch/baseline"
                if current_parent_link
                else "native Spec parent + Parent Spec marker + Ticket branch/baseline"
            )
            return ("Implementation Ticket", evidence)

    declared_wayfinder = PARENT_WAYFINDER_RE.search(body)
    if parent is not None:
        parent_issue = issues.get(parent)
        parent_is_wayfinder = (
            parent_issue is not None
            and "wayfinder:map" in labels(parent_issue)
        )
        planning_identity = bool(
            {"wayfinder:task", "wayfinder:grilling"} & issue_labels
        )
        marker_matches = (
            declared_wayfinder is not None
            and parent == int(declared_wayfinder.group(1))
        )
        if parent_is_wayfinder and (planning_identity or marker_matches):
            evidence = (
                "native Wayfinder parent + matching Parent Wayfinder marker"
                if marker_matches
                else "native Wayfinder parent + Wayfinder planning label (legacy body shape)"
            )
            return ("Wayfinder Decision", evidence)

    if title.startswith("Spec:"):
        return "Spec", "conventional Spec title"

    return None, f"no durable formal-artifact signature for #{number}"


def project_list(projects_json: Any) -> list[dict[str, Any]]:
    if isinstance(projects_json, dict):
        for key in ("projects", "items", "nodes"):
            value = projects_json.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    if isinstance(projects_json, list):
        return [x for x in projects_json if isinstance(x, dict)]
    raise AuditExecutionError("unrecognized `gh project list --format json` response")


def field_list(fields_json: Any) -> list[dict[str, Any]]:
    if isinstance(fields_json, dict):
        for key in ("fields", "items", "nodes"):
            value = fields_json.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    if isinstance(fields_json, list):
        return [x for x in fields_json if isinstance(x, dict)]
    raise AuditExecutionError("unrecognized `gh project field-list --format json` response")


def field_options(field: dict[str, Any]) -> list[str]:
    raw = field.get("options") or []
    result = []
    for item in raw:
        if isinstance(item, dict) and item.get("name") is not None:
            result.append(str(item["name"]))
    return result


def audit_project_schema(
    fields: list[dict[str, Any]],
    audit: Audit,
) -> dict[str, dict[str, Any]]:
    by_name = {str(f.get("name")): f for f in fields if f.get("name")}

    for name in PROJECT_FIELDS:
        if name not in by_name:
            audit.fail(
                "PROJECT SCHEMA",
                "required field",
                PROJECT_TITLE,
                f"required Project field is missing: {name}",
            )

    def exact_options(name: str, expected: list[str]) -> None:
        field = by_name.get(name)
        if not field:
            return
        actual = field_options(field)
        if len(actual) != len(set(actual)) or set(actual) != set(expected):
            audit.fail(
                "PROJECT SCHEMA",
                "single-select options",
                name,
                "Project single-select vocabulary differs from audited contract",
                expected=sorted(expected),
                actual=sorted(actual),
            )

    exact_options("Delivery State", EXPECTED_DELIVERY_OPTIONS)
    exact_options("Artifact Type", EXPECTED_ARTIFACT_OPTIONS)
    exact_options("Work Status", EXPECTED_WORK_STATUS_OPTIONS)
    exact_options("Next Skill", EXPECTED_NEXT_SKILL_OPTIONS)

    workflow = by_name.get("Workflow State")
    if workflow:
        actual = set(field_options(workflow))
        missing = sorted(REQUIRED_WORKFLOW_OPTIONS - actual)
        if missing:
            audit.fail(
                "PROJECT SCHEMA",
                "workflow options",
                "Workflow State",
                "required workflow options are missing",
                expected=sorted(REQUIRED_WORKFLOW_OPTIONS),
                actual=sorted(actual),
                evidence={"missing": missing},
            )

    if "Focused Stalled" in field_options(by_name.get("Delivery State", {})):
        audit.fail(
            "PROJECT SCHEMA",
            "retired option",
            "Delivery State",
            "retired Focused Stalled option still exists",
        )

    if "Blocked" in field_options(by_name.get("Delivery State", {})):
        audit.fail(
            "PROJECT SCHEMA",
            "authorization vocabulary",
            "Delivery State",
            "Delivery State still exposes overloaded Blocked instead of Denied",
        )

    return by_name


def parse_project_items_tsv(text: str, audit: Audit) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.reader(text.splitlines(), delimiter="\t")
    expected_columns = 5 + len(PROJECT_FIELDS)
    for line_no, cells in enumerate(reader, 1):
        if not cells:
            continue
        if len(cells) < expected_columns:
            cells = cells + [""] * (expected_columns - len(cells))
        elif len(cells) > expected_columns:
            audit.fail(
                "PROJECT PROJECTION",
                "Project row shape",
                f"line {line_no}",
                "Project item-list row has unexpected extra columns",
                expected=expected_columns,
                actual=len(cells),
            )
            continue

        kind, title, number_raw, repo, item_id = cells[:5]
        values = dict(zip(PROJECT_FIELDS, cells[5:]))
        number = None
        if number_raw.strip():
            try:
                number = int(number_raw)
            except ValueError:
                audit.fail(
                    "PROJECT PROJECTION",
                    "Project issue number",
                    title,
                    "Project row issue number is not an integer",
                    actual=number_raw,
                )
        rows.append(
            {
                "kind": kind,
                "title": title,
                "number": number,
                "repo": repo,
                "item_id": item_id,
                "values": values,
            }
        )
    return rows


def comments_by_issue(comments: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for comment in comments:
        issue_url = str(comment.get("issue_url") or "")
        m = re.search(r"/issues/(\d+)$", issue_url)
        if m:
            grouped[int(m.group(1))].append(comment)
    for number in grouped:
        grouped[number].sort(
            key=lambda c: (str(c.get("created_at") or ""), int(c.get("id") or 0))
        )
    return grouped


def passing_comment(
    grouped: dict[int, list[dict[str, Any]]],
    issue_number: int,
    heading: str,
) -> dict[str, Any] | None:
    matches = []
    for comment in grouped.get(issue_number, []):
        body = str(comment.get("body") or "")
        if heading in body and PASS_RECEIPT_STATUS_RE.search(body):
            matches.append(comment)
    return matches[-1] if matches else None


def comments_contain(
    grouped: dict[int, list[dict[str, Any]]],
    issue_number: int,
    needle: str,
) -> bool:
    return any(needle in str(c.get("body") or "") for c in grouped.get(issue_number, []))


def spec_parent_from_review(issue: dict[str, Any]) -> int | None:
    body = issue.get("body") or ""
    m = BOLD_PARENT_SPEC_RE.search(body)
    return int(m.group(1)) if m else None


def spec_governance(
    specs: Iterable[int],
    issues: dict[int, dict[str, Any]],
    audit: Audit,
) -> tuple[
    dict[int, set[int]],
    dict[int, set[int]],
    dict[int, set[int]],
    dict[int, set[int]],
]:
    source: dict[int, set[int]] = defaultdict(set)
    remediation: dict[int, set[int]] = defaultdict(set)
    map_derived: dict[int, set[int]] = defaultdict(set)
    map_remediation: dict[int, set[int]] = defaultdict(set)

    for number, issue in issues.items():
        if "wayfinder:map" not in labels(issue):
            continue
        body = issue.get("body") or ""
        for spec_num in DERIVED_SPEC_RE.findall(body):
            map_derived[number].add(int(spec_num))
        for spec_num in REMEDIATION_SPEC_RE.findall(body):
            map_remediation[number].add(int(spec_num))

    for spec in specs:
        issue = issues[spec]
        body = issue.get("body") or ""
        source[spec] = {int(x) for x in WAYFINDER_SOURCE_RE.findall(body)}
        remediation[spec] = {int(x) for x in WAYFINDER_REMEDIATION_RE.findall(body)}

        for governor in sorted(source[spec] | remediation[spec]):
            g = issues.get(governor)
            if not g or "wayfinder:map" not in labels(g):
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec governing Wayfinder",
                    f"#{spec}",
                    f"Spec provenance references non-Wayfinder #{governor}",
                )

        for governor in sorted(source[spec]):
            if spec not in map_derived.get(governor, set()):
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec handoff reconciliation",
                    f"#{spec}",
                    f"wayfinder-source #{governor} lacks matching Derived Spec handoff",
                    evidence={"spec": spec, "wayfinder": governor},
                )

        for governor in sorted(remediation[spec]):
            if spec not in map_remediation.get(governor, set()):
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec handoff reconciliation",
                    f"#{spec}",
                    f"wayfinder-remediation #{governor} lacks matching Remediation Spec handoff",
                    evidence={"spec": spec, "wayfinder": governor},
                )

    spec_set = set(specs)
    for governor, handed in map_derived.items():
        for spec in sorted(handed & spec_set):
            if governor not in source.get(spec, set()):
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec reverse provenance",
                    f"#{spec}",
                    f"Wayfinder #{governor} declares Derived Spec but Spec lacks matching wayfinder-source",
                )

    for governor, handed in map_remediation.items():
        for spec in sorted(handed & spec_set):
            if governor not in remediation.get(spec, set()):
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec reverse remediation provenance",
                    f"#{spec}",
                    f"Wayfinder #{governor} declares Remediation Spec but Spec lacks matching wayfinder-remediation",
                )

    return source, remediation, map_derived, map_remediation


def detect_cycles(
    graph: dict[int, set[int]],
) -> list[list[int]]:
    cycles: list[list[int]] = []
    state: dict[int, int] = {}
    stack: list[int] = []
    index: dict[int, int] = {}

    def visit(node: int) -> None:
        state[node] = 1
        index[node] = len(stack)
        stack.append(node)
        for nxt in sorted(graph.get(node, set())):
            if nxt not in graph:
                continue
            if state.get(nxt, 0) == 0:
                visit(nxt)
            elif state.get(nxt) == 1:
                start = index[nxt]
                cycle = stack[start:] + [nxt]
                if cycle not in cycles:
                    cycles.append(cycle)
        stack.pop()
        index.pop(node, None)
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def parse_singleton_state(body: str) -> tuple[list[int], str] | None:
    pattern = re.compile(
        r"## Current Delivery State\s*"
        r"\n+\*\*Focused Wayfinders:\*\*\s*(?P<focus>[^\n]+)"
        r"\n\*\*Parallel authorization:\*\*\s*(?P<parallel>[^\n]+)",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(body))
    if len(matches) != 1:
        return None
    focus_text = matches[0].group("focus").strip()
    parallel = matches[0].group("parallel").strip()
    if focus_text == "None":
        focus: list[int] = []
    else:
        refs = re.findall(r"#(\d+)", focus_text)
        reconstructed = ", ".join(f"#{int(x)}" for x in sorted(map(int, refs)))
        if reconstructed != focus_text:
            return None
        focus = sorted({int(x) for x in refs})
    return focus, parallel


def base_next_skill(
    artifact_type: str,
    workflow_state: str,
    number: int,
    children: dict[int, list[int]],
    project_rows_by_number: dict[int, dict[str, Any]],
) -> str | None:
    key = (artifact_type, workflow_state)
    route = EXPECTED_ROUTE_TABLE.get(key)
    if route is None:
        return None
    if route != "$to-tickets or None":
        return route

    # Context-sensitive Spec Review / Review Remediation.
    open_remediation_children = []
    for child in children.get(number, []):
        row = project_rows_by_number.get(child)
        if not row:
            continue
        values = row["values"]
        if (
            values.get("Artifact Type") == "Review Remediation Ticket"
            and values.get("Workflow State") != "Complete"
        ):
            open_remediation_children.append(child)
    return "None" if open_remediation_children else "$to-tickets"


def expected_projection_for_open(
    number: int,
    artifact_type: str,
    workflow_state: str,
    governor_state: str,
    issue: dict[str, Any],
    audit: Audit,
    children: dict[int, list[int]],
    project_rows_by_number: dict[int, dict[str, Any]],
) -> dict[str, str] | None:
    base_next = base_next_skill(
        artifact_type,
        workflow_state,
        number,
        children,
        project_rows_by_number,
    )
    if base_next is None:
        audit.fail(
            "PROJECT PROJECTION",
            "route compatibility",
            f"#{number}",
            f"unlisted Artifact Type / Workflow State combination: {artifact_type} / {workflow_state}",
        )
        return None

    blockers = open_blocker_numbers(issue, audit, f"#{number}")

    if workflow_state == "Blocked":
        base_status = "Blocked"
    elif blockers:
        base_status = "Blocked"
    elif artifact_type == "Wayfinder Map" and workflow_state == "Spec Delivery":
        base_status = "In Progress"
    else:
        base_status = "Ready"

    if governor_state == "Independent":
        return {
            "Delivery State": "Independent",
            "Next Skill": base_next,
            "Work Status": base_status,
        }

    if artifact_type == "Wayfinder Map":
        if governor_state == "In Focus":
            return {
                "Delivery State": "In Focus",
                "Next Skill": base_next,
                "Work Status": "In Progress",
            }
        if governor_state == "Eligible":
            return {
                "Delivery State": "Eligible",
                "Next Skill": "$project-delivery-management",
                "Work Status": "Ready",
            }
        if governor_state == "Denied":
            return {
                "Delivery State": "Denied",
                "Next Skill": "None",
                "Work Status": "Blocked",
            }

    # Descendants preserve lifecycle route. Denied forces only Work Status.
    if governor_state == "Denied":
        return {
            "Delivery State": "Denied",
            "Next Skill": base_next,
            "Work Status": "Blocked",
        }
    if governor_state in {"In Focus", "Eligible"}:
        return {
            "Delivery State": governor_state,
            "Next Skill": base_next,
            "Work Status": base_status,
        }

    audit.fail(
        "PROJECT PROJECTION",
        "governor state",
        f"#{number}",
        f"unsupported governor state: {governor_state}",
    )
    return None


def lifecycle_context_checks(
    number: int,
    artifact_type: str,
    workflow_state: str,
    issues: dict[int, dict[str, Any]],
    children: dict[int, list[int]],
    project_rows_by_number: dict[int, dict[str, Any]],
    review_by_spec: dict[int, list[int]],
    comment_map: dict[int, list[dict[str, Any]]],
    audit: Audit,
) -> None:
    child_numbers = children.get(number, [])
    open_children = [
        c for c in child_numbers
        if str(issues.get(c, {}).get("state", "")).upper() == "OPEN"
    ]

    if artifact_type == "Spec":
        open_impl = [
            c for c in open_children
            if project_rows_by_number.get(c, {}).get("values", {}).get("Artifact Type")
            == "Implementation Ticket"
        ]

        if workflow_state == "Ready to Ticket" and open_impl:
            audit.fail(
                "LIVE AUTHORITY",
                "Spec lifecycle context",
                f"#{number}",
                "Ready to Ticket Spec already has open Implementation Ticket children",
                evidence={"open_implementation_tickets": open_impl},
            )

        if workflow_state == "Ready to Implement" and not open_impl:
            audit.fail(
                "LIVE AUTHORITY",
                "Spec lifecycle context",
                f"#{number}",
                "Ready to Implement Spec has no open Implementation Ticket child owning execution",
            )

        if workflow_state == "Ready to Review":
            if not passing_comment(
                comment_map, number, "## Spec Verification Receipt"
            ):
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec verification handoff",
                    f"#{number}",
                    "Ready to Review Spec has no passing Spec Verification Receipt",
                )

        if workflow_state == "Review Remediation":
            reviews = [
                r for r in review_by_spec.get(number, [])
                if str(issues.get(r, {}).get("state", "")).upper() == "OPEN"
            ]
            if len(reviews) != 1:
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec review remediation ownership",
                    f"#{number}",
                    "Review Remediation Spec must have exactly one open conventional Spec Review",
                    expected=1,
                    actual=len(reviews),
                    evidence={"review_issues": reviews},
                )

        if workflow_state == "Ready to Merge":
            reviews = review_by_spec.get(number, [])
            passing = [
                r for r in reviews
                if passing_comment(comment_map, r, "## Spec Review Exit Receipt")
            ]
            if len(passing) != 1:
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec review exit authorization",
                    f"#{number}",
                    "Ready to Merge Spec must resolve exactly one review issue with a passing Exit Receipt",
                    expected=1,
                    actual=len(passing),
                    evidence={"review_issues": reviews, "passing_review_issues": passing},
                )

    if artifact_type == "Wayfinder Map" and workflow_state == "Spec Delivery":
        open_specs = []
        for row_num, row in project_rows_by_number.items():
            if row["values"].get("Artifact Type") != "Spec":
                continue
            if row["values"].get("Workflow State") == "Complete":
                continue
            body = issues.get(row_num, {}).get("body") or ""
            governors = {
                int(x) for x in WAYFINDER_SOURCE_RE.findall(body)
            } | {
                int(x) for x in WAYFINDER_REMEDIATION_RE.findall(body)
            }
            if number in governors:
                open_specs.append(row_num)
        if not open_specs:
            audit.fail(
                "LIVE AUTHORITY",
                "Wayfinder Spec Delivery context",
                f"#{number}",
                "Spec Delivery Wayfinder has no open governed Spec",
            )


def audit_terminal_rows(
    formal_rows: list[dict[str, Any]],
    rest_issues: dict[int, dict[str, Any]],
    audit: Audit,
) -> None:
    for row in formal_rows:
        number = row["number"]
        if number is None:
            continue
        values = row["values"]
        workflow = values.get("Workflow State", "")
        delivery = values.get("Delivery State", "")
        next_skill = values.get("Next Skill", "")
        work_status = values.get("Work Status", "")
        completed_on = values.get("Completed On", "")
        root_blocker = values.get("Root Blocker", "")
        area = values.get("Area", "")
        intake = values.get("Intake State", "")
        issue = rest_issues.get(number)

        # Area is optional presentation metadata. Blank is valid unless a
        # lifecycle owner explicitly supplied an Area change in that transition.
        if intake:
            audit.fail(
                "PROJECT PROJECTION",
                "formal Intake State",
                f"#{number}",
                "formal artifact must not retain Intake State",
                actual=intake,
            )

        artifact_type = values.get("Artifact Type", "")
        if root_blocker:
            if artifact_type != "Review Remediation Ticket" or not re.fullmatch(
                r"RB-\d+", root_blocker
            ):
                audit.fail(
                    "PROJECT PROJECTION",
                    "Root Blocker",
                    f"#{number}",
                    "Root Blocker is valid only as RB-n on Review Remediation Ticket",
                    actual=root_blocker,
                )

        if workflow == "Complete":
            if delivery != "Released":
                audit.fail(
                    "PROJECT PROJECTION",
                    "completion delivery state",
                    f"#{number}",
                    "Complete artifact must be Released",
                    expected="Released",
                    actual=delivery,
                )
            if next_skill != "None":
                audit.fail(
                    "PROJECT PROJECTION",
                    "completion next skill",
                    f"#{number}",
                    "Complete artifact must have Next Skill=None",
                    expected="None",
                    actual=next_skill,
                )
            if work_status != "Done":
                audit.fail(
                    "PROJECT PROJECTION",
                    "completion work status",
                    f"#{number}",
                    "Complete artifact must have Work Status=Done",
                    expected="Done",
                    actual=work_status,
                )
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", completed_on or ""):
                audit.fail(
                    "PROJECT PROJECTION",
                    "Completed On",
                    f"#{number}",
                    "Complete artifact must have ISO Completed On",
                    actual=completed_on,
                )
            if issue and str(issue.get("state", "")).lower() != "closed":
                audit.fail(
                    "LIVE AUTHORITY",
                    "terminal issue state",
                    f"#{number}",
                    "Workflow State=Complete but GitHub issue is not closed",
                    actual=issue.get("state"),
                )
        else:
            if delivery == "Released":
                audit.fail(
                    "PROJECT PROJECTION",
                    "Released iff Complete",
                    f"#{number}",
                    "non-Complete artifact must not be Released",
                    actual={"Workflow State": workflow, "Delivery State": delivery},
                )
            if completed_on:
                audit.fail(
                    "PROJECT PROJECTION",
                    "non-terminal Completed On",
                    f"#{number}",
                    "non-Complete artifact must not have Completed On",
                    actual=completed_on,
                )
            if issue and str(issue.get("state", "")).lower() == "closed":
                audit.fail(
                    "LIVE AUTHORITY",
                    "active issue state",
                    f"#{number}",
                    "non-Complete formal artifact is durably closed",
                    actual={"Workflow State": workflow, "issue_state": issue.get("state")},
                )


def audit_live(
    repo_root: Path,
    repo: str,
    owner: str,
    audit: Audit,
) -> None:
    relation_fields = [
        "number",
        "title",
        "url",
        "state",
        "labels",
        "body",
        "parent",
        "blockedBy",
        "closedAt",
    ]
    issue_relations = run_json(
        [
            "gh", "issue", "list",
            "--repo", repo,
            "--state", "all",
            "--limit", "1000",
            "--json", ",".join(relation_fields),
        ],
        cwd=repo_root,
    )
    if not isinstance(issue_relations, list):
        raise AuditExecutionError("gh issue list returned non-list JSON")
    if len(issue_relations) >= 1000:
        raise AuditExecutionError(
            "issue list reached --limit 1000; completeness cannot be proven"
        )

    issues = {
        int(i["number"]): i
        for i in issue_relations
        if isinstance(i, dict) and i.get("number") is not None
    }

    rest_pages = run_json(
        [
            "gh", "api", "--paginate", "--slurp",
            f"repos/{repo}/issues?state=all&per_page=100",
        ],
        cwd=repo_root,
    )
    rest_issue_list = [
        i for i in flatten_slurp(rest_pages)
        if not i.get("pull_request")
    ]
    rest_issues = {int(i["number"]): i for i in rest_issue_list}

    comments_pages = run_json(
        [
            "gh", "api", "--paginate", "--slurp",
            f"repos/{repo}/issues/comments?per_page=100&sort=created&direction=asc",
        ],
        cwd=repo_root,
    )
    comment_map = comments_by_issue(flatten_slurp(comments_pages))

    projects = project_list(
        run_json(
            ["gh", "project", "list", "--owner", owner, "--format", "json"],
            cwd=repo_root,
        )
    )
    matches = [
        p for p in projects
        if str(p.get("title") or p.get("name") or "") == PROJECT_TITLE
        and not bool(p.get("closed", False))
    ]
    if len(matches) != 1:
        raise AuditExecutionError(
            f"expected exactly one open Project titled {PROJECT_TITLE!r}; found {len(matches)}"
        )
    project = matches[0]
    project_number = int(project["number"])

    fields = field_list(
        run_json(
            [
                "gh", "project", "field-list", str(project_number),
                "--owner", owner,
                "--limit", "100",
                "--format", "json",
            ],
            cwd=repo_root,
        )
    )
    audit_project_schema(fields, audit)

    item_cmd = [
        "gh", "project", "item-list", str(project_number),
        "--owner", owner,
        "--limit", "1000",
    ]
    for field in PROJECT_FIELDS:
        item_cmd += ["--field", field]
    project_rows = parse_project_items_tsv(run(item_cmd, cwd=repo_root), audit)

    # Only repository issue rows participate in this workflow audit.
    repo_rows = [
        r for r in project_rows
        if r.get("repo") == repo and r.get("number") is not None
    ]
    by_number: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in repo_rows:
        by_number[int(row["number"])].append(row)

    for number, rows in sorted(by_number.items()):
        if len(rows) != 1:
            audit.fail(
                "PROJECT PROJECTION",
                "unique Project membership",
                f"#{number}",
                "issue appears more than once in the Polaris Project",
                expected=1,
                actual=len(rows),
            )

    project_rows_by_number = {
        n: rows[0] for n, rows in by_number.items() if len(rows) == 1
    }

    formal_rows = [
        row for row in repo_rows
        if row["values"].get("Artifact Type") in FORMAL_TYPES
    ]
    open_formal_rows = [
        row for row in formal_rows
        if row["values"].get("Workflow State") != "Complete"
    ]

    audit.metrics.update(
        {
            "tracker_issues": len(issues),
            "project_rows_repository": len(repo_rows),
            "project_formal_artifacts": len(formal_rows),
            "project_open_formal_artifacts": len(open_formal_rows),
            "project_number": project_number,
        }
    )

    audit_terminal_rows(formal_rows, rest_issues, audit)

    # Independently classify every open Project formal artifact from tracker state.
    open_tracker_formal: dict[int, str] = {}
    classification_evidence: dict[int, str] = {}

    for row in open_formal_rows:
        number = int(row["number"])
        issue = issues.get(number)
        if not issue:
            audit.fail(
                "LIVE AUTHORITY",
                "open formal tracker identity",
                f"#{number}",
                "open formal Project row has no matching GitHub issue",
            )
            continue
        derived, evidence = artifact_type_from_tracker(issue, issues)
        if not derived:
            audit.fail(
                "LIVE AUTHORITY",
                "Artifact Type derivation",
                f"#{number}",
                "open formal Project row has no independently provable Artifact Type",
                actual=row["values"].get("Artifact Type"),
                evidence=evidence,
            )
            continue
        open_tracker_formal[number] = derived
        classification_evidence[number] = evidence
        if derived != row["values"].get("Artifact Type"):
            audit.fail(
                "LIVE AUTHORITY",
                "Artifact Type derivation",
                f"#{number}",
                "Project Artifact Type disagrees with durable tracker structure",
                expected=derived,
                actual=row["values"].get("Artifact Type"),
                evidence=evidence,
            )

    # Discover any open tracker artifacts that should be formal but are absent from Project.
    for number, issue in sorted(issues.items()):
        if str(issue.get("state", "")).upper() != "OPEN":
            continue
        derived, evidence = artifact_type_from_tracker(issue, issues)
        if not derived:
            continue
        open_tracker_formal.setdefault(number, derived)
        classification_evidence.setdefault(number, evidence)
        row = project_rows_by_number.get(number)
        if not row:
            audit.fail(
                "PROJECT PROJECTION",
                "open formal Project membership",
                f"#{number}",
                "open formal tracker artifact is missing from Project",
                expected=derived,
                evidence=evidence,
            )
        elif row["values"].get("Artifact Type") not in FORMAL_TYPES:
            audit.fail(
                "PROJECT PROJECTION",
                "open formal Project membership",
                f"#{number}",
                "open formal tracker artifact is present but not projected as a formal artifact",
                expected=derived,
                actual=row["values"].get("Artifact Type"),
                evidence=evidence,
            )

    # Native child map over all issues.
    children: dict[int, list[int]] = defaultdict(list)
    for number, issue in issues.items():
        parent = parent_number(issue)
        if parent is not None:
            children[parent].append(number)
    for parent in children:
        children[parent].sort()

    # Spec Review ownership.
    review_by_spec: dict[int, list[int]] = defaultdict(list)
    for number, issue in issues.items():
        if not str(issue.get("title") or "").startswith("Spec Review:"):
            continue
        parent_spec = spec_parent_from_review(issue)
        if parent_spec is not None:
            review_by_spec[parent_spec].append(number)
    for spec in review_by_spec:
        review_by_spec[spec].sort()

    # Open Wayfinder set and frontier.
    open_maps = sorted(
        n for n, t in open_tracker_formal.items()
        if t == "Wayfinder Map"
        and str(issues[n].get("state", "")).upper() == "OPEN"
    )
    frontier: set[int] = set()
    for n in open_maps:
        blockers = open_blocker_numbers(issues[n], audit, f"#{n}")
        if not blockers:
            frontier.add(n)

    # Canonical singleton.
    singletons = [
        n for n, i in issues.items()
        if "project-delivery:management" in labels(i)
    ]
    focus: set[int] = set()
    parallel = None
    if len(singletons) != 1:
        audit.fail(
            "LIVE AUTHORITY",
            "project-delivery singleton",
            "project-delivery:management",
            "expected exactly one canonical singleton across open/closed issues",
            expected=1,
            actual=len(singletons),
            evidence={"issues": sorted(singletons)},
        )
    else:
        singleton = issues[singletons[0]]
        if str(singleton.get("state", "")).upper() != "OPEN":
            audit.fail(
                "LIVE AUTHORITY",
                "project-delivery singleton",
                f"#{singletons[0]}",
                "canonical singleton is not open",
                actual=singleton.get("state"),
            )
        parsed = parse_singleton_state(singleton.get("body") or "")
        if not parsed:
            audit.fail(
                "LIVE AUTHORITY",
                "project-delivery current state",
                f"#{singletons[0]}",
                "singleton Current Delivery State block is missing, duplicated, or malformed",
            )
        else:
            focus_list, parallel = parsed
            focus = set(focus_list)
            for f in sorted(focus):
                if f not in open_maps:
                    audit.fail(
                        "LIVE AUTHORITY",
                        "focused Wayfinder identity",
                        f"#{f}",
                        "focused issue is not an open canonical Wayfinder",
                    )
                elif f not in frontier:
                    audit.fail(
                        "LIVE AUTHORITY",
                        "focused Wayfinder eligibility",
                        f"#{f}",
                        "focused Wayfinder is not in current frontier",
                    )
            if len(focus) <= 1 and parallel != "None":
                audit.fail(
                    "LIVE AUTHORITY",
                    "parallel authorization",
                    f"#{singletons[0]}",
                    "focus cardinality 0..1 requires Parallel authorization=None",
                    expected="None",
                    actual=parallel,
                )
            if len(focus) > 1:
                if not parallel or parallel == "None":
                    audit.fail(
                        "LIVE AUTHORITY",
                        "parallel authorization",
                        f"#{singletons[0]}",
                        "parallel focus requires durable authorization comment URL",
                        actual=parallel,
                    )
                else:
                    auth_comments = [
                        c for c in comment_map.get(singletons[0], [])
                        if str(c.get("html_url") or "") == parallel
                    ]
                    if len(auth_comments) != 1:
                        audit.fail(
                            "LIVE AUTHORITY",
                            "parallel authorization",
                            f"#{singletons[0]}",
                            "parallel authorization URL does not resolve exactly one singleton comment",
                            actual=parallel,
                        )
                    else:
                        body = str(auth_comments[0].get("body") or "")
                        expected_focus_text = ", ".join(f"#{n}" for n in sorted(focus))
                        if (
                            "## Project Delivery Focus Authorization" not in body
                            or "**Operation:** parallel-focus" not in body
                            or f"**Focused Wayfinders:** {expected_focus_text}" not in body
                        ):
                            audit.fail(
                                "LIVE AUTHORITY",
                                "parallel authorization",
                                f"#{singletons[0]}",
                                "parallel authorization comment does not bind exact focused set",
                                expected=expected_focus_text,
                                actual=body,
                            )

    # Governance for open Specs.
    open_specs = sorted(
        n for n, t in open_tracker_formal.items()
        if t == "Spec"
    )
    source, remediation, _, _ = spec_governance(open_specs, issues, audit)

    # Build governors recursively for every open formal artifact.
    governors: dict[int, set[int]] = {}

    def resolve_governors(number: int, trail: tuple[int, ...] = ()) -> set[int]:
        if number in governors:
            return governors[number]
        if number in trail:
            audit.fail(
                "LIVE AUTHORITY",
                "governance recursion",
                f"#{number}",
                "cycle encountered while resolving governing Wayfinders",
                evidence={"trail": list(trail) + [number]},
            )
            return set()

        artifact_type = open_tracker_formal.get(number)
        issue = issues.get(number)
        if not artifact_type or not issue:
            return set()

        result: set[int] = set()
        if artifact_type == "Wayfinder Map":
            result = {number}
        elif artifact_type == "Wayfinder Decision":
            parent = parent_number(issue)
            if parent is not None:
                result = {parent}
        elif artifact_type == "Spec":
            result = set(source.get(number, set())) | set(remediation.get(number, set()))
            if not result and EXPLICIT_INDEPENDENT_RE.search(issue.get("body") or ""):
                result = set()
            elif not result:
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec delivery governance",
                    f"#{number}",
                    "active Spec has no governing Wayfinder and no explicit durable Independent classification",
                )
        elif artifact_type in {"Implementation Ticket", "Review Remediation Ticket"}:
            parent = parent_number(issue)
            if parent is None:
                audit.fail(
                    "LIVE AUTHORITY",
                    "descendant governance",
                    f"#{number}",
                    f"{artifact_type} has no native parent",
                )
            else:
                result = resolve_governors(parent, trail + (number,))
        elif artifact_type == "Spec Review":
            spec = spec_parent_from_review(issue)
            if spec is None:
                audit.fail(
                    "LIVE AUTHORITY",
                    "Spec Review governance",
                    f"#{number}",
                    "Spec Review lacks durable Parent Spec marker",
                )
            else:
                result = resolve_governors(spec, trail + (number,))

        governors[number] = result
        return result

    for number in sorted(open_tracker_formal):
        resolve_governors(number)

    # Historical source provenance remains valid after a Wayfinder closes.
    # Active work needs at least one current open governor, but an additive
    # remediation governor may legitimately coexist with a closed original source.
    for number, govs in sorted(governors.items()):
        valid_governors: list[int] = []
        open_governors: list[int] = []
        for g in sorted(govs):
            gi = issues.get(g)
            if not gi or "wayfinder:map" not in labels(gi):
                audit.fail(
                    "LIVE AUTHORITY",
                    "governing Wayfinder identity",
                    f"#{number}",
                    f"governor #{g} is not a canonical Wayfinder",
                )
                continue
            valid_governors.append(g)
            if str(gi.get("state", "")).upper() == "OPEN":
                open_governors.append(g)

        artifact_type = open_tracker_formal.get(number)
        explicitly_independent = (
            artifact_type == "Spec"
            and EXPLICIT_INDEPENDENT_RE.search(issues[number].get("body") or "")
        )
        if valid_governors and not open_governors and not explicitly_independent:
            audit.fail(
                "LIVE AUTHORITY",
                "active artifact governor state",
                f"#{number}",
                "active Wayfinder-managed artifact has no open governing Wayfinder",
                evidence={"governors": valid_governors},
            )

    # Open formal dependency graph and cycle checks.
    graph: dict[int, set[int]] = {}
    open_formal_set = {
        n for n, i in issues.items()
        if str(i.get("state", "")).upper() == "OPEN"
        and n in open_tracker_formal
    }
    for n in sorted(open_formal_set):
        blockers = open_blocker_numbers(issues[n], audit, f"#{n}")
        graph[n] = set()
        for b in blockers:
            if b not in open_tracker_formal:
                audit.fail(
                    "LIVE AUTHORITY",
                    "formal dependency endpoint",
                    f"#{n}",
                    f"open formal artifact is blocked by non-formal/unprovable issue #{b}",
                )
            else:
                graph[n].add(b)

    cycles = detect_cycles(graph)
    for cycle in cycles:
        audit.fail(
            "LIVE AUTHORITY",
            "dependency cycle",
            " -> ".join(f"#{n}" for n in cycle),
            "native formal dependency graph contains a cycle",
            evidence={"cycle": cycle},
        )

    # Derive expected live projection for every open formal row.
    for number, artifact_type in sorted(open_tracker_formal.items()):
        row = project_rows_by_number.get(number)
        issue = issues[number]
        if not row or row["values"].get("Artifact Type") not in FORMAL_TYPES:
            continue

        values = row["values"]
        workflow = values.get("Workflow State", "")
        if not workflow:
            audit.fail(
                "PROJECT PROJECTION",
                "Workflow State",
                f"#{number}",
                "open formal artifact has blank Workflow State",
            )
            continue
        if workflow == "Complete":
            audit.fail(
                "PROJECT PROJECTION",
                "open formal lifecycle",
                f"#{number}",
                "open tracker artifact is projected Complete",
            )
            continue

        govs = governors.get(number, set())
        if artifact_type == "Spec" and not govs and EXPLICIT_INDEPENDENT_RE.search(
            issue.get("body") or ""
        ):
            governor_state = "Independent"
        elif not govs:
            audit.fail(
                "LIVE AUTHORITY",
                "delivery state derivation",
                f"#{number}",
                "cannot derive project-delivery state without governing Wayfinder",
            )
            continue
        elif any(g in focus and g in frontier for g in govs):
            governor_state = "In Focus"
        elif any(g in frontier for g in govs):
            governor_state = "Eligible"
        else:
            governor_state = "Denied"

        expected = expected_projection_for_open(
            number,
            artifact_type,
            workflow,
            governor_state,
            issue,
            audit,
            children,
            project_rows_by_number,
        )
        if expected:
            for field, exp in expected.items():
                actual = values.get(field, "")
                if actual != exp:
                    audit.fail(
                        "PROJECT PROJECTION",
                        field,
                        f"#{number}",
                        f"{field} disagrees with independently derived projection",
                        expected=exp,
                        actual=actual,
                        evidence={
                            "artifact_type": artifact_type,
                            "workflow_state": workflow,
                            "governors": sorted(govs),
                            "frontier": sorted(frontier),
                            "focus": sorted(focus),
                            "open_blockers": open_blocker_numbers(issue, audit, f"#{number}"),
                        },
                    )

        lifecycle_context_checks(
            number,
            artifact_type,
            workflow,
            issues,
            children,
            project_rows_by_number,
            review_by_spec,
            comment_map,
            audit,
        )

    # Current one-review ownership: duplicates are always invalid; absence is
    # allowed until a review persistence point.
    for spec, reviews in sorted(review_by_spec.items()):
        if len(reviews) > 1:
            audit.fail(
                "LIVE AUTHORITY",
                "conventional Spec Review uniqueness",
                f"Spec #{spec}",
                "more than one conventional Spec Review identifies the same parent Spec",
                expected=1,
                actual=len(reviews),
                evidence={"reviews": reviews},
            )

    audit.metrics.update(
        {
            "open_wayfinder_maps": open_maps,
            "wayfinder_frontier": sorted(frontier),
            "focused_wayfinders": sorted(focus),
            "open_formal_tracker_artifacts": len(open_tracker_formal),
            "dependency_cycles": len(cycles),
        }
    )


def write_report(
    path: Path,
    audit: Audit,
    *,
    repo_root: Path,
    head: str,
    repo: str,
    execution_error: str | None = None,
) -> None:
    payload = {
        "audit": "Polaris workflow consistency",
        "auditor_version": 4,
        "contract_base": CONTRACT_BASE,
        "repository": repo,
        "repository_root": str(repo_root),
        "head": head,
        "result": (
            "INCOMPLETE"
            if execution_error
            else ("FAIL" if audit.failures else "PASS")
        ),
        "execution_error": execution_error,
        "metrics": audit.metrics,
        "contract_file_sha256": audit.contract_files,
        "summary": {
            "failures": len(audit.failures),
            "warnings": len(audit.warnings),
            "findings": len(audit.findings),
        },
        "findings": [asdict(f) for f in audit.findings],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def print_report(audit: Audit, head: str, report_path: Path, execution_error: str | None) -> None:
    print()
    print("POLARIS WORKFLOW AUDIT")
    print(f"Contract base:   {CONTRACT_BASE}")
    print(f"Audited HEAD:    {head}")
    print()

    if execution_error:
        print("AUDIT RESULT: INCOMPLETE")
        print(f"Execution error: {execution_error}")
        print(f"JSON report: {report_path}")
        return

    metrics = audit.metrics
    if metrics:
        if "project_formal_artifacts" in metrics:
            print(f"Project formal artifacts:       {metrics['project_formal_artifacts']}")
        if "project_open_formal_artifacts" in metrics:
            print(f"Project open formal artifacts:  {metrics['project_open_formal_artifacts']}")
        if "open_formal_tracker_artifacts" in metrics:
            print(f"Open tracker formal artifacts:  {metrics['open_formal_tracker_artifacts']}")
        if "open_wayfinder_maps" in metrics:
            print(f"Open Wayfinders:                {len(metrics['open_wayfinder_maps'])}")
        if "focused_wayfinders" in metrics:
            focused = ", ".join(f"#{n}" for n in metrics["focused_wayfinders"]) or "None"
            print(f"Focused Wayfinders:             {focused}")
        if "wayfinder_frontier" in metrics:
            frontier = ", ".join(f"#{n}" for n in metrics["wayfinder_frontier"]) or "None"
            print(f"Wayfinder frontier:             {frontier}")
        print()

    layers = [
        "STATIC CONTRACT",
        "PROJECT SCHEMA",
        "LIVE AUTHORITY",
        "PROJECT PROJECTION",
    ]
    for layer in layers:
        failures = [f for f in audit.failures if f.layer == layer]
        warnings = [f for f in audit.warnings if f.layer == layer]
        status = "PASS" if not failures else f"FAIL ({len(failures)})"
        if warnings:
            status += f", WARN ({len(warnings)})"
        print(f"{layer:<22} {status}")

    other_failures = [f for f in audit.failures if f.layer not in layers]
    if other_failures:
        print(f"{'OTHER':<22} FAIL ({len(other_failures)})")

    print()
    if audit.failures:
        print("FAILURES")
        for idx, finding in enumerate(audit.failures, 1):
            print(f"{idx}. [{finding.layer}] {finding.check} — {finding.subject}")
            print(f"   {finding.message}")
            if finding.expected is not None:
                print(f"   expected: {finding.expected}")
            if finding.actual is not None:
                print(f"   actual:   {finding.actual}")
            if finding.evidence is not None:
                rendered = json.dumps(finding.evidence, sort_keys=True)
                if len(rendered) > 500:
                    rendered = rendered[:497] + "..."
                print(f"   evidence: {rendered}")
        print()

    if audit.warnings:
        print("WARNINGS")
        for idx, finding in enumerate(audit.warnings, 1):
            print(f"{idx}. [{finding.layer}] {finding.check} — {finding.subject}")
            print(f"   {finding.message}")
        print()

    if audit.failures:
        print(f"AUDIT RESULT: FAIL ({len(audit.failures)} invariant violation(s))")
    else:
        print("AUDIT RESULT: PASS")
    print(f"JSON report: {report_path}")


def parse_gh_version(text: str) -> tuple[int, int, int] | None:
    m = re.search(r"gh version\s+(\d+)\.(\d+)\.(\d+)", text)
    if not m:
        return None
    return tuple(map(int, m.groups()))  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only deterministic audit of Polaris workflow contracts and live Project projection."
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Path for machine-readable JSON report (default: ./polaris-workflow-audit-<HEAD12>.json)",
    )
    args = parser.parse_args()

    audit = Audit()
    repo_root = Path.cwd()
    head = "UNKNOWN"
    repo = EXPECTED_REPO
    execution_error: str | None = None

    try:
        repo_root = Path(run(["git", "rev-parse", "--show-toplevel"]).strip())
        head = run(["git", "rev-parse", "HEAD"], cwd=repo_root).strip()

        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", CONTRACT_BASE, head],
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if ancestor.returncode != 0:
            raise AuditExecutionError(
                "auditor contract lineage mismatch: "
                f"required base {CONTRACT_BASE} is not an ancestor of HEAD {head}"
            )

        skill_drift = run(
            ["git", "status", "--porcelain", "--", ".agents/skills"],
            cwd=repo_root,
        ).strip()
        if skill_drift:
            raise AuditExecutionError(
                "local .agents/skills working tree differs from the bound contract; "
                "commit/stash/revert those changes before auditing"
            )

        gh_version_text = run(["gh", "--version"], cwd=repo_root)
        gh_version = parse_gh_version(gh_version_text)
        if gh_version is None or gh_version < MIN_GH_VERSION:
            raise AuditExecutionError(
                f"gh >= {'.'.join(map(str, MIN_GH_VERSION))} required; "
                f"found {gh_version_text.splitlines()[0] if gh_version_text else 'unknown'}"
            )

        repo = run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            cwd=repo_root,
        ).strip()
        if repo != EXPECTED_REPO:
            raise AuditExecutionError(
                f"auditor is bound to {EXPECTED_REPO}; current repository is {repo}"
            )
        owner = repo.split("/", 1)[0]

        static_contract_audit(repo_root, audit)
        audit_live(repo_root, repo, owner, audit)

    except AuditExecutionError as exc:
        execution_error = str(exc)
    except Exception as exc:
        execution_error = f"unexpected auditor failure: {type(exc).__name__}: {exc}"

    if args.json_out:
        report_path = Path(args.json_out).expanduser().resolve()
    else:
        suffix = head[:12] if head != "UNKNOWN" else "unknown"
        report_path = (Path.cwd() / f"polaris-workflow-audit-{suffix}.json").resolve()

    try:
        write_report(
            report_path,
            audit,
            repo_root=repo_root,
            head=head,
            repo=repo,
            execution_error=execution_error,
        )
    except OSError as exc:
        print(f"Could not write JSON report: {exc}", file=sys.stderr)
        if execution_error is None:
            execution_error = f"report write failed: {exc}"

    print_report(audit, head, report_path, execution_error)

    if execution_error:
        return 2
    return 1 if audit.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
