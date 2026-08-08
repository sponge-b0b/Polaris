---

name: domain-modeling
description: Actively build and sharpen the project's domain model by challenging terminology, stress-testing concepts with concrete scenarios, reconciling domain language with observed implementation, and maintaining canonical glossary vocabulary in CONTEXT.md. Keeps domain vocabulary separate from architectural decisions, implementation details, and Living Entity Wiki topology.
compatibility: product=codex product=claude-code network=none
-------------------------------------------------------------

# Domain Modeling

Actively build and sharpen the project's domain model while designing.

This is an **active modeling discipline**:

* challenge ambiguous terminology;
* distinguish concepts that are being conflated;
* invent concrete edge cases;
* test relationships and invariants of the domain language;
* capture resolved vocabulary immediately.

Merely reading `CONTEXT.md` to understand existing terminology is **not** `$domain-modeling`.

Use this skill when the domain model itself is being questioned, refined, or extended.

---

# Core Boundary

`CONTEXT.md` is the canonical **domain glossary**.

It is not:

* an architecture document;
* an implementation guide;
* a project-status document;
* a roadmap;
* a scratchpad;
* an ADR;
* a repository map;
* a copy of the Living Entity Wiki.

Its job is to answer:

> What does this domain term mean in Polaris?

It should not answer:

> Which class implements it?

> Which database stores it?

> Which service owns it?

> What architecture are we planning?

> What has already been implemented?

Those questions belong elsewhere.

---

# File Structure

Polaris normally uses a single-context domain-doc layout:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
└── src/
```

Create files lazily.

If `CONTEXT.md` does not yet exist, create it only when the first canonical term has actually been resolved.

Do not create empty domain-document scaffolding merely because this skill was invoked.

---

## Multiple Bounded Contexts

If a root:

```text
CONTEXT-MAP.md
```

exists, use it to locate the appropriate domain glossary for the bounded context being modeled.

Do not assume a technical package or Living Entity Wiki entity is automatically a DDD bounded context.

Likewise:

```text
bounded context ≠ wiki entity
```

by default.

If domain modeling reveals that the project's bounded-context decomposition itself may need to change, surface that as a deliberate modeling decision.

Do not automatically:

* create a new context;
* split `CONTEXT.md`;
* create `CONTEXT-MAP.md`;
* map each bounded context to a wiki entity;
* restructure entity topology.

A domain boundary and an architectural knowledge boundary may align, but neither mechanically determines the other.

---

# During the Session

## 1. Load the Relevant Glossary

When actively modeling a domain concern, read the relevant `CONTEXT.md` before introducing or redefining terminology.

If `CONTEXT-MAP.md` exists, use it to locate the appropriate glossary first.

Do not scan unrelated context glossaries unless the modeling question crosses those contexts.

---

# 2. Challenge Existing Vocabulary

When the user uses a term differently from the canonical glossary, surface the mismatch immediately.

Example:

```text
CONTEXT.md defines "cancellation" as termination of the entire Order,
but the current discussion uses "cancellation" for removing one OrderLine.

Are those intended to be the same concept?
```

Do not silently redefine the canonical term based on one new usage.

Resolve the semantic difference first.

---

# 3. Sharpen Fuzzy or Overloaded Language

When one word appears to represent multiple domain concepts, propose explicit distinctions.

Example:

```text
"account" currently appears to mean both the customer organization and
an authenticated user identity.

