---
status: accepted
---

# Identity Propagation, Audit Attribution, and Architecture Ownership

## Context

Polaris now has accepted contracts for canonical principals, authentication, Cerbos-backed authorization, and single-tenant resource ownership, but it still needs one propagation and durable-attribution model that connects those decisions across request, runtime, governance, persistence, and observability boundaries. Without that model, future CLI, MCP, API, UI, scheduler, and service entrypoints could invent ambient current-user state, duplicate actor fields, or conflate principal identity with trace/execution identity.

The Living Entity Wiki also lacks a first-class owner for this now-coherent concern even though identity and access has become the primary subject of multiple accepted ADRs and materially constrains several existing entities.

## Decision

Authenticated entrypoints establish one immutable, non-secret request-scoped security context containing the canonical `Principal` and safe authentication context. Existing request-scoped dependency composition is the canonical carrier while execution remains inside the synchronous application boundary; Polaris will not introduce global, thread-local, context-variable, repository-local, or domain-global current-user authority.

Protected application/facade operations authorize against the current principal per protected operation. Authorization decisions are not transitively inherited by unrelated later operations, and internal workflow nodes do not re-authorize merely because identity is propagated. A later independently protected action requires its own authorization decision.

When work crosses an asynchronous, runtime, durable, governance, or independently protected boundary, identity becomes explicit typed actor attribution rather than ambient request state. The canonical attribution distinguishes an effective principal from an optional materially distinct initiating principal. Polaris will not introduce a generic delegation or impersonation chain in the trunk.

Workflow executions durably preserve their initiating principal. Actor-sensitive lifecycle transitions such as workflow control, governance review/approval, residual-risk acceptance, publication, and similar protected mutations persist the canonical principal responsible for that action where the actor materially explains the durable state transition. Derived records should reuse existing provenance instead of duplicating actor fields indiscriminately.

Durable protected mutations must remain reconstructable to the canonical authorization decision that permitted them where that decision materially explains the mutation. Canonical authorization evidence remains distinct from governance/risk decision evidence even when governance records reference it.

Authentication success does not require a second universal durable authentication-audit record for every request. Canonical protected-operation evidence may retain safe authentication method/binding identifiers when useful, while authentication failures ordinarily remain sanitized security telemetry. Raw credentials and provider tokens remain prohibited from durable evidence and telemetry.

Principal identity remains distinct from trace, span, event, workflow, and execution identity. Logs and traces may correlate opaque principal and authorization-decision identifiers when useful, but metrics must not use principal identifiers as high-cardinality labels. Credentials, tokens, mutable external identity claims, and other secrets remain excluded.

Existing free-form actor strings are migrated to canonical principal attribution only when deterministically resolvable. Historical values that cannot be resolved safely remain explicitly legacy/unresolved rather than being guessed into HUMAN, SERVICE, SYSTEM, or ownership semantics. New actor-sensitive writes use canonical principal attribution after realization.

Identity & Access is promoted to a first-class Living Entity Wiki boundary under a new `Security` category. The boundary owns canonical principal identity, authentication/credential resolution, authorization policy/evaluation, request security context, ownership-sensitive access facts, and actor/security attribution. It does not absorb governance/risk authority, persistence ownership, telemetry/trace ownership, multitenancy, interface login/session UX, or the broader Security & Trust Boundary work identified separately by the platform trunk audit.

## Rationale

Request-scoped identity is convenient and already aligned with Polaris dependency composition, but ambient identity becomes unsafe once work outlives or escapes the request. Converting to explicit typed attribution at runtime/durable boundaries preserves provenance and replayability without forcing every internal call to carry transport state.

Selective durable attribution preserves meaningful auditability without adding `created_by` fields everywhere. Linking protected durable mutations to canonical authorization decisions provides reconstructable security evidence while keeping authorization distinct from governance.

The Identity & Access concern now satisfies the wiki promotion rules: it is the primary subject of multiple accepted ADRs, has independent invariants, and materially fans into interfaces, runtime, persistence, governance, and observability without fitting cleanly inside any one existing entity.

## Consequences

- Request-scoped security context is the only ambient carrier and remains confined to the application/request boundary.
- Runtime, asynchronous, durable, governance, and independently protected work receives explicit actor attribution.
- Actor attribution distinguishes effective and optional initiating principals without a generic delegation chain.
- Protected durable mutations can be reconstructed to their canonical authorization decisions where materially required.
- Workflow nodes do not perform redundant authorization unless they initiate a new protected operation.
- Principal identity remains separate from trace/execution/event identity and from governance authority.
- Legacy free-form actor values are never guessed into canonical principals.
- `Identity & Access` becomes a pending Living Entity Wiki entity in the new `Security` category.
