from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import urllib.request
from pathlib import Path

REPO = "sponge-b0b/Polaris"
SPEC = 279
REVIEW = 310
HEAD = "9cae0a1c6bbd5cddd93cfc368ff17b55d418e1b3"
BASELINE = "4daed9034891600597a47c01b6c39d5ebd9914ca"
BODY_HASH = "5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17"
CONTRACT_HASH = "3f3d291df51bde40d129f829c339b8cc7f2090a89be34d0c5d12e698aa8befe5"
BRANCH = "spec-279"
TIMESTAMP = "2026-09-12T13:51:00-06:00"
TOKEN = os.environ["GH_TOKEN"]


def api(method: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def post_comment(issue: int, body: str) -> dict:
    created = api("POST", f"issues/{issue}/comments", {"body": body})
    readback = api("GET", f"issues/comments/{created['id']}")
    assert readback["body"] == body, "comment readback mismatch"
    return created


def ranges(prefix: str, values: list[int]) -> list[str]:
    return [f"{prefix}-{value}" for value in values]


# Fail closed on mutable review bindings.
branch = api("GET", f"branches/{BRANCH}")
assert branch["commit"]["sha"] == HEAD, "spec-279 HEAD moved"
spec = api("GET", f"issues/{SPEC}")
assert hashlib.sha256(spec["body"].encode("utf-8")).hexdigest() == BODY_HASH, "Spec body changed"
comments = api("GET", f"issues/{REVIEW}/comments?per_page=100")
assert not any("## Pending Review Remediation" in item.get("body", "") for item in comments), "Pending packet already exists"
assert not any("<!-- review-spec-proof-reuse:v1 -->" in item.get("body", "") for item in comments), "Proof reuse ledger already exists"

# Import the repository-owned deterministic renderer rather than reimplementing it.
path = Path(".agents/skills/review-spec/scripts/review_spec_artifacts.py")
spec_module = importlib.util.spec_from_file_location("review_spec_artifacts", path)
assert spec_module is not None and spec_module.loader is not None
module = importlib.util.module_from_spec(spec_module)
spec_module.loader.exec_module(module)

finding = (
    "RB-1 — External Resolution contested-applicability veto contradicts the frozen R2 admission contract. "
    "At reviewed HEAD 9cae0a1c6bbd5cddd93cfc368ff17b55d418e1b3, "
    "`_require_external_resolution_admission()` rejects `DecisionApplicability.CONTESTED`, "
    "although Spec #279 US-21/ID-15/ID-16 and the governing application design make ordinary External Resolution depend on a determinately unresolved Need, not determinate operative applicability. "
    "The Decisions-domain transition likewise requires unresolved lifecycle plus `ExternalResolutionBasis` and has no applicability gate. "
    "Classification: Missed prior finding / in-domain falsifier of #303 certified ND-2; remediation uses existing authority and requires no architecture decision."
)

pending_input = {
    "head": HEAD,
    "baseline": BASELINE,
    "branch": BRANCH,
    "spec_body_hash": BODY_HASH,
    "spec_contract_hash": CONTRACT_HASH,
    "reviewer_execution": "same-agent-fallback-three-axis-passes",
    "reviewer_execution_override": (
        "Standing owner authorization in docs/process/session-reconstitution.md; "
        "separate sequential axis-isolated pass; reduced reviewer independence disclosed; "
        "no finding acceptance or suppression waived."
    ),
    "timestamp": TIMESTAMP,
    "standards": [],
    "spec": [finding],
    "architecture": [],
    "root_mappings": [
        "RB-1 -> Spec cells US-21, ID-15, ID-16 -> existing-authority remediation -> architecture decision required: No."
    ],
    "root_state": [
        "RB-1 open. Exact active member: External Resolution × determinately unresolved lifecycle × CONTESTED operative applicability. Seven sibling members in the frozen eight-member resolution-admission domain remain satisfied."
    ],
    "provenance": [
        "RB-1 is a Missed prior finding / in-domain-falsifier. Ticket #303 closure comment 5643082474 froze ND-2 as `{substantive, External} × {valid unresolved-operative, resolved, non-operative, contested}`. Authority is unchanged; membership is in-domain; the prior External×CONTESTED disposition was incorrect. Not regression, domain expansion, or closure-authority defect."
    ],
    "scope_corrections": [],
    "saturation": [
        "Required bounded convergence saturation over #303 ND-2: 8/8 generated, inspected, and dispositioned; 7 satisfied, 1 blocking (External × unresolved + CONTESTED); unchecked 0; no additional root or sibling finding."
    ],
    "coverage": {
        "standards": "17/17 provisional candidates dispositioned; 14 in-scope checked-no-finding; 3 synchronized main-owned policy/process candidates not-applicable; ambiguous 0; unchecked 0",
        "spec": "118/118 manifest cells dispositioned; blocking US-21, ID-15, ID-16; 103 checked-no-finding; OOS-1..OOS-12 not-applicable; unchecked 0",
        "architecture": "8/8 affected architecture cells checked-no-finding; unchecked 0",
        "saturation_challengers": 1,
    },
    "effectiveness": {"primary": 1, "targeted": 0, "saturation": 0},
}

pending = module.render_pending(pending_input)
pending_comment = post_comment(REVIEW, pending)

# Reviewer-certified proof-reuse cells. Blocking cells are intentionally excluded.
standards_in = ranges("STD-CAND", list(range(4, 18)))
standards_na = ranges("STD-CAND", [1, 2, 3])

spec_groups = [
    ("RPR-SPEC-1", "checked-no-finding", ranges("US", list(range(1, 10))) + ranges("ID", list(range(5, 11))) + ranges("TD", list(range(2, 9))),
     "Initiation/continuity application contracts, source/tests, and frozen initiation/continuity authority.",
     "Invalidated by a change to initiation/continuity command contracts or behavior, `contracts.py`/`initiation.py`/`test_initiation.py` evidence material to these cells, or their governing Spec/design authority."),
    ("RPR-SPEC-2", "checked-no-finding", ranges("US", list(range(10, 18))) + ["ID-14"] + ranges("TD", list(range(9, 13))),
     "Subject/Scope/Deferral/withdraw/resume application behavior and its frozen lifecycle/work authority.",
     "Invalidated by a material change to the non-resolution ordinary-work transitions, their tests, or governing Subject/Scope/Deferral/work-posture authority."),
    ("RPR-SPEC-3", "checked-no-finding", ["US-18", "US-19", "US-20", "ID-13", "TD-13"],
     "Trusted substantive-resolution basis/effect and hold/rejection behavior on the exact reviewed HEAD.",
     "Invalidated by a change to trusted Human Investment Decision basis/effect semantics, substantive-resolution admission/behavior, the cited resolution tests, or their governing authority."),
    ("RPR-SPEC-4", "checked-no-finding", ranges("US", list(range(22, 26))) + ["ID-17", "ID-19", "TD-16", "TD-17"],
     "Append-only lifecycle correction and unsupported-Need retraction source/tests plus frozen correction authority.",
     "Invalidated by a material change to lifecycle-correction contracts/implementation/tests or governing correction/support semantics."),
    ("RPR-SPEC-5", "checked-no-finding", ranges("US", list(range(26, 33))) + ["ID-18", "ID-20", "ID-21", "ID-22", "ID-23", "TD-18", "TD-19", "TD-20", "TD-28"],
     "Renewal/Supersession/relationship-correction orchestration and frozen relationship semantic domains.",
     "Invalidated by a material change to relationship command contracts/implementation/tests or governing relationship/admission/graph authority."),
    ("RPR-SPEC-6", "checked-no-finding", ranges("US", list(range(37, 43))) + ["ID-2", "ID-27", "TD-22", "TD-24"],
     "Decision Memory current/temporal/history/lineage query contracts and #306 frozen query domains.",
     "Invalidated by a material change to `memory.py`, query reader/view contracts, query tests, or governing Decision Memory/temporal authority."),
    ("RPR-SPEC-7", "checked-no-finding", ranges("US", [33, 34, 35, 36, 43, 44, 45]) + ranges("ID", [1, 3, 4, 11, 12, 24, 25, 26, 28, 29, 30, 31, 32]) + ranges("TD", [1, 14, 15, 21, 23, 25, 26, 27, 29]),
     "Cross-cutting command/provenance/idempotency/error/persistence-neutral/async/executor/application-boundary obligations across the exact reviewed package.",
     "Invalidated by a material change to shared application contracts/package exports, cross-family transaction/error/provenance behavior, ADR 0004 execution semantics, or governing cross-cutting Spec/architecture authority."),
    ("RPR-SPEC-8", "not-applicable", ranges("OOS", list(range(1, 13))),
     "Spec #279 originating Out-of-Scope clauses and durable Ticket Coverage authoritative exclusions.",
     "Invalidated by a Spec body/contract authority change that activates an excluded surface or by durable scope-routing authority that reclassifies one of OOS-1..OOS-12 for this Spec."),
]

arch_cells = ranges("ARCH", list(range(1, 9)))

all_spec_clean = set()
for _, _, cells, _, _ in spec_groups:
    assert not (all_spec_clean & set(cells)), "duplicate Spec proof-reuse cell"
    all_spec_clean.update(cells)
expected_spec_clean = (
    set(ranges("US", list(range(1, 46))))
    | set(ranges("ID", list(range(1, 33))))
    | set(ranges("TD", list(range(1, 30))))
    | set(ranges("OOS", list(range(1, 13))))
) - {"US-21", "ID-15", "ID-16"}
assert all_spec_clean == expected_spec_clean, f"Spec clean coverage mismatch: {sorted(expected_spec_clean ^ all_spec_clean)}"
assert len(standards_in) + len(standards_na) == 17
assert len(arch_cells) == 8
assert 17 + len(all_spec_clean) + 8 == 140

lines = [
    "<!-- review-spec-proof-reuse:v1 -->",
    "## Review Proof Reuse Ledger",
    "",
    f"**Reviewed HEAD:** {HEAD}",
    f"**Spec Body Hash:** {BODY_HASH}",
    f"**Spec Contract Hash:** {CONTRACT_HASH}",
    "**Clean/N/A cells:** 140",
    "**Proof-reuse cells:** 140",
    "**Missing clean/N/A cells:** 0",
    "**Duplicate proof-reuse cells:** 0",
    "**Proof groups without invalidation boundary:** 0",
    "",
]


def add_group(group_id: str, axis: str, cells: list[str], disposition: str, evidence: str, boundary: str, stability: str = "repository-immutable") -> None:
    lines.extend([
        f"### {group_id}",
        f"Axis: {axis}",
        f"Cells: {', '.join(cells)}",
        f"Disposition: {disposition}",
        f"Evidence identity: {evidence}",
        f"Evidence stability: {stability}",
        "Invalidation boundary:",
        f"- {boundary}",
        f"Reviewed HEAD: {HEAD}",
        f"Spec Body Hash: {BODY_HASH}",
        f"Spec Contract Hash: {CONTRACT_HASH}",
        "",
    ])

add_group(
    "RPR-STANDARDS-1", "Standards", standards_in, "checked-no-finding",
    "Exact reviewed Decisions application source/test candidates at HEAD plus current `$coding-standards` authority and semantic Spec attribution.",
    "Any material change to STD-CAND-04..17, the repository coding standards governing their reviewed predicates, or current-Spec semantic attribution invalidates the affected proof.",
)
add_group(
    "RPR-STANDARDS-2", "Standards", standards_na, "not-applicable",
    "AGENTS.md, `.agents/skills/implement-ticket/SKILL.md`, and `docs/process/session-reconstitution.md` are synchronized main-owned authority/integration ancestry, not #279-owned Standards work.",
    "Any content divergence attributable to #279, changed provenance establishing current-Spec ownership, or changed authority making one of these surfaces a #279 obligation invalidates this N/A proof.",
    "mutable",
)
for group in spec_groups:
    add_group(group[0], "Spec", group[2], group[1], group[3], group[4])
add_group(
    "RPR-ARCH-1", "Architecture", arch_cells, "checked-no-finding",
    "Current platform architecture/ADRs plus exact #279 application package: canonical application→domain direction, Decisions semantic ownership, inward ports, Governance trusted-basis seam, single application caller boundary, executor neutrality, and no platform-wide UoW.",
    "Any material change to reviewed application/domain boundary surfaces, affected architecture authority/ADRs/entity ownership, trusted authority seam, caller topology, executor contract, or transaction/UoW topology invalidates the affected architecture proof.",
    "mutable",
)

ledger = "\n".join(lines).rstrip() + "\n"
ledger_comment = post_comment(REVIEW, ledger)

print(json.dumps({
    "status": "PERSISTED",
    "pending_comment_id": pending_comment["id"],
    "pending_url": pending_comment["html_url"],
    "proof_reuse_comment_id": ledger_comment["id"],
    "proof_reuse_url": ledger_comment["html_url"],
    "clean_na_cells": 140,
    "blocking_cells": ["US-21", "ID-15", "ID-16"],
}, sort_keys=True))
