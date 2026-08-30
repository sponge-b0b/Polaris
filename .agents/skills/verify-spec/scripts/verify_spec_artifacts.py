#!/usr/bin/env python3
"""Deterministic artifact mechanics for the Polaris ``$verify-spec`` skill.

The verifier owns semantic judgment. This utility owns repeatable bookkeeping:
comment parsing, proof-packet validation/hashing, final-state validation,
receipt rendering, and receipt byte validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

CELL_RE = re.compile(r"^(?:US|ID|TD|OOS|NORM)-\d+(?:\.[A-Za-z0-9_-]+)?$")
PROOF_RE = re.compile(r"^P-\d+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
BASELINE_RE = re.compile(
    r"\*\*Baseline Commit Hash:\*\*\s+(?P<sha>[0-9a-fA-F]{40})"
)
RECEIPT_HEADER = "## Spec Verification Receipt"
COVERAGE_STATES = {"proven", "not-applicable", "unresolved"}
GATE_STATES = {"PASS", "NOT APPLICABLE"}
REQUIRED_PROOF_FIELDS = (
    "proof",
    "cells",
    "predicate",
    "falsifier",
    "domain_boundary",
    "nested_universe",
    "evidence",
    "assumptions",
    "disposition",
)


class ValidationError(ValueError):
    """Raised when a deterministic verifier-artifact invariant fails."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _text(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"{label} must be non-empty")
    return value.strip()


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _flatten_pages(raw: Any) -> list[dict[str, Any]]:
    _require(isinstance(raw, list), "comment payload must be a JSON list")
    if not raw:
        return []
    if all(isinstance(item, dict) for item in raw):
        return list(raw)
    result: list[dict[str, Any]] = []
    for page in raw:
        _require(isinstance(page, list), "paginated comment payload contains non-list page")
        for item in page:
            _require(isinstance(item, dict), "comment page contains non-object item")
            result.append(item)
    return result


def comments_summary(raw: Any) -> dict[str, Any]:
    comments = sorted(
        _flatten_pages(raw),
        key=lambda item: (str(item.get("created_at") or ""), int(item.get("id") or 0)),
    )
    baselines: list[str] = []
    receipts: list[dict[str, Any]] = []
    for comment in comments:
        body = str(comment.get("body") or "")
        match = BASELINE_RE.search(body)
        if match:
            baselines.append(match.group("sha").lower())
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
        "baseline_commit": baselines[-1] if baselines else None,
        "latest_receipt": receipts[-1] if receipts else None,
    }


def _manifest_index(manifest: Any) -> tuple[list[str], dict[str, dict[str, Any]]]:
    _require(isinstance(manifest, list) and bool(manifest), "manifest must be non-empty")
    order: list[str] = []
    index: dict[str, dict[str, Any]] = {}
    for row in manifest:
        _require(isinstance(row, dict), "manifest rows must be objects")
        cell = _text(row.get("cell"), "manifest cell")
        _require(bool(CELL_RE.fullmatch(cell)), f"invalid manifest cell: {cell}")
        _require(cell not in index, f"duplicate manifest cell: {cell}")
        _text(row.get("source"), f"manifest {cell} source")
        _text(row.get("requirement"), f"manifest {cell} requirement")
        order.append(cell)
        index[cell] = row
    return order, index


def _validate_nested(value: Any, proof: str) -> None:
    _require(isinstance(value, dict), f"{proof} nested_universe must be an object")
    mode = _text(value.get("mode"), f"{proof} nested_universe.mode")
    _require(
        mode in {"explicit", "exhaustive", "not-applicable"},
        f"{proof} invalid nested universe mode",
    )
    if mode == "explicit":
        members = isinstance(value.get("members"), list) and bool(value["members"])
        generated = bool(str(value.get("generator") or "").strip()) and bool(
            str(value.get("member_digest") or "").strip()
        )
        _require(
            members or generated,
            f"{proof} explicit nested universe needs members or generator+digest",
        )
    elif mode == "exhaustive":
        _text(value.get("mechanism"), f"{proof} nested_universe mechanism")
        _require("result" in value, f"{proof} exhaustive nested universe requires result")
    else:
        _text(value.get("reason"), f"{proof} nested_universe reason")


