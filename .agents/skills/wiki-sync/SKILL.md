---
name: wiki-sync
description: Maintains the Living Entity Wiki around source-code changes, authoritative document changes, ADR lifecycle events, and entity-topology changes. Audits relevant architectural constraints before code changes, detects source conflicts before drift, synchronizes Strict Invariants and Planned content from their inline sources, records qualifying rejected approaches and open questions, promotes realized accepted decisions, and keeps the active entity registry consistent.
compatibility: product=codex product=claude-code system=git network=none
---

# Wiki Sync

`$wiki-sync` maintains the Living Entity Wiki in the context of a specific change.

It is not a full-wiki audit. `$wiki-lint` performs independent whole-wiki health checking.

The Living Entity Wiki is derived:

```text
authoritative docs + implementation evidence
                    ↓
             wiki/entities/
```

Never edit an authoritative `docs/` source merely to make it agree with an entity page.

When authoritative sources materially disagree, surface `[source-conflict]` before attempting ordinary drift repair.

---

# When This Runs

Invoke `$wiki-sync` for any of these triggers:

1. **Before and after a substantive source-code change.**
2. **After a substantive edit, creation, or reclassification of a `docs/current/` or `docs/proposed/` document.**
3. **After an ADR is created, a proposed ADR body is substantively edited, or an ADR lifecycle status changes through `$to-adr-doc`.**
4. **When an entity boundary or topology changes.**

These triggers apply whether the work occurs inside another skill such as `$implement-ticket` or as an ad hoc edit.

This is a workflow convention, not a mechanically enforced repository gate. `$wiki-lint` is the independent backstop for missed synchronization.

---

# Trigger 1 — Source-Code Change

## Trivial-Diff Exemption

Skip the pre-change entity audit only when the intended diff is mechanically classifiable as one of:

* whitespace or formatting only;
* comment or docstring only, with no executable or contractual change; or
* a pure file/symbol rename or move that:

  * changes no behavior or contract; and
  * does not alter a Routing Anchor in `wiki/index.md`.

If a pure rename or move changes a Routing Anchor, no invariant audit is required solely because of the rename, but update `wiki/index.md` after the move so routing remains correct.

If there is doubt whether the change is trivial, run the normal audit.

---

## 1. Route the Change to an Entity

Read `wiki/index.md`.

Use its Routing Anchors as **non-exhaustive starting hints**, not ownership declarations.

### Clear match

If the touched code clearly falls under one entity's Routing Anchors, load that entity first.

### Ambiguous, cross-boundary, or unmatched path

If:

* multiple entities plausibly apply;
* the change crosses architectural boundaries;
* no Routing Anchor matches; or
* the touched path alone is insufficient to understand architectural ownership,

use current repository analysis rather than guessing.

Prefer the project's established discovery tooling, such as `$codegraph` or `$codebase-memory-mcp`, to determine the relevant architectural boundary and blast radius.

If no active entity covers the boundary, follow **No Matching Entity** below.

---

## 2. Load Only Relevant Entity Knowledge

Load the target entity page.

Do not scan every entity.

Then inspect the target entity's relevant:

* Strict Invariants;
* Rejected Approaches;
* Open Questions; and
* Planned entries.

If one of those claims explicitly references another entity and that related entity's constraints materially affect the intended change, load that entity too.

Do not load related entities merely because a structural dependency exists.

Cross-entity loading is driven by relevant architectural knowledge, not by a hand-maintained dependency graph.

---

## 3. Check Source Consistency First

Before using a Strict Invariant as the basis for blocking or reshaping the change, inspect its inline `source:` citation.

For claims materially relevant to the intended change:

1. resolve the cited authoritative source;
2. confirm that the source still has a citation-eligible class/status;
3. inspect applicable accepted ADRs, `docs/current/` claims, and implementation evidence for material disagreement.

Authority is claim-specific:

* source code, configuration, tests, and executable architecture checks provide evidence of **implementation reality**;
* accepted ADRs establish **active architectural decisions**;
* `docs/current/` claims to describe **current architecture**;
* entity pages are **derived** and never choose among conflicting authorities.

### Source conflict

If authoritative evidence materially disagrees, stop and surface:

```text
[source-conflict]
```

Report:

* the conflicting sources;
* what each currently claims;
* the implementation evidence where relevant; and
* why the disagreement affects the intended change.

Do not:

* pick a winner;
* rewrite the entity to match one side;
* modify an ADR or current document to manufacture consistency; or
* continue treating the disputed entity claim as settled architectural truth.

