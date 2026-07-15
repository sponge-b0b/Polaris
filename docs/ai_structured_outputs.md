# AI Structured Outputs

Polaris uses **Instructor** as the canonical runtime structured-output adapter for selected LLM generation paths. Instructor enforces Polaris-owned Pydantic schemas at the LLM boundary so downstream services receive typed, validated objects instead of ad hoc JSON dictionaries.

Instructor is a boundary adapter. It is not a workflow runtime, RAG orchestrator, evaluator, prompt optimizer, prompt registry, or persistence layer.

## Canonical ownership

| Concept | Canonical owner | Notes |
| --- | --- | --- |
| Runtime structured output adapter | `integration.providers.llm_structured_output.InstructorStructuredOutputProvider` | Owns Instructor SDK usage, provider/model configuration, retry handoff, and typed provider results. |
| Structured-output request/result contracts | `integration.providers.llm_structured_output` | Polaris-owned contracts; runtime services depend on these, not on Instructor objects. |
| RAG answer schema | `application.rag.contracts.rag_structured_answer` | Instructor target schema for answer text, citations, quality flags, and safe refusal state. |
| RAG answer generation adapter | `integration.providers.rag.StructuredAnswerGenerationProvider` | Maps validated structured output back into the existing RAG generation result contract. |
| Runtime answer orchestration | `application.rag.generation.RagAnswerGenerator` | Owns secure prompt packaging, no-context behavior, prompt artifact resolution, metadata, and observability handoff. |
| Semantic evaluation | DeepEval evaluation services | Schema validity is not quality evaluation. DeepEval remains the canonical evaluator for faithfulness, grounding, citation support, and safety. |
| AI observability | Langfuse projection services | Observes prompt/artifact/model/schema metadata; does not replace PostgreSQL records. |
| System of record | PostgreSQL | Stores workflow evidence, curated records, evaluation records, prompt/program artifacts, and export jobs. |

## Runtime flow

```text
RagAnswerGenerator
        ↓
resolve approved prompt/program artifact or source-controlled fallback
        ↓
build secure generation prompt and allowed citation context
        ↓
StructuredAnswerGenerationProvider
        ↓
StructuredLlmProviderExecutor
        ↓
InstructorStructuredOutputProvider
        ↓
RagStructuredAnswer Pydantic schema
        ↓
RagAnswerGenerationResult / RagResult
        ↓
PostgreSQL query and answer logs + Langfuse AI-observability projection
```

The runtime path may consume an approved active prompt/program artifact, but it must not run DSPy optimization during normal workflow execution.

## Implemented settings

Use Polaris-prefixed variables for application configuration:

| Variable | Purpose |
| --- | --- |
| `POLARIS_STRUCTURED_OUTPUT_PROVIDER` | Structured-output provider name. Current default is Instructor-backed local model access. |
| `POLARIS_STRUCTURED_OUTPUT_MODEL` | Model used for Instructor structured-output calls. |
| `POLARIS_STRUCTURED_OUTPUT_MAX_RETRIES` | Polaris-owned retry budget for schema/provider failures. |
| `POLARIS_STRUCTURED_OUTPUT_TIMEOUT_SECONDS` | Structured-output call timeout. |

Unprefixed aliases exist for local compatibility, but project documentation and deployment manifests should prefer the `POLARIS_*` names.

## Guardrails

- Define a typed schema before adding a structured-output path.
- Keep Instructor imports inside the integration provider boundary.
- Do not pass arbitrary `dict[str, Any]` objects through application or intelligence internals.
- Preserve full LLM response text in typed fields; do not summarize or truncate long model responses in the adapter.
- Validate generated citations against allowed retrieved-context IDs before returning an answer.
- Treat schema conformance as necessary but insufficient; quality, grounding, and safety are measured by DeepEval.
- Emit Langfuse observations through the canonical AI-observability projection and include prompt/artifact/model/schema metadata.
- Persist canonical prompt/program artifacts and evaluation records in PostgreSQL, not in Instructor or local files.

## Focused verification

Useful checks after structured-output changes:

```bash
uv run pytest -q tests/unit/integration/providers/llm_structured_output
uv run pytest -q tests/unit/integration/providers/rag/test_structured_answer_generation_provider.py
uv run pytest -q tests/unit/application/rag/test_secure_rag_generation.py
uv run pytest -q tests/evaluation/test_structured_rag_output_evals.py
```

Run live model checks only when the required local model service is intentionally available.
