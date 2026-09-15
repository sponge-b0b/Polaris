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
