---
name: project-tracking
description: Invoked by Polaris lifecycle owners after a durable workflow transition to reconcile the public GitHub Project projection. Internal helper only; never determines workflow truth.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Tracking

Reconcile the public Polaris GitHub Project after the owning workflow has already established the authoritative durable state.

This skill is an **internal projection helper**, not a lifecycle owner, workflow engine, scheduler, or correctness authority.

## Invocation Boundary

Invoke this skill only from an already-authorized Polaris lifecycle owner after the corresponding tracker/repository transition succeeds, or from an explicit reconciliation flow that has independently recovered the authoritative durable state.

Do not ask the human to invoke this helper as a lifecycle handoff. Return the synchronization result to the caller.

The caller must supply one or more desired **base formal artifact projections**. For each artifact provide:

* GitHub issue URL;
* `Artifact Type`;
* `Workflow State`;
* `Next Skill` — the ordinary lifecycle next action before any project-delivery focus overlay;
* `Work Status` — the ordinary lifecycle work status before any project-delivery focus overlay;
* `Area`;
* `Root Blocker` as `RB-n` or `None`;
* `Completed On` as `YYYY-MM-DD` when `Workflow State = Complete`, otherwise `None`;
* `Priority` only when the caller intentionally owns a priority change;
* `Project Delivery State` when project-delivery focus is active for the artifact: `focused | focused-stalled | eligible-unfocused | ineligible`.

`Artifact Type = Idea` and `Workflow State = Intake` are outside this helper's current formal-workflow contract. Ideas & Intake remain a pre-workflow Project concern until a dedicated owner exists.

### Project Delivery Context

Project-delivery focus is authoritative only through `$project-delivery-management` and canonical tracker state. This helper never derives focus from Project values.

For a Wayfinder-managed artifact **after project-delivery bootstrap activation**, the caller must recover current governance/focus through `$project-delivery-management` and supply exactly one `Project Delivery State`:

* `focused` — at least one current governing Wayfinder is focused and the artifact is not complete;
* `focused-stalled` — Wayfinder Map only; the map remains focused/eligible but narrower work is currently stalled by lower-level blockers;
* `eligible-unfocused` — the artifact belongs only to currently eligible but unfocused delivery scope;
* `ineligible` — project-delivery authorization currently forbids advancement because the governing scope/artifact is genuinely ineligible.

When a Spec or downstream artifact has multiple current governing Wayfinders, one focused eligible governor is sufficient for `focused`.

Before bootstrap activation, or for an intentionally non-Wayfinder artifact, omit `Project Delivery State`; use the ordinary lifecycle projection unchanged.

The supplied project-delivery classification is routing context from the authoritative owner, not a fact this helper may reconstruct from Project state. If the caller cannot establish it unambiguously, reject the projection rather than guess.

## Authority Rules

The base projection and project-delivery context must come from durable workflow evidence already recovered by the caller.

Never infer semantic workflow or delivery state from:

* GitHub issue Open/Closed state;
* current Project fields;
* saved-view position;
* labels;
* hierarchy/sub-issue position alone;
* prior conversation or session memory.

Project values may be read only to detect and repair projection drift.

If the supplied desired projection conflicts with the durable state the caller recovered, return the conflict to the caller rather than choosing a value.

## Projection Invariants

Before mutating the Project, validate the **base lifecycle projection** first:

* `Workflow State = Complete` requires base `Work Status = Done`, base `Next Skill = None`, and a non-empty `Completed On` date;
* any non-`Complete` projection requires `Completed On = None`;
* a non-empty `Root Blocker` is valid only for `Artifact Type = Review Remediation Ticket` and must match `RB-[0-9]+`;
* `Priority` is optional and is preserved when omitted;
* every requested single-select value must already exist in the Project schema;
* the requested base `Artifact Type`, `Workflow State`, and `Next Skill` combination is allowed by **Base Artifact Route Compatibility** below.

Do not create a completion date from the issue's `closedAt` value. GitHub issue closure is not Polaris lifecycle completion.

