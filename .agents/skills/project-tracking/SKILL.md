---
name: project-tracking
description: Reconcile the public GitHub Project from already-established durable lifecycle state at permanent authorized projection boundaries; never determine workflow truth.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Tracking

`$project-tracking` is a deterministic, non-authoritative projection helper.

It does not own lifecycle state, semantic authority, delivery focus, scheduling,
dependencies, hierarchy, completion, or artifact membership semantics.

## Invocation boundary

Project projection is intentionally eventually consistent during active delivery. Invoke
this helper only at:

1. **Mandatory Spec completion reconciliation** — `$spec-merge-cleanup` reconstructs the
   complete completed-Spec lineage and supplies one desired projection batch.
2. **Explicit human-requested board reconciliation** — the active workflow reconstructs the
   requested authoritative artifact universe and supplies one desired projection batch.

Ordinary lifecycle transitions do not synchronize the Project. Do not persist a pending
Project-update queue/flag/label/comment ledger.

Repository/Project setup, schema changes, historical backfills, or other administrative
conversion work are outside this runtime skill.

## Input contract

The caller supplies one desired base projection per formal artifact:

* GitHub issue URL;
* `Artifact Type`;
* `Workflow State`;
* base `Next Skill`;
* base `Work Status`;
* `Completed On` only for `Complete`;
* current `Project Delivery State` for every active formal artifact:
  `in-focus | eligible | blocked | independent`;
* optional `Area` / `Priority` only when the caller intentionally owns those presentation
  changes.

The caller reconstructs the complete authoritative artifact universe. This skill never
crawls Project rows to decide what ought to exist.

## Authority rules

Never infer lifecycle/delivery truth from:

* Project fields or membership;
* issue open/closed state alone;
* labels;
* saved-view position;
* hierarchy alone;
* prior conversation.

Project state is read only to detect and repair projection drift.

Delivery context comes from `$project-delivery-management` for Wayfinder-managed artifacts
or explicit durable Independent classification. Ambiguous governance is invalid rather than
silently treated as Independent.

## Delivery projection

Map current delivery context to `Delivery State`:

| Authoritative context | Project Delivery State |
| --- | --- |
| `in-focus` | In Focus |
| `eligible` | Eligible |
| `blocked` | Denied |
| `independent` | Independent |
| `Workflow State = Complete` | Released |
| `Workflow State = Superseded` | Superseded |

`Delivery State` never establishes focus, frontier eligibility, dependency state, or
lifecycle authorization.

## Base projection invariants

Validate before mutation:

* `Complete` -> base `Work Status = Done`, `Next Skill = None`, authoritative non-empty
  `Completed On`;
* `Superseded` -> base `Work Status = Done`, `Next Skill = None`, `Completed On = None`, and
  explicit durable retirement authority supplied by the caller;
* all other states -> `Completed On = None`;
* requested select values must already exist in current Project schema;
* `Artifact Type`, `Workflow State`, and base `Next Skill` must satisfy the current route
  table below.

Do not infer `Completed On` from issue `closed_at`.

## Current base route table

| Artifact Type | Workflow State | Allowed base `Next Skill` |
| --- | --- | --- |
| Wayfinder Map | Architecture Decision | `$wayfinder` |
| Wayfinder Map | Ready to Spec | `$to-specs` |
| Wayfinder Map | Spec Delivery | None |
| Wayfinder Map | Architecture Remediation | `$wayfinder` |
| Wayfinder Map | Blocked | None |
| Wayfinder Map | Complete | None |
| Wayfinder Decision | Architecture Decision | `$wayfinder` |
| Wayfinder Decision | Blocked | None |
| Wayfinder Decision | Complete | None |
| Spec | Ready to Ticket | `$to-tickets` |
| Spec | Ready to Implement | None |
| Spec | Ready to Verify | `$verify-spec` |
| Spec | Ready to Review | `$review-spec` |
| Spec | Review Remediation | None |
| Spec | Architecture Remediation | `$architecture-remediation` |
| Spec | Ready to Merge | `$spec-merge-cleanup` |
| Spec | Blocked | None |
| Spec | Complete | None |
| Implementation Ticket | Ready to Implement | `$implement-ticket` |
| Implementation Ticket | Architecture Remediation | `$architecture-remediation` |
| Implementation Ticket | Blocked | None |
| Implementation Ticket | Complete | None |
| Spec Review | Review Remediation | `$to-tickets` or None |
| Spec Review | Architecture Remediation | `$architecture-remediation` |
| Spec Review | Blocked | None |
| Spec Review | Complete | None |
| Review Remediation Ticket | Ready to Implement | `$implement-ticket` |
| Review Remediation Ticket | Architecture Remediation | `$architecture-remediation` |
| Review Remediation Ticket | Blocked | None |
| Review Remediation Ticket | Complete | None |

