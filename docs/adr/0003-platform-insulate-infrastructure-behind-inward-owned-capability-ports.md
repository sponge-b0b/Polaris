---
status: accepted
---

# Insulate infrastructure behind inward-owned capability ports

## Context

Polaris will depend on replaceable infrastructure and external systems such as durable persistence, asynchronous follow-up, model providers, Evidence sources, authoritative Portfolio State sources, execution observations, identity, secrets, scheduling, observability, and distribution.

If application or domain contracts mirror PostgreSQL, a message broker, a model SDK, or another vendor API, the technology choice becomes an inward architectural dependency and weakens the ports-and-adapters boundary. Conversely, abstracting every library behind an interface would create unnecessary indirection and abstraction bloat.

## Decision

Polaris architecture owns required semantics and guarantees. Adapters own vendors, protocols, infrastructure products, and replaceable implementation patterns.

Ports are introduced across boundaries of ownership, authority, infrastructure, or meaningful volatility. They express Polaris capabilities such as durable atomic persistence, authoritative observation, model reasoning, authenticated actor resolution, or durable asynchronous follow-up rather than exposing vendor operations or native types.

PostgreSQL is the initial/reference persistence adapter for 0.2.0, not the persistence architecture. Required asynchronous follow-up is likewise technology-neutral: an outbox, durable queue, broker, event bus, CDC relay, or another mechanism is valid only if it satisfies the inward contract for durability, atomic registration where required, recovery, failure visibility, and idempotent business effect.

An event bus is not prohibited as infrastructure; what is prohibited is making a universal event bus or replay stream the product spine or business source of truth.

## Rationale

This keeps domain and application semantics stable as infrastructure evolves while still allowing each adapter to use technology-specific strengths internally. It avoids both vendor lock-in at the core boundary and lowest-common-denominator abstractions that cripple useful database, broker, or model-provider capabilities.

## Consequences

- domain/application contracts must not leak vendor SDK types, ORM sessions, SQL expressions, broker-native messages, or similar adapter representations without explicit architectural justification;
- replacing an adapter may require new schema, migrations, operational migration, or deployment configuration, but should not require redefining Investment Decision or application use-case semantics;
- adapter contract tests must prove semantic guarantees rather than merely exercise vendor calls;
- architecture tests must enforce dependency direction and vendor insulation;
- pure internal helpers and ordinary libraries do not earn ports merely because they are theoretically replaceable.
