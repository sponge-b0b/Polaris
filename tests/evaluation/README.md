# Polaris Evaluation Test Suite

This directory contains the CI-oriented LLM evaluation suite for Polaris.

The default tests are deterministic and use fake provider outcomes so normal unit and CI jobs do not require a live judge model. Live DeepEval tests are marked with `live_deepeval` and are skipped unless explicitly enabled.

## Groups

- `eval_smoke`: fast deterministic checks for the canonical evaluation runner.
- `eval_rag_regression`: RAG metric and fixture regression checks.
- `eval_prompt_regression`: prompt/rubric regression checks.
- `eval_strategy_synthesis`: structured strategy-synthesis quality checks.
- `eval_security`: prompt-injection and safety-focused checks.
- `live_deepeval`: live judge-model checks, skipped by default.

## Live execution

Run live evaluation tests only after configuring a judge model:

```bash
POLARIS_RUN_LIVE_EVALS=true \
POLARIS_DEEPEVAL_ENABLED=true \
POLARIS_DEEPEVAL_JUDGE_PROVIDER=<provider> \
POLARIS_DEEPEVAL_JUDGE_MODEL=<model> \
uv run pytest -q tests/evaluation -m live_deepeval
```

Set `POLARIS_EVAL_REQUIRED=true` in release-gate jobs when missing evaluation configuration should fail instead of skip.
