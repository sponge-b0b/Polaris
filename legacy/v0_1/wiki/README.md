# Living Entity Wiki

The Living Entity Wiki is Polaris's durable, derived architectural memory.

It organizes architectural knowledge around stable conceptual entities rather than files, packages, or transient implementation structure. Its purpose is to preserve the knowledge that developers and agents should not have to rediscover from scratch every time they work in the repository: why boundaries exist, which invariants constrain them, which approaches were rejected and why, which questions remain unresolved, and which accepted or proposed directions have not yet been realized.

The wiki is **derived knowledge, not architectural authority**. It learns from authoritative decisions, current documentation, implementation evidence, and owner-reviewed experience while preserving the provenance and uncertainty of what it learns.

> **The Living Entity Wiki is self-learning, but not self-authorizing.**
>
> It may discover a pattern. It may not turn that pattern into architectural truth.

## Why It Exists

Large, evolving systems accumulate important knowledge in many places:

* source code and tests describe what currently exists;
* ADRs preserve architectural decisions;
* current documents describe the active architecture;
* proposed documents describe intended future direction;
* implementation work reveals constraints, failed approaches, and unresolved questions;
* conversations and experiments often contain useful reasoning that would otherwise disappear with the session.

A developer or coding agent can rediscover some of this by repeatedly searching the repository, reading documents, tracing code, and reconstructing history. But repeated rediscovery is expensive, incomplete, and especially poor at preserving **why** a decision exists or **why** an apparently reasonable alternative was rejected.

The Living Entity Wiki turns qualified architectural knowledge into a persistent, navigable memory that compounds as the system evolves.

```text
architecture + implementation + experience
                  ↓
         qualified durable knowledge
                  ↓
          Living Entity Wiki
                  ↓
       future development starts
       with accumulated context
```

It is deliberately not a mirror of the repository. Mechanically derivable information such as file inventories, dependency graphs, call chains, and ordinary implementation details remains live evidence rather than duplicated wiki state.

## Origin

### Andrej Karpathy's LLM Wiki

The Living Entity Wiki is based on Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern, published on April 4, 2026.

Karpathy's core idea is that an LLM-backed knowledge system should not repeatedly rediscover the same knowledge from raw sources at query time. Instead, the LLM incrementally builds and maintains a persistent wiki between the user and those sources. New information is integrated into the existing knowledge structure, contradictions are surfaced, relationships are maintained, and synthesis compounds over time.

The key insight adopted by Polaris is:

> **Knowledge should compound rather than be repeatedly rediscovered.**

Karpathy intentionally described a pattern rather than a fixed implementation. Polaris adapts that pattern specifically for software architecture and agent-assisted development.

### The Polaris Adaptation

Polaris narrows the original general-purpose knowledge-base concept into a provenance-aware architectural memory.

The adaptation adds several constraints that are important in a software repository:

* architectural authority remains outside the wiki;
* authority is claim-specific rather than globally ranked;
* only durable architectural knowledge qualifies for persistence;
* entity boundaries are governed rather than inferred casually from directory structure;
* every durable claim retains eligible source or decision provenance;
* uncertainty and authoritative disagreement are represented explicitly;
* repository-wide linting independently challenges accumulated wiki state;
* cross-entity synthesis is report-only and cannot promote inference into authority;
* topology may evolve, but only through explicit boundary decisions and controlled rules.

The result is not a general-purpose project wiki. It is a persistent architectural-memory system built on the LLM Wiki idea.

## Evolution in Polaris

The first Polaris Living Entity Wiki was bootstrapped on August 9, 2026 as part of a broader normalization of architectural authority and documentation.

The initial bootstrap established **18 architectural entities** and **4 cross-cutting discovery documents** from an owner-approved entity-boundary determination and normalized documentation set. The introducing commit, `7bf7656`, aligned architectural documents to entities, separated historical audit material from current authority, and added the first Living Entity Wiki pages with updated authority citations.

From that bootstrap, the wiki evolved into three complementary operating modes:

```text
$wiki-sync       maintain durable knowledge around a change
$wiki-lint       independently audit accumulated knowledge
$wiki-synthesize discover higher-order patterns for human review
```

The current schema, skills, and entity state define the system as it exists now; this history explains how it began, not how current behavior should be inferred.

## Core Idea: Architecture Around Durable Entities

An **entity** is a durable architectural boundary whose meaning should survive ordinary implementation refactoring.

An entity is not automatically a:

* directory;
* package;
* class;
* service;
* module;
* technology choice.

No single structural signal determines an entity boundary. After bootstrap, a new sub-boundary normally requires at least two of three signals defined in [`_schema.md`](_schema.md):

1. a meaningful structural boundary;
2. independent invariants;
3. material fan-in from at least two entities outside its parent boundary.

