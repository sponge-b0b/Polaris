---
status: accepted
---

# Provider-Neutral Authorization Contract with Cerbos PDP

## Context

Polaris now has a canonical `Principal` identity, but it still lacks one actor-resource authorization boundary. Existing runtime policy and governance engines answer broader platform and consequence questions; they do not establish whether a resolved principal may request a particular action on a particular resource.

Without a dedicated authorization contract, future MCP, CLI, API, UI, scheduler, and service integrations could embed role checks or transport-local permission rules. Polaris also needs authorization decisions to remain auditable and replayable without coupling application semantics to one authorization product.

Cerbos PDP provides deny-by-default policy evaluation over principals, actions, resources, roles, and contextual attributes, and can run as a self-hosted open-source component. It is therefore a strong implementation fit, but must remain behind a Polaris-owned boundary.

## Decision

Polaris will define a provider-neutral, fail-closed authorization contract based on a typed request containing:

- the canonical `Principal`;
- a stable Polaris action identifier;
- a typed resource reference; and
- only trusted, platform-derived authorization context required by policy.

The canonical outcome is binary: `ALLOW` or `DENY`. Missing or invalid principal, action, resource facts, policy state, or authorization-provider availability must deny the protected operation. `SYSTEM` principals receive no implicit bypass or superuser privilege.

Application semantics depend on stable actions and resources, not role names. Roles are policy configuration that group effective permissions. Trusted principal/resource attributes may support narrow contextual rules such as ownership, but Polaris will not introduce a general-purpose policy language or home-grown ABAC engine.

A Polaris-owned `AuthorizationService` and provider protocol will own the canonical evaluation boundary. Cerbos PDP is selected as the initial authorization provider behind a Cerbos-specific adapter. Application, runtime, domain, and transport code must not import Cerbos types or call Cerbos directly.

Baseline Cerbos policy will be source controlled, reviewable, and testable with the Polaris deployment. Cerbos Hub is optional and is not a required runtime dependency. Principal-specific policy exceptions, deep scoped-policy hierarchies, and use of Cerbos scope as disguised tenancy are not baseline Polaris authorization semantics.

Polaris remains authoritative for principal identity, principal status and role assignment, stable action/resource semantics, trusted resource facts, provider-independent authorization decisions, and canonical authorization audit evidence. PostgreSQL remains the system of record for durable Polaris authorization evidence.

Each canonical authorization decision must identify the effective policy state used to reach the result. When Cerbos is the provider, Polaris will record both the Cerbos semantic policy version where applicable and an immutable deployed-policy revision such as a source commit or policy-bundle digest. Provider correlation identifiers may be retained as diagnostic evidence, but provider audit logs do not replace the canonical Polaris authorization decision.

Authorization is evaluated at protected application/facade boundaries after authentication resolves a `Principal` and before runtime/domain policy and governance evaluation. An authorization `DENY` is terminal; governance cannot override it. Existing `PolicyEngine` and governance machinery retain their current responsibilities and are not replaced by Cerbos.

## Rationale

A provider-neutral Polaris contract keeps identity, application semantics, auditability, and future migration under platform control while avoiding the cost and security risk of implementing a policy evaluator, condition language, conflict semantics, and policy tooling from scratch.

Cerbos aligns closely with the desired `Principal + Action + Resource + trusted context -> ALLOW | DENY` model and supports incremental use of roles and resource conditions without forcing Polaris to become a multi-tenant SaaS IAM platform. Keeping Cerbos behind an adapter prevents vendor concepts from spreading through the trunk.

Source-controlled baseline policy fits Polaris's self-hosted and single-tenant deployment model, while optional Cerbos services can be adopted later without changing the canonical authorization contract.

## Consequences

- Protected operations gain one fail-closed authorization path shared by all transports.
- Transport-local role or permission checks are prohibited.
- Stable Polaris actions and resource semantics become the authorization vocabulary; role names remain policy configuration.
- Cerbos PDP becomes a deployment dependency for protected operations when it is the configured provider, and provider failure denies access.
- Authorization policy content requires source control, tests, and immutable deployment revision identity for audit/replay.
- Canonical authorization evidence is persisted by Polaris rather than delegated to Cerbos audit storage.
- Existing runtime policy and governance remain distinct downstream controls; governance cannot override an authorization denial.
- Ownership-specific trusted resource facts remain to be finalized by the resource-ownership decision under Wayfinder #182.
