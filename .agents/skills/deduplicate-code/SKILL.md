---
name: deduplicate-code
description: Enforces repository-wide duplicate-code discipline, with zero unsuppressed findings by default and candidate-attribution differential causality for ticket/spec verification.
license: MIT
compatibility: product=codex product=claude-code system=arid system=jscpd network=none
metadata:
  version: 2.6.1
---

# Code Duplication Checks

## Authoritative procedure composition

Before executing this skill, read `.agents/skills/deduplicate-code/PROCEDURE.md` in full.
That file preserves the complete established duplicate-code procedure. This `SKILL.md` is
the authoritative entrypoint and owns the differential-causality and control-plane
corrections below; on conflict, this file wins.

All retained whole-repository scanner scope, finding classification, consolidation,
suppression-merit, migration/test-surface, forbidden-silencing, rerun, and evidence rules
remain normative except where this entrypoint explicitly replaces historical-baseline
causality.

## Ticket-differential uses the Execution Anchor

When delegated by `$implement-ticket`, `ticket-differential` receives:

```text
TICKET_BASELINE
    immutable historical ticket lineage only

EXECUTION_ANCHOR
    exact fetched shared-branch commit admitted before this implementation attempt

candidate
    exact working candidate relative to EXECUTION_ANCHOR
```

For `ticket-differential`, **EXECUTION_ANCHOR is the comparison base**.
`TICKET_BASELINE` is not the scanner/differential baseline and must never be used to create
the isolated comparison worktree for the current attempt.

Run whole-repository candidate scans in the current exact worktree as before. Establish
comparison evidence against an isolated read-only `EXECUTION_ANCHOR` worktree/ref.

A reusable ticket-differential comparison scan is valid only while all of these are
unchanged:

* exact `EXECUTION_ANCHOR`;
* scanner executable/toolchain versions;
* Execution-Anchor Arid/JSCPD configuration and suppression-policy files;
* scan scope/configuration semantics used for the differential comparison.

Interpret the retained four causality states against `EXECUTION_ANCHOR`:

```text
candidate-introduced
candidate-expanded
baseline-identical
unresolved
```

Here `baseline-identical` means identical to the Execution Anchor. Legitimate
shared-branch/prerequisite/workflow changes between historical Ticket baseline and Execution
Anchor are inherited upstream state and cannot become ticket-attributable duplicate debt.

## Spec-differential uses the verify-spec attribution manifest

When delegated by `$verify-spec`, the fixed Spec baseline remains immutable **lineage and
contract history**. It is not, by itself, the technical-gate causality boundary for a
long-lived Spec branch that has also absorbed upstream/default-branch work.

`$verify-spec` must first build the current machine attribution manifest with:

```bash
python .agents/skills/verify-spec/scripts/verify_spec_attribution.py build \
  --repo . \
  --default-ref origin/main \
  --candidate-ref HEAD \
  --output <verify-spec-attribution.json>
```

Require exact:

```text
VERIFY-SPEC ATTRIBUTION: VALID
```

The manifest distinguishes:

```text
candidate_attributable_paths
    branch-side paths whose exact candidate blob is not current default-branch state

inherited_default_equivalent_paths
    branch-side paths whose exact candidate blob equals current default-branch state
```

Whole-repository Arid/JSCPD scanner scope is unchanged. The attribution manifest changes
**repair/blocking causality only**.

Before applying the retained `spec-differential` four-state classification, disposition a
scanner relation as `upstream-inherited` when all of these hold:

1. none of the relation's occurrence paths is in `candidate_attributable_paths`;
2. no candidate-attributable scanner configuration or suppression-policy change caused its
   visibility; and
3. the scanner completed normally.

`upstream-inherited` findings are reported as inherited repository state and do not enter
the `$verify-spec` repair loop or block Spec PASS. They are not silently called
`baseline-identical`; retain their actual upstream/default-branch causality.

Any relation touching at least one `candidate_attributable_paths` entry remains subject to
the retained Spec-baseline correlation and may become `candidate-introduced`,
`candidate-expanded`, `baseline-identical`, or `unresolved` as appropriate. Operational
scanner/source-processing errors remain blocking regardless of path attribution.

A path that diverges from current default branch is candidate-attributable even when it is a
workflow/control-plane path. This rule therefore cannot be used to hide Spec-owned or
branch-owned workflow divergence merely because the path is broadly classified as workflow
code.

The fixed Spec baseline is still supplied to `spec-differential` for historical correlation
of the remaining candidate-attributable relations. It must never be used to turn an exact
current default-branch-equivalent path into Spec-attributable duplicate debt.

## Protected control-plane boundary

When delegated by `$implement-ticket`, this skill has **zero authority** to modify protected
workflow/control-plane or semantic-authority paths. A duplicate finding does not grant such
authority, even when consolidation would otherwise be the preferred repository-wide repair.

Before classifying or repairing ticket-attributable findings, require:

```bash
python -m scripts.workflow_candidate_guard check \
  --anchor <execution-anchor>
```

Run it again after every deduplication repair batch and before returning control to
`$implement-ticket`.

If a candidate-introduced or candidate-expanded duplicate relation can be resolved only by
changing a protected path:

1. leave the protected path untouched;
2. do not add a suppression there;
3. do not weaken scanner configuration;
4. report the relation as blocked by the workflow/control-plane ownership boundary;
5. return control to `$implement-ticket` for upstream routing.

The protected path set is owned by `scripts.workflow_candidate_guard`; this skill must not
redefine, narrow, bypass, or locally override it.

If the candidate already contains a protected-path mutation, stop immediately. The parent
`$implement-ticket` may use its narrow restoration command to restore those paths exactly to
the Execution Anchor; `$deduplicate-code` itself does not perform that recovery.

## Terminal evidence for ticket-differential

In addition to the retained differential evidence, report:

```text
Ticket baseline: <immutable historical sha>
Execution Anchor: <exact comparison sha>
Differential comparison base: Execution Anchor
Protected control-plane candidate paths: 0
```

A ticket-differential PASS is invalid if the comparison worktree was created from
`TICKET_BASELINE`, if the supplied Execution Anchor is missing/mismatched, or if any
protected control-plane candidate path remains.

## Terminal evidence for spec-differential

In addition to the retained Spec differential evidence, report:

```text
Spec baseline: <immutable historical sha>
Default branch head: <exact attribution-manifest sha>
Candidate head: <exact attribution-manifest sha>
Candidate-attributable paths: <n>
Inherited default-equivalent paths: <n>
Upstream-inherited duplicate findings: <n>
```

A `spec-differential` PASS is invalid if the attribution manifest does not bind the exact
candidate HEAD or current fetched default-branch head, or if an unresolved relation remains.

All standalone/default behavior not explicitly overridden here remains unchanged from the
retained procedure.
