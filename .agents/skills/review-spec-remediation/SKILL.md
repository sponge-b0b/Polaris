---
name: review-spec-remediation
description: Invoked only by `$review-spec` when a review returns Blocking findings. Maintains the durable Root Blocker Ledger and cumulative acceptance matrix, then hands architecture-conforming remediation to `$to-tickets`.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec Remediation

`$review-spec-remediation` converts Blocking `$review-spec` findings into durable remediation state.

It does not fix source code.

If a Blocking Architecture finding has `Architecture decision required: Yes`, return it to `$review-spec`. Unresolved architecture must not become ordinary remediation work.

## Root Blocker Model

Group findings by the **durable invariant** they violate, not by file, subsystem, symptom, or reviewing axis.

An `RB-*` ID denotes one stable invariant.

Preserve existing IDs. Do not broaden an existing invariant merely to keep a new finding under the same root.

For each root maintain:

* invariant;
* status;
* affected surface/reference families;
* governing architecture when applicable;
* exit checks;
* current evidence;
* cumulative acceptance obligations;
* Owner Overrides.

For Architecture roots preserve:

```text
Architecture decision required: No
Governing authority: <ADR/doc/invariant>
Routing: <existing-authority remediation>
```

Do not reinterpret `$review-architecture`.

### Finding Reconciliation

Classify each Blocking finding as exactly one of:

* **child symptom** — already derivable from the existing root invariant and closure domain;
* **root-definition gap** — same durable invariant, but the recorded affected surfaces, exit checks, or acceptance matrix were incomplete;
* **regression** — previously satisfied behavior was introduced or broken after the last satisfied `HEAD`;
* **missed prior finding** — the violation already existed at the last satisfied `HEAD`;
* **new root** — a genuinely distinct durable invariant.

Use the provenance classification supplied by `$review-spec`.

Do not label a newly discovered violation `regression` merely because its root was previously satisfied.

### Root Definition Integrity

A root-definition gap may expand:

* affected surface/reference families;
* exit checks;
* acceptance obligations.

It must not materially change what the invariant means.

If accommodating a finding requires broadening the invariant itself, create a new root instead.

Do not allow an existing root to become an ever-expanding container for related architectural concerns.

## Cumulative Acceptance Matrix

Acceptance obligations are cumulative for the lifetime of an active root.

Carry forward every established cell, including:

```text
satisfied
open
regressed
unproven
owner-overridden
```

A later review may update a cell's status or evidence, but omission from a newer review does not remove it.

Remove or replace an obligation only when durable state explicitly establishes that it is:

* superseded by an equivalent obligation;
* no longer required by current Spec/architecture; or
* Owner-overridden.

When replacing or retiring a cell, record why.

For a root-definition gap, add the missing surface/obligation cells before remediation is ticketed.

Do not shrink the matrix to only currently failing symptoms.

For cross-cutting roots, use semantic surface/reference families and production-path obligations rather than enumerating individual files.

A root is satisfied only when every active required cell is satisfied or Owner-overridden.

## Architecture-Conformance Gate

Before persisting a new or materially changed root or acceptance obligation, confirm it conforms to current architecture.

Use the Spec Architecture Impact, applicable accepted ADRs/current docs, and the Architecture finding supplied by `$review-spec`.

An obligation is architecture-blocked when satisfying it would require:

* changing or violating an accepted architectural decision;
* inventing a new canonical owner, contract, path, or boundary;
* choosing a new dependency direction or lifecycle responsibility; or
* resolving materially conflicting authorities.

Do not persist architecture-blocked behavior as ordinary remediation.

Return all independent architecture blockers to `$review-spec` for its `$architecture-remediation` Human Handoff.

Do not propose the architectural answer.

## Durable Ledger Format

Use:

```markdown
## Root Blocker Ledger

### RB-1 — <short stable root name>
Status: open | satisfied | regressed | unproven | owner-overridden
Invariant: <stable durable invariant>
Architecture decision required: No
Governing authority: <ADR/doc/invariant>
Routing: <existing-authority remediation>
Affected surfaces/reference kinds: <semantic surface/reference families>
Exit checks: <root-complete production-path proof>
Current evidence:
- <dated evidence>

## Spec Acceptance Matrix

| Root | Surface/reference kind | Production-path obligation | Status | Evidence |
| --- | --- | --- | --- | --- |
```

