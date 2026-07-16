---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code. Supports features, refactors, migrations, and environment configuration.
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code or configurations, testing, docs they might need to check, and how to verify it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. Test-Driven / Verification-Driven Development. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good verification design very well.

- Never overwrite a root-level global `PLANS.md` for separate features.
- Keep the original proposal separate when appending a Codex recommendation.
- Use Markdown checkboxes for executable tasks.
- Update only the active feature plan incrementally.
- During execution, treat that file as the source of truth and record completed work in its `### Task Results` section.
- Leave historical plans untouched.
- Use stepwise execution, complete one task, record its result, and wait for confirmation before the next.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `superpowers:using-git-worktrees` skill at execution time.

**Save plans to:** `.agents/plans/plan_<plan-name>.md`
- (Don't use the word "plan" in the plan name itself)
- (User preferences for plan location override this default)
- (Example: `.agents/plans/plan_full_core_telemetry_integration.md`)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file or infrastructure block should have one clear responsibility.
- You reason best about changes you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large monolithic configs or files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

A task is the smallest unit that carries its own verification cycle and is worth a fresh reviewer's gate. When drawing task boundaries: fold setup, configuration changes (`.env`, `docker-compose.yml`), schema migrations (`SQL`, `alembic`), scaffolding, and documentation steps into the task whose deliverable needs them; split only where a reviewer could meaningfully reject one task while approving its neighbor. Each task ends with an independently testable or verifiable deliverable.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes if possible):**
- "Write the failing test or isolation harness" - step
- "Run it to make sure it fails or reports the missing resource" - step
- "Implement the minimal code, script, migration, or config to pass verification" - step
- "Run the verification tools and make sure they pass cleanly" - step
- "Commit the discrete atomic change" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature/Objective/Project/Change Target Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds or updates]

**Architecture & Impact:** [2-3 sentences about approach, database impacts, environment modifications, or side-effects]

**Tech Stack & Tooling:** [Key technologies, languages, migration frameworks, or test runners involved]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section.]

---
```

## Task Structure

````markdown
### Task N: [Component / Subsystem Name]

**Overview:** [One sentence describing what this task does: what it builds, modifies, inspects, or verifies]

**Files / Targets:**
- Create/Extract: `exact/path/to/file.ext`
- Modify/Inspect: `exact/path/to/existing.ext:123-145`
- Test / Verify: `exact/path/to/test_or_verification_script.ext`

**Interfaces & Configurations:**
- Consumes: [what this task uses from earlier tasks — exact signatures, environment variables, database tables, or discoveries]
- Produces: [what later tasks rely on — exact function names, API endpoints, schema definitions, parameter types, or verified architectural constraints]

---
#### Choose ONE Track below based on Task Type:

### [TRACK A] For Implementation, Code, Migrations, or Config Changes
*Use this track when modifying system state or code.*

- [ ] **Step 1: Write the failing test or setup the reproduction/assertion failure**

```python
# (Or bash script, sql script, docker execution checking for the absence of the state)
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run verification to verify it fails**

Run: `pytest tests/path/test.py::test_name -v` (or `docker compose up`, `migrate check`, etc.)
Expected: FAIL with clear missing definition, connection error, or assertion failure

- [ ] **Step 3: Write minimal implementation or configuration**

```python
# (Or raw SQL migration, updated docker-compose YAML block, or .env template variables)
def function(input):
    return expected
```

- [ ] **Step 4: Run verification to verify it passes**

Run: `pytest tests/path/test.py::test_name -v` (or framework equivalents)
Expected: PASS with no side-effects or regressions

- [ ] **Step 5: Commit**

```bash
git add exact/path/to/changed_files
git commit -m "type: short descriptive message of change"
```

---

### [TRACK B] For Inspection, Discovery, Architecture Audits, or Investigation
*Use this track when the task requires exploring, verifying constraints, or analyzing existing code/logs without immediate state changes.*

- [ ] **Step 1: Define baseline assumption and target search/inspection commands**

Identify exactly what you are investigating (e.g., checking if an old legacy module imports a specific library, auditing a permission table structure, or checking active process logs).
Run: `grep -rn "pattern" ./src` (or `git log`, database schema inspect commands, etc.)

- [ ] **Step 2: Execute inspection and document the findings**

