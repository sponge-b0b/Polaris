---
name: project-tracking
description: Invoked by Polaris lifecycle owners after a durable workflow transition to reconcile the public GitHub Project projection. Internal helper only; never determines workflow truth.
compatibility: product=codex product=claude-code system=gh network=required
disable-model-invocation: true
---

# Project Tracking

Reconcile the public Polaris GitHub Project after the owning lifecycle has already established authoritative durable state.

`$project-tracking` is an internal projection helper. It does not own lifecycle state, delivery focus, scheduling, or correctness.

## Invocation Boundary

`$project-tracking` supports two internal modes.

### Formal Artifact Projection

Invoke only:

* from an already-authorized Polaris lifecycle owner after its authoritative tracker/repository transition succeeds; or
* from an explicit reconciliation flow that independently recovered the authoritative durable state.

The caller supplies one or more desired **base formal artifact projections**. For each artifact provide:

* GitHub issue URL;
* `Artifact Type`;
* `Workflow State`;
* `Next Skill` — ordinary lifecycle next action before project-delivery overlay;
* `Work Status` — ordinary lifecycle status before project-delivery overlay;
* `Area`;
* `Root Blocker` as `RB-n` or `None`;
* `Completed On` as `YYYY-MM-DD` only when `Workflow State = Complete`, otherwise `None`;
* `Priority` only when the caller intentionally owns a priority change;
* after project-delivery bootstrap, `Project Delivery State` for every non-complete formal artifact: `in-focus | eligible | blocked | independent`.

`Artifact Type = Idea` and `Workflow State = Intake` are outside this helper.

### Wayfinder Delivery Overlay Sync

Only `$project-delivery-management` may invoke this mode.

The caller supplies one or more exact open Wayfinder Map URLs plus their current authoritative `Project Delivery State`: `in-focus | eligible | blocked`. This mode does not determine or change lifecycle state. It reads the existing Project row, requires `Artifact Type = Wayfinder Map`, preserves the current projected `Workflow State`, and derives only the base Wayfinder route needed to re-apply the delivery overlay:

| Existing `Workflow State` | Base `Work Status` | Base `Next Skill` |
| --- | --- | --- |
| Architecture Decision | Ready | `$wayfinder` |
| Ready to Spec | Ready | `$to-specs` |
| Spec Delivery | In Progress | None |
| Architecture Remediation | Ready | `$wayfinder` |
| Blocked | Blocked | None |

Any other existing open Wayfinder workflow state is projection drift and fails closed. This mode may repair `Delivery State`, final `Work Status`, and final `Next Skill` only; it never rewrites `Workflow State`.

Do not hand `$project-tracking` itself to the human. Return its result to the caller.

## Authority Rules

The caller's base projection and project-delivery context must come from durable workflow evidence already recovered by the caller.

Never infer workflow or delivery truth from:

* GitHub issue Open/Closed state alone;
* current Project fields;
* labels;
* saved-view position;
* hierarchy/sub-issue position alone;
* prior conversation/session memory.

Project state may be read only to detect and repair projection drift.

Project-delivery focus is authoritative only through `$project-delivery-management` and canonical tracker state. `$project-tracking` never derives focus from Project values.

After project-delivery bootstrap, every formal artifact has exactly one visible delivery relationship:

* `Workflow State = Complete` → `Released`; no caller-supplied project-delivery context is required;
* non-complete Wayfinder-managed artifact governed by at least one currently focused Wayfinder → caller supplies `in-focus`;
* non-complete Wayfinder-managed artifact governed by no focused Wayfinder but at least one frontier-eligible Wayfinder → caller supplies `eligible`;
* non-complete Wayfinder-managed artifact for which no governing Wayfinder is currently frontier-eligible → caller supplies `blocked`;
* non-complete formal artifact durably established as intentionally outside Wayfinder delivery governance → caller supplies `independent`.

For multiple governing Wayfinders, one focused eligible governor is sufficient for `in-focus`; otherwise one eligible governor is sufficient for `eligible`.

`independent` is an explicit durable classification, not a fallback for missing or ambiguous Wayfinder provenance. A Wayfinder-managed artifact with unresolved governance is invalid rather than `independent`.

Before project-delivery bootstrap, `Delivery State` is outside this helper's required projection contract.

If caller-supplied durable state is contradictory or ambiguous, reject it. Do not repair semantic state from the Project.

### Visible Delivery State Projection

Map authoritative context into the Project's universal `Delivery State` field:

| Authoritative context | Project `Delivery State` |
| --- | --- |
| `in-focus` | In Focus |
| `eligible` | Eligible |
| `blocked` | Denied |
| `independent` | Independent |
| `Workflow State = Complete` | Released |

