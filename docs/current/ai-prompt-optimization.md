# AI Prompt and Program Optimization

Polaris uses **DSPy** as the canonical offline prompt/program optimization workbench. DSPy may propose candidate prompt/program artifacts from approved evaluation datasets, but it must not replace Polaris runtime orchestration, RAG services, workflow execution, DeepEval, Langfuse, or PostgreSQL.

DSPy is an optimization tool. It is not a production agent runtime.

## Canonical ownership

| Concept | Canonical owner | Notes |
| --- | --- | --- |
| Offline optimization application boundary | `application.ai_optimization.AiOptimizationService` | Coordinates dataset loading, candidate creation, evaluation, score summaries, and artifact persistence. |
| DSPy provider boundary | `integration.providers.ai_optimization.DspyOptimizationProvider` | Owns DSPy-specific signatures/modules and candidate artifact construction. |
| Evaluation scoring | DeepEval evaluation services | DeepEval remains the canonical scoring authority. DSPy does not define release quality by itself. |
| Prompt/program artifacts | PostgreSQL `ai_prompt_program_artifacts` records | Durable system of record for draft, approved, active, and retired artifacts. |
| Runtime artifact resolution | `application.ai_optimization.runtime_artifacts.ActiveAiPromptArtifactResolver` | Runtime consumes only approved active artifacts or source-controlled fallback prompts. |
| AI observability | Langfuse projection services | Receives trace, prompt, dataset, score, and artifact correlations. |

## Implemented CLI commands

The AI workbench is intentionally explicit and manual:

```bash
polaris ai optimize --target rag_answer_generation --dataset <dataset-name>
polaris ai artifacts list [--target rag_answer_generation] [--type dspy_compiled_prompt]
polaris ai artifacts approve <artifact-id> --approved-by <reviewer>
polaris ai artifacts activate <artifact-id>
polaris ai artifacts deactivate <artifact-id>
```

Approval and activation are separate operations. Approving an artifact does not change production runtime behavior. Activation is explicit and deactivates any currently active artifact for the same target and artifact type.

## Implemented settings

| Variable | Purpose |
| --- | --- |
| `POLARIS_DSPY_ENABLED` | Enables explicit DSPy workbench execution when set for the operator context. Normal runtime generation does not require this flag. |
| `POLARIS_DSPY_OPTIMIZATION_MODEL` | Model used by the DSPy optimization provider. |
| `POLARIS_DSPY_MAX_TRAINSET_CASES` | Upper bound on persisted evaluation cases used during one optimization pass. |
| `POLARIS_DSPY_ARTIFACT_RETENTION_DAYS` | Retention hint for prompt/program artifact cleanup policy. |

## Artifact lifecycle

```text
approved evaluation dataset in PostgreSQL
        ↓
polaris ai optimize
        ↓
DSPy candidate artifact
        ↓
DeepEval scoring and score reasons
        ↓
Langfuse trace/dataset/run correlation
        ↓
PostgreSQL draft artifact
        ↓
explicit review and approve
        ↓
explicit activate
        ↓
runtime resolver may use approved active artifact
```

The runtime uses active artifacts by reference. It must not invoke the optimizer, select a mutable `latest` prompt, or read unapproved local artifacts during workflow execution.

## Guardrails

- Do not import DSPy from runtime RAG services, workflow nodes, intelligence agents, MCP tools, or CLI rendering code.
- Do not treat a DSPy optimization score as a release gate unless it was produced through the canonical DeepEval evaluation path.
- Do not persist raw secrets, authenticated URLs, or unreviewed prompt bodies in artifact metadata.
- Do not overwrite source-controlled fallback prompts when activating an artifact; fallback remains the safe default when no approved active artifact exists.
- Do not create a second artifact store in Langfuse or local files. Langfuse may observe and compare; PostgreSQL remains authoritative.

## Focused verification

Useful checks after prompt/program optimization changes:

```bash
uv run pytest -q tests/unit/application/ai_optimization
uv run pytest -q tests/unit/integration/providers/ai_optimization
uv run pytest -q tests/unit/interfaces/cli/test_ai_command.py tests/unit/interfaces/cli/test_ai_command_service.py
uv run pytest -q tests/unit/core/storage/persistence/ai_artifacts
```

Run live PostgreSQL or model-backed optimization checks only after confirming required services are running.
