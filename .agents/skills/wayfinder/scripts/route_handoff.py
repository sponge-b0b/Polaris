from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CHECKPOINT = "$wayfinder route clarity"
CONTINUATION_MARKER = "<!-- continuation-reconciliation:v1 -->"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
FINDING = re.compile(r"(?ms)^(\d+)\.\s+.+?(?=^\d+\.\s+|\Z)")
FIELD_PATTERNS = {
    "Observation": re.compile(r"(?m)^\s*Observation:\s*(.+?)\s*$"),
    "Why it matters": re.compile(r"(?m)^\s*Why it matters:\s*(.+?)\s*$"),
    "Authority": re.compile(r"(?m)^\s*Authority:\s*(.+?)\s*$"),
    "Recommendation/routing": re.compile(r"(?m)^\s*Recommendation/routing:\s*(.+?)\s*$"),
    "Blocking basis": re.compile(r"(?m)^\s*Blocking basis:\s*(.+?)\s*$"),
}
CONTINUATION_FIELD = {
    "Status": re.compile(r"(?m)^\*\*Status:\*\*\s*(.+?)\s*$"),
    "Canonical authority": re.compile(r"(?m)^\*\*Canonical authority:\*\*\s*(.+?)\s*$"),
    "Continuation branch": re.compile(r"(?m)^\*\*Continuation branch:\*\*\s*(.+?)\s*$"),
    "Conflict paths": re.compile(r"(?m)^\*\*Conflict paths:\*\*\s*(.+?)\s*$"),
    "Reconciliation owner": re.compile(r"(?m)^\*\*Reconciliation owner:\*\*\s*(.+?)\s*$"),
}


class HandoffError(RuntimeError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise HandoffError(message)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _need(isinstance(value, dict), "map snapshot: expected JSON object")
    return value


def _validate_attention(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").strip()
    lines = raw.splitlines()
    _need(lines, "attention: empty result")

    if lines[0] == "ATTENTION: CLEAR":
        _need(
            lines == [
                "ATTENTION: CLEAR",
                f"Checkpoint: {CHECKPOINT}",
                "Material concerns: 0",
            ],
            "attention: CLEAR result must use the exact three-line Route Clarity form",
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    _need(lines[0] == "ATTENTION: FINDINGS", "attention: invalid result header")
    _need(
        len(lines) >= 4 and lines[1] == f"Checkpoint: {CHECKPOINT}",
        "attention: wrong or missing Route Clarity checkpoint",
    )
    findings_text = "\n".join(lines[2:]).strip()
    findings = list(FINDING.finditer(findings_text))
    _need(findings, "attention: FINDINGS result has no findings")

    for finding in findings:
        block = finding.group(0)
        values: dict[str, str] = {}
        for name, pattern in FIELD_PATTERNS.items():
            match = pattern.search(block)
            _need(match is not None, f"attention: finding missing {name}")
            values[name] = match.group(1).strip()
        _need(
            values["Blocking basis"].lower() == "none",
            f"attention: blocking finding prevents specification handoff: {values['Blocking basis']}",
        )

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _continuation(body: str) -> dict[str, str] | None:
    count = body.count(CONTINUATION_MARKER)
    _need(count <= 1, "map: multiple continuation-reconciliation blocks")
    if count == 0:
        return None

    block = body.split(CONTINUATION_MARKER, 1)[1]
    block = re.sub(
        r"^\s*## Continuation Reconciliation\s*\n", "", block, count=1
    )
    block = re.split(r"(?m)^##\s+", block, maxsplit=1)[0]
    values: dict[str, str] = {}
    for name, pattern in CONTINUATION_FIELD.items():
        match = pattern.search(block)
        _need(match is not None, f"map: continuation block missing {name}")
        values[name] = match.group(1).strip()

    status = values["Status"]
    _need(
        status in {"required", "synchronized", "not-applicable"},
        f"map: unsupported continuation status {status!r}",
    )

    if status == "required":
        _need(
            FULL_SHA.fullmatch(values["Canonical authority"]) is not None,
            "map: required continuation needs full canonical authority SHA",
        )
        _need(
            values["Continuation branch"] not in {"", "None"},
            "map: required continuation needs a branch",
        )
        _need(
            values["Conflict paths"] not in {"", "None"},
            "map: required continuation needs exact conflict paths",
        )
        _need(
            values["Reconciliation owner"] == "$to-specs",
            "map: required continuation must name $to-specs",
        )

    return values


def specification_handoff(map_json: Path, attention_result: Path) -> str:
    snapshot = _read_json(map_json)
    title = snapshot.get("title")
    url = snapshot.get("url")
    body = snapshot.get("body")
    _need(isinstance(title, str) and title.strip(), "map snapshot: missing title")
    _need(
        isinstance(url, str)
        and re.fullmatch(r"https://github\.com/[^/\s]+/[^/\s]+/issues/\d+", url),
        "map snapshot: invalid issue URL",
    )
    _need(isinstance(body, str), "map snapshot: missing body")
    _need("## Route Clarity" in body, "map: missing Route Clarity section")

    attention_hash = _validate_attention(attention_result)
    continuation = _continuation(body)

    lines = [
        "WAYFINDER HANDOFF: SPECIFICATION",
        f"$to-specs - {title.strip()} ({url})",
    ]
    if continuation and continuation["Status"] == "required":
        lines.extend(
            [
                f"Canonical authority: {continuation['Canonical authority']}",
                f"Continuation branch: {continuation['Continuation branch']}",
                f"Conflict paths: {continuation['Conflict paths']}",
            ]
        )
    lines.append(f"Route Clarity Attention SHA-256: {attention_hash}")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    specification = sub.add_parser("specification")
    specification.add_argument("--map-json", type=Path, required=True)
    specification.add_argument("--attention-result", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "specification":
            print(specification_handoff(args.map_json, args.attention_result))
            return 0
        raise HandoffError(f"unsupported command: {args.command}")
    except (HandoffError, json.JSONDecodeError, OSError) as exc:
        print(f"WAYFINDER HANDOFF: INVALID\nReason: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
