---
status: accepted
---

# Attest temporal meaning in R3 current Evidence bases

## Context

ADRs 0013 and 0015 protect the exact current Evidence basis with owner-issued
versions, typed context dependencies, negative guards, and atomic revalidation.
An owner version advances for a material owner commit, not for passage of time.
R2 Decision lifecycle and relationship history can therefore change the
governing Decision's as-of applicability or work posture at a later trusted
`T=K` without changing `DecisionVersion`. Matching versions or two changed
views alone cannot distinguish that lawful transition from invalid unversioned
owner meaning. A simultaneous Evidence freshness threshold can change for an
independent reason.

This decision completes the bounded current-basis contract of ADRs 0013 and
0015. Their other decisions remain active, including exactly seven public
`StaleEvidenceBasis` categories and distinct invalid-history and unavailable
outcomes.

## Decision

### Owner-attested as-of meaning

At the exact read and at fresh trusted `T=K` revalidation, each authoritative
owner supplies a complete typed as-of interpretation and verifiable temporal
cause for any materially used meaning that can change without its protected
owner version. The witness binds the exact typed identity, version, basis key,
read boundary, owner provenance, and completeness. It covers the relevant
fact/correction ancestry, effective and recorded boundaries, and selected-or-
absent relationship guards. Complete owner history with deterministic
re-evaluation or an equivalent owner-attested proof may establish the cause;
changed view values or timestamps alone do not.

For the governing Investment Decision, this includes lifecycle interpretation
and support, work posture, applicability, and materially used lineage and
relationship meaning. The same requirement applies to the exact target,
claim membership, and materially used canonical context owners when their
accepted contracts permit as-of meaning to change without revision. Immutable
Configuration version content remains immutable. Application consumes owner
proof; it does not infer owner history or issue owner revisions. Passage of
time creates neither a synthetic version nor a synthetic fact.

### Fresh comparison and failure

At dependent commit, Application re-resolves the complete protected owner and
Evidence universe at fresh trusted `T=K` and validates the prior and fresh
owner witnesses against authoritative history in the same atomic validation
and write boundary. A same-version as-of difference is valid only when the
complete owner history and its effective, known, recorded, version, and
selection rules entail both interpretations. A later-recorded future-effective
fact can lawfully change meaning when it becomes operative without advancing
the version at that later instant. A valid future-only fact that still cannot
affect the exact key does not stale it, though its history validity is checked.

Unexplained or contradictory same-version owner meaning returns typed
`INVALID_HISTORY`. Missing, incomplete, contested, not-yet-effective, or
unavailable owner meaning returns its applicable distinct typed no-basis
outcome. None is converted to a stale category, inferred absence, or a
time-only change. A determinate changed governing Decision, including
`NON_OPERATIVE` applicability or changed work posture, is stale when a complete
fresh basis exists. The dependent command also enforces the separate Decisions
ordinary-work gate; a clean stale comparison never grants work authority.
Stale or no-basis retry requires a fresh read.

### Seven-category role mapping

Keep exactly ADR 0013's seven categories, with ADR 0015's role predicates
completed for attested as-of meaning:

- `DECISION_CHANGED`: governing `DecisionVersion` changed, or its materially
  used current interpretation changed lawfully with the same version.
- `TARGET_CHANGED`: the exact target reference changed, or its materially used
  temporal meaning changed lawfully under the same reference.
- `CLAIM_CHANGED`: the protected claim catalog or meaning changed, including
  attested temporal membership change.
- `REQUIREMENTS_CHANGED`: the applicable Configuration requirement version or
  assignment changed. Altered immutable content under one version is
  `INVALID_HISTORY` instead.
- `EVIDENCE_SUPPORT_CHANGED`: the scope-local Evidence epoch or interpreted
  Evidence support changed, or a materially used canonical-context identity,
  revision, or attested as-of meaning changed. A prior Decision used only as
  context has this role, not the governing Decision role.
- `NEGATIVE_PREDICATE_BROKEN`: a protected typed absence, membership,
  uniqueness, ancestry, or current-selection guard broke.
- `SUPPORT_CHANGED_BY_TIME`: Evidence support, fitness, or freshness changed
  independently through time with stable stored Evidence inputs and guards.
  A Decision temporal change alone never creates this category.

Return every independently applicable category. An independent Evidence
freshness crossing may yield `SUPPORT_CHANGED_BY_TIME` alongside
`DECISION_CHANGED`; a derived fitness change caused only by the Decision
change does not. A newly selected fact may also break a selection guard, in
which case both its role category and `NEGATIVE_PREDICATE_BROKEN` apply. Only
material meaning changes for the exact key stale the basis. Mere passage of
time, display-only changes, and out-of-key changes do not.

Stale diagnostics retain exact typed changed identity/version references and
broken guards. For a same-reference, same-version meaning change, they also
return the exact typed prior and fresh owner-meaning witnesses without
inventing a version delta. Semantic witness comparison excludes the
observation instant itself. Invalid history and source or persistence
unavailability retain their distinct no-write outcomes.

## Rationale

The owner of each fact is the only authority that can attest how its history
produced both as-of meanings. A complete witness lets Application detect
lawful clock-activated drift and invalid same-version changes without taking
over owner interpretation. Role-based stale mapping preserves the accepted
public failure vocabulary while reporting independent concurrent causes.
Physical encoding, query organization, and private proof-validation algorithms
remain implementation choices.

## Considered Options

Rejecting every same-version change as invalid would reject lawful
future-effective transitions. Calling every such change time-only would hide
invalid owner history and misattribute governing Decision drift to Evidence
fitness. Synthetic clock-driven versions or an eighth stale category would
change accepted R2 version and ADR 0013 public contracts. Comparing only two
owner views cannot prove cause or completeness.
