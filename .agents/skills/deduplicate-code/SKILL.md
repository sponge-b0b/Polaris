---
name: deduplicate-code
description: Enforces repository-wide duplicate-code discipline, with zero unsuppressed findings by default and baseline-differential causality for ticket/spec verification.
license: MIT
compatibility: product=codex product=claude-code system=arid system=jscpd network=none
metadata:
  version: 2.2.0
---

# Code Duplication Checks

## Objective

Prevent codebase bloat and split-brain logic by requiring every duplicate-code finding to reach a durable repository disposition.

The standalone/default terminal invariant is:

> **Zero unsuppressed duplicate findings.**

When delegated in a differential integration mode, the terminal invariant is instead zero candidate-introduced/expanded duplication and zero unresolved causality; machine-correlated `baseline-identical` findings may remain as inherited debt. `$implement-ticket` uses `ticket-differential`; `$verify-spec` uses `spec-differential`. These modes change repair attribution, never whole-repository scan scope.

Physical repetition may remain only when consolidation would be the wrong design and that decision is encoded as a narrow, justified tool-native suppression, or when the active differential mode proves the finding is baseline-identical and therefore outside that parent lifecycle's repair loop. A finding is never complete merely because an agent inspected it and called it harmless.

## Core Invariants

### Single Source of Truth

Do not create or preserve parallel implementations of the same authoritative behavior, policy, calculation, transformation, canonical representation, helper responsibility, or reusable mechanism.

If correctness normally requires occurrences to change together, they require one implementation owner. Consolidate them or consume the existing canonical owner.

If analysis shows separate components attempting to claim authoritative ownership over the same business rule or calculation, treat that as an architectural boundary problem rather than suppressing the duplicate.

### Whole-Repository Scope

Duplication is relational. A changed block can duplicate an unchanged implementation anywhere else in the repository, so changed-file, ticket, or Spec scope is insufficient for this gate.

Always run both scanners from the repository root over their normal configured project scope:

```bash
uv run --locked arid .
jscpd .
```

Do not narrow scanner scope merely because a parent workflow is ticket- or Spec-scoped. Repository-local Arid/JSCPD configuration and ordinary discovery/exclusion policy still apply.

When this skill is delegated by another lifecycle or verification skill, the parent-supplied integration mode controls **repair attribution**, never scanner scope. Default mode retains the repository-wide zero-finding invariant. `$implement-ticket` uses `ticket-differential` against the fixed ticket baseline; `$verify-spec` uses `spec-differential` against the fixed Spec baseline. Candidate-caused duplication is repaired globally without turning either lifecycle into unrelated historical cleanup. Repair authority remains limited to duplicate-code consolidation or justified suppression under this skill; it does not authorize unrelated cleanup.

## Verification Integration Mode: `ticket-differential`

When `$implement-ticket` delegates this skill, it supplies the fixed `TICKET_BASELINE` and the exact current ticket candidate state and invokes `ticket-differential` mode.

Applicability is determined by the parent: use this mode when the ticket changes executable/source files that fall inside the repository's configured Arid or JSCPD scan universe. Scanner scope remains whole-repository.

Run the candidate scans in the current exact ticket worktree and the baseline scans against an isolated read-only `TICKET_BASELINE` worktree/ref. Classify every candidate finding using the same four causality states defined for `spec-differential` below:

```text
candidate-introduced
candidate-expanded
baseline-identical
unresolved
```

Interpret "candidate" as the ticket candidate and "baseline" as `TICKET_BASELINE`.

Only candidate-introduced and candidate-expanded findings enter the ticket repair loop. Repair them before ticket closure using the normal consolidation/suppression rules. A correct shared-owner repair may touch an otherwise unchanged file when necessary to remove the ticket-caused duplicate relation, but this mode does not authorize unrelated inherited cleanup.

The `ticket-differential` terminal invariant is identical in shape to the Spec differential invariant:

```text
Candidate-introduced duplicate findings: 0
Candidate-expanded duplicate findings: 0
Unresolved causality classifications: 0
Candidate-attributable stale/invalid suppressions: 0
Arid operational/source-processing errors: 0
JSCPD operational errors: 0
Actionable competing implementations introduced/expanded by candidate: 0
```

Baseline-identical findings may remain nonzero. If a dedup repair changes the ticket candidate, the parent candidate freeze/evidence is stale and must be recomputed under `$implement-ticket`.

## Verification Integration Mode: `spec-differential`

When `$verify-spec` delegates this skill, it must supply the fixed Spec `BASELINE_COMMIT` and exact candidate HEAD and invoke `spec-differential` mode.

