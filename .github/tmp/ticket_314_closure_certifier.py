from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
TICKET = 314
SPEC = 279
REVIEW = 310
BASELINE = "9081386b8fcbf65e117fdac6c7b8c776edaef8f0"
CANDIDATE_STATE = "3f086c624e0164e7a25ea1201bdf858b7ccbcac8a36208dd62410cde3230fc44"
CHECKPOINT_ID = 5675170405
CHANGED = [
    "src/polaris/application/decisions/__init__.py",
    "src/polaris/application/decisions/contracts.py",
    "src/polaris/application/decisions/initiation.py",
    "src/polaris/application/decisions/ordinary_work.py",
    "src/polaris/application/decisions/relationships.py",
    "tests/application/decisions/test_initiation.py",
    "tests/application/decisions/test_ordinary_work.py",
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
        "DecisionCommandReadUnavailable",
        "find_unresolved_continuity_candidates",
        "get_initiation_receipt",
        "get_mutation_receipt",
        "load_decision_for_command",
        "get_relationship_receipt",
        "load_relationship_state",
    )
    rows: list[str] = []
    for base in (candidate / "src", candidate / "tests"):
        for path in base.rglob("*.py"):
            rel = path.relative_to(candidate)
            if "legacy" in rel.parts or ".venv" in rel.parts:
                continue
            text = path.read_text()
            matches = sorted(needle for needle in needles if needle in text)
            if matches:
                rows.append(f"{rel}: {', '.join(matches)}")
    return "\n".join(sorted(rows))


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    transport = workspace / "transport"
    candidate = workspace / "candidate"
    out_root = Path(os.environ["RUNNER_TEMP"]) / (
        f"ticket-314-closure-certifier-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    )
    out_root.mkdir(parents=True, exist_ok=True)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as handle:
        handle.write(f"CERT_ROOT={out_root}\n")

    if run("git", "rev-parse", "HEAD", cwd=candidate).strip() != BASELINE:
        raise SystemExit("candidate checkout is not pinned ticket baseline")
    if run("git", "status", "--porcelain", cwd=candidate).strip():
        raise SystemExit("candidate checkout dirty before reconstruction")

    env = {"CANDIDATE_ROOT": str(candidate)}
    run("python", ".github/tmp/implement_314_candidate.py", cwd=transport, env=env)
    run("python", ".github/tmp/implement_314_refactor.py", cwd=transport, env=env)
    run("uv", "run", "--locked", "ruff", "format", *CHANGED, cwd=candidate)
    state = candidate_state(candidate)
    if state != CANDIDATE_STATE:
        raise SystemExit(f"candidate state mismatch: {state}")

    # Fresh, non-mutating mechanical/runtime evidence for the fresh semantic verifier.
    checks: list[str] = []
    checks.append("git diff --check:\n" + run("git", "diff", "--check", BASELINE, cwd=candidate))
    checks.append("ruff format --check:\n" + run("uv", "run", "--locked", "ruff", "format", "--check", *CHANGED, cwd=candidate))
    checks.append("ruff check:\n" + run("uv", "run", "--locked", "ruff", "check", *CHANGED, cwd=candidate))
    checks.append(
        "mypy:\n"
        + run(
            "uv", "run", "--locked", "mypy", "--explicit-package-bases",
            *CHANGED,
            "tests/application/decisions/test_lifecycle_correction.py",
            cwd=candidate,
        )
    )
    checks.append(
        "decision application + protected boundary pytest:\n"
        + run(
            "uv", "run", "--locked", "pytest", "-q",
            "tests/application/decisions/test_initiation.py",
            "tests/application/decisions/test_ordinary_work.py",
            "tests/application/decisions/test_relationships.py",
            "tests/application/decisions/test_lifecycle_correction.py",
            "tests/application/decisions/test_resolution.py",
            "tests/application/decisions/test_memory.py",
            cwd=candidate,
            env={"UV_CACHE_DIR": "/tmp/uv-cache"},
        )
    )
    checks.append(
        "complete architecture invariant pytest:\n"
        + run(
            "uv", "run", "--locked", "pytest", "-q",
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

    ticket = gh(candidate, "issue", "view", str(TICKET), "--repo", REPO, "--json", "number,title,body,state,url,labels")
    review = gh(candidate, "issue", "view", str(REVIEW), "--repo", REPO, "--json", "number,title,body,state,url,labels")
    spec = gh(candidate, "issue", "view", str(SPEC), "--repo", REPO, "--json", "number,title,body,state,url,labels")
    checkpoint = gh(candidate, "api", f"repos/{REPO}/issues/comments/{CHECKPOINT_ID}")
    coverage = gh(candidate, "api", f"repos/{REPO}/issues/comments/5630203405")
    finding_ledger = gh(candidate, "api", f"repos/{REPO}/issues/comments/5662220111")
    decomposition = gh(candidate, "api", f"repos/{REPO}/issues/comments/5663250943")
    workspace_metadata = gh(candidate, "api", f"repos/{REPO}/issues/comments/5629965742")
    ticket_json = json.loads(ticket)
    contract_identity = hashlib.sha256(ticket_json["body"].encode()).hexdigest()
    diff = run("git", "diff", "--no-renames", BASELINE, "--", cwd=candidate)
    scan = consumer_scan(candidate)

    instructions = f'''You are the ONE genuinely fresh, non-mutating `$verify-ticket-closure` verifier for Polaris ticket #314. You did not implement, draft, reconcile, review, or certify this candidate before this invocation. The implementation parent is in dispatcher-only mode.

Execute the embedded CURRENT `.agents/skills/verify-ticket-closure/SKILL.md` exactly and return one complete saturated semantic verdict for the immutable candidate. You may not repair, mutate, delegate, or ask the implementation parent to fill gaps. All evidence needed for semantic inspection is embedded below. Do not use tools.

BOUND DISPATCH IDENTITY
- Ticket: #314 — Define application-owned command-side read failure semantics
- Mode: remediation
- Parent Spec: #279
- Remediation parent: Spec Review #310
- Root: RB-2 — Command-side persistence reads must expose a technology-neutral application-owned persistence-failure contract so raw infrastructure failures cannot escape the application boundary.
- Spec obligations: ID-24, ID-26, TD-21
- Architecture obligations: None
- Ticket branch: spec-279
- Ticket baseline: {BASELINE}
- Candidate state: {CANDIDATE_STATE}
- Durable checkpoint: comment {CHECKPOINT_ID}, Stage awaiting-closure-verification, Attempt 1
- Ticket contract identity: issue #314 body SHA-256 {contract_identity}

MANDATORY VERIFIER METHOD
1. First recover and validate the immutable contract, lineage, baseline, checkpoint, root, parent coverage manifest, and bounded authority sources. Treat Proposed Closure Evidence only as claims to challenge.
2. Before using candidate implementation or tests as proof, derive the complete bounded Authority Source Coverage Manifest and independently freeze the authority-first proof plan for every material acceptance obligation. Do not let implementation shape define the universe.
3. Independently derive the bounded architecture/design source set materially governing this ticket. Compare it to the parent Architecture/Design Obligation Manifest and `Architecture obligations: None`. If a material implementation obligation is missing/misrouted, return a decomposition-defect FAIL exactly as the skill requires.
4. Build one authoritative AC-* universe from all explicit ticket build/acceptance/verification/preservation/negative-path obligations; carried Spec ID-24/ID-26/TD-21 semantics applicable to this slice; both active RB-2 cells; Root Invariant Sweep; same-root preservation; and every protected previously-satisfied root whose governed contract intersects the candidate.
5. Explicitly challenge RB-1 preservation because `ordinary_work.py` is shared.
6. Close every finite/discoverable semantic domain from durable authority. Independently decide whether the command-side read-port universe is finite/discoverable and whether a Certified Closure Domain record is required. Do not copy the implementation parent's six-method interpretation without checking authority/current ownership.
7. Independently challenge transition/consumer closure. The parent manifest and fresh repository scan below are evidence only. Determine whether any current caller, implementation, protocol extension, adapter seam, fake/fixture, test, or composition path is omitted. Classify `memory.py` correctly.
8. Prove negative/fail-closed behavior: typed inward read unavailability maps to outward `PersistenceUnavailable`; `None`/not-found stays distinct; unrelated exceptions are not swallowed; failed reads commit no partial mutation/receipt; raw vendor/database exceptions are not caught inward; commit/concurrency/idempotency/lifecycle/relationship families remain distinct.
9. Saturate independent actionable findings before PASS or FAIL. A partial sweep is invalid. Decomposition defects must be explicitly classified and owned by `$to-tickets`.
10. You are NON-MUTATING and NON-DELEGATING. Do not create/edit files, issues, comments, branches, labels, commits, or project state. Do not call tools.

A PASS is legal only when every required AC cell is proven, violated/unproven/unchecked are zero, all required nested/domain construction is closed, every required Certified Closure Domain record is included, production/negative paths are proven, RB-2 is root-complete, RB-1 has no regression, decomposition integrity is complete, and candidate binding is exact.

If PASS, output EXACTLY the current skill's PASS shape, plain text, no markdown fence and no prose before or after. `Ticket contract identity:` must be `issue #314 body SHA-256 {contract_identity}; checkpoint {CHECKPOINT_ID}`. Include every required `<!-- certified-closure-domain:v1 -->` record in full.

If FAIL, output EXACTLY the current skill's FAIL shape, plain text, no markdown fence and no prose before or after. Include the complete saturated finding set. If any finding is a decomposition defect, include its required classification/owner/source/missing-or-misrouted/current-manifest fields.

Do not output PASS merely because tests are green. Do not output FAIL merely because you prefer a different private implementation mechanic when durable authority establishes equivalent semantics.
'''

    parts: list[str] = [instructions]
    for rel in [
        "AGENTS.md",
        ".agents/skills/verify-ticket-closure/SKILL.md",
        ".agents/skills/coding-standards/SKILL.md",
    ]:
        add_file(parts, transport, rel, "CURRENT MAIN AUTHORITY: " + rel)

    for label, content in [
        ("TICKET #314", ticket),
        ("DURABLE CLOSURE CHECKPOINT", checkpoint),
        ("SPEC REVIEW #310", review),
        ("PARENT SPEC #279", spec),
        ("PARENT TICKET COVERAGE + ARCHITECTURE MANIFEST", coverage),
        ("FINDING CONTINUITY LEDGER", finding_ledger),
        ("DECOMPOSITION DEFECT RECORD", decomposition),
        ("SPEC WORKSPACE METADATA", workspace_metadata),
    ]:
        parts.extend([f"\n=== {label} ===\n", content])

    for rel in [
        "docs/current/platform-architecture-0.2.0.md",
        "docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md",
        "docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md",
        "docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md",
        "docs/proposed/application-use-cases-investment-decision-lifecycle.md",
        "docs/proposed/durable-persistence-investment-decision-history.md",
    ]:
        add_file(parts, candidate, rel, "GOVERNING SOURCE: " + rel)

    parts.append("\n=== CANDIDATE / EVIDENCE — use only after authority-first proof plans are frozen ===\n")
    parts.extend(["\n=== EXACT BASELINE-TO-CANDIDATE DIFF ===\n", diff])
    for rel in [
        "src/polaris/application/decisions/__init__.py",
        "src/polaris/application/decisions/contracts.py",
        "src/polaris/application/decisions/initiation.py",
        "src/polaris/application/decisions/memory.py",
        "src/polaris/application/decisions/ordinary_work.py",
        "src/polaris/application/decisions/relationships.py",
        "src/polaris/application/decisions/lifecycle_correction.py",
        "tests/application/decisions/test_initiation.py",
        "tests/application/decisions/test_ordinary_work.py",
        "tests/application/decisions/test_relationships.py",
        "tests/application/decisions/test_lifecycle_correction.py",
        "tests/application/decisions/test_resolution.py",
        "tests/application/decisions/test_memory.py",
    ]:
        add_file(parts, candidate, rel)
    parts.extend(["\n=== FRESH REPOSITORY CONSUMER SCAN ===\n", scan])
    parts.extend(["\n=== FRESH NON-MUTATING MECHANICAL/RUNTIME CHECKS ===\n", "\n".join(checks)])
    parts.extend([
        "\n=== PRIOR FINAL CANDIDATE-BOUND VERIFY-CODE RECEIPT (supporting evidence only) ===\n",
        "Actions run 34932161452 job 104262458252: candidate state before/after "
        + CANDIDATE_STATE
        + "; diff hygiene PASS; Ruff format/lint PASS; Mypy PASS; targeted Decision application tests 98/98 PASS; complete architecture invariant suite 305/305 PASS; contract transition 3/3 classified; consumer closure 12/12 dispositioned; candidate unchanged.\n",
    ])

    prompt = "\n".join(parts)
    proc = subprocess.run(
        [
            "copilot", "-s", "--no-custom-instructions", "--disable-builtin-mcps",
            "--deny-tool=shell,write,url,memory", "--no-ask-user", "--no-remote", "--no-remote-export",
        ],
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode:
        sys.stderr.write(proc.stderr)
        return proc.returncode

    verdict = proc.stdout.strip()
    (out_root / "verdict.txt").write_text(verdict + "\n", encoding="utf-8")
    (out_root / "candidate-state.txt").write_text(CANDIDATE_STATE + "\n", encoding="utf-8")
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
