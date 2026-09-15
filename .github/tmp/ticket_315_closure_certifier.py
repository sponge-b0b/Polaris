from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
TICKET = 315
SPEC = 279
REVIEW = 310
BASELINE = "41bab9971d380b861cb7bbacd59ad2bdf5d9370f"
CANDIDATE_STATE = "64ac0a239d7f472205063a45ae1d59b3815321f753afe67e8deb31658657b341"
CHECKPOINT_ID = 5675531025
CHANGED = [
    "src/polaris/application/decisions/relationships.py",
    "tests/application/decisions/test_relationships.py",
]


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


def gh(candidate: Path, *args: str) -> str:
    return run("gh", *args, cwd=candidate)


def candidate_state(candidate: Path) -> str:
    def zpaths(*args: str) -> list[bytes]:
        raw = subprocess.run(
            ["git", *args], cwd=candidate, check=True, stdout=subprocess.PIPE
        ).stdout
        return [item for item in raw.split(b"\0") if item]

    paths = set(zpaths("diff", "--no-renames", "--name-only", "-z", BASELINE, "--"))
    paths.update(zpaths("ls-files", "--others", "--exclude-standard", "-z"))
    digest = hashlib.sha256()
    for raw_path in sorted(paths):
        path = candidate / os.fsdecode(raw_path)
        digest.update(b"path\0" + raw_path + b"\0")
        try:
            metadata = os.lstat(path)
        except FileNotFoundError:
            digest.update(b"state\0DELETED\0")
            continue
        if stat.S_ISLNK(metadata.st_mode):
            mode = b"120000"
            content_hash = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        elif stat.S_ISREG(metadata.st_mode):
            mode = b"100755" if metadata.st_mode & stat.S_IXUSR else b"100644"
            file_hash = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    file_hash.update(chunk)
            content_hash = file_hash.hexdigest()
        else:
            raise SystemExit(f"unsupported candidate path type: {path}")
        digest.update(b"mode\0" + mode + b"\0sha256\0")
        digest.update(content_hash.encode("ascii") + b"\0")
    return digest.hexdigest()


def add_file(parts: list[str], root: Path, rel: str, label: str | None = None) -> None:
    path = root / rel
    if not path.exists():
        raise SystemExit(f"missing evidence file: {path}")
    parts.extend([f"\n=== {label or ('FILE: ' + rel)} ===\n", path.read_text(encoding="utf-8")])


