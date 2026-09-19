#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 280
BASELINE = "23f7a2df40557b87754fd62e3f70164f60b18788"
BRANCH = "spec-280"
HEAD = "10d4227b1011c6dbd32ff9864374acf2cbda65ff"

RANK = {"US": 0, "ID": 1, "TD": 2, "OOS": 3, "NORM": 4}
CELL_RE = re.compile(r"^(US|ID|TD|OOS|NORM)-(\d+)(?:\.(.+))?$")

NONCANONICAL: dict[str, tuple[str, list[str] | None, str]] = {
    "SU-0001": (
        "normative-represented",
        [
            "US-1",
            "US-3",
            "US-7",
            "US-8",
            "US-18",
            "US-24",
            "US-26",
            "US-30",
            "US-32",
            "US-35",
            "US-36",
            "US-37",
            "US-38",
            "US-39",
            "US-42",
            "ID-28",
            "TD-32",
        ],
        "The Problem Statement summarizes durability, retry/concurrency/correction, "
        "historical reconstruction, and inward technology-neutrality obligations "
        "that are established concretely by the mapped canonical cells.",
    ),
    "SU-0002": (
        "normative-represented",
        [
            "US-2",
            "US-3",
            "US-6",
            "US-7",
            "US-9",
            "US-14",
            "US-15",
            "US-16",
            "US-17",
            "US-18",
            "US-19",
            "US-20",
            "US-21",
            "US-22",
            "US-24",
            "US-25",
            "US-26",
            "US-30",
            "US-32",
            "US-35",
            "US-36",
            "US-37",
            "US-38",
            "US-39",
            "US-42",
            "US-43",
        ],
        "The detailed Problem Statement requirement list is fully decomposed by "
        "the mapped cardinality, atomicity, retry/concurrency, relationship, "
        "dual-time, contested-state, migration, and inward-boundary cells.",
    ),
    "SU-0003": (
        "normative-represented",
        ["ID-1"],
        "The Solution's adapter directive is the same purpose-specific Decisions "
        "command-store and Decision Memory reader adapter obligation in ID-1.",
    ),
    "SU-0004": (
        "normative-represented",
        ["US-42", "US-43", "ID-2", "ID-21", "ID-22", "ID-28"],
        "The greenfield schema, continuity mechanism, PostgreSQL-internal-use, "
        "and technology-neutral-boundary requirements are fully represented by "
        "the mapped cells.",
    ),
    "SU-0005": (
        "normative-represented",
        [
            "US-8",
            "US-21",
            "US-22",
            "US-23",
            "US-24",
            "US-36",
            "US-37",
            "ID-17",
            "ID-18",
            "ID-19",
            "ID-23",
            "ID-24",
            "ID-25",
            "ID-28",
            "ID-33",
        ],
        "Transactional atomicity, restart-safe history/query behavior, and "
        "permitted PostgreSQL implementation techniques are represented by the "
        "mapped atomicity, reconstruction, idempotency, dual-time, and "
        "infrastructure-only implementation cells.",
    ),
    "SU-0006": (
        "non-normative",
        None,
        "Implementation-readiness status; it does not add an acceptance obligation.",
    ),
    "SU-0007": (
        "normative-new",
        ["NORM-1"],
        "Establishes the synchronized design-authority consumption constraint.",
    ),
    "SU-0008": (
        "normative-represented",
        ["NORM-1"],
        "Enumerates one authority input required by NORM-1.",
    ),
    "SU-0009": (
        "normative-represented",
        ["NORM-1"],
        "Enumerates one authority input required by NORM-1.",
    ),
    "SU-0010": (
        "normative-represented",
        ["NORM-1"],
        "Enumerates one authority input required by NORM-1.",
    ),
    "SU-0011": (
        "normative-represented",
        ["NORM-1"],
        "Enumerates the synchronized design inputs required by NORM-1.",
    ),
    "SU-0012": (
        "normative-new",
        ["NORM-2"],
        "Establishes the workflow-owned fixed-baseline publication requirement "
        "and its readiness disposition.",
    ),
    "SU-0063": (
        "non-normative",
        None,
        "Architecture-impact entity inventory; descriptive scope metadata.",
    ),
    "SU-0064": (
        "non-normative",
        None,
        "Architecture-impact classification; descriptive metadata.",
    ),
    "SU-0065": (
        "normative-represented",
        ["US-1", "US-6", "US-7", "US-8", "US-42", "US-43", "ID-28", "OOS-10", "NORM-1"],
        "The governing-constraints summary is fully represented by the mapped "
        "durability/history, inward-boundary, greenfield-migration, no-universal-"
        "event-sourcing, and synchronized-authority cells.",
    ),
    "SU-0066": (
        "non-normative",
        None,
        "Records already-resolved architecture authority; it does not add a new Spec obligation.",
    ),
    "SU-0067": (
        "non-normative",
        None,
        "Reports architecture-question status only.",
    ),
    "SU-0068": (
        "non-normative",
        None,
        "Reports material-design-question status only.",
    ),
    "SU-0069": (
        "non-normative",
        None,
        "Reports implementation-readiness status only.",
    ),
    "SU-0149": (
        "normative-new",
        ["NORM-3"],
        "Establishes the canonical native dependency record and required satisfied dependency state.",
    ),
    "SU-0150": (
        "non-normative",
        None,
        "Historical planning-source provenance; it does not add an acceptance obligation.",
    ),
    "SU-0151": (
        "normative-represented",
        ["NORM-1"],
        "Restates the synchronized authority set represented by NORM-1.",
    ),
    "SU-0152": (
        "normative-represented",
        ["US-42", "ID-28"],
        "Restates PostgreSQL's infrastructure-only role behind inward-owned contracts.",
    ),
    "SU-0153": (
        "normative-represented",
        ["US-50", "ID-31"],
        "Restates the donor-only legacy-mechanics constraint in US-50 and ID-31.",
    ),
}

