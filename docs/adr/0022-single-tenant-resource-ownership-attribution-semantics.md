---
status: accepted
---

# Single-Tenant Resource Ownership and Attribution Semantics

## Context

Polaris is intentionally multi-principal within one deployment, but it is not being designed as shared-database or shared-runtime SaaS. The platform therefore needs explicit ownership semantics without allowing future interfaces, repositories, RAG projections, or authorization policy to infer that every durable record belongs to the principal who created or requested it.

The canonical `Principal` contract, Cerbos-backed authorization boundary, and authentication boundary are already accepted. Resource ownership must now be separated from both tenancy and actor attribution so future implementation does not introduce speculative `tenant_id` dimensions, universal owner fields, or transport-derived ownership.

## Decision

One Polaris deployment represents one organizational trust and data boundary. Ordinary domain, persistence, repository, RAG, cache, configuration, request-context, and authorization contracts must not introduce a tenant, organization, workspace, or equivalent dimension merely to preserve hypothetical shared-database multitenancy.

Durable resources are platform-owned by default. Shared analytical and operational state—including market and macro records, portfolio/account state, workflow definitions and runs, recommendations, strategy/risk evidence, governance and audit records, reports, canonical RAG records, projections, backtests, and replay evidence—does not acquire principal ownership merely because a principal initiated, created, reviewed, or published it.

Principal ownership is introduced only for resource types whose domain semantics inherently require private or principal-specific ownership, such as future private notes, personal preferences, saved views/searches, or notification settings. Such resource contracts carry an explicit non-null canonical principal reference such as `owner_principal_id`. Polaris will not add a generic owner field to every durable record.

Ownership semantics are defined by resource type. A platform-owned resource type needs no synthetic platform principal or nullable owner field. A principal-owned resource type requires resolvable canonical ownership. Missing or invalid required ownership is an authorization-resolution failure and must fail closed rather than being interpreted as shared, platform-owned, or owned by the caller.

Ownership is distinct from actor attribution. Fields and concepts such as `created_by`, `initiated_by`, `requested_by`, `reviewed_by`, `approved_by`, or `published_by` identify actors or lifecycle participation; they do not establish ownership. `SERVICE` and `SYSTEM` principals likewise do not own platform records merely because they created them. Final actor-propagation and attribution contracts remain owned by the subsequent identity-propagation decision.

Where ownership affects authorization, Polaris supplies it to the canonical authorization boundary only as a trusted platform-derived resource fact. Clients, transports, sessions, MCP payloads, and other untrusted request metadata may not assert canonical ownership. Cerbos may evaluate ownership facts but does not own or derive them.

Existing shared platform records remain platform-owned during migration and must not be backfilled with guessed human ownership. If a genuinely principal-owned legacy record is discovered and its owner cannot be established safely, implementation must require explicit resolution or deny ownership-sensitive access rather than guessing.

Generic sharing, delegation, ACL/membership infrastructure, ownership transfer, and shared-database/shared-runtime multitenancy are deferred until a concrete product requirement justifies them. Cerbos scopes, derived roles, resource attributes, or principal attributes must not be used to introduce an implicit tenancy hierarchy.

Introducing multitenancy in the future is an architecture-changing decision requiring explicit reconsideration of persistence keys and uniqueness, authorization resources, RAG isolation, provider credentials, cache identity, configuration, audit, observability, backup/restore, and deployment trust boundaries.

## Rationale

Deployment-level isolation matches Polaris's intended self-hosted, managed single-tenant, and enterprise/on-prem operating models while avoiding pervasive speculative tenancy cost. Platform ownership also matches the semantics of most analytical and operational records: they are installation state, not private documents owned by whoever happened to trigger them.

Separating ownership from attribution prevents authorization from inheriting accidental semantics such as "creator owns the workflow run" and lets actor evidence remain accurate for audit/governance without mutating resource ownership. Defining ownership by resource type avoids universal nullable-owner ambiguity and keeps the model lean.

## Consequences

- One deployment is one organizational trust/data boundary; ordinary contracts do not gain a speculative tenant dimension.
- Platform ownership is the default for shared analytical and operational state.
- Principal ownership exists only where resource semantics require it and is represented by an explicit canonical principal reference.
- No synthetic `PLATFORM` principal or universal owner field is introduced.
- Ownership-sensitive authorization receives only trusted Polaris-derived ownership facts and fails closed when required ownership cannot be resolved.
- Actor attribution remains independent of ownership and is finalized by the subsequent propagation/audit decision.
- Existing shared records remain platform-owned; migration does not guess human owners.
- Generic sharing/delegation/ownership-transfer infrastructure and shared-database multitenancy remain deferred.
- Cerbos scope and attributes must not become an implicit tenancy layer.
