---
name: wiki-synthesize
description: Scans the full Living Entity Wiki for recurring or cumulative patterns across Rejected Approaches and Open Questions that no single entity states on its own. Produces a higher-inference report for human review and never mutates wiki entities, authoritative documents, or architectural decisions.
compatibility: product=codex product=claude-code network=none
disable-model-invocation: true
---

# Wiki Synthesize

`$wiki-synthesize` performs deliberate, higher-inference analysis across the entire Living Entity Wiki.

Its purpose is to surface patterns such as:

* the same underlying architectural problem recurring across entities;
* Open Questions that appear related across otherwise separate boundaries;
* repeated rejection causes that may indicate a platform-level constraint;
* evidence that an unresolved assumption deserves deliberate reconsideration.

It produces **signals for human judgment**, not architectural truth.

---

# Invocation

`$wiki-synthesize` is manual-only.

For Claude Code, retain:

```yaml id="gf84nq"
disable-model-invocation: true
```

For Codex, retain the existing manual invocation configuration in:

```text id="ugqdrz"
agents/openai.yaml
```

Do not remove either mechanism merely because the other product ignores it.

This skill must not be automatically invoked as part of:

* `$wiki-sync`;
* `$wiki-lint`;
* a routine code change;
* document creation;
* ADR lifecycle;
* ticket implementation.

Its value comes from deliberate whole-wiki synthesis, not frequent execution.

---

# When to Run

Run `$wiki-synthesize`:

* when Rejected Approaches or Open Questions have accumulated meaningfully;
* when the same architectural concern appears to be recurring in multiple places;
* before a broader architecture review;
* when considering whether several local problems share one underlying cause; or
* on demand when cross-entity synthesis would help decision-making.

Do not run it after every session.

Most individual changes do not create enough new durable knowledge for a meaningful new cross-entity pattern.

A rough operational heuristic is to consider running it after approximately 10–15 new or materially changed Rejected Approaches/Open Questions have accumulated, but this is not a required threshold.

---

# What This Is Not

`$wiki-synthesize` is not another lint pass.

`$wiki-lint` looks for relatively direct health failures such as:

* `[source-conflict]`;
* `[doc-drift]`;
* `[code-drift]`;
* stale or invalid citations;
* structural corruption;
* direct cross-entity contradictions.

Those checks may still require semantic judgment. They are not necessarily mechanically deterministic.

`$wiki-synthesize` operates at a higher inference level:

```text id="yv07l6"
individual valid observations
          ↓
possible recurring pattern
          ↓
hypothesis worth human review
```

The output is therefore less authoritative than a direct `$wiki-lint` finding.

A synthesis result is a **signal**, not proof.

---

# 1. Load the Full Active Wiki

Read:

```text id="e8f6p2"
wiki/index.md
wiki/entities/*
```

Load every active entity page in full.

This is intentionally different from `$wiki-sync`, which routes to only the entity knowledge relevant to one change.

`$wiki-synthesize` requires whole-wiki context because its purpose is to discover relationships that local routing would not expose.

Do not include retired entities because `wiki/entities/` contains active entities only.

---

# 2. Establish the Analysis Set

Primary synthesis inputs are:

* Rejected Approaches;
* Open Questions.

Strict Invariants may be used as contextual evidence when evaluating whether an Open Question or rejection pattern is reinforced or placed in tension by another entity.

Planned entries may be consulted when they materially clarify an unresolved pattern, but they are not themselves proof that the pattern is real because Planned content is explicitly future state.

Boundary Rationale and `wiki/index.md` may be used to understand entity scope.

Do not treat Routing Anchors, Categories, or implementation structure as synthesis evidence by themselves.

---

# 3. Scan for Recurring Rejection Themes

Look for two or more Rejected Approaches that appear to share a meaningful underlying cause, constraint, or assumption.

Examples:

```text id="egum35"
Entity A:
Direct provider SDK access rejected because it bypasses application boundaries.

Entity B:
Direct broker API access rejected because it bypasses application boundaries.

Possible synthesis:
A recurring platform-level rule may exist around external integration ownership.
```

The repeated wording does not need to be identical.

