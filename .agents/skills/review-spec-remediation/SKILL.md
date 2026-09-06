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

## Certified Domain Reconciliation Gate

This section is authoritative and supersedes preserved wording below that allows a later review to enlarge a previously certified semantic root/domain merely by labeling the new surface a `root-definition gap` or `missed prior finding`.

For every current Blocking finding mapped to a previously `satisfied`/`closed` root, the Pending packet must include one current `$review-spec` **Domain Finality Reconciliation** disposition:

```text
Candidate: <finding/member>
Prior certified domain: <domain ID / durable certification reference>
Authority changed: yes | no
Membership under frozen predicate: in-domain | out-of-domain | ambiguous
Explicit authority contradiction: <None | exact source>
Finality disposition:
  in-domain-falsifier
  authority-changed-domain-stale
  closure-authority-defect
  domain-expansion
```

Consume that disposition mechanically:

* `in-domain-falsifier` — eligible for ordinary current remediation reconciliation (`missed prior finding` or `regression` as provenance proves);
* `authority-changed-domain-stale` — eligible only after the Pending packet identifies the actual changed authority and the current review rebuilt the affected domain from that new authority;
* `closure-authority-defect` — **not** implementation remediation. Preserve the observation and halt the affected root/cell behind explicit authority/domain reconciliation; do not pass it to `$to-tickets`;
* `domain-expansion` — non-actionable for the current certified domain. Preserve the observation historically but do not create/open a remediation cell or root from it.

A full fresh re-review, missing review-proof reuse ledger, stronger challenger, or broader plausible interpretation does not invalidate a certified closure domain by itself.

### Domain-excluded acceptance state

The cumulative matrix may use:

```text
domain-excluded
```

for a historical/current observation that a corrected Domain Finality Reconciliation proves lies outside the applicable frozen semantic domain under unchanged authority.

`domain-excluded` means:

* the observation remains durable;
* the underlying implementation behavior is not claimed false or desirable;
* it is not an active obligation of that certified root/domain;
* it does not count as Blocking remediation;
* it is excluded from `$to-tickets` for the current lifecycle unless durable authority later changes.

Do not use `scope-retired` for this case unless the entire Spec/root ownership itself was also corrected. Scope and domain membership are distinct.

### Root-definition integrity under finality

For a root with an applicable certified closure domain:

* `missed prior finding` requires `in-domain-falsifier`;
* `regression` requires an in-domain behavior whose previously proven disposition later changed;
* `root-definition gap` may not enlarge the frozen domain under unchanged authority;
* saturation evidence may add newly discovered **in-domain** members, but may not replace the certified predicate/source sets with a broader sibling universe;
* `domain-expansion` and `closure-authority-defect` do not create a new root merely to bypass domain finality.

When no applicable certified domain exists, use the ordinary reconciliation rules below.

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

A root-definition gap may expand affected semantic surfaces, exit checks, and acceptance obligations while preserving the same stable invariant **only when the Certified Domain Reconciliation Gate above permits that expansion**. A certified frozen domain under unchanged authority may not be enlarged by this clause.

If the invariant itself would materially broaden, create a new root only when the current accepted finding is not a prohibited domain-expansion/closure-authority-defect under the gate above.

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
domain-excluded
```

Omission from a later update does not remove a cell.

A satisfied cell stays satisfied unless current accepted evidence violates the same semantic obligation or durable state explicitly supersedes/retires/overrides it.

A new sibling manifestation adds/opens the narrow missing cell only when it survived Certified Domain Reconciliation. A domain-expansion observation becomes `domain-excluded`; it does not downgrade unrelated satisfied siblings.

A root is active-satisfied only when every non-retired required cell is `satisfied`, `owner-overridden`, or `domain-excluded`.

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
4. apply Certified Domain Reconciliation to every finding against a previously satisfied/closed root;
5. reconcile only finality-surviving current Blocking findings;
6. add root-definition-gap cells only when allowed by the finality gate;
7. mark corrected out-of-domain historical/current observations `domain-excluded` rather than deleting them;
8. update root status/evidence;
9. apply architecture-conformance gate;
10. persist updated cumulative state.

Do not resurrect historical findings unless they remain active cells or are independently validated in the current Pending packet.

### Root Status

Use:

* **open** — active violated obligation;
* **regressed** — previously satisfied behavior was broken later;
* **unproven** — no known violation but required proof insufficient;
* **satisfied** — all active obligations proven, overridden, retired, or domain-excluded;
* **owner-overridden** — owner explicitly removes Blocking requirement;
* **scope-retired** — no active obligation belongs to this Spec after validated attribution correction.

A root with some scope-retired/domain-excluded cells and some active cells uses the active-cell-derived status.

### Re-review History

Append a concise dated section containing:

* current independently validated findings by axis;
* applied scope corrections;
* Domain Finality Reconciliation results;
* saturation result when present;
* root updates;
* matrix updates.

Preserve historical sections; never rewrite them.

## 3. Remediation Delta

After state is current, compute only **active architecture-conforming Blocking remediation**.

Exclude:

* satisfied cells;
* owner-overridden cells;
* scope-retired cells/roots;
* domain-excluded cells;
* closure-authority-defect/domain-expansion observations awaiting or excluded from current implementation remediation.

For each actionable root pass to `$to-tickets`:

* stable ID/invariant;
* current active status;
* affected semantic families;
* governing authority;
* every active non-satisfied obligation;
* satisfied preservation cells;
* production-path/negative/fail-closed/regression proof;
* root-complete invariant sweep constrained to the currently authoritative/frozen domain;
* missed/regressed provenance;
* current review saturation evidence when supplied.

Do not slice latest symptom bullets directly.

Do not create one ticket per symptom when one root-complete ticket can close the invariant.

## 4. Return / Human Handoff

Let:

```text
ACTIVE_BLOCKING_FINDINGS
```

mean current independently validated Blocking findings that remain active after validated scope corrections **and Certified Domain Reconciliation**.

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

`[X]` is the number of active current Blocking findings after scope/domain correction, not raw historical findings, roots, or cells.

If Scope/Domain Corrections remove all active Blocking findings, return control to `$review-spec`; do not emit `$to-tickets`.

## Owner Overrides

Owner Override remains distinct from Scope retirement and Domain exclusion.

For an explicit owner override:

* persist scope/rationale;
* mark applicable root/cell `owner-overridden`;
* remove from Blocking counts;
* suppress the unchanged finding later.

Do not use Owner Override to repair attribution/domain mistakes that meet Scope Correction or Certified Domain Reconciliation rules.
