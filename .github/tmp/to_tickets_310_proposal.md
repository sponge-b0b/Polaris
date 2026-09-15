# Certified-candidate remediation proposal — Spec Review #310

Source artifact: Spec Review #310 — Spec Review: Implement Investment Decision application lifecycle and Decision Memory queries  
Parent Spec: #279 — Spec: Implement Investment Decision application lifecycle and Decision Memory queries  
Ticket mode: remediation  
Source branch: `spec-279`  
Source candidate HEAD: `9081386b8fcbf65e117fdac6c7b8c776edaef8f0`  
Parent Spec baseline: `4daed9034891600597a47c01b6c39d5ebd9914ca`  
Spec Body Hash: `5f59ee666c65e9e93fe3b69403dbf4bc5328332d14d6339fc55b067755e4eb17`  
Spec Contract Hash: `3044b039742306f1c0ed10085479c7c823ed463443e8d11d761f45de564fb334`  
Canonical finding ledger: Spec Review #310 comment `5662220111`  
Canonical decomposition-defect record: Spec Review #310 comment `5663250943`

## Publication actions

Create exactly four new Review Remediation Tickets. Do not update, reopen, or rewrite any closed ticket. Do not close any open ticket as superseded. Do not add native blocking edges among the four new tickets.

For every new ticket:
- native GitHub parent: Spec Review #310;
- lifecycle/branch provenance: Parent Spec #279;
- `Ticket branch`: `spec-279`;
- `Ticket baseline`: `Pending`;
- initial label/status: `ready-for-agent`;
- Project-field mutation: none in this workflow.

---

# Ticket T1 — Define application-owned command-side read failure semantics

**Exact proposed issue body:**

## Parent

Remediation parent: Spec Review #310  
Parent Spec: #279

## Spec obligations

ID-24, ID-26, TD-21

## Root blocker

RB-2 — Command-side persistence reads must expose a technology-neutral application-owned persistence-failure contract so raw infrastructure failures cannot escape the application boundary.

## Architecture obligations

None

## Architecture context

Application-owned Decisions command boundary governed by Spec #279 ID-24, ID-26, TD-21; `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §16; `docs/proposed/durable-persistence-investment-decision-history.md` §§2 and 16; accepted ADRs 0001–0003. All architecture and material design decisions currently required by this ticket are accepted; no known implementation-readiness blocker remains unresolved.

## What to build

- Define an explicit technology-neutral application-owned failure contract for every command-side receipt, candidate, Decision-state, and relationship read port used by Decision commands.
- Make ordinary-work and relationship command services translate only that inward failure contract into the established application `PersistenceUnavailable` outcome (or the exact established equivalent), rather than allowing raw infrastructure read exceptions to escape.
- Preserve `None`/not-found as semantically distinct from persistence unavailability and preserve lifecycle, relationship, concurrency, continuity, and idempotency outcomes as separate families.
- Keep database/vendor/adapter exception translation adapter-owned; do not add an arbitrary broad application catch.

## Acceptance criteria

- [ ] Every affected command-side read method exposes an explicit technology-neutral application-owned persistence-failure contract.
- [ ] Receipt, continuity-candidate, Decision-state, and relationship reads distinguish persistence unavailability from `None`/not-found.
- [ ] Ordinary-work command-side reads cannot leak raw infrastructure exceptions through the application boundary.
- [ ] Relationship command-side reads cannot leak raw infrastructure exceptions through the application boundary.
- [ ] Persistence unavailability remains distinct from lifecycle, relationship, expected-version/concurrency, continuity, and idempotency outcomes.
- [ ] Focused async-capable tests prove read-side unavailability, semantic distinctions, and no partial mutation or receipt on failed reads.
- [ ] Concrete adapter/database exception translation remains outside inward application contracts; no unrelated failures are swallowed by a broad catch.

## Verification obligations

- Sweep every affected command-side read port and every ordinary-work/relationship command consumer for raw read-exception leakage.
- Prove adapter-specific failure translation remains adapter-owned.
- Prove RB-2's complete two-cell active acceptance universe closes with missing 0, unproven 0, and unchecked 0.
- After the remediation set closes, fresh `$verify-spec` must certify the repaired exact `spec-279` HEAD before `$review-spec` is rerun; that is downstream Spec lifecycle work, not this ticket's closure prerequisite.

## Preservation obligations

- None — RB-2 currently contains no satisfied same-root acceptance cell. Existing typed commit unavailability, replay/idempotency, expected-version/CAS, continuity, lifecycle, relationship, and not-found behavior remain explicit acceptance-preservation constraints above.

## Root-complete sweep required for closure

- Generate, inspect, and disposition both RB-2 active cells: command-side read-port failure contract; ordinary-work/relationship command read translation.
- Missing 0; violated 0; unproven 0; unchecked 0.
- Preserve all adjacent typed commit and semantic failure families.

