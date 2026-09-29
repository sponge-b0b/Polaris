# Investment Intelligence (Entity ID: investment-intelligence)

**Boundary Rationale:** This boundary owns attributable analytical investment judgment: hypotheses, views, theses where applicable, assumptions, uncertainty, invalidation conditions, catalysts, decision alternatives, materially used Signals, Investment Recommendations, and Proposed Actions. It is distinct because analytical judgment must remain separate from human decision authority, deterministic rule results, and external factual truth.
(source: owner-approved entity boundary determination)

### Strict Invariants

* R3 durable Investment Intelligence preserves material business-semantic judgments rather than reasoning traces: materially relied-upon Investment Views, substantive meaningful-challenge results, material Decision Alternatives, Investment Recommendations, and explicit withholding judgments are durable and append-only, while prompts/model traces/transient brainstorming remain technical or transient. (source: docs/adr/0007-investment-intelligence-persist-material-judgments-not-reasoning-traces.md)
* Investment Intelligence may form and challenge investment judgment, but it does not own Human Investment Decision, Approval, execution authority, or external factual truth. (source: docs/current/platform-architecture-0.2.0.md)
* AI/model output is a draft analytical result with technical provenance; deterministic validation and application/domain acceptance are required before it becomes an attributable business judgment. (source: docs/current/platform-architecture-0.2.0.md)
* A model cannot establish Approval, Human Investment Decision, Mandate Exception, Residual-Risk Acceptance, or an external fact by asserting one in generated content. (source: docs/current/platform-architecture-0.2.0.md)
* Meaningful challenge is a product requirement, but no Bull/Bear/Sideways, multi-model, debate-round, agent-registry, or workflow-graph topology is architecturally mandatory. (source: docs/current/platform-architecture-0.2.0.md)


### Planned

* **R3 material analytical judgment contract** — accepted, implementation pending. Investment Views, meaningful challenge results, material Decision Alternatives, Investment Recommendations, and explicit Recommendation withholding judgments will be durable first-class business facts. Recommendation history is append-only; current support is derived rather than destructively stored; withholding remains distinct from both no Recommendation yet and hold/no-action Recommendation; Human Investment Decision and execution semantics remain outside Investment Intelligence. (source: docs/adr/0007-investment-intelligence-persist-material-judgments-not-reasoning-traces.md)
