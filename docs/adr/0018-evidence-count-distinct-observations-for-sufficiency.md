---
status: accepted
ccl_proposal: sha256:24782fe4b8541b6f07a192300fd52b9abfd159057934fb308a15a121eb96dda1
ccl_transaction: contracts/ccl/transactions/24782fe4b8541b6f07a192300fd52b9abfd159057934fb308a15a121eb96dda1.json
---

# Count distinct observations for R3 Evidence sufficiency

## Context

The accepted CCL `evidence.r3-current-basis@1#requirement.evaluator`
counted eligible binding roots. Accepted ADR 0014 chose distinct Evidence
observation identities and explicitly rejected binding-root counting. The
completed Evidence assessment contract in #377 and its evaluator follow ADR
0014. Multiple bindings can reference the same observation, so the mismatch
changes whether a positive threshold is satisfied and what proof supports the
disposition. Wayfinder decision #417 reconciles this source conflict without
rewriting either historical authority.

## Decision

<!-- ccl-decision:v1 -->
The normative semantic contract for this ADR is the typed CCL projection below.
Display summaries are explanatory and non-authoritative.

CCL transaction: `contracts/ccl/transactions/24782fe4b8541b6f07a192300fd52b9abfd159057934fb308a15a121eb96dda1.json`

# R3 Evidence and Current Basis

Contract: evidence.r3-current-basis@2
Owner: evidence
Operation: revise

Summary (non-authoritative)

Durable judgment-relative Evidence, typed sufficiency, and complete current-basis semantics.

Typed contract

