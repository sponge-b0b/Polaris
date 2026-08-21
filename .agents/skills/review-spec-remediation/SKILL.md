---
name: review-spec-remediation
description: Invoked only by `$review-spec` after it persists independently validated Blocking findings in a Pending Review Remediation packet. Maintains the durable Root Blocker Ledger and cumulative acceptance matrix, then hands architecture-conforming remediation to `$to-tickets`.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec Remediation

`$review-spec-remediation` is an internal continuation invoked by `$review-spec` after independently validated Blocking findings are persisted in a **Pending Review Remediation** packet.

It converts those findings into durable remediation state.

It does not review source code and does not fix source code.

Accept only findings that passed `$review-spec`'s axis-provenance gate and were persisted in the current **Pending Review Remediation** packet.

Do not:

* rehabilitate a discarded wrong-axis finding;
* move a finding to another review axis;
* derive a new review finding from Root Blocker history;
* perform another Standards, Spec, or Architecture review.

If a Blocking Architecture finding has `Architecture decision required: Yes`, return it to `$review-spec`. Unresolved architecture must not become ordinary remediation work.

## Invocation Preconditions

The invocation source must be the `Spec Review: ...` issue supplied by `$review-spec`.

Recover the parent Spec from the exact body line:

```markdown
**Parent Spec:** #<spec_issue_number>
```

Recover the latest **Pending Review Remediation** packet.

Require:

* `Status: pending`;
* `Reviewed HEAD` equals the current `HEAD`;
* `Reviewed Baseline` equals the current Spec baseline;
* `Branch` equals the current Spec branch.

Verify:

```bash
CURRENT_HEAD=$(git rev-parse HEAD)
CURRENT_BRANCH=$(git branch --show-current)
```

If the packet is missing or stale, return a remediation-state error to `$review-spec` and do not synthesize remediation.

Do not reconstruct or infer pending review findings from historical ledger entries, previous sessions, or source inspection.

The Pending Review Remediation packet is the sole current-review finding input to this skill.

## Root Blocker Model

Group accepted findings by the **durable invariant** they violate, not by file, subsystem, symptom, or reviewing axis.

An `RB-*` ID denotes one stable invariant.

Preserve existing IDs.

Do not broaden an existing invariant merely to keep a new finding under the same root.

For each root maintain:

* invariant;
* status;
* affected semantic surface/reference families;
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

## Finding Reconciliation

Classify each accepted Blocking finding as exactly one of:

* **child symptom** — already derivable from the existing invariant and closure domain;
* **root-definition gap** — same durable invariant, but affected surfaces, exit checks, or acceptance obligations were incomplete;
* **regression** — previously satisfied behavior was proven to have broken later;
* **missed prior finding** — the violation already existed at the prior satisfied state;
* **new root** — a genuinely distinct durable invariant.

Use provenance supplied by `$review-spec`.

Do not independently reclassify review-axis authority.

Do not label a newly discovered violation `regression` merely because its root was previously satisfied.

### Root Definition Integrity

A root-definition gap may expand:

* affected semantic surface/reference families;
* exit checks;
* acceptance obligations.

It must not materially change what the invariant means.

If accommodating a finding requires broadening the invariant itself, create a new root instead.

Do not allow an existing root to become an ever-expanding container for related concerns.

## Cumulative Acceptance Matrix

Acceptance obligations are cumulative for the lifetime of an active root.

Carry forward every established cell with its current state:

```text
satisfied
open
regressed
unproven
owner-overridden
```

A later review may update a cell's status or evidence, but omission does not remove it.

Remove, replace, or retire an obligation only when durable state explicitly establishes that it is:

* superseded by an equivalent obligation;
* no longer required by current Spec/architecture; or
* Owner-overridden.

Record the reason for any replacement or retirement.

For a root-definition gap, add the missing surface/obligation cells before remediation is ticketed.

Do not shrink the matrix to currently failing symptoms.

For cross-cutting roots, use semantic surface/reference families and production-path obligations rather than file lists.

A root is satisfied only when every active required cell is `satisfied` or `owner-overridden`.

## Architecture-Conformance Gate

Before persisting a new root or materially changed acceptance obligation, confirm that the proposed remediation does not require an unresolved architectural choice.

Use only:

* accepted Architecture findings supplied in the Pending Review Remediation packet;
* current governing authority already attached to the root;
* Spec Architecture Impact where needed for routing.

An obligation is architecture-blocked when satisfying it would require:

* changing or violating an accepted architectural decision;
* inventing a new canonical owner, contract, path, or boundary;
* choosing a new dependency direction or lifecycle responsibility; or
* resolving materially conflicting authorities.

Do not create an Architecture finding merely because another review axis raised an architectural concern.

Do not persist architecture-blocked behavior as ordinary remediation.

