---
status: accepted
---

# Provider-Neutral Authentication and Credential Resolution Boundary

## Context

Polaris has a canonical `Principal` identity and a provider-neutral authorization boundary, but transport and deployment credentials still lack one canonical path into that identity model. Current MCP Streamable HTTP compares one configured bearer token and then forwards the request without producing a `Principal`; trusted stdio intentionally uses process trust rather than a token.

Without an authentication boundary, future CLI, MCP, API, UI, scheduler, service, and identity-provider integrations could leak credential semantics into application/runtime code, treat provider subjects or tokens as durable identity, or invent incompatible rules for trusted local execution.

Authentication must establish identity without becoming authorization, governance, session UX, or credential storage. Raw secrets must terminate at the security boundary; downstream platform semantics operate on canonical principals and non-secret authentication context.

## Decision

Polaris will own a provider-neutral authentication boundary in the security layer. Transport- and deployment-specific authenticators may consume credential material or an explicitly configured trusted-execution binding, but successful authentication resolves to the canonical domain `Principal` through a typed, non-secret authentication context.

The authentication context may carry the resolved principal plus non-secret method/binding metadata needed for later propagation and audit, such as authentication method, a stable binding identifier, authentication time, and expiry when applicable. Exact propagation and durable-attribution requirements remain owned by the subsequent identity-propagation decision.

Raw bearer tokens, API-key secrets, passwords, session cookies, access/refresh tokens, private keys, and equivalent credential material terminate at the authentication boundary. They must not enter application, runtime, authorization, governance, workflow evidence, persistence audit records, traces, or telemetry.

Authentication bindings map an external credential/provider identity or trusted execution binding to a durable Polaris `principal_id`; credentials and external subjects are not themselves principal identity. Provider claims such as external roles do not automatically become Polaris authorization state. Polaris remains authoritative for principal status and Polaris role assignment unless a later explicit architecture decision establishes trusted synchronization.

Authentication is fail-closed. Missing, invalid, expired, revoked, disabled, or otherwise unresolvable credential/binding state must reject a protected operation before authorization. A configured authentication mechanism must not silently fall through to another mechanism after failure. Public endpoints require no principal rather than synthesizing an anonymous one.

The current MCP HTTP bearer credential will migrate to a bearer authenticator whose configured binding resolves to a dedicated `SERVICE` principal. Credential rotation must not create a new principal. Trusted MCP stdio remains credential-free at the protocol level but resolves through an explicit trusted-local binding to a configured `SERVICE` principal rather than anonymous or `SYSTEM` identity.

Local interactive CLI execution resolves through an explicitly configured trusted-local binding to a `HUMAN` principal. Local automation resolves to a `SERVICE` principal. Genuinely platform-initiated work originates through trusted composition/runtime paths as a platform-defined `SYSTEM` principal; `SYSTEM` does not require fake credentials and still receives no authorization bypass.

Authentication must honor principal active/disabled state and, where applicable, credential binding revocation and expiry. Browser login flows, session cookies, refresh-token lifecycle, MFA, password recovery, OAuth/OIDC/SAML provider selection, and similar interface-specific mechanisms remain deferred until an outward interface requires them.

Authentication telemetry may record non-secret dimensions such as success/failure, method, resolved principal identifier on success, safe binding identifier, failure category, timestamp, and correlation identifiers. Outward failures should remain intentionally non-diagnostic with respect to credential validity details, and credential material must remain redacted.

## Rationale

A provider-neutral authentication boundary completes the credential-to-principal side of the identity/access trunk without coupling the domain to one login or identity-provider technology. Keeping credentials out of downstream contracts reduces secret exposure and preserves the distinction among authentication, identity, authorization, governance, and execution correlation.

Explicit trusted-local bindings let Polaris preserve its current local-first MCP and CLI operating model without pretending local execution is anonymous or universally `SYSTEM`. Durable principal identity survives credential rotation and future authenticator changes.

Deferring browser/session/provider-specific login machinery avoids building an IAM product before an outward interface creates a real requirement, while the stable authentication contract leaves those adapters straightforward to add later.

## Consequences

- All protected transports and execution origins must resolve identity through the canonical authentication boundary before authorization.
- Credential parsing/extraction may remain transport-specific, but identity resolution and binding semantics may not be transport-local authority.
- Raw credentials and provider tokens must not propagate beyond authentication or appear in durable platform evidence/telemetry.
- External identity/provider claims do not silently become Polaris roles or permissions.
- MCP HTTP bearer authentication becomes a credential-to-`SERVICE`-principal binding; trusted stdio becomes an explicit trusted-local `SERVICE` binding.
- Local human CLI and automation receive distinct `HUMAN` and `SERVICE` principals; truly platform-originated work uses canonical `SYSTEM` identity.
- Authentication failures are terminal before authorization and do not fall back to alternate authenticators.
- Revocation/expiry semantics are required where a credential type supports them; full session/login UX remains deferred.
- Identity propagation, durable actor attribution, and final Identity & Access wiki topology remain to be decided under Wayfinder #182.