What matters is whether the **causal reason** appears materially shared.

Do not report a pattern merely because:

* two entries mention the same technology;
* two approaches both failed;
* the wording looks superficially similar; or
* the agent can imagine a broad abstraction connecting them.

A pattern requires meaningful shared reasoning.

---

# 4. Scan for Open-Question Reinforcement or Tension

Look for an Open Question on one entity that appears materially related to knowledge on another entity.

Possible relationships include:

### Reinforcement

Multiple entities independently raise the same unresolved concern.

### Partial answer

A Strict Invariant or Rejected Approach elsewhere may provide evidence relevant to the question.

### Tension

An Open Question appears to challenge an assumption embedded in another entity's current constraint.

Example:

```text id="2zlegy"
Entity A Open Question:
Can retry ownership move into individual providers?

Entity B Rejected Approach:
Provider-owned retry policy was rejected because cross-provider behavior became inconsistent.

Possible synthesis:
The existing rejection may materially constrain the unresolved question on Entity A.
```

Do not mark the Open Question resolved.

The relationship is evidence for review, not an automatic answer.

---

# 5. Scan for Invariant Tension

Look for a recurring pattern in Rejected Approaches or Open Questions that suggests a Strict Invariant may depend on an assumption worth reconsidering.

This is the most inferential analysis performed by `$wiki-synthesize`.

Frame it cautiously.

Valid framing:

```text id="kr1k17"
Several entries suggest that the assumption behind invariant X may deserve review.
```

Invalid framing:

```text id="x7kgfr"
Invariant X is obsolete.
```

`$wiki-synthesize` never invalidates or rewrites a Strict Invariant.

If an invariant is directly contradicted by authoritative sources or implementation evidence, that belongs to `$wiki-lint`, not synthesis.

---

# 6. Require Multiple Supporting Signals

A synthesis pattern must have at least **two distinct supporting entries**.

A single interesting entry is not a cross-entity pattern.

Prefer evidence spanning multiple entities when possible.

Multiple entries on the same entity may still establish a recurring theme when the causal pattern genuinely repeats, but describe it as an entity-local recurrence rather than falsely labeling it cross-entity.

Do not manufacture a pattern merely to produce output.

---

# 7. Preserve Provenance

Every reported pattern must identify its supporting entries.

For each supporting item include:

* Entity ID or name;
* section;
* concise entry text;
* the entry's existing provenance.

Example:

```text id="t69sga"
Supporting entries:
- persistence › Rejected Approaches:
  "Qdrant as canonical durability..." 
  (source: session experiment, undocumented)

- retrieval › Open Questions:
  "Should vector state ever become authoritative?"
  (source: owner-raised session question, undocumented)
```

Do not replace an entry's provenance with a stronger characterization.

For example:

```text id="xhxufc"
source: agent-observed during session, unresolved
```

must not become:

```text id="3wjf8g"
owner decision
```

merely because the synthesis considers the signal persuasive.

---

# 8. Respect Source Health

`$wiki-synthesize` assumes the active wiki is broadly usable, but synthesis must not amplify an obvious known health failure into a new architectural theory.

If a supporting entry visibly contains:

* a broken citation;
* an invalid authority;
* a marked unresolved `[source-conflict]`; or
* another clear condition that makes its reliability questionable,

note that limitation in the report.

Do not silently treat questionable input as settled evidence.

If source health itself needs systematic evaluation, recommend `$wiki-lint`.

Do not turn `$wiki-synthesize` into a duplicate lint implementation.

---

# 9. Assign Confidence Conservatively

Every reported pattern receives:

```text id="cf54gz"
Confidence: low | medium | high
```

Confidence describes **strength of the synthesis evidence**, not architectural authority.

### Low

Use when:

* the connection is plausible but indirect;
* supporting entries have materially different causal contexts;
* an important assumption remains speculative.

### Medium

Use when:

* multiple entries share a clear causal theme;
* the relationship is meaningful but still requires interpretation.

### High

Use sparingly when:

* several independent entries strongly reinforce the same underlying pattern;
* causal reasoning aligns closely across those entries;
* little interpretive stretching is required.

Even:

