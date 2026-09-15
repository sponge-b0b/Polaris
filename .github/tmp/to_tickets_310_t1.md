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