`Delivery State` answers only the artifact's current relationship to project-level delivery authorization. `Denied` means current project-delivery authorization forbids advancement; it is distinct from lifecycle/execution `Blocked` in `Workflow State` or `Work Status`. The field never establishes or changes focus, frontier eligibility, dependency state, lifecycle state, or authorization.

A focused Wayfinder with narrower stalled work remains `In Focus`; stalledness is reported by its owning lifecycle and must not create a separate Delivery State value.

## Projection Invariants

Validate the base lifecycle projection before any Project mutation:

* `Workflow State = Complete` requires base `Work Status = Done`, base `Next Skill = None`, and non-empty `Completed On`;
* non-`Complete` requires `Completed On = None`;
* non-empty `Root Blocker` is valid only for `Artifact Type = Review Remediation Ticket` and must match `RB-[0-9]+`;
* `Priority` is preserved when omitted;
* requested single-select values must exist in the Project schema;
* `Artifact Type`, `Workflow State`, and base `Next Skill` must satisfy **Base Artifact Route Compatibility**.

Never infer `Completed On` from issue closure.

When an artifact legitimately re-enters from `Complete`, clear `Completed On` and require its current non-complete `Project Delivery State` to be re-established from durable authority.

### Base Artifact Route Compatibility

`Next Skill` names the next human-invocable lifecycle/HITL entry point for that Project row before focus overlay. Never copy a descendant's next action onto its parent.

`None` is correct when the artifact remains active while child/downstream work owns the next executable action.

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
| Review Remediation Ticket | Awaiting Root Verification | `$verify-root-closure` |
| Review Remediation Ticket | Architecture Remediation | `$architecture-remediation` |
| Review Remediation Ticket | Blocked | None |
| Review Remediation Ticket | Complete | None |

Context-sensitive `None` cases:

* `Spec / Ready to Implement` waits on implementation-ticket children;
* `Spec / Review Remediation` waits on Spec Review/remediation lineage;
* `Spec Review / Review Remediation` uses `$to-tickets` before executable remediation tickets exist and `None` while those children own the next action;
* `Wayfinder Map / Spec Delivery` means durable Derived/Remediation Spec handoffs exist and at least one governed Spec remains open; those Specs own the next executable action.

`Wayfinder Map / Ready to Spec` means specification itself is next. Once durable Spec handoffs exist with active governed Specs, do not leave the map in `Ready to Spec`.

Reject any unlisted combination.

### Project Delivery Overlay

Validate the base route first. Then apply delivery coordination without changing `Artifact Type`, `Workflow State`, `Area`, `Root Blocker`, `Completed On`, or `Priority`.

For `Workflow State = Complete` project exactly:

```text
Work Status = Done
Next Skill = None
Delivery State = Released
```

For a non-complete artifact with `Project Delivery State = independent`, preserve base `Work Status` and base `Next Skill` and project `Delivery State = Independent`.

For a **Wayfinder Map**:

| Project Delivery State | Final `Work Status` | Final `Next Skill` | Final `Delivery State` |
| --- | --- | --- | --- |
| `in-focus` | In Progress | preserve base | In Focus |
| `eligible` | Ready | `$project-delivery-management` | Eligible |
| `blocked` | Blocked | None | Denied |

Rules:

* `in-focus` and `eligible` are invalid with `Workflow State = Blocked`;
* an eligible Wayfinder never advertises `$wayfinder` or `$to-specs`;
* a focused-but-stalled Wayfinder remains `in-focus` / `In Focus` and `In Progress`.

For a **Wayfinder-managed descendant** (`Wayfinder Decision`, `Spec`, `Implementation Ticket`, `Spec Review`, `Review Remediation Ticket`):

| Project Delivery State | Final `Work Status` | Final `Next Skill` | Final `Delivery State` |
| --- | --- | --- | --- |
| `in-focus` | preserve base | preserve base | In Focus |
| `eligible` | Ready | None | Eligible |
| `blocked` | Blocked | None | Denied |

A descendant governed only by an unfocused eligible Wayfinder preserves lifecycle stage while executable handoff is suppressed.

`$project-delivery-management` is a valid final Project `Next Skill` only for an eligible Wayfinder Map row.

### Completion Contradiction Checks

A caller-supplied `Complete` projection requires durable lifecycle authority. Tracker relationships may only prove that completion is impossible; they never establish completion by absence.

Before accepting `Complete`:

* Wayfinder Map — reject if any currently governed Derived/Remediation Spec remains open, any unresolved Wayfinder decision remains, or in-scope `Not yet specified` fog remains;
* preserve original `wayfinder-source` versus additive `wayfinder-remediation` provenance while checking governed Specs;
* Spec — reject if any implementation-ticket child or associated Spec Review remains open;
* Spec Review — reject if any review-remediation ticket remains open.