Return any genuine architecture blocker to `$review-spec` for its Architecture Human Handoff.

Do not propose the architectural resolution.

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

Treat legacy `Status: closed` as `satisfied` when recovering state.

New updates use `satisfied`.

Do not let helper-, validator-, serializer-, mock-, or isolated unit-level proof establish root completion when the obligation requires a production path.

## 1. First Remediation Pass

When the Spec Review issue has no Root Blocker Ledger yet:

1. synthesize the accepted Blocking findings from the Pending Review Remediation packet into stable roots;
2. build the initial cumulative acceptance matrix;
3. apply the Architecture-Conformance Gate;
4. persist the Root Blocker Ledger and Spec Acceptance Matrix to the existing Spec Review issue.

Preserve the existing issue body and exact:

```markdown
**Parent Spec:** #<spec_issue_number>
```

Treat findings as evidence for roots, not as an ever-growing independent blocker list.

## 2. Recursive Remediation Pass

When the Spec Review already has durable Root Blocker state:

1. recover the complete durable Root Blocker Ledger and cumulative acceptance matrix;
2. preserve every active prior obligation;
3. reconcile each accepted Blocking finding from the Pending Review Remediation packet through **Finding Reconciliation**;
4. apply root-definition gaps without changing stable invariant identity;
5. update root status and evidence;
6. apply the Architecture-Conformance Gate to new or materially changed obligations;
7. persist the updated cumulative ledger and matrix.

Do not create another parent issue.

Do not resurrect discarded findings from earlier `$review-spec` passes merely because they remain in historical text.

Historical findings remain evidence/history unless represented by an active cumulative obligation or independently validated in the current Pending Review Remediation packet.

### Root Status

Use:

* **open** — one or more active obligations are violated;
* **regressed** — previously satisfied behavior was proven to have broken later;
* **unproven** — no known violation remains, but required proof is insufficient;
* **satisfied** — every active obligation is proven satisfied;
* **owner-overridden** — owner explicitly removed the root from Blocking status.

A **missed prior finding** makes the root `open`, not `regressed`.

A **root-definition gap** makes the root `open` or `unproven` according to its resulting obligations.

Do not declare a root satisfied from source plausibility alone when closure requires verification evidence.

### Re-review History

Append a concise dated section:

```markdown
## Re-review Findings [YYYY-MM-DD HH:MM]

HEAD reviewed: `<sha>`

### Independently Validated Review Findings

#### Standards
...

#### Spec
...

#### Architecture
...

### Root Blocker Ledger Updates
...

### Spec Acceptance Matrix Updates
...
```

Preserve the original issue body and `**Parent Spec:**` line.

Do not rewrite historical review sections.

Do not re-mine the original diff for unrelated Advisory findings.

## 3. Remediation Delta

After durable root state is current, determine the Blocking remediation delta.

Only architecture-conforming roots proceed.

For each actionable root pass to `$to-tickets`:

* stable Root Blocker ID and invariant;
* current status;
* affected semantic surface/reference families;
* governing authority when applicable;
* every active non-satisfied acceptance obligation;
* satisfied cells that remain preservation obligations;
* required production-path and negative/fail-closed/regression proof;
* root-complete invariant sweep;
* provenance classification for missed/regressed findings.

Do not slice directly from the latest symptom bullets.

Do not create one ticket per symptom when one root-complete remediation ticket can prove the invariant.

Do not treat a previously closed ticket as sufficient when current durable root state contains active violated or unproven obligations.

## 4. Human Handoff

`$to-tickets` is human-gated.

Do not invoke it implicitly.

When architecture-conforming Blocking remediation remains, halt using this exact structure:

> ⚠️ **Spec Review Failed with [X] Blocking Findings.**
>
> I have created or updated the parent tracking issue:
> **`Spec Review: <Feature Name> #<Issue_ID>`**.
>
> Please run the following command to slice the Blocking findings into tracked child tickets:
>
> ```
> $to-tickets Spec Review: <Feature Name> (<Issue URL>)
> ```
>
> `$to-tickets` should slice **Blocking remediation only** unless you explicitly want Advisory findings ticketed.

`[X]` is the number of independently validated current Blocking findings, not the number of Root Blockers or acceptance cells.

Do not alter or embed additional remediation content inside this Human Handoff. When `$review-spec` propagates it, `$review-spec` retains ownership of its already-required aggregate review results before the handoff.

If no Blocking findings remain, return control to `$review-spec` so it can evaluate its Exit Gate.

## Owner Overrides

When the owner explicitly overrides a finding or root:

* persist the scope and rationale;
* mark the applicable root/cell `owner-overridden`;
* remove it from Blocking counts;
* suppress the same unchanged finding on later passes.

Do not use an Owner Override to silently alter architecture or erase historical evidence.