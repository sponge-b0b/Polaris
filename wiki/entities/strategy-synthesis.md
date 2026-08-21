# Strategy Synthesis (Entity ID: strategy-synthesis)

**Boundary Rationale:** Strategy synthesis has independent invariants around structured bull/bear/sideways hypotheses, deterministic candidate scoring, perspective weighting, synthesis, portfolio-manager handoff, trade packaging, and execution-risk guarding.
(source: owner-approved entity promotion)

### Strict Invariants

* Strategy synthesis follows the structured lifecycle from `StrategyEvidenceBuilder` to immutable `StrategyEvidenceContext`, bull/bear/sideways perspective agents, `StrategySynthesisAgent`, `PortfolioManagerAgent`, `TradePackager`, and `ExecutionRiskGuard`, because strategy selection must be comparable and auditable. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* Bull, bear, and sideways agents consume the same immutable evidence context and produce typed `StrategyHypothesis` outputs without communicating or voting among themselves, because each perspective must be independently auditable. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* `StrategyPerspectiveWeightingEngine` computes pre-synthesis plausibility weights and does not consume hypothesis outputs or make the final selection, because weighting evidence and choosing strategy are separate responsibilities. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* `StrategySynthesisAgent` is the only canonical hypothesis-comparison authority and uses deterministic candidate scoring; invalidated hypotheses score zero, because the final comparison must be reproducible. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* Strategy Advisory is a read-only, non-authoritative consumer of canonical strategy evidence and already-produced strategy artifacts; it cannot create or replace canonical `StrategyHypothesis` objects, participate in strategy selection, or alter downstream capital/governance authority, and the canonical strategy lifecycle must produce the same authoritative result when advisory is absent, disabled, or failed. (source: docs/adr/0024-strategy-synthesis-non-authoritative-advisory-boundary.md)
* Strategy Advisory runs once after canonical strategy synthesis as a dedicated workflow sibling to downstream portfolio management; no canonical strategy, portfolio, recommendation, trade-packaging, execution-risk, governance, or policy operation depends on advisory, and presentation/transport surfaces consume advisory output rather than generating it. (source: docs/adr/0025-strategy-advisory-workflow-placement.md)
* Strategy Advisory uses a dedicated typed result with `AVAILABLE`/`DEGRADED`/`UNAVAILABLE` status, a code-owned non-authoritative marker, optional narrative, and typed advisory findings; at runtime it consumes and binds to the completed canonical `StrategyEvidenceContext`, `StrategyHypothesis` values, and `StrategySynthesisDecision` that actually exist at that lifecycle point rather than depending on a pre-materialized decision-evidence packet. Its own claim-bearing output later receives a canonical `DecisionEvidencePacket` through normal materialization. It does not carry canonical strategy-selection fields or numeric advisory confidence, and model/runtime provenance remains outside the semantic payload. (source: docs/adr/0027-strategy-synthesis-advisory-runtime-source-binding.md)
* Risk placement is explicit: analytical and aggregate risk are upstream inputs; `PortfolioManagerAgent` creates portfolio allocation or rebalance intent rather than orders; `TradePackager` creates broker-neutral proposals; and `ExecutionRiskGuard` is the required execution-safety decision boundary, because risk semantics change across the lifecycle. (source: docs/current/platform-architecture-and-operations.md)

### Rejected Approaches

* **Free-form multi-agent debate as canonical strategy selection** — rejected because debate can aid explanation or research but cannot own canonical strategy selection unless it first produces typed hypotheses and delegates comparison to the structured synthesis path.
  Reconsider when: a future accepted decision defines typed debate outputs and preserves deterministic comparison authority.
  (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)

### Planned

* **Non-authoritative Strategy Advisory realization** — authority, workflow placement, semantic output contract, and runtime source-binding lifecycle accepted; implementation pending while evidence validation, model routing/prompt ownership, persistence/publication, and readiness contracts are resolved. (source: docs/adr/0024-strategy-synthesis-non-authoritative-advisory-boundary.md; docs/adr/0025-strategy-advisory-workflow-placement.md; docs/adr/0027-strategy-synthesis-advisory-runtime-source-binding.md)
* **Future strategy capabilities such as scenario expansion and watchlist workflows** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
