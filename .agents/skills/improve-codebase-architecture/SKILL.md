---
name: improve-codebase-architecture
description: Surface architectural friction and propose module-deepening opportunities that improve locality, leverage, testability, and AI navigability. Uses the project's design vocabulary, domain model, authoritative architecture sources, code graph tooling, and Living Entity Wiki knowledge without modifying production code during the review phase.
compatibility: product=codex product=claude-code system=git network=none
disable-model-invocation: true
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones.

The objective is to improve:

* locality;
* leverage;
* testability;
* conceptual compression;
* AI navigability.

This is initially an **architecture review and decision workflow**, not an implementation workflow.

Do not modify production code while discovering or presenting candidates.

---

# Design Vocabulary

Run `$codebase-design` for the architecture vocabulary and principles used by this skill.

Use its terms consistently:

* **module**
* **interface**
* **depth**
* **seam**
* **adapter**
* **leverage**
* **locality**

Apply its principles, including:

* the deletion test;
* "the interface is the test surface";
* "one adapter = hypothetical seam, two = real".

Within architecture recommendations, prefer that vocabulary over loose substitutes such as:

```text
component
service
API
boundary
```

when the `$codebase-design` term is the concept actually being discussed.

Do not mechanically rename real project identifiers merely to satisfy the vocabulary.

---

# Domain Vocabulary

Use canonical domain terminology from `CONTEXT.md`.

If `CONTEXT-MAP.md` exists, consult the relevant bounded-context glossary according to `$domain-modeling`.

Architecture vocabulary and domain vocabulary serve different purposes:

```text
CONTEXT.md
→ names domain concepts

$codebase-design
→ names architectural qualities and structures
```

Do not invent technical jargon where an established domain term already exists.

---

# Architecture Authority

Before proposing architectural changes, distinguish active authority from historical or proposed material.

Use:

* accepted ADRs for active architectural decisions;
* `docs/current/` for authored current architecture;
* verified implementation evidence for current implementation reality;
* entity pages as derived architectural knowledge;
* `docs/proposed/` and proposed ADRs as future direction;
* rejected/deprecated/superseded ADRs as historical context.

Do not treat every ADR as an active constraint merely because it exists.

If applicable authoritative sources materially disagree, surface:

```text
[source-conflict]
```

Do not build a recommendation on top of one side of a known source conflict as though it were settled.

---

# Process

## 1. Scope Before Scanning

Apply YAGNI to architecture review.

Deepening a module is worthwhile only when the resulting reduction in recurring complexity is likely to matter.

Choose **where to inspect before deeply scanning the repository**.

### User-specified scope

If the user names:

* a module;
* an architectural concern;
* a subsystem;
* a recurring pain point;
* a concrete area of the repository;

use that scope.

Do not perform repository-wide architecture archaeology first.

### No user-specified scope

Use recent Git history to identify likely architectural hot spots.

Inspect enough history to find areas that recur meaningfully.

For example:

```bash
git log --oneline --name-only
```

or a more targeted equivalent.

Favor areas that repeatedly change because module depth pays off when future changes become cheaper.

Do not assume high churn automatically means bad architecture.

Use churn only to prioritize investigation.

If no clear hot spot appears, widen the scope deliberately.

---

# 2. Load Relevant Architectural Context

Before deeply exploring the chosen area, inspect the smallest relevant set of architecture knowledge.

Read:

* relevant canonical vocabulary from `CONTEXT.md`;
* applicable accepted ADRs;
* relevant `docs/current/`;
* relevant proposed architecture where it may affect recommendations.

If the Living Entity Wiki exists:

1. start from `wiki/index.md`;
2. route the area through its Routing Anchors;
3. read the relevant entity page or pages.

Consult at minimum the relevant:

* Strict Invariants;
* Rejected Approaches;
* Open Questions;
* Planned content.

This is a **read-only architecture review consult**.

Do not invoke `$wiki-sync` merely because architecture candidates are being explored.

No source code has been changed yet.

---

# 3. Respect Existing Decisions

Do not casually re-litigate active accepted decisions.

If a potential refactor contradicts an accepted ADR, normally exclude it.

Surface it only when observed architectural friction provides a concrete reason that the decision itself may deserve reconsideration.

If so, mark it explicitly:

```text
Conflicts with ADR-00XX.

Reason reconsideration may now be warranted:
<concrete changed circumstance or newly observed cost>
```

Do not portray the conflicting candidate as already valid.

---

# 4. Respect Rejected Approaches

If an entity's Rejected Approaches section contains a candidate that matches or closely resembles something currently being considered, inspect:

* the rejection reason;
* its provenance;
* any `Reconsider when:` condition.

### Rejection still applies

Do not recommend the candidate.

### Reconsideration condition appears satisfied

The candidate may be surfaced as something worth reconsidering.

State:

* which rejected approach it resembles;
* its source;
* which changed circumstance appears to satisfy the reconsideration condition.

### No explicit reconsideration condition

Surface the candidate only if concrete circumstances have materially changed since the rejection.

Do not infer that elapsed time alone invalidates a rejection.

### Unclear

Treat it as requiring owner judgment.

Do not silently override accumulated architectural memory.

---

# 5. Explore the Implementation

Use the project's repository-analysis tool belt.

Choose the smallest combination suited to the architectural question:

* `$repowise`
* `$codegraph`
* `$codebase-memory-mcp`
* `$graphify`

Do not depend on a product-specific `Agent` or `subagent_type=Explore` mechanism.

The exploration workflow must work in Codex without assuming Claude-specific orchestration primitives.

Use multiple analysis skills only when they expose meaningfully different evidence.

---

## Explore Organically

Look for architectural friction rather than applying a rigid smell checklist.

Useful questions include:

### Locality

Where does understanding or changing one domain concept require jumping through many modules?

Where is the logic required to understand one behavior scattered far from the interface that exposes it?

### Depth

Where is a module shallow?

Ask:

> Does the interface hide meaningful complexity, or merely redistribute it?

### Testing

Where have functions been extracted solely to make implementation details independently testable?

Do the important failures actually occur in:

* orchestration;
* sequencing;
* state interaction;
* dependency composition;

rather than inside the isolated function?

### Seams

Where are supposedly separate modules tightly coupled through internal details?

Where does one module need knowledge that should remain hidden behind another's interface?

### Adapters

Where does a hypothetical seam exist with only one adapter?

Where do two or more real adapters demonstrate that the seam has actual leverage?

### Change concentration

Where do repeated changes touch many files because one conceptual operation is split across shallow modules?

---

# 6. Apply the Deletion Test

For every serious deepening candidate ask:

> If this module disappeared and its behavior moved behind a deeper neighboring module, would complexity become more concentrated and easier to reason about, or would the same complexity merely move somewhere else?

A useful deepening candidate should improve:

* locality;
* interface simplicity;
* conceptual compression;
* leverage.

Do not recommend consolidation merely because fewer files look cleaner.

File-count reduction is not architectural depth.

---

# 7. Validate Candidate Scope

Before including a candidate in the report, verify that it represents architectural leverage rather than ordinary cleanup.

Exclude proposals whose main benefit is:

* naming cleanup;
* file-count reduction;
* aesthetic folder organization;
* speculative future extensibility;
* reducing line count;
* creating an interface for a single hypothetical implementation;
* making isolated unit tests easier while making the real behavior harder to understand.

Prefer candidates where repeated complexity can genuinely disappear behind a simpler interface.

---

# 8. Do Not Design Interfaces Yet

During initial candidate discovery:

* identify the shallow module;
* explain the architectural friction;
* explain the deepening opportunity;
* show the likely direction.

Do **not** finalize the new interface.

Interface design occurs only after the user selects a candidate.

This prevents speculative design effort on candidates the owner may reject.

---

# 9. Produce the Architecture Review Report

Write a fresh HTML report outside the repository.

Resolve a temporary directory from the operating system.

Linux/macOS:

```bash
TMP_ROOT="${TMPDIR:-/tmp}"
```

Use an equivalent OS temp directory on other supported systems.

Write:

```text
<tmpdir>/architecture-review-<timestamp>.html
```

Do not create architecture-review artifacts inside the repository.

---

## Report Portability

The report should be usable as a single local HTML artifact.

Prefer:

* embedded CSS;
* inline SVG;
* HTML/CSS diagrams.

Do not require network access merely to render core report content.

If `HTML-REPORT.md` defines additional established project report patterns, follow them where they do not conflict with this requirement.

