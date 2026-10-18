from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

from scripts.workflow_attention import AttentionProtocolError, validate_file

SCHEMA = "polaris.implement-ticket-attention/v1"
POLICY_PREFIXES = (b".agents/skills/", b"docs/process/")
POLICY_FILES = {b"AGENTS.md"}
CONTRACT_HASH_FIELDS = {
    "polaris.ticket-contract/v1": "ticket_contract_hash",
    "polaris.review-remediation-contract/v1": "remediation_contract_hash",
}


class AttentionGateError(RuntimeError):
    pass


def _run_git(*args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    if result.returncode:
        stderr = result.stderr if text else result.stderr.decode("utf-8", "replace")
        raise AttentionGateError(f"git {' '.join(args)} failed: {stderr.strip()}")
    return result.stdout


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise AttentionGateError(message)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def receipt_hash(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _contract_identity(path: Path) -> tuple[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), "contract: expected object")
    schema = value.get("schema")
    _need(schema in CONTRACT_HASH_FIELDS, "contract: unsupported schema")
    assert isinstance(schema, str)
    digest = value.get(CONTRACT_HASH_FIELDS[schema])
    _need(
        isinstance(digest, str)
        and len(digest) == 64
        and all(ch in "0123456789abcdef" for ch in digest),
        "contract: invalid contract hash",
    )
    return schema, digest


def _current_branch() -> str:
    return str(_run_git("branch", "--show-current")).strip()


def _head() -> str:
    return str(_run_git("rev-parse", "HEAD")).strip()


def _verify_commit(commit: str) -> None:
    _run_git("rev-parse", "--verify", f"{commit}^{{commit}}")


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise AttentionGateError(result.stderr.strip())


def _git_paths(*args: str) -> set[bytes]:
    output = _run_git(*args, text=False)
    assert isinstance(output, bytes)
    return {item for item in output.split(b"\0") if item}


def _changed_paths(baseline: str) -> set[bytes]:
    return _git_paths("diff", "--no-renames", "--name-only", "-z", baseline, "--")


def _untracked_paths() -> set[bytes]:
    return _git_paths("ls-files", "--others", "--exclude-standard", "-z")


def _candidate_paths(baseline: str) -> list[bytes]:
    return sorted(_changed_paths(baseline) | _untracked_paths())


def _path_mode(path: bytes) -> bytes:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return b"120000"
    if info.st_mode & stat.S_IXUSR:
        return b"100755"
    return b"100644"


def _path_bytes(path: bytes) -> bytes:
    if os.path.islink(path):
        return os.fsencode(os.readlink(path))
    return Path(os.fsdecode(path)).read_bytes()


def candidate_state(baseline: str) -> str:
    payload = bytearray()
    for raw_path in _candidate_paths(baseline):
        payload.extend(b"path\0")
        payload.extend(raw_path)
        payload.extend(b"\0")
        try:
            mode = _path_mode(raw_path)
        except FileNotFoundError:
            payload.extend(b"state\0DELETED\0")
            continue
        payload.extend(b"mode\0")
        payload.extend(mode)
        payload.extend(b"\0sha256\0")
        payload.extend(hashlib.sha256(_path_bytes(raw_path)).hexdigest().encode("ascii"))
        payload.extend(b"\0")
    return hashlib.sha256(bytes(payload)).hexdigest()


def _is_policy_path(path: bytes) -> bool:
    return path in POLICY_FILES or any(path.startswith(prefix) for prefix in POLICY_PREFIXES)


def _worktree_clean() -> bool:
    return not _git_paths("status", "--porcelain", "-z")


def _blob_at(ref: str, path: bytes) -> bytes | None:
    decoded = os.fsdecode(path)
    result = subprocess.run(
        ["git", "show", f"{ref}:{decoded}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return result.stdout
    return None


def _policy_sync_admissible(baseline: str, head: str, default_ref: str) -> bool:
    _verify_commit(default_ref)
    if head == baseline:
        return True
    paths = _git_paths(
        "diff", "--no-renames", "--name-only", "-z", f"{baseline}..{head}", "--"
    )
    if not paths or any(not _is_policy_path(path) for path in paths):
        return False
    for path in paths:
        if _blob_at(head, path) != _blob_at(default_ref, path):
            return False
    return True


def _attention_result(path: Path, checkpoint: str) -> tuple[str, str]:
    try:
        receipt = validate_file(
            path,
            checkpoint=checkpoint,
            require_nonblocking=True,
        )
    except AttentionProtocolError as exc:
        raise AttentionGateError(str(exc)) from exc
    return receipt.status, receipt.result_sha256


def default_receipt_path(ticket: int) -> Path:
    raw = str(
        _run_git(
            "rev-parse",
            "--git-path",
            f"polaris/implement-ticket-attention/ticket-{ticket}.json",
        )
    ).strip()
    return Path(raw)


def _load_receipt(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), "attention receipt: expected object")
    _need(value.get("schema") == SCHEMA, "attention receipt: unsupported schema")
    return value


def _write_receipt(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(_canonical(value) + b"\n")
    tmp.replace(path)


def _common(
    *,
    ticket: int,
    contract: Path,
    baseline: str,
    branch: str,
) -> tuple[str, str, str]:
    _need(ticket > 0, "ticket: expected positive number")
    _verify_commit(baseline)
    current_branch = _current_branch()
    _need(
        current_branch == branch,
        f"branch mismatch: expected {branch}, got {current_branch}",
    )
    head = _head()
    _need(
        _is_ancestor(baseline, head),
        "baseline is not an ancestor of current HEAD",
    )
    schema, digest = _contract_identity(contract)
    return schema, digest, head


def record_pre_mutation(args: argparse.Namespace) -> dict[str, Any]:
    contract_schema, contract_hash, head = _common(
        ticket=args.ticket,
        contract=args.contract,
        baseline=args.baseline,
        branch=args.branch,
    )
    _need(_worktree_clean(), "pre-mutation gate requires a clean worktree")
    _need(
        _policy_sync_admissible(args.baseline, head, args.default_ref),
        "pre-mutation delta is not an admissible default-branch workflow-policy synchronization",
    )
    attention_status, attention_hash = _attention_result(
        args.attention_result,
        "$implement-ticket pre-mutation",
    )
    receipt = {
        "schema": SCHEMA,
        "ticket": args.ticket,
        "branch": args.branch,
        "baseline": args.baseline,
        "contract_schema": contract_schema,
        "contract_hash": contract_hash,
        "pre_mutation": {
            "head": head,
            "candidate_state": candidate_state(args.baseline),
            "attention_status": attention_status,
            "attention_result_sha256": attention_hash,
        },
        "pre_closure": None,
    }
    _write_receipt(args.receipt, receipt)
    return receipt


def _require_identity(
    receipt: dict[str, Any],
    *,
    ticket: int,
    branch: str,
    baseline: str,
    contract_schema: str,
    contract_hash: str,
) -> None:
    _need(receipt.get("ticket") == ticket, "attention receipt: ticket mismatch")
    _need(receipt.get("branch") == branch, "attention receipt: branch mismatch")
    _need(receipt.get("baseline") == baseline, "attention receipt: baseline mismatch")
    _need(
        receipt.get("contract_schema") == contract_schema,
        "attention receipt: contract schema mismatch",
    )
    _need(
        receipt.get("contract_hash") == contract_hash,
        "attention receipt: contract hash mismatch",
    )
    _need(
        isinstance(receipt.get("pre_mutation"), dict),
        "attention receipt: missing pre-mutation gate",
    )


def record_pre_closure(args: argparse.Namespace) -> dict[str, Any]:
    contract_schema, contract_hash, head = _common(
        ticket=args.ticket,
        contract=args.contract,
        baseline=args.baseline,
        branch=args.branch,
    )
    receipt = _load_receipt(args.receipt)
    _require_identity(
        receipt,
        ticket=args.ticket,
        branch=args.branch,
        baseline=args.baseline,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
    )
    _need(
        receipt["pre_mutation"].get("head") == head,
        "attention receipt: HEAD changed after pre-mutation gate",
    )
    attention_status, attention_hash = _attention_result(
        args.attention_result,
        "$implement-ticket pre-closure",
    )
    receipt["pre_closure"] = {
        "head": head,
        "candidate_state": candidate_state(args.baseline),
        "attention_status": attention_status,
        "attention_result_sha256": attention_hash,
    }
    _write_receipt(args.receipt, receipt)
    return receipt


def verify(args: argparse.Namespace) -> dict[str, Any]:
    contract_schema, contract_hash, _ = _common(
        ticket=args.ticket,
        contract=args.contract,
        baseline=args.baseline,
        branch=args.branch,
    )
    receipt = _load_receipt(args.receipt)
    _require_identity(
        receipt,
        ticket=args.ticket,
        branch=args.branch,
        baseline=args.baseline,
        contract_schema=contract_schema,
        contract_hash=contract_hash,
    )
    _need(
        receipt["pre_mutation"].get("head") == _head(),
        "attention receipt: HEAD changed after pre-mutation gate",
    )
    pre_closure = receipt.get("pre_closure")
    _need(
        isinstance(pre_closure, dict),
        "attention receipt: missing pre-closure gate",
    )
    current_state = candidate_state(args.baseline)
    _need(
        pre_closure.get("candidate_state") == current_state,
        "attention receipt: pre-closure candidate state is stale",
    )
    actual_hash = receipt_hash(receipt)
    _need(
        actual_hash == args.expected_receipt_hash,
        "attention receipt: hash mismatch",
    )
    return receipt


def _print(status: str, receipt: dict[str, Any]) -> None:
    print(status)
    print(f"Ticket: #{receipt['ticket']}")
    print(f"Contract Schema: {receipt['contract_schema']}")
    print(f"Contract Hash: {receipt['contract_hash']}")
    print(f"Attention Receipt Hash: {receipt_hash(receipt)}")
    if isinstance(receipt.get("pre_closure"), dict):
        print(f"Candidate state: {receipt['pre_closure']['candidate_state']}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("pre-mutation", "pre-closure", "verify"):
        item = sub.add_parser(name)
        item.add_argument("--ticket", type=int, required=True)
        item.add_argument("--contract", type=Path, required=True)
        item.add_argument("--baseline", required=True)
        item.add_argument("--branch", required=True)
        item.add_argument("--receipt", type=Path)
        if name in {"pre-mutation", "pre-closure"}:
            item.add_argument("--attention-result", type=Path, required=True)
        if name == "pre-mutation":
            item.add_argument("--default-ref", default="origin/main")
        if name == "verify":
            item.add_argument("--expected-receipt-hash", required=True)
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if args.receipt is None:
        args.receipt = default_receipt_path(args.ticket)
    try:
        if args.command == "pre-mutation":
            receipt = record_pre_mutation(args)
            _print("IMPLEMENT TICKET ATTENTION: PRE-MUTATION VALID", receipt)
        elif args.command == "pre-closure":
            receipt = record_pre_closure(args)
            _print("IMPLEMENT TICKET ATTENTION: PRE-CLOSURE VALID", receipt)
        else:
            receipt = verify(args)
            _print("IMPLEMENT TICKET ATTENTION: VALID", receipt)
    except (AttentionGateError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
