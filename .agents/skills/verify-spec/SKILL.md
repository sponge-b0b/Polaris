---
name: verify-spec
description: Perform authorized spec-wide verification across the completed Spec, select gates from the actual change surface, repair in-scope failures, and record a passing verification receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec against its fixed baseline as a unified system.

A successful run records a **Spec Verification Receipt** for the exact final committed `HEAD`. `$review-spec` requires that receipt.

Verification discipline is applicability-driven:

> Repository location does not determine verification discipline. Derive required gates from the Spec obligations and the actual changed surfaces.

Do not run code-centric checks merely because work lives in a software repository. Mixed Specs apply the union of every relevant discipline.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts before acting. Prior-session summaries or remembered conclusions are routing context only and must not substitute for required durable evidence.

If required durable state cannot be recovered, report the missing artifact rather than infer or recreate it from memory.

## 1. Pin the Fixed Point

Resolve the baseline from the parent Spec unless explicitly overridden:

```bash
BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
  | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
```

If missing and no explicit ref was supplied, ask for it.

Verify the Spec branch:

```bash
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
  echo "❌ Expected spec-<spec_issue_number>; current branch is $CURRENT_BRANCH."
  exit 1
fi

git rev-parse "$BASELINE_COMMIT"
```

Verification must begin from a clean worktree:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Spec verification requires a clean worktree."
  exit 1
fi
```

Capture repository evidence when a branch exists:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

A non-empty repository diff is required only when the Spec changes repository content. A tracker-only Spec may have an empty diff, but only when durable Spec/ticket evidence establishes that no repository mutation was required and tracker-state evidence proves the implementation.

## 2. Identify the Spec

Resolve the originating Spec from:

1. commit references;
2. user-supplied path or issue;
3. matching repository Spec;
4. user only if still unresolved.

Capture its **Architecture Impact**:

* affected entities or delivery-process authorities;
* impact classification;
* governing ADR/doc/Wayfinder references;
* unresolved architecture questions.

A Spec containing unresolved material architecture is not ready for verification.

## Project Delivery Actionability Guard

Before executing verification or mutating repository/tracker state, determine whether the Spec is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

An intentionally non-Wayfinder Spec keeps the existing verification lifecycle. Do not invent a governing Wayfinder merely to enroll it into project focus.

For a Wayfinder-managed Spec:

1. require the Spec issue to be open;
2. read its complete native `blocked by` relationship set and fail closed if blocker data is truncated or unreadable;
3. stop if any direct blocker is open;
4. recover every current governing Wayfinder; ambiguous governance fails closed rather than choosing one;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
7. require at least one governor to return `PROJECT DELIVERY GUARD: ALLOWED`.

If no governor is allowed, stop before verification and report the governing maps, their guard results, current focus, and the explicit human `$project-delivery-management` focus/switch/parallel choices. `$verify-spec` never establishes, switches, or broadens focus.

A legitimately reopened blocker Spec makes this guard fail again through the unchanged native dependency relationship. Ticket completion, prior verification work, Project state, or a stale receipt does not override current blocker state.

Internal child workflows invoked by this already-authorized `$verify-spec` lifecycle inherit the parent authorization and must not introduce a second project-focus Human Handoff. A distinct later human lifecycle invocation must perform its own guard.

Re-run this guard immediately before persisting a passing **Spec Verification Receipt**. If authorization or dependency eligibility changed during verification, do not write a passing receipt.

## 3. Classify Change Surfaces and Verification Gates

Before selecting verification commands, derive the complete change-surface set from:

* normative Spec obligations;
* every implementation ticket and its durable evidence;
* the aggregate repository diff/commit set when present;
* durable tracker mutations owned by the Spec.

Use these surface classes as needed:

* **Code** — production/library/runtime source;
* **Tests** — test source, fixtures, harnesses, or test configuration;
* **Documentation** — Markdown/docs/ADRs/wiki content;
* **Agent skills / workflow policy** — agent skills, lifecycle contracts, tracker/process policy;
* **Repository configuration** — package/tool/runtime configuration;
* **CI / automation** — workflows, scripts, release/qualification automation;
* **Data / schema / migrations** — database models, migrations, durable serializers/contracts;
* **Tracker-only state** — issues, native relationships, labels, durable workflow state, Project projection with no repository file mutation.

`Mixed` means apply the union of all relevant classes; it is not a shortcut that collapses verification to one dominant class.

Build an applicability matrix before running checks. Every candidate gate must be `required`, `not-applicable` with a reason, or `unresolved`. A required gate may not be silently skipped.

Universal verification obligations are:

* branch/baseline correctness when a repository branch is part of the Spec;
* clean worktree before and after verification;
* complete change inventory across repository and tracker surfaces;
* explicit acceptance-criterion coverage;
* applicability selection from the actual change surfaces;
* correction and rerun of Spec-owned failures;
* final state stability;
* passing receipt bound to the exact final `HEAD` and baseline.

Typical surface-driven gates include:

* Code/Tests → applicable formatter/linter/type checks, targeted tests, production-boundary proof, duplication or architecture checks when relevant;
* Documentation → applicable document/ADR/wiki classification and deterministic documentation validation;
* Agent skills/workflow policy → skill structure, cross-skill contract consistency, lifecycle ownership, fail-closed behavior, idempotency/re-entry, tracker relationship and projection proof;
* Repository configuration / CI → syntax/schema/lint/dry-run or repository-defined validation appropriate to the changed configuration;
* Data/schema/migrations → `$database-migrations` plus required migration/database proof;
* Tracker-only state → canonical re-read, native relationship/state verification, idempotency where required, and proof that no repository diff was needed.

Do not manufacture tests or tool invocations that do not prove an actual Spec obligation.

## 4. Execute Applicable Verification

### Guardrails

* Broad commands are authorized only when the applicability matrix requires them.
* Every pytest command executed by this workflow must set `POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>`.
* Do not run untargeted full-suite pytest, coverage, or broad live/service-backed suites unless the Spec itself makes that proof necessary and the repository workflow explicitly authorizes it.
* Read `docs/process/testing-guide.md` when tests are applicable.
* Do not weaken configuration, add pass-only suppressions, or refactor unrelated work merely to pass.
* Report unrelated pre-existing failures separately.

### Repository Diff Hygiene

When repository content changed, run:

```bash
git diff --check "$BASELINE_COMMIT"
```

For findings introduced or carried by this Spec:

* deterministic whitespace-only defects that are provably semantics-preserving for the affected file type → fix mechanically, rerun `git diff --check`, and continue;
* Markdown trailing whitespace → do not rewrite solely to satisfy `git diff --check`; trailing spaces may encode hard line breaks;
* unresolved conflict markers → Blocking; investigate rather than treating them as whitespace cleanup.

Do not alter document/code meaning while fixing whitespace. Unrelated pre-existing whitespace outside the Spec remains report-only.

For tracker-only Specs, mark repository diff hygiene `not-applicable` only after proving the repository diff is empty and repository mutation was not required.

### Code Quality

Run these only when changed Python/code/test/config surfaces are governed by them:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .

POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

Never use Ruff `--add-noqa`.

A documentation-, workflow-, or tracker-only Spec does not run Ruff or Mypy merely because those tools exist in the repository.

### Tests, Services, and Persistence

Run targeted tests only when they prove changed behavior, affected boundaries, Spec acceptance requirements, or regression risks.

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
UV_CACHE_DIR=/tmp/uv-cache \
uv run pytest -q <targeted_test_directory_or_marker>
```

