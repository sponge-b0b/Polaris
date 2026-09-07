# R2 Investment Decision Foundation Public Contract Completion

**Status:** Owner-approved; foundation design complete
**Release:** 0.2.0
**Primary entities:** `investment-decisions`, `portfolio-risk`, `application-use-cases`, `governance-authority`, `security-identity`
**Roadmap milestone:** R2 — Durable decision kernel and historical truth
**Purpose:** Close the public/domain contract gaps exposed by the post-#294 foundation audit so downstream Specs and implementation execute explicit design rather than inventing identity, reference, naming, equality, failure, authorization, or public API semantics.

## Authority and scope

This document is the owner-approved completion authority for the R2 Investment Decision foundation public contract. It refines the already-approved R2 lifecycle/application/persistence design and explicitly amends earlier R2 wording where this document makes a more precise foundation choice.

Where an earlier R2 artifact, Spec body, wiki entry, or glossary sentence conflicts with a contract explicitly frozen here, this document is the controlling R2 design authority until the derived artifact is synchronized. Historical artifacts remain truthful records of the design state that existed when they were written; they are not silently rewritten into having made later choices.

This document does not authorize a full Portfolio implementation, a generic actor registry, a generic authorization framework, a generic provenance framework, a universal event/record abstraction, or #299 source implementation merely by existing. It freezes the design that #299 must execute.

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

## 2. Investment Decision, Decision Need, lifecycle-fact, operation, and actor identity

The foundation uses distinct immutable UUID-backed UUIDv4 identities:

```text
PortfolioId
InvestmentDecisionId
DecisionNeedId
DecisionLifecycleFactId
OperationId
ActorId
```

Each wrapper is type-distinct even when two underlying UUID values happen to be equal. UUID values are semantically opaque and allocated independently of Subject, Scope, Portfolio state/content, chronology, lifecycle, continuity, actor role, provenance, workflow, model, report, persistence, or other mutable/business content.

`OperationId` is an application operation identity. Retry/replay of the same semantic application operation reuses the same `OperationId`; a distinct semantic operation uses a distinct value. Idempotency equivalence is determined by the semantic request/receipt contract, not by UUID contents.

`DecisionLifecycleFactId` is the domain identity of one immutable lifecycle fact. It is not a persistence row ID and is allocated independently of the Decision ID, fact payload, timestamps, operation identity, and technical execution identity.

---

## 3. Decision Need

`DecisionNeed` is a real immutable domain concept, not merely an identifier.

The R2 foundation preserves at least:

```text
DecisionNeedId
statement: non-empty string
effective_at
recorded_at
OperationId
Actor Attribution
Trigger Provenance
optional Technical Provenance
```

The Need statement explains **why one coherent unresolved Portfolio-relevant choice warrants deliberate judgment**. It is distinct from `DecisionSubject.statement`, which identifies **what investment matter is being judged**.

Need establishment is an attributable knowledge/work-state transition, not a consequential investment-authority act. A Need may be established by a human or by Polaris under the applicable product/access/operating boundaries without thereby creating Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, Action Intent, or execution authority.

A later correction to the Need is append-only. It does not erase the historical determination that existed.

---

## 4. Decision Subject

R2 represents Decision Subject with one immutable `DecisionSubject` value whose public payload is:

```text
statement: non-empty string
```

The statement identifies one coherent investment matter whose disposition is being judged. It may describe a composite subject only when the elements form one mutually dependent investment judgment. Independently resolvable matters remain separate Decisions.

The statement is domain meaning, not Decision identity. Revising the statement while preserving the same coherent unresolved choice preserves `InvestmentDecisionId`; a materially independent choice requires a different Decision.

A semantically identical Subject revision is a no-op: it appends no lifecycle fact and does not increment Decision version.

R2 does not introduce a structured instrument/position/action subject graph merely for future possibility.

---

## 5. Decision Scope collection and transition semantics

Decision Scope contains an immutable unique collection of zero or more canonical `PortfolioId` values plus completeness:

```text
UNRESOLVED | ESTABLISHED
```

The Portfolio collection is semantically unordered. Therefore `{A, B} == {B, A}`. Duplicate Portfolio identities are invalid. `ESTABLISHED` with zero Portfolios is invalid. `UNRESOLVED` may contain zero or more confirmed Portfolios.

The public semantic contract is set-like equality/uniqueness. `frozenset[PortfolioId]` is an appropriate direct realization; another representation is acceptable only if it preserves the same observable semantics.

Ordinary Scope transitions are frozen as:

- `UNRESOLVED -> UNRESOLVED` with changed membership: `DecisionScopeRevised`;
- `UNRESOLVED -> ESTABLISHED`: `DecisionScopeEstablished`;
- `ESTABLISHED -> ESTABLISHED` with changed membership: `DecisionScopeRevised`;
- `ESTABLISHED -> UNRESOLVED`: invalid as an ordinary forward transition; an erroneous prior establishment is handled through explicit correction semantics;
- semantically identical Scope input: no-op, with no lifecycle fact and no Decision-version increment.

Subject/Scope revision preserves Decision identity only while the same coherent choice remains. Independently resolvable choices require separate Decision identity.

---

## 6. Actor Attribution, authentication, application authorization, and investment authority

### Canonical actor identity and attribution

`ActorId` is the canonical opaque UUIDv4-backed identity used to recognize a durable actor across domain boundaries. It is intentionally separate from authentication-provider identifiers, usernames, email addresses, model/provider IDs, workflow/job IDs, and authority assignments.

Actor Attribution answers:

> **Who actually formed, authored, or performed this material domain act?**

The stable attribution contract supports truthful known, unknown, and contested states rather than fabricating identity from credentials, likely role, organizational responsibility, or technical provenance. Conceptually:

```text
KnownActorAttribution(actor_id)
UnknownActorAttribution
ContestedActorAttribution(candidate_actor_ids)
```

Ordinary live commands that establish a new attributable act require known Actor Attribution. Historical reconstruction/correction may preserve unknown or contested attribution when that is the truthful supported state.

The foundation does **not** persist a universal `ActorKind` on every attribution fact. Human/collective/organization/Polaris/external classification may exist where independently useful, but it is not the canonical attribution identity and must not become an authorization surrogate.

Polaris itself has stable canonical Actor identity when Polaris forms a Polaris-owned domain judgment or performs an attributable domain act. Models, providers, prompts, tools, workflow nodes, jobs, traces, calculators, retrieval steps, and similar implementation components remain provenance unless a future explicit domain contract independently establishes them as actors. They do not receive Actor identity merely because they contributed technically.

### Four distinct questions

Polaris preserves these layers rather than collapsing them into one generic authorization mechanism:

```text
Authentication
  Who is presenting these credentials?

Application authorization
  May this authenticated actor access or invoke this application capability?

Actor Attribution
  Who actually formed or performed this domain act?

Investment authority
  Did that actor possess this specific investment-authority power
  for this subject/scope and time under the applicable Investment Authority Regime?
```

Security & Identity owns authenticated actor context and application access control. Governance & Authority owns the Investment Authority Regime and power-specific investment-authority semantics. `ActorId` is the stable bridge; ownership of authentication/provider identity and authority assignment does not transfer into Actor Attribution.

### Authority-bearing acts require authority before establishment

Actor Attribution never grants authority. Actor classification, credentials, application access, organizational role, or possession of another power never implies the required investment-authority power.

An authority-bearing canonical domain act may be established only when the applicable Investment Authority Regime confirms that the attributable actor possesses the specific required power for the act's subject, scope, conditions, and authority-effective time.

This applies to power-specific authority acts such as Human Investment Decision, Approval, Mandate Exception, Residual-Risk Acceptance, Authority Denial, and any future authority act governed by an Investment Authority Regime.

If a user attempts an authority-bearing act without the required power, Polaris rejects establishment of the corresponding canonical authority fact. The attempt may be durably auditable under Governance/security audit semantics where required, but it is **not** recorded as `Approval(authorized=false)`, an unauthorized `HumanInvestmentDecision`, or another canonical authority act whose name would falsely imply that the authority act occurred.

Analytical/advisory judgment remains different. An actor may be permitted to form attributable Investment View, challenge, Proposed Action, Portfolio Risk Assessment, research judgment, or other advisory/analytical input without possessing the separate power required to make a Human Investment Decision or another authority act.

Historical validity is evaluated against the authority regime and authority facts applicable when the act occurred. Later revocation or reassignment of authority does not retroactively invalidate or transfer Actor Attribution for a valid historical authority act.

This section explicitly supersedes earlier R2/glossary wording that permitted a canonical Human Investment Decision to exist while its actor lacked the power required to perform that authority-bearing act. Historical unauthorized attempts remain representable, but they do not acquire canonical authority-act semantics merely because they were attempted.

---

## 7. Trigger and technical provenance

Actor Attribution, Trigger Provenance, and Technical Provenance remain separate.

Every new foundation lifecycle fact carries one semantic Trigger Provenance. Trigger vocabulary is deliberately constrained to current R2 meanings rather than arbitrary caller-defined strings. The approved R2 trigger categories are:

```text
HUMAN_REQUEST
ATTENTION
SCHEDULED_REVIEW
EXTERNAL_OBSERVATION
INTERNAL_FOLLOW_UP
```

Each trigger carries a non-empty source-context reference sufficient to reconstruct the triggering context without turning that reference into business identity. New categories require explicit contract extension.

Technical Provenance is optional and may be empty. When present, it is an immutable, semantically unordered, duplicate-free collection of purpose-named technical references. Current R2 technical-reference categories are:

```text
REQUEST
WORK_ITEM
MODEL_INVOCATION
PROVIDER_CALL
ADAPTER_SOURCE_CALL
TRACE
```

Technical reference values may be opaque non-empty strings because they intentionally reference technical/external execution context rather than encode business identity. They may never substitute for `InvestmentDecisionId`, `DecisionNeedId`, `PortfolioId`, `ActorId`, or another business identity.

R2 does not expose one universal arbitrary `(kind: str, identifier: str)` provenance contract.

---

## 8. Business basis/reference typing

R2 does **not** define generic public `BusinessBasis(kind: str, identifier: str)` or `BusinessReference(kind: str, identifier: str)` abstractions.

A lifecycle fact carries a business basis/reference only when that fact's semantics require one, using the purpose-specific typed upstream contract owned by the relevant seam.

Examples include trusted Governance-owned Human Investment Decision basis for later Deferral/substantive-resolution consequences and typed external/correction basis contracts. Those types are introduced with the lifecycle behavior that requires them.

Initiation and Subject/Scope revision do not manufacture generic optional business-basis fields merely to keep a universal metadata envelope shape.

---

## 9. Lifecycle fact vocabulary, identity, sequence, version, and time

The foundation fact vocabulary is:

```text
DecisionInitiated
DecisionSubjectRevised
DecisionScopeEstablished
DecisionScopeRevised
```

`DecisionSubjectRefined`, generic `DecisionScopeRefined`, and bare `FactMetadata` are not stable public contract names.

Common lifecycle-fact attributes use `DecisionLifecycleFactMetadata` when represented by one public value object. Each lifecycle fact has its own `DecisionLifecycleFactId`.

### Lifecycle sequence

`DecisionLifecycleSequence` is canonical ordering within one Decision's immutable lifecycle-fact history:

- `DecisionInitiated` has sequence `1`;
- every appended lifecycle fact/correction for that Decision uses the immediately next sequence;
- sequence has no gaps or duplicates within a validated history;
- reconstruction rejects missing initiation, duplicate/broken sequence, mixed Decision identity, duplicate fact identity, and invalid transition history.

### Decision version

`DecisionVersion` is the monotonic concurrency version of the Decision's current concurrency-protected state:

- initiation creates version `1`;
- every committed mutation that changes Decision current state increments version exactly once;
- semantic no-ops do not increment version;
- lifecycle-fact sequence and Decision version may currently advance together, but they are **not the same concept**;
- a later relationship-only mutation may increment Decision version without inventing a lifecycle fact merely to keep two counters numerically equal.

### Time

`effective_at` and `recorded_at` are timezone-aware instants.

`recorded_at` is trusted commit/knowledge time controlled by the application/persistence boundary rather than arbitrary caller authority. `effective_at` is business-effective time and may be earlier than, equal to, or later than `recorded_at`; R2 does not impose `effective_at <= recorded_at` because late-discovered and known-future-effective facts are legitimate.

`InvestmentDecision.created_at` is derived from `DecisionInitiated.recorded_at`. It is immutable.

Historical interpretation remains:

```text
as_known_at(K) = effective_at(T=K, known_at=K)
```

and `effective_at(T, known_at=K)` uses only knowledge recorded by `K` before interpreting effective state at `T`.

---

## 10. `DecisionInitiated` continuity provenance

`DecisionInitiated` contains a first-class initiation-continuity value sufficient to reconstruct why a distinct Decision identity was created.

The foundation distinguishes:

```text
NO_CANDIDATES
EXPLICIT_CREATE_NEW
```

Initiation continuity preserves:

- the determination kind;
- an immutable, semantically unordered, duplicate-free set of materially considered unresolved operative candidate `InvestmentDecisionId` values;
- the candidate knowledge cutoff / `known_at` boundary used for continuity determination and commit revalidation;
- for `EXPLICIT_CREATE_NEW` with candidates, required known Actor Attribution and a non-empty attributable create-new rationale.