Those should remain one concept only if the domain actually treats them
as the same thing.
```

Prefer precise domain vocabulary over generic software terminology.

Common warning signs include words such as:

```text
account
record
item
state
status
event
request
result
model
strategy
position
signal
run
execution
```

when their meaning changes by context.

Do not rename a concept merely because another name sounds cleaner.

The new term must represent a real semantic distinction.

---

# 4. Stress-Test Concepts With Concrete Scenarios

Use specific scenarios to expose ambiguity.

Prefer:

```text
A Strategy Recommendation is generated Monday.
The user changes the intended holding period Tuesday.
Is the existing Recommendation still the same domain object,
a superseded Recommendation, or a new Recommendation?
```

over:

```text
How should recommendations work?
```

Probe:

* identity;
* lifecycle;
* ownership;
* cardinality;
* state transitions;
* temporal behavior;
* invalid states;
* partial operations;
* duplication;
* replacement;
* cancellation;
* conflicting inputs;
* boundary cases.

The goal is not to invent product behavior arbitrarily.

The goal is to expose where the current language does not yet let the user answer precisely.

---

# 5. Distinguish Domain Rules From Architecture

A domain rule describes the meaning or valid behavior of the business/domain concept.

An architectural rule describes how the software realizes or constrains that domain.

Example domain statement:

```text
A Recommendation describes one proposed course of action for one
analysis context.
```

Potentially valid for `CONTEXT.md`.

Example architectural statement:

```text
Recommendations are persisted in PostgreSQL through RecommendationRepository.
```

Not glossary content.

Example architectural constraint:

```text
Qdrant must never become the canonical writer for Recommendations.
```

Not glossary content.

Do not put implementation or architecture into `CONTEXT.md` merely because it relates to a domain term.

---

# 6. Cross-Reference With Implementation

When a modeling claim describes behavior that should already exist, inspect relevant implementation evidence.

Use the project's normal repository-analysis tools when needed, such as:

* `$repowise`;
* `$codegraph`;
* `$codebase-memory-mcp`;
* `$graphify`.

Example:

```text
The proposed domain model says an Order can be partially cancelled,
but current implementation appears to support only whole-order cancellation.
```

Surface the discrepancy.

Do not automatically conclude:

```text
code wins
```

or:

```text
glossary wins
```

The code provides evidence of current implementation.

The domain discussion determines intended meaning.

The discrepancy may mean:

* the domain statement is wrong;
* implementation is incomplete;
* terminology is overloaded;
* a migration is required;
* an architectural decision is missing.

Resolve the semantic question before changing canonical vocabulary.

---

# 7. Update `CONTEXT.md` Immediately When a Term Is Resolved

Once a domain term or distinction has actually been resolved, update the relevant `CONTEXT.md` during the session.

Do not wait until the end and reconstruct decisions from memory.

If `CONTEXT-FORMAT.md` exists and remains the repository's declared glossary format, follow it.

Otherwise preserve the established structure of the existing `CONTEXT.md`.

Do not gratuitously reformat unrelated glossary entries.

---

## What a Glossary Entry May Contain

Appropriate content includes:

* canonical term;
* precise definition;
* meaningful distinction from similar terms;
* domain-level relationship to another concept;
* aliases or deprecated terminology where useful;
* domain-level lifecycle meaning where necessary to define the concept.

---

## What a Glossary Entry Must Not Contain

Do not add:

* Python class names;
* module paths;
* service ownership;
* provider/client architecture;
* repository paths;
* database-table names;
* storage-engine choices;
* API endpoints;
* dependency-injection details;
* implementation completeness;
* rollout state;
* migration instructions;
* architectural rationale unrelated to the term's meaning;
* Planned work.

Example of **wrong** glossary content:

```text
Recommendation

Implemented by RecommendationService in
src/polaris/application/recommendations/service.py and stored in PostgreSQL.
```

Example of appropriate glossary content:

```text
Recommendation

