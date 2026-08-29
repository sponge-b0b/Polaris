---
name: wiki-lint
description: Audit the Living Entity Wiki for structural integrity, citations, source conflicts, drift, stale questions, and classification hygiene.
compatibility: product=codex product=claude-code system=git system=gh network=required
---

# Wiki Lint

`$wiki-lint` independently audits accumulated Living Entity Wiki state.

`$wiki-sync` maintains one change. `$wiki-lint` audits the whole.

A clean run reports only. Do not mutate the wiki, append `wiki/log.md`, or commit unless applying an explicitly allowed mechanical fix.

## Audit Order

Run in order:

1. structural integrity;
2. citation resolution and eligibility;
3. authoritative-source consistency;
4. document/wiki drift;
5. implementation drift;
6. Open Questions;
7. cross-entity contradictions;
8. document classification.

Do not classify downstream drift until authoritative-source consistency is understood.

## 1. Structural Integrity

`wiki/index.md` is the active-entity registry.

Report `[structural]` for:

* entity/index mismatches;
* duplicate Entity IDs or active scopes;
* invalid `Implementation` values;
* invalid/missing Routing Anchors;
* `pending` when implementation clearly exists;
* `present` when implementation cannot reasonably be found;
* retired/tombstone pages under `wiki/entities/`;
* obsolete metadata/frontmatter;
* invalid entity-page structure;
* missing or invalid Boundary Rationale.

Allowed implementation states:

```text
present
pending
```

A `pending` entity normally has no implementation Routing Anchor.

Entity pages must follow `wiki/_template.md`.

Do not invent missing rationale or topology.

## 2. Citation Resolution and Eligibility

Entity-document relationships exist only through inline `source:` citations.

Use `wiki/_schema.md` and `wiki/_template.md`.

Report:

* `[broken-doc-citation]` — cited `docs/...` path no longer resolves;
* `[invalid-citation]` — source type was never valid for that section;
* `[stale-citation]` — source was valid but its lifecycle/classification changed.

Core eligibility:

### Strict Invariants

* accepted ADR;
* `docs/current/`.

### Planned

* proposed ADR;
* `docs/proposed/`;
* accepted ADR whose realization is still pending.

### Rejected Approaches, Open Questions, Boundary Rationale

Use provenance allowed by `wiki/_template.md`.

Do not delete claims merely because a citation is broken or stale.

## 3. Authoritative-Source Consistency

Authority is claim-specific:

* implementation → what currently exists/behaves;
* accepted ADR → active architectural decision;
* `docs/current/` → current architectural description;
* entity pages → derived knowledge, never authority.

Report `[source-conflict]` only when applicable authorities **normatively disagree** about architecture or when competing authoritative claims about current behavior cannot be reconciled without judgment.

Examples:

* incompatible architectural invariants;
* conflicting canonical owners/paths;
* incompatible boundary or dependency rules;
* one authority requires behavior another forbids;
* authoritative current-state descriptions materially disagree and no deterministic lifecycle update explains the difference.

For each `[source-conflict]`, include:

* entity/claim;
* conflicting sources;
* what each says;
* implementation evidence;
* why the disagreement matters.

Do not select a winner or repair the disputed claim.

### Realization-Status Rule

Do **not** report `[source-conflict]` merely because an accepted ADR still says implementation is `pending`, `not yet realized`, or equivalent while current implementation clearly realizes its accepted normative decision.

When:

1. the ADR remains accepted;
2. its normative decision agrees with the implementation;
3. implementation evidence clearly realizes that decision; and
4. only the ADR's descriptive realization/status statement is stale;

then classify the condition as deterministic **`[doc-drift]`**, not `[source-conflict]`.

Report:

* the accepted decision;
* evidence that implementation realizes it;
* the stale realization/status statement;
* required owner: `$to-adr-doc`.

The derived wiki may already reflect the realized invariant without creating a source conflict when its claim agrees with both the ADR's normative decision and current implementation.

Do not use this rule when implementation contradicts the ADR's actual decision.

## 4. Document and Wiki Drift

Report `[doc-drift]` when meaning or lifecycle state has become stale while underlying architectural authority remains unambiguous.

Examples:

* entity claim no longer reflects its valid source;
* accepted ADR realization status remains pending after clear realization;
* current documentation describes an obsolete state while authority and implementation agree on the replacement.

For entity claims sourced from `docs/current/`:

* confirm the source remains current;
* ensure no `[source-conflict]`;
* compare the claim with current source meaning.

For Planned entries sourced from proposed material:

* compare against the current proposal;
* report drift when it changed, disappeared, or was substantively rewritten.

### Accepted Implementation-Pending Decisions

For accepted ADR-backed Planned entries:

1. confirm the ADR remains accepted;
2. determine whether realization is still pending;
3. inspect strong implementation evidence;
4. if clearly realized:

   * stale ADR realization statement → `[doc-drift]`, owner `$to-adr-doc`;
   * stale wiki `Planned`/`Implementation: pending` state → `[doc-drift]` or `[structural]` as applicable.

Do not infer realization from weak or merely suggestive evidence.

## 5. Implementation Drift

Report `[code-drift]` when implementation materially contradicts an active architectural invariant whose authorities otherwise agree.

Do not use `[code-drift]` for inability to prove a claim.

### Active Implementation Work

When expected implementation cannot be found on the current branch, inspect relevant open GitHub work when useful.

Issues are workflow-status evidence only, never architectural authority or implementation proof.

If an open Spec/ticket explicitly tracks missing realization:

* treat it as pending rather than unexplained;
* inspect its declared work branch read-only when useful;
* do not switch branches;
* unmerged implementation remains in progress, not current implementation.

Closed issues are not implementation proof.

### Evidence

For mechanically observable invariants, use:

