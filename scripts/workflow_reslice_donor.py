from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

from scripts.workflow_reslice_recovery import RecoveryError, RecoveryRecord, parse_record


class DonorValidationError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise DonorValidationError(message)


def _git(donor: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(donor), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    )
    if result.returncode:
        stderr = result.stderr if text else result.stderr.decode("utf-8", "replace")
        raise DonorValidationError(
            f"git {' '.join(args)} failed for protected donor: {stderr.strip()}"
        )
    return result.stdout


def _git_paths(donor: Path, *args: str) -> set[bytes]:
    output = _git(donor, *args, text=False)
    assert isinstance(output, bytes)
    return {item for item in output.split(b"\0") if item}


def _candidate_paths(donor: Path, anchor: str) -> list[bytes]:
    tracked = _git_paths(
        donor,
        "diff",
        "--no-renames",
        "--name-only",
        "-z",
        anchor,
        "--",
    )
    untracked = _git_paths(donor, "ls-files", "--others", "--exclude-standard", "-z")
    return sorted(tracked | untracked)


def _path_mode(path: Path) -> bytes:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode):
        return b"120000"
    if info.st_mode & stat.S_IXUSR:
        return b"100755"
    return b"100644"


def _path_bytes(path: Path) -> bytes:
    if path.is_symlink():
        return os.fsencode(os.readlink(path))
    return path.read_bytes()


def live_candidate_state(donor: Path, anchor: str) -> str:
    payload = bytearray()
    for raw_path in _candidate_paths(donor, anchor):
        payload.extend(b"path\0")
        payload.extend(raw_path)
        payload.extend(b"\0")
        path = donor / os.fsdecode(raw_path)
        try:
            mode = _path_mode(path)
        except FileNotFoundError:
            payload.extend(b"state\0DELETED\0")
            continue
        payload.extend(b"mode\0")
        payload.extend(mode)
        payload.extend(b"\0sha256\0")
        payload.extend(hashlib.sha256(_path_bytes(path)).hexdigest().encode("ascii"))
        payload.extend(b"\0")
    return hashlib.sha256(bytes(payload)).hexdigest()


def _attention_receipt_path(donor: Path, source_ticket: int) -> Path:
    value = str(
        _git(
            donor,
            "rev-parse",
            "--git-path",
            f"polaris/implement-ticket-attention/ticket-{source_ticket}.json",
        )
    ).strip()
    path = Path(value)
    return path if path.is_absolute() else donor / path


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise DonorValidationError(
            f"protected donor Attention receipt is unavailable: {path}"
        ) from exc


def _canonical_attention_receipt_hash(path: Path) -> str:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DonorValidationError(
            f"protected donor Attention receipt is not valid JSON: {path}"
        ) from exc
    _need(
        isinstance(value, dict),
        f"protected donor Attention receipt must contain a JSON object: {path}",
    )
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_attention_receipt(record: RecoveryRecord, donor: Path) -> str:
    receipt_path = _attention_receipt_path(donor, record.source_ticket)
    if not receipt_path.is_file():
        # The Attention receipt lives under per-worktree Git metadata, not in the
        # candidate tree. Recovery records durably preserve its identity because
        # worktree reconstruction may legitimately lose that ephemeral file.
        return record.attention_receipt_hash

    raw_hash = _sha256_file(receipt_path)
    if raw_hash == record.attention_receipt_hash:
        return raw_hash

    canonical_hash = _canonical_attention_receipt_hash(receipt_path)
    _need(
        canonical_hash == record.attention_receipt_hash,
        "protected donor Attention receipt mismatch: "
        f"expected {record.attention_receipt_hash}, "
        f"observed file SHA-256 {raw_hash}, "
        f"canonical receipt hash {canonical_hash}",
    )
    return canonical_hash


def validate_live_donor(record: RecoveryRecord) -> tuple[str, str, str, str]:
    donor = Path(record.donor_checkout)
    _need(donor.is_dir(), f"protected donor checkout is missing: {donor}")

    branch = str(_git(donor, "branch", "--show-current")).strip()
    _need(
        branch == record.source_branch,
        "protected donor branch mismatch: "
        f"expected {record.source_branch}, observed {branch or '<detached>'}",
    )

    head = str(_git(donor, "rev-parse", "HEAD")).strip()
    _need(
        head == record.donor_head,
        f"protected donor HEAD mismatch: expected {record.donor_head}, observed {head}",
    )

    state = live_candidate_state(donor, record.donor_head)
    _need(
        state == record.candidate_state,
        "protected donor candidate state mismatch: "
        f"expected {record.candidate_state}, observed {state}",
    )

    receipt_hash = _validate_attention_receipt(record, donor)
    return branch, head, state, receipt_hash


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        text = Path(args.body).read_text(encoding="utf-8")
        record = parse_record(text)
        branch, head, state, receipt_hash = validate_live_donor(record)
    except (OSError, RecoveryError, DonorValidationError) as exc:
        print("TICKET RESLICE DONOR: INVALID")
        print(f"Reason: {exc}")
        return 1

    receipt_path = _attention_receipt_path(Path(record.donor_checkout), record.source_ticket)
    receipt_evidence = "live-file" if receipt_path.is_file() else "durable-record-only"

    print("TICKET RESLICE DONOR: VALID")
    print(f"Protected donor checkout: {record.donor_checkout}")
    print(f"Branch: {branch}")
    print(f"HEAD: {head}")
    print(f"Candidate state: {state}")
    print(f"Attention receipt hash: {receipt_hash}")
    print(f"Attention receipt evidence: {receipt_evidence}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--body", required=True)
    validate.set_defaults(func=_cmd_validate)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
