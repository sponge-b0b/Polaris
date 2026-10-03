---
status: accepted
---

# Derive R3 Evidence sufficiency from executable requirements

## Context

ADRs 0012 and 0013 establish first-class Evidence sufficiency assessments,
Configuration-owned immutable requirement versions, Evidence-owned deterministic
evaluation, and explicit requirement dispositions. Implementation entry exposed an
in-domain omission: a sufficiency predicate remained free text, callers could
submit dispositions and a selected support subset, and `NOT_APPLICABLE` lacked an
exact Configuration witness. That contract could persist `SATISFIED` and
`SUFFICIENT` with no eligible Evidence or accept absence without authoritative
Configuration support.

This ADR completes that bounded Configuration-to-Evidence contract without
reopening the accepted identities, target union, role/use vocabulary, correction
algebra, reconstruction outcomes, claim lifecycle, requirement-version history,
or current-support basis semantics in ADRs 0012 and 0013.

## Decision

### Ownership and predicate language

Evidence owns a closed inward executable sufficiency-predicate language and
deterministic evaluator. Configuration owns immutable attributable requirement-set
versions and selects concrete predicate values through that contract.
Caller-authored dispositions and caller-selected authoritative support subsets are
removed from the semantic authority path.

The only positive R3 predicate is
`MinimumEligibleEvidence(minimum_distinct_observations, qualifying_roles)`. The
minimum is positive. The role set is non-empty and may contain `SUPPORTING`,
`CONFLICTING`, `CONSTRAINING`, or `QUALIFYING`. `CONTEXTUAL` and `RECONSTRUCTION`
never satisfy a readiness-gating predicate. Narrative description may remain
non-executable metadata. Requirement identity continuity compares the typed
predicate, not prose.

`FreshnessRequirementDefinition` remains a binding-fitness rule with a persisted
binding freshness evaluation. Only `SufficiencyRequirementDefinition` instances
receive sufficiency dispositions. Their proof cites the exact freshness definition
or exact no-freshness witness used per binding.

### Applicability and negative authority

Each sufficiency definition retains its predicate and carries explicit
`REQUIRED | NOT_APPLICABLE` state in the resolved immutable version. A state change
creates a new version but may retain `EvidenceRequirementId` when predicate meaning
is unchanged.

Zero sufficiency definitions in a complete resolved version is a version-level
negative fact. Persist
`EvidenceNoSufficiencyRequirementsWitness(set_id, version_id, applicability coordinates)`.
This differs from a present requirement marked `NOT_APPLICABLE`. Missing,
unavailable, contested, incomplete, or invalid authority supplies neither witness.

A persisted `NOT_APPLICABLE` row carries
`EvidenceRequirementNotApplicableWitness(set_id, version_id, requirement_id, applicability coordinates)`.
The immutable version must mark that exact requirement `NOT_APPLICABLE`.
Membership, empty bindings, authority failure, or evaluator failure is
insufficient.

### Complete candidate universe and eligibility

At exact `(T,K)`, Application and Evidence load the complete interpreted binding
universe for the target, scope, `EvidenceUse`, and typed applicability coordinates.
Endpoint/applicability mismatch is an invalid request/history outcome, not a
disposition.

A binding contributes only when its interpretation is active and determinate at
`(T,K)`, it is materially used for the assessed use, availability is `AVAILABLE`,
its role qualifies, its observation matches the typed subject/reference
coordinates, and assessment-time freshness is `FRESH` or has the exact same-version
no-freshness witness. Assessment-time evaluation does not rewrite historical
binding freshness.

Deficiency witnesses are derived separately:

- exact-key, qualifying-role `UNAVAILABLE` or `UNKNOWN` bindings retain
  `materially_used=false` and enter the unavailable or unresolved upper bound;
- an `AVAILABLE`, qualifying-role binding enters the stale bound only when
  materially used and assessment-time freshness is `STALE`;
- an `AVAILABLE`, qualifying-role, materially used binding with valid
  `INDETERMINATE` freshness enters the `UNKNOWN` unresolved upper bound;