def _validate_evidence(proof: dict[str, Any]) -> None:
    proof_id = proof["proof"]
    evidence = proof["evidence"]
    _require(
        isinstance(evidence, list) and bool(evidence),
        f"{proof_id} evidence must be non-empty",
    )
    for item in evidence:
        _require(isinstance(item, dict), f"{proof_id} evidence entries must be objects")
        kind = _text(item.get("kind"), f"{proof_id} evidence kind")
        _text(item.get("ref"), f"{proof_id} evidence ref")
        if kind == "repository":
            _text(item.get("path"), f"{proof_id} repository evidence path")


def prepare_packet(raw: Any) -> dict[str, Any]:
    _require(isinstance(raw, dict), "packet input must be an object")
    _require(
        isinstance(raw.get("spec_issue"), int) and raw["spec_issue"] > 0,
        "spec_issue must be positive",
    )
    for field in ("head", "baseline"):
        _require(
            bool(SHA_RE.fullmatch(_text(raw.get(field), field))),
            f"{field} must be a lowercase 40-char SHA",
        )
    for field in ("spec_body_hash", "spec_contract_hash"):
        _require(
            bool(DIGEST_RE.fullmatch(_text(raw.get(field), field))),
            f"{field} must be a SHA-256 digest",
        )

    cells, manifest = _manifest_index(raw.get("manifest"))
    coverage = raw.get("coverage")
    _require(
        isinstance(coverage, list) and len(coverage) == len(cells),
        "manifest/coverage counts differ",
    )
    coverage_index: dict[str, dict[str, Any]] = {}
    coverage_order: list[str] = []
    for row in coverage:
        _require(isinstance(row, dict), "coverage rows must be objects")
        cell = _text(row.get("cell"), "coverage cell")
        proof = _text(row.get("proof"), f"coverage {cell} proof")
        state = _text(row.get("state"), f"coverage {cell} state")
        _require(bool(PROOF_RE.fullmatch(proof)), f"invalid proof ID: {proof}")
        _require(state in COVERAGE_STATES, f"invalid coverage state: {state}")
        _require(cell not in coverage_index, f"duplicate coverage cell: {cell}")
        coverage_index[cell] = row
        coverage_order.append(cell)
    _require(coverage_order == cells, "coverage rows must follow exact manifest order")

    proofs = raw.get("proof_objects")
    _require(isinstance(proofs, list) and bool(proofs), "proof_objects must be non-empty")
    prepared: list[dict[str, Any]] = []
    proof_ids: set[str] = set()
    mapped: list[str] = []
    warnings: list[str] = []

    for original in proofs:
        _require(isinstance(original, dict), "proof objects must be objects")
        proof = dict(original)
        for field in REQUIRED_PROOF_FIELDS:
            _require(field in proof, f"proof object missing field: {field}")

        proof_id = _text(proof["proof"], "proof ID")
        _require(bool(PROOF_RE.fullmatch(proof_id)), f"invalid proof ID: {proof_id}")
        _require(proof_id not in proof_ids, f"duplicate proof object: {proof_id}")
        proof_ids.add(proof_id)

        _require(
            isinstance(proof["cells"], list) and bool(proof["cells"]),
            f"{proof_id} cells must be non-empty",
        )
        _require(
            len(proof["cells"]) == len(set(proof["cells"])),
            f"{proof_id} has duplicate cells",
        )
        disposition = _text(proof["disposition"], f"{proof_id} disposition")
        _require(
            disposition in COVERAGE_STATES,
            f"{proof_id} invalid disposition: {disposition}",
        )

        for cell in proof["cells"]:
            _require(cell in manifest, f"{proof_id} references unknown cell: {cell}")
            _require(
                coverage_index[cell]["proof"] == proof_id,
                f"coverage/proof mismatch for {cell}",
            )
            _require(
                coverage_index[cell]["state"] == disposition,
                f"coverage/disposition mismatch for {cell}",
            )
            mapped.append(cell)

        _text(proof["predicate"], f"{proof_id} predicate")
        _text(proof["falsifier"], f"{proof_id} falsifier")
        _text(proof["domain_boundary"], f"{proof_id} domain boundary")
        _validate_nested(proof["nested_universe"], proof_id)
        _validate_evidence(proof)
        _require(
            isinstance(proof["assumptions"], list),
            f"{proof_id} assumptions must be a list",
        )

        if len(proof["cells"]) > 12:
            warnings.append(
                f"{proof_id} maps {len(proof['cells'])} cells; review grouping cohesion"
            )

        proof.pop("proof_object_hash", None)
        proof["proof_object_hash"] = _digest(proof)
        prepared.append(proof)

    _require(
        len(mapped) == len(set(mapped)),
        "manifest cell mapped by multiple proof objects",
    )
    _require(set(mapped) == set(cells), "proof objects do not cover complete manifest")
    _require(
        all(row["proof"] in proof_ids for row in coverage),
        "coverage references undeclared proof",
    )

    result = dict(raw)
    result["proof_objects"] = prepared
    result.pop("proof_packet_hash", None)
    result.pop("validation", None)
    result["proof_packet_hash"] = _digest(result)
    result["validation"] = {
        "manifest_cells": len(cells),
        "coverage_rows": len(coverage),
        "proof_objects": len(prepared),
        "missing_manifest_cells": 0,
        "unknown_manifest_cells": 0,
        "duplicate_cell_mappings": 0,
        "unreferenced_proof_objects": 0,
        "missing_proof_fields": 0,
        "warnings": warnings,
    }
    return result


