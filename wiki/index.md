# Living Entity Wiki

This is the authoritative registry of active architectural entities for the greenfield Polaris system. Use it for entity routing, categories, implementation state, and coarse discovery anchors. Entity pages preserve durable derived knowledge and cite architectural sources inline.

The pre-greenfield registry remains historical donor/reference material under `legacy/v0_1/wiki/` and is not active authority for entity topology.

## Entities

| Entity | Category | Implementation | Routing Anchors | Summary |
|---|---|---|---|---|
| [Investment Decisions](entities/investment-decisions.md) | Domain | pending | — | First-class Investment Decision identity, lifecycle continuity, resolution, deferral, supersession, and renewal semantics. |
| [Evidence](entities/evidence.md) | Domain | pending | — | Attributable Evidence identity, provenance, temporal fitness, sufficiency, and judgment-support bindings. |
| [Investment Intelligence](entities/investment-intelligence.md) | Domain | pending | — | Attributable investment hypotheses, views, uncertainty, alternatives, signals, recommendations, and proposed actions. |
| [Portfolio & Risk](entities/portfolio-risk.md) | Domain | pending | — | Portfolio identity and state, exposure/allocation distinctions, projected consequences, Portfolio Risk, mandates, and deterministic constraints. |
| [Governance & Authority](entities/governance-authority.md) | Domain | pending | — | Policy, admissibility, power-specific authority acts, human investment judgment, contestability, and residual-risk acceptance. |
| [Action Continuity](entities/action-continuity.md) | Domain | pending | — | Post-human Action Intent and reconciliation between intended consequence and authoritative external activity. |
| [Learning](entities/learning.md) | Domain | pending | — | Outcome, Decision Evaluation, Lesson, and hindsight-faithful retrospective learning semantics. |
| [Application Use Cases](entities/application-use-cases.md) | Application | pending | — | Commands, queries, use-case coordination, transaction/idempotency semantics, and inward-owned capability ports. |
| [Durable Persistence](entities/durable-persistence.md) | Infrastructure | pending | — | Durable transactional business persistence, immutable history, concurrency, recovery, and replaceable storage adapters. |
| [Model Access](entities/model-access.md) | Infrastructure | pending | — | Replaceable model/provider access, structured draft responses, deterministic validation, retries, and technical provenance. |
| [External Facts](entities/external-facts.md) | Infrastructure | pending | — | Observation adapters for Evidence, authoritative Portfolio State, execution activity, and other externally owned facts. |
| [Background Work & Durable Follow-Up](entities/background-work-follow-up.md) | Infrastructure | pending | — | Scheduling, worker execution, and reliable post-commit asynchronous follow-up without business-identity ownership. |
| [Observability & Technical Provenance](entities/observability-provenance.md) | Infrastructure | pending | — | Execution correlation, model/source call provenance, diagnostics, sanitation, and replaceable observability backends. |
| [Security & Identity](entities/security-identity.md) | Infrastructure | pending | — | Authenticated actor context, application access control, secrets, and security mechanisms distinct from investment authority. |
| [Configuration](entities/configuration.md) | Infrastructure | pending | — | Domain-facing product configuration and isolation of technical/provider configuration from business semantics. |
| [Interfaces & Presentation](entities/interfaces-presentation.md) | Interfaces | pending | — | Thin human/machine surfaces over shared application commands, queries, and canonical decision truth. |

## Cross-Cutting Discovery

These documents are genuinely cross-cutting discovery starting points; they do not replace entity-page citations or the active entity registry.

* [Polaris 0.2.0 Greenfield Architecture](../docs/current/platform-architecture-0.2.0.md) — approved current system shape, ownership boundaries, dependency direction, and supporting architecture.
* [ADR 0001 — Use a modular monolith with ports and adapters](../docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md) — accepted cross-cutting system-shape decision.
* [ADR 0002 — Persist direct business truth with immutable history](../docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md) — accepted cross-cutting business-truth and historical-memory decision.
* [ADR 0003 — Insulate infrastructure behind inward-owned capability ports](../docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md) — accepted cross-cutting dependency and technology-insulation decision.
