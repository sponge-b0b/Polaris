# Architecture Authority Admissibility Gate

This file is normative for `$architecture-remediation` and has precedence over any more
general routing language in `SKILL.md`.

Its purpose is to prevent an implementation-created invalid state from being mistaken for a
new semantic coordinate that requires Wayfinder or owner-decision work.

## Required ordering

Before creating, reopening, or reusing any semantic decision artifact, evaluate the blocker in
this order:

1. identify the exact **observed state** or interval that caused the blocker;
2. test whether current accepted authority **permits that state to exist**;
3. only when the state is admissible, test whether accepted authority determines the required
   behavior strongly enough;
4. only when the state is admissible **and** a material choice remains unresolved may new
   decision work be created or reopened.

Never reverse steps 2 and 3.

A blocker question such as "what should happen after X but before Y?" does not establish that
the X→Y intermediate state is part of the valid product state machine. The intermediate state
may instead be a defect introduced by an implementation strategy.

## Authority scan

For every blocker, inspect every materially applicable authority class, not only the narrow
owner contract that named the original obligation:

- typed CCL assertions;
- accepted ADRs and accepted decision records;
- current platform architecture and architecture constraints;
- the source workflow's frozen Spec/ticket/review/remediation contract;
- existing cross-owner or transaction-boundary authority when the blocker crosses one of those
  boundaries.

Record an explicit finding for every governing source checked. Do not infer missing semantics
from the absence of one exact sentence when a stronger invariant already forbids the observed
state.

Especially test accepted invariants concerning:

- atomic business admission/commit;
- required durable truth before success;
- historical reconstruction;
- immutable history;
- idempotency/receipt singularity;
- owner/version admission;
- lifecycle admission;
- recovery and continuity.

## Machine disposition

Persist one `polaris.architecture-authority-disposition/v1` artifact containing:

```json
{
  "schema": "polaris.architecture-authority-disposition/v1",
  "source_workflow": "$implement-ticket",
  "source_artifact": "https://github.com/...",
  "observed_state": "exact blocker state or interval",
  "governing_sources_checked": ["..."],
  "findings": [
    {
      "source": "...",
      "relation": "FORBIDS_STATE",
      "basis": "exact invariant and why it applies"
    }
  ],
  "material_coordinate": null,
  "disposition": "FORBIDDEN_BY_EXISTING_AUTHORITY",
  "decision_creation_allowed": false
}
```

Allowed finding relations:

```text
FORBIDS_STATE
FIXES_BEHAVIOR
DOES_NOT_RESOLVE_COORDINATE
CONFLICTS
```

Allowed dispositions:

```text
FORBIDDEN_BY_EXISTING_AUTHORITY
FIXED_BY_EXISTING_AUTHORITY
UNRESOLVED_MATERIAL_CHOICE
SOURCE_CONFLICT
```

Validate it before any semantic decision mutation:

```bash
python .agents/skills/architecture-remediation/scripts/authority_admissibility.py \
  <architecture-authority-disposition.json>
```

Require exactly:

```text
ARCHITECTURE AUTHORITY DISPOSITION: VALID
```

The validator deliberately gives `CONFLICTS`, then `FORBIDS_STATE`, then `FIXES_BEHAVIOR`
precedence over `DOES_NOT_RESOLVE_COORDINATE`. One narrower source that does not describe an
intermediate state cannot create a new semantic coordinate when stronger accepted authority
already forbids that state.

## Disposition rules

### `FORBIDDEN_BY_EXISTING_AUTHORITY`

The observed state is not an admissible product/business state under current authority.

Examples include an implementation-created partial-admission interval that violates an
existing atomicity/durability invariant, or a lifecycle state current authority explicitly
rejects.

Rules:

- **Do not** create, reopen, or reuse Wayfinder/owner-decision work for that state.
- **Do not** design receipt, visibility, retry, recovery, or lifecycle semantics for the invalid
  state merely because one implementation created it.
- Treat the blocker as an implementation/conformance defect against existing authority.
- Update the active architecture blocker to `resolved` with the exact existing authority and
  admissibility disposition.
- Return to the source workflow. For `$implement-ticket`, return to `$implement-ticket` with the
  failed implementation evidence and the requirement to choose a compliant realization.
- This return does **not** reopen feasibility and does not authorize inventing new semantics.

If pre-repair architecture routing created a decision artifact solely for this forbidden state,
mark that decision superseded/unnecessary under the repaired routing policy and remove it from
the active semantic frontier. Preserve its history; do not rewrite it as though it never
existed.

### `FIXED_BY_EXISTING_AUTHORITY`

The state is admissible and accepted authority already fixes the required behavior.

Do not create new semantic decision work. Use existing-authority/Spec reconciliation only when
a durable projection is actually stale; otherwise return to the source workflow with the exact
authority.

### `UNRESOLVED_MATERIAL_CHOICE`

This is the **only** disposition that permits new Wayfinder/owner-decision work.

It requires all of the following:

- the observed state is admissible under current authority;
- no governing source forbids it;
- no governing source already fixes the required behavior;
- no governing sources conflict materially;
- the artifact names one exact unresolved `material_coordinate`.

Only after the machine disposition validates with `decision_creation_allowed=true` may
`SKILL.md` governance routing create/reopen/reuse semantic decision work.

### `SOURCE_CONFLICT`

Accepted governing sources disagree materially. Do not create a new choice that silently picks
a winner. Route the exact source conflict through the repository's CCL conflict procedure.

## Implementation mechanism rule

An implementation mechanism may reveal a counterexample, but it does not by itself enlarge the
product state machine.

In particular, these facts are evidence about realization, not proof of a missing semantic
coordinate:

- a preferred database/vendor feature is unavailable;
- a mechanism needs additional deployment configuration;
- a prototype creates a crash/recovery interval;
- a queue, WAL, outbox, archive, or second transaction introduces a publication gap;
- a candidate deadlocks, retains resources, or has an operational burden.

Ask first whether existing authority requires a realization in which the problematic state
never escapes as admitted business truth. If yes, the state is forbidden and implementation
must choose another compliant realization.

## Existing decision reconciliation

When this gate is introduced after a decision was already created from the old routing policy,
re-run the gate against the original blocker before invoking that decision workflow.

If the result is `FORBIDDEN_BY_EXISTING_AUTHORITY` or `FIXED_BY_EXISTING_AUTHORITY`:

1. do not run the decision workflow;
2. mark the decision superseded/unnecessary (or close `not_planned` when that is the repository
   lifecycle representation);
3. remove it from the active Wayfinder frontier if it was added solely for the invalid route;
4. update the source architecture blocker to `resolved` by existing authority;
5. return to the source workflow.

This reconciliation is routing cleanup, not a new semantic decision.
