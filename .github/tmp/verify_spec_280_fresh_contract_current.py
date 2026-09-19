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


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout


def source_units(body: str) -> list[dict[str, str]]:
    lines = body.splitlines()
    units: list[dict[str, str]] = []
    section = "(preamble)"
    paragraph: list[str] = []
    kind_counts: dict[tuple[str, str], int] = {}
    oos_counter = 0

    def normalize(value: str) -> str:
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        return "\n".join(part.rstrip() for part in value.split("\n")).rstrip()

    def source_identity(kind: str, text: str) -> str:
        nonlocal oos_counter
        numbered = re.match(r"^\s*(\d+)\.\s+", text)
        if (
            section
            in {"User Stories", "Implementation Decisions", "Testing Decisions"}
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


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    candidate = workspace / "candidate"

    if run("git", "rev-parse", "HEAD", cwd=candidate).strip() != HEAD:
        raise SystemExit("fresh builder candidate HEAD mismatch")
    if run("git", "status", "--porcelain", cwd=candidate).strip():
        raise SystemExit("fresh builder candidate is dirty")

    build_root = Path(os.environ["RUNNER_TEMP"]) / (
        f"spec-280-fresh-contract-{os.environ['GITHUB_RUN_ID']}-"
        f"{os.environ['GITHUB_RUN_ATTEMPT']}"
    )
    handoff_path = build_root / "contract.json"
    terminal_path = build_root / "terminal.txt"
    semantic_path = build_root / "semantic.json"
    provenance_path = build_root / "provenance.json"

    if build_root.exists() or handoff_path.exists():
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: pre-existing builder scratch")
    build_root.mkdir(parents=True)

    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as handle:
        handle.write(f"CONTRACT_ROOT={build_root}\n")

    spec_raw = run(
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
    body = json.loads(spec_raw)["body"]
    units = source_units(body)

    agents = (candidate / "AGENTS.md").read_text(encoding="utf-8")
    contract_skill = (
        candidate / ".agents/skills/spec-contract/SKILL.md"
    ).read_text(encoding="utf-8")

    instructions = f"""You are the genuinely fresh semantic builder for Polaris
`$spec-contract` build mode. This model invocation has not been supplied any
prior representation of Spec #280's contract.

Exact allowed build identity:
- Originating Spec: #{SPEC}, Implement durable PostgreSQL Investment Decision persistence
- Fixed baseline: {BASELINE}
- Branch: {BRANCH}
- HEAD: {HEAD}
- Mode: build
- Handoff output is owned by the surrounding isolated process and did not exist before dispatch.

You must follow the embedded CURRENT `$spec-contract` skill for semantic
classification and manifest construction. The surrounding deterministic process
owns only source-unit partitioning, provenance calculation, schema validation,
V2 hashing, and handoff serialization.

STRICT ISOLATION:
- Do not infer, request, search for, or reproduce from any prior contract hash,
  manifest, mapping, source-unit classification, receipt, review artifact,
  proof-reuse state, handoff, conversation, cache, or historical comparison.
- Do not use tools, network, shell, memory, filesystem discovery, or Git history.
- The only semantic inputs are embedded below: current AGENTS.md, current
  spec-contract SKILL.md, current Spec body, and a freshly materialized
  UNCLASSIFIED source-unit inventory from that body.
- Do not emit any hash or historical comparison.

Return EXACTLY one JSON object and nothing else:
{{"inventory":[{{"source_unit":"SU-0001","classification":"normative-new | normative-represented | non-normative","manifest_cells":["US-1"] or null,"reason":"concise reason" or null}}],"manifest":[{{"cell":"US-1","source":"exact deterministic source identity","requirement":"faithful normative obligation","named_surfaces":"explicit named surface" or null}}]}}

Rules:
- One inventory row for every SU-* row, same order.
- Every numbered User Story maps/creates US-<n>; Implementation Decision ID-<n>;
  Testing Decision TD-<n>; Out of Scope OOS-<n>.
- Materially unique normative obligations elsewhere create stable document-order
  NORM-<n> only when not already fully represented by canonical cells.
- normative-represented must list all cells that fully represent the unit and give
  a concise reason.
- non-normative must use manifest_cells null and give a concise reason.
- Mixed explanatory/normative units are normative.
- Preserve positive/negative and fail-closed distinctions.
- Every manifest source must equal an exact source identity from the fresh inventory.
- Before output: every unit classified, every normative unit mapped, every
  non-normative unit reasoned, no missing canonical item, no duplicate cell, no
  ambiguous mapping.
"""

    prompt = "\n".join(
        [
            instructions,
            "\n=== CURRENT ROOT AGENTS.md ===\n",
            agents,
            "\n=== CURRENT spec-contract SKILL.md ===\n",
            contract_skill,
            "\n=== CURRENT SPEC #280 BODY ===\n",
            body,
            "\n=== FRESH UNCLASSIFIED SOURCE UNIT INVENTORY ===\n",
            json.dumps(units, ensure_ascii=False, separators=(",", ":")),
        ]
    )

    copilot_home = build_root / "copilot-home"
    copilot_home.mkdir()
    env = {
        "COPILOT_HOME": str(copilot_home),
        "COPILOT_AUTO_UPDATE": "false",
        "COPILOT_MCP_TOOL_CACHE": "false",
    }
    proc = subprocess.run(
        [
            "copilot",
            "-s",
            "--no-custom-instructions",
            "--disable-builtin-mcps",
            "--deny-tool=shell,write,url,memory",
            "--no-ask-user",
            "--no-remote",
            "--no-remote-export",
        ],
        input=prompt,
        cwd=candidate,
        env={**os.environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode

    semantic_path.write_text(proc.stdout, encoding="utf-8")
    semantic = json.loads(proc.stdout)

    provenance_text = run(
        "python",
        ".agents/skills/spec-contract/scripts/classify_ownership.py",
        "--baseline",
        BASELINE,
        "--branch",
        BRANCH,
        "--head",
        HEAD,
        cwd=candidate,
    )
    provenance_path.write_text(provenance_text, encoding="utf-8")
    provenance = json.loads(provenance_text)

    if set(semantic) != {"inventory", "manifest"}:
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: semantic result schema mismatch")
    inventory = semantic["inventory"]
    manifest = semantic["manifest"]
    if not isinstance(inventory, list) or not isinstance(manifest, list):
        raise SystemExit("SPEC CONTRACT: INVALID\nReason: semantic result types invalid")
    if [row.get("source_unit") for row in inventory] != [
        row["source_unit"] for row in units
    ]:
        raise SystemExit(
            "SPEC CONTRACT: INVALID\nReason: semantic inventory coverage/order mismatch"
        )

    rank = {"US": 0, "ID": 1, "TD": 2, "OOS": 3, "NORM": 4}
    cell_pattern = re.compile(r"^(US|ID|TD|OOS|NORM)-(\d+)(?:\.(.+))?$")

    def cell_key(cell: str) -> tuple[int, int, int, str]:
        match = cell_pattern.fullmatch(cell)
        if not match or int(match.group(2)) <= 0:
            raise ValueError(cell)
        suffix = match.group(3)
        return (
            rank[match.group(1)],
            int(match.group(2)),
            0 if suffix is None else 1,
            "" if suffix is None else suffix,
        )

    manifest_by_cell: dict[str, dict[str, object]] = {}
    for row in manifest:
        if not isinstance(row, dict) or set(row) != {
            "cell",
            "source",
            "requirement",
            "named_surfaces",
        }:
            raise SystemExit("SPEC CONTRACT: INVALID\nReason: manifest row schema mismatch")
        cell = row["cell"]
        if not isinstance(cell, str):
            raise SystemExit("SPEC CONTRACT: INVALID\nReason: non-string manifest cell")
        try:
            cell_key(cell)
        except ValueError:
            raise SystemExit(f"SPEC CONTRACT: INVALID\nReason: invalid cell {cell}")
        if cell in manifest_by_cell:
            raise SystemExit(f"SPEC CONTRACT: INVALID\nReason: duplicate cell {cell}")
        if (
            not isinstance(row["source"], str)
            or not row["source"].strip()
            or not isinstance(row["requirement"], str)
            or not row["requirement"].strip()
        ):
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: incomplete manifest row {cell}"
            )
        manifest_by_cell[cell] = row

    allowed = {"normative-new", "normative-represented", "non-normative"}
    normalized: list[dict[str, object]] = []
    origins = {cell: [] for cell in manifest_by_cell}
    new_origins = {cell: [] for cell in manifest_by_cell}

    for row in inventory:
        if not isinstance(row, dict) or set(row) != {
            "source_unit",
            "classification",
            "manifest_cells",
            "reason",
        }:
            raise SystemExit("SPEC CONTRACT: INVALID\nReason: inventory row schema mismatch")
        source_unit = row["source_unit"]
        classification = row["classification"]
        cells = row["manifest_cells"]
        reason = row["reason"]

        if classification not in allowed:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: invalid classification {source_unit}"
            )

        if classification == "non-normative":
            if cells not in (None, []) or not isinstance(reason, str) or not reason.strip():
                raise SystemExit(
                    f"SPEC CONTRACT: INVALID\nReason: invalid non-normative row {source_unit}"
                )
            normalized_cells = None
        else:
            if (
                not isinstance(cells, list)
                or not cells
                or any(not isinstance(cell, str) for cell in cells)
                or len(cells) != len(set(cells))
            ):
                raise SystemExit(
                    f"SPEC CONTRACT: INVALID\nReason: invalid normative mapping {source_unit}"
                )
            try:
                normalized_cells = sorted(cells, key=cell_key)
            except ValueError as exc:
                raise SystemExit(
                    f"SPEC CONTRACT: INVALID\nReason: invalid mapped cell {exc}"
                )
            if any(cell not in manifest_by_cell for cell in normalized_cells):
                raise SystemExit(
                    f"SPEC CONTRACT: INVALID\nReason: missing mapped cell {source_unit}"
                )
            if classification == "normative-represented" and (
                not isinstance(reason, str) or not reason.strip()
            ):
                raise SystemExit(
                    f"SPEC CONTRACT: INVALID\nReason: represented row lacks reason {source_unit}"
                )
            for cell in normalized_cells:
                origins[cell].append(source_unit)
                if classification == "normative-new":
                    new_origins[cell].append(source_unit)

        normalized.append(
            {
                "source_unit": source_unit,
                "classification": classification,
                "manifest_cells": normalized_cells,
                "reason": reason,
            }
        )

    for cell in manifest_by_cell:
        if not origins[cell] or not new_origins[cell]:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: cell lacks normative origin {cell}"
            )

    canonical_sections = {
        "User Stories": "US",
        "Implementation Decisions": "ID",
        "Testing Decisions": "TD",
        "Out of Scope": "OOS",
    }
    canonical_counts = {prefix: 0 for prefix in canonical_sections.values()}
    canonical_units: set[str] = set()

    for unit, inv in zip(units, normalized, strict=True):
        section = unit["section"]
        if section not in canonical_sections:
            continue
        prefix = canonical_sections[section]
        source = unit["source"]
        match = re.fullmatch(rf"{re.escape(section)} (\d+)", source)
        if not match:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: malformed canonical source {source}"
            )
        number = int(match.group(1))
        canonical_counts[prefix] += 1
        canonical_units.add(unit["source_unit"])
        cell = f"{prefix}-{number}"
        if (
            inv["classification"] != "normative-new"
            or cell not in (inv["manifest_cells"] or [])
            or cell not in manifest_by_cell
            or manifest_by_cell[cell]["source"] != source
        ):
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: canonical mapping mismatch {source}"
            )

    for prefix, count in canonical_counts.items():
        base_cells = {
            cell
            for cell in manifest_by_cell
            if re.fullmatch(rf"{prefix}-\d+", cell)
        }
        if base_cells != {f"{prefix}-{n}" for n in range(1, count + 1)}:
            raise SystemExit(
                f"SPEC CONTRACT: INVALID\nReason: {prefix} source coverage mismatch"
            )

    for unit, inv in zip(units, normalized, strict=True):
        if (
            unit["source_unit"] not in canonical_units
            and inv["classification"] == "normative-new"
            and any(
                not cell.startswith("NORM-")
                for cell in (inv["manifest_cells"] or [])
            )
        ):
            raise SystemExit(
                "SPEC CONTRACT: INVALID\nReason: noncanonical new source mapped "
                f"outside NORM namespace: {unit['source_unit']}"
            )

    sorted_cells = sorted(manifest_by_cell, key=cell_key)
    identity_units = [
        [
            unit["source_unit"],
            unit["text_hash"],
            inv["classification"],
            inv["manifest_cells"],
        ]
        for unit, inv in zip(units, normalized, strict=True)
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

    other_normative = sum(
        1
        for unit, inv in zip(units, normalized, strict=True)
        if (
            unit["source_unit"] not in canonical_units
            and inv["classification"] == "normative-new"
        )
    )
    source_counts = {
        "user_stories": canonical_counts["US"],
        "implementation_decisions": canonical_counts["ID"],
        "testing_decisions": canonical_counts["TD"],
        "out_of_scope": canonical_counts["OOS"],
        "other_normative": other_normative,
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

    handoff_bytes = json.dumps(
        handoff,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    handoff_path.write_bytes(handoff_bytes)
    digest = hashlib.sha256(handoff_bytes).hexdigest()

    counts = {
        classification: sum(
            1
            for row in normalized
            if row["classification"] == classification
        )
        for classification in allowed
    }

    terminal = "\n".join(
        [
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
            f"- Classified source units: {len(normalized)}",
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
            "Build isolation: PASS",
            "Prior contract representations supplied or inspected: 0",
            "Pre-existing scratch contract artifacts inspected: 0",
            "Handoff path existed before build: no",
        ]
    )
    terminal_path.write_text(terminal + "\n", encoding="utf-8")
    print(terminal)

    if run("git", "rev-parse", "HEAD", cwd=candidate).strip() != HEAD:
        raise SystemExit("fresh builder candidate moved")
    if run("git", "status", "--porcelain", cwd=candidate).strip():
        raise SystemExit("fresh builder mutated candidate repository")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
