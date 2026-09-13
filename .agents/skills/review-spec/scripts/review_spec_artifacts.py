#!/usr/bin/env python3
"""Hardened receipt boundary for the Polaris ``$review-spec`` artifacts."""

from __future__ import annotations

import html
import importlib.util
import sys
from pathlib import Path
from typing import Any

BASE_PATH = Path(__file__).with_name("review_spec_artifacts_base.py")
RECEIPT_FORMAT_V2 = "manifest-table-v2"


def _load_base() -> Any:
    spec = importlib.util.spec_from_file_location("_polaris_review_spec_artifacts_base", BASE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("review-spec base artifact utility could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_base = _load_base()
ArtifactError = _base.ArtifactError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def _optional_field(lines: list[str], label: str) -> str | None:
    prefix = f"**{label}:** "
    matches = [line[len(prefix) :] for line in lines if line.startswith(prefix)]
    _require(len(matches) <= 1, f"receipt must contain at most one {label} field")
    return matches[0].strip() if matches else None


def _split_table_row_v2(line: str) -> list[str]:
    text = line.strip()
    _require(text.startswith("|") and text.endswith("|"), "invalid manifest table row")
    return [
        html.unescape(cell.strip().replace("<br>", "\n"))
        for cell in text[1:-1].split("|")
    ]


def _manifest(lines: list[str]) -> list[dict[str, str]]:
    format_version = _optional_field(lines, "Receipt format")
    if format_version is None:
        splitter = _base._split_table_row
    else:
        _require(
            format_version == RECEIPT_FORMAT_V2,
            f"unsupported receipt format: {format_version}",
        )
        splitter = _split_table_row_v2

    section = _base._section(lines, "### Spec Contract Manifest")
    rows = [line for line in section if line.startswith("|")]
    _require(len(rows) >= 3, "verification receipt manifest is empty")
    _require(
        splitter(rows[0]) == ["Cell", "Source", "Requirement"],
        "invalid manifest header",
    )

    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows[2:]:
        cells = splitter(row)
        _require(len(cells) == 3, "manifest row must have three columns")
        cell, source, requirement = cells
        _require(bool(_base.CELL_RE.fullmatch(cell)), f"invalid manifest cell {cell}")
        _require(cell not in seen, f"duplicate manifest cell {cell}")
        _require(
            bool(source) and bool(requirement),
            f"manifest cell {cell} is incomplete",
        )
        seen.add(cell)
        result.append({"cell": cell, "source": source, "requirement": requirement})
    _require(bool(result), "verification receipt manifest is empty")
    return result


def parse_verification_manifest(receipt_body: str) -> list[dict[str, str]]:
    lines = receipt_body.splitlines()
    _require(_base.VERIFY_HEADER in lines, "receipt is not a Spec Verification Receipt")
    return _manifest(lines)


# The preserved checkpoint function resolves its manifest through the base module's
# global name, so replace only that deterministic boundary.
_base._manifest = _manifest


def self_test() -> None:
    _base.self_test() if hasattr(_base, "self_test") else None

    legacy = "\n".join(
        [
            _base.VERIFY_HEADER,
            "",
            "### Spec Contract Manifest",
            "| Cell | Source | Requirement |",
            "| --- | --- | --- |",
            r"| ID-7 | Implementation Decisions 7 | NO_CANDIDATES \| EXPLICIT_CREATE_NEW |",
        ]
    )
    assert (
        parse_verification_manifest(legacy)[0]["requirement"]
        == "NO_CANDIDATES | EXPLICIT_CREATE_NEW"
    )

    v2 = "\n".join(
        [
            _base.VERIFY_HEADER,
            f"**Receipt format:** {RECEIPT_FORMAT_V2}",
            "",
            "### Spec Contract Manifest",
            "| Cell | Source | Requirement |",
            "| --- | --- | --- |",
            (
                "| ID-7 | Implementation Decisions &#124; 7 | "
                "NO_CANDIDATES &#124; EXPLICIT_CREATE_NEW \\ literal"
                "<br>line two &lt;br&gt; &amp; markup |"
            ),
        ]
    )
    parsed = parse_verification_manifest(v2)[0]
    assert parsed["source"] == "Implementation Decisions | 7"
    assert (
        parsed["requirement"]
        == "NO_CANDIDATES | EXPLICIT_CREATE_NEW \\ literal\nline two <br> & markup"
    )

    malformed = legacy.replace(r"\|", r"\\|")
    try:
        parse_verification_manifest(malformed)
    except ArtifactError:
        pass
    else:
        raise AssertionError("double-escaped legacy manifest row was accepted")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "self-test":
        try:
            self_test()
        except (AssertionError, ArtifactError, RuntimeError) as exc:
            print(f"REVIEW-SPEC ARTIFACT ERROR: {exc}", file=sys.stderr)
            return 1
        print("REVIEW-SPEC ARTIFACT SELF-TEST: PASS")
        return 0
    return _base.main()


if __name__ == "__main__":
    raise SystemExit(main())