NORM_MANIFEST = {
    "NORM-1": {
        "source": "Implementation readiness paragraph 2",
        "requirement": (
            "Implementation must consume, not reinterpret, current #278, completed "
            "and synchronized #279, the R2 foundation public contract, and the "
            "synchronized lifecycle, relationship, application, and durable-"
            "persistence designs."
        ),
    },
    "NORM-2": {
        "source": "Implementation readiness paragraph 3",
        "requirement": (
            "$to-tickets must own first-use creation of spec-280 and record the "
            "fixed Spec baseline before ticket publication; absence of that baseline "
            "before $to-tickets is not an implementation-readiness blocker."
        ),
    },
    "NORM-3": {
        "source": "Dependency context paragraph 1",
        "requirement": (
            "The native GitHub dependency on #279 is the canonical dependency record "
            "and must be satisfied for this Spec."
        ),
    },
}


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def normalize(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(part.rstrip() for part in value.split("\n")).rstrip()


def build_source_units(body: str) -> list[dict[str, str]]:
    lines = body.splitlines()
    units: list[dict[str, str]] = []
    section = "(preamble)"
    paragraph: list[str] = []
    kind_counts: dict[tuple[str, str], int] = {}
    oos_counter = 0

    def source_identity(kind: str, text: str) -> str:
        nonlocal oos_counter
        numbered = re.match(r"^\s*(\d+)\.\s+", text)
        if (
            section in {"User Stories", "Implementation Decisions", "Testing Decisions"}
            and numbered
        ):
            return f"{section} {int(numbered.group(1))}"
        if section == "Out of Scope" and kind == "list-item":
            oos_counter += 1
            return f"Out of Scope {oos_counter}"
        key = (section, kind)
        kind_counts[key] = kind_counts.get(key, 0) + 1
        return f"{section} {kind} {kind_counts[key]}"

    def add(kind: str, raw: str) -> None:
        text = normalize(raw)
        if not text:
            return
        units.append(
            {
                "source_unit": f"SU-{len(units) + 1:04d}",
                "source": source_identity(kind, text),
                "section": section,
                "kind": kind,
                "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "text": text,
            }
        )

    def flush() -> None:
        if paragraph:
            add("paragraph", "\n".join(paragraph))
            paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if re.match(r"^#{1,6}\s+", stripped):
            flush()
            section = re.sub(r"^#{1,6}\s+", "", stripped)
            i += 1
            continue

        if stripped.startswith("```"):
            flush()
            block = [line]
            i += 1
            while i < len(lines):
                block.append(lines[i])
                if lines[i].strip().startswith("```"):
                    i += 1
                    break
                i += 1
            add("code", "\n".join(block))
            continue

        if not stripped:
            flush()
            i += 1
            continue

        if stripped.startswith(">"):
            flush()
            block = [line]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i])
                i += 1
            add("blockquote", "\n".join(block))
            continue

        if re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+)", line):
            flush()
            item = [line]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if (
                    not nxt.strip()
                    or re.match(r"^\s*(?:[-*+]\s+|\d+\.\s+)", nxt)
                    or re.match(r"^#{1,6}\s+", nxt.strip())
                ):
                    break
                if nxt.startswith("  ") or nxt.startswith("\t"):
                    item.append(nxt)
                    i += 1
                    continue
                break
            add("list-item", "\n".join(item))
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            flush()
            if not re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
                add("table-row", line)
            i += 1
            continue

        if stripped.startswith("<") and stripped.endswith(">"):
            flush()
            add("html", line)
            i += 1
            continue

        paragraph.append(line)
        i += 1

    flush()
    return units


