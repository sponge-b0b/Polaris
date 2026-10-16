---
name: wayfinder
description: Plan a large, decision-heavy body of work as a durable map and resolve one semantic decision at a time until downstream work is clear.
compatibility: product=codex product=claude-code system=git system=gh network=required
disable-model-invocation: true
---

# Wayfinder

Wayfinder is the planning workflow for work whose destination is clear enough to pursue but whose route still contains multiple or coupled material decisions.

Its job is to eliminate semantic fog before specification or implementation. It does not implement the destination.

For material software decisions, the **Canonical Contract Ledger (CCL)** is the frozen semantic output. Decision-analysis prose explains the choice; it does not become a second semantic contract.

## Session Independence

Assume no prior conversational state.

Recover correctness-critical state from the invocation, repository, issue tracker, active architecture, CCL, and durable workflow artifacts. Conversational summaries are context only.

If required durable state cannot be recovered, stop rather than infer it.

## Two Modes

### Chart the Map

Use when the human provides a large idea or destination whose route is still foggy.

Charting may:

* define the destination and out-of-scope boundary;
* create the canonical `wayfinder:map` issue;
* create currently specifiable decision/research/prototype/task tickets;
* wire genuine semantic dependencies;
* preserve not-yet-specifiable fog.

Charting is planning and is not project-focus gated. It must not establish, switch, or broaden project delivery focus.

### Work Through the Map

Use when the human supplies a Wayfinder map or one of its decision tickets.

Resolve at most one non-research decision ticket per human session.

## Project Delivery Focus Guard

`$project-delivery-management` owns delivery focus. `$wayfinder` never copies or infers focus state.

Before substantive work on an existing map:

1. resolve the exact governing Wayfinder;
2. invoke `$project-delivery-management` `reconcile`;
3. invoke `$project-delivery-management` `guard <Wayfinder>`;
4. require exact `PROJECT DELIVERY GUARD: ALLOWED` before claiming or mutating a decision.

Handle other results as follows:

* `BLOCKED` -> report blockers and stop;
* `FOCUS REQUIRED` with another focused map/set -> report the current focus and stop; never switch automatically;
* `FOCUS REQUIRED` with no focused map -> ask:

  > Establish <Wayfinder Map Title> as the project delivery focus and continue? (yes/no)

  Only explicit `yes` authorizes `$project-delivery-management focus <Wayfinder>`. Re-run the actual guard and require `ALLOWED`.

Manual reconstruction of project-delivery state does not substitute for the delegated child result.

After every durable Wayfinder transition that can affect eligibility or focus validity, invoke `$project-delivery-management reconcile` again.

## Map Model

The map is one issue labelled `wayfinder:map`.

Its body contains:

```markdown
## Destination

<what completion means>

## Notes

<standing constraints and useful context>

## Decisions so far

- [<closed decision title>](url) — <one-line result; CCL refs when applicable>

## Not yet specified

<in-scope fog that cannot yet be stated as a decision>

## Out of scope

<explicitly excluded work>
```

Decision/research/prototype/task tickets are children of the map. Native issue dependencies express real prerequisites.

Ticket types:

```text
wayfinder:research
wayfinder:prototype
wayfinder:grilling
wayfinder:task
```

Research is AFK. A material decision is HITL: the human, not the agent, decides.

## Semantic Decision Boundary

### What Requires CCL

A Wayfinder decision requires a CCL proposal when accepting it would create or change a material product, domain, architecture, persistence, temporal, authority, failure, public, or downstream contract.

Ordinary private implementation mechanics do not require CCL semantics.

Use this test:

> Could two reasonable downstream implementations satisfy the recommendation while creating materially different externally meaningful contracts?

If yes, the decision is not ready for acceptance until those semantics are explicit in the proposed CCL assertions.

### One Semantic Compiler

For a material software decision, invoke `$contract-ledger` in `wayfinder-decision` mode as internal composition.

`$wayfinder` may provide decision context and proposed meaning, but it must not independently author a competing frozen semantic representation. `$contract-ledger` owns normalization into typed CCL revisions, proposal hashing, ledger/revision checks, and final transaction contribution.

Before the human gate, require one exact proposal containing:

```text
Wayfinder map / decision identity
CCL origin mode: wayfinder-decision
Exact typed full-snapshot revisions
Proposal hash
Affected contract@revision identities
Human-readable rendering (non-authoritative)
Applicable governing/constraint sources
```

The pre-acceptance proposal may carry `acceptance: null`; it is a **proposal envelope**, not a ledger-admissible accepted transaction. It must not be written to `contracts/ccl/transactions/`.

Persist one issue comment beginning:

```markdown
## CCL Proposal
```

The comment must contain:

* exact proposal hash;
* exact contract/revision set;
* the complete typed proposal JSON or an equivalently lossless durable representation;
* a human-readable rendering clearly labeled non-authoritative.

