## Parent

Remediation parent: Spec Review #310  
Parent Spec: #279

## Spec obligations

None — the current 122-cell Spec contract contains no direct cell for this missing architecture/design-only existing-identity attachment path; coverage is through `ARCHSRC-2`.

## Root blocker

None — this ticket reconciles decomposition defect DD-2 / finding RF-4 rather than an ordinary Root Blocker.

## Decomposition defect

DD-2 — Late omitted-renewal-lineage attachment omitted from decomposition.

## Architecture obligations

ARCHSRC-2

## Architecture context

`docs/proposed/application-use-cases-investment-decision-lifecycle.md` §11 and §17; `docs/proposed/investment-decisions-decision-relationship-model.md` §§2.1 and 6.8; `docs/proposed/durable-persistence-investment-decision-history.md` §8 and the associated relationship transaction/concurrency contract. These sources permit later attributable assertion of genuinely omitted renewal lineage against an already-established source Decision/Need when the same historical predicates and explicit renewal basis are proven, without recreating or reopening identity. All architecture and material design decisions currently required by this ticket are accepted; no known implementation-readiness blocker remains unresolved.

## What to build

- Add a purpose-specific privileged application command for later attributable assertion of genuinely omitted `RENEWED_FROM` lineage against an already-established source Decision/Need.
- Require an explicit typed renewal relationship basis and ordinary attributable command metadata/provenance.
- Prove each predecessor was supportably substantively or externally resolved both when the source's new judgment episode began and at the relationship claim's effective instant; the relationship cannot predate the source episode.
- Append the missing relationship fact to the existing source/Need without allocating a replacement Decision/Need, reopening a resolved Decision, or rewriting predecessor/source immutable lifecycle history.
- Apply the existing relationship interpretation, temporal graph admission, basis, cycle-safety, both-endpoint version, expected-version, transactional revalidation, idempotency, and atomic persistence contracts.
- Preserve admitted relationship truth across later endpoint lifecycle correction; any later relationship-semantic change remains explicit relationship correction.

## Acceptance criteria

- [ ] A valid late omitted-lineage assertion attaches `RENEWED_FROM` to the already-established source Decision/Need rather than allocating replacement identities.
- [ ] The command requires and preserves an explicit typed renewal relationship basis, known Actor Attribution where required, Trigger Provenance, optional Technical Provenance, effective time, and OperationId.
- [ ] Historical admission proves each predecessor's supported substantive/external resolution at both the new judgment-episode start and the relationship effective instant.
- [ ] The relationship cannot predate the source judgment episode.
- [ ] Source and predecessor Decision/Need identities, lifecycle dispositions, work history, and immutable facts remain unchanged; ordinary resolved Decisions are never reopened.
- [ ] Invalid/unsupported/contested/incomplete historical admission, invalid basis, cycle/indeterminate-cycle safety, stale endpoint or material non-endpoint predicate, idempotency conflict, or persistence failure commits nothing.
- [ ] Expected versions are enforced for directly touched pre-existing endpoints while all material histories/paths/future/absence predicates are revalidated through atomic commit.
- [ ] Relationship-only version consequences follow the frozen both-endpoint support-sensitive contract without lifecycle-sequence mutation.
- [ ] Later endpoint lifecycle correction does not silently rewrite the admitted renewal relationship.
- [ ] Exact same-operation/same-request replay appends nothing; changed-request OperationId reuse conflicts.
- [ ] Deterministic tests cover valid late attachment, identity/history preservation, both historical admission boundaries, invalid/contested cases, graph safety, stale predicates, replay/conflict, version effects, and persistence atomicity.

## Verification obligations

- Independently re-read and prove `ARCHSRC-2` against the final renewal/application/relationship/persistence behavior.
- Prove the late-attachment path remains distinct from ordinary new-identity renewal and does not broaden `RENEWED_FROM` beyond the cited architecture.
- After the remediation set closes, fresh `$verify-spec` must independently validate the reconciled Architecture/Design Obligation Manifest and repaired exact `spec-279` HEAD before `$review-spec` is rerun; downstream Spec lifecycle work is not this ticket's closure prerequisite.

## Preservation obligations

- Existing ordinary renewal still creates a new Decision Need and Decision through normal continuity arbitration when renewed judgment itself is new.
- Existing atomic `RENEWED_FROM` establishment during ordinary renewal remains unchanged.
- Predecessor/source lifecycle truth and immutable history remain unchanged.
- Relationship basis-role separation, historical admission, temporal interpretation, both-endpoint version protection, mixed-lineage graph safety, idempotency, and persistence-failure semantics remain intact.
- Current `RENEWED_FROM`/`SUPERSEDES` contracts gain no speculative `PRIOR_DECISION_CONTEXT` payload and no generic graph framework is introduced.

## Root-complete sweep required for closure

- Reconcile DD-2 to `ARCHSRC-2` and this ticket.
- Generate/inspect/disposition the complete late omitted-renewal-lineage obligation and the preserved ordinary new-identity renewal boundary.
- Missing architecture obligations 0; ambiguous 0; implementation architecture obligations without ticket coverage 0; unchecked 0.

## Blocked by

None — can start immediately.

## Ticket branch

`spec-279`

## Ticket baseline

`Pending`

**Required issue label/status after publication:** `ready-for-agent`