- `availability.vocabulary` — evidence_binding.judgment_time_availability: vocabulary is closed; members: AVAILABLE, UNKNOWN, UNAVAILABLE.
- `basis.atomic-commit` — current_evidence_basis: required invariant — A dependent write performs fresh trusted T=K reconstruction of the complete owner/Evidence universe and atomically validates prior/fresh typed witnesses against authoritative history. Return all independently applicable stale categories with exact typed changed references and broken guards. Stale or no-basis outcomes commit no dependent judgment and require a fresh read; never silently substitute newer support.
- `basis.complete` — current_evidence_basis: required invariant — CurrentEvidenceBasis protects the exact BasisScopeKey and the complete positive and negative dependency universe: Evidence support, typed target-owner revisions, claim-catalog versions, requirement versions, typed canonical-context versions, and selected-or-absent guards. A global epoch, untyped hash, timestamp, or partial owner view is not a substitute for complete typed dependencies and reconstructable history.
- `basis.stale-vocabulary` — stale_evidence_basis.category: vocabulary is closed; members: CLAIM_CHANGED, DECISION_CHANGED, EVIDENCE_SUPPORT_CHANGED, NEGATIVE_PREDICATE_BROKEN, REQUIREMENTS_CHANGED, SUPPORT_CHANGED_BY_TIME, TARGET_CHANGED.
- `basis.temporal-meaning` — current_evidence_basis: required invariant — At exact read and fresh trusted T=K revalidation, each materially used owner whose as-of meaning may change without a version advance attests complete typed meaning and verifiable temporal cause bound to exact identity/version/basis/read boundary/provenance and complete effective/recorded and correction ancestry, including applicable selection/absence history. Lawful governing Decision drift maps to DECISION_CHANGED; target-root drift to TARGET_CHANGED; claim drift to CLAIM_CHANGED; requirement drift to REQUIREMENTS_CHANGED; positive canonical-context or Evidence-support drift to EVIDENCE_SUPPORT_CHANGED with exact typed changed references; broken negative guards to NEGATIVE_PREDICATE_BROKEN; independent time-only fitness drift to SUPPORT_CHANGED_BY_TIME. Missing or incomplete meaning yields a distinct no-basis outcome; unexplained or contradictory same-version meaning is INVALID_HISTORY. Application never infers cause from elapsed time or a difference between two views; no synthetic clock version or eighth stale category is introduced.
- `binding.material-persistence` — evidence_binding: required invariant — Judgment-relative Evidence bindings durably preserve material Judgment-Time Availability, actual use, Evidence role, Freshness Requirement basis/result, and material qualifications. Evidence fitness is use-specific and distinct from availability, sufficiency, relevance, materiality, and authority.
- `claim.catalog` — evidence_judgment_target: required invariant — Each admitted EvidenceJudgmentRef family may expose zero or more explicitly declared material claims. A target declares a separate claim whenever Evidence role, availability, freshness, sufficiency, or contestation can differ for that proposition; judgment-wide scope is valid only when the relation truly applies to the whole target. Claim identity is the typed pair (EvidenceJudgmentRef, ClaimId); claims are target-owned, catalogs are complete/versioned, and narrative text is never inferred into claims.
- `context.assembly` — decision_context: required invariant — Decision Context is an assembled, time-specific historical view over canonical domain facts, not a separately authoritative persisted aggregate. The same underlying fact may participate in Decision Context and an Evidence role without becoming two facts. Historical reconstruction distinguishes what applied from what information was available to the particular judgment.
- `correction.history` — evidence_observation_correction: history is append-only.
- `freshness.vocabulary` — evidence_binding.historical_freshness: vocabulary is closed; members: FRESH, INDETERMINATE, STALE.
- `observation.material-persistence` — evidence_observation: required invariant — Material Evidence observations are durable first-class facts with opaque identity, attributable source provenance/authority, subject/reference identity, temporal provenance, and reconstructable retained representation/reference. Later information cannot become retroactively available to an earlier judgment.
- `requirement.authority` — evidence_sufficiency_requirement: required invariant — Configuration owns immutable requirement definitions and their version history; Evidence owns deterministic interpretation/evaluation of those definitions and their eligible support.
- `requirement.evaluator` — evidence_sufficiency_requirement: required invariant — A sufficiency requirement uses the executable MinimumEligibleEvidence(minimum_distinct_observations, qualifying_roles) predicate, not free-text meaning, caller-selected contributing bindings, or caller-authored dispositions. Evidence deterministically evaluates the complete eligible binding universe. Satisfaction and every lower or upper disposition bound count distinct EvidenceObservationId values: multiple eligible binding roots referencing one observation count once. Immutable proof preserves the counted observation identities and every qualifying contributor or deficiency-witness binding root with its interpreted EvidenceFactRef support.
- `requirement.negative-witness` — evidence_sufficiency_requirement: required invariant — NOT_APPLICABLE requires an authoritative Configuration-issued negative-applicability witness; missing, zero, stale, or unavailable bindings do not by themselves establish non-applicability.
- `sufficiency.vocabulary` — evidence_assessment.sufficiency: vocabulary is closed; members: INDETERMINATE, INSUFFICIENT, SUFFICIENT.

Semantic proposal hash: sha256:24782fe4b8541b6f07a192300fd52b9abfd159057934fb308a15a121eb96dda1
<!-- /ccl-decision:v1 -->


## Rationale

A binding records one judgment-relative use of an observation. Repeating that
use does not create another independent observation. Observation identity is
the count unit selected by ADR 0014; retaining every qualifying binding and
its interpreted fact support still shows precisely how the observation was
used and which deficiencies were considered. The CCL revision restores one
canonical semantic account for Configuration's typed minimum, Evidence's
evaluator, and immutable assessment proof.

## Considered Options

Retaining binding-root counting would allow two eligible uses of one
observation to meet a minimum of two. It would require replacing ADR 0014's
explicit choice and revisiting completed #377 semantics. The accepted choice
keeps the existing anti-duplication rule and makes the canonical CCL agree
with it.

## Consequences

The completed Evidence Spec #357 and open Portfolio & Risk Spec #359 must be
reconciled through their Spec lifecycle owner. Ticket #407 must consume the
updated Spec and ticket contracts before implementation resumes. The other
independent Wayfinder decision #416 remains open.