A helper/unit test is insufficient when the Spec requires proof through a higher authoritative boundary.

If a required targeted check cannot establish its criterion service-free, derive safe local configuration when unambiguous and start only the required authorized local service. A required check skipped solely because local setup is absent remains unresolved.

Never expose secrets or authenticated connection strings.

### Documentation, Workflow, Configuration, and Tracker Proof

For non-code surfaces, verify the authoritative contract directly rather than substituting code checks.

Examples include:

* required headings/frontmatter/schema or repository-defined document/skill structure;
* cross-skill ownership and handoff consistency;
* fail-closed lifecycle guards and re-entry behavior;
* deterministic tracker provenance, hierarchy, native dependency, focus, and Project-projection rules;
* audit-before-apply and second-pass idempotency when required;
* configuration/workflow syntax or repository-defined validation;
* exact durable-state rereads after tracker mutation.

Use the narrowest existing owner/helper for the affected surface. Do not invent a generic validator when the repository has no authoritative one; prove the acceptance criterion from deterministic source/tracker evidence instead.

### Architecture Integrity

Run architecture/wiki checks only when **Architecture Impact** or the actual change surface makes them applicable.

If the Living Entity Wiki is authoritative routing context for affected entities, invoke `$wiki-lint` and evaluate Spec-relevant `[source-conflict]`, `[code-drift]`, `[doc-drift]`, and structural/citation findings.

Use graph queries only when they materially prove affected architecture:

```bash
graphify . --update
graphify query "<affected entities, canonical concepts, changed subsystems, or delivery-process authorities>"
```

For delivery-process architecture, verify the relevant skill/tracker authority boundaries directly; do not force runtime graph analysis when runtime entities are unaffected.

Apply the **Accepted ADR Realization Maintenance** rule before routing `[source-conflict]`.

### Duplication

Invoke `$deduplicate-code` only when the Spec introduces or materially changes code/module/helper/service/canonical behavior for which duplicate implementation is a real risk.

Documentation-, workflow-, configuration-, or tracker-only work does not run code duplication analysis by default.

## 5. Failure Handling

For an ordinary verification failure:

1. determine whether the Spec introduced or owns it;
2. fix the narrowest authoritative point within Spec scope;
3. rerun the affected applicable gate;
4. continue verification.

Do not:

* weaken configuration;
* add pass-only suppressions;
* change expected behavior merely so a check reaches it;
* broaden verification to compensate for failure;
* modify unrelated pre-existing failures.

