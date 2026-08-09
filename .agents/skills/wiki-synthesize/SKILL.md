---
name: wiki-synthesize
description: Scan the full Living Entity Wiki for recurring patterns across Rejected Approaches and Open Questions that no single entity states alone. Produces higher-inference hypotheses for human review and never mutates authoritative or wiki state.
compatibility: product=codex product=claude-code network=none
disable-model-invocation: true
---

# Wiki Synthesize

`$wiki-synthesize` performs deliberate, higher-inference analysis across the full Living Entity Wiki.

It looks for:

* recurring causes behind Rejected Approaches;
* related Open Questions across entities;
* repeated constraints that may indicate a broader architectural concern;
* accumulated evidence that an assumption deserves review.

Its output is a **signal for human judgment**, never architectural authority.

## Invocation

`$wiki-synthesize` is manual-only.

Retain:

* `disable-model-invocation: true` for Claude Code;
* the existing `agents/openai.yaml` manual invocation configuration for Codex.

Do not invoke it automatically from `$wiki-sync`, `$wiki-lint`, routine implementation, document creation, or ADR lifecycle.

Run it when enough durable wiki knowledge has accumulated that cross-entity synthesis may reveal something useful.

Do not run it after every session.

## 1. Load the Active Wiki

Read:

```text
wiki/index.md
wiki/entities/*
```

Load every active entity page.

Primary synthesis inputs are:

* Rejected Approaches;
* Open Questions.

Use Strict Invariants as contextual evidence where relevant.

Use Planned and Boundary Rationale only when they materially clarify the pattern.

Do not treat Routing Anchors, Categories, or implementation structure as synthesis evidence by themselves.

## 2. Find Meaningful Patterns

A pattern requires at least **two distinct supporting entries**.

Prefer cross-entity evidence, but repeated causal evidence within one entity may be reported as an entity-local recurrence.

Do not report patterns based only on:

* similar wording;
* shared technologies;
* two unrelated failures;
* an abstraction the agent can merely imagine.

The **causal reasoning** must meaningfully overlap.

### Recurring Rejections

Look for Rejected Approaches that appear to fail for the same underlying architectural reason.

### Open-Question Relationships

Look for:

* **reinforcement** — multiple entries independently raise the same concern;
* **partial answer** — another entity contains relevant evidence;
* **tension** — an unresolved question challenges an assumption elsewhere.

Do not mark an Open Question resolved merely because another entity provides relevant evidence.

### Invariant Tension

If accumulated rejections/questions suggest that an assumption behind a Strict Invariant deserves review, frame it cautiously.

Valid:

> Several entries suggest that the assumption behind invariant X may deserve review.

Invalid:

> Invariant X is obsolete.

Direct contradictions belong to `$wiki-lint`, not synthesis.

## 3. Preserve Provenance

Every pattern must identify its supporting entries with:

* Entity ID/name;
* section;
* concise entry;
* existing provenance.

Do not strengthen provenance during synthesis.

For example:

```text
source: agent-observed during session, unresolved
```

must never become an owner decision merely because the pattern looks persuasive.

If a supporting entry has an obvious health problem such as a broken citation or unresolved `[source-conflict]`, note the limitation.

Recommend `$wiki-lint` when systematic source-health evaluation is required rather than duplicating lint behavior here.

## 4. Assign Confidence

Use:

```text
Confidence: low | medium | high
```

Confidence means **strength of synthesis evidence**, not architectural authority.

* **Low** — plausible but indirect or assumption-heavy.
* **Medium** — multiple entries share a clear causal theme.
* **High** — several independent entries strongly reinforce the same pattern with little interpretive stretching.

Even `high` means:

> high confidence that the pattern deserves review.

It does not mean a decision has been established.

## 5. Suggest the Smallest Next Step

For each pattern, recommend only the smallest useful follow-up.

Examples:

* review an Open Question;
* reconsider a condition-dependent rejection;
* inspect a Strict Invariant;
* run `$wiki-lint` if a direct conflict may exist;
* consider `$to-adr-doc` if a real architectural decision is needed;
* consider a topology review if several entities may represent one boundary.

Do not perform the action automatically.

## Report Format

Use:

```md
## Synthesis Report — YYYY-MM-DD

### Pattern: [concise description]

**Confidence:** low | medium | high

**Interpretation:**
[Why the entries may share an underlying cause or concern.]

**Supporting entries:**
- [entity] › [section]: [concise entry]
  (source: ...)
- [entity] › [section]: [concise entry]
  (source: ...)

**Suggested next step:**
[Smallest appropriate human-reviewed follow-up.]
```

Add a **Caveat** when evidence quality or source health materially limits the conclusion.

If no meaningful pattern exists, report:

```text
Synthesis: no meaningful recurring patterns found.
```

Do not lower the evidence threshold merely to produce output.

## Report-Only Rule

`$wiki-synthesize` never writes to:

* `wiki/entities/`;
* `wiki/index.md`;
* `wiki/log.md`;
* `docs/`;
* ADRs;
* source code.

It never creates a commit.

The synthesis report itself is not an authoritative source.

If the owner confirms a finding, use the appropriate normal lifecycle afterward:

* architectural decision → `$to-adr-doc`;
* entity/wiki change → `$wiki-sync`;
* direct conflict → `$wiki-lint` / source resolution;
* new non-ADR document → `$to-doc`;
* existing document reclassification → `$classify-doc`.

Do not log the synthesis run itself.

## Out of Scope

`$wiki-synthesize` does not:

* perform ordinary drift or citation auditing;
* resolve `[source-conflict]`;
* maintain entity pages;
* decide topology;
* establish architectural authority;
* create documents or ADRs;
* convert inference directly into durable wiki knowledge.

Its job is to ask:

> What meaningful pattern may be emerging across the knowledge already accumulated?
