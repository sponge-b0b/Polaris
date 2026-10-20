# Workflow Invocation Journal Rollout

> This document records design rationale and rollout planning. It is not runtime workflow
> authority. The canonical WIJ contract is
> `.agents/skills/WORKFLOW_INVOCATION_JOURNAL.md`.

## Problem

Long-running agent skill invocations regularly cross context/token boundaries or require an
agent restart after workflow-policy changes. Product work is often recoverable from the
checkout and lifecycle-critical transition state is persisted in GitHub, but invocation-level
execution evidence such as completed technical checks, searches, wiki synchronization, and
intermediate workflow phases may exist only in conversational context.

After interruption the safe fallback is to reconstruct from durable authority and repeat work
whose prior completion cannot be proven. That is correct but can consume substantial time and
tokens.

## Selected design

Polaris adds a disposable, checkout-local Workflow Invocation Journal (WIJ): an append-only
execution journal stored in Git administrative state. It records state-bound operational
facts needed to accelerate explicit resume requests while remaining strictly subordinate to
current repository/tracker authority.

The design distinguishes:

```text
product durability      -> Git/repository state
workflow durability     -> CCL/tracker contracts/checkpoints/recovery/proof receipts
invocation durability   -> local disposable WIJ
```

WIJ is intentionally the weakest layer. Deleting it at any point must reduce behavior only
to today's ordinary workflow reconstruction and possible repeated work.

## Why Git administrative storage

The location is derived from `git rev-parse --absolute-git-dir` rather than a working-tree
path or branch name. This supports all current development modes without caller-specific
logic:

* ordinary clone with normal branch switching;
* linked worktree;
* detached linked worktree;
* independent temporary clone.

Ordinary branches in one checkout share one administrative journal root. Linked worktrees
receive distinct Git directories and therefore isolated WIJ roots automatically.

## V1 reuse policy

V1 deliberately uses conservative exact-state reuse. Candidate-bound deterministic evidence
may be reused only when the exact candidate and relevant workflow authority remain compatible.
Any candidate difference makes that evidence non-reusable. Path-aware selective invalidation
is deferred until real V1 usage demonstrates that its benefit justifies the extra dependency
reasoning.

Live/mutable state remains live: dependencies, remote branch state, actionability guards,
service readiness, recovery records, and similar authority are refreshed by the consuming
skill even when the journal records an earlier success.

## Failure policy

WIJ is an optimization and may never impede product/workflow progress. Missing, corrupt,
ambiguous, stale, unsupported, unreadable, unwritable, or deleted WIJ state produces a
non-blocking degradation and the owning workflow continues from current authoritative state.

A valid journal prefix may be recovered after a truncated tail or later corruption. Events
form a lightweight SHA-256 hash chain so accidental middle-of-file edits are detected rather
than silently reused.

## Initial adopter: `$implement-ticket`

The first vertical slice integrates only `$implement-ticket` so the shared abstraction is
proven before wider adoption.

The pilot records:

* invocation/authority/binding snapshots;
* pre-mutation and pre-closure Attention outcomes as pointers to authoritative gate state;
* meaningful implementation/wiki milestones;
* Ruff, Mypy, pytest, migration, architecture, Arid, JSCPD and related technical evidence;
* Implementation Evidence Index state;
* v3 closure-checkpoint writes/readbacks;
* independent verifier dispatch/raw-result/finalization observations;
* commit/push/readback/closure/recovery transitions;
* final completion.

The integration contract is
`.agents/skills/implement-ticket/WORKFLOW_INVOCATION_JOURNAL.md`.

## Planned adopters

### First wave

1. `$implement-ticket`
2. `$to-tickets`
3. `$to-specs`
4. `$verify-spec`
5. `$review-spec`

`$to-tickets` is the planned second adopter because it tests the opposite recovery shape from
implementation: substantial external GitHub mutation with comparatively little candidate
filesystem state.

### Second wave

Evaluate measured value and semantics before integrating:

* `$wayfinder`
* `$architecture-remediation`
* `$spec-merge-cleanup`
* `$contract-ledger`
* `$project-tracking`
* `$project-delivery-management`

`$spec-merge-cleanup` is nevertheless the designated lifecycle owner for best-effort WIJ GC
after authoritative Spec completion.

### Helpers

Routine helpers such as `$attention`, `$coding-standards`, `$format-code`,
`$database-migrations`, `$deduplicate-code`, wiki synchronization, and conventional-commit
helpers should normally return evidence to their parent's journal rather than create a new
top-level invocation journal.

Independent closure verifiers may own separate child journals so proof independence remains
visible and cannot be rewritten by the parent.

## V1 falsifier matrix

V1 is not ready for production workflow reuse until tests prove at least:

* ordinary branch checkout stores WIJ outside candidate Git status;
* branch switch preserves the checkout journal root;
* linked worktrees receive isolated journal roots;
* detached worktrees and independent clones work;
* missing/unwritable journal degrades without stopping the workflow;
* explicit resume with no journal reconstructs normally;
* multiple matching journals do not auto-select one;
* normal non-`resume` invocation does not silently attach to old history;
* truncated final JSONL line recovers the valid prefix;
* interior parse/hash corruption uses only the prior valid prefix;
* unsupported schema degrades without stopping work;
* hard interruption without an interruption checkpoint remains discoverable;
* exact same candidate + compatible authority can reuse eligible deterministic PASS evidence;
* a one-byte candidate difference prevents candidate-bound evidence reuse;
* workflow-authority change triggers conservative reconciliation;
* live dependency/remote/service state is refreshed regardless of journal history;
* current Attention verification remains authoritative;
* GitHub v3 closure checkpoint dominates contradictory WIJ state;
* external writes are re-read from their owning system;
* raw unfinalized verifier PASS/FAIL cannot be salvaged from WIJ;
* lifecycle-scope GC removes only exact matching Spec journals and remains non-blocking;
* obvious credential material is rejected;
* deleting the whole WIJ directory mid-ticket leaves `$implement-ticket` behavior correct.

## Acceptance strategy

The first adopter should be exercised through controlled interruption points:

```text
after implementation before tests
after Ruff/Mypy
after focused pytest
after migration verification
after architecture verification
after pre-closure Attention
after v3 awaiting-verification
after verifier FAIL + corrective mutation
after finalized PASS before commit
after commit before push
after push before closure evidence
after ticket close before recovery reconciliation
after closure before frontier handoff
```

The expected invariant is always:

> no correctness step is skipped; already-valid expensive deterministic work is not repeated
> when V1 can prove reuse, and otherwise the workflow conservatively repeats it.

## Future V2

Only after V1 is stable should Polaris consider path-aware evidence invalidation/reuse, a
repository-wide optional invocation index, or broader free-form investigative-skill support.
Those optimizations must preserve the V1 non-authority and non-blocking invariants.