* source;
* tests;
* executable architecture checks;
* `$codegraph`;
* `$codebase-memory-mcp`;
* configuration.

For intent-level invariants, report `[code-drift]` only when contradictory evidence exists.

Otherwise report:

```text
no contrary implementation evidence found
```

not `verified`.

## 6. Open Questions

Report `[stale-question]` when an Open Question deserves deliberate review because of age, changed context, or apparent later resolution.

Approximately 60 days is a heuristic, not an expiry rule.

A stale question may be:

* resolved;
* confirmed open;
* converted into another durable section;
* removed because it is no longer meaningful.

Do not fabricate resolution.

## 7. Cross-Entity Contradictions

Scan active entity claims for material contradictions.

If underlying authorities disagree, use `[source-conflict]`.

If authorities agree and only derived wiki state is stale, use the appropriate drift finding.

Avoid duplicate findings for the same root cause.

## 8. Document Classification

Report `[unclassified-doc]` for project-owned files under `docs/` whose classification cannot be derived from:

* `docs/adr/` plus ADR status;
* `docs/current/`;
* `docs/proposed/`;
* `docs/research/`;
* `docs/reference/`;
* `docs/process/`;
* registered external scaffold directories.

Use `$classify-doc` for existing non-ADR documents.

## Finding Priority

Prefer the root cause:

```text
[source-conflict]
    ↓
[broken-doc-citation]
    ↓
[stale-citation] / [invalid-citation]
    ↓
[doc-drift]
    ↓
[code-drift]
```

Exception: stale realization metadata that satisfies the **Realization-Status Rule** is `[doc-drift]`, not `[source-conflict]`.

Do not emit duplicate downstream findings when one finding explains them.

## Resolution Rules

`$wiki-lint` reports judgment-bearing findings. It does not decide architecture.

Never automatically resolve:

* genuine `[source-conflict]`;
* `[code-drift]`;
* semantic `[doc-drift]`;
* ambiguous citation findings;
* stale questions;
* cross-entity semantic contradictions;
* topology or Boundary Rationale.

### Mechanical Fixes

Apply a fix only when exactly one correction is unambiguous and no architectural judgment is required.

Examples:

* stale link after known rename;
* formatting damage;
* duplicate registry row;
* Routing Anchor changed only by established path rename.

Do not treat architectural claim changes, source selection, realization/lifecycle transitions, or topology changes as mechanical.

For stale accepted-ADR realization status, **report `$to-adr-doc` as owner rather than editing the ADR directly**.

## Reporting

Use:

```text
[source-conflict]
[code-drift]
[doc-drift]
[stale-citation]
[invalid-citation]
[broken-doc-citation]
[unclassified-doc]
[stale-question]
[structural]
```

Each finding includes:

* entity/claim;
* evidence/sources;
* relevant implementation evidence;
* relevant open work when applicable;
* why it matters;
* required next action/owner.

End with counts by finding type.

Clean result:

```text
Wiki lint: 0 issues found
```

## Logging and Commits

A report-only or clean run:

* does not edit `wiki/log.md`;
* does not create a commit.

For an allowed mechanical fix:

* append one semantic `wiki/log.md` entry;
* land fix and log atomically;
* defer commit ownership to the calling workflow when one exists.

Do not log lint runs or issue counts.

## Related Skills

* `$wiki-sync` — per-change synchronization;
* `$to-adr-doc` — ADR lifecycle and realization-status updates;
* `$to-doc` — new non-ADR documents;
* `$classify-doc` — existing non-ADR classification;
* `$wiki-synthesize` — higher-inference synthesis.

## Out of Scope

`$wiki-lint` does not:

* bootstrap the wiki;
* decide entity boundaries;
* settle genuine source conflicts;
* rewrite architectural decisions;
* directly update ADR realization/lifecycle state;
* treat GitHub issues as architectural authority;
* treat unmerged work as current implementation;
* infer intent-level compliance from absence of evidence;
* maintain obsolete entity metadata;
* log clean runs;
* perform cross-entity synthesis.

Its job is to determine whether the Living Entity Wiki can be trusted, distinguish genuine authority conflicts from ordinary lifecycle drift, and route correction to the proper owner.

## Transition-Bound Wiki Audit Coverage

`Wiki lint: 0 issues found` is an exhaustive claim and requires a materialized audit universe. Zero findings among the surfaces that happened to be inspected is not a clean audit.

Before reporting a clean result, build a working **Wiki Audit Coverage** inventory from the repository's current canonical registries/sources. At minimum account for the candidate universes relevant to the eight audit stages:

* every active `wiki/index.md` entity row and every entity page;
* every inline `source:` citation on active entity pages;
* every authoritative source referenced by those citations whose lifecycle/eligibility must be checked;
* every Strict Invariant/Planned/Open Question/Boundary Rationale claim requiring the applicable audit stage;
* every active entity pair/scope implicated by a possible cross-entity contradiction;
* every project-owned `docs/` file subject to classification.

Each candidate receives a working disposition:

```text
Candidate: WA-<n>
Audit stage: <1..8>
Surface/claim: <exact identity>
Disposition: <checked | finding:<type/id> | not-applicable>
Evidence/reason: <direct evidence or exact N/A reason>
```

Candidates may be generated by more than one stage when genuinely necessary; deduplicate identical stage+claim obligations rather than silently dropping them.

Before a clean result require:

```text
Audit candidates: <n>
Coverage rows: <n>
Missing/unclassified candidates: 0
Unchecked candidates: 0
Not-applicable rows without reason: 0
Findings: 0
```

When findings exist, the same coverage discipline still applies: do not stop after the first issue if other independently inspectable audit stages remain. A concise finding report is still allowed; the full working coverage table need not be persisted.