```text id="cxpwoe"
Confidence: high
```

still means:

> high confidence that this pattern deserves review.

It does **not** mean:

> architectural decision established.

---

# 10. Suggest the Smallest Appropriate Next Step

For each pattern, suggest what should happen **next**, without performing it.

Possible next steps include:

* review a specific Open Question;
* reconsider a condition-dependent Rejected Approach;
* inspect an existing Strict Invariant;
* run `$wiki-lint` where a possible direct conflict emerged;
* consider creating an ADR through `$to-adr-doc` if a real architectural decision is required;
* consider a topology review if several entities may actually represent one shared boundary.

Do not automatically:

* create an ADR;
* modify an entity;
* create a new entity;
* change an invariant;
* resolve an Open Question;
* remove a Rejected Approach.

---

# Report Format

Produce:

```md id="7yc0eo"
## Synthesis Report — YYYY-MM-DD

### Pattern: [concise description]

**Confidence:** low | medium | high

**Interpretation:**  
[Why these entries may reflect the same underlying cause or concern.]

**Supporting entries:**
- [entity] › [section]: [concise entry]
  (source: ...)
- [entity] › [section]: [concise entry]
  (source: ...)

**Suggested next step:**  
[Smallest appropriate human-reviewed follow-up.]
```

When important, add:

```md id="3c8wa1"
**Caveat:**  
[Why the evidence may be incomplete or why a supporting entry's authority should be checked.]
```

---

# Clean Result

If no meaningful pattern is found, report plainly:

```text id="nbe1df"
Synthesis: no meaningful recurring patterns found.
```

Do not lower the threshold merely to avoid returning an empty result.

A clean synthesis run is valid.

---

# Resolution Rules

`$wiki-synthesize` is **report-only**.

It never writes to:

* `wiki/entities/`;
* `wiki/index.md`;
* `wiki/log.md`;
* `docs/`;
* ADRs;
* source code.

It never creates a commit.

This applies even when a pattern appears obvious.

The reason is intentional:

`$wiki-synthesize` performs inference across individually valid observations. Automatically persisting that inference would allow an agent-generated hypothesis to become durable architectural "memory" before human judgment established it.

If the owner confirms a synthesis finding, act through the normal lifecycle afterward.

Examples:

```text id="8pg1rp"
confirmed architectural decision
→ `$to-adr-doc`

confirmed entity change
→ `$wiki-sync`

direct conflict discovered
→ `$wiki-lint` / source resolution

confirmed rejected direction
→ `$wiki-sync` with qualifying provenance

resolved Open Question
→ `$wiki-sync`
```

The synthesis report itself is never an authoritative source citation.

---

# Logging

Do not add a `wiki/log.md` entry merely because `$wiki-synthesize` ran.

`wiki/log.md` records substantive Living Entity Wiki mutations, not tool execution history.

Because `$wiki-synthesize` performs no wiki mutation, it normally produces:

```text id="fw6b8p"
report only
no log entry
no commit
```

If a human later acts on a synthesis finding and that action changes the wiki, the owning workflow records the resulting semantic mutation.

---

# Relationship to Other Skills

Use:

* `$wiki-sync` for per-change entity maintenance;
* `$wiki-lint` for whole-wiki health, conflict, citation, and drift checking;
* `$to-adr-doc` when synthesis leads to a real architectural decision;
* `$classify-doc` when an existing non-ADR document needs reclassification;
* `$to-doc` when synthesis leads to creation of a new non-ADR document.

`$wiki-synthesize` remains separate because its purpose is not maintenance or validation.

Its job is to ask:

> What meaningful pattern may be emerging across the knowledge we have already accumulated?

---

# Out of Scope

`$wiki-synthesize` does not:

* detect or repair ordinary `[code-drift]`;
* detect or repair ordinary `[doc-drift]`;
* validate citation eligibility systematically;
* resolve `[source-conflict]`;
* perform structural wiki linting;
* maintain entity pages;
* decide entity topology;
* establish architectural authority;
* create documents or ADRs;
* convert inference into durable wiki knowledge;
* record its own execution in `wiki/log.md`.

It produces hypotheses worth reviewing and nothing more.
