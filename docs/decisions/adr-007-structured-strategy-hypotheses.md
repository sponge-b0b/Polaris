# ADR-007: Structured Strategy Hypotheses

## Status

Accepted

## Context

Polaris strategy analysis previously mixed perspective scoring, synthesis, and downstream portfolio intent in ways that made it difficult to prove why a strategy was selected. A debate-style agent design was considered, but free-form agent-to-agent debate would make authority, replay, evidence attribution, deterministic testing, and persistence projection weaker.

Strategy decisions must be attributable to the same upstream evidence used by the workflow, replayable from runtime outputs, persisted as typed records, and projected into RAG and graph stores without introducing a second strategy stack.

## Decision

Polaris uses a structured-hypothesis strategy architecture instead of agent debate.

The strategy lifecycle is:

```text
canonical analytical node outputs
    ↓
StrategyEvidenceBuilder
    ↓
StrategyEvidenceContext
    ├── StrategyPerspectiveWeightingEngine
    ├── BullAgent
    ├── BearAgent
    └── SidewaysAgent
            ↓
StrategySynthesisAgent
            ↓
PortfolioManagerAgent
            ↓
TradePackager
            ↓
ExecutionRiskGuard
```

The Bull, Bear, and Sideways agents do not communicate with each other and do not vote. Each consumes the same immutable `StrategyEvidenceContext` and produces one typed `StrategyHypothesis` with supporting evidence, contradicting evidence, assumptions, invalidation conditions, strength, confidence, directional bias, and an evidence fingerprint.

`StrategyPerspectiveWeightingEngine` computes pre-synthesis `StrategyPerspectiveWeights` from the shared evidence context. These weights express prior perspective plausibility before hypothesis comparison. They are not a final strategy selection and must not consume Bull, Bear, or Sideways hypothesis outputs.

`StrategySynthesisAgent` is the only hypothesis-comparison authority. It evaluates the three hypotheses using the deterministic candidate-score policy:

```text
perspective weight
× hypothesis strength
× confidence
× assumption support
× (1 - contradiction burden)
```

Invalidated hypotheses receive a candidate score of zero. Candidate scores are normalized into synthesis weights, then existing breadth, market-event, portfolio, and risk constraints adjudicate the final typed `StrategySynthesisDecision`.

Risk placement is explicit:

- Analytical and aggregate risk are upstream inputs to `StrategyEvidenceBuilder` and `StrategySynthesisAgent`.
- Strategy synthesis decides portfolio posture, confidence, uncertainty, and thesis.
- Execution risk remains downstream after portfolio construction and trade packaging, where concrete proposed actions can be approved, resized, deferred, rejected, escalated, or skipped.

## Runtime, persistence, and projection boundaries

`StrategyEvidenceContext`, `StrategyPerspectiveWeights`, `StrategyHypothesis`, `StrategyHypothesisEvaluation`, and `StrategySynthesisDecision` are typed internal contracts. Runtime nodes serialize them only into `RuntimeNodeOutput` at the runtime boundary.

Runtime outputs are workflow evidence, not durable business records by themselves. The canonical workflow-output projection layer converts eligible strategy outputs into persisted records:

- `StrategyHypothesisRecord`
- `StrategySynthesisDecisionRecord`
- `StrategyHypothesisEvaluationRecord`
- downstream recommendation records where a strategy decision maps to portfolio/recommendation semantics

Curated RAG ingestion reads those persisted records, not raw runtime dumps. Qdrant and Neo4j remain rebuildable projections over PostgreSQL records and RAG documents.

## Rationale

Structured hypotheses are preferred because they provide:

- deterministic comparison instead of free-form debate authority;
- one shared evidence context for all perspectives;
- reproducible candidate scores, synthesis weights, and degradation reasons;
- clear separation between pre-synthesis perspective weighting and synthesis synthesis weighting;
- direct testability for invalidation, contradiction, ties, missing data, and all-invalidated scenarios;
- replayable runtime evidence and idempotent persistence projection;
- attributable RAG and graph relationships for “why,” “why not,” and “what would invalidate this decision.”

A debate-style architecture could still be useful for user-facing explanation or research, but it must not own canonical strategy selection unless it first produces typed hypotheses and delegates comparison to the canonical synthesis policy.

## Consequences

- Strategy perspective nodes may run concurrently after `StrategyEvidenceBuilder`.
- Bull, Bear, and Sideways agents must not inspect each other’s outputs.
- Synthesis must not silently skip missing mandatory hypotheses; it emits a typed degraded neutral decision when inputs are unavailable.
- Portfolio management uses the selected synthesis decision and synthesis weights. It must not infer allocation direction from raw hypothesis strength.
- Reports, RAG, graph projection, and recommendation persistence consume typed strategy decisions and records instead of generic legacy strategy payloads.
- Generic strategy signal compatibility contracts must not be reintroduced.

## Affected Modules

- `intelligence/strategy/hypothesis/`
- `intelligence/strategy/bull/bull_agent.py`
- `intelligence/strategy/bear/bear_agent.py`
- `intelligence/strategy/sideways/sideways_agent.py`
- `intelligence/strategy/weighting/strategy_perspective_weighting_engine.py`
- `intelligence/strategy/synthesis/strategy_synthesis_agent.py`
- `intelligence/strategy/synthesis/strategy_synthesis_policy.py`
- `intelligence/portfolio/management/portfolio_manager_agent.py`
- `application/projections/workflow_outputs/projectors/strategy.py`
- `application/rag/ingestion/curated_rag_structured_sources.py`
- `application/rag/projections/graph_projection.py`
- `workflows/definitions/reports/morning_report.py`
