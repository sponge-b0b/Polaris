---
name: prototype
description: Build throwaway code to answer one concrete design question, then preserve only the useful conclusion.
compatibility: product=codex product=claude-code system=git network=none
---

# Prototype

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Pick a branch

Identify which question is being answered:

* **"Does this logic / state model feel right?"** → `LOGIC.md`. Build a tiny interactive terminal app that pushes the state machine through cases that are hard to reason about on paper.
* **"What should this look like?"** → `UI.md`. Generate several meaningfully different UI variations on a single route using the project's existing routing conventions.

If the question is genuinely ambiguous and cannot be resolved from context, ask. Otherwise choose the branch that best matches the surrounding work and state the assumption.

Before building, if the Living Entity Wiki exists, use `wiki/index.md` to read the relevant entity's Rejected Approaches. If the same approach was already rejected, do not silently retry it. Surface the prior reasoning; re-prototype only when circumstances have materially changed or a `Reconsider when:` condition may now apply.

## Rules

1. **Throwaway from day one.** Keep the prototype close to the code it explores, but name it clearly as a prototype.
2. **One command to run.** Use the project's existing tooling; do not introduce a new runner.
3. **No persistence by default.** Use memory unless persistence itself is the question. Any scratch persistence must be isolated and disposable.
4. **Skip production polish.** No abstractions, broad test suite, production observability, or generalized error handling beyond what is needed to answer the question reliably.
5. **Surface the state.** After each logic action or UI variant switch, expose the relevant resulting state.
6. **Test only the question.** Do not mistake incidental prototype choices—single-file structure, no DI, in-memory storage, etc.—for validated production architecture.

## Verdict

Classify the result as:

* **Validated** — the tested idea is worth carrying forward.
* **Invalidated** — the experiment produced concrete evidence against the approach.
* **Inconclusive** — the experiment did not answer the question reliably.

### Validated

Do not treat the prototype as production implementation.

If the user wants the idea implemented, hand it to the normal implementation workflow. Production changes still require their normal `$wiki-sync`, `$coding-standards`, `$tdd`, `$database-migrations`, and `$verify-code` handling as applicable.

A successful prototype is **not itself a wiki write trigger**.

### Invalidated

Capture the question and failure reason in the relevant issue or ticket.

If the failure represents a durable architectural rejection and the Living Entity Wiki exists, use `$wiki-sync` to record it as a Rejected Approach with:

`source: session experiment, undocumented`

Do not record ordinary prototype bugs, environment failures, temporary priorities, or unsupported agent judgment as architectural rejection.

If the result warrants an ADR under `$to-adr-doc`, use that lifecycle instead.

### Inconclusive

Report what was learned and what remains unknown. Do not manufacture an accepted or rejected conclusion.

## Domain discoveries

If the experiment changes or clarifies canonical domain meaning, use `$domain-modeling`.

Do not put implementation details into `CONTEXT.md`.

## Cleanup

Prototype code is disposable. Remove it once its useful knowledge has been captured unless the user explicitly wants the experiment preserved.

If preserved, keep it out of normal production history and respect any parent workflow's branch guard; never switch branches behind `$implement-ticket`.

## Handoff

Report:

* question tested;
* prototype path and run command;
* scenarios or variants exercised;
* verdict and evidence;
* whether the prototype was removed or preserved;
* any `$domain-modeling`, `$to-adr-doc`, or `$wiki-sync` outcome.

Clearly distinguish **prototype validated** from **production implementation completed**.