If a non-architecture failure cannot be safely repaired within Spec scope, stop and report it.

## 6. Architecture Finding Routing

### Accepted ADR Realization Maintenance

Do not accept `[source-conflict]` merely because an accepted realization-required ADR still says implementation is `pending`, `not yet realized`, or equivalent.

When the ADR remains accepted, its normative decision is unambiguous, the completed Spec conforms, aggregate evidence proves full realization, and only permitted realization/reference wording is stale, treat this as deterministic ADR documentation drift.

Invoke `$to-adr-doc` for permitted **Realization Maintenance**, then `$wiki-sync` as required and rerun applicable architecture checks.

Do not use Realization Maintenance when realization is partial/ambiguous, normative ADR content would change, implementation contradicts the decision, or applicable authorities genuinely disagree.

### Existing Authority Determines the Fix

When current authority establishes the correct state, repair within Spec scope using the owning workflow:

* implementation → correct the affected implementation surface;
* entity knowledge → `$wiki-sync`;
* new non-ADR documentation → `$to-doc`;
* classification/relocation → `$classify-doc`;
* ADR lifecycle/permitted Realization Maintenance → `$to-adr-doc`.

Rerun affected applicable checks.

### Architecture Decision Required

A new decision is required only when correction requires choosing/changing a durable invariant, canonical owner/path, architectural boundary, dependency direction, lifecycle responsibility, or when applicable authorities genuinely disagree.

Collect/de-duplicate all independent blockers. Do not resolve architecture here.

Halt with:

> ⚠️ **Spec verification is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> **Architecture blockers:**
>
> 1. **<question/conflict>**
>    * Evidence: <evidence>
>    * Material consequence: <ownership/path/boundary/dependency/lifecycle/conflict>
>    * Governing context: <entities / ADRs / docs / Wayfinder decisions>

Do not propose an architectural answer.

## 7. Final Verification Pass

After all verification-owned fixes, rerun every **applicable** gate needed for final consistency.

At minimum reconcile the applicability matrix so every required gate is `passed`, every non-applicable gate has a concrete reason, and no gate remains `unresolved`.

When repository content changed, rerun `git diff --check "$BASELINE_COMMIT"`. Rerun Ruff, Mypy, targeted tests, database, documentation/workflow/configuration/tracker, architecture/wiki, and duplication checks only when their applicability remains established.

Do not report success while any required gate remains failed or unresolved.

## 8. Persist Verification Fixes

If verification changed repository files:

1. verify `spec-<spec_issue_number>` remains checked out;
2. stage only verification-owned files;
3. invoke `$conventional-commits`;
4. commit;
5. push:

```bash
git push -u origin HEAD
```

Child workflows contribute their mutations to this verification commit when parent commit ownership applies.

Do not use `git add .` with unrelated changes. If staging, commit, or push fails, verification is incomplete.

If no repository files changed, skip commit/push and prove the final repository state remained unchanged.

Require a clean final worktree:

```bash
if [ -n "$(git status --porcelain)" ]; then
  echo "❌ Verification cannot attest to HEAD with an uncommitted worktree."
  exit 1
fi
```

## 9. Record the Verification Receipt

Only after all required gates pass, fixes are committed/pushed when applicable, and the worktree is clean, re-run the **Project Delivery Actionability Guard** when the Spec is Wayfinder-managed.

If current dependency/focus authorization no longer permits this Spec to advance, do not write a passing receipt.

Capture:

```bash
FINAL_HEAD=$(git rev-parse HEAD)
```

Persist on the Spec:

```markdown
## Spec Verification Receipt

**Status:** passed
**Verified HEAD:** <FINAL_HEAD>
**Verified Baseline:** <BASELINE_COMMIT>
**Branch:** spec-<spec_issue_number>
**Change surfaces:** <classified surfaces>

### Verification gates
- <gate>: passed — <evidence>
- <gate>: not-applicable — <reason>
```

The receipt attests only to that exact `HEAD` and the recorded durable tracker state. Do not write a passing receipt while any required gate is failed or unresolved, and never reuse a stale receipt.

Receipt persistence failure means verification is incomplete.

## 10. Reporting

Report:

* baseline and final `HEAD`;
* Spec branch;
* classified change surfaces;
* applicable verification gates and results;
* non-applicable gates with reasons;
* acceptance evidence;
* failures repaired;
* unrelated pre-existing findings;
* verification-fix commits when any;
* push result when any;
* final worktree/repository state;
* verification receipt and `Verified HEAD`.

Do not emit fixed code-centric result headings for gates that were not applicable.

On success:

```text
Spec verification passed.
Verified HEAD: <full SHA>
```

If any required gate or receipt remains unresolved, do not report a pass.

## 11. Review Human Handoff

After successful receipt persistence, halt with:

> ✅ **Spec verification passed.**
>
> The exact verified `HEAD` is ready for independent Spec review.
>
> Please run:
>
> ```
> $review-spec - <Spec Title> (<Spec URL>)
> ```

Then stop.

Do not invoke `$review-spec` implicitly.
