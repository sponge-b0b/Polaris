---
name: review-spec-remediation
description: Internal continuation of `$review-spec` that maintains durable Root Blocker state, applies validated scope corrections without erasing history, and hands only active architecture-conforming remediation to `$to-tickets`.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec Remediation

`$review-spec-remediation` is invoked only by `$review-spec` after a current **Pending Review Remediation** packet is persisted.

It converts already validated review findings and scope corrections into durable remediation state.

It does not review source, create new findings, fix implementation, or independently change finding scope/axis authority.

## Invocation Preconditions

Recover:

* Spec Review issue;
* exact `**Parent Spec:** #<n>` line;
* latest Pending Review Remediation packet;
* current `HEAD`, branch, Spec baseline;
* current passing verification receipt.

Require the packet:

* `Status: pending`;
* `Reviewed HEAD == current HEAD`;
* `Reviewed Baseline == current Spec baseline`;
* branch matches;
* `Spec Body Hash` and `Spec Contract Hash` match the passing verification receipt.

If stale/missing, return a remediation-state error to `$review-spec`.

The packet is the sole current-review input. Do not re-mine historical review text or source code for findings.

## Root Blocker Model

Group accepted Blocking findings by the stable durable invariant they violate, not by file/subsystem/axis.

Preserve existing `RB-*` IDs. Do not broaden an invariant merely to avoid a new root.

Maintain:

* invariant;
* status;
* affected semantic surface/reference families;
* governing architecture when applicable;
* exit checks;
* current evidence;
* cumulative acceptance obligations;
* Owner Overrides;
* Scope retirements.

Architecture roots preserve:

```text
Architecture decision required: No
Governing authority: <authority>
Routing: existing-authority remediation
```

## Finding Reconciliation

Classify each accepted current Blocking finding as exactly one:

* **child symptom**;
* **root-definition gap**;
* **regression**;
* **missed prior finding**;
* **new root**.

Use provenance supplied by `$review-spec`. Do not independently reclassify axis authority.

A missed prior finding makes a root `open`, not `regressed`.

### Root Definition Integrity

A root-definition gap may expand affected semantic surfaces, exit checks, and acceptance obligations while preserving the same stable invariant.

If the invariant itself would materially broaden, create a new root.

Do not let a root become an unlimited thematic container.

## Cumulative Acceptance Matrix

Carry every established cell with one state:

```text
satisfied
open
regressed
unproven
owner-overridden
scope-retired
```

Omission from a later update does not remove a cell.

A satisfied cell stays satisfied unless current accepted evidence violates the same semantic obligation or durable state explicitly supersedes/retires/overrides it.

A new sibling manifestation adds/opens the narrow missing cell; it does not downgrade unrelated satisfied siblings.

A root is active-satisfied only when every non-retired required cell is `satisfied` or `owner-overridden`.

## Scope Correction

`scope-retired` is a durable attribution correction, not an override and not a claim that the historical repository defect was false.

Apply a scope correction only when the current Pending packet explicitly supplies it and its evidence establishes:

1. the root/cell is inherited-only or otherwise not owned by this Spec;
2. no current Spec Contract Manifest obligation requires it;
3. no applicable Architecture Impact/current authority requires it for this Spec;
4. retirement does not remove an active Spec-owned sibling obligation.

Do not independently invent a scope correction.

For a fully unrelated root:

```text
Status: scope-retired
Scope-retirement reason: <ownership + no Spec/Architecture relationship>
Historical finding preserved: yes
```

For a mixed root, mark only unrelated cells `scope-retired` and recompute the root from remaining active cells.

Never use `scope-retired` simply because the violation pre-existed the Spec. Pre-existing behavior that violates an exact Spec/Architecture obligation remains active.

Scope-retired roots/cells:

* remain in historical review state;
* do not count as active Blocking remediation;
* do not go to `$to-tickets` for this Spec;
* may name an external repository follow-up, but this skill does not create that work.

## Architecture-Conformance Gate

Before persisting a new root or materially changed active acceptance obligation, confirm remediation does not require an unresolved architectural choice.

Use only current accepted Architecture findings, existing governing authority, and Spec Architecture Impact.