Run the inspection command. Map out constraints, verify if the architecture pattern matches the spec, or discover hidden dependencies.
Expected: Output must definitively prove or disprove the design assumption (e.g., "Confirming that `module_x` does not handle its own retries").

- [ ] **Step 3: Synthesize discovered interfaces, schema boundaries, or log traces**

Document the exact code references, file blocks, or layout constraints discovered so following implementation tasks can consume them with zero ambiguity. 

- [ ] **Step 4: Run cross-reference audit**

Double check the findings against the global project constraints to ensure no hidden compatibility conflicts or anti-patterns exist.

- [ ] **Step 5: Commit findings to project plans or logs (If applicable)**

```bash
# If documentation updates, architecture logs, or plan state shifts were recorded:
git add .agents/plans/
git commit -m "docs: document system discovery findings for [Component]"
```
````

## Task Results Structure

When a task is marked as completed, the executing agent must append a structured results block directly below the completed task definition. This block provides an unarguable audit trail for developers and automated continuous integration (CI) environments.

````markdown
### Task N Results: [Component / Subsystem Name]

**Status:** [completed | failed | blocked]

**What Changed:**
- [Bullet points describing exact code, configuration, or structural state changes]
- [For Track B Discovery tasks: Document the key findings, discovered interfaces, or architecture invariants]

**Key Files Touched:**
- `exact/path/to/modified_or_created_file.ext`
- `.agents/plans/plan_<name>.md` (if updating plan checklist tracking state)

**Verification Commands Run:**
```bash
# Provide exact terminal execution commands run to verify this step
uv run ruff check path/file.py
docker compose config --quiet
pytest tests/path/test.py -v
```

**Pass/Fail Summary:**
- [Result tool 1]: PASS/FAIL with [brief detail, e.g., "no lint issues found"]
- [Result tool 2]: PASS/FAIL with [brief detail, e.g., "all 24 focused unit tests passed"]

**Notes, Recommendations, and Service Requirements:**
- [Critical notes regarding high-churn files, deployment side-effects, or runtime dependencies]
- [Infrastructure conditions, e.g., "No live containers were started; validated configuration shape only"]
- [Security invariants, e.g., "Verified that credentials use environment indirection; no raw secrets committed"]

**Residual Risks or Deferred Items:**
- [List any assumptions deferred to later tasks, minor edge-case behaviors, or environment traits to track during final production smoke tests]
````

## Full-Stack Task Archetype Examples (For Multi-Layer Planning Reference)

### 🗄️ Database Migration Example Task Block
When a task dictates structural data changes, structure its validation sequence using the migration framework engine rather than application code testing:
```markdown
- [ ] Step 1: Write a down/rollback check or inspect schema layout.
- [ ] Step 2: Run migration status command. Expected: Pending or missing columns.
- [ ] Step 3: Write the exact `UP` schema definition code or migration script block.
- [ ] Step 4: Run migration execution command and log check. Expected: Upgrade Success.
- [ ] Step 5: Commit the state changes.
```

### 🐳 Container / DevOps Example Task Block
When updating base environment layers like Docker or orchestration manifests, layout the assertions around network socket connectivity or layout availability:
```markdown
- [ ] Step 1: Write or execute an isolated healthcheck/ping instruction.
- [ ] Step 2: Run verification check. Expected: Service unreachable or config parameter undefined.
- [ ] Step 3: Implement minimal modifications in `docker-compose.yml` or relevant `.env` blocks.
- [ ] Step 4: Run verification check (`docker compose up --build`). Expected: Healthy daemon logs.
- [ ] Step 5: Commit the configuration patch.
```

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test or verification commands)
- "Similar to Task N" (repeat the code or config — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code/config blocks required for structural steps)
- References to types, functions, methods, environment variables, or tables not defined in any task

## Remember
- Exact file paths always
- Complete code, migration blocks, or configuration definitions in every step — if a step changes state, show the block
- Exact commands with expected outputs
- DRY, YAGNI, Test-Driven / Verification-Driven, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Architectural consistency:** Do the types, method signatures, property names, database columns, and environment keys you used in later tasks match what you defined in earlier tasks? A variable called `DB_URL` in Task 2 but `DATABASE_URL` in Task 5 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `.agents/plans/plan_<plan-name>.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development
- Fresh subagent per task + two-stage review

**If Inline Execution chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:executing-plans
- Batch execution with checkpoints for review
