# R2 Investment Decision Foundation Public Contract Completion

**Status:** Owner-approved in part; design completion in progress
**Release:** 0.2.0
**Primary entities:** `investment-decisions`, `portfolio-risk`, `application-use-cases`
**Roadmap milestone:** R2 — Durable decision kernel and historical truth
**Purpose:** Close the public/domain contract gaps exposed by the post-#294 foundation audit so downstream Specs and implementation execute explicit design rather than inventing identity, reference, naming, equality, failure, or public API semantics.

## Authority and scope

This document refines the already-approved R2 lifecycle/application/persistence design without changing their core lifecycle semantics. Sections explicitly identified as approved are current completion authority. Open items remain non-authoritative until owner approval and block implementation that depends on them.

It does not authorize a full Portfolio implementation, a generic actor registry, a generic provenance framework, or a universal event/record abstraction.

---

## 1. Portfolio domain entity identity — approved

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

## 2. Investment Decision, Decision Need, and operation identity — approved

`InvestmentDecisionId` and `DecisionNeedId` are distinct immutable UUID-backed UUIDv4 domain identity types. `OperationId` is a distinct immutable UUID-backed UUIDv4 application operation identity.

Their UUID values are allocated independently of Decision/Need content and carry no Subject, Scope, Portfolio, chronology, lifecycle, continuity, actor, provenance, workflow, model, report, persistence, or other semantic meaning.

Two different typed ID classes remain non-substitutable even if their underlying UUID values are equal.

Retry/replay of the same semantic application operation reuses the same `OperationId`; a distinct operation uses a distinct `OperationId`. Idempotency semantics are not inferred from UUID contents.

---

## 3. Decision Subject public representation — approved

R2 represents Decision Subject with one immutable `DecisionSubject` value whose public payload is:

```text
statement: non-empty string
```

The statement identifies one coherent investment matter whose disposition is being judged. It may describe a composite subject only when the elements form one mutually dependent investment judgment. Independently resolvable matters remain separate Decisions.

The statement is domain meaning, not Decision identity. Editing/refining the statement while preserving the same coherent unresolved choice preserves `InvestmentDecisionId`; a materially independent choice requires a different Decision.

R2 does not introduce a structured instrument/position/action subject graph merely for future possibility. Later domain work may enrich Subject representation through an explicit contract change without deriving Decision identity from Subject content.

---

## 4. Decision Scope collection semantics — approved in part

Decision Scope contains an immutable unique collection of zero or more canonical `PortfolioId` values plus `UNRESOLVED | ESTABLISHED` completeness.

The Portfolio collection is semantically **unordered**. Therefore:

```text
{Portfolio A, Portfolio B} == {Portfolio B, Portfolio A}
```

Duplicate Portfolio identities are invalid. `ESTABLISHED` with zero Portfolios is invalid. `UNRESOLVED` may contain zero or more confirmed Portfolios.

The public semantic contract is set-like equality/uniqueness. A concrete immutable collection such as `frozenset[PortfolioId]` is an appropriate direct realization; another internal representation is acceptable only if it preserves the same externally observable unordered semantics.

**Open before implementation:** exact ordinary transition semantics among unresolved partial Scope, first establishment, later established revision, same-value no-op, and any attempted `ESTABLISHED -> UNRESOLVED` change.

---

## 5. Actor Attribution — direction approved, concrete contract open

Actor Attribution remains distinct from authentication, authority, and technical provenance. It identifies the domain-recognized originator of a material attributable act.

Approved direction:

- no arbitrary `(kind: str, identifier: str)` public contract;
- actor identity must be typed and stable enough for durable attribution;
- a model, provider, workflow node, tool, prompt, job, trace, or execution identifier is not an actor merely because it contributed technically;
- actor attribution does not itself establish authorization or Investment Authority Regime power.

**Open before implementation:** the exact greenfield actor identity owner, identity type, actor classification/taxonomy, package location, and how Polaris/human/collective/organization/external originators are represented without reviving the superseded pre-greenfield Principal architecture.

The pre-greenfield Identity & Access Wayfinder #182 and its Principal/Cerbos/Dishka architecture are historical only; its supersession record explicitly states that it no longer carries planning authority and identity/access must be independently re-derived against the greenfield architecture.

---

## 6. Trigger and technical provenance — direction approved, concrete vocabulary open

Trigger provenance and technical provenance are non-business-identity context and remain separate from Actor Attribution.

Approved direction:

- do not expose arbitrary generic `(kind: str, identifier: str)` pairs as the stable contract;
- use purpose-named typed references/vocabularies;
- heterogeneous source/runtime reference values need not be UUID business identities;
- technical references may never substitute for Investment Decision, Decision Need, Portfolio, actor, or other business identity;
- no ordering semantics should be inferred merely from collection position unless explicitly designed.

