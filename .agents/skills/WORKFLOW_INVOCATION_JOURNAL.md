# Workflow Invocation Journal

This document is the canonical cross-skill contract for Polaris workflow invocation
resumability.

## Purpose

A Workflow Invocation Journal (WIJ) is disposable, checkout-local execution evidence for a
single top-level skill invocation. It exists only to reduce repeated work after context loss,
agent restart, or an explicitly requested `resume` invocation.

The WIJ is **not** semantic, contract, dependency, candidate, closure, review, or lifecycle
authority. Current repository/tracker authority always wins. If a journal disagrees with
Git, GitHub, CCL, a deterministic contract, a recovery record, a verifier/review receipt, or
another owning authority, the journal entry is stale, superseded, or unusable.

### Non-blocking invariant

WIJ failure is never a workflow failure. Missing, corrupt, ambiguous, stale, incompatible,
unreadable, unwritable, unsupported, or deleted WIJ state may cause already-completed work
to be repeated, but it must never prevent otherwise-valid workflow progress.

When WIJ reuse cannot be proven, the consuming skill falls back to its ordinary authoritative
reconstruction and continues exactly as it would without WIJ support.

## Durability boundary

Polaris has three distinct durability layers:

```text
product durability
    Git commits / repository files

workflow durability
    CCL / tracker contracts / recovery records / checkpoints / verifier-review receipts

invocation durability
    disposable local WIJ execution evidence
```

Only the first two layers may establish lifecycle truth or support a fresh-session Human
Handoff. A WIJ never substitutes for the repository/tracker durability required by
`.agents/skills/README.md`.

## Storage

The current checkout journal root is:

```bash
git rev-parse --absolute-git-dir
```

plus:

```text
polaris/workflow-journal/v1/
```

Therefore the same rule works for ordinary branch-based development, linked worktrees,
detached worktrees, and independent clones. Ordinary branches in one checkout share the
same journal root. Linked worktrees receive isolated roots from Git automatically.

A journal uses:

```text
<GIT_DIR>/polaris/workflow-journal/v1/<skill>/<invocation-id>/
    metadata.json
    events.jsonl
```

No WIJ file may live in the candidate working tree.

## Shared CLI

The canonical helper is:

```bash
python -m scripts.workflow_journal <command> ...
```

V1 commands are:

```text
start
append
locate
inspect
complete
abandon
gc
```

`start` accepts `--manifest <json>` using `polaris.workflow-invocation-start/v1` and may
write a machine-readable result through `--json-output <path>`. `append` accepts
`--journal <invocation-dir>` plus `--event <json>` and may also write `--json-output`.
`locate` accepts exact `--skill`, `--repository`, and `--subject-url` identity. `inspect`,
`complete`, and `abandon` operate on one exact invocation directory. `gc` accepts one exact
`--lifecycle-scope-url`.

The helper supplies sequence numbers, event IDs, timestamps, invocation IDs, and event hashes;
callers do not manufacture them.

Expected WIJ operational degradation is deliberately exit-code zero so a shell using
`set -e` cannot turn a disposable-journal problem into a workflow stop. Human output begins
with an explicit `WORKFLOW JOURNAL:` or `WORKFLOW JOURNAL GC:` status, and `--json-output`
provides structured machine consumption. CLI syntax/programming errors handled by
`argparse` may still return its ordinary nonzero usage status.

Examples:

```bash
python -m scripts.workflow_journal start \
  --manifest /tmp/wij-start.json \
  --json-output /tmp/wij-start-result.json

python -m scripts.workflow_journal locate \
  --skill implement-ticket \
  --repository sponge-b0b/Polaris \
  --subject-url https://github.com/sponge-b0b/Polaris/issues/407 \
  --json-output /tmp/wij-locate.json

python -m scripts.workflow_journal append \
  --journal <invocation-dir> \
  --event /tmp/wij-event.json
```

The CLI never decides workflow meaning. A `FOUND` journal is only evidence the consuming
skill may reconcile; it is not permission to skip current authority checks.

## Invocation metadata

`metadata.json` is immutable after creation and uses schema
`polaris.workflow-invocation/v1`.

It contains at least:

```json
{
  "schema": "polaris.workflow-invocation/v1",
  "invocation_id": "implement-ticket-407-20261020T071500Z-a83f",
  "skill": "implement-ticket",
  "started_at": "2026-10-20T07:15:00Z",
  "repository": {
    "identity": "sponge-b0b/Polaris"
  },
  "subject": {
    "kind": "github-issue",
    "number": 407,
    "url": "https://github.com/sponge-b0b/Polaris/issues/407"
  },
  "lifecycle_scope": {
    "kind": "github-issue",
    "number": 359,
    "url": "https://github.com/sponge-b0b/Polaris/issues/359"
  },
  "checkout": {
    "initial_branch": null,
    "initial_head": "<sha>"
  }
}
```

`initial_branch` is nullable because detached execution worktrees are normal.
`lifecycle_scope` is nullable when no containing lifecycle artifact exists. Consumers under
one Spec should use that Spec as lifecycle scope so `$spec-merge-cleanup` can later garbage
collect the disposable journals.

## Append-only events

`events.jsonl` is append-only. Each complete line is one
`polaris.workflow-journal-event/v1` object with:

```text
schema
sequence
unique event_id
recorded_at
invocation_id
type
candidate_state or null
data object
previous_event_sha256
event_sha256
```

