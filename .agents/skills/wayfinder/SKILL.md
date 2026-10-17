---
name: wayfinder
description: Plan a large, decision-heavy body of work as a durable map and resolve one semantic decision at a time until downstream work is clear.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Wayfinder

Wayfinder is the planning workflow for work whose destination is clear enough to pursue but
whose route still contains multiple or coupled material decisions.

For material software decisions, the Canonical Contract Ledger (CCL) is the frozen semantic
output. Decision-analysis prose explains the choice; it is not a second semantic contract.

## Session independence

Recover correctness-critical state from the invocation, repository, issue tracker, active
architecture, CCL, and durable workflow artifacts. Chat/session summaries are context only.

## Modes

### Chart the Map

Use when a destination still contains material planning fog. Charting may define destination
and boundaries, create the canonical `wayfinder:map`, create currently specifiable
research/prototype/decision/task tickets, wire genuine semantic dependencies, and preserve
not-yet-specifiable fog.

Charting is planning and does not establish/switch project delivery focus.

### Work Through the Map

Use when the human supplies a Wayfinder map or decision ticket. Resolve at most one
non-research decision ticket per human session.

## Project delivery guard

Before substantive work on an existing map:

1. resolve the exact governing Wayfinder;
2. invoke `$project-delivery-management reconcile`;
3. invoke `guard <Wayfinder>`;
4. require exact `PROJECT DELIVERY GUARD: ALLOWED` before claiming/mutating a decision.

Never switch or broaden focus automatically.

## Map model

The map is one issue labelled `wayfinder:map` with:

```markdown
## Destination
<completion meaning>

## Notes
<constraints/context>

## Decisions so far
- [<closed decision>](url) — <result; CCL refs when applicable>

## Not yet specified
<in-scope fog>

## Out of scope
<excluded work>
```

Decision/research/prototype/task tickets are children. Native issue dependencies express
real prerequisites.

## Semantic decision boundary

A decision requires a CCL proposal when accepting it creates or changes a material product,
domain, architecture, persistence, temporal, authority, failure, public, or downstream
contract.

Private implementation mechanics do not require CCL.

Use this test:

> Could two reasonable downstream implementations satisfy the recommendation while
> creating materially different externally meaningful contracts?

If yes, the decision is not acceptance-ready until the exact semantic payload is explicit.

### One semantic compiler

For material software decisions invoke `$contract-ledger wayfinder-decision` internally.
Wayfinder supplies context/recommendation; `$contract-ledger` owns typed normalization,
proposal hashing, revision checks, and transaction contribution.

Before human acceptance require one exact durable proposal containing map/decision identity,
origin mode, complete typed revision snapshots, proposal hash, affected contract@revision
identities, non-authoritative human rendering, and governing/constraint sources.

Persist one `## CCL Proposal` comment with the lossless proposal payload and rendering.

### Decision Analysis

Before a HITL decision persist one `## Decision Analysis` comment with current-state
evidence, constraints, alternatives, trade-offs, and recommendation. For CCL-backed work it
is explanation only and may not add semantics absent from the proposal.

If the recommendation materially changes, persist `## Recommendation Revision` and create a
new CCL proposal/hash when semantics changed.

### Human acceptance

For CCL-backed decisions ask exactly:

> Do you approve this recommendation and CCL proposal `<proposal-hash>`? (yes/no)

`yes` approves only that hash. Immediately persist `## CCL Acceptance` with proposal hash,
decision identity, human owner, and accepted state. The final transaction points to this
durable acceptance artifact.

For genuinely non-material planning decisions ask the ordinary yes/no recommendation gate
without manufacturing CCL state.

## Architecture records

After acceptance, determine ADR qualification through `$to-adr-doc`. When qualified, the
ADR consumes the same accepted CCL transaction; its Decision section is deterministic CCL
projection and its Context/Rationale remain explanatory only.

Other architecture docs remain owned by their document workflows; derived wiki state
remains owned by `$wiki-sync`.

## Atomic repository persistence