If route compatibility, delivery overlay, or completion contradiction fails, do not mutate the Project:

```text
PROJECT TRACKING: INVALID PROJECTION
Artifact: <title / URL>
Rejected projection: <field=value summary>
Reason: <concise invariant failure>
```

## Execution Contract

Use the deterministic command path below for steady-state projection and overlay sync.

Do **not**:

* probe `gh` capabilities with `--help`;
* try alternate command/flag combinations;
* retry a failed command using a different interface;
* inspect or repair Project views, workflows, auto-add rules, or schema;
* narrate successful intermediate discovery, field edits, waits, or no-op checks.

The supported baseline is GitHub CLI `gh 2.97.0` or newer with authenticated `project` scope.

If a prescribed command is unsupported or fails because of CLI/API compatibility, return `PROJECT TRACKING: DRIFT`. Do not discover another interface during the lifecycle run.

For `gh 2.97.0`, **never combine** `gh project item-list --format json` with `--field` / `--field-id`.

Steady-state execution is:

```text
validate projection
→ resolve Project once
→ read schema once
→ read affected current rows once
→ add only missing members
→ compute field deltas
→ submit one batched GraphQL mutation
→ verify affected rows once
```

If no membership or field delta exists, skip mutation and return `SYNCED` after verification.

## 1. Resolve the Existing Project

