---
name: wiki-sync
description: Maintain the Living Entity Wiki around specific source-code, authoritative-document, ADR, and entity-topology changes.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Sync

`$wiki-sync` maintains the derived Living Entity Wiki around a **specific change**.

It is not a whole-wiki audit. The `$wiki-lint` skill owns the separate repository-wide audit and is not invoked as part of `$wiki-sync`.

```text
authoritative architecture + implementation evidence
                    ↓
               wiki/entities/
```

Never modify authoritative sources merely to make them agree with the wiki.

## Context Economy

Preserve correctness while minimizing rediscovery.

* Reuse affected entities, governing authorities, source conclusions, and architecture context already established by the parent workflow or an earlier `$wiki-sync` pass.
* Search before reading. Locate the relevant claim, citation, symbol, or call site, then read the smallest useful surrounding range. Expand only when relevant behavior is distributed.
* Do not reread unchanged authority already established in the current workflow unless new evidence creates ambiguity or contradiction.
* On the post-change pass, start from the implementation diff and reuse the pre-change entity/source set. Expand only when the diff crosses another boundary or introduces new evidence.
* Do not read `wiki/log.md` until a durable wiki mutation requires a log entry or its history is specifically needed.
* Load `wiki/_schema.md`, `wiki/_template.md`, unrelated entities, and topology rules only when entity creation/topology is actually in play.

Whole-file reads are exceptional: use them only when relevant knowledge or behavior cannot be understood from targeted regions.

## When This Runs

Invoke `$wiki-sync`:

1. before and after a substantive source-code change;
2. after substantive creation, editing, or reclassification involving `docs/current/` or `docs/proposed/`;
3. after an ADR is created, substantively edited while proposed, or changes status through `$to-adr-doc`;
4. when entity topology or Boundary Rationale changes.

These triggers apply inside parent workflows such as `$implement-ticket`.

## Core Rules

### Authority

Authority is claim-specific:

* code, tests, configuration, executable checks → implementation reality;
* accepted ADRs → active architectural decisions;
* `docs/current/` → current architectural description;
* entity pages → derived knowledge only.

Resolve only source citations needed for claims that constrain or may change because of the current work.

If applicable authoritative sources materially disagree, surface:

```text
[source-conflict]
```

Report the conflicting sources and material consequence.

Do not:

* pick a winner;
* rewrite the wiki to one side;
* rewrite authoritative sources to manufacture agreement;
* continue treating the disputed claim as settled.

### Durable Knowledge Only

Update an entity only when durable knowledge changed, such as:

* Strict Invariant established or changed;
* accepted implementation-pending decision realized;
* qualifying Rejected Approach established;
* Open Question added or resolved;
* Boundary Rationale changed;
* entity topology changed.

Do not update merely because code was touched, moved, refactored, or an implementation technique succeeded.

### Evidence Strength

Match conclusions to evidence.

Mechanically observable rules may be positively verified when evidence proves them.

For architectural or intent-level claims, absence of contradiction supports:

```text
no contrary implementation evidence found
```

not:

```text
verified
```

Prefer executable architecture/static checks for stable mechanically enforceable subsets.

## 1. Source-Code Changes

### Trivial-Diff Exemption

The pre-change pass may be skipped only for:

* whitespace/formatting-only changes;
* comment/docstring-only changes with no contractual effect;
* pure file/symbol movement or rename with no behavioral or contractual change.

If movement changes a Routing Anchor in `wiki/index.md`, update it afterward.

When unsure, run the audit.

### Route the Change

Start from caller-provided Architecture context when available, then confirm against `wiki/index.md`.

Routing Anchors are coarse hints, not exhaustive ownership declarations.

Load only materially relevant entity pages and inspect applicable:

* Strict Invariants;
* Rejected Approaches;
* Open Questions;
* Planned entries.

Load another entity only when its knowledge materially affects the change.

If ownership is ambiguous, cross-boundary, or unmatched, use targeted repository evidence such as `$codegraph` or `$codebase-memory-mcp` rather than guessing.

Do not reconstruct a dependency graph.

### Pre-Change Audit

For every materially relevant entity claim:

1. confirm required source consistency;
2. check the intended change against applicable Strict Invariants;
3. check materially similar Rejected Approaches.

If a Strict Invariant would be violated, stop and report:

* invariant;
* causal reasoning;
* source;
* concrete conflict.

Do not silently override it.

If a Rejected Approach still applies, stop and surface it.

If it contains:

```text
Reconsider when: ...
```

and the condition clearly holds, mark it **eligible for reconsideration**.

If satisfaction is unclear, require owner judgment.

### Post-Change Audit

Start from the implementation diff.

Re-evaluate only:

* materially affected invariants;
* relevant accepted implementation-pending decisions;
* newly crossed entity boundaries.

Reuse pre-change routing and source conclusions.

Expand only when the diff introduces new evidence, contradicts prior conclusions, or crosses another boundary.

### Realized Accepted Decisions

For a relevant Planned entry marked:

```text
accepted, implementation pending
```

when implementation now realizes the accepted decision:

1. verify realization;
2. re-check `[source-conflict]`;
3. remove the pending Planned entry;
4. create/update the resulting Strict Invariant citing the accepted ADR.

Do not change ADR status.

If realization is partial or unclear, leave it Planned.

## 2. Rejected Approaches and Open Questions

### Rejected Approaches

Create a durable Rejected Approach only when:

* the owner explicitly rejected it for a load-bearing reason;
* an actual experiment failed for a concrete non-obvious reason; or
* an authoritative document records the rejection.

Valid provenance includes:

```text
source: docs/...
source: owner-confirmed session decision, undocumented
source: session experiment, undocumented
```

Unsupported agent judgment is insufficient.

Use `Reconsider when:` only for a genuine condition-dependent rejection.

### Open Questions

A concrete unresolved concern may be preserved with provenance such as:

```text
source: docs/...
source: owner-raised session question, undocumented
source: agent-observed during session, unresolved
```

Agent-observed entries remain questions, not implied facts.

When resolved:

* convert to a Strict Invariant if an active constraint resulted;
* create a qualifying Rejected Approach when appropriate;
* update Planned if future direction changed;
* otherwise remove the question.

## 3. No Matching Entity

If no active entity clearly covers the affected boundary, do not force-fit it.

Search `wiki/index.md` by scope first.

If no entity fits, load `wiki/_schema.md` and apply its Entity Boundary rules.

If promotion clearly qualifies:

* assign a stable Entity ID;
* use an existing Category when appropriate;
* require explicit approval for a new top-level Category;
* create from `wiki/_template.md`;
* add to `wiki/index.md`;
* set Implementation appropriately;
* add coarse Routing Anchors when applicable;
* record Boundary Rationale with required provenance.

If promotion fails, do not create an entity.

If unclear, surface the ambiguity.

## 4. Non-ADR Document Changes

Classification and movement are owned by `$to-doc` and `$classify-doc`.

`$wiki-sync` owns only the derived wiki consequence.

For substantive changes involving `docs/current/` or `docs/proposed/`:

1. search for existing inline citations to the changed document;
2. re-evaluate affected claims;
3. inspect changed regions for newly introduced entity-level knowledge.

For `docs/current/`, retain/update/remove affected Strict Invariants according to current authority and implementation evidence.

For `docs/proposed/`, retain/update/remove affected Planned content according to the proposal.

When a document changes class, evaluate affected claims under its **new authority**.

Rules:

* `proposed → current` does not automatically mean Planned → Strict Invariant;
* leaving `current` may invalidate claims sourced only from it;
* leaving `proposed` may invalidate Planned content sourced only from it;
* entering `current` or `proposed` may introduce newly eligible claims.

If only the path changes and semantic authority does not, update citation paths without rewriting otherwise-valid claims.

Do not recreate `linked_docs`.

## 5. ADR Events

ADR lifecycle is owned by `$to-adr-doc`.

`$wiki-sync` owns only the derived wiki consequence.

Inspect only entity claims materially affected by the ADR.

### Proposed

A proposed ADR may support Planned content.

On creation or substantive edit, update affected citations and add newly meaningful Planned direction when warranted.

### Accepted

Check affected claims for `[source-conflict]`.

Then classify the decision as:

* immediately effective; or
* realization-required.

Immediately effective decisions become active Strict Invariants.

For realization-required decisions:

* if already implemented, verify realization and represent the invariant;
* otherwise retain `accepted, implementation pending` under Planned.

### Rejected

Remove Planned content sourced only from the rejected proposal.

Add a Rejected Approach only when the rejection carries durable repeat-prevention knowledge.

### Deprecated or Superseded

The old ADR is no longer active authority.

For affected claims relying on it:

* retain only when another active source independently supports them;
* otherwise remove or replace them;
* process any successor under its own status.

Do not keep an invariant active solely because implementation still reflects retired authority.

