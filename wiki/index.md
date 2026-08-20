# Living Entity Wiki

This is the authoritative registry of active architectural entities for Polaris. Use it for entity routing, categories, implementation state, and coarse discovery anchors. Entity pages preserve durable derived knowledge and cite their architectural sources inline.

## Entities

| Entity | Category | Implementation | Routing Anchors | Summary |
|---|---|---|---|---|
| [Domain Contracts & Data Semantics](entities/domain-contracts-data-semantics.md) | Domain | present | `domain` | Semantic contract layer for typed internal data, precision, scores, and authority metadata across the platform. |
| [Identity & Access](entities/identity-access.md) | Security | pending | — | Canonical principal identity, authentication, authorization, security-context propagation, ownership-sensitive access facts, and actor/security attribution. |
| [Runtime & Workflow Platform](entities/runtime-workflow-platform.md) | Runtime Platform | present | `core/runtime`, `core/workflow` | Canonical execution trunk for workflow facade, runtime graph execution, runtime context, events, replay, and control hooks. |
| [Dependency Composition](entities/dependency-composition.md) | Runtime Platform | present | `core/bootstrap`, `core/workflow/bootstrap` | Composition-root and dependency-scope policy for runtime, service, CLI, MCP, and test entry paths. |
| [Application Services & Output Curation](entities/application-services-output-curation.md) | Application Services | present | `application/services`, `application/projections` | Use-case orchestration and curated projection of completed runtime outputs into durable domain records. |
| [Data Integration & Providers](entities/data-integration-providers.md) | Integration | present | `integration/providers`, `integration/clients` | Provider protocols and vendor/client adapters that normalize external-system access before data reaches typed services. |
| [Persistence & Curated Records](entities/persistence-curated-records.md) | Persistence | present | `core/storage/persistence`, `application/persistence` | PostgreSQL-backed system-of-record boundary for completed runs, curated records, repositories, and rebuildable projections. |
| [Platform-Native RAG & Retrieval](entities/platform-native-rag-retrieval.md) | RAG | present | `application/rag`, `integration/providers/rag` | Derived retrieval pipeline from curated PostgreSQL records into RAG documents, chunks, vector/graph projections, and answer generation. |
| [Intelligence & Decision Support](entities/intelligence-decision-support.md) | Intelligence | present | `intelligence`, `workflows/definitions` | Analytical reasoning workflows for portfolio, market, risk, strategy, recommendation, and report-oriented decision support. |
| [Strategy Synthesis](entities/strategy-synthesis.md) | Intelligence | present | `intelligence/strategy`, `domain/strategy` | Structured bull/bear/sideways hypothesis lifecycle, deterministic synthesis, portfolio handoff, trade packaging, and execution-risk guarding. |
| [Governance, Authority & Decision Evidence](entities/governance-authority-decision-evidence.md) | Governance | present | `application/governance`, `domain/authority` | Decision authority, risk-authority reviewability, contestability, residual-risk acceptance, and evidence/audit semantics. |
| [Decision Evidence Packets](entities/decision-evidence-packets.md) | Governance | present | `domain/decision_evidence`, `application/decision_evidence` | Canonical typed evidence packet semantics for material governed decisions and their durable audit records. |
| [Governance Approval Lifecycle](entities/governance-approval-lifecycle.md) | Governance | present | `application/governance`, `core/runtime/governance` | Audit records, review tasks, immutable review decisions, residual-risk acceptance, and release decisions for governed outputs. |
| [Telemetry, Observability & Trace Lifecycle](entities/telemetry-observability-trace-lifecycle.md) | Observability | present | `core/telemetry`, `application/observability` | Operational events, trace identity lifecycle, metrics/logs/traces, observability storage, and backend projections. |
| [Interfaces & External Transports](entities/interfaces-external-transports.md) | Interfaces | present | `interfaces`, `mcp_server` | User and external entrypoints that adapt transport requests into canonical services and runtime workflows. |
| [MCP Server](entities/mcp-server.md) | Interfaces | present | `mcp_server` | MCP transport for LLM hosts, with strict request/response models and delegation into canonical platform services. |
| [AI Model Operations & Evaluation](entities/ai-model-operations-evaluation.md) | AI Operations | present | `core/llm`, `application/evaluations` | Model-access operations, structured-output adapters, evaluation cases/runs/metrics, prompt optimization, and AI observability projections. |
| [Model Gateway & Profile Policy](entities/model-gateway-profile-policy.md) | AI Operations | present | `core/llm`, `config/litellm` | Logical model aliases, profile policy, LiteLLM routing, fallback constraints, and provider-gateway ownership. |
| [Backtesting & Simulation](entities/backtesting-simulation.md) | Backtesting | present | `application/services/backtesting`, `integration/providers/backtesting` | Deterministic simulation capability around the canonical runtime, provider selection, simulated ledger, and backtest metrics. |

## Cross-Cutting Discovery

These documents are genuinely cross-cutting discovery starting points; they do not replace entity-page citations or the active entity registry.

* [Platform Architecture and Operations](../docs/current/platform-architecture-and-operations.md) — current cross-cutting platform architecture and operations overview.
* [Platform Architecture Ownership Ledger](../docs/current/platform-architecture-ownership-ledger.md) — current cross-cutting ownership, storage-class, and projection rules.
* [Runtime Events, Telemetry, and Trace Propagation ADR](../docs/adr/0003-platform-runtime-events-telemetry-trace-propagation.md) — accepted cross-cutting runtime-event and trace-propagation decision.
* [Future Architecture Roadmap](../docs/proposed/platform-future-architecture.md) — proposed cross-cutting future direction.
