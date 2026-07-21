# Spec-review readiness verification for #34

Date: 2026-07-21
Parent follow-up: #25, for original spec #14

## Scope

This note records the final targeted readiness check for the local model allocation
and validation-gates spec-review follow-up. The check was intentionally targeted
at the changed seams from #26 through #33. A full pytest suite was not run by
default because the follow-up changed bounded documentation, evaluation,
strategy, reasoning-trace, reporting, and MCP seams with service-free unit
coverage.

No optional live validation was run. If live validation is requested later, list
required services first and report the live results separately from the required
service-free verification. Likely services for optional validation include
PostgreSQL, Qdrant, Neo4j, LiteLLM, Ollama, Langfuse, Prometheus, Jaeger, and
Grafana, depending on the chosen live scenario.

## Nine original findings mapped to outcomes

| Finding from #25 | Resolved by | Outcome |
| --- | --- | --- |
| 1. Reasoning-trace safety was only partially enforced across the required sink list. | #32 and #33 | Reusable reasoning-trace sanitization now protects typed, durable, curated, report, MCP, and customer-facing publication sinks. Complete safe reasoning blocks are stripped; unsafe/unclosed traces fail closed where appropriate; reasoning-key payload fields are excluded recursively. |
| 2. Strategy aliases were recorded as metadata rather than clearly driving model execution. | #31 | Strategy policy is now explicit: current strategy paths are code-owned and do not execute LLM output. Runtime metadata exposes `strategy_model_execution_mode=not_executed`, `calculation_authority=code`, and `llm_output_authority=none` while preserving configured reasoning and synthesis aliases. |
| 3. Local-operations behavior existed in dataset coverage but was not meaningfully evaluated by the replacement gate. | #29 | The model replacement gate now reports local readiness and executable local-operations behavior, including timeout viability, low-VRAM fit, conservative concurrency expectations, passed/failed/skipped outcomes, and unsupported target types with reasons. |
| 4. Agent workflow changes appeared unrelated to the model-allocation spec. | #26 | Agent process guidance now tells implementers not to bundle unrelated agent workflow, skill, or repository-process changes with feature work unless the active ticket explicitly asks for them; necessary process work must be split into governed tracker items. |
| 5. Agent implementation-skill testing instructions conflicted with targeted-test policy. | #26 | Implementation guidance now instructs agents to use targeted checks tied to changed files, affected boundaries, and regression risks; it explicitly says not to run the full suite by default and to keep live validation separate. |
| 6. The model replacement gate constructed settings internally instead of receiving explicit dependencies. | #28 | `ModelReplacementValidationGate` now requires explicit settings/configuration through construction/composition and no longer constructs hidden settings/defaults during operational validation. |
| 7. Strategy model configuration used hidden default fallback behavior. | #30 | Strategy agents and synthesis nodes require explicit `StrategyModelConfig`; the DI/composition seam supplies `StrategyModelConfig.from_settings(settings)`, and hidden module-global fallback behavior was removed. |
| 8. Model-regression coverage-tag definitions were duplicated across tests. | #27 | Required model-regression coverage tags are centralized in an evaluation-facing contract consumed by dataset and fixture tests. The canonical set still covers structured output, RAG quality, RAG grounding, prompt-injection/security, strategy hypothesis, strategy synthesis, recommendation/execution-risk, and local-operations behavior. |
| 9. Model replacement gate terminology used approval-shaped language without a complete approval subsystem. | #28 | Gate terminology and docs now distinguish validation pass/fail evidence from governance approval. Approval-shaped mode/result names were replaced with validation semantics. |

## Targeted service-free verification

Agent-process guidance assertions:

```text
python text assertions over .agents/skills/implement/SKILL.md
```

Formatting and linting over the targeted readiness file set:

```text
uv run ruff format --check <49 targeted Python files>
uv run ruff check <49 targeted Python files>
```

Static typing over the same targeted readiness file set:

```text
uv run mypy --explicit-package-bases <49 targeted Python files>
```

Targeted service-free tests:

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q -x \
  tests/evaluation/test_golden_dataset_fixtures.py \
  tests/unit/application/evaluations/test_evaluation_datasets.py \
  tests/unit/application/evaluations/test_model_replacement_gate.py \
  tests/unit/config/test_model_allocation_readiness.py \
  tests/unit/intelligence/strategy/test_bear_hypothesis_policy.py \
  tests/unit/intelligence/strategy/test_breadth_strategy_agents.py \
  tests/unit/intelligence/strategy/test_bull_hypothesis_policy.py \
  tests/unit/intelligence/strategy/test_sideways_hypothesis_policy.py \
  tests/unit/intelligence/strategy/test_strategy_model_alias_behavior.py \
  tests/unit/intelligence/strategy/test_strategy_synthesis_breadth_gating.py \
  tests/unit/intelligence/strategy/test_structured_hypothesis_baseline.py \
  tests/unit/application/projections/test_agent_signal_workflow_output_projector.py \
  tests/unit/application/rag/test_curated_rag_document_builder.py \
  tests/unit/core/storage/persistence/test_agent_intelligence_persistence_contracts.py \
  tests/unit/core/storage/persistence/test_agent_signal_persistence_contracts.py \
  tests/unit/domain/test_reasoning_trace_safety.py \
  tests/unit/application/reports/morning/test_morning_report_persistence.py \
  tests/unit/application/reports/morning/test_morning_report_renderer.py \
  tests/unit/mcp_server/contracts/test_structured_outputs.py \
  tests/unit/mcp_server/test_completed_run_get_tool.py \
  tests/unit/mcp_server/test_models.py \
  tests/unit/mcp_server/test_rag_tool.py \
  tests/unit/core/storage/persistence/test_agent_signal_persistence_serializer.py \
  tests/unit/core/storage/persistence/test_agent_intelligence_persistence_serializer.py \
  tests/unit/core/storage/persistence/test_postgres_agent_signal_persistence_repository.py \
  tests/unit/core/storage/persistence/test_postgres_agent_intelligence_persistence_repository.py \
  tests/unit/integration/providers/llm_structured_output/test_structured_output_provider.py \
  tests/unit/integration/clients/llm/test_litellm_gateway_client.py \
  tests/unit/application/rag/test_secure_rag_generation.py
```

Result: 203 passed in 2.57s.

## Remaining open risks before code review

- No required service-free risks remain from the nine original #25 findings.
- Optional live validation was not run and is not required for readiness. Live
  checks would add confidence in deployed provider/database wiring, but they
  should be treated as optional and reported separately because the acceptance
  criteria are covered by service-free targeted tests and source inspection.
- Repowise indexing was behind current HEAD during the review (`indexed_commit`
  `1803e1813acd` versus live HEAD `8d84b6526bd4`) and semantic embeddings were
  degraded due missing Gemini credentials. Risk checks still identified hotspot
  files; source and test verification were used as the authoritative readiness
  evidence.
