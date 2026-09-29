---
status: accepted
---

# Freeze R3 Evidence identity, binding, and reconstruction

## Context

ADR 0006 establishes durable Evidence observations, judgment-relative bindings,
judgment/use-relative sufficiency, and hindsight-safe Decision Context assembly.
ADR 0011 establishes domain-owned opaque identity, typed cross-domain references,
append-only material history, and application-owned reconstruction.

Preparing the first R3 Evidence Spec exposed material choices those decisions did
not fix: which Evidence facts need independent identity, their continuity and
cardinality, the admissible judgment references and binding vocabulary, the
correction algebra and vocabulary, and the exact current/historical reconstruction
contract. Leaving those choices to implementation would create incompatible public,
persistence, temporal, and downstream behavior.

## Decision

This ADR extends ADRs 0006 and 0011 with the implementation-ready R3 contract below.

### First-class facts and identity

First-class identity follows semantic lifecycle needs rather than a blanket UUID
rule. A fact receives its own identity when it must be independently addressable,
attributable, correctable, historically reconstructable, or referenced downstream.

R3 has four such Evidence fact identities:

- `EvidenceObservationId` identifies an observation that can be independently
  bound, attributed, corrected, reconstructed, and referenced;
- `EvidenceBindingId` identifies the attributable relationship between one
  observation and one scoped use of one judgment;
- `EvidenceSufficiencyAssessmentId` identifies an attributable assessment of a
  target/scope/use and its requirement dispositions; and
- `EvidenceCorrectionId` identifies each immutable correction act so exact
  ancestry, correction-of-correction, restoration, and competing support remain
  addressable.

Each is an opaque UUIDv4-backed identity allocated by Application through
injectable generation before domain construction. Identity is independent of
source identity, payload, target, role, time, database row, and runtime/workflow
identity. PostgreSQL preserves native UUID values but does not generate or redefine
the inward identity contract.

An observation, binding, or sufficiency-assessment ID identifies its immutable base
fact; there is no second generic fact ID for that base assertion. A correction uses
its `EvidenceCorrectionId`. `EvidenceFactRef` is a closed typed reference over the
three root IDs and `EvidenceCorrectionId` for ancestry and interpretation support.

Exact semantic command retry reuses its `OperationId` and returns the existing
committed identities. Reuse of an operation for a different semantic request is an
idempotency conflict. Every distinct attributable act receives fresh identity even
when its content is equivalent.

Identity continuity and cardinality are:

- correction of the record of the same acquisition/observation act retains its
  `EvidenceObservationId`; a later acquisition, newly published source version, or
  materially different observation receives a new one;
- one observation may have zero or many bindings;
- a binding root fixes exactly one observation, typed target judgment, scope, and
  use; changing any of those creates a new binding rather than changing lineage;
- independently attributable bindings may share the same endpoint/scope/use tuple;
  opaque IDs and command receipts, not semantic tuples, are uniqueness boundaries;
- a sufficiency assessment addresses one target/scope/use at one attributable
  assessment boundary and references zero or many bindings plus explicit
  requirement dispositions;
- correction of a misrecorded assessment remains attached to that assessment;
  reassessment caused by time, new Evidence, or changed requirements receives a
  new assessment identity.

Intentional succession between root facts is explicit but is not correction.
An observation may carry one typed `supersedes_observation_id`; an assessment may
carry one typed `reassesses_assessment_id`. Each points to an earlier same-family
root and the resulting predecessor chain is acyclic. Succession never rewrites its
predecessor or selects truth merely by recency. A binding with an erroneous or
replaced fixed observation/target/scope/use is retracted and a new binding is
created; binding supersession is not a separate shortcut.

### Typed judgment binding

`EvidenceJudgmentRef` is a closed typed union over the owner-specific identities of:

- Investment Hypothesis;
- Investment View;
- meaningful-challenge result;
- Projected Portfolio Consequence;
- Portfolio Risk Assessment;
- Investment Recommendation;
- Recommendation-withholding judgment;
- Human Investment Decision;
- Decision Evaluation; and
- Lesson.

Outcome, actual Portfolio State, Decision Alternative, and Investment Decision
lifecycle identity remain context or fact inputs rather than Evidence-judgment
targets. Adding another target family requires an explicit later architecture
change; a generic `(kind, id)` entity reference is not permitted.

Every binding has exactly one scope: `JUDGMENT_WIDE` or
`CLAIM_SPECIFIC(ClaimId)`. `ClaimId` is an opaque UUIDv4 dependent identity owned by
and meaningful only with its target judgment. Judgment-wide scope does not imply a
binding to every material claim.

Evidence role is exactly:

- `SUPPORTING`;
- `CONFLICTING`;
- `CONSTRAINING`;
- `QUALIFYING`;
- `CONTEXTUAL`; or
- `RECONSTRUCTION`.

Evidence use is exactly:

- `JUDGMENT_BASIS`;
- `CHALLENGE_BASIS`;
- `CURRENT_SUPPORT_CHECK`;
- `RETROSPECTIVE_LATER_EVIDENCE`; or
- `RECONSTRUCTION_ONLY`.

Role describes how Evidence bears on the scoped judgment or claim; use describes
why it is consumed. A binding also preserves `AVAILABLE | UNAVAILABLE | UNKNOWN`,
whether it was materially used, the applicable Freshness Requirement reference and
basis when one exists, `FRESH | STALE | INDETERMINATE` when freshness applies, and
material qualification. No applicable freshness requirement is explicit absence,
not a fourth freshness result. Material use requires `AVAILABLE`; a history that
claims actual use of unavailable or unknown Evidence is contested or invalid rather
than silently normalized.

### Sufficiency

A sufficiency assessment preserves target, scope, use, requirement-set identity or
version, contributing binding IDs, attribution, effective time, recorded time, and
`SUFFICIENT | INSUFFICIENT | INDETERMINATE`.

Every material requirement has exactly one disposition: `SATISFIED`, `MISSING`,
`UNAVAILABLE`, `STALE`, `UNKNOWN`, `DISPUTED`, `CONTESTED`, or `NOT_APPLICABLE`.
`SUFFICIENT` requires every applicable required item to be determinately satisfied
by eligible non-contested support. Determinate missing, unavailable, or stale
required support yields `INSUFFICIENT`. Unknown, disputed, contested, or otherwise
unresolved required support yields `INDETERMINATE`. Missing support is never
represented as synthetic Evidence.

### Correction and interpretation

R3 Evidence reuses the accepted append-only correction algebra but owns correction
vocabulary distinct from Decision-specific `QUALIFY` and `DISCONFIRM`:

- `REVISE` appends a complete replacement assertion for the same fact lineage; it
  is never a partial patch; and
- `RETRACT` withdraws the targeted assertion without supplying a replacement.

`QUALIFY` is not an Evidence correction effect because `QUALIFYING` already names a
binding role. `DISCONFIRM` is not an Evidence correction effect because it can be
mistaken for conflicting Evidence and does not unambiguously state withdrawal.

Each family-specific correction variant carries the corrected root identity, its
own `EvidenceCorrectionId`, attribution, basis, effective time, recorded time, and
exactly one target: the root base fact or an earlier correction from the same root
and family. `REVISE` also carries the complete family-specific replacement
assertion. Correction ancestry is acyclic.

Retracting a correction recursively restores the branch interpretation immediately
preceding that correction. Sibling branches remain independent. Materially
equivalent surviving assertions coalesce and union their complete support
`EvidenceFactRef` sets. Incompatible positive branches, or positive support versus
withdrawal support, produce a valid `CONTESTED` interpretation. A surviving
assertion may also preserve disputed or unknown provenance or interpretation.