This mode preserves **Whole-Repository Scope**. Both Arid and JSCPD still scan their normal configured repository scope for the candidate. The baseline is used only to determine whether a reported relation is caused or expanded by the active Spec candidate.

Use an isolated read-only baseline worktree/ref and correlate machine-readable scanner results before performing semantic source inspection. Classify each candidate finding as exactly one of:

```text
candidate-introduced
candidate-expanded
baseline-identical
unresolved
```

Classification rules:

* **candidate-introduced** — the duplicate relation is absent at baseline. This includes changed/new candidate code duplicating an unchanged implementation elsewhere.
* **candidate-expanded** — the relation existed at baseline but the candidate adds an occurrence, materially enlarges the duplicated region, creates new shared-authority coupling, or makes an existing suppression stale/invalid.
* **baseline-identical** — the material occurrence set and duplicate relation are unchanged from baseline and the candidate does not alter their detector/suppression semantics.
* **unresolved** — causality cannot be established safely; blocks PASS.

If Arid/JSCPD configuration or suppression policy changed between baseline and candidate, that delta is candidate-caused and must be inspected explicitly. Do not classify a visibility change as `baseline-identical` merely because the source block itself predates the candidate.

Only `candidate-introduced` and `candidate-expanded` findings enter the repair loop. Repair them using the normal consolidation/suppression rules, even when the correct repair touches an unchanged/non-Spec file to establish the real shared owner.

`baseline-identical` findings remain in the evidence summary as inherited repository debt and do not authorize opportunistic cleanup during `$verify-spec`. Once exact baseline correlation establishes unchanged identity, do not repeatedly perform semantic source analysis for every inherited group unless another candidate change invalidates that correlation.

The `spec-differential` terminal invariant is:

```text
Candidate-introduced duplicate findings: 0
Candidate-expanded duplicate findings: 0
Unresolved causality classifications: 0
Candidate-attributable stale/invalid suppressions: 0
Arid operational/source-processing errors: 0
JSCPD operational errors: 0
Actionable competing implementations introduced/expanded by candidate: 0
```

Baseline-identical findings may remain nonzero in this mode. That is not a narrowed scan; it is a bounded repair disposition for this parent lifecycle.

### Zero-Finding Invariant

In standalone/default mode, a successful run requires all of the following:

```text
Arid reportable duplicate groups: 0
Arid stale suppressions: 0
Arid operational/source-processing errors: 0
JSCPD reportable clones: 0
JSCPD operational errors: 0
Unresolved duplicate findings: 0
Suppressions without meaningful justification: 0
Actionable competing implementations remaining: 0
```

In standalone/default mode, a non-zero finding count starts or continues the repair loop. In `ticket-differential` or `spec-differential` mode, only candidate-introduced, candidate-expanded, unresolved, operational, or candidate-attributable stale/invalid-suppression results continue the repair loop; baseline-identical findings are already dispositioned.

## Finding Repair Loop

Run the whole-repository scans and inspect actual matching source where repair/classification requires it.

In standalone/default mode, disposition every reported finding as exactly one of:

```text
consolidate
suppress
unresolved
```

In a differential mode, perform baseline causality classification first. Only `candidate-introduced` and `candidate-expanded` findings then receive `consolidate | suppress | unresolved`; `baseline-identical` is a terminal inherited disposition for that invocation and does not enter the repair loop.

Apply all authorized repairs, rerun invalidated verification when executable behavior changed, and rerun both repository-wide candidate scanners. Repeat until the active mode's terminal invariant is satisfied or a concrete blocker makes further safe repair impossible.

`unresolved` blocks PASS in every mode.

Do not stop after producing a prose explanation for surviving findings.

## Consolidation-Required Conditions

A duplicate must be consolidated or otherwise removed when any of these is true:

* the occurrences implement the same authoritative business rule, policy, calculation, validation, transformation, representation, or reusable behavior;
* correctness requires changes to one occurrence normally to be mirrored in another;
* an existing canonical helper, service, contract, utility, or owner already represents the behavior;
* the repeated implementation creates or risks competing authorities, behavioral drift, divergent fixes, or split-brain logic;
* a shared abstraction expresses the real semantic relationship more directly than the repeated blocks;
* the repetition exists only because code was copied instead of consuming an established boundary.

Consolidate at the narrowest authoritative point. Do not create a generic helper merely to reduce line count if the helper has no real semantic owner.

If consolidation changes Python executable code or tests, invoke `$verify-code` for the affected change and directly affected consumers/tests before accepting the repair. A suppression-only comment change does not by itself require `$verify-code`; the duplicate scanners and applicable syntax/structure checks remain required.

