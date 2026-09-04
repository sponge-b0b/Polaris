# AI Model Operations & Evaluation (Entity ID: ai-model-operations-evaluation)

**Boundary Rationale:** This boundary owns model access policy, model-profile indirection, structured-output adapter semantics, evaluation datasets/runs/metrics, prompt optimization artifacts, and AI observability projections. It is meaningful because these rules govern how AI behavior is configured, tested, and observed across RAG and intelligence features.
(source: owner-approved entity boundary determination)

### Strict Invariants

* Evaluation datasets, cases, runs, metric results, thresholds, and Langfuse projections are owned by the evaluation services and PostgreSQL records, because model quality evidence must be reproducible and durable. (source: docs/current/ai-model-operations-evaluation-llm-evaluation.md)
* Production code must access DeepEval only through `integration.providers.llm_evaluation.DeepEvalEvaluationProvider`, because evaluation-provider specifics must not leak into workflow nodes, RAG, intelligence, CLI, MCP, or persistence code. (source: docs/current/ai-model-operations-evaluation-llm-evaluation.md)
* Langfuse export flows through `AiObservation`, `AiObservabilityProjector`, durable sink records, export queue processing, and `LangfuseSdkExportClient`, because Langfuse is an observability projection rather than a second result store. (source: docs/current/ai-model-operations-evaluation-langfuse-observability.md)
* Prompt optimization artifacts are durable PostgreSQL records, and runtime uses only approved active artifacts or source fallback, because optimization output cannot implicitly replace production prompt authority. (source: docs/current/ai-model-operations-evaluation-prompt-optimization.md)
* Structured-output SDK objects remain behind the provider boundary while Polaris contracts remain typed domain/application contracts, because SDK convenience must not define platform data semantics. (source: docs/current/ai-model-operations-evaluation-structured-outputs.md)

### Planned

* **Broader model platform capabilities for routing, fine tuning, evaluation, and AI observability** — proposed, not yet accepted. (source: docs/proposed/platform-future-architecture.md)
