# Application Use Cases for the Investment Decision Lifecycle

**Status:** Proposed  
**Release:** 0.2.0  
**Primary entity:** `application-use-cases`  
**Roadmap milestone:** R2 — Durable decision kernel and historical truth  
**Purpose:** Define the R2 application command/query contracts, transaction boundaries, idempotency, concurrency behavior, and cross-entity seams for the Investment Decision lifecycle.

## Authority

This design refines:

- [`../current/platform-architecture-0.2.0.md`](../current/platform-architecture-0.2.0.md);
- [`platform-domain-interaction-map.md`](platform-domain-interaction-map.md);
- [`investment-decisions-lifecycle-model.md`](investment-decisions-lifecycle-model.md);
- [`investment-decisions-r2-decision-kernel-component-boundaries.md`](investment-decisions-r2-decision-kernel-component-boundaries.md);
- [`../product/requirements-0.2.0.md`](../product/requirements-0.2.0.md);
- accepted ADRs under [`../adr/`](../adr/).

It does not introduce an alternate domain model. Application use cases coordinate entity-owned behavior and technology-neutral ports.

---

# 1. R2 application surface

R2 exposes a deliberately small application surface around Decision lifecycle truth.

Conceptual command responsibilities:

```text
initiate_decision
revise_decision_subject
revise_decision_scope
defer_decision
resume_decision_work
record_substantive_resolution
externally_resolve_decision
supersede_decision
initiate_renewed_decision
```

Conceptual query responsibilities:

```text
get_decision
get_decision_history
get_decision_as_known_at
find_unresolved_decisions_for_context
```

Names are semantic responsibilities, not mandated Python symbols.

R2 does not expose Recommendation, Governance, Action Intent, Attention, or Learning commands.

---

# 2. Command envelope

Every mutating R2 command carries a small application-owned envelope independent of database/message technology.

The semantic envelope contains:

- operation/idempotency identity;
- command kind;
- attributable initiating context;
- requested effective time when caller legitimately knows it, otherwise application clock time;
- expected Decision version for mutations of an existing Decision;
- command-specific payload.

The envelope must not contain:

- ORM session;
- SQL transaction;
- broker message object;
- workflow/job identity as business identity;
- vendor SDK request type.

Technical request/work IDs may be carried separately for observability/correlation.

---

# 3. Application result model

Commands return semantic results only after required durable commit succeeds.

A successful result contains the minimum useful combination of:

- affected Investment Decision ID(s);
- resulting lifecycle state;
- resulting domain version(s);
- committed lifecycle fact identity/identities where useful;
- whether the result was newly committed or returned from an idempotent replay.

Queries return application-owned Decision Memory/read models rather than persistence rows.

---

# 4. Error model

R2 application callers must be able to distinguish deterministic business/application outcomes.

At minimum:

| Error meaning | Caller implication |
|---|---|
| Decision not found | Target identity does not exist. |
| Invalid lifecycle transition | Command is incompatible with current Decision state. |
| Concurrency conflict | Expected version is stale; caller must reload/re-evaluate. |
| Idempotency conflict | Same operation ID was reused with a different semantic request. |
| Resolution basis invalid/missing | Substantive resolution cannot proceed. |
| External-resolution basis invalid/missing | External Resolution cannot proceed. |
| Supersession conflict | Invalid predecessor/successor relation or concurrent terminalization. |
| Continuity conflict | Caller attempted a new/resume/renew relationship inconsistent with current terminal/unresolved state. |
| Persistence unavailable/commit failed | No success may be returned; committed state is unchanged or recovered according to adapter guarantees. |

Transport mapping of these outcomes belongs to future interfaces.

---

# 5. Initiate Decision use case

## Inputs

- operation ID;
- Decision Need content/origin;
- Decision Subject;
- Decision Scope;
- optional causal `renewed_from` Decision ID when this is explicitly renewed judgment after a terminal predecessor.

## Preconditions