- an available, fresh/no-freshness but unused binding is visible but neither
  contributes nor creates a deficiency; and
- disputed or contested interpretations enter the unresolved upper bound only when
  a surviving branch would meet the role/coordinates/material-use rule, or records
  the exact unavailable/unknown intended relationship.

Count distinct `EvidenceObservationId` values, not binding roots. Preserve every
qualifying or witness binding and interpreted `EvidenceFactRef` in provenance.
Withdrawn interpretations do not count; invalid or incomplete ancestry aborts the
assessment; facts recorded after `K` cannot affect it.

### Disposition entailment and aggregate result

Disposition is entailed as follows:

- `NOT_APPLICABLE` requires the exact Configuration witness above;
- `SATISFIED` requires the eligible distinct-observation threshold;
- otherwise compute lower and upper distinct-observation bounds; if unresolved
  candidates could meet the threshold, select `CONTESTED`, then `DISPUTED`, then
  `UNKNOWN`, retaining all reasons; `UNKNOWN` covers both unknown availability and
  valid indeterminate freshness;
- otherwise select `STALE` if stale witnesses close the gap, `UNAVAILABLE` if stale
  plus unavailable witnesses close it, and `MISSING` otherwise; and
- wrong-role-only, available-but-unused-only, and zero-candidate cases are
  `MISSING`.

The aggregate algebra remains:

- any `MISSING | UNAVAILABLE | STALE` yields `INSUFFICIENT`;
- otherwise any `UNKNOWN | DISPUTED | CONTESTED` yields `INDETERMINATE`; and
- otherwise `SATISFIED` and authoritatively `NOT_APPLICABLE` yield `SUFFICIENT`.

A complete zero-sufficiency-definition version yields `SUFFICIENT` only with its
durable version-level witness.

### Persisted proof and commit boundary

For each present sufficiency requirement, Evidence derives and the immutable
assessment preserves:

- the exact requirement reference and entailed disposition;
- every contributor binding ID and interpreted fact support;
- every deficiency-witness binding ID with typed reason, material-use,
  availability, and assessment-time freshness state;
- counted observation IDs;
- `(T,K)` and the applicability key;
- requirement set and version;
- any negative-applicability witness; and
- the exact `EvidenceSupportVersion` and typed absence guards relied upon.

Overall `contributing_binding_ids` is the union of derived positive contributors. A
zero-definition version preserves the version-level witness instead.

At a trusted commit instant, re-evaluate and atomically revalidate the exact
requirement version and assignment, complete binding and correction universe,
support version, and negative predicates before append. Valid indeterminate binding
freshness is distinct from requirement-authority failure. Missing, unavailable,
contested, or invalid authority; unavailable revalidation; stale basis; invalid
history; or persistence failure produces its existing fail-closed outcome and no
assessment. A changed requirement version creates a new reassessment root;
historical assessments retain their original proof.

### R3 exclusion

R3 introduces no arbitrary expression language, generic rule graph, executable
Configuration code, weighted scoring, source-diversity rule, Boolean nesting,
custom predicate plugin, or broader future predicate family.

## Rationale

The closed threshold predicate makes Configuration facts executable without moving
Evidence semantics into Configuration or creating a generic rule engine. Deriving
dispositions from the complete historical binding universe prevents a caller from
hiding contradictory or deficient support. Counting observation identity prevents
duplicate attributable bindings from manufacturing support cardinality, while
preserving every binding and fact reference retains provenance. Exact negative
witnesses keep absence authoritative and distinguish it from missing or broken
authority.

## Considered Options

### Keep free text and validate submitted enums

Rejected because it cannot prove entailment and leaves the durable contract to
caller convention.

### Let Configuration execute sufficiency rules

Rejected because role, availability, freshness, correction interpretation, and
support are Evidence semantics. Executable Configuration would reverse the
authority boundary.

### Introduce a generic Boolean or plugin rule language

Rejected because R3 needs one narrow threshold predicate and a generic rule graph
would add unsupported product, identity, and persistence semantics.

### Count binding roots or infer non-applicability from missing bindings

Rejected because duplicate bindings could manufacture support and absence of
support is not Configuration authority.
