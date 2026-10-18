---
name: deduplicate-code
description: Enforces repository-wide duplicate-code discipline, with zero unsuppressed findings by default and Execution-Anchor differential causality for ticket verification.
license: MIT
compatibility: product=codex product=claude-code system=arid system=jscpd network=none
metadata:
  version: 2.5.0
---

# Code Duplication Checks

## Authoritative procedure composition

Before executing this skill, read `.agents/skills/deduplicate-code/PROCEDURE.md` in full.
That file preserves the complete established duplicate-code procedure. This `SKILL.md` is
the authoritative entrypoint and owns the ticket-differential and control-plane corrections
below; on conflict, this file wins.

All retained whole-repository scanner scope, finding classification, consolidation,
suppression-merit, migration/test-surface, forbidden-silencing, rerun, and evidence rules
remain normative except where this entrypoint explicitly replaces Ticket-baseline-relative
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

The fixed Spec baseline behavior for `$verify-spec` `spec-differential` is unchanged.

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

All standalone/default and `$verify-spec` behavior not explicitly overridden here remains
unchanged from the retained procedure.