- operation ID is valid and not already used for a different semantic request;
- `renewed_from`, when supplied, references a terminal Decision state permitted by the lifecycle design;
- initiation must not be presented as a retry of an existing unresolved Decision merely because Subject/Scope are similar.

## Coordination

1. normalize command/application metadata;
2. check idempotency receipt;
3. validate optional causal predecessor state;
4. ask Decisions domain to establish Decision Need + Investment Decision;
5. atomically persist the Decision Need, Decision current state, initial lifecycle fact, causal relationship, and command receipt;
6. return success only after durable commit.

## Idempotent replay

Retrying the same operation ID with the same semantic request returns the original Decision ID/result.

Reusing the operation ID with different Decision Need/Subject/Scope/causal data is an idempotency conflict.

---

# 6. Resume existing Decision use case

`resume_decision_work` is explicit continuation of a known unresolved Decision, not a search heuristic.

## Inputs

- operation ID;
- Investment Decision ID;
- expected version;
- optional resumption reason/context reference.

## Behavior

- if state is `DEFERRED`, append Resumption fact and move to `ACTIVE`;
- if already `ACTIVE`, a distinct new command should not manufacture another Resumption fact merely to say work continues; return an explicit already-active/no-transition outcome or reject according to final implementation API;
- terminal states are invalid;
- same operation retry is idempotent.

The application does not create a new Decision for a resume request.

---

# 7. Defer Decision use case

## Inputs

- operation ID;
- Decision ID;
- expected version;
- attributable Deferral reason;
- optional future Review Condition reference only when a current owner/type exists.

R2 does not invent the full Review Condition model merely to decorate Deferral.

## Behavior

- `ACTIVE` → `DEFERRED`;
- terminal state → invalid;
- already `DEFERRED` under the same operation → idempotent replay;
- a new Deferral command against already deferred state does not silently overwrite the prior Deferral reason.

Later Review Conditions may trigger Attention, but they do not reopen resolved Decisions.

---

# 8. Subject/Scope revision use cases

R2 must preserve `DEC-003`/`DEC-004`: Decision Subject and Scope are distinct from Decision identity.

For a known unresolved Decision, explicit revision commands may update current Subject/Scope while appending immutable history.

Rules:

- only `ACTIVE` or `DEFERRED` Decisions may be revised;
- revision keeps the same Decision ID;
- the command must not infer that changed scope creates a new Decision;
- if the caller determines the coherent unresolved choice itself changed, it must use explicit new/superseding Decision behavior instead of hiding that change as a Scope revision;
- terminal Decisions are immutable.

---

# 9. Substantive Resolution use case

This command establishes the **Decisions-side lifecycle consequence** of an attributable resolution owned elsewhere.

## Inputs

- operation ID;
- Decision ID;
- expected version;
- typed resolution-basis reference;
- effective time;
- optional Decision-lifecycle summary.

## Trust boundary

The application command is an internal coordination contract, not an R2 public human API for self-asserted authority.

The resolution-basis reference must originate from an approved business owner/category. In later milestones, `governance-authority` will normally provide a Human Investment Decision reference where substantive human judgment resolves the Decision.

R2 may exercise the contract in deterministic tests through a trusted fixture; it must not create a fake Human Investment Decision record.

## Coordination

1. load current Decision + expected version;
2. validate the supplied resolution-basis reference category;
3. apply domain `RESOLVED` transition;
4. atomically persist the lifecycle change + idempotency receipt;
5. when later Governance is in scope, coordinate both owner facts in one application transaction when atomicity is required by the use case.

---

# 10. External Resolution use case

## Inputs

- operation ID;
- Decision ID;
- expected version;
- attributable external-resolution basis/explanation;
- optional external fact reference;
- effective time.

## Behavior

- `ACTIVE`/`DEFERRED` → `EXTERNALLY_RESOLVED`;
- no Human Investment Decision is created;
- no Action Intent is created;
- no Recommendation is manufactured;
- terminal Decision → invalid;
- late-recorded external facts preserve both effective and recorded time.