A CCL-backed acceptance is one authority transaction. When repository files change:

1. freeze current canonical `origin/main` and caller-worktree identity;
2. use a clean isolated worktree at that base;
3. have `$contract-ledger` contribute the accepted transaction;
4. have `$to-adr-doc` and `$wiki-sync` contribute required derived records;
5. require every changed path to belong to this accepted decision;
6. commit once under repository conventional-commit policy;
7. recheck canonical-main concurrency and push without force;
8. read back and revalidate CCL plus any ADR projection;
9. prove the protected caller worktree unchanged.

Persistence failure never changes the accepted semantic hash. The decision remains open
until canonical repository authority is durable.

## Continuation reconciliation

If accepted authority must be inherited into an existing continuation branch, attempt a
clean merge only after canonical-main persistence. A merge conflict is downstream semantic
reconciliation work, not permission for Wayfinder to choose `ours`/`theirs`.

Record an actual conflict with one machine-managed block:

```markdown
<!-- continuation-reconciliation:v1 -->
## Continuation Reconciliation

**Status:** required | synchronized | not-applicable
**Canonical authority:** <main commit | None>
**Continuation branch:** <branch | None>
**Conflict paths:** <exact paths | None>
**Reconciliation owner:** <$to-specs | None>
```

`required` is legal only for a real semantic merge conflict and names `$to-specs`.

## Resolution persistence

Only after required repository authority is canonical:

1. post a concise final resolution comment;
2. include proposal hash, transaction path, contract@revision identities, ADR path when any,
   and canonical commit for CCL-backed decisions;
3. close the decision ticket;
4. append it to `Decisions so far`;
5. update newly surfaced tickets/fog/out-of-scope state;
6. reconcile project-delivery state.

## Route clarity

Wayfinder is complete when the route is clear, not merely when current tickets are closed.
Every material destination obligation must be exactly one of:

```text
accepted CCL contract/assertion
implementation-equivalent/private mechanic
explicitly out of scope
open decision/fog
```

Route clarity requires zero open/blocking decisions, zero unresolved fog, zero unresolved
material semantic obligations, zero CCL source conflicts, no pending required ADR/docs/wiki
or repository persistence, current project-delivery reconciliation, and continuation state
`synchronized | semantic-reconciliation-required | not-applicable`.

Run `$attention` before declaring route clear. Do not rebuild prose contract matrices or
independent semantic challenger domains around accepted CCL assertions.

If closure finds a missing semantic choice, route it to its owning decision. If it finds
only an implementation-equivalent private mechanic, do not create architecture work.

## Invocation flow

### Chart the Map

1. define destination/boundaries;
2. recover current architecture/CCL;
3. identify decisions and fog breadth-first;
4. if no fog exists, finish the bounded decision directly rather than manufacturing a map;
5. otherwise create map/tickets/dependencies/fog state;
6. persist authorized repository artifacts;
7. reconcile project-delivery state;
8. stop.

### Work Through the Map

1. recover map/frontier;
2. pass project-delivery guard;
3. claim one decision;
4. investigate only enough to close it;
5. persist Decision Analysis;
6. prepare exact CCL proposal when material semantics change;
7. run human gate and persist acceptance;
8. atomically persist CCL + ADR/docs/wiki when required;
9. persist resolution/close ticket/update map;
10. reconcile project-delivery state;
11. run Route Clarity or hand off the next frontier decision.

## Human handoffs

Next frontier decision:

```text
$wayfinder - <Decision Title> (<Decision URL>)
```

Route clear for specification:

```text
$to-specs - <Wayfinder Map Title> (<Map URL>)
```

When continuation inheritance requires semantic reconciliation, include canonical authority
commit, continuation branch, and exact conflict paths. `$to-specs` owns downstream Spec
reconciliation.

Wayfinder never implements destination code, lets implementation choose missing semantics,
reinterprets CCL through downstream prose, mutates CCL outside `$contract-ledger`, or
creates duplicate ADR semantics beside CCL.