A domain-level proposed course of action produced from an analysis context.
It expresses advice; it is not an execution instruction.
```

---

# 8. Treat `CONTEXT.md` Changes as Vocabulary Changes

Updating canonical vocabulary does not by itself trigger `$wiki-sync`.

The Living Entity Wiki is not a second domain glossary.

Do not automatically:

* add the glossary definition to an entity page;
* create a `wiki/log.md` entry;
* create a wiki commit;
* change entity topology.

When an entity page is later modified for a legitimate `$wiki-sync` reason, use the canonical terminology from `CONTEXT.md`.

If a vocabulary change reveals that existing architecture documentation or entity wording is now semantically wrong rather than merely using an older synonym, surface the affected material for deliberate correction.

Do not silently broaden a glossary edit into a repository-wide architecture rewrite.

---

# 9. Escalate Durable Architectural Outcomes Through the Correct Owner

Domain modeling sometimes exposes something that is not merely vocabulary.

Route the result according to what actually crystallized.

---

## Domain Term or Semantic Distinction

Write:

```text
CONTEXT.md
```

No architecture document is required merely because a term became clearer.

---

## Architectural Decision

If the discussion establishes a real architectural decision, apply the criteria owned by `$to-adr-doc`.

Do not duplicate those criteria here.

When warranted, use `$to-adr-doc`.

Examples might include a decision about:

* canonical ownership;
* a hard system boundary;
* an intentionally rejected architectural alternative;
* a difficult-to-reverse architectural choice.

Do not turn every useful modeling conclusion into an ADR.

---

## Durable Current Architecture Description

If domain modeling reveals current architecture that deserves authored documentation but does not warrant an ADR, create the appropriate non-ADR document through `$to-doc`.

Do not place that architecture into `CONTEXT.md`.

---

## Durable Proposed Architecture

If the modeling work crystallizes meaningful future architecture that belongs in authored documentation but is not yet an accepted ADR, use `$to-doc` so it is classified appropriately.

Do not use `CONTEXT.md` as a future-state design document.

---

## Existing Architecture Document Needs Reclassification

Use `$classify-doc`.

Do not manually move an existing document as a side effect of domain modeling.

---

# 10. Apply `$wiki-sync` Only When Its Real Triggers Occur

Domain modeling does not receive a special wiki exemption, but ordinary glossary edits do not trigger the wiki lifecycle either.

Invoke `$wiki-sync` when domain-modeling work also results in one of its normal triggers, including:

* substantive source-code changes;
* substantive `docs/current/` or `docs/proposed/` changes;
* ADR lifecycle activity through `$to-adr-doc`;
* an actual entity-topology decision.

Do not invoke `$wiki-sync` merely because:

```text
CONTEXT.md changed
```

or:

```text
a new domain concept was named
```

unless that same work also changed architecture through a normal trigger.

---

# 11. Do Not Derive Wiki Entity Topology From the Domain Model

DDD modeling is a useful signal for architectural decomposition.

It is not the entity registry's source of truth.

Do not automatically:

```text
new domain term → new entity
```

```text
bounded context → entity
```

```text
aggregate → entity
```

```text
domain service → entity
```

Entity creation, promotion, split, merge, rename, and removal follow the topology rules in `wiki/_schema.md` and are maintained through `$wiki-sync`.

If a domain-modeling session produces evidence that entity topology may now be wrong, surface that evidence and let the topology workflow evaluate it.

---

# 12. Source Conflicts

If domain modeling exposes material disagreement among:

* accepted ADRs;
* `docs/current/`;
* verified implementation evidence;

surface:

```text
[source-conflict]
```

through the normal wiki/architecture lifecycle.

Do not resolve an architectural source conflict by redefining a domain term in `CONTEXT.md`.

Changing vocabulary must not be used to disguise incompatible architectural claims.

---

# 13. Keep Domain History Only When It Helps Current Meaning

`CONTEXT.md` describes the **current canonical vocabulary**.

Do not accumulate a chronological decision log inside it.

If terminology changes:

* update the canonical definition;
* preserve a former term or alias only when readers may still encounter it and need translation.

Example:

```text
Historical alias: Trade Proposal
```

may be useful.

A narrative such as:

```text
In March we called this X, then tried Y, then Bob suggested Z...
```

does not belong in the glossary.

Architectural decision history belongs in ADRs.

Git provides file history.

---

# 14. Completion Check

Before considering a domain-modeling pass complete, ask:

### Vocabulary

* Are newly important terms defined precisely?
* Are overloaded words separated where necessary?
* Are aliases or obsolete names clear?
* Are neighboring concepts distinguishable?

### Domain behavior

* Were ambiguous relationships stress-tested with concrete scenarios?
* Are identity and lifecycle semantics clear enough for the current work?

### Implementation comparison

* Were claims about existing behavior checked against current evidence when appropriate?
* Were discrepancies surfaced rather than silently normalized?

### Separation of concerns

* Does `CONTEXT.md` remain free of implementation detail?
* Were architectural decisions routed to `$to-adr-doc` where warranted?
* Were architecture documents routed through `$to-doc` or `$classify-doc`?
* Was `$wiki-sync` invoked only if a genuine wiki trigger occurred?
* Was entity topology left to `wiki/_schema.md` and `$wiki-sync`?

---

# Handoff

Report only the outcomes relevant to the modeling work:

* canonical terms added or changed;
* important distinctions resolved;
* unresolved domain questions;
* implementation/domain discrepancies discovered;
* architectural decisions escalated to `$to-adr-doc`;
* non-ADR architecture documents created through `$to-doc`;
* existing documents reclassified through `$classify-doc`;
* any normal `$wiki-sync` trigger that occurred and its result.

Do not report a wiki update when only `CONTEXT.md` changed and no wiki lifecycle trigger occurred.

---

# Out of Scope

`$domain-modeling` does not:

* use `CONTEXT.md` as an implementation specification;
* record current architecture in the glossary;
* record future architecture in the glossary;
* define ADR lifecycle — use `$to-adr-doc`;
* create ordinary architecture documents outside `$to-doc`;
* reclassify existing docs outside `$classify-doc`;
* maintain Living Entity Wiki claims directly — use `$wiki-sync`;
* derive entity topology mechanically from DDD concepts;
* resolve `[source-conflict]`;
* refactor code merely to make names match the glossary unless that implementation change is actually part of the requested work.

Its job is to make the project's **domain language precise enough that architecture and implementation can be reasoned about without semantic ambiguity**.