Use Mermaid only when the repository already provides a local/reliable way to render it without making the report's basic usefulness depend on an external CDN.

The architecture analysis matters more than the frontend framework used to display it.

---

# 10. Report Structure

For each candidate, render a visual card containing:

### Module

Use the relevant domain name plus the `$codebase-design` vocabulary.

### Files

Identify the principal implementation files involved.

Keep this concise.

Do not turn the report into a repository inventory.

### Problem

Explain why the current module is shallow or why locality/leverage is poor.

### Solution Direction

Describe the deepening opportunity in plain language.

Do not finalize its interface yet.

### Benefits

Explain specifically how the change may improve:

* locality;
* leverage;
* interface simplicity;
* testability;
* AI navigability.

### Before / After

Provide a visual comparison showing:

```text
before
→ where complexity leaks today

after
→ where complexity would be concentrated
```

Prefer a diagram over paragraphs when structure is the point.

### Evidence

Include the concrete evidence behind the candidate:

* dependency structure;
* recurring changes;
* call-flow complexity;
* testing friction;
* repeated knowledge leakage.

Name the repository-analysis skill when its evidence materially supports the conclusion.

### Architecture Constraints

Where applicable include:

* accepted ADR constraints;
* relevant Strict Invariants;
* Planned work already addressing the problem;
* Rejected Approach history;
* `[source-conflict]`.

### Recommendation Strength

Use exactly:

```text
Strong
Worth exploring
Speculative
```

Strength represents the quality of the architectural evidence.

Do not manufacture numerical scoring precision.

---

# 11. Top Recommendation

End the report with:

```text
Top recommendation
```

Choose the candidate with the clearest combination of:

* recurring friction;
* locality improvement;
* leverage;
* testability improvement;
* evidence that the module is genuinely shallow.

Explain why it is the best first candidate to **explore**, not why it must necessarily be implemented.

---

# 12. Open the Report

Open the generated report for the user using the appropriate local mechanism.

Linux:

```bash
xdg-open "<path>"
```

macOS:

```bash
open "<path>"
```

Windows:

```text
start <path>
```

Report the absolute path.

Then ask:

> Which of these would you like to explore?

Do not begin designing the candidate's interface until the user selects one.

---

# 13. Grilling Loop

Once the user selects a candidate, run `$grilling`.

Use it to explore:

* actual constraints;
* dependencies;
* what complexity belongs behind the deeper module;
* what the seam should conceal;
* what behavior must remain visible;
* what tests should survive;
* what tests exist only because implementation details currently leak.

Do not begin implementation merely because the candidate survived initial review.

The output of this stage is an architectural decision or design direction.

---

# 14. Use `$domain-modeling` Only When Domain Semantics Change

Do not automatically invoke `$domain-modeling` for every architectural discussion.

Use it when the grilling process actually:

* introduces a new domain concept;
* changes canonical meaning;
* exposes overloaded terminology;
* changes relationships between domain concepts.

Examples:

### New domain concept

Use `$domain-modeling` and add the resolved term to `CONTEXT.md`.

### Fuzzy term sharpened

Use `$domain-modeling` and update the canonical definition immediately.

### Pure architecture terminology

Do not modify `CONTEXT.md` merely because a new module name was discussed.

A module name is not automatically a domain concept.

---

# 15. Record Rejected Candidates Correctly

If the owner rejects the candidate, determine whether the reasoning is durable.

---

## Ephemeral rejection

Examples:

```text
not worth doing right now
too much work for this release
not a current priority
```

Do not create durable architecture memory merely to preserve scheduling preference.

---

## ADR-worthy rejection

If the rejection satisfies `$to-adr-doc`'s ADR criteria, offer to record the decision through `$to-adr-doc`.

Do not duplicate the ADR criteria here.

If accepted, use `$to-adr-doc`.

---

## Durable non-ADR rejection

If:

* the owner explicitly rejects the architectural approach;
* the reason is load-bearing enough that a future architecture review would otherwise likely re-propose it;
* the decision does not warrant an ADR;
* the Living Entity Wiki exists;

invoke `$wiki-sync`.

Record the Rejected Approach using provenance:

```text
source: owner-confirmed session decision, undocumented
```

Do not use:

```text
source: session decision, undocumented
```

because that fails to distinguish an owner decision from an agent inference.

If the rejection is condition-dependent, add:

