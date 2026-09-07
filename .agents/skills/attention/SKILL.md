---
name: attention
description: Surface material concerns proactively without gaining mutation, design, scope, or workflow authority.
compatibility: product=codex product=claude-code system=git network=none
disable-model-invocation: true
---

# Attention

`$attention` is Polaris's reusable **report-only** concern-surfacing skill.

It exists to prevent an agent from silently proceeding past something material merely because the current task, checklist, tests, or workflow did not explicitly ask the right question.

The always-on duty lives in `AGENTS.md`. This skill provides a deliberate sweep for formal workflow checkpoints.

## Authority Boundary

Attention may:

* notice;
* inspect;
* compare against authority;
* challenge assumptions;
* surface concerns;
* recommend routing or questions.

Attention may **not**:

* mutate repository, tracker, Project, or runtime state;
* change scope;
* make product, domain, architecture, or design decisions;
* approve its own recommendation;
* repair the concern;
* override the owning workflow or its human-approval boundary.

A concern becomes blocking only because an existing governing rule makes it blocking. `$attention` does not create independent blocking authority.

## Materiality

Surface a concern when it could materially affect one or more of:

* correctness or failure behavior;
* product/domain meaning;
* identity, lifecycle, temporal, authority, provenance, or persistence semantics;
* architecture or dependency boundaries;
* public/downstream contracts;
* data integrity or security;
* maintainability, accidental complexity, or duplicate meaning;
* domain/public naming likely to mislead future consumers;
* verification completeness or hidden assumptions;
* workflow/process correctness;
* a materially better or safer approach that current work may be overlooking.

Do not interrupt for trivial stylistic preference, private local naming with no material effect, or speculative future work with no present consequence.

## Sweep Procedure

At a formal checkpoint:

1. Recover the exact current artifact/change and the authority already loaded by the owning workflow.
2. Look outward from the intended transition, not only inward from the diff or checklist.
3. Ask what a competent reviewer, downstream consumer, domain owner, or future maintainer could reasonably find surprising, ambiguous, under-specified, unsafe, or unnecessarily constraining.
4. For every candidate concern, determine whether current authority already resolves it.
5. Do not invent a resolution when authority is silent.
6. Report every material concern before the owning workflow crosses the checkpoint.

Useful challenge questions include:

* Is a public/domain name understandable at its import/use site without hidden conversational context?
* Did an implementation choose a representation, identity scheme, cardinality, state meaning, failure meaning, or public shape that upstream authority never established?
* Could two reasonable implementations satisfy the written requirement while creating materially different downstream contracts?
* Does a convenient primitive (`str`, mapping, generic metadata, nullable sentinel, broad enum, etc.) weaken a semantic distinction the domain claims to own?
* Did a single type collapse distinctions the authoritative design keeps separate?
* Does equality/ordering/serialization behavior accidentally create domain meaning?
* Are we proving the actual authoritative claim, or only the behavior we happened to implement/test?
* Is an abstraction/name broad or generic enough to hide its bounded context?
* Did current work create an unnecessary framework, compatibility path, representation, or coupling?
* Is a valid concern being silently treated as out of scope instead of surfaced and, when warranted, durably deferred?

## Workflow Checkpoint Profiles

### `$wayfinder`

Before route-clear/downstream handoff, challenge whether any material architecture/design choice, contract, boundary, or ambiguity remains unresolved even if all previously listed questions are closed.

### `$to-specs`

Before publication/amendment as implementation-ready, challenge whether the planning/design authority is detailed enough that implementation will execute rather than invent. In particular apply the materially-different-implementations test from `AGENTS.md`.

### `$to-tickets`

Before proposal-readiness certification/publication, challenge whether decomposition delegates any material design/public-contract choice to `$implement-ticket`.

### `$implement-ticket`

Before first substantive mutation, challenge each material choice as:

```text
authorized contract
semantically equivalent mechanic
design gap
```

A `design gap` is routed under the owning workflow's fail-closed rule before that choice is implemented.

Before closure evidence is frozen, sweep the actual public/durable change surface again for suspicious representations, ambiguous naming, unowned contracts, accidental semantic collapse, and hidden assumptions introduced during coding.

### `$verify-ticket-closure`

During the independent adversarial sweep, explicitly challenge whether the candidate introduces an unowned material design/public contract even when all explicit ticket tests/checks pass.

### `$verify-spec`

Before integrated certification is finalized, look for cross-ticket contradictions, duplicated semantics, interface mismatches, lifecycle/identity inconsistencies, or design gaps visible only in composition.

### `$review-spec`

Before review exit, surface material correctness, architecture, naming, coupling, maintainability, or future-constraint concerns even when formal acceptance is otherwise satisfied.

## Output

When no material concern remains:

```text
ATTENTION: CLEAR
Checkpoint: <workflow/stage or direct task>
Material concerns: 0
```

When concerns exist:

```text
ATTENTION: FINDINGS
Checkpoint: <workflow/stage or direct task>

1. <concise concern>
   Observation: <what was noticed>
   Why it matters: <material consequence>
   Authority: <resolved by source | unresolved | conflicting>
   Recommendation/routing: <what should happen next>
   Blocking basis: <existing workflow rule | none>
```

Keep the result compact and decision-useful. Do not bury the owning workflow in a generic review essay.

## Deferred Concerns

If a finding is valid but outside the active scope and does not block the current transition, do not fix it opportunistically. Use the repository's established Deferred Future Work Capture policy when the concern is worth preserving durably.

Attention is the sensing mechanism; existing workflow/design/architecture authority decides what happens next.