def consumer_scan(candidate: Path) -> str:
    needles = (
        "DecisionRelationshipService",
        "DecisionRelationshipCorrectionService",
        ".renew(",
        "establish_supersession(",
        ".correct(",
        "relationship_fact(",
        "relationship_correction(",
        "_RELATIONSHIP_ERRORS",
        "_raise_relationship_error",
    )
    rows: list[str] = []
    for base in (candidate / "src", candidate / "tests"):
        for path in base.rglob("*.py"):
            rel = path.relative_to(candidate)
            if "legacy" in rel.parts or ".venv" in rel.parts:
                continue
            text = path.read_text(encoding="utf-8")
            matches = sorted(needle for needle in needles if needle in text)
            if matches:
                rows.append(f"{rel}: {', '.join(matches)}")
    return "\n".join(sorted(rows))


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    transport = workspace / "transport"
    candidate = workspace / "candidate"
    out_root = Path(os.environ["RUNNER_TEMP"]) / (
        f"ticket-315-closure-certifier-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    )
    out_root.mkdir(parents=True, exist_ok=True)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as handle:
        handle.write(f"CERT_ROOT={out_root}\n")

    if run("git", "rev-parse", "HEAD", cwd=candidate).strip() != BASELINE:
        raise SystemExit("candidate checkout is not pinned ticket baseline")
    if run("git", "status", "--porcelain", cwd=candidate).strip():
        raise SystemExit("candidate checkout dirty before reconstruction")

    env = {"CANDIDATE_ROOT": str(candidate)}
    run("python", ".github/tmp/implement_315_candidate.py", cwd=transport, env=env)
    run("uv", "run", "--locked", "ruff", "check", "--fix", *CHANGED, cwd=candidate)
    run("uv", "run", "--locked", "ruff", "format", *CHANGED, cwd=candidate)
    state = candidate_state(candidate)
    if state != CANDIDATE_STATE:
        raise SystemExit(f"candidate state mismatch: {state}")

    checks: list[str] = []
    checks.append(
        "git diff --check:\n" + run("git", "diff", "--check", BASELINE, cwd=candidate)
    )
    checks.append(
        "ruff format --check:\n"
        + run("uv", "run", "--locked", "ruff", "format", "--check", *CHANGED, cwd=candidate)
    )
    checks.append(
        "ruff check:\n" + run("uv", "run", "--locked", "ruff", "check", *CHANGED, cwd=candidate)
    )
    checks.append(
        "mypy:\n"
        + run(
            "uv",
            "run",
            "--locked",
            "mypy",
            "--explicit-package-bases",
            *CHANGED,
            cwd=candidate,
        )
    )
    checks.append(
        "targeted relationship pytest:\n"
        + run(
            "uv",
            "run",
            "--locked",
            "pytest",
            "-q",
            "tests/application/decisions/test_relationships.py",
            cwd=candidate,
            env={"UV_CACHE_DIR": "/tmp/uv-cache"},
        )
    )
    checks.append(
        "complete architecture invariant pytest:\n"
        + run(
            "uv",
            "run",
            "--locked",
            "pytest",
            "-q",
            "tests/test_architecture_guard.py",
            "tests/test_architecture_guard_identity_aliases.py",
            "tests/test_architecture_guard_legacy_loaders.py",
            cwd=candidate,
            env={
                "UV_CACHE_DIR": "/tmp/uv-cache",
                "POLARIS_BROAD_VERIFY_AUTHORIZED": "verify-architecture",
            },
        )
    )
    if candidate_state(candidate) != CANDIDATE_STATE:
        raise SystemExit("candidate mutated during fresh non-mutating checks")

    ticket = gh(
        candidate,
        "issue",
        "view",
        str(TICKET),
        "--repo",
        REPO,
        "--json",
        "number,title,body,state,url,labels",
    )
    review = gh(
        candidate,
        "issue",
        "view",
        str(REVIEW),
        "--repo",
        REPO,
        "--json",
        "number,title,body,state,url,labels",
    )
    spec = gh(
        candidate,
        "issue",
        "view",
        str(SPEC),
        "--repo",
        REPO,
        "--json",
        "number,title,body,state,url,labels",
    )
    parent = gh(candidate, "api", f"repos/{REPO}/issues/{TICKET}/parent")
    checkpoint = gh(candidate, "api", f"repos/{REPO}/issues/comments/{CHECKPOINT_ID}")
    coverage = gh(candidate, "api", f"repos/{REPO}/issues/comments/5630203405")
    finding_ledger = gh(candidate, "api", f"repos/{REPO}/issues/comments/5662220111")
    decomposition = gh(candidate, "api", f"repos/{REPO}/issues/comments/5663250943")
    ticket_json = json.loads(ticket)
    contract_identity = hashlib.sha256(ticket_json["body"].encode()).hexdigest()
    diff = run("git", "diff", "--no-renames", BASELINE, "--", cwd=candidate)
    scan = consumer_scan(candidate)

    instructions = f'''You are the ONE genuinely fresh, non-mutating `$verify-ticket-closure` verifier for Polaris ticket #315. You did not implement, draft, reconcile, review, or certify this candidate before this invocation. The implementation parent is in dispatcher-only mode.

Execute the embedded CURRENT `.agents/skills/verify-ticket-closure/SKILL.md` exactly and return one complete saturated semantic verdict for the immutable candidate. You may not repair, mutate, delegate, or ask the implementation parent to fill gaps. All evidence needed for semantic inspection is embedded below. Do not use tools.

BOUND DISPATCH IDENTITY
- Ticket: #315 — Translate relationship construction failures at the application boundary
- Mode: remediation
- Parent Spec: #279
- Remediation parent: Spec Review #310
- Root: RB-3 — Relationship-construction domain failures must cross the application-owned relationship error-translation boundary rather than leaking raw domain exceptions.
- Spec obligations: ID-26, TD-21
- Architecture obligations: None
- Ticket branch: spec-279
- Ticket baseline: {BASELINE}
- Candidate state: {CANDIDATE_STATE}
- Durable checkpoint: comment {CHECKPOINT_ID}, Stage awaiting-closure-verification, Attempt 1
- Ticket contract identity: issue #315 body SHA-256 {contract_identity}

MANDATORY VERIFIER METHOD
1. Recover and validate immutable contract, native parent #310, declared lineage, branch/baseline, checkpoint, root, parent coverage manifest, and bounded authority sources. Proposed Closure Evidence is only a claim set to challenge.
2. Before candidate/tests are proof, independently derive the bounded Authority Source Coverage Manifest and freeze one authority-first proof plan per material acceptance obligation.
3. Independently derive the bounded architecture/design obligations governing this failure-translation slice. Compare to parent Architecture/Design Obligation Manifest and `Architecture obligations: None`. #316/#317 separately own ARCHSRC-1/ARCHSRC-2; do not misclassify those as #315 obligations merely because the same module is adjacent. If current authority establishes another material #315 implementation obligation missing/misrouted from this ticket, return decomposition-defect FAIL with required fields.
4. Build one complete AC universe from every ticket build, acceptance, verification, preservation, negative-path requirement; applicable ID-26/TD-21 semantics; both active RB-3 cells; Root Invariant Sweep; and protected roots intersecting the candidate.
5. Explicitly challenge protected RB-2 because `relationships.py` is a shared surface and #314 established application-owned read-unavailability translation there. Determine from authority/diff whether RB-1 intersects; do not add it merely by proximity.
6. Independently close the three constructor-bearing application paths (renewal, Supersession, privileged correction) and the established relationship-domain failure translation family. Decide from durable authority whether these finite/discoverable domains materially contribute to PASS and therefore need Certified Closure Domain records.
7. Independently challenge the exact mapping families: definite cycle -> RelationshipCycle; contested possible-cycle -> RelationshipCycleSafetyIndeterminate; invalid/incomplete relationship history -> RelationshipHistoryInvalidOrIncomplete; InvalidDecisionTransition -> ConcurrencyConflict; remaining covered relationship admission/basis failures -> RelationshipConflict. Confirm constructor phase and downstream apply phase are both inside the same narrow catch without changing the mapped family.
8. Prove fail-closed behavior: no broad Exception catch; unrelated failures are not swallowed; constructor failures commit no history/receipt; success behavior, atomicity, replay/idempotency, endpoint-version/concurrency, relationship revalidation, persistence/read-unavailability semantics remain intact.
9. Independently challenge transition/consumer closure using repository scan + exact source. Shared symbol adjacency is not automatically a semantic consumer; classify actual callers/fakes/tests/current exports correctly.
10. Saturate all independent actionable findings before PASS or FAIL. The verifier is NON-MUTATING and NON-DELEGATING.

A PASS is legal only when every AC cell is proven, violated/unproven/unchecked are zero, all material nested domains are closed, every required Certified Closure Domain record is present, RB-3 is root-complete, protected roots are preserved, decomposition integrity is complete, and binding is exact.

If PASS, output EXACTLY the current skill PASS shape, plain text, no markdown fence and no prose before/after. `Ticket contract identity:` must be `issue #315 body SHA-256 {contract_identity}; checkpoint {CHECKPOINT_ID}`. Include every required certified-closure-domain record in full.
If FAIL, output EXACTLY the current skill FAIL shape, plain text, no markdown fence/prose before/after, with the complete saturated findings. Include decomposition-defect classification fields whenever applicable.
'''

    parts: list[str] = [instructions]
    for rel in [
        "AGENTS.md",
        ".agents/skills/verify-ticket-closure/SKILL.md",
        ".agents/skills/coding-standards/SKILL.md",
    ]:
        add_file(parts, transport, rel, "CURRENT MAIN AUTHORITY: " + rel)

    for label, content in [
        ("TICKET #315", ticket),
        ("NATIVE PARENT READBACK", parent),
        ("DURABLE CLOSURE CHECKPOINT", checkpoint),
        ("SPEC REVIEW #310", review),
        ("PARENT SPEC #279", spec),
        ("PARENT TICKET COVERAGE + ARCHITECTURE MANIFEST", coverage),
        ("FINDING CONTINUITY LEDGER", finding_ledger),
        ("DECOMPOSITION DEFECT RECORD", decomposition),
    ]:
        parts.extend([f"\n=== {label} ===\n", content])

    for rel in [
        "docs/proposed/application-use-cases-investment-decision-lifecycle.md",
        "docs/proposed/investment-decisions-decision-relationship-model.md",
        "docs/proposed/durable-persistence-investment-decision-history.md",
        "src/polaris/domain/decisions/relationships.py",
    ]:
        add_file(parts, candidate, rel, "GOVERNING SOURCE: " + rel)

    parts.append(
        "\n=== CANDIDATE / EVIDENCE — use only after authority-first proof plans are frozen ===\n"
    )
    parts.extend(["\n=== EXACT BASELINE-TO-CANDIDATE DIFF ===\n", diff])
    for rel in [
        "src/polaris/application/decisions/relationships.py",
        "src/polaris/application/decisions/contracts.py",
        "tests/application/decisions/test_relationships.py",
    ]:
        add_file(parts, candidate, rel)
    parts.extend(["\n=== FRESH REPOSITORY CONSUMER SCAN ===\n", scan])
    parts.extend(
        [
            "\n=== FRESH NON-MUTATING MECHANICAL/RUNTIME CHECKS ===\n",
            "\n".join(checks),
        ]
    )
    parts.extend(
        [
            "\n=== PRIOR FINAL CANDIDATE-BOUND VERIFY-CODE RECEIPT (supporting evidence only) ===\n",
            "Actions run 34935122636 job 104271275946: candidate state before/after "
            + CANDIDATE_STATE
            + "; exact two changed Python paths; diff hygiene PASS; Ruff fix/format and format/lint PASS; Mypy PASS; targeted relationship tests 26/26 PASS; complete architecture invariant suite 305/305 PASS; candidate unchanged. Mechanical contract-impact scan classified three behavior transitions; semantic completeness intentionally reserved for this verifier.\n",
        ]
    )

    prompt = "\n".join(parts)
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
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode

    verdict = proc.stdout.strip()
    (out_root / "verdict.txt").write_text(verdict + "\n", encoding="utf-8")
    (out_root / "candidate-state.txt").write_text(
        CANDIDATE_STATE + "\n", encoding="utf-8"
    )
    first = verdict.splitlines()[0] if verdict else ""
    if first not in {"TICKET CLOSURE: PASS", "TICKET CLOSURE: FAIL"}:
        print("INVALID VERIFIER OUTPUT")
        print(verdict)
        return 3
    required = [
        f"Ticket: #{TICKET}",
        "Mode: remediation",
        f"Ticket baseline: {BASELINE}",
        f"Candidate state: {CANDIDATE_STATE}",
    ]
    if any(item not in verdict for item in required):
        print("VERIFIER OUTPUT NOT CANDIDATE-BOUND")
        print(verdict)
        return 4
    if candidate_state(candidate) != CANDIDATE_STATE:
        print("VERIFIER CANDIDATE MUTATION DETECTED")
        return 5
    print("CLOSURE-VERDICT-BEGIN")
    print(verdict)
    print("CLOSURE-VERDICT-END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
