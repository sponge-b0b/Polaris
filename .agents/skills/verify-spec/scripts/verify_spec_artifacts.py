#!/usr/bin/env python3
"""Deterministic bookkeeping for the Polaris ``$verify-spec`` skill."""

from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

CELL_RE = re.compile(r"^(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?$")
SOURCE_UNIT_RE = re.compile(r"^SU-\d{4,}$")
SOURCE_UNIT_STATES = {"normative-new", "normative-represented", "non-normative"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
WORKSPACE_METADATA_HEADER = "## Workspace Metadata"
BASELINE_LINE_RE = re.compile(r"^\*\*Baseline Commit Hash:\*\* (?P<sha>[0-9a-f]{40})$")
RECEIPT_HEADER = "## Spec Verification Receipt"
TCM_HEADER = "## Ticket Coverage Manifest"
RECEIPT_FORMAT = "manifest-table-v2"
PROOF_STATES = {"proven", "not-applicable", "unresolved"}
GATE_STATES = {"PASS", "NOT APPLICABLE"}
CONTRACT_HANDOFF_KEYS = {
    "spec_issue",
    "head",
    "baseline",
    "branch",
    "spec_body_hash",
    "spec_contract_hash",
    "default_branch",
    "default_head",
    "source_counts",
    "manifest",
    "contract_identity",
}


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


def _tcm_field(lines: list[str], label: str) -> str:
    prefix = f"{label}: "
    matches = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    _require(len(matches) == 1, f"TCM must contain exactly one {label} field")
    return matches[0].strip()


def _strings(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    _require(isinstance(value, list), f"{label} must be a list")
    return [_text(item, label) for item in value]


def _table(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return html.escape(value, quote=False).replace("|", "&#124;").replace("\n", "<br>")


def _review_manifest_parser(receipt: str) -> list[dict[str, str]]:
    review_path = (
        Path(__file__).resolve().parents[2]
        / "review-spec"
        / "scripts"
        / "review_spec_artifacts.py"
    )
    _require(review_path.is_file(), "review-spec artifact parser is missing")
    module_spec = importlib.util.spec_from_file_location(
        "_polaris_review_spec_artifacts",
        review_path,
    )
    _require(
        module_spec is not None and module_spec.loader is not None,
        "review-spec artifact parser could not be loaded",
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    try:
        parsed = module.parse_verification_manifest(receipt)
    except Exception as exc:  # downstream compatibility boundary
        raise ValidationError(
            f"rendered receipt is not consumable by $review-spec: {exc}"
        ) from exc
    _require(isinstance(parsed, list), "review-spec manifest parser returned invalid data")
    return parsed


def _validate_receipt_round_trip(receipt: str, state: dict[str, Any]) -> None:
    _require(
        _review_manifest_parser(receipt) == state["manifest"],
        "rendered receipt manifest does not round-trip exactly through $review-spec",
    )


def _require_contract_digest(path: str | Path, expected: str) -> None:
    expected_digest = _digest_text(expected, "contract handoff digest")
    actual_digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    _require(
        actual_digest == expected_digest,
        "contract handoff digest mismatch; rebuild via $spec-contract and recertify",
    )


def _validate_contract_identity(contract: dict[str, Any]) -> None:
    identity = contract.get("contract_identity")
    _require(isinstance(identity, dict), "contract_identity must be an object")
    _require(
        set(identity) == {"source_units", "manifest"},
        "contract_identity keys must be source_units and manifest",
    )
    source_rows = identity["source_units"]
    manifest_rows = identity["manifest"]
    _require(
        isinstance(source_rows, list) and bool(source_rows),
        "contract identity source units missing",
    )
    _require(
        isinstance(manifest_rows, list) and bool(manifest_rows),
        "contract identity manifest missing",
    )

    body_hash = _digest_text(contract.get("spec_body_hash"), "spec_body_hash")
    expected_hash = _digest_text(
        contract.get("spec_contract_hash"),
        "spec_contract_hash",
    )

    source_ids: list[str] = []
    reverse: dict[str, list[str]] = {}
    for row in source_rows:
        _require(
            isinstance(row, list) and len(row) == 4,
            "invalid source-unit identity row",
        )
        source_id, text_hash, classification, mapped_cells = row
        _require(
            isinstance(source_id, str)
            and SOURCE_UNIT_RE.fullmatch(source_id) is not None,
            "invalid source-unit ID",
        )
        _require(source_id not in source_ids, f"duplicate source-unit ID: {source_id}")
        source_ids.append(source_id)
        _digest_text(text_hash, f"{source_id} text hash")
        _require(
            classification in SOURCE_UNIT_STATES,
            f"invalid {source_id} classification",
        )
        if mapped_cells is None:
            cells: list[str] = []
        else:
            _require(
                isinstance(mapped_cells, list),
                f"{source_id} manifest cells must be a list or null",
            )
            cells = mapped_cells
        _require(
            len(cells) == len(set(cells)),
            f"{source_id} duplicates manifest cells",
        )
        if classification == "non-normative":
            _require(not cells, f"non-normative {source_id} must not map manifest cells")
        else:
            _require(bool(cells), f"normative {source_id} must map manifest cells")
        for cell in cells:
            _require(
                isinstance(cell, str) and CELL_RE.fullmatch(cell) is not None,
                f"invalid mapped cell in {source_id}",
            )
            reverse.setdefault(cell, []).append(source_id)

    display_manifest, _ = _manifest(contract.get("manifest"))
    display_cells = [row["cell"] for row in display_manifest]
    identity_cells: list[str] = []
    for row in manifest_rows:
        _require(
            isinstance(row, list) and len(row) == 2,
            "invalid manifest identity row",
        )
        cell, row_source_ids = row
        _require(
            isinstance(cell, str) and CELL_RE.fullmatch(cell) is not None,
            "invalid manifest identity cell",
        )
        _require(cell not in identity_cells, f"duplicate manifest identity cell: {cell}")
        _require(
            isinstance(row_source_ids, list) and bool(row_source_ids),
            f"manifest identity {cell} has no source units",
        )
        _require(
            len(row_source_ids) == len(set(row_source_ids)),
            f"manifest identity {cell} duplicates source units",
        )
        _require(
            all(source_id in source_ids for source_id in row_source_ids),
            f"manifest identity {cell} references unknown source unit",
        )
        _require(
            reverse.get(cell, []) == row_source_ids,
            f"manifest identity {cell} disagrees with source-unit reverse mapping",
        )
        identity_cells.append(cell)

    _require(
        identity_cells == display_cells,
        "contract identity/display manifest cell order mismatch",
    )
    _require(
        set(reverse) == set(identity_cells),
        "source-unit identity maps cells outside the manifest identity",
    )

    payload = (
        "SPEC-CONTRACT\n"
        + body_hash
        + "\n--SOURCE-UNITS--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in source_rows
        )
        + "\n--MANIFEST--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in manifest_rows
        )
        + "\n"
    )
    actual_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    _require(
        actual_hash == expected_hash,
        "contract handoff structural identity does not reproduce SPEC_CONTRACT_HASH",
    )


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
    ticket_coverage_manifests: list[dict[str, Any]] = []
    for comment in comments:
        body = str(comment.get("body") or "")
        record = {
            "id": comment.get("id"),
            "created_at": comment.get("created_at"),
            "html_url": comment.get("html_url") or comment.get("url"),
            "body": body,
        }
        if RECEIPT_HEADER in body:
            receipts.append(record)
        if TCM_HEADER in body.splitlines():
            ticket_coverage_manifests.append(record)
    return {
        "comment_count": len(comments),
        "workspace_metadata": metadata,
        "baseline_commit": metadata["baseline_commit"],
        "latest_receipt": receipts[-1] if receipts else None,
        "ticket_coverage_manifest": (
            ticket_coverage_manifests[0]
            if len(ticket_coverage_manifests) == 1
            else None
        ),
        "ticket_coverage_manifest_count": len(ticket_coverage_manifests),
    }


def contract_coherence(summary: Any, contract: Any) -> dict[str, str]:
    _require(isinstance(summary, dict), "comments summary must be an object")
    _require(isinstance(contract, dict), "contract handoff must be an object")
    keys = set(contract)
    _require(
        keys == CONTRACT_HANDOFF_KEYS,
        "contract handoff keys mismatch: "
        f"missing={sorted(CONTRACT_HANDOFF_KEYS - keys)}, "
        f"extra={sorted(keys - CONTRACT_HANDOFF_KEYS)}",
    )
    _validate_contract_identity(contract)

    _require(
        summary.get("ticket_coverage_manifest_count") == 1,
        "exactly one current Ticket Coverage Manifest is required",
    )
    tcm = summary.get("ticket_coverage_manifest")
    _require(isinstance(tcm, dict), "current Ticket Coverage Manifest is missing")
    tcm_body = _text(tcm.get("body"), "Ticket Coverage Manifest body")
    lines = tcm_body.splitlines()
    _require(TCM_HEADER in lines, "invalid Ticket Coverage Manifest")

    contract_body_hash = _digest_text(
        contract.get("spec_body_hash"),
        "contract spec_body_hash",
    )
    contract_hash = _digest_text(
        contract.get("spec_contract_hash"),
        "contract spec_contract_hash",
    )
    tcm_body_hash = _digest_text(
        _tcm_field(lines, "Spec Body Hash"),
        "TCM Spec Body Hash",
    )
    tcm_hash = _digest_text(
        _tcm_field(lines, "Spec Contract Hash"),
        "TCM Spec Contract Hash",
    )

    _require(tcm_body_hash == contract_body_hash, "TCM Spec Body Hash mismatch")
    _require(tcm_hash == contract_hash, "TCM Spec Contract Hash mismatch")

    return {
        "status": "PASS",
        "spec_body_hash": contract_body_hash,
        "spec_contract_hash": contract_hash,
        "ticket_coverage_manifest_id": str(tcm.get("id") or ""),
    }


def _manifest(raw: Any) -> tuple[list[dict[str, str]], list[str]]:
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


def finalize_parts(
    contract: Any,
    proofs: Any,
    gates: Any,
    *,
    mode: str,
    prior_checkpoint: str | None,
    repairs: list[str],
    inherited_findings: list[str],
) -> dict[str, Any]:
    _require(isinstance(contract, dict), "contract handoff must be an object")
    keys = set(contract)
    _require(
        keys == CONTRACT_HANDOFF_KEYS,
        "contract handoff keys mismatch: "
        f"missing={sorted(CONTRACT_HANDOFF_KEYS - keys)}, "
        f"extra={sorted(keys - CONTRACT_HANDOFF_KEYS)}",
    )
    _validate_contract_identity(contract)
    finalizer_contract = {
        key: value for key, value in contract.items() if key != "contract_identity"
    }
    return finalize(
        {
            **finalizer_contract,
            "mode": mode,
            "prior_checkpoint": prior_checkpoint,
            "proofs": proofs,
            "gates": gates,
            "repairs": repairs,
            "unrelated_inherited_findings": inherited_findings,
        }
    )


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
        f"**Receipt format:** {RECEIPT_FORMAT}",
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


def _emit_finalization(state: dict[str, Any], receipt_output: str) -> None:
    receipt = render_receipt(state)
    _validate_receipt_round_trip(receipt, state)
    Path(receipt_output).write_text(receipt, encoding="utf-8")
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
        {
            "id": 3,
            "created_at": "2026-08-31T00:02:00Z",
            "body": (
                "## Ticket Coverage Manifest\n"
                f"Spec Body Hash: {'b' * 64}\n"
                f"Spec Contract Hash: {'c' * 64}"
            ),
        },
    ]
    summary = comments_summary(canonical_comments)
    assert summary["baseline_commit"] == "a" * 40
    assert summary["workspace_metadata"]["comment_id"] == 1
    assert summary["ticket_coverage_manifest_count"] == 1
    assert summary["ticket_coverage_manifest"]["id"] == 3

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

    source_identity = [
        ["SU-0001", "1" * 64, "normative-new", ["US-1"]],
        ["SU-0002", "2" * 64, "normative-new", ["US-2"]],
        ["SU-0003", "3" * 64, "normative-new", ["OOS-1"]],
    ]
    manifest_identity = [
        ["US-1", ["SU-0001"]],
        ["US-2", ["SU-0002"]],
        ["OOS-1", ["SU-0003"]],
    ]
    body_hash = "c" * 64
    contract_payload = (
        "SPEC-CONTRACT\n"
        + body_hash
        + "\n--SOURCE-UNITS--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in source_identity
        )
        + "\n--MANIFEST--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in manifest_identity
        )
        + "\n"
    )
    contract_hash = hashlib.sha256(contract_payload.encode("utf-8")).hexdigest()

    raw = {
        "spec_issue": 1,
        "head": "a" * 40,
        "baseline": "b" * 40,
        "branch": "spec-1",
        "mode": "full",
        "prior_checkpoint": None,
        "spec_body_hash": body_hash,
        "spec_contract_hash": contract_hash,
        "default_branch": "main",
        "default_head": "e" * 40,
        "source_counts": {"user_stories": 2, "out_of_scope": 1},
        "manifest": [
            {
                "cell": "US-1",
                "source": "User Stories | 1",
                "requirement": r"NO_CANDIDATES | EXPLICIT_CREATE_NEW \ literal",
            },
            {
                "cell": "US-2",
                "source": "User Stories 2",
                "requirement": "line one\nline two <br> & markup",
            },
            {
                "cell": "OOS-1",
                "source": "Out of Scope 1",
                "requirement": r"literal \| stays literal",
            },
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

    contract = {
        key: raw[key]
        for key in CONTRACT_HANDOFF_KEYS
        if key != "contract_identity"
    }
    contract["contract_identity"] = {
        "source_units": source_identity,
        "manifest": manifest_identity,
    }
    coherent_tcm = {
        "id": 99,
        "body": (
            "## Ticket Coverage Manifest\n"
            f"Spec Body Hash: {body_hash}\n"
            f"Spec Contract Hash: {contract_hash}\n"
            "US-1 -> implementation ticket #1\n"
            "US-2 -> implementation ticket #1\n"
            "OOS-1 -> authoritative-exclusion"
        ),
    }
    coherence_summary = {
        "ticket_coverage_manifest": coherent_tcm,
        "ticket_coverage_manifest_count": 1,
    }
    coherent = contract_coherence(coherence_summary, contract)
    assert coherent["status"] == "PASS"
    bad_body = coherent_tcm["body"].replace(
        f"Spec Contract Hash: {contract_hash}",
        f"Spec Contract Hash: {'9' * 64}",
    )
    broken_summary = {
        "ticket_coverage_manifest": {"id": 99, "body": bad_body},
        "ticket_coverage_manifest_count": 1,
    }
    try:
        contract_coherence(broken_summary, contract)
    except ValidationError:
        pass
    else:
        raise AssertionError("contract-incoherent TCM was accepted")

    assembled = finalize_parts(
    assembled = finalize_parts(
        contract,
        raw["proofs"],
        raw["gates"],
        mode="full",
        prior_checkpoint=None,
        repairs=[],
        inherited_findings=[],
    )
    assert assembled["verification_hash"] == state["verification_hash"]

    receipt = render_receipt(state)
    assert f"**Receipt format:** {RECEIPT_FORMAT}" in receipt
    assert "### Spec Contract Manifest" in receipt
    assert "### Spec Proof Objects" not in receipt
    assert "- proven: US-1, US-2" in receipt
    assert "&#124;" in receipt
    assert "&lt;br&gt;" in receipt
    _validate_receipt_round_trip(receipt, state)

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "contract.json"
        path.write_text(
            json.dumps(contract, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _require_contract_digest(path, digest)
        try:
            _require_contract_digest(path, "0" * 64)
        except ValidationError:
            pass
        else:
            raise AssertionError("invalid contract handoff digest was accepted")

    tampered = json.loads(json.dumps(contract))
    tampered["contract_identity"]["source_units"][0][1] = "9" * 64
    try:
        _validate_contract_identity(tampered)
    except ValidationError:
        pass
    else:
        raise AssertionError("structurally invalid contract identity was accepted")

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
    coherence = sub.add_parser("contract-coherence")
    coherence.add_argument("--comments-summary", required=True)
    coherence.add_argument("--contract-input", required=True)
    parts = sub.add_parser("finalize-parts")
    parts.add_argument("--contract-input", required=True)
    parts.add_argument("--contract-digest", required=True)
    parts.add_argument("--proofs-input", required=True)
    parts.add_argument("--gates-input", required=True)
    parts.add_argument("--mode", required=True)
    parts.add_argument("--prior-checkpoint")
    parts.add_argument("--repair", action="append", default=[])
    parts.add_argument("--inherited-finding", action="append", default=[])
    parts.add_argument("--receipt-output", required=True)
    sub.add_parser("self-test")
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        if args.command == "comments":
            result = comments_summary(_read_json(args.input))
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "contract-coherence":
            result = contract_coherence(
                _read_json(args.comments_summary),
                _read_json(args.contract_input),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "finalize-parts":
            _require_contract_digest(args.contract_input, args.contract_digest)
            _emit_finalization(
                finalize_parts(
                    _read_json(args.contract_input),
                    _read_json(args.proofs_input),
                    _read_json(args.gates_input),
                    mode=args.mode,
                    prior_checkpoint=args.prior_checkpoint,
                    repairs=args.repair,
                    inherited_findings=args.inherited_finding,
                ),
                args.receipt_output,
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
