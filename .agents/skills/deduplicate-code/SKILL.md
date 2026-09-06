---
name: deduplicate-code
description: Enforces zero unsuppressed duplicate-code findings across the repository by consolidating real duplicate implementation or narrowly suppressing independently justified repetition with tool-native directives.
license: MIT
compatibility: product=codex product=claude-code system=arid system=jscpd network=none
metadata:
  version: 2.0.0
---

# Code Duplication Checks

## Objective

Prevent codebase bloat and split-brain logic by requiring every duplicate-code finding to reach a durable repository disposition.

The terminal invariant is:

> **Zero unsuppressed duplicate findings.**

Physical repetition may remain only when consolidation would be the wrong design and that decision is encoded as a narrow, justified tool-native suppression. A finding is never complete merely because an agent inspected it and called it harmless.

## Core Invariants

### Single Source of Truth

Do not create or preserve parallel implementations of the same authoritative behavior, policy, calculation, transformation, canonical representation, helper responsibility, or reusable mechanism.

If correctness normally requires occurrences to change together, they require one implementation owner. Consolidate them or consume the existing canonical owner.

If analysis shows separate components attempting to claim authoritative ownership over the same business rule or calculation, treat that as an architectural boundary problem rather than suppressing the duplicate.

### Whole-Repository Scope

Duplication is relational. A changed block can duplicate an unchanged implementation anywhere else in the repository, so changed-file, ticket, or Spec scope is insufficient for this gate.

Always run both scanners from the repository root over their normal configured project scope:

```bash
arid .
jscpd .
```

Do not narrow scanner scope merely because a parent workflow is ticket- or Spec-scoped. Repository-local Arid/JSCPD configuration and ordinary discovery/exclusion policy still apply.

When this skill is delegated by another lifecycle or verification skill, **this skill owns the repository-wide duplication gate and the narrowly bounded repository repairs required to make that gate pass**, even when a finding is outside the parent's semantic change scope. This authority is limited to duplicate-code consolidation or justified suppression under this skill; it does not authorize unrelated cleanup.

### Zero-Finding Invariant

A successful run requires all of the following:

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

A non-zero finding count starts or continues the repair loop. It is not a successful disposition.

## Finding Repair Loop

Run the whole-repository scans, inspect the actual matching source, and disposition every reported finding as exactly one of:

```text
consolidate
suppress
unresolved
```

Then apply all safe repairs, rerun invalidated verification when executable behavior changed, and rerun both repository-wide scanners. Repeat until both scanners are clean or a concrete blocker makes further safe repair impossible.

`unresolved` blocks PASS.

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

After suppression changes, audit suppression health. The final Arid gate is:

```bash
arid . --fail-on-stale --suppression-summary
```

It must exit successfully with zero reportable duplicate groups and zero stale suppressions.

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
4. inspect any remaining findings against actual source rather than assuming they share the previous disposition;
5. continue until the Zero-Finding Invariant is satisfied.

Use:

```bash
arid . --fail-on-stale --suppression-summary
jscpd .
```

The final successful native exit status for both tools must be zero.

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

Report PASS only after the final scans actually satisfy the terminal invariant:

```text
DEDUPLICATION: PASS

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

If the tool cannot run, a finding cannot be safely classified/repaired, a required consolidation needs unresolved architecture, or another concrete external/tooling constraint prevents completion, report the exact blocker. Do not report PASS with a non-zero finding count.
