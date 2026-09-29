---
status: accepted
---

# Complete R3 claim, requirement, and current-support basis semantics

## Context

ADR 0012 fixed R3 Evidence identities, typed judgment bindings, claim-specific
scope, requirement-aware freshness and sufficiency, and current-support version
revalidation. Preparing the decision for implementation exposed three coupled
omissions inside that contract:

1. `ClaimId` had no target-owned production, continuity, or historical-membership
   lifecycle;
2. Freshness and sufficiency requirements had no canonical authority, identity,
   applicability, or append-only version history; and
3. the promised Decision, judgment, and Evidence-set revalidation did not define
   the protected universe or its negative predicates.

Those omissions permit materially incompatible public, persistence, temporal, and
concurrency behavior. This ADR extends ADR 0012 without reopening its accepted
Evidence identities, target union, role/use vocabulary, correction algebra,
reconstruction outcomes, or anti-hindsight rules.

## Decision

### Target-owned claims

All ten judgment families admitted by `EvidenceJudgmentRef` may expose zero or more
explicit material claims. A target declares a separate claim whenever Evidence
role, availability, freshness, sufficiency, or contestation can differ for that
proposition. Narrative text is never inferred into claims, and judgment-wide scope
is valid only when the relationship truly applies to the whole target.

`ClaimId` is an application-allocated opaque UUIDv4 dependent identity. Its public
identity is the typed pair `(EvidenceJudgmentRef, ClaimId)`; `ClaimId` alone has no
meaning. The target domain owns and persists a complete claim catalog rather than
delegating claims to a generic Claim or Evidence table.

Each target root has a positive `ClaimCatalogVersion` starting at 1. It advances
once for a committed operation that changes current claim membership, proposition
meaning, or surviving support. Target owners retain versioned historical catalogs.

At target formation, every independently Evidence-addressable material proposition
gets a fresh `ClaimId`. Within the same target root, a correction that preserves the
same evidentiary proposition retains the ID; a material proposition or scope change
gets a fresh ID and leaves the predecessor non-current but historical. A new
judgment root, reassessment, or superseding target always receives fresh claim IDs;
claim IDs never migrate automatically across target roots.

Retraction makes target claims non-current from the applicable
`(effective_at, known_at)` boundary without deleting historical membership.
Supersession does not rewrite old claims or Evidence bindings. A historical binding
remains valid when its claim belonged to the target at the binding's historical
boundary; current support may count only currently supported target and claim
membership. Evidence binding endpoints remain immutable.

Append admission and reconstruction validate membership against the target owner's
authoritative catalog at `(T,K)`. Public outcomes distinguish:

- target or claim not known at the cutoff;
- target or claim not yet effective;
- claim not current for a live command;
- invalid or wrong-target claim reference;
- contested claim history; and
- invalid or incomplete claim history.

A command basis protects both the target-owner version and `ClaimCatalogVersion`.
Physical storage, foreign-key, and locking mechanics are private only when typed
target ownership and atomic validation remain exact.

### Requirement authority and version history

Freshness and sufficiency definitions are independently addressable immutable
product-configuration facts. The Configuration boundary owns them through an
inward Evidence-requirements contract. Evidence owns applicability resolution,
deterministic evaluation, and persisted results; it cannot silently invent or
change requirements.

The public identities are application-allocated opaque UUIDv4 values:

- `EvidenceRequirementSetId` for one continuing logical set;
- `EvidenceRequirementSetVersionId` for one immutable complete version; and
- dependent `EvidenceRequirementId`, whose identity is the pair
  `(EvidenceRequirementSetId, EvidenceRequirementId)`.

A set version preserves attributable configuration authority and source,
`effective_at`, `recorded_at`, a typed applicability assignment, and complete
requirement definitions. UUID, insertion, and recording order never select
authority.

Applicability is explicit over the supported R3 coordinates that can change
meaning: target judgment family, scope kind and exact target/`ClaimId` when
specifically assigned, Evidence use, canonical Evidence subject/reference family,
`PortfolioId`, instrument identity, and `InvestmentHorizon` where applicable. It
uses typed domain values rather than free-form discriminators or a generic rule
graph. Application resolves exactly one applicable set version for the authoritative
typed key at `(T,K)`.

Every new version appends with exactly one typed predecessor effect:

- `CORRECTS` records a newly known correction to the same authority; or
- `SUPERSEDES` records a prospective replacement.

The version graph is acyclic. `EvidenceRequirementId` continues only while its
semantic predicate is unchanged; changed meaning receives a fresh ID. Correction
or supersession never rewrites an earlier binding or assessment and never selects
truth merely by recency. Zero applicable versions is missing authority, multiple
incomparable applicable versions are contested authority, and invalid ancestry is
invalid requirement history.