There is no `RESTORE`, `CONTEST`, or `SUPERSEDE` correction effect. Restoration and
contestation are derived interpretation; succession and reassessment use new root
facts and their typed predecessor relations. Recorded recency, UUID ordering, and
database ordering never choose a winner. Missing or unknown ancestry is invalid or
incomplete history rather than contestation. Original, revised, retracted, and
defeated facts remain inspectable.

Every interpretation is explicitly bound to `(effective_at=T, known_at=K)` and
distinguishes not known at the cutoff, not yet effective, determinate, withdrawn,
and contested states where applicable.

### Application reconstruction contract

One deep Application query module owns Decision Context/Evidence composition.

A historical or judgment reconstruction request requires `InvestmentDecisionId`,
typed `EvidenceJudgmentRef`, timezone-aware `effective_at`, and timezone-aware
`known_at`. A convenience “as formed” request may derive the immutable target
judgment's formation/effective and recording/knowledge boundaries, but returns those
boundaries and is not an unbounded judgment-only lookup.

A current-support request requires `InvestmentDecisionId`, typed target, scope,
use, and an explicit caller-visible observation instant interpreted as `T=K`. When
the result becomes a command basis, the caller supplies the Decision, judgment, and
Evidence-set versions or absence predicates returned by the preceding read; commit
revalidates them and returns a typed stale-read-base/concurrency outcome on mismatch.
Pure historical inspection does not require expected versions because `(T,K)` fixes
its knowledge universe.

The result keeps applicable canonical context facts separate from Evidence
observations, bindings, and sufficiency. It preserves owning provenance,
availability, role, use, actual use, freshness, support, and contestation. For
Decision Evaluation, judgment-time Evidence and `RETROSPECTIVE_LATER_EVIDENCE` are
separate; later Evidence never changes the earlier availability result.

The result universe distinguishes:

- complete reconstruction;
- incomplete reconstruction, with missing required facts, provenance, or history
  and any safe partial view;
- contested reconstruction, with conflict and support references and any safe
  partial view;
- target or Decision not known at the knowledge cutoff;
- target not belonging to the requested Decision or invalid claim reference;
- not-yet-effective target or context;
- invalid or incomplete correction history;
- persistence or source read unavailable; and
- stale expected version or read basis.

`UNAVAILABLE` or `UNKNOWN` availability, `STALE` or `INDETERMINATE` freshness, and
`INSUFFICIENT` or `INDETERMINATE` sufficiency are domain results rather than
transport errors. Consumers requiring determinate support fail closed on them, on
contestation, or on incomplete/invalid reconstruction. Reconstruction never fills a
gap from hindsight or substitutes current retrievability for historical
availability.

## Rationale

The four identities follow the facts that must participate independently in
attribution, reference, correction, and reconstruction; UUIDv4 is merely their
opaque greenfield representation. The closed target/scope/role/use contract retains
referential and bounded-context meaning without a universal entity graph. The
Evidence-owned `REVISE | RETRACT` vocabulary preserves the proven correction
algebra without conflating correction with Evidence qualification or conflict.
Explicit temporal and version boundaries make historical reconstruction and
command-bound current reads safe against hindsight and stale bases.

## Considered Options

### Give every stored row UUIDv4 identity by default

Rejected because storage shape is not the semantic reason for identity and would
create redundant base-fact identity layers.

### Reuse Decision `QUALIFY | DISCONFIRM` vocabulary unchanged

Rejected because those terms collide with Evidence role/conflict meaning. The
algebra is reusable; the bounded-context vocabulary is not.

### Use semantic tuples, mutable singleton rows, or latest-write-wins correction

Rejected because they erase independently attributable acts, make references
unstable, and cannot preserve restoration, sibling support, or valid contestation.

### Use a generic polymorphic target and one Decision Context snapshot

Rejected because this weakens referential meaning and creates a duplicate source of
cross-domain truth.
