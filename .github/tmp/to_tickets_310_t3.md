## Parent

Remediation parent: Spec Review #310  
Parent Spec: #279

## Spec obligations

None — the current 122-cell Spec contract contains no direct cell for this missing architecture/design-only cardinality/final-history obligation; coverage is through `ARCHSRC-1`.

## Root blocker

None — this ticket reconciles decomposition defect DD-1 / finding RF-3 rather than an ordinary Root Blocker.

## Decomposition defect

DD-1 — Atomic multi-relationship correction omitted from decomposition.

## Architecture obligations

ARCHSRC-1

## Architecture context

`docs/proposed/application-use-cases-investment-decision-lifecycle.md` §§12–13 and §17; `docs/proposed/investment-decisions-decision-relationship-model.md` §5.4; `docs/proposed/durable-persistence-investment-decision-history.md` §§5 and 8. These sources require one explicitly supplied atomic correction set to be validated as a complete final history and committed all-or-nothing, with no intermediate graph state. All architecture and material design decisions currently required by this ticket are accepted; no known implementation-readiness blocker remains unresolved.

## What to build

- Extend the privileged relationship-correction application command to accept a complete one-or-more correction set rather than only one target correction.
- Preserve explicit same-command correction target ancestry and validate the complete proposed post-command relationship history across the entire set.
- Run the frozen temporal mixed-lineage graph predicate over the complete final history across all materially distinct known historical/future intervals.
- Commit the full correction set, all required protected endpoint `DecisionVersion` effects, and the command receipt atomically, or commit nothing; no tentative/intermediate correction order becomes public state.
- Require expected-version guards for every directly touched pre-existing endpoint and transactionally revalidate all material endpoint/admission histories, correction ancestry, graph paths/return paths, known-future facts, and absence predicates relied on by admission.
- Make operation idempotency bind the complete semantic correction set: exact replay returns the stored result; same OperationId with a changed set conflicts.
- Preserve existing single-target correction as the one-element case and consume the domain's existing interpretation/graph predicates rather than inventing an application-side reducer.

## Acceptance criteria

- [ ] One correction command can carry several explicit relationship corrections, each with valid same-lineage target ancestry.
- [ ] The complete proposed final relationship history is validated for correction ancestry, interpretation, temporal admission, and graph safety before commit.
- [ ] A valid multi-correction repair commits every requested correction atomically with its complete required version/receipt consequences.
- [ ] Any invalid target, definite cycle, indeterminate possible cycle, incomplete history, relationship conflict, stale concurrency predicate, or persistence failure commits no correction and no partial result.
- [ ] No request-list order, insertion order, UUID order, timestamp order, or tentative serialization order gains semantic precedence.
- [ ] Expected endpoint versions are necessary but not treated as sufficient graph-safety proof; all material non-endpoint/future/absence predicates are revalidated through commit.
- [ ] Relationship-only version effects remain support/basis-sensitive, advance each existing Decision at most once for the atomic command, and never fabricate lifecycle facts or advance `DecisionLifecycleSequence`.
- [ ] Exact replay appends nothing; changed-request OperationId reuse conflicts.
- [ ] Existing single-target correction remains behaviorally compatible.
- [ ] Deterministic tests cover multi-correction success, one-invalid-member rollback, recursive restoration/contest, definite and possible cycles, stale non-endpoint/future/absence dependencies, replay/conflict, version effects, and no visible intermediate graph state.

## Verification obligations

- Independently re-read and prove `ARCHSRC-1` against the final command/application/domain/persistence behavior.
- Prove the complete atomic-correction acceptance domain plus the preserved one-element case.
- After the remediation set closes, fresh `$verify-spec` must independently validate the reconciled Architecture/Design Obligation Manifest and repaired exact `spec-279` HEAD before `$review-spec` is rerun; downstream Spec lifecycle work is not this ticket's closure prerequisite.

## Preservation obligations

- Existing relationship correction remains privileged/internal and append-only.
- Original relationship facts/corrections remain immutable and inspectable.
- Recursive `QUALIFY`/`DISCONFIRM`, restoration, sibling independence, contested interpretation, correction ancestry, relationship-basis role separation, cycle safety, idempotent replay, and no-partial-commit behavior remain intact.
- Relationship-only `DecisionVersion` and lifecycle-sequence separation remain intact.
- Existing new-identity renewal and one-or-many Supersession behavior from closed #305 remain unchanged.

## Root-complete sweep required for closure

- Reconcile DD-1 to `ARCHSRC-1` and this ticket.
- Generate/inspect/disposition the complete architecture-required atomic multi-correction obligation and its preserved single-correction boundary.
- Missing architecture obligations 0; ambiguous 0; implementation architecture obligations without ticket coverage 0; unchecked 0.

## Blocked by

None — can start immediately.

## Ticket branch

`spec-279`

## Ticket baseline

`Pending`

**Required issue label/status after publication:** `ready-for-agent`