Resolve the authoritative-source conflict first.

Only then update the derived wiki.

---

## 4. Audit Strict Invariants

Check the intended change against every relevant Strict Invariant whose authoritative sources are not in conflict.

### No conflict

Proceed.

### Proposed change violates an invariant

Stop before writing code and surface:

* the invariant;
* its causal reasoning;
* its source;
* the concrete aspect of the proposed change that conflicts with it.

Do not silently override or rewrite the invariant.

The invoking task or owner must determine whether:

* the implementation should change;
* an authoritative architectural decision needs to change through its normal lifecycle; or
* the apparent conflict concerns a different scope.

---

## 5. Audit Rejected Approaches

Check the intended approach against relevant Rejected Approaches entries.

A close semantic match matters even when implementation details or naming differ.

### Ordinary active rejection

If the intended approach matches a prior rejection whose reasoning still applies:

* stop;
* surface the rejected approach;
* include its reason and provenance;
* do not silently retry it.

### Conditional rejection

If the entry contains:

```text
Reconsider when: ...
```

check whether that condition now appears satisfied.

If the condition is clearly unchanged, treat the rejection normally.

If the condition appears satisfied, surface the approach as **eligible for reconsideration** rather than assuming the old rejection no longer applies.

Do not silently erase or bypass the prior rejection.

If it is unclear whether the condition has been satisfied, surface that uncertainty for owner judgment.

---

## 6. Modify Source Code

Proceed with the implementation work only after the relevant pre-change audit is clear.

The invoking task or skill owns ordinary implementation procedure.

---

## 7. Re-Evaluate Implementation Evidence

After the source change, re-evaluate any affected Strict Invariants and relevant accepted-pending Planned decisions.

The strength of the conclusion must match the strength of the evidence.

### Mechanically observable invariant

Where an invariant is directly testable through source structure, tests, configuration, executable architecture checks, `$codegraph`, `$codebase-memory-mcp`, or equivalent evidence:

* positively verify it when the evidence supports that conclusion;
* report concrete contradictory evidence when it does not.

### Architectural or intent-level invariant

Where an invariant cannot be positively proven mechanically:

* inspect plausible implementation surfaces for concrete evidence of violation;
* report a violation when concrete contradictory evidence exists;
* do not claim compliance merely because no violation was found.

The strongest valid clean conclusion is:

```text
no contrary implementation evidence found
```

not:

```text
verified
```

unless the invariant is actually mechanically observable.

Whenever a stable subset of an architectural rule can be enforced through an executable architecture test or static rule, prefer that mechanical enforcement for the testable subset.

---

## 8. Promote Realized Accepted Decisions

Inspect relevant Planned entries marked:

```text
accepted, implementation pending
```

If the current change realizes such a decision:

1. verify realization using appropriate current-state evidence;
2. re-check for `[source-conflict]`;
3. remove the accepted-pending Planned entry; and
4. create or update the resulting Strict Invariant with the accepted ADR citation.

Do not change the ADR's `status`.

ADR acceptance and implementation realization are separate lifecycles.

If realization remains incomplete or ambiguous, leave the entry under Planned.

---

## 9. Record Durable Outcomes Conditionally

Update the entity page only when the change produces durable entity knowledge.

A wiki update is warranted when one or more of these occurred:

* a Strict Invariant changed or was established;
* an accepted implementation-pending decision was realized;
* a qualifying Rejected Approach was established;
* an Open Question surfaced;
* an existing Open Question was resolved;
* Boundary Rationale changed through an explicit topology decision; or
* entity topology changed.

Do **not** update the entity merely because:

* a new function was added;
* an internal refactor occurred;
* code moved;
* an implementation technique worked;
* a dependency changed without architectural consequence; or
* the entity's code was touched.

A successful or "validated" approach is not an independent wiki-write trigger.

If success produces no durable architectural outcome, the implementation itself is sufficient evidence.

---

## 10. Recording a Rejected Approach

A durable Rejected Approaches entry may be created only when:

* the owner explicitly rejected the approach;
* the approach was actually attempted and failed for a concrete, non-obvious reason worth preserving; or
* an authoritative document records the rejection.

Allowed provenance includes:

```text
(source: docs/...)
(source: owner-confirmed session decision, undocumented)
(source: session experiment, undocumented)
```

An agent's unsupported judgment is never enough to create a durable Rejected Approaches entry.

Where the reason depends on a condition that may later change, add:

```text
Reconsider when: ...
```

Do not add expiration dates merely because time may pass.

---

## 11. Recording or Resolving an Open Question

An unresolved concern may be recorded as an Open Question when it represents a concrete signal worth preserving.

Allowed provenance includes:

```text
(source: docs/...)
(source: owner-raised session question, undocumented)
(source: agent-observed during session, unresolved)
```

Agent-observed questions must remain clearly phrased as unresolved questions, not facts or decisions.

When an Open Question is resolved:

* convert the result into a Strict Invariant if an active constraint is established;
* add a qualifying Rejected Approach when appropriate;
* update Planned when future direction changes; or
* remove the question if the resolution produces no durable entity knowledge.

Do not leave resolved questions behind as if they remain open.

---

# No Matching Entity

If no active entity covers the architectural boundary being changed, do not force-fit the code into an unrelated entity.

## 1. Check for Existing Coverage

Search `wiki/index.md` by scope as well as name.

Different wording does not imply a new entity.

If an existing entity already owns the concern, route to it.

## 2. Apply the Promotion Test

Use the Entity Boundaries rules in `wiki/_schema.md`.

A newly surfaced sub-boundary normally requires at least 2 of:

* meaningful structural boundary;
* independent invariants;
* cross-entity fan-in.

Apply the ADR-only pending-implementation exception where appropriate.

## 3. Passes

If promotion is clearly warranted:

* assign a stable kebab-case Entity ID;
* reuse an existing Category when appropriate;
* surface introduction of a new top-level Category for explicit approval;
* create the page from `wiki/_template.md`;
* add it to `wiki/index.md`;
* set Implementation to `present` or `pending` as appropriate;
* add 1–2 coarse Routing Anchors for a `present` implementation where useful; and
* record Boundary Rationale with required provenance.

Treat creation as an entity-topology mutation and follow the atomic logging rules below.

## 4. Does Not Pass

Do not create an entity.

If durable architectural knowledge emerged, place it on the existing entity whose scope actually owns the constraint.

If no durable entity knowledge changed, no wiki write is needed.

## 5. Unclear

Proceed without inventing a boundary solely to close the workflow.

Surface that entity coverage is unresolved and requires owner judgment.

Do not silently create architectural topology from ambiguous evidence.

---

# Trigger 2 — Non-ADR Document Change

This trigger applies to substantive creation, editing, or reclassification involving:

* `docs/current/`; or
* `docs/proposed/`.

Documents classified as `research`, `reference`, or `process` do not directly establish Strict Invariants or Planned entries.

Their ordinary content edits therefore do not trigger entity synchronization unless reclassification changes their authority.

Existing-document classification and reclassification are owned by `$classify-doc`.

New-document creation is owned by `$to-doc`.

---

## 1. Determine the Document's Current Class

Classification is derived from folder location according to `wiki/_schema.md`.

Do not look for or create a `Doc-Class:` line or independent classification field.

---

## 2. Find Existing Derived Claims

Search inline `source:` citations across `wiki/entities/` for the document's path.

Do not use or recreate a `linked_docs` registry.

The inline citation attached to the actual claim is the single source of truth.

If citations exist, note the section containing each one:

* Strict Invariants;
* Planned;
* Rejected Approaches;
* Open Questions;
* Boundary Rationale.

---

## 3. Re-Evaluate Existing Claims

### `docs/current/`

Re-evaluate any Strict Invariant sourced from the changed document.

Before deciding that an entity is stale:

1. check applicable accepted ADRs;
2. inspect relevant implementation evidence;
3. evaluate `[source-conflict]` first.

If sources are consistent:

* claim still supported → leave it unchanged;
* claim wording or meaning changed → update the derived entity claim;
* source no longer supports the claim → remove or revise the derived claim;
* unclear → surface for human review.

### `docs/proposed/`

Re-evaluate any Planned entry sourced from the changed document.

* still supported → no change;
* proposed direction changed → update the Planned entry;
* direction was removed → remove the Planned entry;
* unclear → surface for human review.

Do not let Planned content remain stale merely because the document stayed inside `docs/proposed/`.

---

## 4. Check for Newly Introduced Claims

A substantive edit may introduce new architectural knowledge even if the document was already classified and previously cited nowhere.

After re-evaluating existing citations, inspect the changed content for newly introduced material.

### Current document

If the edit establishes a new current architectural constraint:

* determine the relevant entity;
* check authoritative-source consistency;
* inspect implementation evidence at the appropriate evidentiary strength;
* add a Strict Invariant only when the claim is legitimately current and source-consistent.

