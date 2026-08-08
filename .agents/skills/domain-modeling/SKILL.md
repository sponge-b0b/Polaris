---

name: domain-modeling
description: Actively sharpen the project's domain model by resolving terminology, stress-testing concepts, reconciling domain language with implementation, and maintaining canonical vocabulary in CONTEXT.md.
compatibility: product=codex product=claude-code network=none
-------------------------------------------------------------

# Domain Modeling

Actively build and sharpen the project's domain model as you design.

This is the **active** discipline: challenge terms, invent edge-case scenarios, reconcile stated behavior with the code, and capture resolved vocabulary as it crystallizes.

Merely reading `CONTEXT.md` for vocabulary is not `$domain-modeling`.

## File Structure

Most repositories use a single domain glossary:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── src/
```

If `CONTEXT-MAP.md` exists, use it to locate the appropriate bounded-context glossary.

Do not assume a bounded context, package, or wiki entity automatically maps one-to-one to another.

Create glossary files lazily — only when there is resolved vocabulary to record.

## During the Session

### Challenge Against the Glossary

When the user uses a term inconsistently with `CONTEXT.md`, surface the conflict immediately.

Example:

> `CONTEXT.md` defines "cancellation" as X, but this discussion seems to use it as Y. Are those intended to be different concepts?

Do not silently redefine an existing canonical term.

### Sharpen Fuzzy Language

When a term is vague or overloaded, propose a more precise distinction.

Example:

> You're using "account" for both the customer organization and the authenticated user. Are those actually the same domain concept?

Prefer canonical domain language over generic software terminology.

### Discuss Concrete Scenarios

Stress-test domain relationships with specific scenarios, especially around:

* identity;
* lifecycle;
* state transitions;
* ownership;
* cardinality;
* partial operations;
* invalid states;
* temporal behavior.

Use scenarios to expose ambiguity, not to invent product behavior arbitrarily.

### Cross-Reference With Code

When a claim describes behavior that should already exist, inspect the implementation.

If code and the proposed domain model disagree, surface the discrepancy rather than silently deciding which is correct.

The discrepancy may indicate:

* incorrect vocabulary;
* incomplete implementation;
* an overloaded concept;
* a missing architectural decision.

Resolve the semantic question first.

## Update `CONTEXT.md` Inline

When a term or distinction is resolved, update `CONTEXT.md` immediately rather than batching glossary changes until the end.

Follow `CONTEXT-FORMAT.md` when present.

`CONTEXT.md` is a **domain glossary only**.

It may contain:

* canonical terms;
* precise definitions;
* meaningful distinctions;
* domain-level relationships;
* useful aliases or deprecated terminology.

It must not contain:

* implementation details;
* class or module paths;
* database choices;
* architecture decisions;
* project status;
* roadmap items;
* Planned work.

A glossary entry explains **what a domain concept means**, not how Polaris implements it.

## Keep Domain and Architecture Separate

A resolved domain statement belongs in `CONTEXT.md`.

An architectural decision belongs through `$to-adr-doc` when its criteria are met.

Durable current or proposed architecture that does not warrant an ADR belongs through `$to-doc`.

If an existing non-ADR document needs reclassification, use `$classify-doc`.

Do not use `CONTEXT.md` as a substitute for architecture documentation.

## Living Entity Wiki

A `CONTEXT.md` vocabulary change is **not by itself a `$wiki-sync` trigger**.

Do not copy glossary definitions into entity pages or create `wiki/log.md` entries merely because terminology changed.

Use `$wiki-sync` only when the domain-modeling session also causes one of its normal triggers, such as:

* substantive source-code changes;
* substantive `docs/current/` or `docs/proposed/` changes;
* ADR lifecycle activity;
* an approved entity-topology change.

Do not derive wiki entities mechanically from:

* domain terms;
* aggregates;
* bounded contexts;
* domain services.

Entity topology remains governed by `wiki/_schema.md` and `$wiki-sync`.

## Source Conflicts

If domain modeling exposes material disagreement between accepted ADRs, current architecture docs, and verified implementation evidence, surface `[source-conflict]`.

Do not resolve an architectural conflict by redefining terminology in `CONTEXT.md`.

## Handoff

Report:

* canonical terms added or changed;
* important distinctions resolved;
* unresolved domain questions;
* implementation/domain discrepancies discovered;
* any `$to-adr-doc`, `$to-doc`, `$classify-doc`, or `$wiki-sync` outcome.

Do not report a wiki change when only `CONTEXT.md` changed.