Resolve repository owner once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
OWNER=${REPO%%/*}
```

Resolve exactly one open Project titled `Polaris` once:

```bash
gh project list --owner "$OWNER" --format json
```

Capture its Project number and GraphQL node ID. Fail closed if unreadable, missing, or ambiguous.

Do not hard-code the Project number or node ID.

Do not run `gh auth status` or `gh auth refresh` during normal reconciliation. Authentication failure is Project drift; the operator may repair auth outside this helper.

## 2. Read and Validate Schema Once

Run exactly once per invocation:

```bash
gh project field-list "$PROJECT_NUMBER" \
  --owner "$OWNER" \
  --limit 100 \
  --format json
```

Require existing fields:

* `Artifact Type` — single select;
* `Workflow State` — single select;
* `Next Skill` — single select;
* `Work Status` — single select;
* `Intake State` — single select;
* `Priority` — single select;
* `Area` — single select;
* `Root Blocker` — text;
* `Completed On` — date.

When project-delivery bootstrap is active, additionally require:

* `Delivery State` — single select with `In Focus`, `Eligible`, `Denied`, `Independent`, `Released`;
* `Workflow State` option `Spec Delivery`;
* `Next Skill` option `$project-delivery-management`.

If these projection additions are missing, return drift and report the exact missing Project schema. Steady-state `$project-tracking` never mutates schema.

From this one response capture:

* each required field's GraphQL node ID;
* every requested single-select option ID.

Validate only the fields/options required by the supplied projections. Do not inspect unrelated Project configuration.

## 3. Read Affected Current Rows Once

Read Project items once for all supplied artifacts:

```bash
gh project item-list "$PROJECT_NUMBER" \
  --owner "$OWNER" \
  --limit 1000 \
  --field "Artifact Type" \
  --field "Workflow State" \
  --field "Delivery State" \
  --field "Next Skill" \
  --field "Work Status" \
  --field "Intake State" \
  --field "Priority" \
  --field "Area" \
  --field "Root Blocker" \
  --field "Completed On"
```

Do not add `--format json` to this command on `gh 2.97.0`.

Locate each supplied artifact by repository + issue number/URL and capture:

* Project item node ID;
* current required field values.

### Missing Membership

Direct Project membership is the synchronization mechanism.

If an artifact is absent, add it once:

```bash
gh project item-add "$PROJECT_NUMBER" \
  --owner "$OWNER" \
  --url "$ISSUE_URL" \
  --format json
```

Capture the returned item ID when available.

If any item was added, rerun the affected-row read once after all additions so every target has a current item ID/value snapshot.

Do not maintain or depend on the `workflow:tracked` label. Existing auto-add automation may remain a safety net, but `$project-tracking` neither waits for it nor mutates issue labels.

Never archive/delete formal workflow artifacts merely because they completed.

## 4. Compute the Minimal Field Delta

Compare each final projection against its current Project row.

Write only differences.

Rules:

* `Artifact Type`, `Workflow State`, final `Delivery State`, final `Next Skill`, final `Work Status`, and `Area` → set only when different;
* after project-delivery bootstrap, never intentionally leave `Delivery State` empty for a formal artifact;
* `Priority` → preserve unless caller supplied it; then set only when different;
* `Root Blocker = RB-n` → set text only when different;
* `Root Blocker = None` → clear only when currently populated;
* `Completed On` → set date only for `Complete` and only when different; otherwise clear only when populated;
* `Intake State` → clear only when populated.

If delta count is zero, skip Section 5 and verify.

## 5. Apply All Field Deltas in One GraphQL Request

Do not use one `gh project item-edit` process per field.

GitHub's `updateProjectV2ItemFieldValue` still updates one field value per mutation field, but a GraphQL mutation operation may contain multiple aliased top-level mutation fields. Batch **all** field deltas for **all supplied artifacts** into one `gh api graphql` request.

Use:

* `updateProjectV2ItemFieldValue` to set single-select, text, or date values;
* `clearProjectV2ItemFieldValue` to clear values.

Example shape:

```graphql
mutation {
  u1: updateProjectV2ItemFieldValue(
    input: {
      projectId: "<PROJECT_ID>"
      itemId: "<ITEM_ID>"
      fieldId: "<FIELD_ID>"
      value: { singleSelectOptionId: "<OPTION_ID>" }
    }
  ) {
    projectV2Item { id }
  }

  u2: updateProjectV2ItemFieldValue(
    input: {
      projectId: "<PROJECT_ID>"
      itemId: "<ITEM_ID>"
      fieldId: "<ROOT_BLOCKER_FIELD_ID>"
      value: { text: "RB-17" }
    }
  ) {
    projectV2Item { id }
  }

  c1: clearProjectV2ItemFieldValue(
    input: {
      projectId: "<PROJECT_ID>"
      itemId: "<ITEM_ID>"
      fieldId: "<INTAKE_STATE_FIELD_ID>"
    }
  ) {
    projectV2Item { id }
  }
}
```

Submit the complete generated operation exactly once:

```bash
gh api graphql -f query="$MUTATION"
```

Top-level GraphQL mutation fields execute serially, so preserve a deterministic alias/order.

Requirements:

* one alias per delta;
* use captured Project/item/field/option IDs rather than field-name discovery during mutation;
* interpolate only controlled Project values, `RB-n`, and ISO dates; GraphQL-escape any text value;
* require a successful API response with no GraphQL `errors`;
* require every mutation alias to return a non-empty `projectV2Item.id`.

If the batch returns any error or incomplete result, report drift. Do not retry failed fields individually through `gh project item-edit`.

GitHub Projects v2 does not provide a REST endpoint that replaces this Project-field mutation. Do not use repository issue-field REST endpoints as Project fields.

## 6. Verify Once

Re-run the exact affected-row command from Section 3 once after mutation.

Require exact agreement with every final projection:

* every artifact is a Project member;
* required formal fields equal final projected values;
* after project-delivery bootstrap, every formal artifact has exactly one valid `Delivery State` value;
* `Root Blocker` is set/cleared as requested;
* `Completed On` is set/cleared as requested;
* `Priority` changed only when supplied;
* `Intake State` is empty.

Do not infer success from mutation exit status alone.

## Operational Output

Keep successful reconciliation silent internally until final verification.

Do not emit progress narration for:

* Project discovery;
* schema reads;
* current-row reads;
* individual membership adds;
* delta construction;
* individual GraphQL mutation aliases;
* waiting for API calls;
* successful no-op checks.

Return only the final synchronization result to the lifecycle owner unless an invalid projection or drift requires early return.

On success:

```text
PROJECT TRACKING: SYNCED
Artifact: <title / URL>
Projection: <field=value summary>
```

For multiple artifacts, return one result per artifact and aggregate `PROJECT TRACKING: SYNCED` only when every artifact verifies.

## Failure Semantics

Project synchronization happens after authoritative workflow/project-delivery state is durable. A synchronization failure never rolls back, rewrites, reopens, recloses, refocuses, or otherwise changes authoritative workflow state merely to match the Project.

On membership, auth, schema, network, API, mutation, CLI-contract, or verification failure:

```text
PROJECT TRACKING: DRIFT
Artifact: <title / URL>
Desired projection: <field=value summary>
Unreconciled: <membership or exact field mismatches>
Cause: <concise failure>
```

The lifecycle owner continues to treat durable tracker/repository state as authoritative and reports the drift.

## Scope Boundary

This helper may:

* ensure formal issue membership in the existing Polaris Project;
* validate caller-supplied project-delivery context;
* apply the deterministic delivery overlay;
* project the universal visible `Delivery State` field;
* set/clear existing Project field values;
* verify final projection.

This helper must not:

* determine lifecycle state or project focus;
* infer delivery state from Project fields or incidental tracker metadata;
* modify GitHub issue labels or issue content;
* open/close issues;
* create/change parent, sub-issue, or blocking relationships;
* create/delete/repair Project schema, options, views, workflows, hierarchy, or automation;
* archive/delete formal workflow history;
* modify repository files;
* perform another lifecycle Human Handoff.