This keeps the wiki organized around architectural concepts rather than mirroring whichever folder structure happens to exist today.

The authoritative registry of active entities is [`index.md`](index.md). It owns each entity's stable ID, category, implementation state, routing anchors, and concise scope summary.

## Source Authority and Trust Model

There is no single global source-of-truth ladder. Authority is **claim-specific**:

| Source | Authority |
| --- | --- |
| Code, configuration, tests, executable checks | Implementation reality |
| Accepted ADRs | Active architectural decisions |
| `docs/current/` | Current architectural description |
| Entity pages | Derived knowledge only |

Accepted ADRs may describe decisions whose implementation is still pending. `docs/current/` is usable as active authority only when materially consistent with applicable accepted ADRs and verified implementation evidence.

The wiki never becomes authoritative merely because it is persistent, well organized, or repeatedly consulted.

```text
authoritative sources
        ↓
 derived interpretation
        ↓
 Living Entity Wiki
```

Never reverse that arrow by changing authoritative sources merely to make them agree with the wiki.

## The Knowledge Model

Entity pages follow [`_template.md`](_template.md) and preserve only qualified durable knowledge.

### Boundary Rationale

Explains **why the entity is a distinct architectural boundary and why the boundary sits where it does**.

Boundary Rationale changes only through an explicit boundary or topology decision. Moving files or reorganizing packages is not sufficient evidence that the conceptual boundary changed.

### Strict Invariants

Record constraints that are actively true and matter architecturally, including the causal reason they matter.

Eligible authority comes from accepted ADRs and `docs/current/`, subject to implementation evidence and source-consistency rules.

A good invariant preserves more than a rule. It preserves the reason the rule exists so future work can distinguish a load-bearing architectural constraint from accidental implementation shape.

### Rejected Approaches

Preserve approaches rejected for a load-bearing reason, concrete failed experiments, or documented decisions.

A rejection records **why** the approach was rejected and may include a genuine `Reconsider when:` condition.

This creates causal memory rather than cargo-cult rules:

```text
not:  "Do not use X."

but:  "X was rejected because Y.
       Reconsider when Z materially changes."
```

Unsupported agent preference is not sufficient provenance for a Rejected Approach.

### Open Questions

Preserve concrete unresolved concerns without pretending they are facts or decisions.

An agent-observed concern may be recorded as an unresolved question with that provenance, but it remains a question until resolved through the proper workflow.

This gives uncertainty a durable home instead of forcing premature certainty or losing the concern when a session ends.

### Planned

Preserves future architectural state that is not yet current:

* proposed ADR or `docs/proposed/` direction;
* accepted decisions whose implementation is still pending.

Planned content never describes current implementation merely because the future direction has been accepted.

## How the Wiki Works

The Living Entity Wiki has three distinct operational responsibilities.

### 1. Change-Time Synchronization — `$wiki-sync`

[`$wiki-sync`](../.agents/skills/wiki-sync/SKILL.md) maintains derived wiki knowledge around a **specific substantive change**.

It runs around relevant source-code changes and after meaningful ADR, current/proposed document, or entity-topology changes.

Its basic loop is:

```text
authoritative or implementation state changes
                  ↓
             $wiki-sync
                  ↓
      re-evaluate affected entities
                  ↓
       durable knowledge changed?
           ├─ no  → no wiki mutation
           └─ yes → update entity/index/log atomically
```

Touching code does not automatically justify a wiki edit. The wiki changes only when durable architectural knowledge changes: an invariant, accepted realization, qualifying rejection, open question, boundary rationale, or topology.

This prevents "living documentation" from becoming documentation churn.

### 2. Repository-Wide Audit — `$wiki-lint`

[`$wiki-lint`](../.agents/skills/wiki-lint/SKILL.md) independently audits the accumulated Living Entity Wiki.

It checks the whole system for conditions such as:

* structural integrity problems;
* broken, stale, or invalid citations;
* authoritative-source conflicts;
* document drift;
* implementation drift;
* stale Open Questions;
* cross-entity contradictions;
* document-classification problems.

A clean run reports only. Judgment-bearing findings are routed to the proper owner rather than silently repaired.

The distinction is intentional:

```text
$wiki-sync  → maintain one change
$wiki-lint  → challenge the accumulated whole
```

### 3. Cross-Entity Synthesis — `$wiki-synthesize`

[`$wiki-synthesize`](../.agents/skills/wiki-synthesize/SKILL.md) performs deliberate higher-inference analysis across the full wiki.

It looks for patterns that no single entity necessarily states alone, especially:

* recurring causal reasons behind Rejected Approaches;
* relationships among Open Questions;
* repeated constraints suggesting a broader concern;
* accumulated evidence that an architectural assumption deserves review.

