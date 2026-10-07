---
status: accepted
---

# Complete R3 target and context version basis

## Context

ADRs 0012–0014 establish the R3 Evidence target, claim, requirement, correction,
sufficiency, and current-support contracts. ADR 0013 requires a target-owner
judgment/version reference and typed versions of canonical context facts that affect
an exact current Evidence basis. It does not define those references or the complete
R3 context family set. Distinct implementations could therefore accept different
stale commands while claiming to satisfy the same basis contract.

This decision completes that in-domain contract. It extends ADR 0013 without
changing its seven `StaleEvidenceBasis` categories or its other accepted rules.
The earlier proposal for an eighth `CONTEXT_CHANGED` category is rejected: the
existing `EVIDENCE_SUPPORT_CHANGED` category can truthfully describe a change to
the complete protected support basis when the exact changed typed reference is
returned with it.

## Decision

### Target-owner judgment versions

`TargetJudgmentVersionRef` is a closed typed union matching exactly the ten
`EvidenceJudgmentRef` families in ADR 0012: Investment Hypothesis, Investment
View, meaningful-challenge result, Projected Portfolio Consequence, Portfolio
Risk Assessment, Investment Recommendation, Recommendation-withholding judgment,
Human Investment Decision, Decision Evaluation, and Lesson. Each variant carries
the family-specific typed root identity and a positive root-local
`JudgmentRevision`. This pair is public and persistence-visible. The target owner
issues and preserves it; Evidence and Application do not synthesize it.

A root starts at revision 1 on formation. One atomic owner commit advances its
revision once when that root's current interpreted assertion, support/provenance,
validity, or applicability changes through correction, retraction, restoration,
contestation, or an explicit predecessor/successor effect. Revision is a current
support epoch, not a row count. Future-only or unrelated appends that do not
affect current interpretation, support, or history validity do not advance it.
A change caused solely by passage of time still requires commit-time
re-evaluation; no query or clock tick fabricates a revision. Historical `(T,K)`
reads use the owner assertion and correction support known at that boundary,
never the present-day revision retroactively.

Correction of the same attributable judgment keeps its root identity. A new
material judgment, reassessment, or superseding judgment has a new root and starts
at revision 1. It does not inherit claim identities or rewrite the predecessor.
A later root changes an earlier root's current basis only when an explicit owner
relationship changes that earlier root's applicability/support, advancing its
revision, or when the request depends on a current-judgment selection guard that
the later root breaks. Mere existence of a later judgment does not invalidate an
exact-root read. The target-root revision and `ClaimCatalogVersion` are separate:
claim membership, proposition, or support changes advance the catalog version;
the root revision advances only when its own assertion, support, or applicability
also changes. ADR 0013's claim identity and continuity rules remain in force.

Each target owner exposes the root/version and current versus withdrawn,
contested, or invalid interpretation at `T=K`. Missing, unavailable, contested,
or invalid owner history cannot produce a command-usable current basis.

### Canonical context versions

Only canonical facts that actually affect applicability, result, or complete
support/provenance for the exact `BasisScopeKey` contribute positive context
dependencies. Their version references form this closed, owner-specific typed
R3 union:

1. Decisions: `(InvestmentDecisionId, DecisionVersion)` for the governing or a
   materially used prior Decision's lifecycle, subject, scope, lineage, and
   relied-on Review/awaited-condition state.
2. Other admitted judgment facts: the corresponding typed
   `TargetJudgmentVersionRef`, when used as context rather than as the exact
   Evidence target.
3. Investment Intelligence: `(DecisionAlternativeId, positive root-local
   revision)` for a materially selected Decision Alternative.
4. Portfolio & Risk: `(PortfolioBoundaryId, revision)`,
   `(PortfolioStateId, revision)` for actual State,
   `(ProjectedPortfolioStateId, revision)`, `(InvestmentMandateId, revision)`,
   and `(InvestmentStrategyId, revision)`, when selected. The complete Mandate
   revision covers the applicable Investment Objective and Investment Principle
   membership, content, temporal applicability, and exact dependent member
   references; they are not invented as separate first-class identities for
   this basis.
5. Governance & Authority: `(InvestmentAuthorityRegimeId, revision)` when its
   current power/scope meaning affects the target.
6. Learning: `(OutcomeId, revision)` when retrospective context affects a
   Decision Evaluation or Lesson.

For each additional context fact root, revision begins at 1 and advances once
per owner commit changing its current interpreted content, applicability,
support/provenance, or validity through correction, retraction, restoration,
contestation, or relationship change. A new attributable fact or fresh as-of
Portfolio State has a new root identity. The owner keeps its version history and
provenance. Each ID and revision is typed to its owning family; no universal
context-fact identity or revision type replaces them. Immutable `PortfolioId`,
instrument identity, Investment Horizon, scope, and Evidence use remain typed
coordinates in the key or referenced owner fact. Changing a containing fact's
material coordinates changes its revision or
identity. External source/as-of provenance remains attached to its canonical
Portfolio State or Evidence fact.

