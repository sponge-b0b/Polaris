  # Baseline Golden Evaluation Dataset Implementation Plan

  ## Summary

  Create a true Polaris baseline golden dataset with 100 curated, source-controlled evaluation cases, persisted into PostgreSQL and runnable through the existing DeepEval/Langfuse evaluation pipeline.

  Use this exact distribution:

   Dataset                                         Cases    Target type
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   golden_rag_questions                               25    rag_answer
  ────────────────────────────────────────────  ─────────  ───────────────────────────────
   rag_citation_support                               12    rag_answer
  ────────────────────────────────────────────  ─────────  ───────────────────────────────
   rag_security_prompt_injection                      13    rag_answer
  ────────────────────────────────────────────  ─────────  ───────────────────────────────
   morning_report_quality                             15    morning_report
  ────────────────────────────────────────────  ─────────  ───────────────────────────────
   strategy_synthesis_quality                         15    strategy_synthesis
  ────────────────────────────────────────────  ─────────  ───────────────────────────────
   recommendation_explanations                        12    recommendation_explanation
  ────────────────────────────────────────────  ─────────  ───────────────────────────────
   mcp_tool_responses + agent_task_completion    8 total    mcp_tool_response, agent_task

  The golden dataset source of truth will be deterministic JSONL fixtures under tests/evaluation/fixtures/, with PostgreSQL used as the durable runtime system of record after seeding.

  ## Key Implementation Changes

  1. [x] Expand deterministic fixture cases
      - Replace each current one-row fixture with curated multi-row JSONL data.
      - Keep existing dataset IDs and version v1; do not rename canonical datasets.
      - Use stable case IDs such as:
          - golden-rag-answer-001
          - rag-citation-001
          - rag-security-injection-001
          - morning-report-quality-001
          - strategy-synthesis-quality-001
          - recommendation-explanation-001
          - mcp-tool-response-001
          - agent-task-completion-001

      - Each case must include, at minimum:
          - case_id
          - target_type
          - input_text
          - actual_output
          - expected_output or rubric
          - retrieval_context where grounding is relevant
          - citation_context_ids where citation support is relevant
          - tags

      - Prefer deterministic synthetic-but-realistic financial scenarios over live market facts so the benchmark remains stable.

  2. [x] Strengthen fixture schema validation
      - Update evaluation fixture helpers/tests so all supported durable fields are validated, including:
          - source_record_ids
          - workflow_execution_id
          - langfuse_trace_id
          - langfuse_observation_id
          - retrieval_context
          - citation_context_ids

      - Enforce:
          - unique case IDs across all fixtures
          - non-empty expected output or rubric
          - target type matches dataset definition
          - citation cases include citation IDs
          - security cases include adversarial input or context tags
          - total case count is exactly 100
          - each dataset meets its assigned count

  3. [x] Add canonical dataset seeding support
      - Add a CLI command under the existing evaluation CLI, for example:
          - polaris eval datasets seed
          - optional: --dataset <name>
          - optional: --dry-run

      - The command must:
          - read canonical dataset definitions
          - load matching JSONL fixtures
          - persist EvaluationDatasetRecord and EvaluationCaseRecord through the canonical evaluation persistence repository
          - report dataset counts and case counts

  4. [x] Add baseline benchmark execution guidance
      - Document the intended baseline workflow:
          1. seed datasets into PostgreSQL
          2. confirm counts with polaris eval datasets list
          3. run selected datasets through DeepEval
          4. inspect persisted results with polaris eval results --run <run-id>
          5. drain Langfuse export jobs

      - Do not automatically run all 100 live DeepEval cases in normal CI.
      - Use deterministic provider tests in CI and reserve full DeepEval benchmark runs for explicit local/release-gate execution.

  5. [x] Update documentation
      - Update docs/llm_evaluation.md to define:
          - what Polaris means by “golden dataset”
          - why fixtures are the source-controlled baseline
          - why PostgreSQL is the durable runtime copy
          - how to seed, run, and inspect the benchmark
          - how to add a new golden case safely

      - Add a short “Golden Dataset Quality Rules” section:
          - cases must be reviewed, not bulk-generated blindly
          - expected outputs must be specific and attributable
          - cases must cover positive, negative, edge, and adversarial scenarios
          - benchmark changes require intentional review because they alter the platform baseline


  6. [x] Follow-up live verification and release gate
      - Run live PostgreSQL seeding verification against the configured local database.
      - Run one selected live DeepEval benchmark dataset and inspect persisted results.
      - Add a release-gate script that verifies fixture expectations, PostgreSQL seed/count parity, optional AI-observability health, and selected DeepEval run status.
      - Document the release-gate script in the LLM evaluation guide.

  7. [x] Add canonical dataset replacement semantics
      - Extend evaluation persistence bundles with explicit dataset-case replacement membership.
      - Make canonical fixture seeding detach stale cases from active dataset membership without deleting historical case records or metric results.
      - Confirm live PostgreSQL seeding brings all persisted canonical dataset counts back into parity with source-controlled fixtures.

  ## Test Plan

  - Add or update unit tests to verify:
      - total fixture case count is exactly 100
      - every canonical dataset has the assigned number of cases
      - every case ID is globally unique
      - every row validates into an EvaluationCase
      - dataset target types match canonical definitions
      - citation/security/report/strategy/recommendation-specific fields are present where required

  - Add CLI/service tests for:
      - polaris eval datasets seed --dry-run
      - idempotent seed behavior
      - seeded PostgreSQL case counts
      - polaris eval datasets list showing the expected persisted counts

  - Keep live DeepEval tests gated behind existing live-evaluation environment flags.

  ## Assumptions and Defaults

  - Use 100 cases as the baseline target.
  - Keep existing canonical dataset names and v1 version.
  - Treat JSONL fixtures as the reviewed source-controlled benchmark source of truth.
  - Treat PostgreSQL records as the durable operational copy used by CLI evaluation runs.
  - Do not use live market data as golden facts unless the facts are frozen into deterministic fixture text.
  - Do not change DeepEval metric thresholds as part of this work.
  - Do not require Langfuse to be running for fixture validation or seeding tests; Langfuse remains part of live evaluation/export verification.

  ## Step Results

  ### Step 1 — Expand deterministic fixture cases

  - Replaced the one-row evaluation fixtures with a 100-case baseline golden dataset across the existing canonical fixture files.
  - Added: 25 RAG answer-quality cases, 12 citation/grounding cases, 13 security/prompt-injection cases, 15 morning-report cases, 15 strategy-synthesis cases, 12 recommendation-explanation cases, 4 MCP tool-response cases, and 4 agent-task completion cases.
  - Preserved existing dataset names, dataset versions, and target types while adding stable case IDs, expected outputs or rubrics, retrieval context, citation context IDs where relevant, tags, and source metadata fields.
  - Updated the existing strategy-synthesis and prompt-regression fixture tests so they validate multi-row fixtures instead of the prior one-row baseline assumptions.
  - Verification:
      - JSONL validation script confirmed globally unique case IDs, required fields, non-empty expected output or rubric, and total count of 100.
      - `uv run ruff check tests/evaluation/test_strategy_synthesis_evals.py tests/evaluation/test_prompt_regression_evals.py` passed.
      - `uv run pytest -q --tb=short tests/evaluation/test_rag_regression_evals.py tests/evaluation/test_quick_smoke_evals.py tests/evaluation/test_security_evals.py tests/evaluation/test_strategy_synthesis_evals.py tests/evaluation/test_prompt_regression_evals.py` passed with 10 tests.

  ### Step 2 — Strengthen fixture schema validation

  - Updated `tests/evaluation/_helpers.py` so `evaluation_case_from_row()` now preserves all supported durable evaluation-case metadata fields: `source_record_ids`, `workflow_execution_id`, `langfuse_trace_id`, `langfuse_observation_id`, `retrieval_context`, and `citation_context_ids`.
  - Added `tests/evaluation/test_golden_dataset_fixtures.py` to validate the canonical 100-case fixture inventory against dataset definitions, expected per-dataset counts, globally unique case IDs, target-type alignment, required expected output or rubric, source lineage metadata, citation metadata, security/adversarial tagging, and workflow execution IDs for workflow-derived fixtures.
  - Added a focused preservation test proving parsed fixture rows round-trip through `EvaluationCase` and `EvaluationCaseRecord` without losing durable metadata fields.
  - Verification:
      - `uv run pytest -q --tb=short tests/evaluation/test_golden_dataset_fixtures.py` passed with 4 tests.
      - `uv run ruff check tests/evaluation/_helpers.py tests/evaluation/test_golden_dataset_fixtures.py tests/evaluation/test_strategy_synthesis_evals.py tests/evaluation/test_prompt_regression_evals.py` passed.
      - `uv run mypy tests/evaluation/_helpers.py tests/evaluation/test_golden_dataset_fixtures.py --explicit-package-bases` passed.
      - `uv run pytest -q --tb=short tests/evaluation/test_golden_dataset_fixtures.py tests/evaluation/test_rag_regression_evals.py tests/evaluation/test_quick_smoke_evals.py tests/evaluation/test_security_evals.py tests/evaluation/test_strategy_synthesis_evals.py tests/evaluation/test_prompt_regression_evals.py` passed with 14 tests.
      - `uv run graphify update .` completed and refreshed the code graph.

  ### Step 3 — Add canonical dataset seeding support

  - Added typed canonical dataset seeding contracts: `EvaluationDatasetSeedRequest`, `EvaluationDatasetSeedItem`, and `EvaluationDatasetSeedResult`.
  - Extended `EvaluationDatasetService` with `seed_canonical_datasets()` so fixture loading and persistence happen through the canonical application service and `EvaluationPersistenceRepository`, not directly in the CLI.
  - The seeding service now reads canonical dataset definitions, loads their deterministic JSONL fixtures, validates each row into `EvaluationCaseRecord`, persists `EvaluationDatasetRecord` and `EvaluationCaseRecord` through an atomic `EvaluationPersistenceBundle`, and supports `dry_run=True` without database writes.
  - Added the CLI command `polaris eval datasets seed` with `--dataset <name>` and `--dry-run` options, plus human-readable count reporting.
  - Added service and CLI tests covering dry-run counts, selected-dataset seeding, idempotent upsert behavior, command-service delegation, and the Typer command path.
  - Verification:
      - `uv run ruff check application/evaluations/contracts.py application/evaluations/evaluation_dataset_service.py application/evaluations/__init__.py interfaces/cli/services/evaluation_command_service.py interfaces/cli/commands/evaluation_command.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_evaluation_command.py --fix` passed.
      - `uv run ruff format application/evaluations/contracts.py application/evaluations/evaluation_dataset_service.py application/evaluations/__init__.py interfaces/cli/services/evaluation_command_service.py interfaces/cli/commands/evaluation_command.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_evaluation_command.py` completed.
      - `uv run mypy application/evaluations/contracts.py application/evaluations/evaluation_dataset_service.py interfaces/cli/services/evaluation_command_service.py interfaces/cli/commands/evaluation_command.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_evaluation_command.py --explicit-package-bases` passed.
      - `uv run pytest -q --tb=short tests/unit/application/evaluations/test_evaluation_services.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_evaluation_command.py tests/evaluation/test_golden_dataset_fixtures.py` passed with 26 tests.
      - `POLARIS_POSTGRES_PASSWORD=placeholder timeout 30s uv run polaris eval datasets seed --dry-run` rendered 8 datasets and 100 cases with zero writes.
      - `uv run pytest -q --tb=short tests/evaluation/test_golden_dataset_fixtures.py tests/evaluation/test_rag_regression_evals.py tests/evaluation/test_quick_smoke_evals.py tests/evaluation/test_security_evals.py tests/evaluation/test_strategy_synthesis_evals.py tests/evaluation/test_prompt_regression_evals.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/interfaces/cli/test_evaluation_command_service.py tests/unit/interfaces/cli/test_evaluation_command.py` passed with 36 tests.
      - `uv run graphify update .` completed and refreshed the code graph.

  ### Step 4 — Add baseline benchmark execution guidance

  - Updated `docs/llm_evaluation.md` with the canonical baseline benchmark execution workflow: seed canonical datasets into PostgreSQL, confirm persisted counts, run selected datasets through DeepEval, inspect persisted results by run ID, and verify Langfuse export-queue drain through AI-observability status.
  - Clarified that `polaris eval datasets seed --dry-run` should be used before non-dry-run seeding, and that `--dataset <dataset-name>` can seed a bounded dataset during local validation.
  - Documented that full 100-case DeepEval benchmark runs are explicit local or release-gate operations, not normal CI work; normal CI remains deterministic fixture validation and fake-provider/non-live evaluation coverage.
  - Clarified the current Langfuse boundary: export delivery is handled by the configured `AiObservabilityExportWorker` or deployment scheduler, while `uv run polaris observability ai-status` verifies queue health and backlog.
  - Verification:
      - `git diff --check docs/llm_evaluation.md .agents/plans/plan_golden_dataset_implementation.md` passed.

  ### Step 5 — Update documentation

  - Expanded `docs/llm_evaluation.md` with a dedicated golden dataset baseline section defining Polaris golden datasets as reviewed, versioned evaluation benchmarks and explaining the relationship between source-controlled fixtures and PostgreSQL operational copies.
  - Added “Golden Dataset Quality Rules” covering deliberate review, specific expected outputs and rubrics, attribution, scenario coverage, deterministic frozen facts, threshold discipline, and intentional review for benchmark changes.
  - Added “Adding a golden case safely” guidance for choosing the target type, adding stable JSONL fixture rows, preserving lineage metadata, running validation, dry-run seeding, bounded seeding, persisted-count checks, and live DeepEval validation only when intentional.
  - Verification:
      - `git diff --check docs/llm_evaluation.md .agents/plans/plan_golden_dataset_implementation.md` passed.


  ### Step 6 — Follow-up live verification and release gate

  - Ran live PostgreSQL seeding verification using the local configured environment:
      - `polaris eval datasets seed` completed successfully with 8 datasets and 100 fixture cases written.
      - `polaris eval datasets list` confirmed all canonical datasets were persisted.
      - The verification exposed one stale PostgreSQL case membership in `golden_rag_questions_v1`: the fixture source of truth has 25 cases, while the persisted operational copy currently reports 26 cases.
  - Ran a selected live DeepEval benchmark dataset:
      - `polaris eval run --dataset agent_task_completion` executed successfully through the CLI and produced run ID `eval_4f25a4b4caab4a6ead9acb7156360aa6`.
      - `polaris eval results --run eval_4f25a4b4caab4a6ead9acb7156360aa6` confirmed 8 persisted metric results in PostgreSQL.
      - The canonical run completed but its benchmark status was `failed` because all 8 metric results failed their current thresholds; Langfuse projection was attempted.
  - Added `scripts/run_baseline_evaluation_gate.py` as a release-gate entrypoint over the canonical evaluation CLI services.
      - The script validates DeepEval configuration, dry-run fixture expectations, PostgreSQL seed writes unless skipped, persisted case-count parity, optional AI-observability health, and selected DeepEval run status.
      - The script intentionally fails when persisted dataset membership no longer matches source-controlled fixture expectations.
  - Added `tests/unit/scripts/test_run_baseline_evaluation_gate.py` covering passing release gates, count mismatches, failed live run status, and skipped seed writes.
  - Updated `docs/llm_evaluation.md` with release-gate script usage.
  - Verification:
      - `uv run ruff check scripts/run_baseline_evaluation_gate.py tests/unit/scripts/test_run_baseline_evaluation_gate.py --fix` passed.
      - `uv run ruff format scripts/run_baseline_evaluation_gate.py tests/unit/scripts/test_run_baseline_evaluation_gate.py` completed.
      - `uv run mypy scripts/run_baseline_evaluation_gate.py tests/unit/scripts/test_run_baseline_evaluation_gate.py --explicit-package-bases` passed.
      - `uv run pytest -q tests/unit/scripts/test_run_baseline_evaluation_gate.py` passed with 4 tests.
      - `uv run python scripts/run_baseline_evaluation_gate.py --dataset agent_task_completion --skip-live-evaluation` passed against live PostgreSQL.
      - `uv run python scripts/run_baseline_evaluation_gate.py --skip-live-evaluation` correctly failed the all-dataset count gate because `golden_rag_questions_v1` currently has one stale persisted case.
  - Follow-up recommendation:
      - Add canonical seed replacement semantics that detach stale cases from a dataset when they are no longer present in the source-controlled fixture. This likely requires a small `core/storage/persistence/evaluation` repository contract update; it was not changed here because this follow-up request did not explicitly authorize modifying `core/`.

  ### Step 7 — Add canonical dataset replacement semantics

  - Added `EvaluationDatasetCaseReplacement` and `EvaluationPersistenceBundle.dataset_case_replacements` so canonical seed operations can express exact dataset membership as a typed persistence contract.
  - Updated `EvaluationDatasetService.seed_canonical_datasets()` to include one replacement contract per seeded canonical dataset.
  - Updated the PostgreSQL evaluation repository so `persist_evaluation_bundle()` atomically upserts datasets/cases and detaches stale cases whose `dataset_id` no longer appears in the source-controlled fixture case list.
  - The fix preserves historical case rows by setting stale `evaluation_cases.dataset_id` to `NULL`; it does not delete cases or cascade-delete historical metric results.
  - Updated the in-memory test repository and added unit coverage proving stale canonical dataset membership is replaced during seeding.
  - Updated `docs/llm_evaluation.md` to document exact canonical seed replacement semantics.
  - Live verification:
      - `uv run python scripts/run_baseline_evaluation_gate.py --skip-live-evaluation` now passes against live PostgreSQL.
      - All canonical persisted dataset counts now match fixture expectations: 8 datasets and 100 cases total, including `golden_rag_questions_v1` back to 25 persisted cases.
  - Verification:
      - `uv run ruff check core/storage/persistence/evaluation/evaluation_persistence_models.py core/storage/persistence/evaluation/__init__.py core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py application/evaluations/evaluation_dataset_service.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/core/database/test_evaluation_persistence_records.py --fix` passed.
      - `uv run ruff format core/storage/persistence/evaluation/evaluation_persistence_models.py core/storage/persistence/evaluation/__init__.py core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py application/evaluations/evaluation_dataset_service.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/core/database/test_evaluation_persistence_records.py` completed.
      - `uv run mypy core/storage/persistence/evaluation/evaluation_persistence_models.py core/storage/persistence/evaluation/__init__.py core/storage/persistence/repositories/postgres_evaluation_persistence_repository.py application/evaluations/evaluation_dataset_service.py tests/unit/application/evaluations/test_evaluation_services.py tests/unit/core/database/test_evaluation_persistence_records.py --explicit-package-bases` passed.
      - `uv run pytest -q tests/unit/application/evaluations/test_evaluation_services.py tests/unit/core/database/test_evaluation_persistence_records.py tests/unit/scripts/test_run_baseline_evaluation_gate.py` passed with 20 tests.
      - `uv run graphify update .` completed.