This comment is the recoverable proposal record. A later session must be able to reconstruct the same semantic payload without chat memory.

### Decision Analysis

Before asking the human to accept a HITL decision, persist one issue comment beginning:

```markdown
## Decision Analysis
```

Keep it concise but preserve material current-state evidence, constraints, alternatives, trade-offs, and the recommendation.

For CCL-backed decisions, Decision Analysis is rationale and explanation only. It must not add normative semantics absent from the exact CCL proposal.

If later discussion materially changes the recommendation, post:

```markdown
## Recommendation Revision
```

and produce a new CCL proposal/hash when semantic meaning changed. Never rewrite old analysis to hide history.

### Human Acceptance

For a CCL-backed decision, ask exactly:

> Do you approve this recommendation and CCL proposal `<proposal-hash>`? (yes/no)

`yes` approves only that exact semantic proposal hash.

`no` leaves the decision open. Continue analysis; if the recommendation changes materially, generate and persist a new CCL proposal/hash before asking again.

After explicit `yes`, immediately persist a durable issue comment beginning:

```markdown
## CCL Acceptance
```

It must record:

```text
Proposal hash: <exact approved hash>
Decision: <ticket identity>
Accepted by: human owner
Acceptance state: accepted
```

The final CCL transaction's `acceptance.artifact.ref` points to this durable acceptance comment.

Nearby prose, a different hash, or an inferred yes is not acceptance.

### Non-CCL HITL Decisions

If the decision truly does not create/change material software semantics, present the recommendation and ask:

> Do you agree with this recommendation? (yes/no)

Do not manufacture CCL entries for ordinary planning preferences or implementation-equivalent mechanics.

## Architecture Records

After a CCL-backed decision is accepted, determine whether the decision merits an ADR using `$to-adr-doc`'s qualification rule.

If yes, `$to-adr-doc` consumes the **same accepted CCL transaction**. Its `## Decision` section is a deterministic CCL projection; Context/Rationale explain why the decision was made and may not add new normative semantics.

Other architecture documentation remains owned by its existing document workflows. Derived wiki maintenance remains owned by `$wiki-sync`.

During this staged migration, accepted ADRs remain a discoverable architecture surface for downstream workflows that have not yet been converted to direct CCL consumption. Therefore the generated ADR projection must be complete enough to expose the typed CCL semantics without paraphrase.

## Atomic Repository Persistence

A CCL-backed Wayfinder acceptance is one authority transaction.

If repository files must change, persist them atomically on canonical `main`:

1. fingerprint the caller worktree, including branch/HEAD, staged state, unstaged tracked state, and untracked path/content state;
2. fetch and freeze exact `origin/main` as `CANONICAL_MAIN_BASE`;
3. create a clean isolated worktree at that exact base;
4. inside that isolated worktree, invoke `$contract-ledger` for **parent-owned atomic contribution** of the accepted transaction;
5. if an ADR is required, invoke `$to-adr-doc` against that exact transaction path;
6. invoke `$wiki-sync` or other already-required derived-document owner as applicable;
7. require every changed path to belong to the accepted decision; unexpected paths block persistence;
8. stage only intended paths and commit once through `$conventional-commits`;
9. fetch `origin/main` immediately before push and require it still equals `CANONICAL_MAIN_BASE`;
10. push normally to `main`, never force;
11. fetch/read back the exact commit, rerun CCL ledger validation, and for every CCL-backed ADR run:

   ```bash
   python -m scripts.ccl_adr check-adr <adr-path> <transaction-path>
   ```

12. prove the protected caller worktree fingerprint is unchanged.

The transaction file, its ADR projection, and required derived architecture updates either become canonical together or the decision remains unresolved for repository persistence.

If canonical persistence fails after human acceptance, preserve the acceptance history but **do not close the decision**. Retry persistence from fresh canonical state; never reinterpret the accepted hash.

### Continuation Branch

If this Wayfinder is repairing authority above an existing durable continuation branch, attempt inheritance only after canonical `main` persistence using a second isolated worktree.

A clean merge may be pushed normally after a concurrency check.

A merge conflict means downstream semantic reconciliation is required. Preserve both canonical authority and downstream state; do not choose `ours`/`theirs` or manually redesign downstream artifacts inside Wayfinder. Record the canonical commit, continuation branch, and exact conflict paths for `$to-specs` reconciliation.

When reconciliation is required, maintain exactly one machine-managed block on the governing map so the current `$to-specs` workflow can recover the transition without chat memory:

```markdown
<!-- continuation-reconciliation:v1 -->
## Continuation Reconciliation

**Status:** required | synchronized | not-applicable
**Canonical authority:** <main commit | None>
**Continuation branch:** <branch | None>
**Conflict paths:** <exact paths | None>
**Reconciliation owner:** <$to-specs | None>
```

