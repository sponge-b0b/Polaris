---
name: wiki-sync
description: Maintain the Living Entity Wiki around specific source-code, authoritative-document, ADR, and entity-topology changes. Audits architectural constraints before code changes, detects source conflicts, synchronizes derived entity knowledge, promotes realized accepted decisions, and keeps the active entity registry consistent.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Sync

`$wiki-sync` maintains the Living Entity Wiki around a **specific change**.

It is not a whole-wiki audit. Use `$wiki-lint` for independent repository-wide checking.

The wiki is derived:

```text
authoritative architecture + implementation evidence
                        ↓
                  wiki/entities/
```

Never modify an authoritative source merely to make it agree with the wiki.

When authoritative sources materially disagree, surface `[source-conflict]` before ordinary drift repair.

## When This Runs

Invoke `$wiki-sync`:

1. before and after a substantive source-code change;
2. after substantive creation, editing, or reclassification involving `docs/current/` or `docs/proposed/`;
3. after an ADR is created, a proposed ADR body is substantively edited, or ADR status changes through `$to-adr-doc`;
4. when entity topology or Boundary Rationale changes.

These triggers apply inside parent workflows such as `$implement-ticket` as well as ad hoc work.

## 1. Source-Code Changes

### Trivial-Diff Exemption

The pre-change audit may be skipped only for:

* whitespace/formatting-only changes;
* comment/docstring-only changes with no contractual effect;
* pure file/symbol rename or movement with no behavioral or contractual change.

If a rename/move changes a Routing Anchor in `wiki/index.md`, update the anchor afterward.

When unsure whether a diff is trivial, run the audit.

### Route the Change

Start with `wiki/index.md`.

Routing Anchors are coarse starting hints, not exhaustive ownership declarations.

If ownership is ambiguous, cross-boundary, or unmatched, use current repository evidence such as `$codegraph` or `$codebase-memory-mcp` rather than guessing.

Load only the relevant entity page(s).

Inspect applicable:

* Strict Invariants;
* Rejected Approaches;
* Open Questions;
* Planned entries.

Load another entity only when its actual architectural knowledge materially affects the change.

Do not reconstruct a dependency graph.

### Check Source Consistency First

Before relying on an entity claim:

1. resolve its inline `source:` citation;
2. confirm the source still has authority appropriate to that claim;
3. compare applicable accepted ADRs, `docs/current/`, and implementation evidence.

Authority is claim-specific:

* code, tests, configuration, and executable checks → implementation reality;
* accepted ADRs → active architectural decisions;
* `docs/current/` → current architectural description;
* entity pages → derived knowledge only.

If these materially disagree, surface:

```text
[source-conflict]
```

Report the conflicting sources and why the disagreement matters.

Do not:

* pick a winner;
* rewrite the wiki to one side;
* rewrite an ADR/current document to manufacture agreement;
* continue treating the disputed claim as settled.

### Audit Strict Invariants

Check the intended change against every materially relevant Strict Invariant whose sources are consistent.

If the change violates one, stop before editing and report:

* the invariant;
* causal reasoning;
* source;
* concrete conflict.

Do not silently override it.

### Audit Rejected Approaches

Check semantically similar Rejected Approaches, not only exact implementation matches.

If the rejection still applies, stop and surface it.

If it contains:

```text
Reconsider when: ...
```

and the condition appears satisfied, mark it **eligible for reconsideration** rather than silently bypassing it.

If satisfaction is unclear, require owner judgment.

### Post-Change Evidence

After implementation, re-evaluate affected invariants and accepted implementation-pending decisions.

Match conclusion strength to evidence.

For mechanically observable rules, positive verification is allowed when evidence actually proves them.

For architectural or intent-level rules, inspect plausible implementation surfaces for contradiction.

When nothing contradictory is found, say:

```text
no contrary implementation evidence found
```

not:

```text
verified
```

Prefer executable architecture/static tests for stable mechanically enforceable subsets.

### Realized Accepted Decisions

For a relevant Planned entry marked:

```text
accepted, implementation pending
```

if the implementation now realizes the accepted decision:

1. verify realization;
2. re-check `[source-conflict]`;
3. remove the pending Planned entry;
4. create/update the resulting Strict Invariant citing the accepted ADR.

Do not change ADR status.

If realization is partial or unclear, leave it Planned.

## 2. Durable Entity Outcomes

Update an entity only when durable knowledge changed.

Qualifying outcomes include:

* Strict Invariant established or changed;
* accepted implementation-pending decision realized;
* qualifying Rejected Approach established;
* Open Question added or resolved;
* explicit Boundary Rationale change;
* entity topology change.

Do not update the wiki merely because:

* code was touched;
* a function was added;
* an internal refactor occurred;
* code moved;
* a dependency changed without architectural consequence;
* an implementation technique succeeded.

A validated implementation approach is not independently wiki-worthy.

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

Unsupported agent judgment is never sufficient.

Use `Reconsider when:` only for a real condition-dependent rejection.

Do not add generic expiration dates.

### Open Questions

A concrete unresolved concern may be preserved with provenance such as:

```text
source: docs/...
source: owner-raised session question, undocumented
source: agent-observed during session, unresolved
```

Agent-observed entries must remain questions, not implied facts.

When resolved:

