# Session Reconstitution

## Purpose

This guide defines how a new agent session should reconstruct enough Polaris context to continue prior work safely and efficiently.

It is a **bootstrap and recovery procedure**, not a source of architectural truth, workflow state, or domain semantics.

The goal is to avoid rebuilding project context from large conversation transcripts when the repository and tracker already preserve the durable state.

## Core Principle

Reconstitute from durable project state first.

Use prior conversation only for ephemeral session state such as:

- the exact task that was in progress;
- the last command or result exchanged;
- an uncommitted local change that is not visible remotely;
- a decision that has not yet been persisted to an authoritative artifact.

If remembered conversation conflicts with current durable state, surface the conflict and prefer the applicable authority defined by `AGENTS.md` unless the user explicitly resolves it otherwise.

## Authority

Start with `AGENTS.md` and follow its authority model.

In particular:

- code, configuration, executable checks, and relevant tests describe implementation reality;
- accepted ADRs define active architectural decisions;
- `docs/current/` describes current architecture;
- `wiki/entities/` contains derived architectural knowledge;
- workflow artifacts and native tracker relationships define delivery state;
- the GitHub Project is an operational projection and does not override authoritative repository or tracker state.

Do **not** read `CONTEXT.md` merely because a session is being reconstructed. Follow the `AGENTS.md` rules for when canonical domain vocabulary actually requires it.

## Reconstitution Procedure

### 1. Establish repository state

Inspect the current default branch and recent relevant commits.

Determine whether the user's local working tree may contain uncommitted or unpushed state that cannot be observed remotely. Never assume remote repository state includes those changes.

### 2. Load repository operating policy

Read `AGENTS.md` before interpreting project state or making changes.

Load narrower skills only when their responsibility is relevant to the active work. Prefer current skill contracts over remembered behavior from earlier sessions.

Common workflow skills include:

- `$wayfinder`
- `$to-specs`
- `$to-tickets`
- `$implement-ticket`
- `$verify-spec`
- `$review-spec`
- `$spec-merge-cleanup`
- `$architecture-remediation`
- `$project-tracking`

For source-code changes, follow `$coding-standards`.

For commits, follow `$conventional-commits` in `.agents/skills/conventional-commits/SKILL.md`. Do not reconstruct commit-message rules from memory or restate a divergent local convention.

For Living Entity Wiki work, use the current contracts for `$wiki-sync`, `$wiki-lint`, and `$wiki-synthesize` as applicable.

### 3. Identify the active durable artifacts

Determine which repository and tracker artifacts represent the work currently in progress.

Depending on the task, inspect only the smallest relevant set, such as:

- active Wayfinder maps;
- Specs and their dependency relationships;
- Tickets and Ticket baselines;
- verification or review receipts;
- current architecture documents and ADRs;
- `wiki/index.md` and relevant `wiki/entities/` pages;
- research or audit documents under `docs/research/`;
- process guidance under `docs/process/`;
- relevant GitHub Issues, pull requests, and Project projection state.

Do not perform a broad repository tour when narrower evidence is sufficient.

### 4. Reconstruct workflow state from durable evidence

Treat the delivery workflow as a state machine rather than assuming a one-way pipeline.

The normal path is approximately:

```text
$wayfinder
    ↓
$to-specs
    ↓
$to-tickets
    ↓
$implement-ticket
    ↓
$verify-spec
    ↓
$review-spec
    ↓
$spec-merge-cleanup
```

Verification failure, review findings, remediation, or genuine architectural ambiguity may cause re-entry into an earlier state.

Keep these concepts distinct:

- **technical dependency** — what is allowed to advance;
- **project focus** — what the team has chosen to advance now;
- **workflow state** — where an artifact is in its lifecycle;
- **Project state** — the board's projection of durable state.

Do not invent dependency edges to express project focus or work-in-progress preference.

### 5. Reconstruct architectural context only as needed

Use Wayfinders for genuine architectural uncertainty, not as a mandatory wrapper around ordinary cleanup or implementation.

Typical routing:

- obvious mechanical cleanup → direct change or focused Spec;
- dead or stale code with clear ownership → direct cleanup;
- structural refactor with known semantics → Refactor Spec;
- implementation of already accepted architecture → implementation work;
- unclear canonical ownership → Wayfinder;
- competing abstractions or unresolved boundaries → Wayfinder;
- implementation that would need to invent or change durable semantics → architecture re-entry.

Do not infer architectural uncertainty merely from file size, complexity, duplication, or poor metrics.

### 6. Restore only the ephemeral handoff from conversation

After durable state is reconstructed, use the previous session handoff to locate the exact stopping point.

A useful handoff should be short and contain only facts that are not cheaply recoverable from the repository, for example:

```markdown
### LAST ACTIVE THREAD

We were validating candidate CH-CANDIDATE-007 in the current code-health audit.
The deterministic measurements are already committed.
The last local command was `...`, which produced `...`.
No remediation has been started yet.
```

A few final materially relevant exchanges may be included when necessary, but avoid pasting full historical sessions unless the durable state is genuinely insufficient.

### 7. Check for conflicts before continuing

Before resuming work, identify any material conflict among:

- the user's handoff;
- current repository state;
- current tracker state;
- applicable skill contracts;
- architectural authorities.

Surface genuine conflicts explicitly rather than silently selecting whichever state is easiest to continue from.

### 8. Report the recovered state concisely

The initial response after reconstitution should state only:

- the current repository/workflow state;
- the active objective;
- the exact stopping point;
- the next logical action;
- any genuine uncertainty or blocker.

Do not respond with a generic Polaris overview or repeat every artifact inspected.

## Collaboration Boundary

Perform work directly through available repository, GitHub, and other connected tooling whenever possible.

Ask the user to run local commands only when the required state or tool is unavailable remotely, such as:

- uncommitted local changes;
- local test execution;
- profiling;
- local repository-analysis tools;
- environment-specific scripts or services.

When local execution is required, provide exact Linux/bash commands and use the returned output as evidence.

## Recommended New-Session Prompt

A new session normally needs only this bootstrap message:

```markdown
We are continuing work on Polaris:
https://github.com/sponge-b0b/Polaris

Reconstitute our working session using
`docs/process/session-reconstitution.md`.

Read the repository's current durable state rather than assuming previous
conversation state is still correct.

### LAST ACTIVE THREAD

[Briefly describe the exact task and stopping point. Include local-only state
or the last few materially relevant exchanges only when needed.]

After reconstructing the state, tell me where we are, what should happen next,
and whether you have any genuine blocking questions.
```

## Design Constraint

Keep this document focused on **how to recover context**, not on preserving the context itself.

If a rule, architectural decision, workflow contract, domain definition, audit finding, or delivery state already has an authoritative home elsewhere in Polaris, reference that source rather than copying it here.

That keeps session reconstitution stable even as the project evolves.