When an artifact legitimately re-enters the lifecycle from `Complete`, clear `Completed On` as part of the non-Complete projection.

### Base Artifact Route Compatibility

`Next Skill` in the caller's base projection names the next human-invocable lifecycle/HITL entry point **before focus overlay** for the artifact represented by that Project row. Never copy a descendant artifact's next action onto its parent.

`None` is correct when the artifact remains active but the next executable work belongs to a child or downstream artifact.

Allow only these base combinations:

| Artifact Type | Workflow State | Allowed base `Next Skill` |
| --- | --- | --- |
| Wayfinder Map | Architecture Decision | `$wayfinder` |
| Wayfinder Map | Ready to Spec | `$to-specs` or `None` |
| Wayfinder Map | Architecture Remediation | `$wayfinder` |
| Wayfinder Map | Blocked | `None` |
| Wayfinder Map | Complete | `None` |
| Wayfinder Decision | Architecture Decision | `$wayfinder` |
| Wayfinder Decision | Blocked | `None` |
| Wayfinder Decision | Complete | `None` |
| Spec | Ready to Ticket | `$to-tickets` |
| Spec | Ready to Implement | `None` |
| Spec | Ready to Verify | `$verify-spec` |
| Spec | Ready to Review | `$review-spec` |
| Spec | Review Remediation | `None` |
| Spec | Architecture Remediation | `$architecture-remediation` |
| Spec | Ready to Merge | `$spec-merge-cleanup` |
| Spec | Blocked | `None` |
| Spec | Complete | `None` |
| Implementation Ticket | Ready to Implement | `$implement-ticket` |
| Implementation Ticket | Architecture Remediation | `$architecture-remediation` |
| Implementation Ticket | Blocked | `None` |
| Implementation Ticket | Complete | `None` |
| Spec Review | Review Remediation | `$to-tickets` or `None` |
| Spec Review | Architecture Remediation | `$architecture-remediation` |
| Spec Review | Blocked | `None` |
| Spec Review | Complete | `None` |
| Review Remediation Ticket | Ready to Implement | `$implement-ticket` |
| Review Remediation Ticket | Awaiting Root Verification | `$verify-root-closure` |
| Review Remediation Ticket | Architecture Remediation | `$architecture-remediation` |
| Review Remediation Ticket | Blocked | `None` |
| Review Remediation Ticket | Complete | `None` |

Context-sensitive base `None` cases are intentional:

* a `Spec` in `Ready to Implement` waits on its implementation-ticket children;
* a `Spec` in `Review Remediation` waits on its Spec Review/remediation lineage;
* a `Spec Review` in `Review Remediation` uses `$to-tickets` before executable remediation tickets exist and `None` while those child tickets own the next action;
* a `Wayfinder Map` in `Ready to Spec` uses `$to-specs` when specification work is the next human action and `None` while already-handed-off Specs own the active downstream work.

Any base combination not listed above is invalid. Reject it before applying project-delivery overlay rather than normalizing it to a nearby value.

### Project Delivery Overlay

After the base lifecycle projection passes validation, apply the focus overlay without changing `Artifact Type`, `Workflow State`, `Area`, `Root Blocker`, `Completed On`, or `Priority`.

`Workflow State` always describes the artifact's actual lifecycle stage. Focus never rewrites it to `Blocked`, `Ready`, or another stage merely for scheduling presentation.

For `Workflow State = Complete`, project exactly:

```text
Work Status = Done
Next Skill = None
```

Do not accept contradictory non-complete focus context for a completed artifact; supplying `Project Delivery State` with `Workflow State = Complete` is invalid.

For a **Wayfinder Map**:

| Project Delivery State | Projected `Work Status` | Projected `Next Skill` |
| --- | --- | --- |
| `focused` | `In Progress` | preserve validated base `Next Skill` |
| `focused-stalled` | `In Progress` | preserve validated base `Next Skill` |
| `eligible-unfocused` | `Ready` | `$project-delivery-management` |
| `ineligible` | `Blocked` | `None` |

Rules:

* `focused-stalled` is valid only for `Artifact Type = Wayfinder Map`;
* `eligible-unfocused` is invalid with `Workflow State = Blocked` or `Complete`;
* `focused` / `focused-stalled` are invalid with `Workflow State = Blocked` or `Complete`;
* an eligible-but-unfocused Wayfinder must never advertise `$wayfinder` or `$to-specs` directly;
* a focused-but-stalled Wayfinder remains `In Progress`; do not falsely project it as dependency-blocked.

For a **Wayfinder-managed descendant** (`Wayfinder Decision`, `Spec`, `Implementation Ticket`, `Spec Review`, or `Review Remediation Ticket`):

| Project Delivery State | Projected `Work Status` | Projected `Next Skill` |
| --- | --- | --- |
| `focused` | preserve validated base `Work Status` | preserve validated base `Next Skill` |
| `eligible-unfocused` | `Ready` | `None` |
| `ineligible` | `Blocked` | `None` |

A descendant governed only by an unfocused Wayfinder preserves its `Workflow State` while its executable handoff is suppressed. When a current governor becomes focused, its ordinary validated lifecycle `Next Skill` is restored on the next reconciliation.

Do not use project-delivery overlay to bypass a base route incompatibility. The helper must first prove what the artifact would advertise absent focus, then apply only the scheduling overlay above.

`$project-delivery-management` is therefore a valid **final Project `Next Skill` option only for eligible-unfocused Wayfinder Map rows**. It is not a base lifecycle route and must not appear on descendant rows.

### Completion Contradiction Checks

A caller-supplied `Complete` projection still requires durable lifecycle authority. This helper may use tracker relationships only to detect a contradiction that proves the requested completion is impossible; it must never use issue closure or an all-closed descendant set to infer completion by itself.

Before accepting `Workflow State = Complete`:

* for a `Wayfinder Map`, recover its complete currently governed Spec set from both forward `Derived Spec` / `Remediation Spec` handoff metadata and reverse `wayfinder-source` / `wayfinder-remediation` provenance; reject completion if any governed Derived or Remediation Spec remains open;
* for a `Wayfinder Map`, also reject completion when an unresolved Wayfinder decision or in-scope `Not yet specified` fog remains;
* preserve the distinction between original `wayfinder-source` provenance and additive remediation governance; do not rewrite one role into the other while checking completion;
* for a `Spec`, reject completion if any implementation-ticket child or associated Spec Review remains open;
* for a `Spec Review`, reject completion if any review-remediation ticket remains open.

An open required descendant/decision/fog is contradiction evidence only. The absence of one is not completion evidence.

If route compatibility, project-delivery overlay, or a completion contradiction fails, do not mutate the Project. Return:

```text
PROJECT TRACKING: INVALID PROJECTION
Artifact: <title / URL>
Rejected projection: <field=value summary>
Reason: <base route incompatibility, invalid project-delivery overlay, or completion contradiction>
```

## 1. Resolve the Existing Project