ADR 0013's `DecisionVersion`, `ClaimCatalogVersion`, exact Configuration
requirement-set/version and assignment, scope-local `EvidenceSupportVersion`,
interpreted Evidence facts, and typed negative predicates remain separately
protected. A generic `(kind, id)` graph, global Evidence token, hash, or query
timestamp cannot replace the owner-specific references. R4/R5/R6-only facts and
presentation projections are outside this R3 basis.

A current-selection query also protects the exact typed relationship and absence
that selected one fact or no fact. A new current fact cannot hide behind an
unchanged version of the previously selected root. A context fact shown only in a
broader Decision Context view contributes no current-basis dependency when it
cannot affect this Evidence key; historical reconstruction still returns
applicable context separately. Future-only and out-of-key changes do not stale
the basis unless they enter a protected dependency.

### Assembly, failure, and stale categories

At one explicit current `T=K`, authoritative owners provide their exact typed
fact identities/versions, interpreted lineage and applicability coordinates, or
typed scoped absences, with provenance. Application returns the complete set used
to select the target, claim, requirement assignment, canonical context, and
Evidence result. It cannot infer versions from text or IDs, omit a used
dependency, or treat an unavailable, contested, or invalid owner read as absence.
The read attests to completeness of the selected family/relationship universe;
unknown membership or a missing required fact produces the applicable existing
incomplete, contested, unavailable, or invalid result without a command-usable
`CurrentEvidenceBasis`.

At dependent commit, Application obtains a fresh trusted `T=K`, re-resolves the
same positive and negative universe, and atomically compares typed references
and guards while re-evaluating temporal and Evidence support meaning with the
write. A mismatch returns `StaleEvidenceBasis` with one or more of exactly ADR
0013's seven categories, mapped by the dependency's role in this basis:

- `DECISION_CHANGED`: the requested governing Investment Decision's protected
  `DecisionVersion` changed.
- `TARGET_CHANGED`: the exact Evidence target's owner-issued judgment/version
  reference changed.
- `CLAIM_CHANGED`: the exact target's `ClaimCatalogVersion` or protected claim
  meaning changed.
- `REQUIREMENTS_CHANGED`: Configuration requirement-set/version or assignment
  authority changed.
- `EVIDENCE_SUPPORT_CHANGED`: the complete protected current Evidence support
  basis changed through the exact scope-local Evidence support epoch,
  interpreted Evidence facts/support, **or a positive canonical context-fact
  identity/version dependency** used in applicability, result, or complete
  support/provenance. The scope-local `EvidenceSupportVersion` need not change.
  A prior Decision or another judgment used only as context belongs here.
- `NEGATIVE_PREDICATE_BROKEN`: a relied-on typed absence, membership,
  uniqueness, ancestry, or current-selection guard broke.
- `SUPPORT_CHANGED_BY_TIME`: re-evaluation at commit changes support or
  freshness solely through time while stored positive references and guards
  remain unchanged.

The category is a description of the changed **complete basis**, not a claim
that an Evidence observation, its scope-local epoch, or final sufficiency result
necessarily changed. `StaleEvidenceBasis` also returns the exact typed changed
positive references and broken guards. If a replacement selected context fact
changes a positive dependency and breaks its selection guard, both
`EVIDENCE_SUPPORT_CHANGED` and `NEGATIVE_PREDICATE_BROKEN` apply. Independent
mismatches return all applicable categories; irrelevant displayed-only context
changes return none. Invalid history and persistence/source unavailability keep
their distinct ADR 0012 outcomes, append nothing, and require a fresh read
before retry. Cross-domain reads need not use one giant transaction, but
revalidation with the dependent write is atomic.

## Rationale

Typed owner versions make cross-domain dependencies explicit without assigning
their authority to Evidence or a generic graph. Root-local revision preserves
correction continuity while new judgments remain distinct. Complete positive
and negative dependency capture catches changed context, selection, temporal
fitness, and support provenance without unrelated global contention. Keeping
ADR 0013's seven categories preserves its public failure vocabulary while
typed changed-reference detail makes context-caused stale results precise.

## Considered Options

### Add `CONTEXT_CHANGED` as an eighth stale category

Rejected. ADR 0013 already admits positive canonical-context dependencies, and
`EVIDENCE_SUPPORT_CHANGED` is not restricted to an Evidence-owned version.
Defining it over the complete protected support basis represents context drift
truthfully without changing the closed public category vocabulary.

### Use one global context token or current snapshot

Rejected because it obscures owner identity, creates unrelated contention, and
cannot explain exact historical or stale dependencies.