def cell_key(cell: str) -> tuple[int, int, int, str]:
    match = CELL_RE.fullmatch(cell)
    if not match or int(match.group(2)) <= 0:
        raise SystemExit(f"SPEC CONTRACT: INVALID\nReason: invalid cell {cell}")
    suffix = match.group(3)
    return (
        RANK[match.group(1)],
        int(match.group(2)),
        0 if suffix is None else 1,
        "" if suffix is None else suffix,
    )


def canonical_cell(unit: dict[str, str]) -> str | None:
    section = unit["section"]
    source = unit["source"]
    prefixes = {
        "User Stories": "US",
        "Implementation Decisions": "ID",
        "Testing Decisions": "TD",
        "Out of Scope": "OOS",
    }
    prefix = prefixes.get(section)
    if prefix is None:
        return None
    match = re.fullmatch(rf"{re.escape(section)} (\d+)", source)
    if not match:
        raise SystemExit(
            f"SPEC CONTRACT: INVALID\nReason: malformed canonical source {source}"
        )
    return f"{prefix}-{int(match.group(1))}"


def display_requirement(unit: dict[str, str]) -> str:
    text = unit["text"].strip()
    if unit["section"] == "Out of Scope":
        return "Must remain out of scope: " + re.sub(r"^\s*[-*+]\s+", "", text)
    return re.sub(r"^\s*\d+\.\s+", "", text)


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    transport = workspace / "transport"
    candidate = workspace / "candidate"
    output = Path(os.environ["RUNNER_TEMP"]) / (
        f"spec-280-in-session-contract-{os.environ['GITHUB_RUN_ID']}-"
        f"{os.environ['GITHUB_RUN_ATTEMPT']}"
    )
    if output.exists():
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: pre-existing output directory")
    output.mkdir(parents=True)

    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as handle:
        handle.write(f"CONTRACT_ROOT={output}\n")

    if run("git", "branch", "--show-current", cwd=candidate).strip() != BRANCH:
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: candidate branch mismatch")
    if run("git", "rev-parse", "HEAD", cwd=candidate).strip() != HEAD:
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: candidate HEAD mismatch")
    if run("git", "status", "--porcelain", cwd=candidate).strip():
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: candidate worktree dirty")

    issue = json.loads(
        run(
            "gh",
            "issue",
            "view",
            str(SPEC),
            "--repo",
            REPO,
            "--json",
            "body",
            cwd=candidate,
        )
    )
    body = issue["body"]
    units = build_source_units(body)
    if len(units) != 153:
        raise SystemExit(
            f"SPEC CONTRACT: INVALID\nReason: expected 153 current source units, got {len(units)}"
        )

    inventory: list[dict[str, object]] = []
    manifest_by_cell: dict[str, dict[str, str]] = {}

    for unit in units:
        cell = canonical_cell(unit)
        if cell is not None:
            inventory.append(
                {
                    "source_unit": unit["source_unit"],
                    "classification": "normative-new",
                    "manifest_cells": [cell],
                    "reason": None,
                }
            )
            manifest_by_cell[cell] = {
                "cell": cell,
                "source": unit["source"],
                "requirement": display_requirement(unit),
            }
            continue

        classification = NONCANONICAL.get(unit["source_unit"])
        if classification is None:
            raise SystemExit(
                "SPEC CONTRACT: INVALID\nReason: missing noncanonical classification "
                + unit["source_unit"]
            )
        state, cells, reason = classification
        inventory.append(
            {
                "source_unit": unit["source_unit"],
                "classification": state,
                "manifest_cells": None if cells is None else sorted(cells, key=cell_key),
                "reason": reason,
            }
        )

    for cell, row in NORM_MANIFEST.items():
        manifest_by_cell[cell] = {"cell": cell, **row}

    if set(NONCANONICAL) != {
        unit["source_unit"] for unit in units if canonical_cell(unit) is None
    }:
        raise SystemExit(
            "SPEC CONTRACT: INVALID\nReason: noncanonical classification universe mismatch"
        )

    allowed = {"normative-new", "normative-represented", "non-normative"}
    origins: dict[str, list[str]] = {cell: [] for cell in manifest_by_cell}
    new_origins: dict[str, list[str]] = {cell: [] for cell in manifest_by_cell}

    for unit, row in zip(units, inventory, strict=True):
        state = row["classification"]
        cells = row["manifest_cells"]
        reason = row["reason"]
        if state not in allowed:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: bad classification {unit['source_unit']}"
            )
        if state == "non-normative":
            if cells is not None or not isinstance(reason, str) or not reason.strip():
                raise SystemExit(
                    f"SPEC CONTRACT: INVALID\nReason: invalid non-normative row {unit['source_unit']}"
                )
            continue
        if (
            not isinstance(cells, list)
            or not cells
            or len(cells) != len(set(cells))
            or any(cell not in manifest_by_cell for cell in cells)
        ):
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: invalid mapping {unit['source_unit']}"
            )
        if state == "normative-represented" and (
            not isinstance(reason, str) or not reason.strip()
        ):
            raise SystemExit(
                "SPEC CONTRACT: INVALID\nReason: represented unit lacks reason "
                + unit["source_unit"]
            )
        for cell in cells:
            origins[cell].append(unit["source_unit"])
            if state == "normative-new":
                new_origins[cell].append(unit["source_unit"])

    for cell in manifest_by_cell:
        if not origins[cell] or not new_origins[cell]:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: cell lacks normative-new origin {cell}"
            )

    expected_counts = {"US": 50, "ID": 34, "TD": 34, "OOS": 11}
    for prefix, expected in expected_counts.items():
        actual = {
            cell for cell in manifest_by_cell if re.fullmatch(rf"{prefix}-\d+", cell)
        }
        wanted = {f"{prefix}-{n}" for n in range(1, expected + 1)}
        if actual != wanted:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: {prefix} coverage mismatch"
            )

    sorted_cells = sorted(manifest_by_cell, key=cell_key)
    identity_units = [
        [
            unit["source_unit"],
            unit["text_hash"],
            row["classification"],
            row["manifest_cells"],
        ]
        for unit, row in zip(units, inventory, strict=True)
    ]
    identity_manifest = [[cell, origins[cell]] for cell in sorted_cells]

    body_bytes = body.encode("utf-8")
    if not body.endswith("\n"):
        body_bytes += b"\n"
    spec_body_hash = hashlib.sha256(body_bytes).hexdigest()

    payload = (
        "SPEC-CONTRACT-V2\n"
        + spec_body_hash
        + "\n--SOURCE-UNITS--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in identity_units
        )
        + "\n--MANIFEST--\n"
        + "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in identity_manifest
        )
        + "\n"
    )
    contract_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    helper = transport / ".agents/skills/spec-contract/scripts/classify_ownership.py"
    provenance_raw = run(
        "python",
        str(helper),
        "--baseline",
        BASELINE,
        "--branch",
        BRANCH,
        "--head",
        HEAD,
        cwd=candidate,
    )
    provenance = json.loads(provenance_raw)

    source_counts = {
        "user_stories": 50,
        "implementation_decisions": 34,
        "testing_decisions": 34,
        "out_of_scope": 11,
        "other_normative": sum(
            1
            for unit, row in zip(units, inventory, strict=True)
            if canonical_cell(unit) is None and row["classification"] == "normative-new"
        ),
    }

    handoff = {
        "spec_issue": SPEC,
        "head": HEAD,
        "baseline": BASELINE,
        "branch": BRANCH,
        "spec_body_hash": spec_body_hash,
        "spec_contract_encoding": "V2",
        "spec_contract_hash": contract_hash,
        "default_branch": provenance["default_branch"],
        "default_head": provenance["default_head"],
        "source_counts": source_counts,
        "manifest": [
            {
                "cell": manifest_by_cell[cell]["cell"],
                "source": manifest_by_cell[cell]["source"],
                "requirement": manifest_by_cell[cell]["requirement"],
            }
            for cell in sorted_cells
        ],
        "contract_identity": {
            "source_units": identity_units,
            "manifest": identity_manifest,
        },
    }

    handoff_path = output / "contract.json"
    tmp_path = output / "contract.json.tmp"
    data = json.dumps(
        handoff,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, handoff_path)
    digest = hashlib.sha256(data).hexdigest()

    semantic = {
        "source_units": units,
        "inventory": inventory,
        "manifest": [manifest_by_cell[cell] for cell in sorted_cells],
    }
    (output / "semantic.json").write_text(
        json.dumps(semantic, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    counts = {
        state: sum(1 for row in inventory if row["classification"] == state)
        for state in allowed
    }

    lines = [
        "SPEC CONTRACT: VALID",
        f"Spec: #{SPEC}",
        f"Spec Body Hash: {spec_body_hash}",
        "Spec Contract Encoding: V2",
        f"Spec Contract Hash: {contract_hash}",
        f"Contract handoff digest: {digest}",
        f"Baseline: {BASELINE}",
        f"Branch: {BRANCH}",
        f"HEAD: {HEAD}",
        f"Default branch: {provenance['default_branch']}",
        f"Default branch ref: {provenance['default_head']}",
        "",
        "Source unit integrity:",
        f"- Source units: {len(units)}",
        f"- Classified source units: {len(inventory)}",
        f"- Normative-new source units: {counts['normative-new']}",
        f"- Normative-represented source units: {counts['normative-represented']}",
        f"- Non-normative source units: {counts['non-normative']}",
        "- Unclassified source units: 0",
        "- Normative source units without manifest mapping: 0",
        "- Non-normative source units without reason: 0",
        "",
        "Source counts:",
        f"- User Stories: {source_counts['user_stories']}",
        f"- Implementation Decisions: {source_counts['implementation_decisions']}",
        f"- Testing Decisions: {source_counts['testing_decisions']}",
        f"- Out of Scope: {source_counts['out_of_scope']}",
        f"- Other normative source items: {source_counts['other_normative']}",
        "",
        f"Manifest cells: {len(sorted_cells)}",
        "Unmapped source items: 0",
        "Duplicate source mappings: 0",
        "Ambiguous source items: 0",
        "",
        f"Branch-local commits: {len(provenance['branch_local_commits'])}",
        f"Branch-local surfaces: {len(provenance['branch_local_surfaces'])}",
        f"Mixed-provenance surfaces: {len(provenance['mixed_provenance_surfaces'])}",
        f"Inherited-only integration surfaces: {len(provenance['inherited_only_surfaces'])}",
        "",
        "Build isolation: OWNER-AUTHORIZED IN-SESSION SUBSTITUTE",
        "Historical contract state used as construction input: no",
        "Historical comparison performed before substitute terminal result: no",
        "",
        "Source Unit Inventory:",
    ]

    for unit, row in zip(units, inventory, strict=True):
        cells = row["manifest_cells"]
        lines.append(
            f"- {unit['source_unit']} | {unit['source']} | {unit['text_hash']} | "
            f"{row['classification']} | {cells if cells is not None else 'None'} | "
            f"{row['reason'] if row['reason'] is not None else 'None'}"
        )

    lines.append("")
    lines.append("Spec Contract Manifest:")
    for cell in sorted_cells:
        row = manifest_by_cell[cell]
        lines.append(
            f"- {cell} | {row['source']} | {row['requirement']} | "
            f"Origins: {origins[cell]}"
        )

    terminal = "\n".join(lines) + "\n"
    (output / "terminal.txt").write_text(terminal, encoding="utf-8")
    print("\n".join(lines[:35]))

    if run("git", "rev-parse", "HEAD", cwd=candidate).strip() != HEAD:
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: candidate moved")
    if run("git", "status", "--porcelain", cwd=candidate).strip():
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: candidate mutated")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
