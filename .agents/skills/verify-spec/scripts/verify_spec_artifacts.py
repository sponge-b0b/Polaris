#!/usr/bin/env python3
"""Deterministic artifact mechanics for the Polaris ``$verify-spec`` skill.

The verifier owns semantic judgment. This utility owns repeatable bookkeeping:
comment parsing, proof-packet validation/hashing, certification-slice construction,
carry-forward delta validation, receipt rendering, and receipt byte validation.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
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
REQUIRED_PROOF_FIELDS = (
    "proof",
    "cells",
    "predicate",
    "falsifier",
    "domain_boundary",
    "nested_universe",
    "evidence",
    "assumptions",
    "invalidation_boundary",
    "evidence_stability",
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


def _matches(path: str, patterns: list[str]) -> bool:
    path = path.strip("/")
    for pattern in patterns:
        pattern = pattern.strip("/")
        if pattern.endswith("/**"):
            prefix = pattern[:-3].rstrip("/")
            if path == prefix or path.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False


def _validate_nested(value: Any, proof: str) -> None:
    _require(isinstance(value, dict), f"{proof} nested_universe must be an object")
    mode = _text(value.get("mode"), f"{proof} nested_universe.mode")
    _require(mode in {"explicit", "exhaustive", "not-applicable"}, f"{proof} invalid nested universe mode")
    if mode == "explicit":
        members = isinstance(value.get("members"), list) and bool(value["members"])
        generated = bool(str(value.get("generator") or "").strip()) and bool(
            str(value.get("member_digest") or "").strip()
        )
        _require(members or generated, f"{proof} explicit nested universe needs members or generator+digest")
    elif mode == "exhaustive":
        _text(value.get("mechanism"), f"{proof} nested universe mechanism")
        _require("result" in value, f"{proof} exhaustive nested universe requires result")
    else:
        _text(value.get("reason"), f"{proof} nested universe reason")


def _validate_evidence(proof: dict[str, Any]) -> list[str]:
    proof_id = proof["proof"]
    evidence = proof["evidence"]
    boundary = proof["invalidation_boundary"]
    stability = proof["evidence_stability"]
    _require(isinstance(evidence, list) and bool(evidence), f"{proof_id} evidence must be non-empty")
    _require(isinstance(boundary, list) and bool(boundary), f"{proof_id} invalidation boundary must be non-empty")
    patterns = [_text(item, f"{proof_id} invalidation boundary") for item in boundary]
    _require(stability in {"repository-immutable", "mutable"}, f"{proof_id} invalid evidence stability")
    for item in evidence:
        _require(isinstance(item, dict), f"{proof_id} evidence entries must be objects")
        kind = _text(item.get("kind"), f"{proof_id} evidence kind")
        _text(item.get("ref"), f"{proof_id} evidence ref")
        if kind == "repository":
            path = _text(item.get("path"), f"{proof_id} repository evidence path")
            _require(_matches(path, patterns), f"{proof_id} repository evidence outside invalidation boundary: {path}")
        elif stability == "repository-immutable" and item.get("immutable_snapshot") is not True:
            raise ValidationError(
                f"{proof_id} is repository-immutable but relies on mutable {kind} evidence: {item.get('ref')}"
            )
    warnings: list[str] = []
    if len(proof["cells"]) > 12:
        warnings.append(f"{proof_id} maps {len(proof['cells'])} cells; review grouping cohesion")
    return warnings


def prepare_packet(raw: Any) -> dict[str, Any]:
    _require(isinstance(raw, dict), "packet input must be an object")
    _require(isinstance(raw.get("spec_issue"), int) and raw["spec_issue"] > 0, "spec_issue must be positive")
    for field in ("head", "baseline"):
        _require(bool(SHA_RE.fullmatch(_text(raw.get(field), field))), f"{field} must be a lowercase 40-char SHA")
    for field in ("spec_body_hash", "spec_contract_hash"):
        _require(bool(DIGEST_RE.fullmatch(_text(raw.get(field), field))), f"{field} must be a SHA-256 digest")

    cells, manifest = _manifest_index(raw.get("manifest"))
    coverage = raw.get("coverage")
    _require(isinstance(coverage, list) and len(coverage) == len(cells), "manifest/coverage counts differ")
    coverage_index: dict[str, dict[str, Any]] = {}
    coverage_order: list[str] = []
    for row in coverage:
        _require(isinstance(row, dict), "coverage rows must be objects")
        cell = _text(row.get("cell"), "coverage cell")
        proof = _text(row.get("proof"), f"coverage {cell} proof")
        state = _text(row.get("state"), f"coverage {cell} state")
        _require(bool(PROOF_RE.fullmatch(proof)), f"invalid proof ID: {proof}")
        _require(state in {"pending-certification", "proven", "not-applicable", "unresolved"}, f"invalid coverage state: {state}")
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
        _require(isinstance(proof["cells"], list) and bool(proof["cells"]), f"{proof_id} cells must be non-empty")
        _require(len(proof["cells"]) == len(set(proof["cells"])), f"{proof_id} has duplicate cells")
        for cell in proof["cells"]:
            _require(cell in manifest, f"{proof_id} references unknown cell: {cell}")
            _require(coverage_index[cell]["proof"] == proof_id, f"coverage/proof mismatch for {cell}")
            mapped.append(cell)
        _text(proof["predicate"], f"{proof_id} predicate")
        _text(proof["falsifier"], f"{proof_id} falsifier")
        _text(proof["domain_boundary"], f"{proof_id} domain boundary")
        _validate_nested(proof["nested_universe"], proof_id)
        _require(isinstance(proof["assumptions"], list), f"{proof_id} assumptions must be a list")
        warnings.extend(_validate_evidence(proof))
        proof.pop("proof_object_hash", None)
        proof["proof_object_hash"] = _digest(proof)
        prepared.append(proof)
    _require(len(mapped) == len(set(mapped)), "manifest cell mapped by multiple proof objects")
    _require(set(mapped) == set(cells), "proof objects do not cover complete manifest")
    _require(all(row["proof"] in proof_ids for row in coverage), "coverage references undeclared proof")

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
    _require(result["proof_packet_hash"] == expected_hash, "proof_packet_hash mismatch")
    _require(result["validation"] == expected_validation, "packet validation metadata mismatch")
    return result


def make_slice(packet: Any, proof_ids: list[str]) -> dict[str, Any]:
    packet = _prepared(packet)
    wanted = set(proof_ids)
    _require(bool(wanted), "at least one proof ID is required")
    proofs = [row for row in packet["proof_objects"] if row["proof"] in wanted]
    _require({row["proof"] for row in proofs} == wanted, "slice requested unknown proof")
    assigned = {cell for proof in proofs for cell in proof["cells"]}
    result = {
        "spec_issue": packet["spec_issue"],
        "head": packet["head"],
        "spec_contract_hash": packet["spec_contract_hash"],
        "manifest": [row for row in packet["manifest"] if row["cell"] in assigned],
        "coverage": [row for row in packet["coverage"] if row["cell"] in assigned],
        "proof_objects": proofs,
    }
    result["certification_slice_hash"] = _digest(result)
    return result


def _git_paths(repo_root: str | Path, from_head: str, to_head: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff", "--name-only", "--no-renames", from_head, to_head],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ValidationError(
            f"git delta failed for {from_head}..{to_head}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _path_digest(paths: list[str]) -> str:
    return hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest()


def build_carry_forward(
    packet: Any,
    certifications: Any,
    policy_impact: Any,
    *,
    final_head: str,
    repo_root: str | Path,
) -> list[dict[str, Any]]:
    packet = _prepared(packet)
    _require(isinstance(certifications, list), "certifications must be a list")
    _require(isinstance(policy_impact, dict), "policy impact must be keyed by proof ID")
    proofs = {row["proof"]: row for row in packet["proof_objects"]}
    certs = {row.get("proof"): row for row in certifications if isinstance(row, dict)}
    _require(set(certs) == set(proofs), "certifications must cover every proof exactly once")
    rows: list[dict[str, Any]] = []
    for proof_id, proof in proofs.items():
        cert = certs[proof_id]
        certified_head = _text(cert.get("certified_head"), f"{proof_id} certified_head")
        if certified_head == final_head:
            continue
        impact = _text(policy_impact.get(proof_id), f"{proof_id} proof-policy impact")
        _require(impact in {"none", "invalidating", "uncertain"}, f"{proof_id} invalid proof-policy impact")
        _require(impact == "none", f"{proof_id} cannot carry with proof-policy impact: {impact}")
        _require(proof["evidence_stability"] == "repository-immutable", f"{proof_id} cannot carry mutable evidence")
        paths = _git_paths(repo_root, certified_head, final_head)
        hits = [path for path in paths if _matches(path, proof["invalidation_boundary"])]
        _require(not hits, f"{proof_id} carry-forward intersects invalidation boundary: {hits}")
        rows.append(
            {
                "proof": proof_id,
                "from_head": certified_head,
                "to_head": final_head,
                "repository_delta_digest": _path_digest(paths),
                "boundary_intersection": 0,
                "proof_policy_impact": "none",
                "result": "retained-certified",
            }
        )
    return rows


def validate_final(state: Any, *, repo_root: str | Path | None = None) -> dict[str, Any]:
    _require(isinstance(state, dict), "final state must be an object")
    packet = _prepared(state.get("packet"))
    verification = state.get("verification")
    _require(isinstance(verification, dict), "verification metadata must be an object")
    final_head = _text(verification.get("final_head"), "final_head")
    _require(final_head == packet["head"], "final_head must equal packet head")
    _require(bool(SHA_RE.fullmatch(final_head)), "final_head must be a lowercase 40-char SHA")

    proofs = {row["proof"]: row for row in packet["proof_objects"]}
    cert_rows = state.get("certifications")
    _require(isinstance(cert_rows, list) and len(cert_rows) == len(proofs), "certification count mismatch")
    certs: dict[str, dict[str, Any]] = {}
    for cert in cert_rows:
        _require(isinstance(cert, dict), "certification rows must be objects")
        proof_id = _text(cert.get("proof"), "certification proof")
        _require(proof_id in proofs and proof_id not in certs, f"invalid/duplicate certification: {proof_id}")
        _require(cert.get("proof_object_hash") == proofs[proof_id]["proof_object_hash"], f"{proof_id} certification hash mismatch")
        _text(cert.get("certified_head"), f"{proof_id} certified_head")
        _text(cert.get("certification_slice_hash"), f"{proof_id} certification_slice_hash")
        _require(cert.get("certification") == "certified", f"{proof_id} is not certified")
        _require(cert.get("disposition") in {"proven", "not-applicable"}, f"{proof_id} invalid disposition")
        _text(cert.get("evidence"), f"{proof_id} certification evidence")
        certs[proof_id] = cert

    carry = state.get("carry_forward", [])
    _require(isinstance(carry, list), "carry_forward must be a list")
    carry_by_proof: dict[str, list[dict[str, Any]]] = {}
    for row in carry:
        _require(isinstance(row, dict), "carry-forward rows must be objects")
        proof_id = _text(row.get("proof"), "carry-forward proof")
        _require(proof_id in proofs, f"unknown carry-forward proof: {proof_id}")
        carry_by_proof.setdefault(proof_id, []).append(row)

    for proof_id, cert in certs.items():
        certified_head = cert["certified_head"]
        rows = carry_by_proof.get(proof_id, [])
        if certified_head == final_head:
            _require(not rows, f"{proof_id} certified at final HEAD must not carry forward")
            continue
        _require(repo_root is not None, f"{proof_id} carry-forward validation requires --repo-root")
        _require(proofs[proof_id]["evidence_stability"] == "repository-immutable", f"{proof_id} mutable proof cannot carry")
        _require(len(rows) == 1, f"{proof_id} must have exactly one deterministic carry-forward row")
        row = rows[0]
        _require(row.get("from_head") == certified_head and row.get("to_head") == final_head, f"{proof_id} invalid carry-forward endpoints")
        paths = _git_paths(repo_root, certified_head, final_head)
        hits = [path for path in paths if _matches(path, proofs[proof_id]["invalidation_boundary"])]
        _require(row.get("repository_delta_digest") == _path_digest(paths), f"{proof_id} delta digest mismatch")
        _require(row.get("boundary_intersection") == len(hits), f"{proof_id} boundary count mismatch")
        _require(not hits, f"{proof_id} invalidation boundary intersects final delta: {hits}")
        _require(row.get("proof_policy_impact") == "none", f"{proof_id} proof-policy impact prevents carry")
        _require(row.get("result") == "retained-certified", f"{proof_id} carry-forward not retained")

    coverage_map = {row["cell"]: row for row in packet["coverage"]}
    final_coverage = []
    for manifest_row in packet["manifest"]:
        cell = manifest_row["cell"]
        proof_id = coverage_map[cell]["proof"]
        final_coverage.append(
            {"cell": cell, "state": certs[proof_id]["disposition"], "proof": proof_id}
        )

    result = dict(state)
    result["packet"] = packet
    result["final_coverage"] = final_coverage
    result["summary"] = {
        "manifest_cells": len(packet["manifest"]),
        "coverage_rows": len(final_coverage),
        "proof_objects": len(proofs),
        "certified_proof_objects": len(certs),
        "unresolved_cells": 0,
    }
    return result


def _table(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return value.replace("|", "\\|").replace("\n", "<br>")


def render_receipt(state: Any, *, repo_root: str | Path | None = None) -> str:
    state = validate_final(state, repo_root=repo_root)
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
        "**Proof certification execution:** independent-subagent",
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
        lines.append(f"| {row['cell']} | {_table(row['source'])} | {_table(row['requirement'])} |")

    lines += [
        "",
        "### Spec Proof Objects",
        "| Proof | Object Hash | Cells | Predicate | Falsifier | Domain / Nested Universe | Evidence / Assumptions | Invalidation Boundary | Evidence Stability |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for proof in packet["proof_objects"]:
        domain = {"boundary": proof["domain_boundary"], "nested_universe": proof["nested_universe"]}
        evidence = {"evidence": proof["evidence"], "assumptions": proof["assumptions"]}
        lines.append(
            "| " + " | ".join(
                [
                    proof["proof"],
                    proof["proof_object_hash"],
                    _table(proof["cells"]),
                    _table(proof["predicate"]),
                    _table(proof["falsifier"]),
                    _table(domain),
                    _table(evidence),
                    _table(proof["invalidation_boundary"]),
                    proof["evidence_stability"],
                ]
            ) + " |"
        )

    lines += [
        "",
        "### Independent Proof Certification",
        "| Proof | Object Hash | Certified HEAD | Slice Hash | Certification | Disposition | Certification Evidence |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    certs = {row["proof"]: row for row in state["certifications"]}
    for proof in packet["proof_objects"]:
        cert = certs[proof["proof"]]
        lines.append(
            f"| {proof['proof']} | {cert['proof_object_hash']} | {cert['certified_head']} | "
            f"{cert['certification_slice_hash']} | {cert['certification']} | {cert['disposition']} | {_table(cert['evidence'])} |"
        )

    lines += [
        "",
        "### Proof Certification Carry-Forward",
        "| Proof | From HEAD | To HEAD | Repository Delta Digest | Boundary Intersection | Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if state.get("carry_forward"):
        for row in state["carry_forward"]:
            lines.append(
                f"| {row['proof']} | {row['from_head']} | {row['to_head']} | "
                f"{row['repository_delta_digest']} | {row['boundary_intersection']} | {row['result']} |"
            )
    else:
        lines.append("| None | — | — | — | — | — |")

    lines += [
        "",
        "### Spec Contract Coverage",
        "| Cell | State | Proof |",
        "| --- | --- | --- |",
    ]
    for row in state["final_coverage"]:
        lines.append(f"| {row['cell']} | {row['state']} | {row['proof']} |")

    lines += ["", "### Verification Gates"]
    gates = verification.get("gates") or []
    _require(bool(gates), "receipt requires at least one verification gate")
    for gate in gates:
        _require(isinstance(gate, dict), "gate rows must be objects")
        name = _text(gate.get("name"), "gate name")
        status = _text(gate.get("status"), f"gate {name} status")
        evidence = _text(gate.get("evidence"), f"gate {name} evidence")
        lines.append(f"- {name}: {status} — {evidence}")

    lines += ["", "### Unrelated Inherited Findings"]
    findings = verification.get("unrelated_inherited_findings") or []
    lines.extend(f"- {item}" for item in findings) if findings else lines.append("- None")
    return "\n".join(lines) + "\n"


def validate_receipt(state: Any, receipt: str | Path, *, repo_root: str | Path | None = None) -> None:
    _require(
        Path(receipt).read_text(encoding="utf-8") == render_receipt(state, repo_root=repo_root),
        "receipt bytes differ from deterministic rendering of validated final state",
    )


def self_test() -> None:
    packet = {
        "spec_issue": 1,
        "head": "a" * 40,
        "baseline": "b" * 40,
        "spec_body_hash": "c" * 64,
        "spec_contract_hash": "d" * 64,
        "manifest": [{"cell": "US-1", "source": "User Stories 1", "requirement": "must hold"}],
        "coverage": [{"cell": "US-1", "proof": "P-1", "state": "pending-certification"}],
        "proof_objects": [
            {
                "proof": "P-1",
                "cells": ["US-1"],
                "predicate": "the required behavior holds",
                "falsifier": "the required behavior does not hold",
                "domain_boundary": "application/x.py",
                "nested_universe": {"mode": "not-applicable", "reason": "no quantified domain"},
                "evidence": [{"kind": "repository", "ref": "application/x.py:1", "path": "application/x.py"}],
                "assumptions": [],
                "invalidation_boundary": ["application/x.py"],
                "evidence_stability": "repository-immutable",
            }
        ],
    }
    prepared = prepare_packet(packet)
    assert prepare_packet(packet)["proof_packet_hash"] == prepared["proof_packet_hash"]
    assert make_slice(prepared, ["P-1"])["certification_slice_hash"]
    broken = json.loads(json.dumps(packet))
    broken["proof_objects"][0]["evidence"].append({"kind": "tracker", "ref": "current issue state"})
    try:
        prepare_packet(broken)
    except ValidationError:
        pass
    else:
        raise AssertionError("mutable evidence admission test did not fail")
    broken = json.loads(json.dumps(packet))
    broken["proof_objects"][0]["invalidation_boundary"] = ["tests/**"]
    try:
        prepare_packet(broken)
    except ValidationError:
        pass
    else:
        raise AssertionError("boundary admission test did not fail")

    with tempfile.TemporaryDirectory() as tempdir:
        repo = Path(tempdir)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "verify-spec@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "verify-spec"], check=True)
        (repo / "other.txt").write_text("one\n")
        subprocess.run(["git", "-C", str(repo), "add", "other.txt"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "one"], check=True)
        first = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        (repo / "other.txt").write_text("two\n")
        subprocess.run(["git", "-C", str(repo), "commit", "-qam", "two"], check=True)
        second = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        raw = dict(prepared)
        raw.pop("proof_packet_hash")
        raw.pop("validation")
        raw["head"] = second
        prepared = prepare_packet(raw)
        proof_hash = prepared["proof_objects"][0]["proof_object_hash"]
        certs = [
            {
                "proof": "P-1",
                "proof_object_hash": proof_hash,
                "certified_head": first,
                "certification_slice_hash": "e" * 64,
                "certification": "certified",
                "disposition": "proven",
                "evidence": "self-test",
            }
        ]
        rows = build_carry_forward(prepared, certs, {"P-1": "none"}, final_head=second, repo_root=repo)
        assert len(rows) == 1 and rows[0]["boundary_intersection"] == 0


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("comments")
    p.add_argument("--input", required=True)
    p = sub.add_parser("prepare-packet")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("make-slice")
    p.add_argument("--packet", required=True)
    p.add_argument("--proof", action="append", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("build-carry-forward")
    p.add_argument("--packet", required=True)
    p.add_argument("--certifications", required=True)
    p.add_argument("--policy-impact", required=True)
    p.add_argument("--final-head", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("validate-final")
    p.add_argument("--input", required=True)
    p.add_argument("--repo-root")
    p.add_argument("--output")
    p = sub.add_parser("render-receipt")
    p.add_argument("--input", required=True)
    p.add_argument("--repo-root")
    p.add_argument("--output", required=True)
    p = sub.add_parser("validate-receipt")
    p.add_argument("--input", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--repo-root")
    sub.add_parser("self-test")
    return parser.parse_args()


def main() -> int:
    args = _args()
    try:
        if args.command == "comments":
            print(json.dumps(comments_summary(_read_json(args.input)), indent=2, sort_keys=True))
        elif args.command == "prepare-packet":
            _write_json(args.output, prepare_packet(_read_json(args.input)))
        elif args.command == "make-slice":
            _write_json(args.output, make_slice(_read_json(args.packet), args.proof))
        elif args.command == "build-carry-forward":
            _write_json(
                args.output,
                build_carry_forward(
                    _read_json(args.packet),
                    _read_json(args.certifications),
                    _read_json(args.policy_impact),
                    final_head=args.final_head,
                    repo_root=args.repo_root,
                ),
            )
        elif args.command == "validate-final":
            result = validate_final(_read_json(args.input), repo_root=args.repo_root)
            _write_json(args.output, result) if args.output else print(json.dumps(result["summary"], indent=2, sort_keys=True))
        elif args.command == "render-receipt":
            Path(args.output).write_text(render_receipt(_read_json(args.input), repo_root=args.repo_root), encoding="utf-8")
        elif args.command == "validate-receipt":
            validate_receipt(_read_json(args.input), args.receipt, repo_root=args.repo_root)
            print("RECEIPT VALIDATION: PASS")
        elif args.command == "self-test":
            self_test()
            print("VERIFY-SPEC ARTIFACT SELF-TEST: PASS")
        else:  # pragma: no cover
            raise AssertionError(args.command)
    except (OSError, json.JSONDecodeError, ValidationError, subprocess.SubprocessError) as exc:
        print(f"VERIFY-SPEC ARTIFACT ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