```text
Reconsider when:
```

only when the owner actually establishes the condition.

Do not invent reconsideration criteria.

---

## Failed experiment

If a real prototype or experiment was attempted during the session and failed for a concrete architectural reason, `$wiki-sync` may preserve that Rejected Approach using:

```text
source: session experiment, undocumented
```

Do not turn an untested agent opinion into a Rejected Approach.

---

# 16. Design Interfaces Only After Candidate Selection

If the user wants to explore alternate interfaces for the selected deepened module, run `$codebase-design`.

Use its design-it-twice approach where available.

Compare materially different interfaces, not cosmetic variants.

The goal is to discover which interface creates the deepest useful module.

---

# 17. Persist Architectural Outcomes Through Their Owners

If the grilling/design process produces a durable architectural outcome, route it according to what actually happened.

---

## Architectural decision

Use `$to-adr-doc` when its ADR criteria are satisfied.

---

## Durable proposed architecture

If the design is worth preserving but has not become an accepted decision, use `$to-doc` for the appropriate proposed architecture document.

Do not store future architecture in `CONTEXT.md`.

---

## Durable current architecture description

If the review documents already-existing current architecture that deserves authoritative prose but does not warrant an ADR, use `$to-doc`.

---

## Existing document needs classification change

Use `$classify-doc`.

---

## Living Entity Wiki consequence

Allow the normal `$wiki-sync` trigger from `$to-adr-doc`, `$to-doc`, `$classify-doc`, or a later implementation workflow to maintain entity knowledge.

Do not manually edit entity pages from `$improve-codebase-architecture`.

---

# 18. Entity Topology

Architecture review may reveal that the current entity decomposition deserves reconsideration.

Examples:

* two entities actually behave as one durable architectural unit;
* one entity contains an independently useful sub-boundary;
* an entity no longer exists;
* a boundary rationale is no longer accurate.

Do not change topology during candidate discovery.

Surface the evidence.

If the owner approves an actual topology change, apply the lifecycle through `$wiki-sync` according to `wiki/_schema.md`.

Do not derive topology mechanically from:

* directory structure;
* one code graph cluster;
* a proposed deeper module.

---

# 19. Implementation Handoff

This skill does not implement the selected architecture refactor.

Once a direction is approved for implementation, hand it to the repository's normal implementation workflow.

That implementation must independently satisfy:

* `$wiki-sync` pre-change auditing;
* `$coding-standards`;
* `$tdd` where appropriate;
* `$verify-code`;
* database migration workflow where applicable;
* post-change `$wiki-sync`.

Do not treat the architecture review's read-only entity consultation as satisfying a later implementation-time `$wiki-sync` pre-change audit.

Architecture may have changed between review and implementation.

---

# 20. Final Handoff

Report:

* candidates examined;
* selected candidate, if any;
* evidence supporting it;
* applicable accepted ADRs;
* relevant Strict Invariants;
* relevant Rejected Approaches and reconsideration status;
* any `[source-conflict]`;
* architectural decision reached;
* domain vocabulary changed through `$domain-modeling`, if any;
* ADR created through `$to-adr-doc`, if any;
* architecture document created through `$to-doc`, if any;
* Rejected Approach recorded through `$wiki-sync`, if any;
* entity-topology issue surfaced or approved, if any;
* implementation status.

Clearly distinguish:

```text
reviewed
approved for design
architecturally decided
documented
implemented
```

Do not imply that a reviewed or accepted architecture candidate has already been implemented.

---

# Out of Scope

`$improve-codebase-architecture` does not:

* modify production code during candidate discovery;
* use a Claude-specific subagent mechanism as a requirement;
* treat every ADR as current authority;
* re-litigate accepted ADRs without changed evidence;
* ignore applicable Rejected Approaches;
* infer that a `Reconsider when:` condition has been satisfied without evidence;
* write entity pages directly;
* modify entity topology without owner-approved `$wiki-sync` lifecycle;
* use `CONTEXT.md` for architecture;
* create speculative interfaces before candidate selection;
* equate fewer files with deeper modules;
* treat passing tests as proof of architectural correctness;
* treat a wiki entity as equivalent to a module or bounded context.

Its job is to find places where **more complexity can be hidden behind less interface**, and to help the owner decide whether that deepening is architecturally worthwhile.