An Evidence binding persists the exact set-version and requirement reference plus
the evaluation basis used for freshness. At most one freshness requirement may
apply to an exact binding applicability key. No applicable freshness requirement is
legal only as an explicit negative applicability witness against a successfully
resolved set version; missing, unavailable, or contested authority is not absence.

A sufficiency assessment persists its exact set version and a disposition for every
applicable material requirement. A changed version causes a new assessment root
under ADR 0012's reassessment rule. Historical assessments retain their original
requirement authority and version.

Missing or unavailable authority produces indeterminate freshness and sufficiency
plus incomplete or unavailable reconstruction. Contested authority produces
indeterminate results plus contested reconstruction. Invalid requirement history
produces the existing invalid/incomplete-history outcome. Deterministic consumers
fail closed. `NOT_APPLICABLE` is valid only when the resolved authoritative version
says so. External factual authority remains separate.

### Current-support basis and concurrency

Current Evidence support is protected at the exact
`BasisScopeKey = (InvestmentDecisionId, EvidenceJudgmentRef, scope, EvidenceUse)`.
It is neither global nor merely Decision-wide. A current-support query returns a
`CurrentEvidenceBasis` bound to its explicit read observation instant `T=K`.

The basis contains:

- typed `DecisionVersion`;
- the target owner's judgment and version reference;
- `ClaimCatalogVersion` for claim-specific scope;
- exact requirement-set version and applicability-assignment references;
- typed version references for canonical context facts that affected applicability
  or the result;
- `EvidenceSupportVersion` for the exact basis scope; and
- explicit negative predicates that materially influenced the result.

Encoding and hashing are private mechanics; this dependency set is the public
meaning.

`EvidenceSupportVersion` is a non-negative integer local to the exact
target/scope/use key; zero is the empty epoch. It advances once per atomic commit
when the current interpreted result or complete support/provenance changes at the
same recording boundary, including equivalent or support-only additions. A
future-only append that changes neither current result/support nor current history
validity need not advance it. Time passage and queries never advance a version.

Negative predicates protect exact absences relied upon by the result, including:

- no additional active eligible binding for the key or requirement;
- no current assessment or reassessment needed by the result;
- no competing applicable requirement assignment or version;
- expected claim membership or absence; and
- complete correction and succession ancestry for referenced lineages.

These are typed and scoped guards, not generic strings.

The basis is invalidated by a result-affecting change to any protected dependency,
including a binding append/revision/retraction; correction or succession of a
referenced observation; sufficiency assessment, reassessment, or correction;
target or claim-catalog change; requirement definition, assignment, or version;
availability or freshness basis; applicable canonical context; support-only state;
or a relied-upon absence. An unbound observation or a change outside the exact key
does not invalidate unless it enters one of those typed dependencies. Late-recorded
history effective by commit invalidates. Known future facts that do not affect the
current result still pass ancestry/history guards; facts outside the command's
current semantics do not create a stale result.

Commit obtains a new trusted observation instant, reconstructs and re-evaluates the
protected result at commit `T=K`, and atomically revalidates every version and
negative predicate in the same semantic transaction as the dependent judgment or
command write. This detects a freshness threshold crossed only through time.
Matching versions alone are insufficient. If authoritative cross-owner
revalidation cannot complete, the command does not commit.

A mismatch returns `StaleEvidenceBasis` with one or more typed categories:

- `DECISION_CHANGED`;
- `TARGET_CHANGED`;
- `CLAIM_CHANGED`;
- `REQUIREMENTS_CHANGED`;
- `EVIDENCE_SUPPORT_CHANGED`;
- `NEGATIVE_PREDICATE_BROKEN`; or
- `SUPPORT_CHANGED_BY_TIME`.

Invalid history and persistence/source unavailability remain the distinct ADR 0012
outcomes rather than becoming stale. Retry requires a fresh read; Polaris never
silently substitutes a newer basis.

## Rationale

Target-owned dependent claim identity preserves proposition-level Evidence meaning
without manufacturing a universal Claim entity. Immutable, attributable requirement
versions make freshness and sufficiency historically reconstructable without
treating current configuration as timeless authority. Exact support-basis versions
plus negative-predicate revalidation protect absence, support provenance, temporal
freshness, and cross-owner state that ordinary compare-and-swap versions cannot
prove.

This accepts bounded additional concurrency contention in exchange for a truthful
command basis. Implementations may optimize storage, hashes, locking, and query
organization without weakening the protected semantics.

## Considered Options

### Derive claims from text or reuse claim IDs across judgments

Rejected because inferred or migrated identity would make historical membership
unstable and silently transfer Evidence relationships to a different attributable
judgment.

### Embed unversioned rules in bindings or read current configuration

Rejected because later rule changes would rewrite historical freshness and
sufficiency and because missing authority could be mistaken for no requirement.

### Use one global Evidence version or endpoint versions alone

Rejected because a global token causes unrelated contention, while endpoint-only
versions cannot protect support-only changes, temporal re-evaluation, ancestry, or
relied-upon absence.