## Suppression Merit: False Coupling Invariant

A duplicate merits suppression only when:

> **Consolidating it would create a false semantic dependency between things that must remain independently meaningful, independently testable, independently evolvable, or independently owned.**

All of the following must be true before suppression is allowed:

1. **No competing authority** — the occurrences are not separate implementations of one authoritative behavior.
2. **Independent evolution** — one occurrence can legitimately change without requiring corresponding changes to the others.
3. **False-coupling proof** — extracting or sharing the matching block would couple independent semantics, obscure the thing being proved/represented, cross an ownership boundary that should remain separate, or require artificial parameterization/branching whose purpose is only to make syntactically similar code look DRY.
4. **No canonical owner to consume** — there is no existing helper/interface/owner that the occurrences should already use.
5. **Clarity is improved by local repetition** — the repeated form keeps the relevant semantics more explicit than the abstraction would.
6. **Minimum suppression** — the suppression covers only the smallest source region sufficient to remove the justified finding.
7. **Meaningful durable justification** — an adjacent source comment explains why sharing would be wrong, not merely that the duplication is intentional.

The classification of a file as a test, fixture, generated artifact, configuration file, or helper is evidence only. It never automatically merits suppression.

### Independence Test

Use this counterfactual when the answer is unclear:

> If occurrence A changes for a legitimate semantic reason, may occurrence B correctly remain unchanged?

* **No** → they are one behavior and should normally be consolidated.
* **Yes** → suppression may be considered, but only if every False Coupling condition above also holds.

## Suppression Requirements

Use source-local tool-native suppression, not detector weakening.

Immediately adjacent to every new suppression, add a concise meaningful justification comment using this convention:

```text
# duplicate-code: <why a shared implementation would create false coupling or hide independent semantics>
```

A comment such as `intentional duplication`, `false positive`, `test code`, or `required` is not sufficient justification.

### Arid

Use the smallest necessary Arid suppression region:

```python
# duplicate-code: separate architecture falsifier; sharing this source scaffold would couple independent scope-semantics proofs.
# arid: disable
<justified repeated region>
# arid: enable
```

Arid permits a disabled region through EOF, but prefer a bounded region whenever later source is not part of the same justification.

After suppression changes, audit suppression health with the whole-repository Arid command:

```bash
uv run --locked arid . --fail-on-stale --suppression-summary
```

In standalone/default mode it must exit successfully with zero reportable duplicate groups and zero stale suppressions. In a differential mode, retain the native output/exit status for classification: a finding-caused non-zero result may remain only for machine-correlated `baseline-identical` groups, while operational/source-processing failures and candidate-attributable stale/invalid suppressions remain blocking.

### JSCPD

Use the smallest necessary JSCPD ignored region:

```python
# duplicate-code: separate architecture falsifier; sharing this source scaffold would couple independent scope-semantics proofs.
# jscpd:ignore-start
<justified repeated region>
# jscpd:ignore-end
```

If the same source region is independently reported by both tools, co-locate the directives under one justification:

```python
# duplicate-code: separate falsifiers intentionally preserve their exact source shape; extraction would hide the distinction being proved.
# arid: disable
# jscpd:ignore-start
<justified repeated region>
# jscpd:ignore-end
# arid: enable
```

Use only the directive for the tool that reports the finding when the other tool does not require suppression.

## Forbidden Silencing Mechanisms

Do not make the gate green by changing what the detector is allowed to see instead of resolving the finding.

For a reported duplicate, do not:

* raise `min-lines`, token thresholds, or similar detection thresholds merely to hide it;
* add or broaden project-wide file/path exclusions solely to remove the finding;
* add a broad JSCPD ignore glob or `ignorePattern` solely to silence specific current findings;
* disable same-file detection or other configured detection behavior;
* use Arid `--no-fail-on-findings` for the final gate;
* create or expand an Arid baseline to accept newly encountered duplicate debt;
* weaken repository Arid/JSCPD configuration merely to obtain a zero count;
* cosmetically perturb equivalent code so the detector no longer recognizes it;
* suppress a whole function/file when a smaller justified region is sufficient;
* use suppression to preserve duplicated business logic or competing canonical implementations.

Existing repository configuration or an explicitly authorized migration/adoption baseline remains separate project authority; this skill must not enlarge it as a shortcut around current findings.

## Post-Repair Verification

After every repair cycle:

1. if executable Python source/tests changed through consolidation, invoke `$verify-code` for the affected change and consumer set;
2. rerun Arid across the repository with stale-suppression enforcement;
3. rerun JSCPD across the repository;
4. in default mode, inspect remaining findings normally; in a differential mode, reuse exact baseline-identical correlations unless a repair/configuration/suppression change invalidated them;
5. continue until the active mode's terminal invariant is satisfied.