* convert to a Strict Invariant if an active constraint resulted;
* create a qualifying Rejected Approach where appropriate;
* update Planned if future direction changed;
* otherwise remove the question.

## 3. No Matching Entity

If no active entity clearly covers the affected boundary, do not force-fit it.

First search `wiki/index.md` by scope, not just terminology.

If no existing entity fits, apply the Entity Boundary rules in `wiki/_schema.md`.

A candidate boundary normally needs at least two of the schema's promotion signals, subject to its documented exceptions.

If promotion clearly passes:

* assign a stable Entity ID;
* use an existing Category when appropriate;
* require explicit approval for a new top-level Category;
* create the entity from `wiki/_template.md`;
* add it to `wiki/index.md`;
* set Implementation appropriately;
* add coarse Routing Anchors when applicable;
* record Boundary Rationale with required provenance.

If promotion fails, do not create an entity.

If promotion is unclear, surface the ambiguity rather than inventing topology.

## 4. Non-ADR Document Changes

Classification and movement are owned by `$to-doc` and `$classify-doc`.

`$wiki-sync` handles the **derived wiki consequence**.

For substantive changes involving `docs/current/` or `docs/proposed/`:

1. find existing inline `source:` citations to the document;
2. re-evaluate those claims;
3. inspect the changed content for newly introduced entity-level knowledge.

For `docs/current/`:

* re-check source consistency and implementation evidence;
* retain, update, or remove derived Strict Invariants according to what the document still supports.

For `docs/proposed/`:

* retain, update, or remove Planned content according to the current proposal.

If a document changes class, evaluate its derived claims according to its **new authority**.

Important rules:

* `proposed → current` does not automatically mean Planned → Strict Invariant;
* leaving `current` may invalidate claims sourced only from that document;
* leaving `proposed` may invalidate Planned content sourced only from it;
* moving into `current` or `proposed` may introduce newly eligible claims even when nothing cited the document before.

If only the path changes and semantic authority does not, update inline citation paths without rewriting otherwise-valid claims.

Do not recreate `linked_docs`.

## 5. ADR Events

ADR lifecycle is owned by `$to-adr-doc`.

`$wiki-sync` owns the derived wiki consequence.

Run after:

* ADR creation;
* substantive proposed-ADR body edit;
* ADR status change.

### Proposed

A proposed ADR may support Planned content.

On creation or body edit:

* update existing Planned citations;
* inspect for newly meaningful Planned direction.

### Accepted

First check `[source-conflict]`.

Then determine whether the decision is:

* immediately effective; or
* realization-required.

If immediately effective, represent the active constraint as a Strict Invariant.

If realization-required but already implemented, verify realization and represent the resulting invariant.

Otherwise keep:

```text
accepted, implementation pending
```

under Planned.

### Rejected

Remove Planned content sourced only from the rejected proposal.

Add a Rejected Approach only if the rejection contains durable repeat-prevention knowledge.

### Deprecated or Superseded

The old ADR is no longer active authority.

Re-evaluate every derived claim relying on it:

* retain only where another valid active source independently supports the claim;
* otherwise remove or replace the active derived claim;
* process a successor ADR according to its own current status.

Do not keep an invariant active solely because implementation still happens to reflect a retired decision.

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

Apply `wiki/_schema.md` promotion and topology rules.

### Rename

Atomically:

* rename the entity page;
* update `wiki/index.md`;
* update explicit entity links.

Do not casually rename historical ADRs merely because an entity ID changes.

### Split

For each resulting boundary:

* confirm it qualifies;
* redistribute existing knowledge by actual scope;
* update `wiki/index.md`;
* remove the old entity if it no longer exists.

Do not duplicate claims merely for symmetry.

### Merge

Choose/create the survivor, combine only valid knowledge, deduplicate overlaps, update Boundary Rationale/index, and remove obsolete entity pages.

Do not hide `[source-conflict]` during a merge.

### Removal

Remove the entity page and index entry and update explicit links.

Do not create tombstones.

`wiki/entities/` contains active entities only.

### Boundary Rationale

Change Boundary Rationale only after an explicit boundary/topology decision.

Ordinary file movement or package cleanup is not sufficient.

Use provenance required by `wiki/_template.md`.

## 7. Wiki Mutation Rules

Whenever `$wiki-sync` makes a substantive wiki mutation:

1. keep entity pages and `wiki/index.md` consistent;
2. maintain inline citations;
3. preserve causal reasoning;
4. avoid mechanically derivable structure;
5. append one concise semantic entry to `wiki/log.md`;
6. land the mutation and log entry atomically.

Examples include:

* entity created/removed/renamed/split/merged;
* Strict Invariant materially changed;
* Planned promoted to implemented invariant;
* Rejected Approach recorded;
* Open Question added/resolved;
* Implementation changed `pending → present`;
* Routing Anchor changed;
* Boundary Rationale changed.

If called inside a parent committing workflow such as `$implement-ticket`, stage the wiki/log changes with the parent commit rather than creating another commit.

If no durable wiki knowledge changed:

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
* perform a full wiki audit — use `$wiki-lint`;
* synthesize inferred cross-entity patterns — use `$wiki-synthesize`;
* rewrite authoritative docs merely to make the wiki agree;
* persist derivable dependency graphs, inventories, or call chains.

`$wiki-sync` maintains the derived wiki around a specific change. `$wiki-lint` independently checks the whole system.
