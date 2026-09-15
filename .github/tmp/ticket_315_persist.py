from __future__ import annotations

import json
import os
import subprocess

REPO = "sponge-b0b/Polaris"
COMMENT_ID = 5675531025
EXPECTED_STATE = "64ac0a239d7f472205063a45ae1d59b3815321f753afe67e8deb31658657b341"

VERDICT = r'''TICKET CLOSURE: PASS
Ticket: #315
Mode: remediation
Ticket baseline: 41bab9971d380b861cb7bbacd59ad2bdf5d9370f
Candidate state: 64ac0a239d7f472205063a45ae1d59b3815321f753afe67e8deb31658657b341
Ticket contract identity: issue #315 body SHA-256 9f7dc4d029dd851a4aabacb7e9ebbe6b4d068dabd4612c3d6b3292fb456d0765; checkpoint 5675531025
Acceptance: 18; proven 18; violated 0; unproven 0; unchecked 0
Proof plans: 18/18 authority-first; remaining composition/order seams 0
Nested domains: 3; closed 3; open 0
Domain construction: 3/3 complete; remaining authoritative members 0
Domain membership: 15; in-domain 11; out-of-domain 4; ambiguous 0
Certified closure domains: 3; frozen 3; unresolved 0
Production-path obligations: Renewal, Supersession, and privileged relationship-correction constructor/application paths all place construction and downstream application inside the established narrow `_RELATIONSHIP_ERRORS` translation boundary; renewal, multi-target Supersession, correction, commit, read, replay, and persistence paths remain wired through their existing application owners.
Negative/fail-closed obligations: Covered relationship-domain failures map to the established semantic application outcomes; definite cycles map to `RelationshipCycle`, contested possible cycles to `RelationshipCycleSafetyIndeterminate`, invalid/incomplete history to `RelationshipHistoryInvalidOrIncomplete`, `InvalidDecisionTransition` to `ConcurrencyConflict`, and remaining covered failures to `RelationshipConflict`. No broad `Exception` catch was added; unrelated failures remain visible; constructor failures commit no history or receipt.
Remediation root: RB-3 — Relationship-construction domain failures must cross the application-owned relationship error-translation boundary rather than leaking raw domain exceptions.
Protected roots: RB-2 preserved — shared relationship read/unavailability translation remains unchanged and command-side read failures remain application-owned.
Evidence: Immutable contract, native parent #310, parent Spec #279, checkpoint, branch/baseline, candidate binding, Finding Continuity Ledger RF-2, and parent coverage/architecture manifest reconciled with zero missing or ambiguous authority units. Bounded authority coverage is complete for ID-26, TD-21, RB-3's two active cells, preservation, negative-path, and verification obligations. Applicable material architecture/design obligations: 0; manifest rows covering applicable obligations: 0; missing, ambiguous, and misrouted obligations: 0; ticket architecture IDs missing from manifest mapping: 0; manifest implementation obligations absent from ticket contract: 0. Renewal, Supersession, and correction constructor domains are all closed. The established relationship error-family mapping is unchanged and complete. Fresh consumer scan classifies only the three application constructor-bearing paths as in-domain consumers; adjacent domain constructors, tests, and exports are out of domain for this ticket. Candidate-bound mechanical evidence reports exact two-file scope, clean diff, Ruff format/lint, Mypy, 26/26 targeted relationship tests, and 305/305 architecture invariant tests. Candidate state remained unchanged during final verification. Authority-first proof plans: 18/18. Required composition/order seams: 0 remaining. Generated, inspected, and dispositioned authoritative members: 11/11/11. Independent actionable findings: 0. Unexplored authoritative siblings: 0. Unproven material assumptions: 0.

<!-- certified-closure-domain:v1 -->
Certified Closure Domains:
- Certified Closure Domain: ND-315-1 — constructor-bearing application relationship paths
  Parent claim/root: AC-1, AC-2, AC-3, AC-14, RB-3
  Authority identity: Ticket #315 body SHA-256 9f7dc4d029dd851a4aabacb7e9ebbe6b4d068dabd4612c3d6b3292fb456d0765; checkpoint 5675531025; Spec #279 ID-26 and TD-21; Spec Review #310 RB-3; current `src/polaris/application/decisions/relationships.py`
  Membership predicate: An application production path is a member when it constructs a relationship fact or correction through `relationship_fact()` or `relationship_correction()` for renewal, Supersession, or privileged relationship correction under the RB-3 contract.
  Dimensions / authoritative source sets: `{renewal, Supersession, privileged relationship correction}` × `{relationship constructor, downstream relationship application}`; ticket #315 affected-surface list; current application relationship service implementations.
  Closure criterion: Finite authoritative enumeration of all three constructor-bearing application paths named by RB-3 and the ticket contract.
  Expected/generated/inspected/dispositioned: 3/3/3/3
  Material out-of-domain boundary observations: Domain-level `relationship_fact()` and `relationship_correction()` definitions are construction implementations, not additional application paths; tests and package exports are evidence/consumer surfaces, not production constructor owners.
  Finality: frozen-under-unchanged-authority

- Certified Closure Domain: ND-315-2 — established relationship-domain failure translation family
  Parent claim/root: AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, RB-3
  Authority identity: Ticket #315 acceptance and verification obligations; Spec #279 §16 Semantic outcomes; `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §16; `docs/proposed/durable-persistence-investment-decision-history.md` §16; current `_RELATIONSHIP_ERRORS` and `_raise_relationship_error` in `src/polaris/application/decisions/relationships.py`
  Membership predicate: A failure class is a member when it belongs to the established `_RELATIONSHIP_ERRORS` relationship-domain family and is eligible for application translation at the renewal, Supersession, or relationship-correction boundary.
  Dimensions / authoritative source sets: `{DecisionLifecycleLineageCycle, DecisionLifecycleLineageSafetyIndeterminate, InvalidDecisionRelationshipHistory, InvalidDecisionTransition, InvalidDecisionRelationshipBasis, DecisionRelationshipAdmissionRejected}` with established subclass-specific mapping precedence and fallback mapping.
  Closure criterion: Finite enumeration of every class in the application-owned `_RELATIONSHIP_ERRORS` tuple, with mapping disposition checked against the established semantic outcome family.
  Expected/generated/inspected/dispositioned: 6/6/6/6
  Material out-of-domain boundary observations: `DecisionCommandReadUnavailable`, persistence/store outcomes, `TypeError`, and unrelated `Exception` failures are not members of the relationship-domain translation family; they retain their existing owners and are not swallowed by the narrow catch.
  Finality: frozen-under-unchanged-authority

- Certified Closure Domain: ND-315-3 — RB-3 active root acceptance cells
  Parent claim/root: AC-15, AC-16, RB-3
  Authority identity: Spec Review #310 RB-3 active acceptance matrix; parent coverage manifest comment 5630203405; checkpoint 5675531025; Finding Continuity Ledger RF-2 comment 5662220111
  Membership predicate: A root cell is a member when it is one of the two active RB-3 acceptance cells explicitly carried by the remediation parent and mapped to ticket #315.
  Dimensions / authoritative source sets: `{renewal/Supersession relationship construction translation, relationship-correction construction translation}`; root ledger affected surfaces and exit checks.
  Closure criterion: Exact finite enumeration of both active RB-3 cells with missing, violated, unproven, and unchecked counts all zero.
  Expected/generated/inspected/dispositioned: 2/2/2/2
  Material out-of-domain boundary observations: RB-1 is satisfied and protected; RB-2 is satisfied and separately preserved; ARCHSRC-1 and ARCHSRC-2 are explicitly routed to #316 and #317 and are not #315 obligations.
  Finality: frozen-under-unchanged-authority'''


