from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 279
REVIEW = 310
CANDIDATE_HEAD = "9081386b8fcbf65e117fdac6c7b8c776edaef8f0"


def run(*args: str, cwd: Path | None = None, input_text: str | None = None) -> str:
    p = subprocess.run(args, cwd=cwd, input=input_text, text=True, capture_output=True, check=False)
    if p.returncode:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        raise SystemExit(p.returncode)
    return p.stdout


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    ws = Path(os.environ["GITHUB_WORKSPACE"])
    candidate = ws / "candidate"
    root = Path(os.environ["RUNNER_TEMP"]) / f"to-tickets-310-draft-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    root.mkdir(parents=True)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as f:
        f.write(f"DRAFT_ROOT={root}\n")

    assert run("git", "rev-parse", "HEAD", cwd=candidate).strip() == CANDIDATE_HEAD

    spec = run("gh", "issue", "view", str(SPEC), "--repo", REPO, "--json", "number,title,body,state,comments,url", cwd=candidate)
    review = run("gh", "issue", "view", str(REVIEW), "--repo", REPO, "--json", "number,title,body,state,comments,url", cwd=candidate)
    ticket305 = run("gh", "issue", "view", "305", "--repo", REPO, "--json", "number,title,body,state,comments,url", cwd=candidate)
    ticket311 = run("gh", "issue", "view", "311", "--repo", REPO, "--json", "number,title,body,state,comments,url", cwd=candidate)

    instructions = r'''You are a fresh NON-CERTIFYING drafting helper for Polaris `$to-tickets`. You did not participate in the interrupted draft. Do not mutate anything. Do not certify proposal readiness. Your job is to independently reconstruct the complete semantic/accounting inputs that the parent will use to freeze a proposal for Spec Review #310 / parent Spec #279.

Authority rules:
- Follow the embedded current `$to-tickets` and `$to-remediation-tickets` skills exactly.
- The active ordinary remediation roots are RB-2/RF-1 and RB-3/RF-2 in Spec Review #310.
- The active decomposition-defect reports DD-1/RF-3 and DD-2/RF-4 are falsifier candidates. Independently validate them against the embedded architecture/design sources and existing #305 ticket before routing them.
- Closed tickets are historical evidence only and must never be reopened/rewritten.
- Preserve the exact 122-cell parent Spec contract from durable authority. Remediation Root Blocker universes remain authoritative for ordinary remediation tickets.
- Build the bounded Architecture/Design Obligation Disposition Manifest from the exact architecture/design sources materially required by this remediation and the parent Spec. Do not define completeness from proposed wording. When an architecture obligation is fully represented by a Spec cell, record that Spec-cell reference instead of inventing duplicate implementation responsibility.
- Material design choices delegated to implementation must be zero.
- New tickets use branch `spec-279` and baseline `Pending`.
- Native parent for new remediation tickets is Spec Review #310; parent Spec #279 is lifecycle/branch provenance.
- Run the logical `$attention` sensing pass over this transition and return every material signal with disposition. Attention does not change authority.

Return EXACTLY one JSON object and nothing else with this shape:
{
  "source_state": {"review":310,"parent_spec":279,"candidate_head":"...","mode":"remediation"},
  "decomposition_defects": [
    {"id":"DD-1","classification":"confirmed-decomposition-defect|rejected-no-decomposition-defect|unresolved-source-or-ownership","reason":"...","architecture_obligation":"ARCHSRC-N|None"},
    {"id":"DD-2",...}
  ],
  "root_delta": {
    "roots":[{"root":"RB-2","status":"open","remediation":["..."],"verification":["..."],"preservation":["..."],"root_complete_sweep":["..."]}, {"root":"RB-3",...}],
    "active_root_cells":0,"root_delta_rows":0,"missing_cells":0,"unknown_cells":0,"unclassified":0,"required_remediation_without_ticket":0,"satisfied_preservation_omitted":0
  },
  "architecture_manifest": {
    "bounded_sources":["path + exact section/anchor"],
    "rows":[{"id":"ARCHSRC-1","source":"...","requirement":"...","spec_cell_reference":"ID-X|None","disposition":"implementation-ticket|verification-only|deferred-existing-owner|not-applicable","destination":"T1|T2|T3|T4|$verify-spec|#existing-owner|None","reason":"..."}],
    "material_nonduplicated_obligations":0,"unmapped":0,"ambiguous":0,"implementation_without_ticket":0,"deferred_without_owner":0
  },
  "tickets":[
    {"key":"T1","title":"...","root_or_defect":"RB-2|RB-3|DD-1|DD-2","spec_obligations":["..."],"architecture_obligations":["ARCHSRC-N"],"blocked_by":["T1"],"architecture_context":"...","what_to_build":["..."],"acceptance":["..."],"verification":["..."],"preservation":["..."],"root_complete_sweep":["..."],"branch":"spec-279","baseline":"Pending","initial_ready_for_agent":true}
  ],
  "spec_coverage_delta":{"spec_cells":122,"mapped":122,"unmapped":0,"ambiguous":0,"material_design_choices_delegated":0,"new_or_changed_cell_mappings":[{"cell":"ID-24","tickets":["existing lineage","T1"],"reason":"..."}]},
  "attention":[{"signal":"...","severity":"high|medium|low","disposition":"...","mapped_to":"..."}],
  "proposal_notes":["..."]
}

Draft the SMALLEST root-complete four-ticket delta if current authority supports four separate tickets. If authority proves a different slicing is required, return that instead and explain. Do not use a historical count of architecture obligations as a target; independently derive the bounded source-unit universe and report the resulting count. Do not create broad dependency edges merely to serialize shared files: only declare a blocker when one ticket's semantic contract genuinely must exist before the other can be implemented correctly. New decomposition tickets may have `Spec obligations: None` when the missing requirement is architecture/design-only and the manifest proves no direct Spec cell represents it.
'''

    parts = [instructions, "\n=== SPEC #279 ===\n", spec, "\n=== SPEC REVIEW #310 ===\n", review, "\n=== CLOSED HISTORICAL TICKET #305 ===\n", ticket305, "\n=== CLOSED REMEDIATION TICKET #311 EXAMPLE ===\n", ticket311]
    for rel in [
        ".agents/skills/to-tickets/SKILL.md",
        ".agents/skills/to-remediation-tickets/SKILL.md",
        ".agents/skills/attention/SKILL.md",
        "docs/proposed/application-use-cases-investment-decision-lifecycle.md",
        "docs/proposed/investment-decisions-decision-relationship-model.md",
        "docs/proposed/durable-persistence-investment-decision-history.md",
        "docs/proposed/investment-decisions-lifecycle-model.md",
        "docs/proposed/investment-decisions-r2-foundation-public-contract.md",
        "docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md",
        "docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md",
        "docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md",
        "docs/adr/0004-platform-make-async-and-multi-core-execution-first-class.md",
        "src/polaris/application/decisions/contracts.py",
        "src/polaris/application/decisions/ordinary_work.py",
        "src/polaris/application/decisions/relationships.py",
        "tests/application/decisions/test_ordinary_work.py",
        "tests/application/decisions/test_relationships.py",
    ]:
        path = candidate / rel
        if path.exists():
            parts.extend([f"\n=== FILE: {rel} ===\n", read(path)])

    prompt = "\n".join(parts)
    result = subprocess.run([
        "copilot", "-s", "--no-custom-instructions", "--disable-builtin-mcps",
        "--deny-tool=shell,write,url,memory", "--no-ask-user", "--no-remote", "--no-remote-export"
    ], input=prompt, text=True, capture_output=True, check=False)
    if result.returncode:
        sys.stderr.write(result.stderr)
        return result.returncode
    out = root / "draft.json"
    out.write_text(result.stdout, encoding="utf-8")
    data = json.loads(result.stdout)
    assert data["source_state"]["candidate_head"] == CANDIDATE_HEAD
    assert data["source_state"]["review"] == REVIEW
    assert data["source_state"]["parent_spec"] == SPEC
    assert len(data["tickets"]) >= 1
    assert data["spec_coverage_delta"]["spec_cells"] == 122
    assert data["spec_coverage_delta"]["unmapped"] == 0
    assert data["spec_coverage_delta"]["ambiguous"] == 0
    assert data["spec_coverage_delta"]["material_design_choices_delegated"] == 0
    print("DRAFT-HELPER-RESULT-BEGIN")
    print(result.stdout)
    print("DRAFT-HELPER-RESULT-END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
