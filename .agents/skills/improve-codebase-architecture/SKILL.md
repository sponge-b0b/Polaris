---

name: improve-codebase-architecture
description: Surface architectural friction and propose module-deepening opportunities that improve locality, leverage, testability, and AI navigability.
compatibility: product=codex product=claude-code system=git network=none
disable-model-invocation: true
------------------------------

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

This skill is informed by the project's domain model and shared design vocabulary:

* Run `$codebase-design` for the architecture vocabulary (**module**, **interface**, **depth**, **seam**, **adapter**, **leverage**, **locality**) and its principles, including the deletion test, "the interface is the test surface," and "one adapter = hypothetical seam, two = real." Use those terms consistently in suggestions.
* Use canonical domain language from `CONTEXT.md`.
* Treat accepted ADRs and applicable current architecture as constraints, not suggestions.
* If the Living Entity Wiki exists, consult relevant Strict Invariants, Rejected Approaches, Open Questions, and Planned entries before proposing changes.
* If authoritative sources materially disagree, surface `[source-conflict]` rather than designing around one side.

## 1. Explore

**Scope before scanning — YAGNI.**

Deepening pays off when it makes recurring future changes easier, so prioritize areas that actually matter.

* If the user names a module, subsystem, or pain point, use that scope.
* Otherwise inspect enough Git history to identify recurring hot spots. If changes are scattered, widen the search deliberately.

Read the relevant `CONTEXT.md`, accepted ADRs, and current architecture docs first.

If the Living Entity Wiki exists, use `wiki/index.md` to locate the relevant entity page(s). This is a read-only consultation, not a `$wiki-sync` invocation.

Then explore using the project's repository-analysis tools such as `$repowise`, `$codegraph`, `$codebase-memory-mcp`, or `$graphify`.

Look organically for friction:

* Where does understanding one concept require bouncing between many modules?
* Where are modules **shallow** — interface nearly as complex as implementation?
* Where were functions extracted mainly for testability while the real bugs live in their composition?
* Where is **locality** poor?
* Where do supposedly separate modules leak knowledge across their seams?
* Which behavior is hard to test through its real interface?

Apply the **deletion test** to serious candidates: would deleting the shallow module concentrate complexity behind a deeper interface, or merely move the same complexity elsewhere?

Do not recommend refactors merely to reduce file count or create speculative abstractions.

### Existing decisions

Do not casually re-litigate accepted ADRs.

If a candidate conflicts with one, normally omit it. Surface it only when concrete changed circumstances make reconsideration genuinely warranted, and mark the conflict explicitly.

Apply the same rule to Rejected Approaches:

* if the rejection still applies, do not recommend it;
* if its `Reconsider when:` condition appears satisfied, it may be surfaced for reconsideration;
* without an explicit condition, require concrete changed circumstances rather than elapsed time alone.

Do not override accumulated architectural memory silently.

## 2. Present Candidates as an HTML Report

Write a self-contained HTML report to the OS temporary directory:

```text
<tmpdir>/architecture-review-<timestamp>.html
```

Nothing from the review should land in the repository.

Open the report for the user with the platform's normal local-file opener and report its absolute path.

Follow `HTML-REPORT.md` for established report patterns.

Prefer self-contained HTML/CSS/SVG. Do not make the report's core usefulness depend on network-only assets.

For each candidate include:

* **Files** — principal modules involved.
* **Problem** — why the architecture creates friction.
* **Solution** — the deepening direction, without designing the final interface yet.
* **Benefits** — locality, leverage, testability, and AI navigability.
* **Before / After** — visual comparison.
* **Evidence** — concrete dependency, change, call-flow, or testing evidence.
* **Constraints** — relevant ADRs, invariants, rejected approaches, Planned work, or `[source-conflict]`.
* **Recommendation strength** — `Strong`, `Worth exploring`, or `Speculative`.

End with a **Top recommendation** and explain which candidate is most worth exploring first.

Use `CONTEXT.md` terminology for the domain and `$codebase-design` terminology for architecture.

Do **not** design interfaces yet.

Ask:

> Which of these would you like to explore?

## 3. Grilling Loop

Once the user selects a candidate, run `$grilling`.

Explore:

* constraints and dependencies;
* what complexity belongs behind the deeper module;
* what should remain visible through the seam;
* what tests should survive;
* whether alternative interfaces should be compared.

Use `$codebase-design` when exploring alternative interfaces.

Use `$domain-modeling` only when the discussion actually changes or sharpens domain meaning. A new module name alone is not automatically a new domain concept.

### Rejected candidate

If the user rejects the candidate:

* ephemeral reasons such as "not now" or "not worth it this release" are not durable architecture knowledge;
* if the rejection warrants an ADR, use `$to-adr-doc`;
* otherwise, if the rejection is load-bearing and the Living Entity Wiki exists, use `$wiki-sync` to record a Rejected Approach with:

`source: owner-confirmed session decision, undocumented`

Add `Reconsider when:` only if the owner actually establishes such a condition.

If a real experiment failed for a concrete architectural reason, use:

`source: session experiment, undocumented`

Do not turn unsupported agent judgment into a Rejected Approach.

### Accepted direction

If the review produces a durable architectural outcome:

* use `$to-adr-doc` for an ADR-worthy decision;
* use `$to-doc` for durable current or proposed architecture that does not warrant an ADR;
* use `$classify-doc` if an existing document needs reclassification.

Do not edit entity pages directly. Normal `$wiki-sync` triggers own derived wiki updates.

## 4. Entity Topology

A review may reveal that an entity should be split, merged, renamed, added, removed, or have its Boundary Rationale changed.

Do not perform topology changes during candidate discovery.

If the owner approves such a change, use `$wiki-sync` according to `wiki/_schema.md`.

A module, package, bounded context, or graph cluster is not automatically a wiki entity.

## 5. Implementation Handoff

This skill reviews and shapes architecture; it does not implement the selected refactor.

Production implementation must enter the normal implementation workflow and perform its own `$wiki-sync` pre-change audit.

The read-only wiki consultation performed during architecture review does not satisfy that later implementation check.

## Handoff

Report:

* candidates considered;
* selected candidate, if any;
* supporting evidence;
* relevant ADRs/invariants/rejections;
* any `[source-conflict]`;
* architectural decision reached;
* any `$domain-modeling`, `$to-adr-doc`, `$to-doc`, `$classify-doc`, or `$wiki-sync` outcome;
* whether implementation has actually occurred.

Distinguish clearly between **reviewed**, **architecturally decided**, **documented**, and **implemented**.