def _prepared(packet: Any) -> dict[str, Any]:
    _require(isinstance(packet, dict), "prepared packet must be an object")
    expected_hash = packet.get("proof_packet_hash")
    expected_validation = packet.get("validation")
    raw = dict(packet)
    raw.pop("proof_packet_hash", None)
    raw.pop("validation", None)
    result = prepare_packet(raw)
    _require(
        result["proof_packet_hash"] == expected_hash,
        "proof_packet_hash mismatch",
    )
    _require(
        result["validation"] == expected_validation,
        "packet validation metadata mismatch",
    )
    return result


def _validate_gates(verification: dict[str, Any]) -> list[dict[str, str]]:
    gates = verification.get("gates")
    _require(isinstance(gates, list) and bool(gates), "verification gates must be non-empty")
    validated: list[dict[str, str]] = []
    names: set[str] = set()
    for row in gates:
        _require(isinstance(row, dict), "gate rows must be objects")
        name = _text(row.get("name"), "gate name")
        _require(name not in names, f"duplicate gate name: {name}")
        names.add(name)
        status = _text(row.get("status"), f"gate {name} status")
        _require(
            status in GATE_STATES,
            f"gate {name} must be PASS or NOT APPLICABLE for final validation",
        )
        command = _text(row.get("command"), f"gate {name} command")
        evidence = _text(row.get("evidence"), f"gate {name} evidence")
        validated.append(
            {
                "name": name,
                "status": status,
                "command": command,
                "evidence": evidence,
            }
        )
    return validated


def validate_final(state: Any) -> dict[str, Any]:
    _require(isinstance(state, dict), "final state must be an object")
    packet = _prepared(state.get("packet"))
    verification = state.get("verification")
    _require(isinstance(verification, dict), "verification metadata must be an object")

    final_head = _text(verification.get("final_head"), "final_head")
    _require(final_head == packet["head"], "final_head must equal packet head")
    _require(
        bool(SHA_RE.fullmatch(final_head)),
        "final_head must be a lowercase 40-char SHA",
    )

    for field in ("branch", "mode", "default_branch", "default_head"):
        _text(verification.get(field), field)
    _require(
        bool(SHA_RE.fullmatch(_text(verification["default_head"], "default_head"))),
        "default_head must be a lowercase 40-char SHA",
    )

    gates = _validate_gates(verification)
    unresolved = [
        row["cell"] for row in packet["coverage"] if row["state"] == "unresolved"
    ]
    _require(not unresolved, f"unresolved manifest cells: {unresolved}")

    proven = sum(row["state"] == "proven" for row in packet["coverage"])
    not_applicable = sum(
        row["state"] == "not-applicable" for row in packet["coverage"]
    )

    result = dict(state)
    result["packet"] = packet
    result["verification"] = dict(verification)
    result["verification"]["gates"] = gates
    result["final_coverage"] = list(packet["coverage"])
    result["summary"] = {
        "manifest_cells": len(packet["manifest"]),
        "coverage_rows": len(packet["coverage"]),
        "proof_objects": len(packet["proof_objects"]),
        "proven_cells": proven,
        "not_applicable_cells": not_applicable,
        "unresolved_cells": 0,
        "verification_gates": len(gates),
    }
    return result