The first event binds `previous_event_sha256` to the canonical SHA-256 of `metadata.json`.
Each later event binds to the previous event hash. The hash chain detects accidental
valid-looking editing or interior corruption; it is not a security boundary.

A truncated final line is ignored and the valid prefix remains readable with degraded
health. Interior parse/schema/hash failure terminates the usable prefix immediately. A
degraded journal must not be repaired by rewriting history; later workflow execution simply
falls back to ordinary reconstruction when needed.

## V1 event vocabulary

The shared V1 event types are:

```text
invocation_started
authority_snapshot
binding_snapshot
work_completed
check_result
external_write
frontier
interruption_checkpoint
resume_started
resume_reconciled
child_invocation_started
child_result_observed
invocation_completed
invocation_abandoned
```

Events record meaningful workflow progress, not terminal history. Reading files, searches,
individual edits, shell navigation, and internal reasoning are not journal events merely
because they occurred.

`frontier` and `interruption_checkpoint` are execution hints, not authority. Resume always
reconstructs current authority before choosing a continuation point.

## Evidence binding and reuse

A consumer owns the meaning of its candidate identity and determines which events are
reusable. The shared journal engine stores facts only.

V1 uses conservative exact-state reuse:

```text
same exact candidate + compatible workflow authority
    -> candidate-bound deterministic PASS evidence may be reused

candidate differs or compatibility is uncertain
    -> redo the check
```

Path-aware selective invalidation is explicitly deferred beyond V1.

A historical PASS remains a true historical event even when it is no longer reusable.
Resume reconciliation classifies current usability; it does not rewrite or erase the old
event.

Live or mutable state must be refreshed according to the consuming skill even when a journal
records an earlier success. Examples include native blockers, remote branch state,
project-delivery guards, service readiness, and other mutable external prerequisites.

## External writes

An `external_write` event records an attempted durable transition only after the owning
workflow has performed its required readback. On resume the owning workflow must re-read the
actual external authority. The journal may identify what to verify; it never proves that the
external system still contains the claimed state.

## Resume selection

V1 consumes an old journal only for an explicit `resume $<skill> ...` request. A normal skill
invocation follows the ordinary fresh reconstruction and starts a new journal instead of
silently attaching to previous local execution history.

Resume discovery matches at least:

```text
current checkout journal root
+ skill
+ repository identity
+ durable subject URL
+ nonterminal invocation
```

Outcomes are non-blocking:

```text
zero matches       -> ordinary reconstruction
one match          -> attempt reconciliation
multiple matches   -> skip automatic reuse; ordinary reconstruction
unusable journal   -> ordinary reconstruction
```

## Workflow authority changes

A consumer records the relevant workflow authority in `authority_snapshot` events. When
current authority materially differs, prior journal entries remain historical evidence but
do not automatically authorize skipping current workflow requirements. V1 conservatively
re-evaluates workflow-dependent evidence under the new rules.

## Invocation state

Invocation state is derived from events, never from a mutable status field.

A nonterminal journal is `ACTIVE` in the storage sense even if the prior agent process died
without writing an interruption event. `interruption_checkpoint` may describe a graceful
context boundary; its absence never prevents resume discovery.

`invocation_completed` and `invocation_abandoned` are terminal journal events. They do not
replace the consuming workflow's own legal termination states.

WIJ health (`HEALTHY`, `DEGRADED`, `UNAVAILABLE`) is separate from workflow lifecycle state.
A health transition can never move a ticket, Spec, review, or other artifact through its
lifecycle.

## Independent children

Ordinary helpers normally return evidence to the parent invocation and the parent records
that result. A genuinely independent verifier/reviewer may own a separate child journal.
The parent records only dispatch and exact result observation; it may not rewrite the child
journal or use WIJ state to weaken the independent proof boundary.

## Secrets and hygiene

Never record credentials, passwords, tokens, authorization headers, private connection
strings, `.env` contents, or process environments. Commands stored as evidence must be
sanitized and should record only the semantic command needed for resume. The shared engine
rejects obvious secret-bearing fields/patterns; callers remain responsible for never passing
secret material to it.

## Garbage collection

`$spec-merge-cleanup` is the lifecycle owner for best-effort WIJ garbage collection after
authoritative Spec completion. GC matches exact immutable `lifecycle_scope` identity, not
branch names, and may remove terminal or nonterminal journals for that completed Spec.

GC discovers the primary checkout and linked worktree journal roots beneath the repository's
Git common directory. Independent clones are naturally outside that discovery boundary and
disappear when their clone is removed.

GC failure is non-blocking and never rolls Spec completion backward.

## Shared tooling boundary

`scripts/workflow_journal.py` owns only journal mechanics: storage resolution, immutable
metadata creation, append/hash-chain integrity, valid-prefix loading, resume discovery,
inspection, terminal-event append, and lifecycle-scope GC.

It must not interpret Ticket Contracts, compute `$implement-ticket` candidate identity,
decide test reuse, interpret closure checkpoints, validate blockers, decide Attention
currency, or choose the semantic resume point. Those decisions remain with the consuming
skill.

## V1 adopters

The first adopter is `$implement-ticket`. Planned later adopters include `$to-tickets`,
`$to-specs`, `$verify-spec`, and `$review-spec`, followed by other long-running lifecycle
owners where measured benefit justifies integration.