## 6. Entity Topology

After bootstrap, `$wiki-sync` owns active entity topology.

Topology changes include:

* creation/promotion;
* rename;
* split;
* merge;
* removal;
* material scope change;
* Boundary Rationale change.

Load and apply `wiki/_schema.md` only when topology is changing.

### Rename

Atomically rename the page, update `wiki/index.md`, and update explicit entity links.

Do not rename historical ADRs merely because an entity ID changes.

### Split

Confirm each resulting boundary qualifies, redistribute knowledge by actual scope, update the index, and remove the old entity when it no longer exists.

Do not duplicate claims for symmetry.

### Merge

Choose/create the survivor, combine only valid knowledge, deduplicate overlaps, update Boundary Rationale/index, and remove obsolete pages.

Do not hide `[source-conflict]`.

### Removal

Remove the entity page, index entry, and explicit links.

Do not create tombstones.

`wiki/entities/` contains active entities only.

### Boundary Rationale

Change Boundary Rationale only after an explicit boundary/topology decision.

Ordinary file movement or package cleanup is insufficient.

Use provenance required by `wiki/_template.md`.

## 7. Wiki Mutation

When durable knowledge changes:

1. keep entity pages and `wiki/index.md` consistent;
2. maintain inline citations and causal reasoning;
3. avoid mechanically derivable structure;
4. append one concise semantic entry to `wiki/log.md`;
5. land the entity/index/log mutation atomically.

Load `wiki/log.md` only after determining that a durable mutation is required.

If `$wiki-sync` runs inside a parent committing workflow such as `$implement-ticket`, include its wiki changes in the parent commit.

If no durable knowledge changed:

* do not edit `wiki/log.md`;
* do not create a wiki-only commit;
* report that no entity update was required.

The log records semantic state changes, not tool executions.

## Failure and Ambiguity

Do not manufacture certainty.

Surface for owner judgment:

* `[source-conflict]`;
* ambiguous entity ownership;
* unclear promotion;
* introduction of a new Category;
* unclear immediate-vs-realization-required ADR acceptance;
* uncertain implementation realization;
* uncertain `Reconsider when:` satisfaction;
* unresolved material disagreement among relevant entity claims.

Derived wiki content must never conceal ambiguity in its sources.

## Out of Scope

`$wiki-sync` does not:

* perform initial repository-wide entity bootstrap;
* classify/move existing non-ADR documents — use `$classify-doc`;
* create new non-ADR documents — use `$to-doc`;
* own ADR lifecycle — use `$to-adr-doc`;
* perform or invoke a full wiki audit — that separate workflow belongs to the `$wiki-lint` skill;
* synthesize inferred cross-entity patterns — use `$wiki-synthesize`;
* rewrite authoritative docs merely to make the wiki agree;
* persist derivable dependency graphs, inventories, or call chains.

`$wiki-sync` maintains derived knowledge around a specific change. The `$wiki-lint` skill independently checks the whole system.

## Transition-Bound Affected Knowledge Routing

For a bounded `$wiki-sync` invocation, `no durable knowledge changed` is a semantic disposition and must be supported by an explicit affected-knowledge universe.

Before deciding mutation vs no-op, build a working **Affected Knowledge Routing Record** from the current change and authoritative routing evidence:

```text
Candidate: WK-<n>
Changed surface/authority: <exact source>
Candidate entity/claim: <exact entity + claim/section>
Routing basis: <routing anchor | inline citation | changed authority | boundary evidence | other direct evidence>
Disposition: <affected | not-affected | unresolved>
Reason/evidence: <why durable knowledge changes or does not>
```

The candidate universe must include every entity/claim surfaced by applicable Routing Anchors, direct inline citations to changed authoritative documents, and any additional entity boundary directly crossed by the diff/current change. Context-economy rules still apply after this routing universe is established; they may narrow how much text is read, not which surfaced candidates receive a disposition.

`no durable knowledge changed` is legal only when:

```text
Affected-knowledge candidates: <n>
Missing/unclassified candidates: 0
Unresolved candidates: 0
Affected candidates requiring mutation: 0
Not-affected candidates without reason/evidence: 0
Unresolved source conflicts: 0
```

When durable knowledge changes, the entity/index/log mutation set must correspond to the `affected` candidates and remain atomic under the existing Wiki Mutation rules. Do not create wiki edits for candidates explicitly proven `not-affected`, and do not silently omit an `affected` candidate because another entity was updated.