**Open before implementation:** the exact trigger categories, exact technical-reference categories, whether their reference collections are semantically unordered/unique, and which foundation facts require trigger/technical provenance versus permit absence/empty provenance.

---

## 7. Business basis/reference typing — approved direction

R2 does **not** define a generic public `BusinessBasis(kind: str, identifier: str)` or `BusinessReference(kind: str, identifier: str)` abstraction.

A lifecycle fact carries a business basis/reference only when that fact's semantics require one, and that field uses the purpose-specific typed upstream contract owned by the relevant domain seam.

Examples include the later trusted Human Investment Decision basis for Deferral/substantive resolution and typed external/correction basis contracts. Those types are introduced with the lifecycle behavior that requires them.

Initiation and Subject/Scope refinement do not manufacture a generic business-basis field merely to keep one universal metadata envelope shape.

**Open before implementation:** Decision Need itself must preserve the attributable reason deliberate judgment was warranted; its exact statement/rationale/basis representation is not yet frozen.

---

## 8. Lifecycle fact vocabulary and common metadata — approved in part

The approved foundation fact vocabulary includes:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeEstablished
DecisionScopeRevised
```

`DecisionSubjectRefined` is not the approved public fact name. Scope establishment and revision are distinct historical meanings and must not be collapsed into one generic `DecisionScopeRefined` fact.

Common lifecycle-fact temporal/ordering/operation/attribution/provenance attributes, when represented by one public value type, use the name:

```text
DecisionLifecycleFactMetadata
```

Bare `FactMetadata` is not a stable public domain name.

`DecisionLifecycleFactMetadata` contains only attributes genuinely common to the applicable lifecycle facts. Fact-specific business basis/reference remains on the fact or a purpose-specific fact payload when required rather than forcing unrelated optional generic fields into universal metadata.

**Open before implementation:** lifecycle-fact identity, exact recorded-sequence/version rules, required Actor/Trigger fields for each foundation fact, timezone/instant validation semantics, and the immutable creation-time derivation.

---

## 9. Public Investment Decision construction and reconstruction surface — approved direction, exact API open

The stable public domain surface is behavior-oriented.

- New Decisions are created through the initiation domain operation, not by callers directly constructing an arbitrary `InvestmentDecision(facts=...)` history.
- Subject and Scope changes are performed through explicit domain operations that append the approved immutable fact meaning.
- `InvestmentDecision` is an immutable derived domain view/state reconstructed from validated lifecycle facts; its raw fact collection is historical authority but arbitrary caller-supplied fact tuples are not the normal public creation API.
- Durable-history reconstruction uses one explicit validation/reconstruction boundary rather than exposing direct aggregate construction as an unchecked public contract.
- Package exports are intentional stable contracts, not “every implemented class/helper”. Private realization helpers stay private.

**Open before implementation:** exact public operation names/signatures, revision-continuity input, reconstruction/history property names, duplicate-reconciliation result surface, and whether semantic transition failures are typed exceptions or returned result values.

---

## 10. Additional approved upstream obligations discovered by Attention

The already-approved lifecycle/application designs require, but #294 did not implement:

- a reconstructable Decision Need statement/basis and attributable establishment context;
- identity for every lifecycle fact;
- initiation recorded version/sequence `1` with each committed Decision mutation incrementing once;
- immutable Decision creation time and monotonic current domain version;
- `DecisionInitiated` continuity provenance sufficient to reconstruct `NO_CANDIDATES` versus explicit create-new, materially considered candidate Decision IDs, attributable create-new rationale/basis when required, and the candidate knowledge/revalidation basis used for commit;
- the earned source boundary `src/polaris/domain/decisions/`, rather than the implementation-selected `src/polaris/domain/investment_decisions/` package.

These are not optional implementation refinements. Their concrete public representation must be completed before remediation code is authorized.

---

## 11. Implementation readiness consequence

**FOUNDATION IMPLEMENTATION READINESS: BLOCKED.**

The owner-approved identity, Portfolio, Subject, Scope-equality, business-basis direction, fact naming, metadata naming, and behavior-oriented API decisions remain authoritative. However, the additional open items above must be owner-approved and reconciled into Spec #278 and remediation ticket #299 before implementation mutates the foundation code.

Ticket #294 remains closed as truthful history for its original contract. #299 is the explicit remediation vehicle but is not actionable while this design-completion gate remains open. #295 remains non-actionable until #299 is certified and closed.

Implementation is not authorized to fill any open item by choosing the most convenient code shape.