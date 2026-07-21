# Polaris Model Profile Policy

Polaris model names are split into two layers:

1. **Logical aliases** are Polaris contracts used by source code, typed settings,
   tests, evaluation records, telemetry, and operator runbooks.
2. **Concrete model bindings** are deployment/runtime choices owned by LiteLLM,
   environment variables, and deployment configuration.

Application, runtime, RAG, strategy, intelligence, evaluation, reporting, and
future MCP code must depend on logical aliases. Do not hard-code concrete local
or hosted model names as architectural defaults in those layers.

## Alias taxonomy

The `polaris-local-*` aliases are capability contracts. A deployment can point
those aliases at different concrete providers, but the alias meaning must remain
stable.

| Logical alias | Contracted capability | Default local binding in `config/litellm/config.yaml` | Primary Polaris settings |
| --- | --- | --- | --- |
| `polaris-local-fast` | Low-latency planning, query rewrite, and triage work. | `ollama_chat/qwen2.5:7b` | `RAG_QUERY_REWRITE_MODEL`, `RAG_ADAPTIVE_TRIAGE_MODEL` |
| `polaris-local-reasoning` | Heavier local reasoning where latency can be higher. | `ollama_chat/qwen3.5:4b` | `STRATEGY_PERSPECTIVE_REASONING_MODEL`, `RAG_HYDE_MODEL` |
| `polaris-local-structured` | JSON/schema-oriented outputs and routing decisions. | `ollama_chat/qwen2.5-coder:7b` | `STRUCTURED_OUTPUT_MODEL`, `RAG_ROUTE_SELECTION_MODEL`, `RAG_CRAG_GRADER_MODEL`, `RAG_CRAG_QUERY_REWRITE_MODEL`, `RAG_SELF_REFLECTION_MODEL` |
| `polaris-local-synthesis` | User-facing synthesis, strategy synthesis, and final RAG answers. | `ollama_chat/qwen2.5-coder:7b` | `DEFAULT_MODEL`, `STRATEGY_SYNTHESIS_MODEL`, `RAG_SYNTHESIS_MODEL` |
| `polaris-local-evaluation` | DeepEval judge calls and model-regression gate judging. | `ollama_chat/qwen2.5-coder:7b` | `DEEPEVAL_JUDGE_MODEL` when the judge provider is `litellm` |
| `polaris-local-optimization` | DSPy/prompt optimization jobs. | `ollama_chat/qwen2.5-coder:7b` | `DSPY_OPTIMIZATION_MODEL` |

Direct concrete aliases such as `qwen2.5:7b`, `qwen3.5:4b`,
`qwen3.5:9b`, `qwen2.5-coder:7b`, and `deepseek-r1:8b` may exist in the
LiteLLM config for manual diagnostics or explicit operator experiments. They
are not Polaris architectural defaults. DeepSeek-R1 is challenger-only until a
future approved replacement decision promotes it through the validation gate.

## Source defaults versus runtime bindings

`config/settings.py` defines the stable source defaults. Those defaults should
name Polaris aliases, not concrete model IDs. The current source defaults route:

- RAG query rewrite and adaptive triage to `polaris-local-fast`;
- RAG routing, CRAG grading, CRAG rewrite, and Self-RAG reflection to
  `polaris-local-structured`;
- RAG HyDE and strategy perspective reasoning to `polaris-local-reasoning`;
- RAG synthesis, strategy synthesis, and the general default model to
  `polaris-local-synthesis`;
- structured-output provider calls to `polaris-local-structured`;
- DSPy optimization to `polaris-local-optimization`.

Concrete model bindings belong in runtime configuration:

- local LiteLLM model routing: `config/litellm/config.yaml` plus the
  container/runtime environment;
- Polaris setting overrides: `POLARIS_*_MODEL` variables;
- production deployment config or secret-managed environment state.

Changing a concrete backend behind an existing alias is an operations/profile
change. Changing the alias contract, changing a source default to a different
alias, or making a challenger model canonical is a model replacement and must
pass the validation requirements below.

## Approved low-VRAM local profile

The approved local development profile targets predictable operation on an
8GB-VRAM machine. Its canonical properties are:

- LiteLLM routes Polaris aliases to the low-VRAM Ollama-backed bindings listed
  above.
- `POLARIS_LITELLM_MAX_CONCURRENCY` defaults to `1`.
- `POLARIS_DEEPEVAL_MAX_CONCURRENCY` defaults to `1`.
- `POLARIS_LITELLM_TIMEOUT_SECONDS` and `POLARIS_DEEPEVAL_TIMEOUT_SECONDS`
  default to `60` seconds.
- `POLARIS_LITELLM_REQUEST_BUDGET_TOKENS` defaults to `4096`.
- `POLARIS_LITELLM_REJECT_MODEL_FALLBACK` defaults to `true`.
- Operator-facing validation should report timeout and low-VRAM viability,
  including whether the requested candidate requires more VRAM than the machine
  can provide.