Use:

```bash
uv run --locked arid . --fail-on-stale --suppression-summary
jscpd .
```

In standalone/default mode, the final successful native exit status for both tools must be zero. In a differential mode, a scanner may still report only machine-correlated `baseline-identical` findings; the differential wrapper/classification must prove candidate-introduced `0`, candidate-expanded `0`, unresolved `0`, candidate-attributable stale/invalid suppressions `0`, and operational errors `0`.

This skill does not commit independently when invoked as a child workflow. The owning lifecycle includes deduplication repairs in its normal candidate verification and commit/persistence process.

## Examples

### Suppression Merited — Independent Architecture Falsifiers

Repeated synthetic source construction in architecture tests may deliberately keep the same `_write(...)` scaffold while varying loader rebinding, parameter shadowing, global scope, class scope, and method scope.

Those cases are separate language-semantics proofs. If a shared helper would hide the exact source form or couple independent falsifiers, the repetition satisfies the False Coupling Invariant and should be narrowly suppressed with a justification stating that reason.

The rule is **not** "test duplication is acceptable." If several tests repeat one semantically identical canonical fixture that must evolve together, consolidate that fixture instead.

### Consolidation Required — Parallel Business Rule

Two modules independently normalize or score the same Investment Decision input using equivalent logic. A change to the business rule must be reflected in both or behavior diverges.

That fails the Independence Test. Do not suppress it. Establish or consume the canonical owner and remove the duplicate implementation.

### Suppression Merited — Local Proof Shape, Not Parallel Authority

Two small visitor/checking sequences inside one central architecture guard may have similar structure while proving distinct AST contexts. Suppression is legal only if inspection establishes that they are not competing implementations, each may evolve independently, and extraction would obscure or artificially couple the contexts. Otherwise consolidate the common mechanism.

## Terminal Result

Report PASS only after the active mode's terminal invariant is satisfied.

Standalone/default mode:

```text
DEDUPLICATION: PASS
Mode: default

Whole-project scope:
- Arid: .
- JSCPD: .

Arid:
- Reportable duplicate groups: 0
- Stale suppressions: 0
- Operational/source-processing errors: 0

JSCPD:
- Reportable clones: 0
- Operational errors: 0

Finding disposition:
- Consolidated/refactored: <n>
- Justified and suppressed: <n>
- Unresolved: 0
- Suppressions without meaningful justification: 0
- Actionable competing implementations remaining: 0
```

`$implement-ticket` `ticket-differential` mode:

```text
DEDUPLICATION: PASS
Mode: ticket-differential
Baseline: <TICKET_BASELINE>
Candidate: <exact ticket candidate state>

Whole-project scope:
- Arid candidate scan: .
- Arid baseline scan: .
- JSCPD candidate scan: .
- JSCPD baseline scan: .

Causality:
- Candidate-introduced: 0
- Candidate-expanded: 0
- Baseline-identical: <n>
- Unresolved: 0

Health:
- Candidate-attributable stale/invalid suppressions: 0
- Arid operational/source-processing errors: 0
- JSCPD operational errors: 0
- Actionable competing implementations introduced/expanded by candidate: 0

Repairs:
- Consolidated/refactored: <n>
- Justified and suppressed: <n>
```

`$verify-spec` `spec-differential` mode:

```text
DEDUPLICATION: PASS
Mode: spec-differential
Baseline: <BASELINE_COMMIT>
Candidate: <HEAD>

Whole-project scope:
- Arid candidate scan: .
- Arid baseline scan: .
- JSCPD candidate scan: .
- JSCPD baseline scan: .

Causality:
- Candidate-introduced: 0
- Candidate-expanded: 0
- Baseline-identical: <n>
- Unresolved: 0

Health:
- Candidate-attributable stale/invalid suppressions: 0
- Arid operational/source-processing errors: 0
- JSCPD operational errors: 0
- Actionable competing implementations introduced/expanded by candidate: 0

Repairs:
- Consolidated/refactored: <n>
- Justified and suppressed: <n>
```

If the tool cannot run, causality cannot be safely classified, a candidate-caused finding cannot be safely repaired, a required consolidation needs unresolved architecture, or another concrete external/tooling constraint prevents completion, report the exact blocker. In default mode, do not report PASS with a non-zero unsuppressed finding count. In either differential mode, do not fail merely because classified baseline-identical findings remain; do fail for any candidate-introduced, candidate-expanded, unresolved, stale/invalid-suppression, or operational count above zero.