def _table(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    return value.replace("|", "\\|").replace("\n", "<br>")


def render_receipt(state: Any) -> str:
    state = validate_final(state)
    packet = state["packet"]
    verification = state["verification"]
    counts = verification.get("source_counts") or {}
    ownership = verification.get("ownership") or {}

    lines = [
        RECEIPT_HEADER,
        "",
        "**Status:** passed",
        f"**Verified HEAD:** {verification['final_head']}",
        f"**Verified Baseline:** {packet['baseline']}",
        f"**Branch:** {verification['branch']}",
        f"**Verification mode:** {verification['mode']}",
        f"**Prior verified checkpoint:** {verification.get('prior_checkpoint') or 'None'}",
        f"**Spec Body Hash:** {packet['spec_body_hash']}",
        f"**Spec Contract Hash:** {packet['spec_contract_hash']}",
        f"**Proof Packet Hash:** {packet['proof_packet_hash']}",
        "**Semantic proof owner:** $verify-spec parent verifier",
        f"**Default branch:** {verification['default_branch']}",
        f"**Default branch head used for ownership:** {verification['default_head']}",
        f"**Change surfaces:** {_table(verification.get('change_surfaces', []))}",
        "",
        "### Spec Contract Integrity",
        f"- User Stories: {counts.get('user_stories', 0)}",
        f"- Implementation Decisions: {counts.get('implementation_decisions', 0)}",
        f"- Testing Decisions: {counts.get('testing_decisions', 0)}",
        f"- Out of Scope: {counts.get('out_of_scope', 0)}",
        f"- Other normative source items: {counts.get('other_normative', 0)}",
        f"- Manifest cells: {len(packet['manifest'])}",
        "- Unmapped source items: 0",
        "- Duplicate source mappings: 0",
        "- Ambiguous source items: 0",
        "",
        "### Spec Change Ownership",
        f"- Spec-owned repository surfaces: {_table(ownership.get('spec_owned', []))}",
        f"- Mixed repository surfaces: {_table(ownership.get('mixed', []))}",
        f"- Inherited-only integration surfaces: {_table(ownership.get('inherited_only', []))}",
        f"- Spec-owned tracker surfaces: {_table(ownership.get('tracker', []))}",
        "",
        "### Spec Contract Manifest",
        "| Cell | Source | Requirement |",
        "| --- | --- | --- |",
    ]
    for row in packet["manifest"]:
        lines.append(
            f"| {row['cell']} | {_table(row['source'])} | {_table(row['requirement'])} |"
        )

    lines += [
        "",
        "### Spec Proof Objects",
        "| Proof | Object Hash | Cells | Disposition | Predicate | Falsifier | Domain / Nested Universe | Evidence / Assumptions |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for proof in packet["proof_objects"]:
        domain = {
            "boundary": proof["domain_boundary"],
            "nested_universe": proof["nested_universe"],
        }
        evidence = {
            "evidence": proof["evidence"],
            "assumptions": proof["assumptions"],
        }
        lines.append(
            "| "
            + " | ".join(
                [
                    proof["proof"],
                    proof["proof_object_hash"],
                    _table(proof["cells"]),
                    proof["disposition"],
                    _table(proof["predicate"]),
                    _table(proof["falsifier"]),
                    _table(domain),
                    _table(evidence),
                ]
            )
            + " |"
        )

    lines += [
        "",
        "### Spec Contract Coverage",
        "| Cell | State | Proof |",
        "| --- | --- | --- |",
    ]
    for row in state["final_coverage"]:
        lines.append(f"| {row['cell']} | {row['state']} | {row['proof']} |")

    lines += ["", "### Verification Gates"]
    for gate in verification["gates"]:
        lines.append(
            f"- {gate['name']}: {gate['status']} — command `{gate['command']}` — {gate['evidence']}"
        )

    lines += ["", "### Unrelated Inherited Findings"]
    findings = verification.get("unrelated_inherited_findings") or []
    if findings:
        lines.extend(f"- {item}" for item in findings)
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def validate_receipt(state: Any, receipt: str | Path) -> None:
    _require(
        Path(receipt).read_text(encoding="utf-8") == render_receipt(state),
        "receipt bytes differ from deterministic rendering of validated final state",
    )


def self_test() -> None:
    packet = {
        "spec_issue": 1,
        "head": "a" * 40,
        "baseline": "b" * 40,
        "spec_body_hash": "c" * 64,
        "spec_contract_hash": "d" * 64,
        "manifest": [
            {
                "cell": "US-1",
                "source": "User Stories 1",
                "requirement": "must hold",
            }
        ],
        "coverage": [{"cell": "US-1", "proof": "P-1", "state": "proven"}],
        "proof_objects": [
            {
                "proof": "P-1",
                "cells": ["US-1"],
                "predicate": "the required behavior holds",
                "falsifier": "the required behavior does not hold",
                "domain_boundary": "application/x.py",
                "nested_universe": {
                    "mode": "not-applicable",
                    "reason": "no quantified domain",
                },
                "evidence": [
                    {
                        "kind": "repository",
                        "ref": "application/x.py:1",
                        "path": "application/x.py",
                    }
                ],
                "assumptions": [],
                "disposition": "proven",
            }
        ],
    }
    prepared = prepare_packet(packet)
    assert prepare_packet(packet)["proof_packet_hash"] == prepared["proof_packet_hash"]

    bad = json.loads(json.dumps(packet))
    bad["coverage"][0]["state"] = "not-applicable"
    try:
        prepare_packet(bad)
    except ValidationError:
        pass
    else:
        raise AssertionError("coverage/disposition mismatch did not fail")

    state = {
        "packet": prepared,
        "verification": {
            "final_head": "a" * 40,
            "branch": "spec-1",
            "mode": "full",
            "prior_checkpoint": None,
            "default_branch": "main",
            "default_head": "e" * 40,
            "change_surfaces": ["application/x.py"],
            "source_counts": {
                "user_stories": 1,
                "implementation_decisions": 0,
                "testing_decisions": 0,
                "out_of_scope": 0,
                "other_normative": 0,
            },
            "ownership": {
                "spec_owned": ["application/x.py"],
                "mixed": [],
                "inherited_only": [],
                "tracker": [],
            },
            "gates": [
                {
                    "name": "Ruff lint",
                    "status": "PASS",
                    "command": "uv run ruff check .",
                    "evidence": "All checks passed",
                }
            ],
            "unrelated_inherited_findings": [],
        },
    }
    validated = validate_final(state)
    assert validated["summary"]["unresolved_cells"] == 0
    receipt = render_receipt(state)
    assert "**Semantic proof owner:** $verify-spec parent verifier" in receipt

    unresolved = json.loads(json.dumps(packet))
    unresolved["coverage"][0]["state"] = "unresolved"
    unresolved["proof_objects"][0]["disposition"] = "unresolved"
    unresolved_state = dict(state)
    unresolved_state["packet"] = prepare_packet(unresolved)
    try:
        validate_final(unresolved_state)
    except ValidationError:
        pass
    else:
        raise AssertionError("unresolved coverage did not fail final validation")


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("comments")
    p.add_argument("--input", required=True)

    p = sub.add_parser("prepare-packet")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)

    p = sub.add_parser("validate-final")
    p.add_argument("--input", required=True)
    p.add_argument("--output")

    p = sub.add_parser("render-receipt")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)

    p = sub.add_parser("validate-receipt")
    p.add_argument("--input", required=True)
    p.add_argument("--receipt", required=True)

    sub.add_parser("self-test")
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        if args.command == "comments":
            print(
                json.dumps(
                    comments_summary(_read_json(args.input)),
                    indent=2,
                    sort_keys=True,
                )
            )
        elif args.command == "prepare-packet":
            _write_json(args.output, prepare_packet(_read_json(args.input)))
        elif args.command == "validate-final":
            result = validate_final(_read_json(args.input))
            if args.output:
                _write_json(args.output, result)
            else:
                print(json.dumps(result["summary"], indent=2, sort_keys=True))
        elif args.command == "render-receipt":
            Path(args.output).write_text(
                render_receipt(_read_json(args.input)),
                encoding="utf-8",
            )
        elif args.command == "validate-receipt":
            validate_receipt(_read_json(args.input), args.receipt)
            print("RECEIPT VALIDATION: PASS")
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
