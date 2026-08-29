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
* affected production paths/contracts for that obligation, when known;
* architecture Review Universe cells, when provided by `$review-spec`;
* review pass strategy: `authority-first | adversarial-surface-first`, when provided.

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

### Architecture Coverage Contract

Architecture review is coverage-driven, not discovery-until-interest-runs-out.

When `$review-spec` supplies Architecture Review Universe cells, preserve every supplied cell and its ID. Do not merge or drop materially distinct cells.

The architecture universe must account for:

* every affected entity in the Spec Architecture Impact;
* every governing ADR/current architectural document identified by the Spec or current entity context;
* every changed production surface materially participating in those entities or authorities;
* named canonical owners, paths, boundaries, persistence/release/evaluation seams, and transports;
* relevant sibling or alternate paths required to obey the same authority, even when they are unchanged by the latest remediation;
* the applicable architecture dimensions below.

For each relevant surface or boundary, evaluate applicable dimensions:

* canonical owner and source of truth;
* boundary crossing and dependency direction;
* authority/evidence/lifecycle ownership;
* fail-closed, unavailable, optional-dependency, default, and fallback behavior;
* alternate, compatibility, direct-construction, bypass, and parallel canonical paths;
* duplicate ownership of durable concepts, services, repositories, or sources of truth;
* caller/model/payload/metadata/mapping control over authoritative semantics;
* accepted realization-required decisions versus actual realization;
* retirement or topology changes not deliberately resolved.

Do not restrict architecture review to changed hunks when the governing authority requires parity across sibling entry points or transports.

Every coverage cell must end in exactly one state:

```text
checked-no-finding | blocking | advisory | not-applicable
```

`not-applicable` requires a concrete reason. `unknown`, `unchecked`, `deferred`, or silent omission is not complete review.

For every coverage cell, return concise evidence identifying the authority and inspected implementation surface(s). A finding does not discharge unrelated cells; continue until all cells are dispositioned.

If review discovers an additional materially relevant architecture surface or authority not present in the supplied universe, add a new coverage cell rather than silently expanding another one.

### Independent Pass Strategies

When `review pass strategy` is supplied:

**`authority-first`**

Start from each governing entity/ADR/current authority and trace forward to its canonical implementation, callers, persistence/release/evaluation seams, and required sibling surfaces.

**`adversarial-surface-first`**

Start from changed and named production surfaces and trace backward to authority. Deliberately search for paths most likely to evade the canonical lifecycle, including:

* `None`/optional dependency behavior;
* defaults, fallbacks, compatibility branches, and early returns;
* direct construction or alternate service/facade entry points;
* caller-supplied authority/evidence/version/provenance;
* metadata/mapping/type-recovery authority paths;
* alternate persistence, release, promotion, audit, or evaluation paths;
* sibling CLI/backtest/MCP/runtime/facade behavior;
* paths that succeed when the canonical owner/service is unavailable.

Do not use another reviewer's findings or coverage conclusions. Each pass must independently disposition the complete architecture universe.

### Architectural Checks

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

When this skill is reviewing only a proposed remediation obligation rather than an aggregate implementation, full Spec-wide coverage accounting is not required; cover the supplied obligation and its affected production paths/contracts.

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

For aggregate implementation review, always append:

```markdown
## Coverage

- ARCH-<id> — <checked-no-finding | blocking | advisory | not-applicable> — <authority>; <surfaces inspected>; <evidence/reason>
```

Include every supplied and reviewer-added Architecture Review Universe cell exactly once.

If no findings exist, report `No findings.` **and still return the complete Coverage section**.

Keep findings concise and evidence-based. Coverage may be longer because it is an internal completeness artifact consumed by `$review-spec`.

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

## Transition-Bound Architecture Review Coverage

Architecture review completeness has two separate gates: complete construction of the applicable architecture universe, then sound disposition of every cell. Neither may be inferred from `checked = all cells the reviewer happened to create`.

Before dispositioning `ARCH-*` cells, build a working **Architecture Candidate Inventory** from the supplied Architecture Impact plus current accepted authorities and directly implicated canonical owners, paths, boundaries, lifecycles, sources of truth, and authority-required sibling/alternate surfaces.

Each candidate records:

```text
Candidate: AC-<n>
Source/authority: <exact source>
Architectural dimension/surface: <exact concern>
Disposition: <ARCH-<n> | excluded>
Reason: <None | exact authority/scope reason for exclusion>
```

Every candidate must be dispositioned. Exclusion is explicit evidence-bearing state, not omission. Before review can complete require `Unclassified architecture candidates: 0` and `Excluded candidates without reason: 0`.

For every `ARCH-*` cell maintain:

```text
Claim: <authoritative architecture obligation>
Predicate: <subject + quantifier + domain + required predicate + material conditions/exceptions>
Falsifier: <concrete current state that would make the claim false>
Evidence: <direct current evidence>
Survivability: <excluded | survives>
Assumptions: <None | material assumption + authority/direct proof>
Disposition: <checked-no-finding | Blocking | Advisory | not-applicable | unresolved>
```

`checked-no-finding` requires `Survivability: excluded` and no unproven material assumption. If all inspected evidence could succeed while the architecture claim remains false, the cell is unresolved or finding-bearing, never clean by default.

Return architecture coverage counts with the existing review result and require:

```text
Missing ARCH cells: 0
Unknown ARCH cells: 0
Unchecked/unresolved ARCH cells: 0
Incomplete checked-no-finding proof records: 0
Unclassified architecture candidates: 0
```

These are working review records; concise human reporting remains acceptable.
