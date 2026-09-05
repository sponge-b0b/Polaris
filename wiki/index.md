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

## Cross-Cutting Discovery

These documents are genuinely cross-cutting discovery starting points; they do not replace entity-page citations or the active entity registry.

* [Polaris 0.2.0 Greenfield Architecture](../docs/current/platform-architecture-0.2.0.md) — approved current system shape, ownership boundaries, dependency direction, and supporting architecture.
* [ADR 0001 — Use a modular monolith with ports and adapters](../docs/adr/0001-platform-use-modular-monolith-with-ports-and-adapters.md) — accepted cross-cutting system-shape decision.
* [ADR 0002 — Persist direct business truth with immutable history](../docs/adr/0002-platform-persist-direct-business-truth-with-immutable-history.md) — accepted cross-cutting business-truth and historical-memory decision.
* [ADR 0003 — Insulate infrastructure behind inward-owned capability ports](../docs/adr/0003-platform-insulate-infrastructure-behind-inward-owned-capability-ports.md) — accepted cross-cutting dependency and technology-insulation decision.