## Blocked by

None — can start immediately.

## Ticket branch

`spec-279`

## Ticket baseline

`Pending`

**Required issue label/status after publication:** `ready-for-agent`

---

# Ticket T2 — Translate relationship construction failures at the application boundary

**Exact proposed issue body:**

## Parent

Remediation parent: Spec Review #310  
Parent Spec: #279

## Spec obligations

ID-26, TD-21

## Root blocker

RB-3 — Relationship-construction domain failures must cross the application-owned relationship error-translation boundary rather than leaking raw domain exceptions.

## Architecture obligations

None

## Architecture context

Application relationship orchestration governed by Spec #279 ID-26 and TD-21; `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §16; `docs/proposed/durable-persistence-investment-decision-history.md` §16; and the synchronized Decision relationship contract. All architecture and material design decisions currently required by this ticket are accepted; no known implementation-readiness blocker remains unresolved.

## What to build

- Put renewal relationship-fact construction inside the established application relationship-error translation boundary.
- Put Supersession relationship-fact construction inside that same boundary.
- Put privileged relationship-correction construction inside that same boundary.
- Translate only the established relationship-domain error family into the established semantic application outcomes; do not add an arbitrary broad `Exception` catch.
- Preserve relationship admission, correction, cycle/history, concurrency, idempotency, persistence, and atomic transaction semantics.

## Acceptance criteria

- [ ] Renewal relationship construction failures cross the application translation boundary.
- [ ] Supersession relationship construction failures cross the application translation boundary.
- [ ] Relationship-correction construction failures cross the application translation boundary.
- [ ] Definite cycle failures remain the established cycle outcome; possible-cycle-under-contest remains the established indeterminate-cycle-safety outcome.
- [ ] Invalid/incomplete relationship ancestry/history remains the established history-invalid/incomplete outcome.
- [ ] Other covered relationship construction failures remain typed relationship conflict/specific established outcomes rather than raw domain exceptions.
- [ ] No arbitrary broad catch masks unrelated failures.
- [ ] Valid relationship behavior, atomicity, replay/idempotency, expected-version/concurrency, and persistence behavior remain intact.
- [ ] Focused tests exercise constructor failures for renewal, Supersession, and relationship correction.

## Verification obligations

- Prove no covered relationship-domain constructor exception escapes renewal, Supersession, or correction application paths.
- Prove RB-3's complete two-cell active acceptance universe closes with missing 0, unproven 0, and unchecked 0.
- After the remediation set closes, fresh `$verify-spec` must certify the repaired exact `spec-279` HEAD before `$review-spec` is rerun; that is downstream Spec lifecycle work, not this ticket's closure prerequisite.

## Preservation obligations

- None — RB-3 currently contains no satisfied same-root acceptance cell. Existing relationship admission, cycle/history typing, atomicity, idempotency, concurrency, and persistence outcomes remain explicit acceptance-preservation constraints above.

## Root-complete sweep required for closure

- Generate, inspect, and disposition both RB-3 active cells: renewal/Supersession construction translation; relationship-correction construction translation.
- Missing 0; violated 0; unproven 0; unchecked 0.
- Preserve the established typed relationship error universe and adjacent success paths.

## Blocked by

None — can start immediately.

## Ticket branch

`spec-279`

## Ticket baseline

`Pending`

**Required issue label/status after publication:** `ready-for-agent`

---

# Ticket T3 — Add atomic multi-relationship correction coordination

**Exact proposed issue body:**

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

---

# Ticket T4 — Attach omitted renewal lineage to existing Decisions

**Exact proposed issue body:**

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

---

# Coverage and transition accounting

## Root Delta Coverage

Active unresolved Root Blocker cells: 4  
Root delta rows: 4

- RB-2 / command-side read-port failure contract / open → remediation → T1.
- RB-2 / ordinary-work and relationship command reads / open → remediation → T1.
- RB-3 / renewal and Supersession relationship construction / open → remediation → T2.
- RB-3 / relationship-correction construction / open → remediation → T2.

Missing cells: 0  
Unknown cells: 0  
Unclassified obligation types: 0  
Required remediation without active ticket coverage: 0  
Satisfied same-root cells omitted from preservation: 0  
Rows without reason/authority: 0

## Decomposition Defect Reconciliation

Confirmed decomposition defects supplied: 2  
Decomposition defects dispositioned: 2

- DD-1 / RF-3 → confirmed-decomposition-defect → ARCHSRC-1 → T3.
- DD-2 / RF-4 → confirmed-decomposition-defect → ARCHSRC-2 → T4.

Unmapped decomposition defects: 0  
Ambiguous decomposition destinations: 0  
Architecture obligations without active ticket/authorized non-ticket destination: 0