Omit Architecture fields for non-Architecture roots.

Treat legacy `Status: closed` as `satisfied` when recovering existing state. New updates use `satisfied`.

Do not let helper-, validator-, serializer-, mock-, or isolated unit-level proof establish root completion when the obligation requires a production path.

## 1. First-Pass Failure

When no Spec Review tracking issue exists:

1. synthesize Blocking findings into stable roots;
2. build the initial cumulative acceptance matrix;
3. apply the Architecture-Conformance Gate;
4. create one parent issue titled:

```text
Spec Review: <Feature Name>
```

The first body line must be:

```markdown
**Parent Spec:** #<spec_issue_number>
```

Then include:

1. Root Blocker Ledger;
2. Spec Acceptance Matrix;
3. aggregated Standards / Spec / Architecture findings;
4. useful Advisory findings.

Treat individual findings as evidence for roots, not as an independent permanent blocker list.

## 2. Recursive Remediation Pass

When the Spec Review already exists:

1. recover the complete durable Root Blocker Ledger and cumulative acceptance matrix;
2. preserve every active prior obligation;
3. reconcile each new Blocking finding through **Finding Reconciliation**;
4. apply any root-definition gaps before ticketing;
5. update root status and evidence;
6. apply the Architecture-Conformance Gate to every new or materially changed obligation;
7. persist the updated cumulative ledger/matrix.

Do not create a new parent issue.

### Root Status

Use:

* **open** — one or more active obligations are violated;
* **regressed** — previously satisfied behavior was proven to have been broken later;
* **unproven** — no known violation remains, but required proof is insufficient;
* **satisfied** — every active obligation is proven satisfied;
* **owner-overridden** — owner explicitly removed the root from blocking status.

A **missed prior finding** makes the root `open`, not `regressed`.

A **root-definition gap** makes the root `open` or `unproven` according to the resulting obligations; it is not automatically a regression.

Do not declare a root satisfied from source plausibility alone when its closure requires verification evidence.

### Re-review History

Append a concise dated section:

```markdown
## Re-review Findings [YYYY-MM-DD HH:MM]

HEAD reviewed: `<sha>`

## Root Blocker Ledger Updates

...

## Spec Acceptance Matrix Updates

...

## Aggregated Review Findings

...
```

Preserve the original issue body and `**Parent Spec:**` line.

Do not re-mine the original diff for unrelated Advisory findings.

## 3. Remediation Delta

After the durable root model is current, determine the Blocking remediation delta.

Only architecture-conforming roots proceed.

For each actionable root pass `$to-tickets`:

* stable root ID and invariant;
* current status;
* affected semantic surface/reference families;
* governing authority when applicable;
* every active non-satisfied acceptance obligation;
* satisfied cells that must remain protected;
* required production-path and negative/regression proof;
* provenance classification for missed/regressed findings.

Do not slice directly from the latest symptom bullets.

Do not create one ticket per symptom when one root-complete remediation ticket can prove the invariant.

Do not treat a previously closed ticket as sufficient when current durable root state contains active violated or unproven obligations.

## 4. Human Handoff

`$to-tickets` is human-gated. Do not invoke it implicitly.

When architecture-conforming Blocking remediation remains, halt with:

> ⚠️ **Spec Review has Blocking remediation.**
>
> I have created or updated:
> **`Spec Review: <Feature Name> #<Issue_ID>`**
>
> Please run:
>
> ```
> $to-tickets - Spec Review: <Feature Name> (<Issue URL>)
> ```
>
> `$to-tickets` should slice Blocking remediation only unless you explicitly choose to include Advisory work.

If no Blocking findings remain, return to `$review-spec` so it can evaluate its Exit Gate.

## Owner Overrides

When the owner explicitly overrides a finding or root:

* persist the scope and rationale;
* mark the applicable root/cell `owner-overridden`;
* remove it from Blocking counts;
* suppress the same unchanged finding on later passes.

Do not use an Owner Override to silently alter architecture or erase historical evidence.
