---
status: accepted
ccl_proposal: sha256:250672ecda3bc8a4bc15500f0c203409b18acdf813bf2cb8ba2f87341ea643d7
ccl_transaction: contracts/ccl/transactions/250672ecda3bc8a4bc15500f0c203409b18acdf813bf2cb8ba2f87341ea643d7.json
---

# Resolve overlapping future-effective Investment Intelligence corrections

## Context

Investment Intelligence target judgments and complete claim catalogs use append-only
corrections, owner-issued current versions, and historical `(T,K)` interpretation.
A future-effective correction can be recorded while the earlier assertion remains
current. A later immediate correction before activation leaves two known acts
that would overlap at the future boundary. Prior accepted contracts require a
complete temporal-cause witness but do not say which act governs. This gap
blocks Spec #358 ticket #399: different answers change target and claim meaning,
Evidence support, and dependent-write results.

## Decision

<!-- ccl-decision:v1 -->
The normative semantic contract for this ADR is the typed CCL projection below.
Display summaries are explanatory and non-authoritative.

CCL transaction: `contracts/ccl/transactions/250672ecda3bc8a4bc15500f0c203409b18acdf813bf2cb8ba2f87341ea643d7.json`

# R3 Investment Intelligence Judgments

Contract: investment-intelligence.r3-judgments@2
Owner: investment-intelligence
Operation: revise

Summary (non-authoritative)

Durable material judgments, versioned target-owned claims, Recommendation history, and exact Evidence-basis consumption.

Typed contract