Use the repository owner and the Project title `Polaris`. Do not hard-code the Project number.

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
OWNER=${REPO%%/*}
```

Resolve exactly one open Project titled `Polaris` with `gh project list --owner "$OWNER" --format json`.

Fail closed if the Project cannot be read, is missing, or is ambiguous.

Require authenticated `gh` access with the `project` scope. If needed, the operator can authorize it with:

```bash
gh auth refresh -s project
```

## 2. Validate the Existing Schema

Read the schema before mutation:

```bash
gh project field-list "$PROJECT_NUMBER" \
  --owner "$OWNER" \
  --limit 100 \
  --format json
```

Require these existing fields:

* `Artifact Type` — single select;
* `Workflow State` — single select;
* `Next Skill` — single select;
* `Work Status` — single select;
* `Intake State` — single select;
* `Priority` — single select;
* `Area` — single select;
* `Root Blocker` — text;
* `Completed On` — date.

When project-delivery bootstrap is active, also require the existing `Next Skill` field to contain exactly one option named:

```text
$project-delivery-management
```

The option is introduced only by an explicit one-time operator rollout. Steady-state `$project-tracking` must never create or repair it.

Validate every requested select value against the field's existing options.

**Do not create, delete, rename, or repair Projects, fields, options, views, workflows, or auto-add rules.** Schema failure is projection drift that must be reported.

## 3. Ensure Formal Artifact Membership

For each GitHub issue projection:

1. read Project items and locate the item by exact issue URL;
2. if absent, add it with `gh project item-add`;
3. if present, reuse the existing Project item;
4. never archive or delete a formal workflow artifact merely because it completed.

Use direct Project membership as the synchronization mechanism. The `workflow:tracked` auto-add rule is only a safety net and may be asynchronous.

For an active formal issue, ensure the `workflow:tracked` label exists on the issue without removing any other labels. The label aids discovery; it does not establish lifecycle state.

## 4. Reconcile Desired Fields

Apply the **final projection after Project Delivery Overlay**, not the unmodified base values.

Prefer the current native `gh project item-edit` interface. Confirm the installed command exposes the required `--field`, `--value`, `--text`, `--date`, and `--clear` flags before relying on them.

For single-select fields:

```bash
gh project item-edit "$PROJECT_NUMBER" \
  --owner "$OWNER" \
  --url "$ISSUE_URL" \
  --field "Workflow State" \
  --value "$WORKFLOW_STATE"
```

Apply the same pattern to `Artifact Type`, final `Next Skill`, final `Work Status`, `Area`, and `Priority` when supplied.

For `Root Blocker`, set the desired text or clear the field when the desired value is `None`.

For `Completed On`, set the supplied date only for `Complete`; otherwise clear it.

Clear `Intake State` on formal workflow artifacts if it contains stale data.

Update only fields whose current projection differs from the desired projection. Do not rewrite already-correct fields merely to generate activity.

## 5. Verify the Projection

Re-read the affected item with `gh project item-list`, requesting the relevant fields explicitly, and require exact agreement with the **final focus-aware projection**.

Verification must prove:

* the issue is a Project member;
* every required formal field equals the final projected value;
* `Root Blocker` is set or cleared as requested;
* `Completed On` is set or cleared as requested;
* `Priority` changed only when explicitly supplied;
* `Intake State` is empty for a formal artifact.

Do not infer success merely because mutation commands returned zero.

## Failure Semantics

Project synchronization happens **after** semantic workflow/project-delivery state is durable. Therefore a synchronization failure must never roll back, rewrite, reopen, re-close, refocus, or otherwise alter the authoritative workflow artifacts merely to make the board match.

An invalid requested base projection or project-delivery overlay is rejected before mutation under **Projection Invariants**. It is not Project drift.

On any membership, permission, schema, network, mutation, or verification failure, return:

```text
PROJECT TRACKING: DRIFT
Artifact: <title / URL>
Desired projection: <field=value summary>
Unreconciled: <membership or exact field mismatches>
Cause: <concise failure>
```

The parent lifecycle owner continues to treat its durable tracker/repository result as authoritative and reports the Project drift. A later lifecycle entry may invoke this helper again after recovering durable state.

On success, return:

```text
PROJECT TRACKING: SYNCED
Artifact: <title / URL>
Projection: <field=value summary>
```

For multiple artifacts, return one result per artifact plus an aggregate `SYNCED` only when every artifact verifies successfully.

## Scope Boundary

This helper may:

* ensure formal issue membership in the existing Polaris Project;
* ensure the `workflow:tracked` safety-net label on active formal issues;
* validate an authoritative project-delivery context supplied by the owning lifecycle;
* apply the deterministic focus-aware `Work Status` / `Next Skill` projection overlay;
* set or clear existing Project field values;
* verify the resulting projection.

This helper must not:

* determine lifecycle state or project focus;
* infer project-delivery state from Project fields or incidental tracker metadata;
* create or modify GitHub issues except for the additive `workflow:tracked` label;
* open or close issues;
* create or alter parent/sub-issue or blocking relationships;
* create, delete, or change Project schema, field options, saved views, hierarchy settings, or automation;
* archive or delete formal workflow history;
* commit or modify repository files;
* perform another lifecycle Human Handoff.