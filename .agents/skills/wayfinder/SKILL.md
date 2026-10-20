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

### Human focus handoff

A guard failure caused only by the target Wayfinder not being focused is a human focus
boundary, not a generic dead end and not permission for `$wayfinder` to choose focus.

Do not mutate the decision/map and do not inspect or reproduce Project Delivery singleton
logic to guess the current focused set. Surface this exact ownership handoff:

```text
PROJECT DELIVERY: HUMAN FOCUS HANDOFF
Target Wayfinder: #<n>
Reason: not focused
Next human action:
$project-delivery-management status
```

After the human sees current canonical delivery state, they may explicitly invoke the exact
`focus`, `switch-focus`, or `parallel-focus` operation they choose. Resume Wayfinder work
only after a later current-run `guard <Wayfinder>` returns exact
`PROJECT DELIVERY GUARD: ALLOWED`.

A guard failure for `not frontier-eligible`, invalid control state, or unreadable blockers
is not a focus-choice handoff. Report the exact guard reason/blocker and stop without
suggesting an ineligible focus mutation.

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

## Decision closure gate

An accepted decision may not proceed from canonical repository persistence to final
resolution by prose alone. Before posting final resolution, closing the decision, or
mutating the Wayfinder map frontier, generate a structured closure receipt outside
repository candidate state and pass the machine gate:

```bash
python .agents/skills/wayfinder/scripts/decision_closure.py \
  --repo-root <clean-canonical-authority-worktree> \
  --receipt <decision-closure-receipt.json>
```

Require exact first line:

```text
WAYFINDER DECISION CLOSURE: ALLOWED
```

The receipt schema is:

```json
{
  "schema": "polaris.wayfinder-decision-closure/v1",
  "decision": {
    "number": 123,
    "url": "https://github.com/<owner>/<repo>/issues/123"
  },
  "canonical_commit": "<full 40-hex commit>",
  "semantic_mode": "ccl-backed",
  "ccl_proposal": "sha256:<64-hex>",
  "ccl_transaction": "contracts/ccl/transactions/<64-hex>.json",
  "adr": {
    "disposition": "CREATED | UPDATED | UNCHANGED | NOT-QUALIFIED",
    "path": "docs/adr/<qualified-adr>.md | null",
    "projection_check": "PASS | N/A"
  },
  "wiki_sync": {
    "disposition": "UPDATED | NO_DURABLE_KNOWLEDGE_CHANGED",
    "affected_knowledge_routing": [
      {
        "candidate": "WK-1",
        "changed_surface_authority": "<exact source>",
        "candidate_entity_claim": "<exact entity + claim/section>",
        "routing_basis": "<routing evidence>",
        "disposition": "affected | not-affected",
        "reason_evidence": "<non-empty reason/evidence>"
      }
    ],
    "mutations": ["wiki/<changed-path>"]
  }
}
```

For a CCL-backed decision, `$wiki-sync` is mandatory even when no wiki text changes. A
claimed no-op is valid only after `$wiki-sync` has produced the complete Affected Knowledge
Routing Record required by its own workflow. `NO_DURABLE_KNOWLEDGE_CHANGED` is rejected if
any candidate remains `affected`, unresolved, or lacks reason/evidence. `UPDATED` requires
at least one affected candidate, exact `wiki/` mutation paths, and `wiki/log.md`.

The gate independently requires the persisted transaction to match the accepted proposal,
requires its origin to be `wayfinder-decision` with durable acceptance, checks any qualified
ADR binds the exact proposal/transaction, and requires the gate worktree to be clean at the
recorded canonical commit. `NOT-QUALIFIED` is legal only as the `$to-adr-doc` disposition;
it is not permission to skip `$wiki-sync` for a CCL-backed decision.

For a genuinely non-material planning decision, use `semantic_mode: non-material`, omit CCL
coordinates, and record exact `NOT-APPLICABLE` child dispositions. Do not manufacture CCL,
ADR, or wiki work merely to satisfy the gate.

A failed or missing closure gate means the decision remains open. Do not post final
resolution, close the decision, or mutate the map frontier, even when the semantic answer
and repository persistence are otherwise correct.

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

Only after required repository authority is canonical **and the Decision closure gate has
returned `WAYFINDER DECISION CLOSURE: ALLOWED`**:

1. post a concise final resolution comment;
2. include proposal hash, transaction path, contract@revision identities, ADR path when any,
   canonical commit, and Decision closure receipt SHA-256 for CCL-backed decisions;
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

### Specification handoff gate

When Route Clarity resolves to downstream specification or specification reconciliation,
Wayfinder may not terminate successfully from prose alone. Generate and admit the exact
terminal handoff mechanically from the final durable map snapshot and the formal Route
Clarity Attention result.

Capture the final map after all resolution/map/project-delivery mutations:

```bash
gh issue view <wayfinder-map> --repo <owner/repo> --json title,url,body \
  > <wayfinder-map-json>
```

Write the exact formal `$attention` result for this checkpoint to a temporary file outside
repository candidate state. The checkpoint must be exactly:

```text
Checkpoint: $wayfinder route clarity
```

A `FINDINGS` result must use the complete `$attention` finding shape. Only findings whose
`Blocking basis` is `none` are compatible with a specification handoff; a blocking finding
means Route Clarity is not terminal yet.

Then run:

```bash
python .agents/skills/wayfinder/scripts/route_handoff.py specification \
  --map-json <wayfinder-map-json> \
  --attention-result <route-clarity-attention-result>
```

Require exact first line:

```text
WAYFINDER HANDOFF: SPECIFICATION
```

The helper does not decide semantic Route Clarity. It admits terminal output only after that
decision exists. It validates formal Attention shape, map identity, and any current
`continuation-reconciliation:v1` record. When continuation status is `required`, it requires
full canonical authority SHA, continuation branch, exact conflict paths, and `$to-specs` as
reconciliation owner.

A failed gate means Wayfinder has **not** terminated successfully. Do not replace the failed
handoff with explanatory prose.

For a successful specification/reconciliation terminal, the final user-visible response
must end with the helper stdout **byte-for-byte as one terminal block**. Do not paraphrase,
omit, reorder, or replace the generated `$to-specs` command or reconciliation coordinates.

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
9. pass the Decision closure gate against the clean canonical authority worktree;
10. persist resolution/close ticket/update map;
11. reconcile project-delivery state;
12. run Route Clarity; when it resolves to specification/reconciliation, pass the
   Specification handoff gate and emit its exact terminal block; otherwise hand off the next
   frontier decision.

## Human handoffs

Next frontier decision:

```text
$wayfinder - <Decision Title> (<Decision URL>)
```

Route clear for specification is machine-generated. The canonical terminal shape is:

```text
WAYFINDER HANDOFF: SPECIFICATION
$to-specs - <Wayfinder Map Title> (<Map URL>)
Canonical authority: <full main SHA>        # only when continuation reconciliation is required
Continuation branch: <branch>              # only when continuation reconciliation is required
Conflict paths: <exact paths>               # only when continuation reconciliation is required
Route Clarity Attention SHA-256: <sha256>
```

The `route_handoff.py specification` stdout is the handoff authority for terminal output.
Successful specification/reconciliation termination without that exact emitted stdout is an
invalid Wayfinder termination, even when explanatory prose correctly names `$to-specs`.

When continuation inheritance requires semantic reconciliation, `$to-specs` owns downstream
Spec reconciliation.

Wayfinder never implements destination code, lets implementation choose missing semantics,
reinterprets CCL through downstream prose, mutates CCL outside `$contract-ledger`, or
creates duplicate ADR semantics beside CCL.