Raise concurrency, token budgets, or model size only after validating the active
machine and model set. Do not normalize a larger local model by changing source
defaults; change the deployment profile and then run the replacement gate before
using it as a canonical default.

## Production profile policy

Production may use hosted or larger self-hosted models without source-code
changes. The production policy is:

- preserve the same logical alias contracts consumed by Polaris code;
- bind those aliases to production-approved concrete provider/model names in the
  LiteLLM deployment or production settings;
- keep credentials, API keys, tokens, passwords, and authenticated connection
  strings in environment variables or the approved secrets manager, never in
  source, tests, plans, or documentation;
- keep `POLARIS_LITELLM_REJECT_MODEL_FALLBACK=true` unless an approved
  operations exception explicitly accepts visible fallback metadata;
- validate production overrides with the model-regression gate before treating
  the profile as canonical.

This lets production bind `polaris-local-synthesis` or a future neutral alias to
a hosted model while application, RAG, strategy, and evaluation code continue to
call the same typed capability boundary.

## No-silent-fallback behavior

Silent alias/model fallback is prohibited for model replacements. The LiteLLM
client compares the requested model alias with the response model. When fallback
is detected and `POLARIS_LITELLM_REJECT_MODEL_FALLBACK=true`, Polaris raises a
model fallback error instead of returning a potentially different model's output
as if it came from the requested alias.

If fallback rejection is disabled for a deliberate diagnostic profile, fallback
metadata must remain visible in the result metadata and telemetry. That mode is
not sufficient to validate a canonical default replacement.

## Reasoning-trace safety

Raw model-internal deliberation is not a Polaris business record. Chain-of-
thought, thinking blocks, scratchpads, hidden reasoning, and similar reasoning
trace artifacts must remain at the model boundary and must not enter:

- typed domain contracts;
- persistence records or curated RAG records;
- RAG citation evidence;
- reports, CLI output, MCP/customer responses, or other presentation output;
- Langfuse or telemetry observations by default.

The LLM boundary sanitizes high-signal reasoning markers. Strict JSON/schema
paths fail closed when reasoning text contaminates structured output, and unsafe
or ambiguous reasoning traces are rejected rather than parsed or published.

This policy does not prohibit curated business rationale. A typed strategy
hypothesis, recommendation rationale, or risk explanation may be persisted only
after it has crossed the boundary as publishable, non-hidden content and remains
subject to normal source, evidence, lineage, and projection rules.

## Model-regression validation gate

Exploratory smoke tests are useful for diagnostics, but they cannot produce
a replacement-validation pass signal. A default model/profile change becomes
validation-ready only after a `replacement_validation` run of
`ModelReplacementValidationGate` passes every required section:

1. static/config boundary checks;
2. structured-output checks;
3. RAG quality, grounding, and prompt-injection checks;
4. strategy hypothesis and synthesis checks;
5. execution-risk and recommendation-explanation checks;
6. DeepEval execution with persisted run and metric results;
7. Langfuse projection acceptance for observations/results;
8. local operations readiness, including timeout, low-VRAM fit, and conservative
   concurrency expectations;
9. executable local-operations behavior from model-regression cases tagged
   `local_operations`.

The gate uses the canonical `model_regression` dataset slice, which is the
bounded golden model-gate slice covering structured output, RAG quality and
grounding, prompt injection, strategy synthesis, recommendation explanations,
execution risk, and local operations. The default minimum replacement-gate
operation timeout is `30` seconds; local profiles should normally keep the
existing `60` second LiteLLM and DeepEval timeouts unless a validated profile
requires a different value.

Replacement validation is all-or-nothing for replacement mode: any failed,
skipped, or unsupported section prevents a validation pass. Unsupported
local-operations behavior must be reported with target-type and case reasons
rather than being counted as passed behavior. The gate emits validation evidence
only; it is not a governance approval subsystem and does not mutate source
defaults or production aliases. `exploratory_smoke` mode may run the same style
of checks for operator learning, but its result scope is smoke-only.

For the cross-boundary readiness matrix and live-service validation prerequisites,
see [Model Allocation Readiness Check](model_allocation_readiness.md).

## Change checklist

Before changing a canonical alias/default/profile:

1. Identify whether the change is only a concrete runtime binding or a Polaris
   alias contract/source-default change.
2. Keep credentials and authenticated endpoints out of source, docs, tests, and
   plans.
3. Confirm fallback rejection remains enabled for replacement validation.
4. Confirm reasoning-trace guards still fail closed for structured and
   persistence-bound paths.
5. Seed or verify the canonical `model_regression` evaluation cases.
6. Run the replacement gate in `replacement_validation` mode with DeepEval and
   Langfuse configured.
7. Persist the gate result and record the validated profile in
   deployment/runtime configuration rather than in application code unless the
   source alias contract itself intentionally changed.
