# Strategy Synthesis (Entity ID: strategy-synthesis)

**Boundary Rationale:** Strategy synthesis has independent invariants around structured bull/bear/sideways hypotheses, deterministic candidate scoring, perspective weighting, synthesis, portfolio-manager handoff, trade packaging, and execution-risk guarding.
(source: owner-approved entity promotion)

### Strict Invariants

* Strategy synthesis follows the structured lifecycle from `StrategyEvidenceBuilder` to immutable `StrategyEvidenceContext`, bull/bear/sideways perspective agents, `StrategySynthesisAgent`, `PortfolioManagerAgent`, `TradePackager`, and `ExecutionRiskGuard`, because strategy selection must be comparable and auditable. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* Bull, bear, and sideways agents consume the same immutable evidence context and produce typed `StrategyHypothesis` outputs without communicating or voting among themselves, because each perspective must be independently auditable. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* `StrategyPerspectiveWeightingEngine` computes pre-synthesis plausibility weights and does not consume hypothesis outputs or make the final selection, because weighting evidence and choosing strategy are separate responsibilities. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* `StrategySynthesisAgent` is the only canonical hypothesis-comparison authority and uses deterministic candidate scoring; invalidated hypotheses score zero, because the final comparison must be reproducible. (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)
* Risk placement is explicit: analytical and aggregate risk are upstream inputs; `PortfolioManagerAgent` creates portfolio allocation or rebalance intent rather than orders; `TradePackager` creates broker-neutral proposals; and `ExecutionRiskGuard` is the required execution-safety decision boundary, because risk semantics change across the lifecycle. (source: docs/current/platform-architecture-and-operations.md)

### Rejected Approaches

* **Free-form multi-agent debate as canonical strategy selection** — rejected because debate can aid explanation or research but cannot own canonical strategy selection unless it first produces typed hypotheses and delegates comparison to the structured synthesis path.
  Reconsider when: a future accepted decision defines typed debate outputs and preserves deterministic comparison authority.
  (source: docs/adr/0007-strategy-synthesis-structured-hypotheses.md)

### Planned

* **Future strategy capabilities such as scenario expansion, watchlist workflows, and broader advisory behavior** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