### Proposed document

If the edit establishes a meaningful future direction:

* determine the relevant entity;
* add or update the corresponding Planned entry.

Do not require a document to be newly created before newly added architectural content can enter the wiki.

---

## 5. Reclassification Transitions

When `$classify-doc` moves an existing document between classes, invoke `$wiki-sync` after the atomic move/reference update.

Evaluate the transition according to the new authority.

Examples:

### `research | reference | process → proposed`

Evaluate newly eligible content for Planned.

### `research | reference | process → current`

Evaluate newly eligible content for Strict Invariants, subject to `[source-conflict]` and implementation evidence.

### `proposed → current`

Do not automatically convert Planned content into Strict Invariants.

The document now claims to describe current reality, so:

1. verify source consistency;
2. inspect applicable current-state evidence;
3. promote only claims that are legitimately current;
4. surface `[source-conflict]` where authorities disagree.

### `current → proposed`

Claims sourced solely from that document may no longer remain active Strict Invariants.

Re-evaluate them:

* move appropriate future-state content to Planned;
* retain an invariant only if another valid active source independently supports it;
* otherwise remove the active derived claim.

### `current | proposed → research | reference | process`

The document can no longer serve its previous active wiki role.

Re-evaluate all derived claims sourced from it and remove or replace those that no longer have valid authority.

---

# Trigger 3 — ADR Lifecycle or Proposed-ADR Edit

ADR lifecycle rules are owned by `$to-adr-doc`.

Invoke `$wiki-sync` after:

* creating a new ADR;
* substantively editing an ADR while it remains `proposed`; or
* changing an ADR lifecycle status.

---

## Proposed ADR

A proposed ADR may support Planned content.

### New proposed ADR

Determine whether the decision belongs under Planned on an existing entity.

If the decision introduces a possible new entity boundary, apply the Entity Boundaries rules rather than silently creating one.

### Proposed ADR body edit

Search inline citations for Planned entries sourced from the ADR and re-evaluate them.

Also inspect whether the edit introduces a newly meaningful Planned claim not previously represented.

Do not assume a proposed ADR remains semantically unchanged merely because its `status` field did not change.

---

## `proposed → accepted`

First evaluate `[source-conflict]` against applicable current documentation and implementation evidence.

Then determine the nature of the accepted decision.

### Immediately-effective constraint

If acceptance itself establishes the active constraint, add or update the Strict Invariant immediately.

Remove the corresponding proposed Planned entry if one exists.

### Realization-required decision already realized

If the decision requires implementation but current evidence shows it is already fully realized at acceptance time:

* verify realization;
* create/update the Strict Invariant;
* remove the proposed Planned entry.

### Realization-required decision not yet realized

Keep or replace the Planned entry as:

```text
accepted, implementation pending
```

Do not create a Strict Invariant yet.

---

## `proposed → rejected`

Remove any Planned entry sourced solely from the rejected proposal.

If the rejection captures a non-obvious failure or direction worth protecting against future retries, add or update a Rejected Approaches entry citing the rejected ADR.

Do not create a Rejected Approaches entry merely because every proposed ADR necessarily ended in rejection; preserve only durable repeat-prevention knowledge.

---

## `accepted → deprecated`

The ADR is no longer active architectural authority.

Search entity claims citing it.

For each affected Strict Invariant:

* retain it only if another valid active source independently supports the claim;
* otherwise remove it from active Strict Invariants;
* if applicable authoritative sources disagree, surface `[source-conflict]`.

Do not preserve an active invariant solely because implementation still happens to reflect a deprecated decision.

Current implementation reality does not by itself turn a retired architectural decision back into an active invariant.

---

## `accepted | deprecated → superseded by ADR-NNNN`

Re-evaluate all entity claims citing the old ADR.

Then process the successor ADR according to its own status and meaning.

Do not leave the superseded ADR as active authority.

If the successor establishes a replacement constraint, derive the new entity claim from the successor rather than rewriting the historical ADR.

---

# Trigger 4 — Entity Topology Change

`$wiki-sync` owns living entity topology after bootstrap.

Topology changes include:

* creation or promotion;
* rename;
* split;
* merge;
* removal;
* a material scope change; or
* a change to Boundary Rationale.

These are architectural changes, not ordinary file maintenance.

---

## Rename

When an entity ID changes:

1. rename `wiki/entities/<old-id>.md`;
2. update its `wiki/index.md` entry;
3. update explicit entity links using the old path or ID;
4. update document prefixes only when the owning document workflow explicitly requires that rename; do not casually rename historical ADRs merely because an entity ID changed;
5. keep the operation atomic.

Do not leave both old and new entities active.

---

## Split

When one entity becomes multiple meaningful boundaries:

1. apply the Entity Boundaries rules to each resulting boundary;
2. create the resulting active entities;
3. redistribute existing knowledge by actual scope:

   * Strict Invariants;
   * Rejected Approaches;
   * Open Questions;
   * Planned entries;
   * Boundary Rationale;
4. do not duplicate claims across resulting entities unless the same cross-entity constraint genuinely applies to both;
5. update `wiki/index.md`;
6. remove the old entity if it no longer represents an active boundary.

---

## Merge

When multiple entities become one boundary:

1. choose or create the surviving Entity ID;
2. combine only still-valid knowledge;
3. deduplicate overlapping claims;
4. resolve `[source-conflict]` rather than hiding contradictions during the merge;
5. update Boundary Rationale;
6. update `wiki/index.md`;
7. remove obsolete entity pages.

---

## Removal

When a boundary ceases to exist:

* remove it from `wiki/index.md`;
* remove its entity page;
* update explicit entity links;
* preserve history in ADRs, authoritative documents, Git, and the semantic wiki log.

Do not create tombstone entity pages.

`wiki/entities/` contains active entities only.

---

## Boundary Rationale Changes

Boundary Rationale changes only as part of an explicit topology or boundary decision.

Required provenance is defined by `wiki/_template.md`.

Ordinary source-file movement, package cleanup, or refactoring is not sufficient reason to rewrite Boundary Rationale.

---

# Wiki Mutation Rules

Whenever `$wiki-sync` makes a substantive wiki mutation:

1. keep the affected entity pages and `wiki/index.md` mutually consistent;
2. update inline citations rather than maintaining a separate document registry;
3. preserve causal reasoning;
4. avoid mechanically derivable structure;
5. append one concise semantic entry to `wiki/log.md`; and
6. land the wiki mutation and matching log entry atomically.

Examples of substantive mutations:

* entity created;
* entity content materially updated;
* Planned decision promoted to Strict Invariant;
* qualifying Rejected Approach recorded;
* Open Question added or resolved;
* Implementation changed from `pending` to `present`;
* Routing Anchor changed;
* entity renamed, split, merged, or removed;
* Boundary Rationale changed.

Example:

```text
## [YYYY-MM-DD] entity-update | persistence — promoted ADR-0012 to implemented invariant
```

---

## When Invoked Inside Another Committing Skill

If `$wiki-sync` runs inside a workflow such as `$implement-ticket` that performs one commit for the overall change:

* stage the wiki mutation and matching `wiki/log.md` entry with that change;
* do not create a second standalone wiki commit.

The requirement is atomicity of the semantic wiki mutation and its log entry, not ownership of the Git commit.

---

## No Wiki Mutation

If `$wiki-sync` audits the change and determines that no durable wiki knowledge changed:

* do not edit `wiki/log.md`;
* do not create a wiki-only commit;
* report that no entity update was required.

The wiki log records state changes, not tool executions.

---

# Failure and Ambiguity Rules

`$wiki-sync` must not manufacture certainty to complete its workflow.

Surface rather than silently resolve:

* `[source-conflict]`;
* ambiguous entity ownership;
* unclear entity promotion;
* unclear new Category introduction;
* uncertainty about whether an accepted ADR is immediately effective or realization-required;
* uncertainty about implementation realization;
* uncertainty about whether a `Reconsider when:` condition has been met;
* unresolved material disagreement among relevant entity claims.

Derived wiki content must never become the mechanism used to conceal ambiguity in its sources.

---

# Out of Scope

`$wiki-sync` does not:

* perform the initial repository-wide entity decomposition and bootstrap;
* independently classify or move non-ADR documents — use `$classify-doc`;
* create new non-ADR documents — use `$to-doc`;
* own ADR lifecycle rules — use `$to-adr-doc`;
* perform a full independent wiki-health audit — use `$wiki-lint`;
* synthesize inferred cross-entity patterns — use `$wiki-synthesize`;
* rewrite authoritative `docs/` sources merely to make the wiki consistent;
* persist mechanically derivable dependency graphs, file inventories, or call chains.

`$wiki-sync` maintains the derived wiki around a specific change. `$wiki-lint` independently checks the system as a whole.