Synthesis is manual-only and report-only. Even a high-confidence pattern means only that the pattern deserves review.

It does not mutate entity pages, ADRs, documents, source code, or the semantic log.

## Why It Is "Living"

The wiki is living because maintenance is integrated into normal architectural and implementation workflows rather than performed as an occasional documentation cleanup.

Knowledge can change when reality changes:

* an accepted implementation-pending decision becomes realized;
* a proposed direction changes or is rejected;
* an invariant gains stronger evidence or becomes contradicted;
* an Open Question is resolved;
* a rejected approach becomes eligible for reconsideration;
* an entity boundary emerges, splits, merges, changes scope, or disappears.

The wiki is therefore neither a snapshot nor an append-only pile of notes. It is maintained derived state whose claims remain tied to current authority and evidence.

## How It Is Self-Learning

"Self-learning" describes the wiki's controlled feedback loop. It does **not** mean autonomous architectural decision-making.

### Experience Becomes Durable Knowledge

Normal development can produce information worth preserving:

```text
implementation work
      ↓
new evidence / failed experiment / owner decision / unresolved concern
      ↓
qualification + provenance
      ↓
durable entity knowledge
```

`$wiki-sync` decides whether the information belongs in the durable knowledge model and preserves its provenance rather than strengthening it.

### Knowledge Is Continuously Challenged

Accumulation without correction would create increasingly confident stale memory.

`$wiki-lint` independently checks whether wiki claims still agree with eligible sources and current implementation evidence. It distinguishes genuine authority conflicts from ordinary drift instead of treating every mismatch the same way.

### Accumulated Knowledge Produces New Signals

As Rejected Approaches and Open Questions accumulate across entities, `$wiki-synthesize` can detect recurring causal patterns that were not explicit in any one source.

For example:

```text
Entity A: approach rejected because authority leaked into a local adapter
Entity B: approach rejected because transport metadata became decision authority
Entity C: open question about projection-layer governance ownership

                         ↓
                  $wiki-synthesize
                         ↓
Possible broader signal:
authority may repeatedly be leaking into boundary/projection layers
                         ↓
                    human review
```

The accumulated memory makes the pattern visible. It does not make the pattern true.

### Human Judgment Closes the Learning Loop

When synthesis or unresolved conflict indicates that a real architectural decision is needed, the result returns to the ordinary decision lifecycle.

```text
Living Entity Wiki
      ↓
pattern / conflict / question
      ↓
human judgment + normal architecture workflow
      ↓
ADR / current doc / implementation
      ↓
$wiki-sync
      ↓
richer, better-grounded memory
```

This is why the system is **self-learning but not self-authorizing**.

## Provenance and Evidence Strength

The wiki preserves not only claims, but where the claims came from.

Depending on the section, valid provenance may include:

```text
source: docs/...
source: owner-confirmed session decision, undocumented
source: session experiment, undocumented
source: owner-raised session question, undocumented
source: agent-observed during session, unresolved
```

These are intentionally not equivalent.

An agent-observed unresolved concern does not become an owner decision because it appears persuasive later. A session experiment does not become an accepted architectural decision. Synthesis may combine signals, but it may not strengthen their provenance.

Evidence conclusions are similarly bounded. Mechanically observable rules may be positively verified when evidence proves them. For intent-level or architectural claims, absence of contradiction supports:

> no contrary implementation evidence found

not an unsupported claim of verification.

## Source Conflicts and Uncertainty

When applicable authoritative sources materially disagree, the wiki surfaces:

```text
[source-conflict]
```

The system does not:

* choose whichever source appears newest;
* choose whichever source agrees with the implementation;
* rewrite the wiki to one side;
* rewrite authoritative sources to manufacture consistency;
* continue treating the disputed claim as settled.

The correct result can be **we do not currently know which authority should govern**.

That ability to preserve uncertainty is part of the wiki's trust model, not a failure of it.

## Entity Topology and Evolution

The entity model itself can evolve.

After bootstrap, `$wiki-sync` owns controlled topology operations:

* creation or promotion;
* rename;
* split;
* merge;
* removal;
* material scope change;
* Boundary Rationale change.

This means the wiki can learn not only facts about a fixed taxonomy, but also that the architectural taxonomy itself should change as the system evolves.

Topology remains governed. New entities must satisfy the boundary rules in `_schema.md`, new top-level Categories require explicit approval, and changes must keep the registry, entity pages, explicit links, and semantic log consistent.

`wiki/entities/` contains active entities only; retired entities are not kept as tombstones.

## Semantic History

Git and [`log.md`](log.md) serve different historical purposes.

> **Git is byte-level history. `wiki/log.md` is semantic history.**