---

# 11. Supersede Decision use case

Supersession is one semantic transaction spanning two Investment Decisions owned by the same domain entity.

## Inputs

- operation ID;
- predecessor Decision ID + expected version;
- successor Decision Need;
- successor Subject;
- successor Scope;
- attributable Supersession reason/effective time.

## Coordination

1. load predecessor and verify unresolved state/version;
2. check operation idempotency;
3. create new successor Decision ID and initial facts;
4. apply terminal `SUPERSEDED` transition to predecessor referencing successor;
5. establish inverse successor relationship to predecessor;
6. atomically persist both Decisions, lifecycle facts, relationships, Decision Need, and command receipt;
7. return both IDs and resulting versions.

No observer may see a committed state where predecessor is superseded but the successor does not exist, or successor exists as the superseding Decision while predecessor remains unsuperseded.

---

# 12. Initiate Renewed Decision use case

Renewal applies only after the predecessor is already terminal through substantive or External Resolution.

## Inputs

- operation ID;
- predecessor Decision ID;
- new Decision Need;
- new Subject/Scope;
- attributable reason renewed deliberate judgment is required.

## Behavior

- predecessor remains unchanged and terminal;
- successor gets a new Decision ID;
- successor records `renewed_from` relationship;
- predecessor history is not copied or mutated;
- if predecessor is still unresolved, the command is rejected; caller must resume/supersede as appropriate.

---

# 13. Query contracts

## 13.1 Get current Decision

Returns an application-owned view containing:

- Decision ID;
- Decision Need summary/reference;
- current Subject/Scope;
- current lifecycle state;
- version;
- creation/terminal timestamps where applicable;
- renewal/Supersession relationships;
- no persistence-native representations.

## 13.2 Get Decision history

Returns lifecycle facts in deterministic per-Decision sequence order, with effective and recorded times preserved.

## 13.3 Get Decision as known at

Input: Decision ID + knowledge cutoff.

Behavior:

- include only lifecycle facts committed no later than cutoff;
- reconstruct state from that subset;
- do not include later-recorded facts even if their effective time is earlier;
- return explicit not-yet-known/not-yet-existing state when appropriate.

## 13.4 Find unresolved Decisions for context

R2 may expose a query that returns candidate `ACTIVE`/`DEFERRED` Decisions filtered by stable Subject/Scope/Portfolio-related criteria needed by future Attention or user navigation.

This query does **not** decide whether a new observation is semantically the same Decision. It supplies candidates; the caller/use case makes an explicit continuity choice.

---

# 14. Transaction patterns

## 14.1 Single-Decision mutation

```text
load Decision + version
      ↓
check idempotency
      ↓
domain transition
      ↓
atomic commit:
  current state
  + immutable fact
  + command receipt
      ↓
return committed result
```

## 14.2 Supersession

```text
load predecessor
      ↓
validate unresolved + expected version
      ↓
create successor + supersession change
      ↓
ONE semantic transaction:
  predecessor state/fact
  + successor need/state/fact
  + relationship
  + command receipt
```

## 14.3 Future cross-owner resolution

```text
Governance creates authoritative human-decision fact
      +
Decisions records resulting substantive resolution
      ↓
ONE application transaction when atomicity is required
```

R2 designs the coordination seam now; it does not prematurely implement Governance persistence.

---

# 15. Idempotency contract

Operation identity belongs to an application command, not to an Investment Decision universally.

For each retryable command, durable persistence must preserve enough information to distinguish:

1. operation unseen → execute;
2. operation already committed with same semantic request → return prior result;
3. operation already committed with materially different request → `IdempotencyConflict`.

A canonical semantic request fingerprint may be used internally, but the application contract is the behavior above, not a particular hashing algorithm.

Idempotency receipts are technical/application durability facts and must not become Investment Decision identity.

---

# 16. Optimistic concurrency contract

Mutations of existing Decisions require `expected_version`.

Adapter behavior must provide compare-and-set equivalence:

```text
commit only if current_version == expected_version
```

If another command committed first:

- no partial current/history mutation from the stale command may remain;
- stale command receives `ConcurrencyConflict` with enough information to reload;
- caller decides whether to retry/re-evaluate based on new state;
- application does not silently apply stale intent to a newer version.

---

# 17. Clock and time source

Application code owns establishment of recorded/commit time through an inward-owned clock abstraction only if deterministic testing or external effective-time handling requires it.

Do not create a generic infrastructure clock framework speculatively. A small injectable time source is sufficient when needed.

Caller-supplied effective time is accepted only where semantically legitimate and must not replace commit/recorded time.

---

# 18. Persistence ports required by R2

The application layer requires two narrow semantic capabilities:

## Decision command store

A capability to:

- load current Decision state/version;
- inspect existing idempotency result;
- atomically commit one Decision change set;
- atomically commit the Supersession two-Decision change set;
- preserve command result/receipt for retry semantics.

## Decision memory reader

A capability to:

- load current Decision view inputs;
- load ordered lifecycle history;
- reconstruct/read as-known-at views;
- query unresolved candidate Decisions by bounded criteria.

The exact interfaces should remain as small as implementation use requires. R2 does not introduce generic CRUD repositories or a platform-wide Unit of Work solely because those patterns are common.

---

# 19. Application testing decisions

Use deterministic in-memory/fake implementations of the inward-owned R2 persistence capabilities.

Application tests cover externally observable command/query behavior rather than private method structure.

Required cases include:

- initiation retry returns same Decision;
- initiation same operation/different payload conflicts;
- Deferral/resumption preserves Decision ID and history;
- stale expected version conflicts;
- substantive resolution requires trusted attributable basis;
- External Resolution does not create human judgment;
- terminal Decision cannot reopen;
- renewed Decision creates new linked ID;
- Supersession is all-or-nothing across predecessor/successor;
- historical query excludes later-recorded facts;
- persistence failure never returns successful command result.

Fakes must implement the same semantic contract as the PostgreSQL adapter, not a looser convenience API.

---

# 20. Requirements traceability

| Requirement | Application consequence |
|---|---|
| `GF-001`, `GF-005` | Commands use first-class Decision identity; technical attempt IDs remain separate. |
| `DEC-001`–`DEC-004` | Explicit initiate/resume/renew/supersede contracts prevent accidental identity replacement. |
| `DEC-006` | Dedicated Deferral/resumption behavior. |
| `DEC-008` | Dedicated External Resolution command with no Human Investment Decision side effect. |
| `DEC-009`–`DEC-011` | Terminal guards plus new-ID renewal/Supersession contracts. |
| `DEC-012` | History/as-known query contracts. |
| `REL-*` | Durable command semantics, retry safety, failure visibility, recovery expectations. |
| `TMP-*` | Effective and recorded time remain separate in command/history contracts. |
| `AS-001`–`AS-005` | Application test suite exercises full lifecycle scenarios. |
| `AS-022` | Ports/fakes/application code remain independent of `legacy/`. |

---

# 21. Out of scope

This design does not define:

- web/CLI/MCP API mapping;
- authentication provider;
- Human Investment Decision implementation;
- Recommendation/Evidence/Portfolio domain internals;
- asynchronous follow-up for R2, because no R2 command currently requires it;
- PostgreSQL/ORM/migration library;
- generic application bus/mediator/CQRS framework;
- workflow engine;
- event-sourcing framework.

---

# 22. Spec-readiness gate

This design is Spec-ready only when review confirms:

1. each R2 command has deterministic inputs, preconditions, result, retry, and concurrency semantics;
2. Supersession atomicity is explicit;
3. substantive resolution does not let R2 fabricate Governance-owned authority facts;
4. query semantics distinguish current, history, and as-known-at views;
5. ports are capability-oriented rather than PostgreSQL-shaped;
6. no implementation Spec must invent transaction or idempotency behavior.