- `alternative.minimum-set` — decision_alternative: required invariant — For the first R3 SPY slice, the minimum economic alternatives are increase exposure, hold current exposure or deliberate no-action, and reduce exposure. This contract does not predefine Portfolio/Risk consequence payloads owned by Portfolio & Risk.
- `alternative.persistence` — decision_alternative: required invariant — Only Decision Alternatives that materially participate in comparison or later inform a Human Investment Decision need durable representation; transient brainstorming alternatives are not durable.
- `alternative.root-revision` — decision_alternative_context: required invariant — Materially selected DecisionAlternativeId context facts expose owner-issued positive root-local revisions. Correction, retraction, restoration, contestation, or relationship change advances the root only when current content, applicability, support/provenance, or validity changes; a new alternative receives a new root. Protect a current-selection/absence guard when selection matters, and do not stale an exact-root read merely because a later alternative or judgment exists.
- `basis.capture` — investment_judgment_formation: required invariant — When judgment formation consumes a current Evidence result, preserve its exact CurrentEvidenceBasis; never silently substitute newer support.
- `challenge.disposition` — meaningful_challenge_result.disposition: vocabulary is closed; members: INCONCLUSIVE, QUALIFIED, REJECTED, SURVIVES_CHALLENGE.
- `challenge.material` — meaningful_challenge_result: required invariant — Every View used to support a consequential Recommendation has a durable substantive challenge result. Preserve the strongest credible alternative explanation or competing material interpretation actually considered, material Conflicting Evidence, challenged assumptions or uncertainty or invalidation conditions, and the material basis for the disposition. A challenged=true flag alone is insufficient. No fixed model count, debate topology, or agent arrangement is required.
- `challenge.persistence` — meaningful_challenge_result: persistence is durable.
- `hypothesis.persistence` — investment_hypothesis: required invariant — An Investment Hypothesis is durable only when it materially shapes a View, challenge, Recommendation, or later Decision Evaluation; transient hypotheses remain reasoning-local.
- `model.output-boundary` — model_provider_output.canonical-business-judgment: forbidden.
- `recommendation.current-support` — current_recommendation_support: persistence is derived.
- `recommendation.disposition` — investment_recommendation.preferred_economic_disposition: vocabulary is closed; members: HOLD, INCREASE, REDUCE.
- `recommendation.history` — investment_recommendation: history is append-only.
- `recommendation.human-boundary` — investment_recommendation.human-decision-approval-admissibility-action-intent-order-execution-authority: forbidden.
- `recommendation.material-basis` — investment_recommendation: required invariant — A durable Recommendation preserves its governing Investment Decision, formation time, explicit Investment Horizon, preferred economic disposition, materially relied-upon View(s), materially considered Decision Alternatives, material Evidence bindings, substantive challenge result(s), material Investment Uncertainty, Portfolio/Risk consequence references supplied by #352, and material assumptions, invalidation conditions, or Review Condition references where applicable. Proposed Action references are preserved only when a concrete candidate implementation is actually needed.
- `recommendation.no-reactivation` — investment_recommendation: required invariant — Evidence refresh alone does not create a new Recommendation. A new attributable preference appends a new Recommendation even when its disposition repeats. A later Recommendation never rewrites an earlier one; an unsupported newer Recommendation does not reactivate an older one. Current support is derived from durable history, Decision applicability, and current Evidence/Risk fitness; no mutable authoritative current flag is the source of truth.
- `recommendation.persistence` — investment_recommendation: persistence is durable.
- `slice.scope` — r3_investment_decision: required invariant — The first supported R3 slice covers one Portfolio; SPY is its only investable instrument and cash is represented only as Portfolio State. The user-initiated Investment Decision chooses increase, hold, or reduce SPY exposure over one explicit Investment Horizon. Canonical contracts remain instrument-identity based rather than hard-coded to SPY.
- `target.claim-catalog` — investment_intelligence_evidence_target: required invariant — Each of the five admitted Investment Intelligence target families owns a complete versioned claim catalog. ClaimId is application-allocated opaque UUIDv4 identity meaningful only with the typed target. ClaimCatalogVersion is a positive target-local integer beginning at 1 and advances once for a committed change to current claim membership, proposition meaning, or surviving support; historical catalogs remain reconstructable. Retain a ClaimId only for the same evidentiary proposition within one root; materially changed proposition/scope and new, reassessed, or superseding roots receive fresh ClaimIds. Narrative text is never inferred into claims.
- `target.correction-overlap-admission` — investment_intelligence_evidence_target: required invariant — For the same target root, the target assertion and complete claim catalog are distinct correction lanes. Each immutable owner correction act has an opaque owner-issued act reference typed by target family and root, distinct from JudgmentRevision and ClaimCatalogVersion, plus attribution, basis, effective/recorded/known boundaries, affected lane(s), and complete same-root correction ancestry. At atomic admission, an act changing a lane must explicitly resolve every already-known pending future-effective act whose effect would overlap on that lane: either supersede/cancel that pending act, or retain it as the scheduled successor and expressly bound the new act as interim until the retained act's effective boundary. A multi-lane act resolves each affected lane in the same commit. Validate the complete post-commit known effective timeline at all relevant boundaries; every lane has a determinate selected interpretation or an explicit owner-contested interpretation. An unresolved overlap, missing ancestry, or implicit precedence is rejected without commit. Recorded recency, effective-time recency, UUID/database order, and owner-version order never choose a winner.
- `target.correction-overlap-temporal` — investment_intelligence_evidence_target: required invariant — Reconstruct each target and complete claim-catalog lane at (effective_at=T, known_at=K) only from acts known by K and effective by T, their explicit ancestry/supersession and interval bounds, never from later knowledge. In the A/B/C overlap, future B recorded at K1 leaves A current before T3; immediate C recorded at K2<T3 is inadmissible without explicit B resolution. If C cancels B, C governs from K2 through T3 and later until another lawful change. If C retains B as scheduled successor, C governs only from K2 until T3 and B governs beginning T3. Reads with K before K2 preserve the then-known B schedule. The same rule governs complete catalog membership, proposition meaning, and surviving support; original and defeated acts remain inspectable.
- `target.correction-overlap-version-basis` — investment_intelligence_evidence_target: required invariant — A valid future-only B append at K1 advances neither current owner version. A C commit at K2 advances JudgmentRevision once iff current target assertion, support/provenance, validity, or applicability changes, and ClaimCatalogVersion once iff current catalog membership, proposition meaning, or surviving support changes; advance both when both change. Clock activation of retained B at T3 creates no synthetic owner commit or version advance. Complete owner-attested temporal-cause witnesses bind typed root, act references, both version histories, exact (T,K) boundary, owner provenance, selected/pending/defeated ancestry, explicit overlap resolution, interval and effective/recorded/known history, and applicable selection/absence guards. A lawful material same-version target change maps to TARGET_CHANGED and claim change to CLAIM_CHANGED, with both when independently applicable; broken protected ancestry/selection/absence guards add NEGATIVE_PREDICATE_BROKEN. A still-future or canceled B with unchanged exact-key meaning causes no stale result. Missing/incomplete/contested meaning returns its distinct no-basis result; contradictory or unexplained owner history is INVALID_HISTORY. Application validates owner proof and never infers precedence, fabricates a version, or adds a stale category.
- `target.judgment-revision` — investment_intelligence_evidence_target: required invariant — For the five admitted target families—Investment Hypothesis, Investment View, meaningful-challenge result, Investment Recommendation, and Recommendation-withholding judgment—the owning domain issues an opaque root ID and positive root-local JudgmentRevision beginning at 1. Advance once per owner commit changing current interpreted assertion, support/provenance, validity, or applicability. Same-judgment correction retains the root; a new, reassessed, or superseding judgment receives a new root. Expose historical (T,K) support and withdrawn, contested, or invalid current interpretation; protect ClaimCatalogVersion separately.
- `target.version-contract` — investment_intelligence_evidence_target: required invariant — The inward application contract exposes the authoritative target revision and ClaimCatalogVersion needed by Evidence admission, historical reconstruction, and command-basis revalidation.
- `temporal.owner-attestation` — investment_intelligence_temporal_owner: required invariant — For exact reads and fresh trusted T=K commit revalidation, an Intelligence owner whose same-revision as-of meaning may change attests the complete typed historical meaning and verifiable temporal cause for the exact identity, revision, basis key, read boundary, provenance, fact/correction ancestry, effective/recorded history, and selection/absence history. Application validates owner proof and never infers lawful cause from two changed views or elapsed time.
- `transaction.revalidation` — investment_judgment_commit: required invariant — External/model work remains outside store transactions. Before commit, re-resolve and atomically revalidate the complete material Decision, target, claim, requirement, Evidence-support, context, and time-sensitive basis; return typed StaleEvidenceBasis or a distinct no-basis outcome without silently rebasing or committing the judgment. The ordinary-work gate for the governing Decision remains independent and can still forbid the dependent write.
- `view.material-content` — investment_view: required invariant — A materially relied-upon Investment View is an attributable, time-specific first-class judgment with opaque identity. Preserve formation time, Investment Horizon, material Evidence bindings, assumptions, uncertainty, material alternative explanation or dissent, invalidation conditions, and materially used Signal provenance where applicable. A materially new View appends rather than overwrites an earlier View.

Semantic proposal hash: sha256:250672ecda3bc8a4bc15500f0c203409b18acdf813bf2cb8ba2f87341ea643d7
<!-- /ccl-decision:v1 -->

## Rationale

The owner must state how an immediate correction interacts with every known
pending act on the affected target or catalog lane. Explicit cancellation and
an expressly interim correction preserve both intended outcomes. Validating the
known effective timeline at admission prevents a later clock crossing from
silently reversing owner intent. Complete ancestry and interval proof let
historical reads retain the knowledge available at each cutoff and let
Application distinguish lawful same-version drift from invalid history.

## Considered Options

Recorded-recency precedence would silently cancel a scheduled act. Effective-
recency precedence would allow a scheduled act to displace a later intended
lasting correction. Treating every overlap as contested would prevent the
owner from recording a deliberate interim correction or cancellation. The
chosen explicit resolution carries more admission and witness work, but
preserves attributable owner intent without adding a version on clock passage
or another public stale category.