Git tells us which lines changed. The semantic log records why the wiki's durable architectural state changed.

The log records changes such as:

* topology changes;
* material entity-content changes;
* `pending → present` transitions;
* Planned → Strict Invariant realization;
* Routing Anchor changes;
* Boundary Rationale changes.

It does not record clean lint runs, synthesis executions, or `$wiki-sync` invocations that produced no durable semantic change.

## Developer Workflow

Developers and agents normally interact with the wiki through the workflows that own its maintenance.

```text
architecture-sensitive implementation
    → read relevant entity knowledge
    → $wiki-sync before/after substantive change

ADR lifecycle
    → $to-adr-doc
    → $wiki-sync derived consequence

current/proposed document lifecycle
    → $to-doc / $classify-doc
    → $wiki-sync derived consequence

repository-wide trust check
    → $wiki-lint

occasional higher-order learning
    → human invokes $wiki-synthesize
```

Entity knowledge should constrain work when applicable, but developers should not treat an entity page as a substitute for checking the authoritative source behind a load-bearing claim.

## Directory Structure

```text
wiki/
├── README.md
├── index.md
├── _schema.md
├── _template.md
├── log.md
└── entities/
    ├── runtime-workflow-platform.md
    ├── governance-authority-decision-evidence.md
    └── ...
```

Responsibilities:

| Path | Responsibility |
| --- | --- |
| `README.md` | Conceptual architecture and developer orientation |
| `index.md` | Authoritative registry of active entities and routing metadata |
| `_schema.md` | Structural, authority, classification, boundary, and topology rules |
| `_template.md` | Entity knowledge sections and provenance format |
| `entities/` | Active derived architectural knowledge |
| `log.md` | Semantic history of substantive wiki mutations |

Procedures belong to the skills that perform them. Do not duplicate detailed skill procedures into this README or into `_schema.md`.

## Related Skills

| Skill | Role |
| --- | --- |
| `$wiki-sync` | Maintain durable derived knowledge around a specific change |
| `$wiki-lint` | Independently audit the whole wiki for trust, drift, conflicts, and structure |
| `$wiki-synthesize` | Detect higher-order patterns across accumulated knowledge for human review |
| `$to-adr-doc` | Own ADR creation and lifecycle |
| `$to-doc` | Create non-ADR documents |
| `$classify-doc` | Classify or reclassify existing non-ADR documents |

The wiki skills cooperate with those document and architecture workflows; they do not replace them.

## What the Wiki Is Not

The Living Entity Wiki is not:

* an architectural source of truth;
* a replacement for ADRs;
* a replacement for current architecture documents;
* a replacement for source-code or test inspection;
* a package or file inventory;
* a hand-authored dependency graph;
* a session transcript archive;
* a place to persist every implementation technique that worked;
* unrestricted agent memory;
* an autonomous architecture decision maker;
* a mechanism for turning AI inference directly into durable truth.

If information is easy and reliable to derive mechanically from the current repository, prefer deriving it when needed rather than persisting another copy that can drift.

## Design Principles

The Living Entity Wiki follows these principles:

1. **Knowledge compounds.** Preserve qualified architectural understanding so later work can build on it rather than rediscover it.
2. **Authority stays outside the wiki.** Derived memory never outranks its sources.
3. **Persist durable knowledge, not repository trivia.** Record meaning that survives ordinary implementation change.
4. **Preserve causality.** Record why invariants and rejections exist, not only their conclusions.
5. **Preserve provenance.** Do not strengthen evidence or authorship through repetition or synthesis.
6. **Represent uncertainty honestly.** Open Questions and `[source-conflict]` are valid states.
7. **Separate maintenance from audit.** The mechanism that updates knowledge is not the only mechanism that judges its health.
8. **Inference requires human review.** Cross-entity synthesis produces signals, not decisions.
9. **Let topology evolve deliberately.** Architectural boundaries may change, but not merely because directories move.
10. **Keep derived state lean.** Do not duplicate mechanically reconstructable structure.

## Anti-Patterns

Avoid:

```text
wiki says X
    ↓
therefore X is architectural authority
```

```text
code moved directories
    ↓
automatically create/rename/split an entity
```

```text
agent notices a plausible pattern
    ↓
persist it as a Strict Invariant
```

```text
new implementation disagrees with a cited ADR
    ↓
rewrite the entity to match the code
```

```text
ordinary refactor touched an entity's files
    ↓
write a wiki/log update even though durable knowledge did not change
```

```text
persist dependency graphs, inventories, or call chains
that repository tooling can reliably reconstruct
```

The system is useful precisely because it remembers selectively: durable architectural meaning is preserved, current implementation remains live evidence, inference remains distinguishable from authority, and accumulated knowledge is continuously open to challenge.