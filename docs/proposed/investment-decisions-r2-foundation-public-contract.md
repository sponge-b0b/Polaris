# R2 Investment Decision Foundation Public Contract Completion

**Status:** Owner-approved
**Release:** 0.2.0
**Primary entities:** `investment-decisions`, `portfolio-risk`, `application-use-cases`
**Roadmap milestone:** R2 — Durable decision kernel and historical truth
**Purpose:** Close the public/domain contract gaps exposed by the post-#294 foundation audit so downstream Specs and implementation execute explicit design rather than inventing identity, reference, naming, equality, or public API semantics.

## Authority and scope

This document refines the already-approved R2 lifecycle/application/persistence design without changing their core lifecycle semantics. It is the owner-approved completion authority for the gaps recorded after ticket #294.

It does not authorize a full Portfolio implementation, a generic actor registry, a generic provenance framework, or a universal event/record abstraction.

---

## 1. Portfolio domain entity identity

`Portfolio` is a durable domain entity/concept owned by the Portfolio & Risk boundary. The Living Entity Wiki entity `Portfolio & Risk` is an architectural ownership boundary; it is not the same thing as the `Portfolio` domain entity.

`PortfolioId` is the canonical identity type of the `Portfolio` domain entity.

`PortfolioId` semantics:

- immutable and type-distinct;
- UUID-backed using UUIDv4 values;
- opaque to consumers;
- allocated independently of holdings, capital, Portfolio State, account, broker, Investment Strategy, manager, Mandate version, display name, or any other mutable Portfolio content;
- never derived from a ticker, account number, Portfolio name, hash of current state, or another mutable business fact;
- carries no chronology, ownership, account, Mandate, Strategy, or other business meaning in its encoded value;
- never reused for a different continuing investment responsibility.

A complete `Portfolio` aggregate/entity implementation is not required merely to establish this identity contract. The Portfolio & Risk boundary owns `PortfolioId`; other boundaries reference it rather than inventing local Portfolio-reference identity types.

Investment Decision Scope therefore contains `PortfolioId` values. A Decision-local `PortfolioRef(str)` identity is not part of the canonical contract.

---

## 2. Investment Decision, Decision Need, and operation identity

`InvestmentDecisionId` and `DecisionNeedId` are distinct immutable UUID-backed UUIDv4 domain identity types. `OperationId` is a distinct immutable UUID-backed UUIDv4 application operation identity.

Their UUID values are allocated independently of Decision/Need content and carry no Subject, Scope, Portfolio, chronology, lifecycle, continuity, actor, provenance, workflow, model, report, persistence, or other semantic meaning.

Two different typed ID classes remain non-substitutable even if their underlying UUID values are equal.

Retry/replay of the same semantic application operation reuses the same `OperationId`; a distinct operation uses a distinct `OperationId`. Idempotency semantics are not inferred from UUID contents.

---

## 3. Decision Subject public representation

R2 represents Decision Subject with one immutable `DecisionSubject` value whose public payload is:

```text
statement: non-empty string
```

The statement identifies one coherent investment matter whose disposition is being judged. It may describe a composite subject only when the elements form one mutually dependent investment judgment. Independently resolvable matters remain separate Decisions.

The statement is domain meaning, not Decision identity. Editing/refining the statement while preserving the same coherent unresolved choice preserves `InvestmentDecisionId`; a materially independent choice requires a different Decision.

R2 does not introduce a structured instrument/position/action subject graph merely for future possibility. Later domain work may enrich Subject representation through an explicit contract change without deriving Decision identity from Subject content.

---

## 4. Decision Scope collection semantics

Decision Scope contains an immutable unique collection of zero or more canonical `PortfolioId` values plus `UNRESOLVED | ESTABLISHED` completeness.

The Portfolio collection is semantically **unordered**. Therefore:

```text
{Portfolio A, Portfolio B} == {Portfolio B, Portfolio A}
```

Duplicate Portfolio identities are invalid. `ESTABLISHED` with zero Portfolios is invalid. `UNRESOLVED` may contain zero or more confirmed Portfolios.

The public semantic contract is set-like equality/uniqueness. A concrete immutable collection such as `frozenset[PortfolioId]` is an appropriate direct realization; another internal representation is acceptable only if it preserves the same externally observable unordered semantics.

---

## 5. Actor Attribution foundation type

Actor Attribution remains distinct from authority and provenance.

R2 uses:

```text
ActorKind = HUMAN | COLLECTIVE | ORGANIZATION | POLARIS | EXTERNAL
ActorId   = opaque UUIDv4 domain identity
ActorAttribution = ActorKind + ActorId
```