Persistence-specific lock IDs, advisory-lock keys, row-version tokens, and similar mechanical guard details are not domain lifecycle provenance. The command receipt/persistence adapter may preserve the mechanical evidence required to prove its revalidation guarantee.

Changed candidate basis before commit produces continuity conflict/re-evaluation rather than silent duplicate Decision creation.

---

## 11. Semantic failure mechanism

The Decision foundation uses a stable `InvestmentDecisionError` hierarchy, or equivalently specific typed domain exceptions under that base, for rejected domain operations such as:

- invalid identity/type use;
- invalid Decision Scope;
- Decision Need already grounded;
- independent choice requiring a new Decision;
- invalid lifecycle/work transition;
- invalid trusted basis;
- invalid/non-operative or contested applicability where deterministic operation is required;
- invalid history/reconstruction;
- relationship conflict/cycle where owned by the Decision domain.

Valid contested/indeterminate domain state is represented as domain state/value rather than thrown merely because certainty is unavailable. Semantic no-op is also not exceptional.

The application layer translates domain failures, concurrency/idempotency conflicts, persistence failures, and other cross-boundary outcomes into its own command/API outcomes. R2 does not introduce a universal platform `Result` framework merely for this domain.

---

## 12. Public Investment Decision construction/reconstruction surface

The stable foundation API is behavior-oriented. Exact Python layout may remain lean, but the public semantics are equivalent to:

```text
initiate_decision(...)
revise_subject(...)
establish_or_revise_scope(...)
reconstruct_decision(history)
```

`InvestmentDecision` is an immutable derived domain view. Its stable observable surface includes at least:

```text
decision_id
need_id
subject
scope
version
created_at
history
```

Callers do not normally create a Decision through arbitrary public `InvestmentDecision(facts=...)` construction. `reconstruct_decision(history)` is the one explicit durable-history validation/reconstruction boundary and rejects invalid mixed identity/order/fact-ID/transition histories.

Package exports contain only intentional stable domain contracts. Realization helpers remain private.

Historical duplicate Decisions are preserved. Duplicate Need grounding is surfaced as explicit reconciliation-required state/diagnostic; the domain does not silently merge, delete, rename, or pick a winner.

---

## 13. Minimal cross-boundary identity surfaces

The approved R2 component-boundary plan originally earned `src/polaris/domain/decisions/` and intentionally prohibited speculative scaffolding. This completion design narrowly amends that plan because two externally owned identities are now required by the frozen Decision contract.

R2 therefore earns only these additional minimal identity surfaces:

```text
src/polaris/domain/portfolio.py   # canonical PortfolioId only; no Portfolio aggregate scaffold
src/polaris/domain/actors.py      # ActorId + Actor Attribution values only; no actor registry/security/governance scaffold
```

The Decision implementation belongs under:

```text
src/polaris/domain/decisions/
```

not the implementation-selected `src/polaris/domain/investment_decisions/` package created by #294.

This amendment does not authorize `common.py`, `shared.py`, generic `types.py`, a full Portfolio package, Security & Identity implementation, Governance implementation, an actor registry, or a generic authorization service.

---

## 14. Authorization boundary invariant for later Governance implementation

R2 does not implement Governance, but later Governance design and implementation must preserve this foundation boundary:

```text
AuthenticatedActorContext
        -> application authorization
        -> canonical ActorId
        -> Investment Authority Regime evaluation
           (actor + specific power + subject/scope + authority-effective time)
        -> power-specific canonical authority act only on successful authority evaluation
```

Do not collapse application permissions and investment authority behind one generic `AuthorizationService.can(actor, action, object)` semantic contract. Infrastructure may use common policy technology internally, but the inward/domain contracts must preserve the distinct meanings.

A regime grants specific powers to an attributable actor in a defined scope and time. It does not grant authority to an `ActorKind`, authentication role name, model/provider identity, or generic organizational label merely by classification.

---

## 15. Foundation implementation readiness

**FOUNDATION IMPLEMENTATION READINESS: PASS.**

The owner approved the complete recommendation set and the authorization refinement captured above. No material foundation choice identified by the post-#294 Attention sweep remains delegated to implementation.

Ticket #294 remains closed as truthful history for its original contract. Ticket #299 is the remediation vehicle that must execute this completed contract before #295 proceeds.

Before #299 source mutation begins, tracker authority must be reconciled to this completed contract, the `spec-278` branch must contain the current design authority, #299 must pass its implementation-readiness certification, and its Ticket baseline must be pinned. Implementation remains prohibited from choosing a materially different contract merely because another code shape would be convenient.