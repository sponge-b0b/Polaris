from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 279
REVIEW = 310
CANDIDATE_HEAD = "9081386b8fcbf65e117fdac6c7b8c776edaef8f0"
BASELINE = "4daed9034891600597a47c01b6c39d5ebd9914ca"
PROPOSAL_SHA256 = "6ea20c4a3e858acd10520f80e05b268c8b32cfcd4565e25783a3546f3510b446"
SOURCE_STATE_SHA256 = "d2c05b8a6dd4d2e9ed17ddf376f81c94dab3549fdad2939b452c3c7179d6e8dc"


def run(*args: str, cwd: Path | None = None) -> str:
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if p.returncode:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit(p.returncode)
    return p.stdout


def gh_json(candidate: Path, *args: str) -> str:
    return run("gh", *args, cwd=candidate)


def add_file(parts: list[str], root: Path, rel: str, label: str | None = None) -> None:
    p = root / rel
    if p.exists():
        parts.extend([f"\n=== {label or ('FILE: ' + rel)} ===\n", p.read_text(encoding="utf-8")])


def main() -> int:
    ws = Path(os.environ["GITHUB_WORKSPACE"])
    transport = ws / "transport"
    candidate = ws / "candidate"
    out_root = Path(os.environ["RUNNER_TEMP"]) / f"to-tickets-310-certifier-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    out_root.mkdir(parents=True)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as f:
        f.write(f"CERT_ROOT={out_root}\n")

    proposal_path = transport / ".github/tmp/to_tickets_310_proposal.md"
    proposal = proposal_path.read_text(encoding="utf-8")
    assert hashlib.sha256(proposal.encode()).hexdigest() == PROPOSAL_SHA256
    assert run("git", "rev-parse", "HEAD", cwd=candidate).strip() == CANDIDATE_HEAD
    assert run("git", "branch", "--show-current", cwd=candidate).strip() == "spec-279"
    assert not run("git", "status", "--porcelain", cwd=candidate).strip()
    assert run("git", "merge-base", "--is-ancestor", BASELINE, "HEAD", cwd=candidate) == ""

    source_descriptor = (
        "Spec Review #310|Parent Spec #279|spec-279@" + CANDIDATE_HEAD
        + "|SpecBody=5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17"
        + "|SpecContract=3044b039742306f1c0ed10085479c7c823ed463443e8d11d761f45de564fb334"
        + "|FindingLedger=5662220111|DecompositionDefects=5663250943"
    )
    assert hashlib.sha256(source_descriptor.encode()).hexdigest() == SOURCE_STATE_SHA256

    inputs: list[tuple[str, str]] = []
    inputs.append(("SOURCE IDENTITY", source_descriptor))
    inputs.append(("FROZEN PROPOSAL", proposal))
    inputs.append(("SPEC REVIEW #310", gh_json(candidate, "issue", "view", "310", "--repo", REPO, "--json", "number,title,body,state,comments,url,labels")))
    inputs.append(("PARENT SPEC #279", gh_json(candidate, "issue", "view", "279", "--repo", REPO, "--json", "number,title,body,state,comments,url,labels")))
    inputs.append(("UPSTREAM SPEC #278", gh_json(candidate, "issue", "view", "278", "--repo", REPO, "--json", "number,title,body,state,url")))
    for issue in [301, 302, 303, 304, 305, 306, 311]:
        inputs.append((f"EXISTING TICKET #{issue}", gh_json(candidate, "issue", "view", str(issue), "--repo", REPO, "--json", "number,title,body,state,comments,url,labels")))
    for cid, label in [
        (5629965742, "WORKSPACE METADATA"),
        (5630203405, "HISTORICAL TICKET COVERAGE MANIFEST"),
        (5659536204, "122-CELL SPEC VERIFICATION RECEIPT"),
        (5662220111, "FINDING CONTINUITY LEDGER"),
        (5663250943, "CANONICAL DECOMPOSITION DEFECT RECORD"),
    ]:
        inputs.append((label, gh_json(candidate, "api", f"repos/{REPO}/issues/comments/{cid}")))
    inputs.append(("CURRENT OPEN ISSUE UNIVERSE", gh_json(candidate, "issue", "list", "--repo", REPO, "--state", "open", "--limit", "200", "--json", "number,title,body,url,labels")))
    inputs.append(("PRODUCT-BRANCH ADVANCE SINCE VERIFIED HEAD", run("git", "diff", "--name-status", "4baa54445e0bcd9f19bb75277a9abc84bea3008c..HEAD", cwd=candidate)))

    instructions = f'''You are the ONE genuinely fresh, non-mutating proposal-readiness certifier required by Polaris `$to-tickets` for the exact frozen Spec Review #310 remediation proposal embedded below. You did not draft, reconcile, transform, or review this proposal before this invocation.

You must independently validate the exact frozen proposal against the embedded CURRENT repository policy, durable tracker state, parent Spec contract, current unresolved Root Blocker acceptance universe, current decomposition-defect record, existing ticket lineage, and the bounded architecture/design sources. The drafting parent's claims inside the proposal are NOT authority.

BOUND IDENTITY:
- Source: Spec Review #310 / Parent Spec #279
- Mode: remediation
- Product branch candidate: spec-279@{CANDIDATE_HEAD}
- Parent Spec baseline: {BASELINE}
- Proposal identity: {PROPOSAL_SHA256}
- Source-state identity: {SOURCE_STATE_SHA256}

MANDATORY METHOD:
1. Follow the embedded current `.agents/skills/to-tickets/SKILL.md` Proposal Readiness Certification contract and `.agents/skills/to-remediation-tickets/SKILL.md` exactly.
2. Treat the 122-cell verification receipt as the exact parent Spec contract universe, not as proof that current remediation is complete.
3. Independently recover the current cumulative active Root Blocker cells from Spec Review #310. Verify the remediation/verification/preservation partition and every proposed ticket against those cells.
4. Independently validate DD-1 and DD-2 as falsifier candidates against the supplied architecture/design sources and historical ticket #305. Do not trust their proposed classification merely because the proposal says so.
5. Independently derive the bounded materially normative architecture/design source-unit universe for these four remediation slices. Check whether the proposed Architecture/Design Obligation Disposition Manifest is complete, whether any source obligation is duplicated by a Spec/root cell, whether any non-duplicated obligation is missing, and whether every implementation obligation is explicitly present in its ticket.
6. Validate the 122-cell parent coverage reconciliation, including NORM-1..4 and the changed ID-24/ID-26/TD-21 mappings. Do not invent new Spec cells for architecture-only defects.
7. Validate ticket bodies as publication-ready Review Remediation Tickets: direct parent #310, lifecycle provenance #279, branch `spec-279`, baseline `Pending`, label/status `ready-for-agent`, exact Spec/Architecture obligations, Root Blocker or decomposition-defect provenance, build/acceptance/verification/preservation/root-complete obligations, and no material implementation-delegated design choice.
8. Validate dependencies from semantics, not shared-file overlap. Confirm whether zero blocking edges among T1-T4 is correct.
9. Validate duplicate/conflicting coverage against the complete existing/open issue universe; closed historical tickets must not be reopened or rewritten.
10. Validate the `$attention` transition gate: every material signal is mapped/dispositioned and unresolved design-gap findings are zero.
11. Repository/process-only changes after the 122-cell verified product checkpoint may establish current workflow authority but do not by themselves erase durable open findings. Use the supplied current branch diff to determine whether product/source authority relevant to this proposal changed.
12. You are NON-MUTATING. Do not create/edit issues, comments, branches, files, dependencies, labels, or project fields. Do not delegate. Do not access any tools; all evidence is embedded.

A PASS is legal only if ALL of these are established:
Source implementation readiness: pass
Material design choices delegated to implementation: 0
Attention design-gap findings unresolved: 0
Source obligations/root cells complete: yes
Architecture/design obligation coverage complete: yes
Architecture/design obligations missing or ambiguous: 0
Proposal coverage complete: yes
Missing obligations/cells: 0
Ambiguous dispositions: 0
Unclassified dispositions: 0
Required remediation without ticket coverage: 0
Required preservation omitted: 0
Required verification omitted/misclassified: 0
Template/required fields valid: yes
Native parent/lineage valid: yes
Ticket branch semantics valid: yes
Ticket baseline semantics valid: yes
Label/status semantics valid: yes
Dependencies/blocking edges internally valid: yes
Closed tickets reopened/rewritten: 0
Duplicate/conflicting active ticket coverage: 0
Unresolved repository-policy conflicts: 0

If and only if every applicable check passes, output EXACTLY this shape, plain text, with no markdown fence and no text before/after:
TICKET PROPOSAL READINESS: PASS
Source: Spec Review #310 — Spec Review: Implement Investment Decision application lifecycle and Decision Memory queries
Mode: remediation
Proposal identity: {PROPOSAL_SHA256}
Design delegation: 0
Coverage: <n>/<n>; missing 0; ambiguous 0; unclassified 0
Mechanics: template/lineage/branch/baseline/status/dependencies valid
Repository-policy conflicts: 0
Human verification required: no

Otherwise output EXACTLY:
TICKET PROPOSAL READINESS: FAIL
Source: Spec Review #310 — Spec Review: Implement Investment Decision application lifecycle and Decision Memory queries
Mode: remediation
Proposal identity: {PROPOSAL_SHA256}
Findings:
1. <exact violated authority / affected proposal element / required correction>
...

The certifier does not repair the proposal. Do not soften a defect into advice. Do not fail merely because you prefer different wording or implementation shape when the frozen authority already determines the proposal semantics.
'''

    parts = [instructions]
    for label, content in inputs:
        parts.extend([f"\n=== {label} ===\n", content])

    for rel in [
        "AGENTS.md",
        ".agents/skills/to-tickets/SKILL.md",
        ".agents/skills/to-remediation-tickets/SKILL.md",
        ".agents/skills/attention/SKILL.md",
    ]:
        add_file(parts, transport, rel, "CURRENT MAIN AUTHORITY: " + rel)

    for rel in [
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
        "src/polaris/application/decisions/contracts.py",
        "src/polaris/application/decisions/ordinary_work.py",
        "src/polaris/application/decisions/relationships.py",
        "src/polaris/application/decisions/initiation.py",
        "src/polaris/application/decisions/lifecycle_correction.py",
        "tests/application/decisions/test_ordinary_work.py",
        "tests/application/decisions/test_relationships.py",
        "tests/application/decisions/test_initiation.py",
        "tests/application/decisions/test_lifecycle_correction.py",
    ]:
        add_file(parts, candidate, rel)

    prompt = "\n".join(parts)
    proc = subprocess.run([
        "copilot", "-s", "--no-custom-instructions", "--disable-builtin-mcps",
        "--deny-tool=shell,write,url,memory", "--no-ask-user", "--no-remote", "--no-remote-export"
    ], input=prompt, text=True, capture_output=True, check=False)
    if proc.returncode:
        sys.stderr.write(proc.stderr)
        return proc.returncode

    verdict = proc.stdout.strip()
    (out_root / "verdict.txt").write_text(verdict + "\n", encoding="utf-8")
    first = verdict.splitlines()[0] if verdict else ""
    if first not in {"TICKET PROPOSAL READINESS: PASS", "TICKET PROPOSAL READINESS: FAIL"}:
        print("INVALID CERTIFIER OUTPUT")
        print(verdict)
        return 3
    if f"Proposal identity: {PROPOSAL_SHA256}" not in verdict:
        print("CERTIFIER OUTPUT NOT PROPOSAL-BOUND")
        print(verdict)
        return 4
    print("CERTIFIER-VERDICT-BEGIN")
    print(verdict)
    print("CERTIFIER-VERDICT-END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