## Architecture / Design Obligation Disposition Manifest

Bounded source units: 6  
Material non-duplicated architecture obligations: 2  
Architecture disposition rows: 2

### ARCHSRC-1

- Source: `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §§12–13 and §17; `docs/proposed/investment-decisions-decision-relationship-model.md` §5.4; `docs/proposed/durable-persistence-investment-decision-history.md` §5 transaction boundary and §8 relationship persistence/reconstruction.
- Requirement: accept and validate one complete explicitly supplied atomic relationship-correction set capable of repairing several relationships together; validate the complete final history and commit every requested correction atomically without an intermediate public graph state.
- Spec-cell reference: None — this cardinality/final-history repair obligation is not fully represented by a direct 122-cell Spec Contract cell.
- Disposition: implementation-ticket → T3.

### ARCHSRC-2

- Source: `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §11 and §17; `docs/proposed/investment-decisions-decision-relationship-model.md` §2.1 and §6.8; `docs/proposed/durable-persistence-investment-decision-history.md` §8.
- Requirement: support later attributable attachment of genuinely omitted renewal lineage to an already-established source Decision/Need only when the same historical admission predicates and explicit renewal relationship basis are proven, without recreating/reopening identity or rewriting immutable history.
- Spec-cell reference: None — this existing-identity late-attachment path is not fully represented by a direct 122-cell Spec Contract cell.
- Disposition: implementation-ticket → T4.

Unmapped architecture obligations: 0  
Ambiguous architecture obligations: 0  
Implementation architecture obligations without ticket coverage: 0  
Deferred obligations without durable existing owner: 0

All other materially governing architecture/design constraints for T1–T4 are already completely represented by their cited Spec contract cells, Root Blocker acceptance cells, or explicit preservation constraints; no additional non-duplicated `ARCHSRC-*` implementation obligation is created.

## Parent Spec Contract Coverage Reconciliation

Exact parent Spec contract: 122 cells.

- Original 118 US/ID/TD/OOS cells remain dispositioned by the historical #301–#306 implementation lineage except the following active remediation additions:
  - ID-24 → existing lineage + T1.
  - ID-26 → existing lineage + T1 + T2.
  - TD-21 → existing lineage + T1 + T2.
- NORM-1 → existing #301–#306 implementation lineage; no separate new implementation ticket is required beyond the active direct-cell remediation above.
- NORM-2 → existing #301 initiation/continuity implementation lineage.
- NORM-3 → existing #301–#306 implementation lineage; prerequisite #278 is closed.
- NORM-4 → no-implementation-work: #278 is closed and `spec-279` has fixed Spec baseline `4daed9034891600597a47c01b6c39d5ebd9914ca`.
- OOS-1..OOS-12 remain authoritative exclusions exactly as stated by Spec #279.

Spec contract cells: 122  
Disposition rows: 122  
Mapped/dispositioned: 122  
Unmapped cells: 0  
Ambiguous cells: 0  
Unclassified cells: 0  
Implementation cells without ticket coverage: 0  
Non-ticket dispositions without reason/authority: 0  
Material design choices delegated to implementation: 0

## Attention transition gate

- HIGH — the historical Ticket Coverage Manifest lacks the current 122-cell/NORM accounting and any Architecture/Design Obligation Disposition Manifest. Disposition: supersede/reconcile the parent coverage artifact only after this proposal is approved and the four tickets are published; mapped to parent coverage reconciliation + ARCHSRC-1/2.
- HIGH — DD-1 and DD-2 are real architecture/design decomposition gaps, not missing Spec cells. Disposition: preserve them as DD/ARCHSRC provenance and route forward to T3/T4; do not fabricate new Spec cells.
- HIGH — closed #305 is historical evidence and must not be reopened/re-written. Disposition: forward-only T3/T4 remediation.
- MEDIUM — the interrupted Codex proposal/certifier state was bound to a stale local/product checkpoint and cannot authorize publication. Disposition: this candidate is newly frozen against `spec-279@9081386b8fcbf65e117fdac6c7b8c776edaef8f0`.
- MEDIUM — shared implementation files are not a semantic dependency. Disposition: no native blocking edges among T1–T4.
- LOW — current cited sources determine the required contracts; unresolved material design choices delegated to implementation: 0.

Unresolved design-gap findings: 0

## Proposal mutation summary

New tickets: T1, T2, T3, T4  
Update open tickets: None  
Close as superseded: None  
Dependency changes: None  
Closed tickets reopened/rewritten: 0  
Native parent for all new tickets: Spec Review #310  
Branch for all new tickets: `spec-279`  
Baseline for all new tickets: `Pending`  
Initial label/status for all new tickets: `ready-for-agent`
