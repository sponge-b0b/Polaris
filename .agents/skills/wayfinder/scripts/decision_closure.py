from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "polaris.wayfinder-decision-closure/v1"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
PROPOSAL_HASH = re.compile(r"^sha256:([0-9a-f]{64})$")
ISSUE_URL = re.compile(r"^https://github\.com/[^/\s]+/[^/\s]+/issues/(\d+)$")
ADR_DISPOSITIONS = {"CREATED", "UPDATED", "UNCHANGED", "NOT-QUALIFIED"}
WIKI_DISPOSITIONS = {"UPDATED", "NO_DURABLE_KNOWLEDGE_CHANGED"}
WIKI_CANDIDATE_DISPOSITIONS = {"affected", "not-affected"}


class ClosureError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ClosureError(message)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), f"{label}: expected JSON object")
    return value


def _repo_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repo_clean(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout == ""


def _path_under(repo_root: Path, relative: str, prefix: str) -> Path:
    path = Path(relative)
    _need(not path.is_absolute(), f"{prefix}: path must be repository-relative")
    _need(".." not in path.parts, f"{prefix}: path may not escape repository root")
    resolved = repo_root / path
    _need(resolved.exists(), f"{prefix}: missing path {relative}")
    return resolved


def _validate_decision(receipt: dict[str, Any]) -> tuple[int, str]:
    decision = receipt.get("decision")
    _need(isinstance(decision, dict), "receipt: missing decision object")
    number = decision.get("number")
    url = decision.get("url")
    _need(isinstance(number, int) and number > 0, "decision: invalid number")
    _need(isinstance(url, str), "decision: missing URL")
    match = ISSUE_URL.fullmatch(url)
    _need(match is not None, "decision: invalid GitHub issue URL")
    _need(int(match.group(1)) == number, "decision: URL/number mismatch")
    return number, url


def _validate_ccl(repo_root: Path, receipt: dict[str, Any]) -> tuple[str, str]:
    proposal_hash = receipt.get("ccl_proposal")
    transaction_path = receipt.get("ccl_transaction")
    _need(isinstance(proposal_hash, str), "CCL: missing proposal hash")
    match = PROPOSAL_HASH.fullmatch(proposal_hash)
    _need(match is not None, "CCL: invalid proposal hash")
    _need(isinstance(transaction_path, str), "CCL: missing transaction path")
    expected = f"contracts/ccl/transactions/{match.group(1)}.json"
    _need(
        transaction_path == expected,
        "CCL: transaction path does not match proposal hash",
    )
    transaction_file = _path_under(repo_root, transaction_path, "CCL")
    transaction = _read_json(transaction_file, "CCL transaction")
    _need(
        transaction.get("proposal_hash") == proposal_hash,
        "CCL: persisted transaction proposal hash mismatch",
    )
    origin = transaction.get("origin")
    _need(isinstance(origin, dict), "CCL: persisted transaction missing origin")
    _need(
        origin.get("mode") == "wayfinder-decision",
        "CCL: persisted transaction is not a Wayfinder decision",
    )
    _need(
        isinstance(transaction.get("acceptance"), dict),
        "CCL: missing durable acceptance",
    )
    return proposal_hash, transaction_path


def _validate_adr(
    repo_root: Path,
    receipt: dict[str, Any],
    proposal_hash: str,
    transaction_path: str,
) -> tuple[str, str | None]:
    adr = receipt.get("adr")
    _need(isinstance(adr, dict), "ADR: missing disposition")
    disposition = adr.get("disposition")
    _need(disposition in ADR_DISPOSITIONS, "ADR: unsupported disposition")
    path = adr.get("path")
    projection = adr.get("projection_check")

    if disposition == "NOT-QUALIFIED":
        _need(path is None, "ADR: NOT-QUALIFIED must not name a path")
        _need(projection == "N/A", "ADR: NOT-QUALIFIED projection must be N/A")
        return disposition, None

    _need(
        isinstance(path, str) and path.startswith("docs/adr/"),
        "ADR: invalid path",
    )
    _need(projection == "PASS", "ADR: CCL projection check must be PASS")
    adr_file = _path_under(repo_root, path, "ADR")
    text = adr_file.read_text(encoding="utf-8")
    _need(
        f"ccl_proposal: {proposal_hash}" in text,
        "ADR: frontmatter does not bind the accepted proposal",
    )
    _need(
        f"ccl_transaction: {transaction_path}" in text,
        "ADR: frontmatter does not bind the persisted transaction",
    )
    return disposition, path


def _validate_wiki(receipt: dict[str, Any]) -> str:
    wiki = receipt.get("wiki_sync")
    _need(isinstance(wiki, dict), "wiki-sync: missing result")
    disposition = wiki.get("disposition")
    _need(
        disposition in WIKI_DISPOSITIONS,
        "wiki-sync: CCL-backed decisions require UPDATED or "
        "NO_DURABLE_KNOWLEDGE_CHANGED",
    )
    candidates = wiki.get("affected_knowledge_routing")
    _need(
        isinstance(candidates, list),
        "wiki-sync: missing Affected Knowledge Routing Record",
    )

    affected = 0
    for index, candidate in enumerate(candidates, start=1):
        label = f"wiki-sync candidate {index}"
        _need(isinstance(candidate, dict), f"{label}: expected object")
        for field in (
            "candidate",
            "changed_surface_authority",
            "candidate_entity_claim",
            "routing_basis",
            "reason_evidence",
        ):
            value = candidate.get(field)
            _need(
                isinstance(value, str) and bool(value.strip()),
                f"{label}: missing {field}",
            )
        candidate_disposition = candidate.get("disposition")
        _need(
            candidate_disposition in WIKI_CANDIDATE_DISPOSITIONS,
            f"{label}: unresolved/unsupported disposition",
        )
        if candidate_disposition == "affected":
            affected += 1

    mutations = wiki.get("mutations")
    _need(isinstance(mutations, list), "wiki-sync: mutations must be a list")
    _need(
        all(isinstance(path, str) and path.startswith("wiki/") for path in mutations),
        "wiki-sync: mutation paths must remain under wiki/",
    )
    _need(len(mutations) == len(set(mutations)), "wiki-sync: duplicate mutation path")

    if disposition == "NO_DURABLE_KNOWLEDGE_CHANGED":
        _need(affected == 0, "wiki-sync: no-op result contains affected candidate(s)")
        _need(not mutations, "wiki-sync: no-op result may not contain mutations")
    else:
        _need(affected > 0, "wiki-sync: UPDATED requires an affected candidate")
        _need(bool(mutations), "wiki-sync: UPDATED requires mutation paths")
        _need("wiki/log.md" in mutations, "wiki-sync: UPDATED requires wiki/log.md")

    return disposition


def validate_closure(repo_root: Path, receipt_path: Path) -> str:
    receipt = _read_json(receipt_path, "receipt")
    _need(receipt.get("schema") == SCHEMA, "receipt: unsupported schema")
    number, _ = _validate_decision(receipt)

    canonical_commit = receipt.get("canonical_commit")
    _need(
        isinstance(canonical_commit, str)
        and FULL_SHA.fullmatch(canonical_commit) is not None,
        "receipt: invalid canonical commit",
    )
    _need(
        _repo_head(repo_root) == canonical_commit,
        "repository: HEAD is not canonical commit",
    )
    _need(
        _repo_clean(repo_root),
        "repository: closure gate requires a clean worktree",
    )

    semantic_mode = receipt.get("semantic_mode")
    _need(
        semantic_mode in {"ccl-backed", "non-material"},
        "receipt: invalid semantic mode",
    )

    lines = ["WAYFINDER DECISION CLOSURE: ALLOWED", f"Decision: #{number}"]
    if semantic_mode == "ccl-backed":
        proposal_hash, transaction_path = _validate_ccl(repo_root, receipt)
        adr_disposition, adr_path = _validate_adr(
            repo_root, receipt, proposal_hash, transaction_path
        )
        wiki_disposition = _validate_wiki(receipt)
        lines.extend(
            [
                f"CCL proposal: {proposal_hash}",
                f"ADR: {adr_disposition}" + (f" {adr_path}" if adr_path else ""),
                f"Wiki sync: {wiki_disposition}",
            ]
        )
    else:
        _need(
            receipt.get("ccl_proposal") is None,
            "non-material: CCL proposal must be absent",
        )
        _need(
            receipt.get("ccl_transaction") is None,
            "non-material: CCL transaction must be absent",
        )
        adr = receipt.get("adr")
        wiki = receipt.get("wiki_sync")
        _need(
            adr == {"disposition": "NOT-APPLICABLE"},
            "non-material: ADR disposition must be NOT-APPLICABLE",
        )
        _need(
            wiki == {"disposition": "NOT-APPLICABLE"},
            "non-material: wiki-sync disposition must be NOT-APPLICABLE",
        )
        lines.extend(["ADR: NOT-APPLICABLE", "Wiki sync: NOT-APPLICABLE"])

    digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    lines.append(f"Closure receipt SHA-256: {digest}")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        print(validate_closure(args.repo_root, args.receipt))
        return 0
    except (
        ClosureError,
        json.JSONDecodeError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"WAYFINDER DECISION CLOSURE: INVALID\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