def gh_json(*args: str) -> dict:
    proc = subprocess.run(["gh", *args], check=True, text=True, capture_output=True)
    return json.loads(proc.stdout)


comment = gh_json("api", f"repos/{REPO}/issues/comments/{COMMENT_ID}")
body = comment["body"]
if f"**Candidate state:** {EXPECTED_STATE}" not in body:
    raise SystemExit("checkpoint candidate mismatch")
if "**Stage:** awaiting-closure-verification" not in body:
    raise SystemExit("checkpoint is not awaiting closure verification")
if "### Last verifier result\nNone" not in body:
    raise SystemExit("checkpoint last-verifier slot is not empty")

body = body.replace(
    "**Stage:** awaiting-closure-verification",
    "**Stage:** verifier-passed",
    1,
)
body = body.replace(
    "### Last verifier result\nNone",
    "### Last verifier result\n" + VERDICT,
    1,
)
body = body.replace(
    f"- Attempt 1 | {EXPECTED_STATE} | awaiting-verification | final candidate-bound implementation verification complete; fresh semantic certification pending",
    f"- Attempt 1 | {EXPECTED_STATE} | PASS | fresh independent `$verify-ticket-closure` certified exact candidate; acceptance 18/18; domains 3/3 frozen; RB-3 complete; RB-2 preserved",
    1,
)

payload = json.dumps({"body": body})
subprocess.run(
    ["gh", "api", "-X", "PATCH", f"repos/{REPO}/issues/comments/{COMMENT_ID}", "--input", "-"],
    input=payload,
    text=True,
    check=True,
    capture_output=True,
)
readback = gh_json("api", f"repos/{REPO}/issues/comments/{COMMENT_ID}")
if readback["body"] != body:
    raise SystemExit("checkpoint readback mismatch")
if "**Stage:** verifier-passed" not in body or VERDICT not in body:
    raise SystemExit("checkpoint verifier-passed binding incomplete")
print("CHECKPOINT_VERIFIER_PASS=PASS")