If correction requires a new owner/path/boundary/dependency/lifecycle choice or conflicting-authority resolution, return a genuine architecture blocker to `$review-spec`.

Do not create Architecture findings here.

## Durable Ledger Format

Use:

```markdown
## Root Blocker Ledger

### RB-<n> — <stable name>
Status: open | satisfied | regressed | unproven | owner-overridden | scope-retired
Invariant: <stable invariant>
Architecture decision required: No
Governing authority: <authority>
Routing: existing-authority remediation
Affected surfaces/reference kinds: <semantic families>
Exit checks: <root-complete proof>
Current evidence:
- <evidence>
Scope-retirement reason: <when applicable>

## Spec Acceptance Matrix

| Root | Surface/reference kind | Production-path obligation | Status | Evidence |
| --- | --- | --- | --- | --- |
```

Treat legacy `closed` as `satisfied`.

Do not let helper/unit proof establish completion when an obligation requires a production path.

## 1. First Remediation Pass

When no ledger exists:

1. synthesize current accepted Blocking findings into stable roots;
2. build initial cumulative matrix;
3. apply architecture-conformance gate;
4. persist the ledger/matrix.

Scope corrections normally apply only to existing durable review state; ignore a correction for a nonexistent historical root/cell as malformed input.

Preserve the exact `**Parent Spec:**` line.

## 2. Recursive Remediation Pass

When durable state exists:

1. recover complete ledger/matrix;
2. preserve every active prior obligation;
3. apply explicit Scope Corrections first;
4. reconcile each current accepted Blocking finding;
5. add root-definition-gap cells without changing invariant identity;
6. update root status/evidence;
7. apply architecture-conformance gate;
8. persist updated cumulative state.

Do not resurrect historical findings unless they remain active cells or are independently validated in the current Pending packet.

### Root Status

Use:

* **open** — active violated obligation;
* **regressed** — previously satisfied behavior was broken later;
* **unproven** — no known violation but required proof insufficient;
* **satisfied** — all active obligations proven;
* **owner-overridden** — owner explicitly removes Blocking requirement;
* **scope-retired** — no active obligation belongs to this Spec after validated attribution correction.

A root with some scope-retired cells and some active cells uses the active-cell-derived status.

### Re-review History

Append a concise dated section containing:

* current independently validated findings by axis;
* applied scope corrections;
* saturation result when present;
* root updates;
* matrix updates.

Preserve historical sections; never rewrite them.

## 3. Remediation Delta

After state is current, compute only **active architecture-conforming Blocking remediation**.

Exclude:

* satisfied cells;
* owner-overridden cells;
* scope-retired cells/roots.

For each actionable root pass to `$to-tickets`:

* stable ID/invariant;
* current active status;
* affected semantic families;
* governing authority;
* every active non-satisfied obligation;
* satisfied preservation cells;
* production-path/negative/fail-closed/regression proof;
* root-complete invariant sweep;
* missed/regressed provenance;
* current review saturation evidence when supplied.

Do not slice latest symptom bullets directly.

Do not create one ticket per symptom when one root-complete ticket can close the invariant.

## 4. Return / Human Handoff

Let:

```text
ACTIVE_BLOCKING_FINDINGS
```

mean current independently validated Blocking findings that remain active after validated scope corrections.

If active architecture-conforming remediation remains, halt using:

> ⚠️ **Spec Review Failed with [X] Blocking Findings.**
>
> I have created or updated the parent tracking issue:
> **`Spec Review: <Feature Name> #<Issue_ID>`**.
>
> Please run:
>
> ```
> $to-tickets Spec Review: <Feature Name> (<Issue URL>)
> ```
>
> `$to-tickets` should slice **Blocking remediation only** unless you explicitly want Advisory findings ticketed.

`[X]` is the number of active current Blocking findings after scope correction, not raw historical findings, roots, or cells.

If Scope Corrections remove all active Blocking findings, return control to `$review-spec`; do not emit `$to-tickets`.

## Owner Overrides

Owner Override remains distinct from Scope retirement.

For an explicit owner override:

* persist scope/rationale;
* mark applicable root/cell `owner-overridden`;
* remove from Blocking counts;
* suppress the unchanged finding later.

Do not use Owner Override to repair attribution mistakes that meet Scope Correction rules.