`ActorId` identifies a domain-recognized originator, not a model, provider, workflow node, tool, prompt, job, or other implementation component. `ActorKind` classifies the originator role without encoding authority.

The special `POLARIS` kind still uses a stable `ActorId`; callers do not infer Polaris ownership from a magic string or from technical provenance.

This foundation establishes attributable-actor identity only. It does not implement actor directory/profile lifecycle or Governance authority assignment.

---

## 6. Trigger and technical provenance

Trigger provenance and technical provenance are non-business-identity context. Their carriers may reflect heterogeneous external/runtime identifier formats, so their reference values are not required to be UUID domain identities.

R2 uses constrained role types rather than arbitrary `(kind: str, identifier: str)` pairs.

Trigger provenance uses:

```text
TriggerKind = HUMAN_REQUEST | ATTENTION | SCHEDULED_REVIEW | EXTERNAL_EVENT | APPLICATION_REQUEST
TriggerProvenance = TriggerKind + non-empty reference
```

The trigger reference identifies the originating occurrence within the corresponding source context. The enum is the R2 foundation vocabulary; adding another trigger category is an explicit contract extension rather than passing an arbitrary new string.

Technical provenance uses zero or more typed references:

```text
TechnicalReferenceKind =
    WORKFLOW_EXECUTION
  | JOB_EXECUTION
  | MODEL_INVOCATION
  | PROVIDER_REQUEST
  | TOOL_INVOCATION
  | REPORT_OUTPUT

TechnicalReference = TechnicalReferenceKind + non-empty reference
TechnicalProvenance = immutable collection of TechnicalReference
```

These references are provenance only and may never serve as Investment Decision, Decision Need, Portfolio, actor, or other business identity.

---

## 7. Business basis/reference typing

R2 does **not** define a generic public `BusinessBasis(kind: str, identifier: str)` or `BusinessReference(kind: str, identifier: str)` abstraction.

A lifecycle fact carries a business basis/reference only when that fact's semantics require one, and that field uses the purpose-specific typed upstream contract owned by the relevant domain seam.

Examples include the later trusted Human Investment Decision basis for Deferral/substantive resolution and typed external/correction basis contracts. Those types are introduced with the lifecycle behavior that requires them.

Initiation and Subject/Scope refinement do not manufacture a generic business-basis field merely to keep one universal metadata envelope shape.

---

## 8. Lifecycle fact vocabulary and common metadata

The approved public fact vocabulary uses:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeEstablished
DecisionScopeRevised
```

for the #294 foundation slice. `DecisionSubjectRefined` is not the approved public fact name. Scope establishment and subsequent revision are distinct historical meanings and must not be collapsed into one generic `DecisionScopeRefined` fact.

Common lifecycle-fact temporal/ordering/operation/attribution/provenance attributes, when represented by one public value type, use the name:

```text
DecisionLifecycleFactMetadata
```

Bare `FactMetadata` is not a stable public domain name.

`DecisionLifecycleFactMetadata` contains only attributes genuinely common to the applicable lifecycle facts. Fact-specific business basis/reference remains on the fact or a purpose-specific fact payload when required rather than forcing unrelated optional generic fields into universal metadata.

---

## 9. Public Investment Decision construction and reconstruction surface

The stable public domain surface is behavior-oriented.

- New Decisions are created through the initiation domain operation, not by callers directly constructing an arbitrary `InvestmentDecision(facts=...)` history.
- Subject and Scope changes are performed through explicit domain operations that append the approved immutable fact meaning.
- `InvestmentDecision` is an immutable derived domain view/state reconstructed from validated lifecycle facts; its raw fact collection is historical authority but arbitrary caller-supplied fact tuples are not the normal public creation API.
- Durable-history reconstruction uses one explicit validation/reconstruction boundary rather than exposing direct aggregate construction as an unchecked public contract.
- Package exports are intentional stable contracts, not “every implemented class/helper”. Private realization helpers stay private.

The implementation may choose the narrowest function/class arrangement that realizes this contract, but it may not expose a broader public API merely because the implementation uses additional classes internally.

---

## 10. Implementation readiness consequence

With this document approved:

- the post-#294 foundation design questions for Decision Subject, Portfolio identity/reference, Scope equality, actor/provenance representation, business-basis typing, lifecycle-fact naming, and public construction/export surface are resolved;
- Spec #278 must be reconciled to these decisions before remediation code changes;
- ticket #294 remains closed as truthful history for its original contract;
- a new explicit remediation ticket must repair the #294 implementation against the amended #278 contract;
- #295 remains non-actionable until that remediation ticket is certified and closed.

Implementation is not authorized to reinterpret or replace these decisions with a different public/domain contract.