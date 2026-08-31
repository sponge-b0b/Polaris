#!/usr/bin/env python3
"""Deterministic bookkeeping for the Polaris ``$verify-spec`` skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

CELL_RE = re.compile(r"^(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
WORKSPACE_METADATA_HEADER = "## Workspace Metadata"
BASELINE_LINE_RE = re.compile(r"^\*\*Baseline Commit Hash:\*\* (?P<sha>[0-9a-f]{40})$")
RECEIPT_HEADER = "## Spec Verification Receipt"
PROOF_STATES = {"proven", "not-applicable", "unresolved"}
GATE_STATES = {"PASS", "NOT APPLICABLE"}


class ValidationError(ValueError):
    """Raised when verifier artifact data is invalid."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _text(value: Any, label: str) -> str:
    _require(
        isinstance(value, str) and bool(value.strip()),
        f"{label} must be non-empty",
    )
    return value.strip()


def _sha(value: Any, label: str) -> str:
    text = _text(value, label)
    _require(bool(SHA_RE.fullmatch(text)), f"{label} must be a 40-char SHA")
    return text


def _digest_text(value: Any, label: str) -> str:
    text = _text(value, label)
    _require(
        bool(DIGEST_RE.fullmatch(text)),
        f"{label} must be a SHA-256 digest",
    )
    return text


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _strings(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    _require(isinstance(value, list), f"{label} must be a list")
    return [_text(item, label) for item in value]


def _table(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return value.replace("|", "\\|").replace("\n", "<br>")


def _workspace_metadata(comments: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for comment in comments:
        body = str(comment.get("body") or "")
        lines = body.splitlines()
        if WORKSPACE_METADATA_HEADER not in lines:
            continue
        baseline_lines = [
            line for line in lines if line.startswith("**Baseline Commit Hash:**")
        ]
        _require(
            len(baseline_lines) == 1,
            "Workspace Metadata must contain exactly one Baseline Commit Hash line",
        )
        match = BASELINE_LINE_RE.fullmatch(baseline_lines[0])
        _require(
            match is not None,
            "Workspace Metadata Baseline Commit Hash must be an unquoted "
            "lowercase 40-character SHA",
        )
        candidates.append(
            {
                "comment_id": comment.get("id"),
                "baseline_commit": match.group("sha"),
            }
        )
    _require(
        len(candidates) == 1,
        "exactly one canonical Workspace Metadata comment is required",
    )
    return candidates[0]


def comments_summary(raw: Any) -> dict[str, Any]:
    _require(isinstance(raw, list), "comment payload must be a JSON list")
    if raw and not all(isinstance(item, dict) for item in raw):
        raw = [item for page in raw for item in page]
    _require(
        all(isinstance(item, dict) for item in raw),
        "comment payload contains a non-object item",
    )
    comments = sorted(
        raw,
        key=lambda item: (
            str(item.get("created_at") or ""),
            int(item.get("id") or 0),
        ),
    )
    metadata = _workspace_metadata(comments)
    receipts: list[dict[str, Any]] = []
    for comment in comments:
        body = str(comment.get("body") or "")
        if RECEIPT_HEADER in body:
            receipts.append(
                {
                    "id": comment.get("id"),
                    "created_at": comment.get("created_at"),
                    "html_url": comment.get("html_url") or comment.get("url"),
                    "body": body,
                }
            )
    return {
        "comment_count": len(comments),
        "workspace_metadata": metadata,
        "baseline_commit": metadata["baseline_commit"],
        "latest_receipt": receipts[-1] if receipts else None,
    }


def _manifest(raw: Any) -> tuple[list[dict[str, str]], list[str]]:
    _require(bool(isinstance(raw, list) and raw), "manifest must be non-empty")
    rows: list[dict[str, str]] = []
    cells: list[str] = []
    for item in raw:
        _require(isinstance(item, dict), "manifest rows must be objects")
        cell = _text(item.get("cell"), "manifest cell")
        _require(bool(CELL_RE.fullmatch(cell)), f"invalid manifest cell: {cell}")
        _require(cell not in cells, f"duplicate manifest cell: {cell}")
        rows.append(
            {
                "cell": cell,
                "source": _text(item.get("source"), f"manifest {cell} source"),
                "requirement": _text(
                    item.get("requirement"),
                    f"manifest {cell} requirement",
                ),
            }
        )
        cells.append(cell)
    return rows, cells


def _proofs(
    raw: Any,
    manifest_cells: list[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    _require(bool(isinstance(raw, list) and raw), "proofs must be non-empty")
    manifest = set(manifest_cells)
    mapped: set[str] = set()
    counts = {"proven": 0, "not-applicable": 0, "unresolved": 0}
    proofs: list[dict[str, Any]] = []

    for index, item in enumerate(raw, start=1):
        label = f"proof {index}"
        _require(isinstance(item, dict), f"{label} must be an object")
        cells = _strings(item.get("cells"), f"{label} cells")
        _require(bool(cells), f"{label} cells must be non-empty")
        _require(len(cells) == len(set(cells)), f"{label} duplicates cells")
        unknown = [cell for cell in cells if cell not in manifest]
        _require(not unknown, f"{label} references unknown cells: {unknown}")
        duplicate = [cell for cell in cells if cell in mapped]
        _require(not duplicate, f"cells mapped more than once: {duplicate}")

        state = _text(item.get("state"), f"{label} state")
        _require(state in PROOF_STATES, f"{label} invalid state: {state}")
        proof: dict[str, Any] = {"cells": cells, "state": state}
        if state == "proven":
            evidence = _strings(item.get("evidence"), f"{label} evidence")
            _require(bool(evidence), f"{label} evidence must be non-empty")
            proof["evidence"] = evidence
        elif state == "not-applicable":
            proof["reason"] = _text(item.get("reason"), f"{label} reason")
        elif item.get("reason") is not None:
            proof["reason"] = _text(item.get("reason"), f"{label} reason")

        mapped.update(cells)
        counts[state] += len(cells)
        proofs.append(proof)

    missing = [cell for cell in manifest_cells if cell not in mapped]
    _require(not missing, f"manifest cells missing proof mapping: {missing}")
    _require(
        not counts["unresolved"],
        "unresolved manifest cells prevent a passing receipt",
    )
    return proofs, counts


def _gates(raw: Any) -> list[dict[str, str]]:
    _require(bool(isinstance(raw, list) and raw), "gates must be non-empty")
    result: list[dict[str, str]] = []
    names: set[str] = set()
    for item in raw:
        _require(isinstance(item, dict), "gate rows must be objects")
        name = _text(item.get("name"), "gate name")
        _require(name not in names, f"duplicate gate name: {name}")
        names.add(name)
        status = _text(item.get("status"), f"gate {name} status")
        _require(
            status in GATE_STATES,
            f"gate {name} must be PASS or NOT APPLICABLE",
        )
        result.append(
            {
                "name": name,
                "status": status,
                "evidence": _text(item.get("evidence"), f"gate {name} evidence"),
            }
        )
    return result


def _source_counts(raw: Any) -> dict[str, int]:
    _require(isinstance(raw, dict), "source_counts must be an object")
    result: dict[str, int] = {}
    for key, value in raw.items():
        name = _text(key, "source count name")
        _require(
            isinstance(value, int) and value >= 0,
            f"source count {name} must be a non-negative integer",
        )
        result[name] = value
    return result


def finalize(raw: Any) -> dict[str, Any]:
    _require(isinstance(raw, dict), "finalize input must be an object")
    _require(
        isinstance(raw.get("spec_issue"), int) and raw["spec_issue"] > 0,
        "spec_issue must be positive",
    )
    manifest, cells = _manifest(raw.get("manifest"))
    proofs, counts = _proofs(raw.get("proofs"), cells)
    gates = _gates(raw.get("gates"))
    result = {
        "spec_issue": raw["spec_issue"],
        "head": _sha(raw.get("head"), "head"),
        "baseline": _sha(raw.get("baseline"), "baseline"),
        "branch": _text(raw.get("branch"), "branch"),
        "mode": _text(raw.get("mode"), "mode"),
        "prior_checkpoint": raw.get("prior_checkpoint"),
        "spec_body_hash": _digest_text(raw.get("spec_body_hash"), "spec_body_hash"),
        "spec_contract_hash": _digest_text(
            raw.get("spec_contract_hash"),
            "spec_contract_hash",
        ),
        "default_branch": _text(raw.get("default_branch"), "default_branch"),
        "default_head": _sha(raw.get("default_head"), "default_head"),
        "source_counts": _source_counts(raw.get("source_counts")),
        "manifest": manifest,
        "proofs": proofs,
        "gates": gates,
        "repairs": _strings(raw.get("repairs"), "repair"),
        "unrelated_inherited_findings": _strings(
            raw.get("unrelated_inherited_findings"),
            "inherited finding",
        ),
    }
    if result["prior_checkpoint"] is not None:
        result["prior_checkpoint"] = _text(
            result["prior_checkpoint"],
            "prior_checkpoint",
        )
    result["summary"] = {
        "manifest_cells": len(cells),
        "proof_groups": len(proofs),
        "proven_cells": counts["proven"],
        "not_applicable_cells": counts["not-applicable"],
        "unresolved_cells": counts["unresolved"],
        "verification_gates": len(gates),
    }
    result["verification_hash"] = _digest(result)
    return result


def _coverage_by_state(state: dict[str, Any]) -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {name: [] for name in PROOF_STATES}
    for proof in state["proofs"]:
        coverage[proof["state"]].extend(proof["cells"])
    return coverage


def render_receipt(state: dict[str, Any]) -> str:
    summary = state["summary"]
    counts = state["source_counts"]
    coverage = _coverage_by_state(state)
    lines = [
        RECEIPT_HEADER,
        "",
        "**Status:** passed",
        f"**Spec:** #{state['spec_issue']}",
        f"**Verified HEAD:** {state['head']}",
        f"**Verified Baseline:** {state['baseline']}",
        f"**Branch:** {state['branch']}",
        f"**Verification mode:** {state['mode']}",
        f"**Prior verified checkpoint:** {state.get('prior_checkpoint') or 'None'}",
        f"**Spec Body Hash:** {state['spec_body_hash']}",
        f"**Spec Contract Hash:** {state['spec_contract_hash']}",
        f"**Verification Hash:** {state['verification_hash']}",
        (
            "**Default ownership point:** "
            f"{state['default_branch']}@{state['default_head']}"
        ),
        "",
        "### Spec Contract Integrity",
        f"- User Stories: {counts.get('user_stories', 0)}",
        (f"- Implementation Decisions: {counts.get('implementation_decisions', 0)}"),
        f"- Testing Decisions: {counts.get('testing_decisions', 0)}",
        f"- Out of Scope: {counts.get('out_of_scope', 0)}",
        f"- Other normative source items: {counts.get('other_normative', 0)}",
        f"- Manifest cells: {summary['manifest_cells']}",
        "- Unmapped source items: 0",
        "- Duplicate source mappings: 0",
        "- Ambiguous source items: 0",
        "",
        "### Spec Contract Manifest",
        "| Cell | Source | Requirement |",
        "| --- | --- | --- |",
    ]
    for row in state["manifest"]:
        lines.append(
            f"| {row['cell']} | {_table(row['source'])} | "
            f"{_table(row['requirement'])} |"
        )

    lines += ["", "### Spec Contract Coverage"]
    for status in ("proven", "not-applicable", "unresolved"):
        cells = coverage[status]
        lines.append(f"- {status}: {', '.join(cells) if cells else 'None'}")

    lines += ["", "### Verification Gates"]
    lines.extend(
        f"- {gate['name']}: {gate['status']} — {gate['evidence']}"
        for gate in state["gates"]
    )
    lines += ["", "### Repairs"]
    lines.extend(f"- {item}" for item in state["repairs"] or ["None"])
    lines += ["", "### Unrelated Inherited Findings"]
    findings = state["unrelated_inherited_findings"] or ["None"]
    lines.extend(f"- {item}" for item in findings)
    return "\n".join(lines) + "\n"


def self_test() -> None:
    canonical_comments = [
        {
            "id": 1,
            "created_at": "2026-08-31T00:00:00Z",
            "body": (
                "## Workspace Metadata\n"
                f"**Baseline Commit Hash:** {'a' * 40}\n"
                "**Branch:** spec-1"
            ),
        },
        {
            "id": 2,
            "created_at": "2026-08-31T00:01:00Z",
            "body": (
                f"## Implementation Tickets\n**Baseline Commit Hash:** `{'a' * 40}`"
            ),
        },
    ]
    summary = comments_summary(canonical_comments)
    assert summary["baseline_commit"] == "a" * 40
    assert summary["workspace_metadata"]["comment_id"] == 1

    invalid_comments = [
        [
            {
                "id": 1,
                "body": (
                    f"## Workspace Metadata\n**Baseline Commit Hash:** `{'a' * 40}`"
                ),
            }
        ],
        [
            {
                "id": 1,
                "body": (
                    f"## Workspace Metadata\n**Baseline Commit Hash:** {'a' * 40}"
                ),
            },
            {
                "id": 2,
                "body": (
                    f"## Workspace Metadata\n**Baseline Commit Hash:** {'a' * 40}"
                ),
            },
        ],
    ]
    for invalid in invalid_comments:
        try:
            comments_summary(invalid)
        except ValidationError:
            continue
        raise AssertionError("invalid Workspace Metadata was accepted")

    raw = {
        "spec_issue": 1,
        "head": "a" * 40,
        "baseline": "b" * 40,
        "branch": "spec-1",
        "mode": "full",
        "prior_checkpoint": None,
        "spec_body_hash": "c" * 64,
        "spec_contract_hash": "d" * 64,
        "default_branch": "main",
        "default_head": "e" * 40,
        "source_counts": {"user_stories": 2, "out_of_scope": 1},
        "manifest": [
            {"cell": "US-1", "source": "User Stories 1", "requirement": "one"},
            {"cell": "US-2", "source": "User Stories 2", "requirement": "two"},
            {"cell": "OOS-1", "source": "Out of Scope 1", "requirement": "no"},
        ],
        "proofs": [
            {
                "cells": ["US-1", "US-2"],
                "state": "proven",
                "evidence": ["application/x.py:1-20", "test_x::test_behavior"],
            },
            {
                "cells": ["OOS-1"],
                "state": "not-applicable",
                "reason": "Originating Spec excludes this surface.",
            },
        ],
        "gates": [
            {"name": "Ruff lint", "status": "PASS", "evidence": "clean"},
        ],
    }
    state = finalize(raw)
    assert state["verification_hash"] == finalize(raw)["verification_hash"]
    receipt = render_receipt(state)
    assert "### Spec Contract Manifest" in receipt
    assert "### Spec Proof Objects" not in receipt
    assert "- proven: US-1, US-2" in receipt

    cases = []
    bad = json.loads(json.dumps(raw))
    bad["proofs"][1]["cells"] = ["US-1", "OOS-1"]
    cases.append(bad)
    bad = json.loads(json.dumps(raw))
    bad["proofs"][0] = {"cells": ["US-1", "US-2"], "state": "unresolved"}
    cases.append(bad)
    bad = json.loads(json.dumps(raw))
    bad["proofs"][0]["evidence"] = []
    cases.append(bad)
    bad = json.loads(json.dumps(raw))
    bad["gates"][0]["status"] = "FAIL"
    cases.append(bad)
    for invalid in cases:
        try:
            finalize(invalid)
        except ValidationError:
            continue
        raise AssertionError("invalid finalization input was accepted")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    comments = sub.add_parser("comments")
    comments.add_argument("--input", required=True)
    finish = sub.add_parser("finalize")
    finish.add_argument("--input", required=True)
    finish.add_argument("--receipt-output", required=True)
    sub.add_parser("self-test")
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        if args.command == "comments":
            result = comments_summary(_read_json(args.input))
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "finalize":
            state = finalize(_read_json(args.input))
            Path(args.receipt_output).write_text(
                render_receipt(state),
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {
                        **state["summary"],
                        "verification_hash": state["verification_hash"],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "self-test":
            self_test()
            print("VERIFY-SPEC ARTIFACT SELF-TEST: PASS")
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"VERIFY-SPEC ARTIFACT ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