`required` is legal only for an actual semantic merge conflict and must name `$to-specs`. Update this block in place; do not append competing transition state.

## Resolution Persistence

Only after required repository authority is canonical:

1. post a concise final resolution comment;
2. for CCL-backed decisions include proposal hash, transaction path, contract@revision identities, ADR path when any, and canonical commit;
3. close the decision ticket;
4. append the decision to `Decisions so far`;
5. update newly surfaced tickets/fog/out-of-scope state;
6. run project-delivery reconciliation.

Do not duplicate the full Decision Analysis or CCL payload in the resolution comment.

## Legacy Decision Compatibility

Existing accepted Wayfinder decisions created before CCL are historical authority; do not automatically rewrite them.

Before a legacy map may newly declare route clarity, every material legacy semantic decision still needed by the destination must be handled exactly once:

* if current accepted sources determine one exact semantic meaning without conflict, invoke `$contract-ledger existing-authority` to register that meaning;
* if governing/constraint sources disagree materially, report `CCL SOURCE CONFLICT` and return to the exact governing decision/domain rather than choosing one;
* if a material choice was never actually decided, reopen/remediate the governing decision or create a genuinely new decision when no existing domain owns it;
* do not manufacture extra semantics merely to make migration look complete.

This is migration of accepted meaning, not reinterpretation of history.

## Route Clarity

Wayfinder is complete when the route is clear, not merely when known tickets happen to be closed.

Immediately before route-clear handoff, perform one bounded map closure audit.

Every material destination obligation must be in exactly one state:

```text
accepted CCL contract/assertion
existing authority registered into CCL
implementation-equivalent/private mechanic
explicitly out of scope
open decision/fog
```

Anything else is unresolved.

Route clarity requires:

```text
Open decision tickets: 0
Blocked/non-actionable open decisions: 0
Unresolved Not yet specified fog: 0
Unresolved material semantic obligations: 0
Material legacy semantics still needed but not registered/reconciled: 0
CCL source conflicts: 0
Required ADR/docs/wiki reconciliation pending: 0
Wayfinder-owned repository persistence pending: 0
Required project-delivery reconciliation: complete
Continuation state: synchronized | semantic-reconciliation-required | not-applicable
```

Run the prescribed `$attention` checkpoint before declaring route clear. Attention may identify a real missing obligation, but it does not itself create authority.

Do **not** rebuild another prose contract matrix, source-unit universe, semantic challenger domain, or independent interpretation of already accepted CCL assertions. The ledger is the frozen semantic contract.

If closure finds a missing semantic choice, route it to its owning decision. If it finds only an implementation-equivalent private mechanic, do not create architecture work.

## Invocation Flow

### Chart the Map

1. name destination and boundaries;
2. recover current architecture/CCL relevant to the destination;
3. identify current decisions and fog breadth-first;
4. if no fog exists, finish the bounded decision directly instead of manufacturing a map;
5. otherwise create the map, tickets, dependencies, and fog state;
6. persist any authorized repository artifacts;
7. reconcile project-delivery state;
8. stop.

### Work Through the Map

1. recover map and named decision/frontier;
2. pass the Project Delivery Focus Guard;
3. claim the decision;
4. investigate only enough to close that decision;
5. persist Decision Analysis;
6. if material software semantics change, prepare/persist the exact CCL Proposal;
7. run the human acceptance gate;
8. after acceptance, persist the CCL Acceptance record;
9. atomically persist CCL + ADR/docs/wiki when required;
10. persist final resolution and close the ticket;
11. update map/fog/dependencies;
12. reconcile project-delivery state;
13. run Route Clarity or hand off the next frontier decision.

## Human Handoffs

If another frontier decision remains:

```text
$wayfinder - <Decision Title> (<Decision URL>)
```

If the map remains focused but every open decision is blocked, report `PROJECT DELIVERY: FOCUSED-BUT-STALLED` with exact blockers.

If route clarity passes and the destination is specification:

```text
$to-specs - <Wayfinder Map Title> (<Map URL>)
```

When continuation inheritance requires semantic reconciliation, include canonical authority commit, continuation branch, and conflict paths. `$to-specs` owns reconciling existing governed Specs.

Do not hand off to `$to-specs` while canonical persistence, source conflict, project-delivery reconciliation, or branch identity/concurrency remains unresolved.

## Non-Goals

Wayfinder does not:

* implement destination code;
* let downstream implementation decide missing material semantics;
* make `$to-specs` reinterpret Decision Analysis prose as a stronger contract;
* independently mutate CCL outside `$contract-ledger`;
* create duplicate ADR semantics beside CCL;
* reopen frozen CCL semantics merely because another wording is imaginable.