Every listed Artifact Type also permits `Superseded / None` with explicit retirement
authority.

Context-sensitive `None` means downstream children own the next executable action; it does
not mean the parent is complete.

Reject unlisted combinations rather than guessing.

## Delivery overlay

Validate the base route first, then apply only delivery presentation:

* terminal Complete -> `Done / None / Released`;
* terminal Superseded -> `Done / None / Superseded`;
* Independent active artifact -> preserve base status/next skill, Delivery State Independent;
* focused Wayfinder Map -> `In Progress`, preserve base next skill, In Focus;
* eligible Wayfinder Map -> `Ready`, `$project-delivery-management`, Eligible;
* blocked Wayfinder Map -> `Blocked`, None, Denied;
* Wayfinder-managed descendant -> preserve base lifecycle status/next skill for
  `in-focus|eligible`; for delivery `blocked`, set visible Work Status Blocked while
  preserving its lifecycle next skill; project the matching Delivery State.

Delivery authorization never changes `Workflow State`.

## Terminal contradiction checks

Caller-supplied `Complete` must be supported by owning lifecycle evidence. Tracker
relationships may disprove completion but never establish it by absence.

At minimum reject:

* Wayfinder Map complete while a governed Spec/decision/fog remains unresolved;
* Spec complete while an implementation ticket or conventional Spec Review remains open;
* Spec Review complete while a Review Remediation Ticket remains open.

## Resolve current Project and schema

Resolve exactly one open Project titled `Polaris` for the repository owner. Resolve its
current fields once and require:

* Artifact Type;
* Workflow State;
* Next Skill;
* Work Status;
* Intake State;
* Priority;
* Area;
* Completed On;
* Delivery State.

All required single-select options used by the supplied batch must already exist. Missing
Project/schema/configuration state is `PROJECT TRACKING: DRIFT`; this skill does not create
or repair schema.

## Deterministic execution

Use one reconciliation path:

```text
validate supplied projections
-> resolve Project once
-> read schema once
-> read affected current rows once
-> add only missing members
-> establish post-membership row snapshot
-> compute one complete field-delta plan
-> submit bounded deterministic GraphQL batches
-> verify affected rows once
```

A recoverable membership-add failure permits at most one **state-reconciled** retry:
re-read membership, recompute the still-missing set, and retry only that set through the
same interface. This is ordinary transient-write recovery, not historical conversion.

Do not retry field batches through alternate interfaces, recompute semantic projections in
response to write failures, probe CLI capability with `--help`, or modify Project views,
automations, or schema.

If no membership or field delta exists, return `SYNCED` after verification.

## Mutation ownership

This skill may mutate only Project membership and the supplied current projection fields.
Preserve Area/Priority when omitted. Do not mutate GitHub issue lifecycle state, hierarchy,
dependencies, CCL, delivery focus, branches, or repository content.

## Result

Return exactly one:

```text
PROJECT TRACKING: SYNCED
Artifacts supplied: <n>
Members added: <n>
Field changes: <n>
Verified rows: <n>
```

or:

```text
PROJECT TRACKING: INVALID PROJECTION
Artifact: <identity>
Reason: <invariant failure>
```

or:

```text
PROJECT TRACKING: DRIFT
Reason: <missing/ambiguous project or schema | read/write/verification failure>
Authoritative lifecycle state changed: no
```

Project drift never rolls back authoritative lifecycle work.
