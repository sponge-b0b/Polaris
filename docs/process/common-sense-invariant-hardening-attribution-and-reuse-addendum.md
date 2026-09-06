# Change Attribution, Conditional Routing, and Review Reuse Hardening Addendum

**Status:** Active process hardening record  
**Date:** 2026-09-06  
**Governing record:** `docs/process/common-sense-invariant-hardening.md`

## Purpose

This addendum extends the common-sense invariant-hardening record with four generic transition invariants exposed by repeated Spec verification/review convergence failures.

The rules are deliberately source-agnostic. They do not name a particular Spec, file, tool, language, architecture test, or historical defect. Historical incidents are evidence for the invariant; they are not the vocabulary of the resulting workflow rule.

## 1. Change Provenance Is Not Semantic Ownership

> **Where a change appears in Git history does not establish which lifecycle artifact semantically owns that change.**

A branch/diff classifier may establish mechanical provenance such as branch-local, mixed-provenance, inherited-only, or unchanged/named. It may not infer `Spec-owned`, `ticket-owned`, or another semantic lifecycle owner from branch locality alone.

When semantic ownership/relevance authorizes a Standards finding, verification gate, repair, skip, or other consequential transition, the transition owner must disposition the complete provenance candidate universe against durable authority.

A generic attribution cell is:

```text
Candidate surface/change
Mechanical provenance
Relevant contract/authority
Semantic disposition: in-scope | out-of-scope | ambiguous
Evidence/reason
```

Rules:

* path names, directory classes, branch locality, commit authorship, and timing are evidence inputs, not semantic authority by themselves;
* `out-of-scope` is an explicit escape disposition and requires authority/evidence;
* `ambiguous` fails closed for the transition that depends on attribution;
* no filename or repository area is globally exempt: a lifecycle artifact may own any surface when its authoritative contract materially requires that change.

## 2. Verification Scope Must Be Authorized

> **A verification gate must execute over the smallest complete authoritative change/impact universe; broad repository scope is not the default substitute for scope construction.**

Before a gate can authorize PASS, repair, or exclusion, the transition owner must identify the gate's candidate scope and disposition it explicitly.

```text
Gate
Candidate surface/consumer
Scope disposition: target | excluded | unresolved
Authority/reason
```

Rules:

* changed implementation plus directly affected consumers form the ordinary starting universe;
* contract-impact discovery may broaden the target universe when unchanged consumers can observe the change;
* repository-wide execution is valid only when the active authoritative change itself is repository-wide or another explicit gate contract requires it;
* `.` or an equivalent whole-repository target must never be used merely because it is convenient;
* an observed failure remains in the failure universe until causally dispositioned even if a later authorized narrower rerun passes;
* a failure authorizes repair only when the active lifecycle contract owns the failed behavior/change. Branch provenance alone does not establish that relation.

This is a generic strengthening of Transition-Bound Reasoning, Observed Failure Disposition, and Semantic-First Cost Control.

## 3. Conditional Obligations Must Preserve Their Trigger and Destination

> **A conditional obligation may neither be strengthened into present work while its trigger is inactive nor disappear merely because the trigger has not fired yet.**

For every materially conditional Spec/planning obligation, preserve:

```text
Obligation
Condition/trigger
Current trigger state: active | inactive | ambiguous
Current responsibility
Deferred destination/owner when inactive
Disposition
```

Rules:

* only the authoritative source defines the trigger and consequent;
* an inactive trigger does not authorize inventing automation, infrastructure, policy, or pre-provisioning absent explicit authority;
* an inactive obligation may use a deferred/non-current disposition only when a durable future destination/owner is already established by authority;
* if the source requires future behavior but no durable destination can be established, routing remains unresolved rather than being silently forgotten or locally invented;
* when the trigger becomes active, the deferred disposition is stale and the receiving transition must evaluate the consequent normally.

This is an Explicit Escape Disposition and evidence-entailment rule, not a new global scheduler.

## 4. Review Proof Reuse Requires Certified Invalidation Boundaries

> **A completed clean review disposition may survive remediation only when the reviewer that certified it also established an invalidation boundary and deterministic delta analysis proves that boundary was not crossed.**

A reusable clean proof group records:

```text
Proof group
Axis
Cells
Disposition: checked-no-finding | not-applicable
Evidence identity/stability
Invalidation boundary
Reviewed HEAD / contract identity
```

On a later review:

```text
Prior proof group
Changed repository/authority/tracker surface set
Boundary intersection: zero | non-zero | ambiguous
Reuse state: reused | stale
```

Rules:

* missing or malformed prior proof state means full re-review for the affected universe;
* `ambiguous` intersection is `stale`;
* reused cells remain explicit members of the current review universe and count toward complete coverage; they do not disappear through omission;
* stale cells, active/root-remediation cells, and cells whose evidence/authority changed are re-reviewed;
* a later mutation does not force unrelated clean cells to be semantically rediscovered from zero;
* a previously clean unchanged cell cannot become a new current finding merely because a new reviewer chose a different interpretation when its certified proof object and invalidation boundary remain valid. Such a contradiction is process-integrity evidence about the prior certification rather than an automatic new remediation root.

This applies Certified Invalidation Boundaries to adversarial review without forbidding legitimate new findings on changed or previously uncertified surfaces.

## Earliest Enforcement Points

Apply these invariants locally at the transition owner:

* `$spec-contract` / its deterministic helper — mechanical change provenance only; never infer lifecycle ownership from Git position;
* `$verify-spec` — verification-scope authorization, causal failure disposition, and repair authority;
* `$to-tickets` — conditional/deferred obligation routing during decomposition;
* `$verify-spec-closure` — exact conditional claim entailment and inactive-trigger proof;
* `$review-spec` — semantic Standards attribution plus durable clean-proof invalidation/reuse.

Do not move these rules into one universal helper merely to centralize them. Each transition owner must consume the minimum state needed to make its own consequential transition non-bypassable.

## Non-Goals

This hardening does not:

* add path-specific allow/deny lists;
* exempt project configuration, workflow files, tests, or source code by filename;
* forbid repository-wide gates when the authoritative change is genuinely repository-wide;
* convert every conditional requirement into automation;
* prevent review from finding defects on stale/changed proof domains;
* permit old findings to disappear without explicit disposition;
* require full private reasoning transcripts.

The goal remains the minimum explicit, independently checkable state needed to distinguish provenance from authority, scope verification correctly, preserve conditional semantics, and make remediation reviews converge without hiding invalidated behavior.
