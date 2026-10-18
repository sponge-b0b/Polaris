from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

CLEAR_HEADER = "ATTENTION: CLEAR"
FINDINGS_HEADER = "ATTENTION: FINDINGS"
VALID_HEADERS = frozenset({CLEAR_HEADER, FINDINGS_HEADER})
FINDING = re.compile(r"(?ms)^(\d+)\.\s+.+?(?=^\d+\.\s+|\Z)")
FIELD_PATTERNS = {
    "Observation": re.compile(r"(?m)^\s*Observation:\s*(.+?)\s*$"),
    "Why it matters": re.compile(r"(?m)^\s*Why it matters:\s*(.+?)\s*$"),
    "Authority": re.compile(r"(?m)^\s*Authority:\s*(.+?)\s*$"),
    "Recommendation/routing": re.compile(r"(?m)^\s*Recommendation/routing:\s*(.+?)\s*$"),
    "Blocking basis": re.compile(r"(?m)^\s*Blocking basis:\s*(.+?)\s*$"),
}


class AttentionProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class AttentionReceipt:
    checkpoint: str
    status: str
    result_sha256: str
    finding_count: int


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise AttentionProtocolError(message)


def validate_text(
    text: str,
    *,
    checkpoint: str,
    require_nonblocking: bool = False,
) -> AttentionReceipt:
    raw = text.strip()
    lines = raw.splitlines()
    _need(lines, "attention result: empty result")
    _need(lines[0] in VALID_HEADERS, "attention result: unsupported formal result header")

    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    if lines[0] == CLEAR_HEADER:
        _need(
            lines == [
                CLEAR_HEADER,
                f"Checkpoint: {checkpoint}",
                "Material concerns: 0",
            ],
            f"attention result: expected formal receipt for {checkpoint}; CLEAR must use the exact three-line form",
        )
        return AttentionReceipt(
            checkpoint=checkpoint,
            status="clear",
            result_sha256=digest,
            finding_count=0,
        )

    _need(
        len(lines) >= 4 and lines[1] == f"Checkpoint: {checkpoint}",
        f"attention result: expected formal FINDINGS receipt for {checkpoint}",
    )
    findings_text = "\n".join(lines[2:]).strip()
    findings = list(FINDING.finditer(findings_text))
    _need(findings, "attention result: FINDINGS receipt has no finding rows")

    blocking_bases: list[str] = []
    for finding in findings:
        block = finding.group(0)
        blocking_match = FIELD_PATTERNS["Blocking basis"].search(block)
        if blocking_match is not None:
            blocking_bases.append(blocking_match.group(1).strip())

    blocking = [value for value in blocking_bases if value.lower() != "none"]
    if require_nonblocking and blocking:
        raise AttentionProtocolError(
            "attention result: unresolved blocking finding(s): " + "; ".join(blocking)
        )

    for finding in findings:
        block = finding.group(0)
        for name, pattern in FIELD_PATTERNS.items():
            match = pattern.search(block)
            _need(match is not None, f"attention result: finding missing {name}")
            value = match.group(1).strip()
            _need(value != "", f"attention result: finding has empty {name}")

    return AttentionReceipt(
        checkpoint=checkpoint,
        status="findings-nonblocking" if not blocking else "findings-blocking",
        result_sha256=digest,
        finding_count=len(findings),
    )


def validate_file(
    path: Path,
    *,
    checkpoint: str,
    require_nonblocking: bool = False,
) -> AttentionReceipt:
    return validate_text(
        path.read_text(encoding="utf-8"),
        checkpoint=checkpoint,
        require_nonblocking=require_nonblocking,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--result", type=Path, required=True)
    validate.add_argument("--checkpoint", required=True)
    validate.add_argument("--require-nonblocking", action="store_true")
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        if args.command != "validate":
            raise AttentionProtocolError(f"unsupported command: {args.command}")
        receipt = validate_file(
            args.result,
            checkpoint=args.checkpoint,
            require_nonblocking=args.require_nonblocking,
        )
    except (AttentionProtocolError, OSError) as exc:
        parser.error(str(exc))

    print("ATTENTION PROTOCOL: VALID")
    print(f"Checkpoint: {receipt.checkpoint}")
    print(f"Status: {receipt.status}")
    print(f"Finding count: {receipt.finding_count}")
    print(f"Attention Result SHA-256: {receipt.result_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
