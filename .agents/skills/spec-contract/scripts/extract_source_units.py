from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

_LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?:[-+*]|\d+[.)])[ \t]+")
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(?P<title>.+?)[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(?P<fence>\x60{3,}|~{3,})")
_TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
_PROVENANCE_COMMENT_RE = re.compile(
    r"^\s*<!--\s*(?:"
    r"wayfinder-source|wayfinder-remediation|architecture-blocker|"
    r"decomposition-defects|ticket-coverage-manifest|spec-contract|"
    r"workflow:|project-delivery:"
    r")\b.*?-->\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip(" \t") for line in value.split("\n")).rstrip("\n")


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return bool(cells) and all(
        _TABLE_SEPARATOR_CELL_RE.fullmatch(cell) for cell in cells
    )


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return "|" in stripped and not _is_table_separator(line)


def _starts_special_block(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or bool(_HEADING_RE.match(line))
        or bool(_FENCE_RE.match(line))
        or bool(_LIST_RE.match(line))
        or stripped.startswith(">")
        or _is_table_row(line)
        or stripped.startswith("<!--")
    )


def _append_unit(
    units: list[dict[str, Any]],
    *,
    section: str,
    kind: str,
    ordinal: int,
    text: str,
) -> None:
    normalized = _normalize_text(text)
    if not normalized:
        return
    units.append(
        {
            "source_unit": f"SU-{len(units) + 1:04d}",
            "section": section,
            "kind": kind,
            "ordinal": ordinal,
            "text": normalized,
            "text_hash": _sha256_text(normalized),
        }
    )


def extract_source_units(body: str) -> list[dict[str, Any]]:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    units: list[dict[str, Any]] = []
    section = "<preamble>"
    section_ordinals: dict[tuple[str, str], int] = {}
    i = 0

    def next_ordinal(kind: str) -> int:
        key = (section, kind)
        section_ordinals[key] = section_ordinals.get(key, 0) + 1
        return section_ordinals[key]

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            section = heading.group("title").strip()
            i += 1
            continue

        fence = _FENCE_RE.match(line)
        if fence:
            opening = fence.group("fence")
            fence_char = opening[0]
            fence_len = len(opening)
            block = [line]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                candidate = lines[i].lstrip()
                if candidate.startswith(fence_char * fence_len):
                    i += 1
                    break
                i += 1
            _append_unit(
                units,
                section=section,
                kind="code-block",
                ordinal=next_ordinal("code-block"),
                text="\n".join(block),
            )
            continue

        if stripped.startswith("<!--"):
            block = [line]
            i += 1
            while "-->" not in "\n".join(block) and i < len(lines):
                block.append(lines[i])
                i += 1
            text = "\n".join(block)
            if not _PROVENANCE_COMMENT_RE.match(text):
                _append_unit(
                    units,
                    section=section,
                    kind="html-block",
                    ordinal=next_ordinal("html-block"),
                    text=text,
                )
            continue

        if stripped.startswith(">"):
            block = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i])
                i += 1
            _append_unit(
                units,
                section=section,
                kind="blockquote",
                ordinal=next_ordinal("blockquote"),
                text="\n".join(block),
            )
            continue

        # A Markdown list marker owns the source-unit kind even when the item text
        # contains a pipe character. Check list structure before table-row syntax so
        # values such as `REVISE | RETRACT` remain numbered/bulleted list items.
        if _LIST_RE.match(line):
            block = [line]
            base_indent = len(line) - len(line.lstrip(" \t"))
            i += 1
            while i < len(lines):
                candidate = lines[i]
                if (
                    not candidate.strip()
                    or _HEADING_RE.match(candidate)
                    or _FENCE_RE.match(candidate)
                    or _LIST_RE.match(candidate)
                ):
                    break
                indent = len(candidate) - len(candidate.lstrip(" \t"))
                if indent <= base_indent and _starts_special_block(candidate):
                    break
                if candidate.strip().startswith(">") or _is_table_row(candidate):
                    break
                block.append(candidate)
                i += 1
            _append_unit(
                units,
                section=section,
                kind="list-item",
                ordinal=next_ordinal("list-item"),
                text="\n".join(block),
            )
            continue

        if _is_table_separator(line):
            i += 1
            continue

        if _is_table_row(line):
            _append_unit(
                units,
                section=section,
                kind="table-row",
                ordinal=next_ordinal("table-row"),
                text=line,
            )
            i += 1
            continue

        block = [line]
        i += 1
        while i < len(lines):
            candidate = lines[i]
            if _starts_special_block(candidate):
                break
            block.append(candidate)
            i += 1
        _append_unit(
            units,
            section=section,
            kind="paragraph",
            ordinal=next_ordinal("paragraph"),
            text="\n".join(block),
        )

    return units


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract deterministic Spec source units and hashes from a "
            "gh issue JSON snapshot."
        )
    )
    parser.add_argument("--issue-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    payload = json.loads(args.issue_json.read_text(encoding="utf-8"))
    body = payload.get("body")
    if not isinstance(body, str):
        raise SystemExit("issue JSON must contain a string 'body' field")

    result = {
        "spec_body_hash": _sha256_text(body),
        "source_units": extract_source_units(body),
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
