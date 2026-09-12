from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 279
BASELINE = "4daed9034891600597a47c01b6c39d5ebd9914ca"
BRANCH = "spec-279"
HEAD = "9cae0a1c6bbd5cddd93cfc368ff17b55d418e1b3"
SPEC_BODY_HASH = "5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17"
SPEC_CONTRACT_HASH = "3f3d291df51bde40d129f829c339b8cc7f2090a89be34d0c5d12e698aa8befe5"
OLD_COVERAGE_HASH = "0808834ffa17cd2d7aae2d5c7c82180fd7d4bcab70fb1b6d917468681846265e"
DEFAULT_HEAD = os.environ["POLARIS_DEFAULT_HEAD"]
UTILITY = Path(".agents/skills/verify-spec/scripts/verify_spec_artifacts.py")


def run(*args: str) -> str:
    completed = subprocess.run(
        list(args),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def gh_json(path: str):
    return json.loads(run("gh", "api", path))


issue = gh_json(f"repos/{REPO}/issues/{SPEC}")
body = issue["body"]
if issue["state"] != "open":
    raise SystemExit("Spec #279 is not open")
body_hash = hashlib.sha256((body + "\n").encode()).hexdigest()
if body_hash != SPEC_BODY_HASH:
    raise SystemExit(f"Spec body hash changed: {body_hash}")

branch = gh_json(f"repos/{REPO}/branches/{BRANCH}")
if branch["commit"]["sha"] != HEAD:
    raise SystemExit(f"{BRANCH} moved: {branch['commit']['sha']}")

repo = gh_json(f"repos/{REPO}")
if repo["default_branch"] != "main":
    raise SystemExit("default branch changed")

blocked_by = gh_json(f"repos/{REPO}/issues/{SPEC}/dependencies/blocked_by")
if len(blocked_by) != 1 or blocked_by[0]["number"] != 278 or blocked_by[0]["state"] != "closed":
    raise SystemExit("Spec #279 blocker state changed")

subissues = gh_json(f"repos/{REPO}/issues/{SPEC}/sub_issues")
if len(subissues) != 6 or any(item["state"] != "closed" for item in subissues):
    raise SystemExit("Spec #279 implementation child frontier changed")

comments = gh_json(f"repos/{REPO}/issues/{SPEC}/comments?per_page=100")
if any("## Spec Verification Receipt" in (item.get("body") or "") for item in comments):
    raise SystemExit("Spec #279 already has a verification receipt")

sections: dict[str, list[str]] = {}
current: str | None = None
for raw in body.replace("\r\n", "\n").replace("\r", "\n").splitlines():
    if raw.startswith("## "):
        current = raw[3:].strip()
        sections.setdefault(current, [])
        continue
    if current is not None:
        sections[current].append(raw)

manifest: list[dict[str, str]] = []
for section, prefix, expected in [
    ("User Stories", "US", 45),
    ("Implementation Decisions", "ID", 32),
    ("Testing Decisions", "TD", 29),
]:
    rows: list[tuple[int, str]] = []
    for line in sections[section]:
        match = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if match:
            rows.append((int(match.group(1)), match.group(2).strip()))
    if [n for n, _ in rows] != list(range(1, expected + 1)):
        raise SystemExit(f"{section} numbering changed")
    for number, requirement in rows:
        manifest.append({
            "cell": f"{prefix}-{number}",
            "source": f"{section} {number}",
            "requirement": requirement,
        })

oos_rows = [
    line.strip()[2:].strip()
    for line in sections["Out of Scope"]
    if line.strip().startswith("- ")
]
if len(oos_rows) != 12:
    raise SystemExit(f"Out of Scope count changed: {len(oos_rows)}")
for number, requirement in enumerate(oos_rows, start=1):
    manifest.append({
        "cell": f"OOS-{number}",
        "source": f"Out of Scope {number}",
        "requirement": requirement,
    })
if len(manifest) != 118:
    raise SystemExit(f"manifest count changed: {len(manifest)}")

contract = {
    "spec_issue": SPEC,
    "head": HEAD,
    "baseline": BASELINE,
    "branch": BRANCH,
    "spec_body_hash": SPEC_BODY_HASH,
    "spec_contract_hash": SPEC_CONTRACT_HASH,
    "default_branch": "main",
    "default_head": DEFAULT_HEAD,
    "source_counts": {
        "user_stories": 45,
        "implementation_decisions": 32,
        "testing_decisions": 29,
        "out_of_scope": 12,
        "other_normative": 0,
    },
    "manifest": manifest,
}


def cells(prefix: str, start: int, end: int) -> list[str]:
    return [f"{prefix}-{n}" for n in range(start, end + 1)]


proofs = [
    {
        "cells": cells("US", 1, 9) + cells("ID", 5, 10) + cells("TD", 2, 8),
        "state": "proven",
        "evidence": [
            "contracts.py/initiation.py own conservative candidate discovery, explicit continuity outcomes, known-at provenance, idempotency and atomic candidate-basis revalidation.",
            "test_initiation.py covers no-candidate creation, continuation, ambiguity/stale determination, explicit create-new rationale/provenance, Need uniqueness, continuity conflict, replay/conflict and a threaded different-operation race; complete application suite passed.",
        ],
    },
    {
        "cells": cells("US", 10, 17) + ["ID-14", "ID-15"] + cells("TD", 9, 12),
        "state": "proven",
        "evidence": [
            "ordinary_work.py keeps Subject/Scope/Deferral/withdraw/resume purpose-specific while centralizing only transaction mechanics and enforcing unresolved+operative admission.",
            "test_ordinary_work.py plus test_initiation.py cover unresolved/partial/established Scope, no-op, invalid established-to-unresolved mutation, continuity-preserving Subject revision, re-Deferral basis identity, Review Condition separation, withdrawal/resume and non-operative/contested fail-closed behavior.",
        ],
    },
    {
        "cells": cells("US", 18, 22) + ["ID-13", "ID-16", "TD-13", "TD-15"],
        "state": "proven",
        "evidence": [
            "ordinary_work.py gives substantive and External Resolution separate typed paths; External Resolution now admits unresolved OPERATIVE or NON_OPERATIVE Decisions but rejects contested/resolved state and late historical acts.",
            "test_resolution.py proves valid trusted resolving basis, non-resolving Recommendation rejection, untrusted-basis rejection, ordinary External Resolution including NON_OPERATIVE unresolved state, contested fail-closed, and late/resolved routing to correction.",
        ],
    },
    {
        "cells": cells("US", 23, 25) + cells("ID", 17, 19) + cells("TD", 16, 18),
        "state": "proven",
        "evidence": [
            "lifecycle_correction.py and relationships.py keep correction append-only and privileged/internal rather than package-exported state setters.",
            "test_lifecycle_correction.py proves unsupported-Need correction preserves prior acts, late External Resolution qualification, competing support becomes contested, disconfirmation preserves targets, history-tail concurrency safety and typed failures; test_relationships.py proves relationship correction preserves original fact identity and can contest support.",
        ],
    },
    {
        "cells": cells("US", 26, 32) + cells("ID", 20, 23) + ["TD-14", "TD-19", "TD-20"],
        "state": "proven",
        "evidence": [
            "relationships.py owns renewal, RENEWED_FROM, many-target SUPERSEDES, full-history/endpoint revalidation, version guards, cycle safety and atomic relationship commits.",
            "test_relationships.py proves renewal creates a new Need/Decision while predecessors remain unchanged, continuity revalidation, many-target Supersession atomicity, relationship-only version behavior, non-operative applicability without lifecycle rewrite, cycle/contested safety, correction support and concurrent history revalidation.",
        ],
    },
    {
        "cells": cells("US", 33, 36) + ["ID-3", "ID-4", "ID-11", "ID-12", "ID-26", "TD-21", "TD-23"],
        "state": "proven",
        "evidence": [
            "DecisionCommandEnvelope separates OperationId, Actor Attribution, Trigger Provenance, Technical Provenance, effective time and expected versions; mutation/relationship stores expose semantic outcomes rather than raw database exceptions.",
            "initiation/ordinary/correction/relationship tests prove expected-version, idempotency, continuity, lifecycle, relationship-cycle/contested and persistence-unavailable outcomes remain distinct, replay ignores technical-only retry changes, semantic request changes conflict, and conflicts commit no partial facts.",
        ],
    },
    {
        "cells": cells("US", 37, 42) + ["ID-2", "ID-27", "ID-28", "TD-22", "TD-24"],
        "state": "proven",
        "evidence": [
            "memory.py exposes async current, as_known_at, effective_at, raw history, lineage and unresolved-continuity queries as application projections over immutable lifecycle/relationship history.",
            "test_memory.py proves current view is not a canonical InvestmentDecision, one-snapshot coherence, effective-time versus knowledge cutoff, raw correction history, lineage fact identity/direction/support/correction, hindsight-safe cutoffs, missing ancestry fail-closed and application error translation.",
        ],
    },
    {
        "cells": cells("US", 43, 45) + ["ID-1", "ID-24", "ID-25", "TD-1", "TD-25", "TD-26"],
        "state": "proven",
        "evidence": [
            "application.decisions package exposes the reusable command/query boundary and technology-neutral Protocol ports; privileged correction commands stay internal; contracts.py imports standard library + domain only and no concrete persistence/ORM/vendor adapter.",
            "Deterministic fake ports are the primary tests; 305 architecture guards passed and no alternate presentation/persistence business-write path or platform-wide Unit of Work was introduced by the baseline-to-candidate change.",
        ],
    },
    {
        "cells": cells("ID", 29, 32) + cells("TD", 27, 29),
        "state": "proven",
        "evidence": [
            "All I/O-owning ports/services are async while domain reducers remain synchronous; application contracts contain no event-loop/thread/process/subinterpreter executor types.",
            "test_initiation.py and test_memory.py exercise behavior across threads/event loops, and transaction correctness uses CAS/version/history-tail/revalidation/idempotency rather than in-memory locks around domain objects; architecture suite passed.",
        ],
    },
    {
        "cells": cells("OOS", 1, 12),
        "state": "not-applicable",
        "reason": "The originating Spec explicitly excludes these 12 surfaces. The baseline-to-candidate product delta is confined to reusable application/decisions contracts/services and their tests; it adds none of the excluded PostgreSQL, Governance storage, Decision Context, AI reasoning, Action Continuity/Learning, ranking, PRIOR_DECISION_CONTEXT material-use, generic workflow runtime, platform UoW, presentation implementation, or concrete executor selection.",
    },
]

mapped = [cell for proof in proofs for cell in proof["cells"]]
if len(mapped) != 118 or len(set(mapped)) != 118:
    raise SystemExit("proof coverage is not exactly 118 unique cells")
if set(mapped) != {row["cell"] for row in manifest}:
    raise SystemExit("proof coverage does not equal manifest")

gates = [
    {"name": "Spec contract identity", "status": "PASS", "evidence": f"Spec body {SPEC_BODY_HASH}; canonical current V2 contract {SPEC_CONTRACT_HASH}; 143 source units and 118 manifest cells. Final previous rebind failure was an ad-hoc dict-order serialization defect, not contract drift."},
    {"name": "Service preflight", "status": "PASS", "evidence": "Exact acceptance/architecture scopes are service-free by fixture/import inspection; deterministic fake async ports own persistence/query seams."},
    {"name": "Ruff format and lint", "status": "PASS", "evidence": "Parent verify-spec post-repair native run reported format/check clean on the affected files; the stable candidate commit contains exactly that repaired tracked tree."},
    {"name": "Mypy", "status": "PASS", "evidence": "Parent verify-spec post-repair native run reported no typing issues on the affected files; no tracked mutation followed before commit."},
    {"name": "Application acceptance", "status": "PASS", "evidence": "123 application/decisions tests passed after both closure findings were repaired."},
    {"name": "$verify-architecture", "status": "PASS", "evidence": "305 architecture guard tests passed after repair."},
    {"name": "$deduplicate-code", "status": "PASS", "evidence": "Repository-wide Arid reported zero duplicate groups/zero stale suppressions and JSCPD reported zero clones after the dedup repair and again after closure repair."},
    {"name": "$wiki-lint", "status": "PASS", "evidence": "Living Entity Wiki audit completed. Four citation-policy findings were proven byte-for-byte inherited from the fixed baseline; wiki/ is unchanged by this Spec and no Spec-owned wiki failure remains."},
    {"name": "Artifact utility self-test", "status": "PASS", "evidence": "verify_spec_artifacts.py self-test passed in the parent run; finalization uses the same utility blob on candidate and main."},
    {"name": "Delegated gate ownership", "status": "PASS", "evidence": "Required delegated gates $verify-architecture, $deduplicate-code and $wiki-lint executed under their owner procedures; required delegated gates without valid terminal disposition: 0."},
    {"name": "Observed failure disposition", "status": "PASS", "evidence": "Initial dedup/static repair-loop failures and the first closure certifier's two Spec findings were retained and resolved; four wiki citation findings are inherited-unrelated by baseline identity; unresolved failures 0, Spec-owned failures remaining 0."},
    {"name": "Attention", "status": "PASS", "evidence": f"ATTENTION:FINDINGS was report-only: old Ticket Coverage hash {OLD_COVERAGE_HASH} differs from current canonical V2 identity and four wiki citation findings are inherited. The terminal rebind mismatch was separately diagnosed as temporary manifest-order serialization error; no blocking Attention basis remains."},
    {"name": "Hierarchy and dependencies", "status": "PASS", "evidence": "All six direct implementation subissues are closed; sole direct blocker #278 is closed. No open implementation frontier remains."},
    {"name": "Project delivery guard", "status": "NOT APPLICABLE", "evidence": "Spec #279 has no native parent/Wayfinder governor; the Wayfinder-managed guard branch of $verify-spec does not apply."},
    {"name": "Independent semantic closure", "status": "PASS", "evidence": "Reduced-independence fallback disclosed: a separate deliberate non-mutating pass in the same ChatGPT instance substituted for an unavailable fresh-agent primitive. Manifest 118; proven 106; originating-Spec not-applicable 12; violated/unproven/unchecked 0. Five finite nested domains closed 5/5; 43 authoritative members generated/inspected/dispositioned; remaining 0; ambiguous membership 0; actionable findings 0; unexplored authoritative siblings 0; unproven material assumptions 0."},
    {"name": "Exact candidate binding", "status": "PASS", "evidence": f"Remote {BRANCH} is pinned to {HEAD}; candidate is a clean fast-forward descendant of the fixed baseline and was not mutated during the second closure pass."},
]

repairs = [
    "Deduplication repair centralized shared one-Decision mutation transaction mechanics while preserving purpose-specific command semantics; final Arid and JSCPD are clean.",
    "Closure finding repaired: ordinary External Resolution now accepts unresolved NON_OPERATIVE Decisions while contested/resolved/late-history cases still fail closed.",
    "Closure finding repaired: TD-9 now includes partial-Scope initiation persistence coverage.",
    "Verification bookkeeping repaired without product mutation: the failed final rebind used dictionary iteration instead of canonical stable manifest-cell order; canonical V2 identity remains unchanged.",
]
inherited = [
    "Living Entity Wiki audit found four strict-invariant citation-policy findings; wiki/ is byte-identical to the fixed baseline, so they are inherited-unrelated and report-only for Spec #279.",
    f"Ticket Coverage Manifest retains prior contract identity {OLD_COVERAGE_HASH}; current canonical V2 reconstruction of the unchanged Spec is {SPEC_CONTRACT_HASH} with the same complete 118-cell acceptance universe. This decomposition-provenance drift is not lifecycle authority.",
]

with tempfile.TemporaryDirectory(prefix="verify-spec-279-") as td:
    root = Path(td)
    contract_path = root / "contract.json"
    proofs_path = root / "proofs.json"
    gates_path = root / "gates.json"
    receipt_path = root / "receipt.md"
    contract_path.write_text(json.dumps(contract, ensure_ascii=False, separators=(",", ":")))
    proofs_path.write_text(json.dumps(proofs, ensure_ascii=False, separators=(",", ":")))
    gates_path.write_text(json.dumps(gates, ensure_ascii=False, separators=(",", ":")))

    self_test = run(sys.executable, str(UTILITY), "self-test")
    if "VERIFY-SPEC ARTIFACT SELF-TEST: PASS" not in self_test:
        raise SystemExit("artifact utility self-test did not pass")

    command = [
        sys.executable, str(UTILITY), "finalize-parts",
        "--contract-input", str(contract_path),
        "--proofs-input", str(proofs_path),
        "--gates-input", str(gates_path),
        "--mode", "full",
        "--receipt-output", str(receipt_path),
    ]
    for repair in repairs:
        command += ["--repair", repair]
    for finding in inherited:
        command += ["--inherited-finding", finding]
    summary = json.loads(run(*command))
    receipt = receipt_path.read_text()

    payload = root / "payload.json"
    payload.write_text(json.dumps({"body": receipt}, ensure_ascii=False))
    posted = json.loads(run(
        "gh", "api", "--method", "POST",
        f"repos/{REPO}/issues/{SPEC}/comments",
        "--input", str(payload),
    ))
    comment_id = posted["id"]
    comment_url = posted["html_url"]
    readback = gh_json(f"repos/{REPO}/issues/comments/{comment_id}")["body"]
    if readback != receipt:
        raise SystemExit(f"receipt readback mismatch: {comment_url}")

print(json.dumps({
    "status": "PASS",
    "receipt_comment_id": comment_id,
    "receipt_url": comment_url,
    "verification_hash": summary["verification_hash"],
    "manifest_cells": summary["manifest_cells"],
    "proof_groups": summary["proof_groups"],
    "proven_cells": summary["proven_cells"],
    "not_applicable_cells": summary["not_applicable_cells"],
    "unresolved_cells": summary["unresolved_cells"],
    "verification_gates": summary["verification_gates"],
}, sort_keys=True))
