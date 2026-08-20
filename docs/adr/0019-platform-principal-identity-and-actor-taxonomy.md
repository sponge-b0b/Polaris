---
status: accepted
---

# Canonical Principal Identity and Actor Taxonomy

## Context

Polaris already has transport authentication and actor-like attribution seams, but it does not yet have one canonical platform identity contract. MCP Streamable HTTP authenticates a bearer token without producing a durable platform identity, while runtime control records `requested_by` as a free-form string. Future API, UI, scheduler, service, and multi-principal use would otherwise force transports and subsystems to invent incompatible meanings for identity.

Identity must remain distinct from authentication, authorization, governance/risk authority, execution correlation, and component identity. Polaris is intentionally single-tenant at the deployment boundary, but it must support multiple human and non-human principals within that deployment.

## Decision

Polaris will use a minimal immutable domain-owned `Principal` contract whose stable identity consists of:

- an opaque deployment-scoped `principal_id`; and
- a `kind` drawn from exactly `HUMAN`, `SERVICE`, or `SYSTEM`.

`principal_id` is not an email address, username, bearer token, API key, OAuth/OIDC subject, session identifier, trace identifier, workflow identifier, or execution identifier.

`HUMAN` represents a person acting through Polaris. `SERVICE` represents independently authenticated automation or an external/service integration. `SYSTEM` represents platform-initiated action for which no human or service principal is the effective actor.

Polaris will not define `AGENT`, `EXTERNAL_CLIENT`, or `ANONYMOUS` as principal kinds in the trunk. AI agents and runtime components execute under an effective human/service/system principal while retaining their ordinary workflow, node, service, or component identity separately. External clients authenticate as a human or service principal. Unauthenticated state is represented by the absence of a principal rather than by a synthetic anonymous identity.

Authentication credentials resolve to a `Principal`; credentials are never themselves principal identity. Transport- or deployment-specific authenticators may change without changing the canonical principal.

Principal identity remains separate from roles, permissions, authorization decisions, risk/governance authority, authentication/session state, and trace/execution correlation. Mutable display or authentication metadata does not become part of the stable identity contract. A change of principal kind creates a new principal rather than mutating identity semantics.

Canonical human and service principal identities are durable Polaris records with PostgreSQL as their authoritative registry. Platform-defined system identities resolve through the same `Principal` contract. Existing free-form actor fields such as workflow-control `requested_by` are implementation-pending migration targets for typed principal attribution or the richer actor context established by subsequent identity/access decisions.

## Rationale

A small typed principal contract gives every future transport and subsystem one meaning for "who or what is acting" without coupling the domain to a login mechanism or provider. Keeping credentials, roles, governance authority, and execution correlation outside `Principal` prevents identity from becoming an overloaded security or workflow object.

Three actor kinds are sufficient for the intended single-tenant, multi-principal platform. An `AGENT` principal would blur the existing rule that models and intelligence components do not acquire independent platform authority. `EXTERNAL_CLIENT` describes a transport/integration shape rather than an actor class, and an `ANONYMOUS` principal would convert missing authentication into a potentially authorizable identity.

A durable deployment-local identity survives credential rotation and future authentication-provider changes while remaining compatible with self-hosted, managed single-tenant, and enterprise/on-prem deployments.

## Consequences

- Authorization can depend on one typed principal contract rather than transport credentials or free-form actor strings.
- Future authentication adapters must map credentials to canonical principals instead of leaking provider identity into application/domain/runtime code.
- Human, service, and system actions can be attributed distinctly without pretending automation is a human.
- AI agents retain workflow/component identity but do not become independently authorized principals.
- Existing actor-like string fields require migration when the identity/access implementation is realized.
- The decision does not yet define authorization policy, resource ownership, authentication adapter mechanics, identity propagation, or Living Entity Wiki topology; those remain separate decisions under Wayfinder #182.
