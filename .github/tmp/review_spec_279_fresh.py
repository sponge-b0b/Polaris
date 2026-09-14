from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

REPO = "sponge-b0b/Polaris"
SPEC = 279
HEAD = "4baa54445e0bcd9f19bb75277a9abc84bea3008c"
BASELINE = "4daed9034891600597a47c01b6c39d5ebd9914ca"
BODY_HASH = "5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17"
CONTRACT_HASH = "3044b039742306f1c0ed10085479c7c823ed463443e8d11d761f45de564fb334"
VERIFICATION_HASH = "4b7f7a1641603337b2880adb851ca8ee4d4c13baee97b1da0f80a63d69eac9e4"
RECEIPT_ID = 5659536204


def run(*args: str, cwd: Path | None = None, input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def write_command_output(path: Path, *args: str, cwd: Path | None = None) -> None:
    path.write_text(run(*args, cwd=cwd), encoding="utf-8")


def categories(surface: str) -> list[str]:
    if surface.endswith(".py"):
        return ["python-coding-standards"]
    if (
        surface == "AGENTS.md"
        or surface.startswith(".agents/skills/")
        or surface.startswith("docs/process/")
    ):
        return ["workflow-process-policy"]
    if surface.startswith("wiki/"):
        return ["living-entity-wiki-policy"]
    if surface in {".jscpd.json", "pyproject.toml", "uv.lock"}:
        return ["repository-tool-configuration"]
    return ["repository-policy"]


def add_file(parts: list[str], candidate: Path, rel: str) -> None:
    path = candidate / rel
    if path.exists():
        parts.extend([f"\n=== FILE: {rel} ===\n", path.read_text(encoding="utf-8")])


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    transport = workspace / "transport"
    candidate = workspace / "candidate"
    root = Path(os.environ["RUNNER_TEMP"]) / f"review-spec-279-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    root.mkdir(parents=True, exist_ok=False)
    env_file = Path(os.environ["GITHUB_ENV"])
    with env_file.open("a", encoding="utf-8") as f:
        f.write(f"REVIEW_ROOT={root}\n")

    comments = root / "spec-comments.json"
    comments.write_text(
        run(
            "gh",
            "api",
            "--paginate",
            "--slurp",
            "-H",
            "X-GitHub-Api-Version: 2026-03-10",
            f"repos/{REPO}/issues/{SPEC}/comments?per_page=100",
            cwd=candidate,
        ),
        encoding="utf-8",
    )
    summary = root / "spec-comments-summary.json"
    write_command_output(
        summary,
        "python",
        ".agents/skills/verify-spec/scripts/verify_spec_artifacts.py",
        "comments",
        "--input",
        str(comments),
        cwd=candidate,
    )
    spec_body = root / "spec-body.md"
    spec_body.write_text(
        run(
            "gh",
            "issue",
            "view",
            str(SPEC),
            "--repo",
            REPO,
            "--json",
            "body",
            "--jq",
            ".body",
            cwd=candidate,
        ),
        encoding="utf-8",
    )
    checkpoint_path = root / "checkpoint.json"
    write_command_output(
        checkpoint_path,
        "python",
        ".agents/skills/review-spec/scripts/review_spec_artifacts.py",
        "checkpoint",
        "--comments-summary",
        str(summary),
        "--spec-body",
        str(spec_body),
        "--spec",
        str(SPEC),
        "--head",
        HEAD,
        "--branch",
        "spec-279",
        cwd=candidate,
    )
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["head"] == HEAD
    assert checkpoint["baseline"] == BASELINE
    assert checkpoint["branch"] == "spec-279"
    assert checkpoint["spec_body_hash"] == BODY_HASH
    assert checkpoint["spec_contract_hash"] == CONTRACT_HASH
    assert checkpoint["verification_hash"] == VERIFICATION_HASH
    assert int(checkpoint["receipt_id"]) == RECEIPT_ID
    assert len(checkpoint["manifest"]) == 122
    assert not checkpoint["coverage"]["unresolved"]
    print("Review checkpoint: PASS; exact 122-cell verified contract pinned.")

    provenance_path = root / "provenance.json"
    write_command_output(
        provenance_path,
        "python",
        ".agents/skills/spec-contract/scripts/classify_ownership.py",
        "--baseline",
        BASELINE,
        "--branch",
        "spec-279",
        "--head",
        HEAD,
        cwd=candidate,
    )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    rows: list[dict[str, str]] = []
    candidates: list[tuple[str, str]] = []
    for kind, key in (
        ("branch-local", "branch_local_surfaces"),
        ("mixed", "mixed_provenance_surfaces"),
    ):
        for surface in provenance[key]:
            candidates.append((surface, kind))
    candidates.sort()
    n = 0
    for surface, provenance_kind in candidates:
        for category in categories(surface):
            n += 1
            rows.append(
                {
                    "candidate": f"STD-CAND-{n:03d}",
                    "surface": surface,
                    "mechanical_provenance": provenance_kind,
                    "standards_category": category,
                }
            )
    standards_path = root / "standards-universe.json"
    standards_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Provisional Standards candidates: {len(rows)}; omitted before attribution: 0")

    arch = [
        {
            "cell": "ARCH-1",
            "claim": "Application Use Cases owns Decision commands, queries, transaction semantics, idempotency, and cross-entity coordination without becoming a second domain source of truth.",
            "authority": ["Spec #279 Architecture Impact", "docs/current/platform-architecture-0.2.0.md", "docs/proposed/application-use-cases-investment-decision-lifecycle.md", "ADR 0001"],
        },
        {
            "cell": "ARCH-2",
            "claim": "Investment Decision identity, lifecycle, applicability, correction, renewal, and relationship semantics remain domain-owned while the application layer coordinates them without redefining them.",
            "authority": ["Spec #279", "docs/proposed/investment-decisions-r2-foundation-public-contract.md", "docs/proposed/investment-decisions-lifecycle-model.md", "docs/proposed/investment-decisions-decision-relationship-model.md"],
        },
        {
            "cell": "ARCH-3",
            "claim": "Durable Persistence is accessed only through technology-neutral inward-owned Decisions ports; PostgreSQL, ORM, driver, locking, isolation, and vendor-native representations do not leak into application contracts.",
            "authority": ["Spec #279 US-44, ID-24, OOS-1", "ADR 0003", "docs/proposed/durable-persistence-investment-decision-history.md"],
        },
        {
            "cell": "ARCH-4",
            "claim": "Governance & Authority trusted-basis seams preserve the separation between Actor Attribution, application authorization, and investment authority; #279 does not implement Governance durable truth.",
            "authority": ["Spec #279 US-18..20, US-36, ID-4, ID-13, OOS-2", "docs/proposed/application-use-cases-investment-decision-lifecycle.md"],
        },
        {
            "cell": "ARCH-5",
            "claim": "Interfaces and Background Work are later thin callers of the same application use cases and no alternate business-write path is introduced by #279.",
            "authority": ["Spec #279 US-43, OOS-11", "docs/current/platform-architecture-0.2.0.md", "ADR 0001"],
        },
        {
            "cell": "ARCH-6",
            "claim": "Real I/O/waiting seams are async-first, pure deterministic Decision-domain work remains synchronous, contracts stay executor-neutral, and correctness does not depend on one event loop, one thread, or incidental GIL serialization.",
            "authority": ["Spec #279 Solution, ID-29..32", "ADR 0004"],
        },
        {
            "cell": "ARCH-7",
            "claim": "The implementation preserves modular-monolith dependency direction, inward-owned ports, direct business truth, immutable history, and avoids concrete infrastructure imports from the application boundary.",
            "authority": ["Spec #279 Architecture Impact", "ADR 0001", "ADR 0002", "ADR 0003", "docs/current/platform-architecture-0.2.0.md"],
        },
        {
            "cell": "ARCH-8",
            "claim": "R2 remains purpose-specific: no platform-wide Unit of Work, generic workflow/event runtime, speculative PRIOR_DECISION_CONTEXT payload/retrieval, or other unearned cross-owner machinery is introduced.",
            "authority": ["Spec #279 US-42, US-45, ID-25, ID-28, OOS-7..10"],
        },
    ]
    arch_path = root / "architecture-universe.json"
    arch_path.write_text(json.dumps(arch, indent=2), encoding="utf-8")

    authority_files = {
        "CURRENT ROOT AGENTS": transport / "AGENTS.md",
        "CURRENT REVIEW-SPEC SKILL": transport / ".agents/skills/review-spec/SKILL.md",
        "CURRENT REVIEW-ARCHITECTURE SKILL": transport / ".agents/skills/review-architecture/SKILL.md",
        "CURRENT CODING-STANDARDS SKILL": transport / ".agents/skills/coding-standards/SKILL.md",
        "SPEC #279 BODY": spec_body,
        "EXACT REVIEW CHECKPOINT JSON": checkpoint_path,
        "CURRENT CHANGE PROVENANCE JSON": provenance_path,
        "PROVISIONAL STANDARDS UNIVERSE JSON": standards_path,
        "ARCHITECTURE UNIVERSE JSON": arch_path,
    }

    instructions = r'''You are the single genuinely fresh semantic reviewer for Polaris `$review-spec` on Spec #279. You did not participate in implementation, verification, prior review, remediation, or parent orchestration.

Review exact candidate `spec-279@4baa54445e0bcd9f19bb75277a9abc84bea3008c`, baseline `4daed9034891600597a47c01b6c39d5ebd9914ca`, using the embedded current authority and evidence only.

CRITICAL ADVERSARIAL BOUNDARY:
- Do NOT seek, infer, or use any prior Spec Review issue, Root Blocker history, previous review finding, prior review-proof ledger, prior reviewer conclusion, conversation memory, or historical remediation conclusion.
- The parent will perform root/provenance/domain-finality reconciliation only after your provisional findings are frozen.
- The passing verification receipt establishes the immutable review contract/manifest, not correctness evidence for your semantic dispositions.
- Do not rerun verification gates. This is semantic review, not `$verify-spec`.
- Do not mutate repository/tracker state and do not access network, shell, memory, or external tools.

EXECUTION INTEGRITY:
Perform exactly three sequential, semantically independent passes in this order: Standards, Spec, Architecture. Freeze each axis before starting the next. Shared factual excerpts may be reused; an earlier axis's semantic conclusion is never evidence for a later axis. Continue through all cells even if you find a blocker.

STANDARDS:
The supplied standards universe is complete provisional candidate input. Return exactly one attribution/disposition row per supplied candidate. Mechanical provenance is not semantic ownership. `in-scope` requires exact current Spec/architecture/tracker authority materially owning that Standards behavior. `out-of-scope` remains explicit N/A. Resolve ambiguity through a bounded same-context self-challenge or report it as an unresolved challenge trigger. Standards Blocking requires both in-scope attribution and an actual current repository-standard violation.

SPEC:
Use the supplied checkpoint manifest EXACTLY. Return exactly one coverage row per manifest cell and no extra Spec cells. Do not rebuild or expand the Spec contract. Evaluate every requirement against current source/tests and supplied governing authority. Preserve conditions/triggers if a cell is conditional. OOS cells may be `not-applicable` only with the exact exclusion reason. A passing verifier is never proof that a cell is clean.

ARCHITECTURE:
Use every supplied ARCH cell and apply the embedded `$review-architecture` method. Add ARCH cells only when supplied current authority independently requires a materially distinct affected authority/surface omitted by the parent. Build authority-first and inspect canonical, sibling, alternate, and bypass paths represented by supplied evidence. Architecture findings state whether a new architecture decision is required.

CLAIM-PROOF INTEGRITY:
For every material cell internally establish claim/predicate/domain/falsifier/evidence and exclude the falsifier before `checked-no-finding`; no unproven material assumption may remain. When concrete ambiguity/evidence conflict appears, perform one bounded self-challenge in this SAME reviewer context before final output. `challenge_triggers` contains only questions still unresolved after that attempt.

PROOF REUSE OUTPUT:
Every clean or N/A cell must appear exactly once in a proof group for its axis. Group only when evidence identity and invalidation boundary are genuinely shared. Every proof group needs a non-empty invalidation boundary. Blocking/advisory cells appear in no clean proof group.

Emit EXACTLY one JSON object and nothing else using this schema:
{
  "reviewer_execution":"fresh-github-actions-copilot-single-reviewer-three-axis-passes",
  "standards":{
    "coverage":[{"candidate":"STD-CAND-001","scope":"in-scope|out-of-scope","standards_disposition":"checked-no-finding|blocking|advisory|not-applicable","authority":"...","evidence":"..."}],
    "blocking":[{"title":"...","cells":["STD-CAND-..."],"surface":"...","authority":"...","evidence":"...","why":"..."}],
    "advisory":[{"title":"...","cells":["STD-CAND-..."],"surface":"...","authority":"...","evidence":"...","why":"..."}],
    "proof_groups":[{"id":"RPR-STANDARDS-1","cells":["STD-CAND-..."],"disposition":"checked-no-finding|not-applicable","evidence_identity":"...","evidence_stability":"repository-immutable|mutable","invalidation_boundary":["..."]}],
    "challenge_triggers":[]
  },
  "spec":{
    "coverage":[{"cell":"US-1","disposition":"checked-no-finding|blocking|advisory|not-applicable","evidence":"...","reason":null}],
    "blocking":[{"title":"...","cells":["US-..."],"surface":"...","authority":"...","evidence":"...","why":"..."}],
    "advisory":[{"title":"...","cells":["US-..."],"surface":"...","authority":"...","evidence":"...","why":"..."}],
    "proof_groups":[{"id":"RPR-SPEC-1","cells":["US-..."],"disposition":"checked-no-finding|not-applicable","evidence_identity":"...","evidence_stability":"repository-immutable|mutable","invalidation_boundary":["..."]}],
    "challenge_triggers":[]
  },
  "architecture":{
    "coverage":[{"cell":"ARCH-1","disposition":"checked-no-finding|blocking|advisory|not-applicable","authority":"...","surfaces":["..."],"evidence":"...","architecture_decision_required":"Yes|No|null","routing":"existing-authority remediation|upstream architecture resolution|none"}],
    "blocking":[{"title":"...","cells":["ARCH-..."],"surface":"...","authority":"...","evidence":"...","why":"...","architecture_decision_required":"Yes|No","routing":"..."}],
    "advisory":[{"title":"...","cells":["ARCH-..."],"surface":"...","authority":"...","evidence":"...","why":"...","architecture_decision_required":"Yes|No|null","routing":"..."}],
    "added_cells":[{"cell":"ARCH-9","claim":"...","authority":["..."]}],
    "proof_groups":[{"id":"RPR-ARCH-1","cells":["ARCH-..."],"disposition":"checked-no-finding|not-applicable","evidence_identity":"...","evidence_stability":"repository-immutable|mutable","invalidation_boundary":["..."]}],
    "challenge_triggers":[]
  }
}

Consistency rules:
- Coverage is one-to-one with each supplied universe plus declared Architecture added cells.
- Standards `out-of-scope` uses `not-applicable`.
- A finding cell is not both Blocking and Advisory.
- Every clean/N/A cell is in exactly one proof group; finding-bearing cells are in none.
- Keep evidence concise but specific enough for parent provenance validation.
'''

    parts = [instructions]
    for label, path in authority_files.items():
        parts.extend([f"\n=== {label} ===\n", path.read_text(encoding="utf-8")])

    evidence_files = [
        "pyproject.toml",
        "wiki/index.md",
        "wiki/_schema.md",
        "wiki/entities/investment-decisions.md",
        "wiki/entities/application-use-cases.md",
        "wiki/entities/durable-persistence.md",
        "wiki/entities/governance-authority.md",
        "wiki/entities/interfaces-presentation.md",
        "wiki/entities/background-work-follow-up.md",
        "docs/current/platform-architecture-0.2.0.md",
        "docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md",
        "docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md",
        "docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md",
        "docs/adr/0004-platform-make-async-and-multi-core-execution-first-class.md",
        "docs/proposed/investment-decisions-r2-foundation-public-contract.md",
        "docs/proposed/investment-decisions-lifecycle-model.md",
        "docs/proposed/investment-decisions-decision-relationship-model.md",
        "docs/proposed/application-use-cases-investment-decision-lifecycle.md",
        "docs/proposed/durable-persistence-investment-decision-history.md",
        "src/polaris/application/__init__.py",
        "src/polaris/application/decisions/__init__.py",
        "src/polaris/application/decisions/contracts.py",
        "src/polaris/application/decisions/initiation.py",
        "src/polaris/application/decisions/lifecycle_correction.py",
        "src/polaris/application/decisions/memory.py",
        "src/polaris/application/decisions/ordinary_work.py",
        "src/polaris/application/decisions/relationships.py",
        "tests/application/decisions/test_initiation.py",
        "tests/application/decisions/test_lifecycle_correction.py",
        "tests/application/decisions/test_memory.py",
        "tests/application/decisions/test_ordinary_work.py",
        "tests/application/decisions/test_relationships.py",
        "tests/application/decisions/test_resolution.py",
    ]
    for rel in evidence_files:
        add_file(parts, candidate, rel)

    prompt = "\n".join(parts)
    result = subprocess.run(
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
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    review_path = root / "review-result.json"
    review_path.write_text(result.stdout, encoding="utf-8")

    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["reviewer_execution"] == "fresh-github-actions-copilot-single-reviewer-three-axis-passes"
    allowed = {"checked-no-finding", "blocking", "advisory", "not-applicable"}

    std_expected = [row["candidate"] for row in rows]
    std_rows = review["standards"]["coverage"]
    std_actual = [row["candidate"] for row in std_rows]
    assert len(std_actual) == len(set(std_actual)) == len(std_expected)
    assert set(std_actual) == set(std_expected)
    for row in std_rows:
        assert row["scope"] in {"in-scope", "out-of-scope"}
        assert row["standards_disposition"] in allowed
        if row["scope"] == "out-of-scope":
            assert row["standards_disposition"] == "not-applicable"

    spec_expected = [row["cell"] for row in checkpoint["manifest"]]
    spec_rows = review["spec"]["coverage"]
    spec_actual = [row["cell"] for row in spec_rows]
    assert len(spec_actual) == len(set(spec_actual)) == 122
    assert set(spec_actual) == set(spec_expected)
    assert all(row["disposition"] in allowed for row in spec_rows)

    supplied_arch = [row["cell"] for row in arch]
    added = review["architecture"].get("added_cells", [])
    added_ids = [row["cell"] for row in added]
    assert len(added_ids) == len(set(added_ids))
    assert not (set(supplied_arch) & set(added_ids))
    arch_expected = supplied_arch + added_ids
    arch_rows = review["architecture"]["coverage"]
    arch_actual = [row["cell"] for row in arch_rows]
    assert len(arch_actual) == len(set(arch_actual)) == len(arch_expected)
    assert set(arch_actual) == set(arch_expected)
    assert all(row["disposition"] in allowed for row in arch_rows)

    for axis_name, id_key, disposition_key in (
        ("standards", "candidate", "standards_disposition"),
        ("spec", "cell", "disposition"),
        ("architecture", "cell", "disposition"),
    ):
        axis = review[axis_name]
        coverage = axis["coverage"]
        clean = {
            row[id_key]
            for row in coverage
            if row[disposition_key] in {"checked-no-finding", "not-applicable"}
        }
        finding = {
            row[id_key]
            for row in coverage
            if row[disposition_key] in {"blocking", "advisory"}
        }
        proof_cells: list[str] = []
        for group in axis["proof_groups"]:
            assert group["disposition"] in {"checked-no-finding", "not-applicable"}
            assert group["invalidation_boundary"]
            proof_cells.extend(group["cells"])
        assert len(proof_cells) == len(set(proof_cells))
        assert set(proof_cells) == clean
        assert not (set(proof_cells) & finding)
        assert not axis.get("challenge_triggers")

    result_summary = {
        "standards_candidates": len(std_rows),
        "spec_cells": len(spec_rows),
        "architecture_cells": len(arch_rows),
        "standards_blocking": len(review["standards"]["blocking"]),
        "standards_advisory": len(review["standards"]["advisory"]),
        "spec_blocking": len(review["spec"]["blocking"]),
        "spec_advisory": len(review["spec"]["advisory"]),
        "architecture_blocking": len(review["architecture"]["blocking"]),
        "architecture_advisory": len(review["architecture"]["advisory"]),
    }
    (root / "review-summary.json").write_text(json.dumps(result_summary, indent=2), encoding="utf-8")
    print("Fresh review coverage validation: PASS")
    print(json.dumps(result_summary, sort_keys=True))
    print("=== REVIEW-RESULT-BEGIN ===")
    print(review_path.read_text(encoding="utf-8"))
    print("=== REVIEW-RESULT-END ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
