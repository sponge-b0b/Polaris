---
name: review-architecture
description: Audit an aggregate implementation diff or proposed remediation obligation against resolved architecture and current architectural authorities. Report architecture drift, unresolved architectural changes, and boundary violations without modifying code, docs, ADRs, or the Living Entity Wiki.
compatibility: product=codex product=claude-code system=git system=gh network=required
---

# Review Architecture

Audit whether an implemented change or proposed remediation obligation preserves or correctly realizes resolved architecture.

This is a **read-only review**. It reports architecture findings; it does not redesign or repair the system.

## Inputs

Use the caller-provided:

* aggregate diff and commit list, when reviewing implementation;
* originating spec;
* spec **Architecture Impact**, when present;
* affected entities and governing ADR/doc references, when known;
* owner overrides, when applicable;
* proposed remediation or Root Blocker acceptance obligation, when evaluating its architecture conformance;
* affected production paths/contracts for that obligation, when known.

## 1. Establish the Intended Architecture

Read the spec's **Architecture Impact** and identify:

* affected entities;
* impact: `none | conforming | extending | changing | retiring`;
* governing architectural decisions or constraints;
* ADRs/docs that resolved intentional architecture changes.

If implementation materially changes architecture but the spec contains no resolved architectural basis for that change, report a **Blocking** finding.

Do not invent the missing decision here.

## 2. Load Current Architectural Context

If the Living Entity Wiki exists:

1. Read `wiki/index.md`.
2. Load the affected entity pages.
3. Follow relevant inline citations to authoritative sources.
4. Read `wiki/_schema.md` when authority or conflict semantics are needed.

Consult applicable:

* accepted ADRs;
* `docs/current/`;
* relevant `docs/proposed/` for planned architecture;
* implementation evidence from the codebase.

The wiki is derived context, not architectural authority.

Use read-only structural tools such as `codegraph` or `codebase-memory-mcp` only when targeted repository evidence is needed.

Do not update indexes or regenerate graphs.

## 3. Review the Aggregate Implementation

When reviewing implementation, inspect the complete spec diff for architecture consequences that may not be visible in any individual ticket.

Look for:

* ownership moving away from the canonical owner;
* layers bypassing established boundaries;
* reversed or invalid dependency direction;
* duplicate ownership of a durable concept;
* parallel canonical paths, runtimes, repositories, services, or sources of truth;
* new architectural abstractions or boundaries not resolved by the spec;
* existing architectural boundaries or responsibilities silently retired;
* implementation that contradicts an applicable invariant or accepted decision;
* accepted realization-required decisions implemented differently from what was resolved;
* entity topology changes not deliberately resolved through the architecture lifecycle.

Evaluate the implementation as a system, not as isolated hunks.

## 4. Review Proposed Remediation Obligations

When the caller provides a proposed remediation or Root Blocker acceptance obligation, evaluate whether that obligation is implementable under current architectural authority.

Do not decide whether the obligation is desirable and do not design its solution.

Report **Blocking** with `Architecture decision required: Yes` when satisfying the obligation would require:

* violating or changing an accepted architectural decision;
* introducing a new canonical contract, owner, path, or boundary;
* choosing a new dependency direction or lifecycle responsibility; or
* reconciling materially conflicting architectural authorities.

Use `Architecture decision required: No` when current authority already permits and determines the required behavior.

If the obligation conforms to current architecture, report no architecture finding for it.

## 5. Handle Evidence Correctly

Follow the repository's claim-specific authority rules.

If applicable architectural authorities materially disagree, report `[source-conflict]` as **Blocking**. Do not choose a winner.

Do not classify implementation absence or nonconformance as `[source-conflict]` merely because an accepted decision has not yet been realized. Distinguish implementation or documentation drift from disagreement between architectural authorities.

For mechanically observable constraints, positive implementation evidence may verify compliance.

For intent-level architectural constraints, absence of contradictory code is not proof. State only that no contrary implementation evidence was found.

Do not turn uncertainty into an architectural fact.

### Active Work Context

When an apparent architecture mismatch may reflect active implementation or remediation work, check relevant **open GitHub issues** using strong identifiers such as the affected entity, ADR, canonical owner, root blocker, or spec.

GitHub issues are **workflow-status evidence only**. They are not architectural authority or implementation proof.

Use them to determine whether:

* an existing architecture decision is already being realized or remediated;
* the mismatch is known and actively tracked;
* remediation requires a new architecture decision or only conformance with an existing one.

If a relevant issue declares a work branch, inspect that ref read-only when useful. Do not switch branches.

Implementation present only on another branch is **in progress**, not implemented on the branch under review.

Active work does not make the audited branch pass, and a closed issue does not prove implementation.

## 6. Classify Findings

Use the caller's Finding Taxonomy when provided.

Otherwise:

* **Blocking** — implementation or a proposed remediation obligation violates applicable architectural authority, introduces/requires an unresolved material architecture change, or cannot be judged because of a material `[source-conflict]`.
* **Advisory** — architecture concern worth review but not supported strongly enough to establish a violation.
* **Owner-overridden** — explicitly accepted by the owner; report only when useful for context.

Do not promote general design preferences or smells into Blocking architecture findings.

For every **Blocking** finding, determine:

```text
Architecture decision required: Yes | No
```

Use **No** when existing architectural authority already establishes the required result and the remaining work is conformance or remediation.

Use **Yes** only when remediation requires a new or changed architectural decision, applicable architectural authorities materially disagree, or the governing architecture cannot be determined.

Do not equate **Blocking** with **Architecture decision required: Yes**.

## Output

For each finding report:

```markdown
### <Blocking | Advisory | Owner-overridden> — <short title>

**Issue:** <what the implementation or proposed obligation does/requires>

**Evidence:** <diff/source/obligation evidence>

**Architecture:** <affected entity, ADR, document, contract, or invariant>

**Why it matters:** <specific architectural consequence>

**Architecture decision required:** <Yes | No>

**Routing:** <existing-authority remediation | upstream architecture resolution>
```

For `Architecture decision required: No`, identify the governing authority when known.

For `Architecture decision required: Yes`, identify the specific unresolved architectural question.

If reviewing a proposed remediation obligation, identify the exact blocked obligation when applicable.

If no findings exist:

```text
No findings.
```

Keep the report concise and evidence-based.

## Out of Scope

`$review-architecture` does not:

* run tests, Ruff, Mypy, coverage, and duplication scans;
* invoke the `$wiki-lint` skill;
* update repository graphs;
* perform the Standards or Spec review axes;
* invent or modify Root Blocker acceptance obligations;
* modify source code;
* create or edit ADRs or non-ADR documents;
* mutate the Living Entity Wiki;
* resolve `[source-conflict]`;
* design new architecture to fix a finding;
* create remediation tickets;
* treat GitHub issues as architectural authority;
* treat unmerged branch work as current implementation.

The caller owns remediation and lifecycle routing.
