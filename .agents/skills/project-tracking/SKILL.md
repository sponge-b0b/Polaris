---
name: project-tracking
description: Invoked by Polaris lifecycle owners after a durable workflow transition to reconcile the public GitHub Project projection. Internal helper only; never determines workflow truth.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Tracking

Reconcile the public Polaris GitHub Project after the owning workflow has already established the authoritative durable state.

This skill is an **internal projection helper**, not a lifecycle owner, workflow engine, or correctness authority.

## Invocation Boundary

Invoke this skill only from an already-authorized Polaris lifecycle owner after the corresponding tracker/repository transition succeeds, or from an explicit reconciliation flow that has independently recovered the authoritative durable state.

Do not ask the human to invoke this helper as a lifecycle handoff. Return the synchronization result to the caller.

The caller must supply one or more desired **formal artifact projections**. For each artifact provide:

* GitHub issue URL;
* `Artifact Type`;
* `Workflow State`;
* `Next Skill`;
* `Work Status`;
* `Area`;
* `Root Blocker` as `RB-n` or `None`;
* `Completed On` as `YYYY-MM-DD` when `Workflow State = Complete`, otherwise `None`;
* `Priority` only when the caller intentionally owns a priority change.

`Artifact Type = Idea` and `Workflow State = Intake` are outside this helper's current formal-workflow contract. Ideas & Intake remain a pre-workflow Project concern until a dedicated owner exists.

## Authority Rules

The desired projection must come from durable workflow evidence already recovered by the caller.

Never infer semantic workflow state from:

* GitHub issue Open/Closed state;
* current Project fields;
* saved-view position;
* labels;
* hierarchy/sub-issue position alone;
* prior conversation or session memory.

Project values may be read only to detect and repair projection drift.

If the supplied desired projection conflicts with the durable state the caller recovered, return the conflict to the caller rather than choosing a value.

## Projection Invariants

Before mutating the Project, validate:

* `Workflow State = Complete` requires `Work Status = Done`, `Next Skill = None`, and a non-empty `Completed On` date;
* any non-`Complete` projection requires `Completed On = None`;
* a non-empty `Root Blocker` is valid only for `Artifact Type = Review Remediation Ticket` and must match `RB-[0-9]+`;
* `Priority` is optional and is preserved when omitted;
* every requested single-select value must already exist in the Project schema.

Do not create a completion date from the issue's `closedAt` value. GitHub issue closure is not Polaris lifecycle completion.

When an artifact legitimately re-enters the lifecycle from `Complete`, clear `Completed On` as part of the non-Complete projection.

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

Prefer the current native `gh project item-edit` interface. Confirm the installed command exposes the required `--field`, `--value`, `--text`, `--date`, and `--clear` flags before relying on them.

For single-select fields:

```bash
gh project item-edit "$PROJECT_NUMBER" \
  --owner "$OWNER" \
  --url "$ISSUE_URL" \
  --field "Workflow State" \
  --value "$WORKFLOW_STATE"
```

Apply the same pattern to `Artifact Type`, `Next Skill`, `Work Status`, `Area`, and `Priority` when supplied.

For `Root Blocker`, set the desired text or clear the field when the desired value is `None`.

For `Completed On`, set the supplied date only for `Complete`; otherwise clear it.

Clear `Intake State` on formal workflow artifacts if it contains stale data.

Update only fields whose current projection differs from the desired projection. Do not rewrite already-correct fields merely to generate activity.

## 5. Verify the Projection

Re-read the affected item with `gh project item-list`, requesting the relevant fields explicitly, and require exact agreement with the desired projection.

Verification must prove:

* the issue is a Project member;
* every required formal field equals the requested value;
* `Root Blocker` is set or cleared as requested;
* `Completed On` is set or cleared as requested;
* `Priority` changed only when explicitly supplied;
* `Intake State` is empty for a formal artifact.

Do not infer success merely because mutation commands returned zero.

## Failure Semantics

Project synchronization happens **after** semantic workflow state is durable. Therefore a synchronization failure must never roll back, rewrite, reopen, re-close, or otherwise alter the authoritative workflow artifacts merely to make the board match.

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
* set or clear existing Project field values;
* verify the resulting projection.

This helper must not:

* determine lifecycle state;
* create or modify GitHub issues except for the additive `workflow:tracked` label;
* open or close issues;
* create or alter parent/sub-issue or blocking relationships;
* create, delete, or change Project schema, saved views, hierarchy settings, or automation;
* archive or delete formal workflow history;
* commit or modify repository files;
* perform another lifecycle Human Handoff.
