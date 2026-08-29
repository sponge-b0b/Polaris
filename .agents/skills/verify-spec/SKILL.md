---
name: verify-spec
description: Perform authorized Spec-wide verification against a deterministic Spec contract, reuse safe ancestor checkpoints, repair Spec-owned failures, and record a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec against its fixed baseline as a unified system.

A successful run records a **Spec Verification Receipt** for the exact final committed `HEAD`. `$review-spec` requires that receipt.

Verification discipline is applicability-driven:

> Repository location does not determine verification discipline. Derive required proof from the deterministic Spec contract and the actual Spec-owned change surfaces.

The fixed baseline establishes integration history. It does **not** make every later default-branch change part of the Spec's repository-standards ownership.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the explicit invocation, repository, and durable tracker artifacts. Prior-session summaries are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## 1. Pin the Fixed Point

Resolve the repository and read the parent Spec's complete durable comment history once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>

SPEC_COMMENT_PAGES=$(
  gh api --paginate --slurp \
    -H "X-GitHub-Api-Version: 2026-03-10" \
    "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100"
)
```

Resolve the baseline from that complete comment snapshot unless explicitly supplied:

```bash
BASELINE_COMMIT=$(
  printf '%s\n' "$SPEC_COMMENT_PAGES" \
    | jq -r '
        [.[][]
         | select((.body // "") | contains("**Baseline Commit Hash:**"))
         | {id, created_at, body}]
        | sort_by(.created_at, .id)
        | last
        | .body // ""
        | capture("\\*\\*Baseline Commit Hash:\\*\\*\\s+(?<sha>[0-9a-fA-F]{40})").sha // empty'
)
```

Do not substitute `gh issue view --json comments` or an unpaginated comment read. Reuse `SPEC_COMMENT_PAGES` for checkpoint receipt selection in Section 3.

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

Capture the complete fixed-baseline integration evidence:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

A tracker-only Spec may have an empty repository diff only when durable Spec/ticket evidence proves no repository mutation was required.

## 2. Identify the Spec and Build the Shared Contract

Resolve the originating Spec from:

1. user-supplied issue/path;
2. commit references;
3. matching repository Spec;
4. user only if still unresolved.

Capture its **Architecture Impact** and unresolved architecture questions. A Spec with unresolved material architecture is not ready for verification.

Invoke `$spec-contract` in `build` mode with the Spec, `BASELINE_COMMIT`, current branch, and current `HEAD`.

Require `SPEC CONTRACT: VALID`.

Capture:

* `SPEC_BODY_HASH`;
* `SPEC_CONTRACT_HASH`;
* complete ordered Spec Contract Manifest;
* source counts and manifest-integrity counts;
* Spec-owned, Mixed, Inherited-only, and Spec-owned tracker surfaces;
* immutable default-branch name and head returned by `$spec-contract` for ownership.

Treat the returned default-branch SHA as `DEFAULT_HEAD`. `$verify-spec` does not independently refresh or reinterpret default-branch state.

If the contract is invalid or ownership is ambiguous, verification cannot pass.

### Spec Contract Is the Acceptance Universe

The returned manifest is the complete verification acceptance universe.

Do not replace it with a prose summary, ticket checklist, Root Blocker matrix, reviewer history, or an ad hoc subset of requirements.

Every manifest cell must receive a final verification disposition:

```text
proven | not-applicable | unresolved
```

`not-applicable` requires a concrete reason grounded in the originating Spec. `unresolved` prevents PASS.

## Project Delivery Actionability Guard

Before executing verification or mutating repository/tracker state, determine whether the Spec is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

For a Wayfinder-managed Spec:

1. require the Spec issue open;
2. read its complete native `blocked by` set;
3. stop if any direct blocker is open;
4. recover every current governing Wayfinder; ambiguity fails closed;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
7. require at least one `PROJECT DELIVERY GUARD: ALLOWED`.

If no governor is allowed, stop before verification and report the explicit human focus/switch/parallel choices. `$verify-spec` never changes focus.

Re-run this guard immediately before persisting a passing receipt.

## 3. Incremental Re-verification

The fixed Spec baseline remains the canonical verification origin. A prior passing **Spec Verification Receipt** may reduce repeated proof work only as a verified ancestor checkpoint.

### Select a Checkpoint

From `SPEC_COMMENT_PAGES`, select exactly the latest durable comment whose body contains the exact header `## Spec Verification Receipt`, ordered by `created_at` then comment `id`:

```bash
CHECKPOINT_RECEIPT_JSON=$(
  printf '%s\n' "$SPEC_COMMENT_PAGES" \
    | jq -c '
        [.[][]
         | select((.body // "") | contains("## Spec Verification Receipt"))
         | {id, created_at, html_url, body}]
        | sort_by(.created_at, .id)
        | last // empty'
)
```

That newest receipt is the only checkpoint candidate. If it is absent, malformed, stale, or fails any condition below, perform full verification from the fixed baseline. Do **not** search backward for an older convenient receipt.

Use checkpoint mode only when that receipt is well formed and:

1. `Status: passed`;
2. `Verified Baseline` equals `BASELINE_COMMIT`;
3. `Branch` equals the current Spec branch;
4. `Verified HEAD` resolves and is an ancestor of current `HEAD`;
5. `Spec Body Hash` equals current `SPEC_BODY_HASH`;
6. `Spec Contract Hash` equals current `SPEC_CONTRACT_HASH`;
7. the receipt contains complete per-cell Spec contract coverage;
8. the complete checkpoint→current repository delta is bounded.

Prove ancestry:

```bash
CHECKPOINT_HEAD=<prior Verified HEAD>

git merge-base --is-ancestor "$CHECKPOINT_HEAD" HEAD
git log "$CHECKPOINT_HEAD"..HEAD --oneline
git diff --name-status "$CHECKPOINT_HEAD"..HEAD
git diff "$CHECKPOINT_HEAD"..HEAD
```

If any condition fails, perform full verification from the fixed baseline. Do not search backward for a more convenient older checkpoint.

### Inherit Only Unaffected Immutable Proof

A checkpoint may carry forward only proof over immutable repository state that the complete checkpoint delta cannot invalidate.

Before inheriting a gate or Spec-contract cell:

1. inventory the complete checkpoint delta;
2. freshly recover current Spec/ticket/tracker obligations;
3. recompute current `$spec-contract` ownership;
4. identify direct and transitive invalidation;
5. rerun every affected or uncertain proof.

Never inherit mutable tracker, dependency, project-focus, hierarchy, authorization, or lifecycle truth.

A prior cell disposition may be inherited only when its exact evidence remains immutable and unaffected. Otherwise prove that manifest cell fresh.

### Verification-Owned Changes

If verification changes repository files, those changes extend the checkpoint delta. Recompute ownership/delta/invalidation before the final pass.

Whether full or checkpoint mode, success always requires a new receipt for the exact final `HEAD`.

## 4. Classify Surfaces and Verification Gates

Use `$spec-contract` ownership rather than treating the entire fixed-baseline integration history as Spec-owned.

### Surface Rules

* **Spec-owned / Mixed repository surfaces** determine repository Standards/tooling applicability.
* **Spec-owned tracker surfaces** determine tracker-policy verification owned by this Spec.
* **Inherited-only surfaces** are integration context. Do not manufacture a current-Spec repository-standard failure from them.
* **Spec behavioral proof** may inspect any current surface required by a manifest cell, including inherited or unchanged named surfaces.
* **Architecture proof** may inspect any surface required by the Spec's Architecture Impact/current authority.
* If an inherited-only defect makes an exact Spec or Architecture obligation fail, that behavioral/architecture obligation remains unresolved; ownership does not excuse required behavior.

Classify as needed:

* Code;
* Tests;
* Documentation;
* Agent skills / workflow policy;
* Repository configuration;
* CI / automation;
* Data / schema / migrations;
* Tracker-only state.

Build an applicability matrix. Every candidate gate is:

```text
required | not-applicable | unresolved
```

A required gate may not be silently skipped.

Universal obligations:

* branch/baseline/worktree correctness;
* valid `$spec-contract`;
* complete Spec-owned/integration inventory;
* complete per-cell Spec contract proof;
* current ticket/hierarchy/dependency/focus state;
* applicability reconciliation;
* correction and rerun of Spec-owned failures;
* final state stability;
* exact-HEAD receipt.

Typical gates:

* Code/Tests → formatter/linter/type checks, targeted tests, production-boundary proof;
* Documentation → applicable classification/reference/structure proof;
* Agent skills/workflow policy → structure, ownership/handoff, fail-closed, idempotency/re-entry, tracker/projection proof;
* Repository configuration / CI → syntax/schema/lint/dry-run;
* Data/schema/migrations → `$database-migrations` and required persistence proof;
* Tracker-only → canonical state/relationship rereads and idempotency where required.

Do not run a gate solely because an Inherited-only surface exists in fixed-baseline history.

## 5. Execute Applicable Verification

### Guardrails

* Broad commands are authorized only when applicability requires them.
* Every pytest command must set `POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>`.
* Do not run untargeted broad live/service suites unless required by the Spec.
* Before any pytest invocation, follow the mandatory test-service preflight in `AGENTS.md` and `docs/process/testing-guide.md`.
* Do not weaken configuration or add pass-only suppressions.
* Report unrelated inherited/pre-existing repository defects separately.

### Repository Diff Hygiene

When Spec-owned/Mixed repository content changed, run:

```bash
git diff --check "$BASELINE_COMMIT"
```

Fix only deterministic Spec-owned whitespace defects that are semantics-preserving. Markdown hard-break whitespace is not rewritten merely to satisfy `git diff --check`.

### Code Quality

Run when Spec-owned/Mixed Python/code/test/config surfaces make them applicable:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

If these broad tools expose an inherited-only failure unrelated to any Spec obligation, report it separately; do not absorb it into Spec remediation.

Never use Ruff `--add-noqa`.

### Tests, Services, and Persistence

Run targeted tests that prove manifest cells, affected boundaries, or Spec-owned regression risk:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
PYTHONDONTWRITEBYTECODE=1 \
UV_CACHE_DIR=/tmp/uv-cache \
uv run pytest -q -p no:cacheprovider <targeted_test_directory_or_marker>
```

A helper/unit test is insufficient when a manifest cell requires a higher authoritative boundary.

A required check skipped solely because local setup is absent remains unresolved.

Never expose secrets or authenticated connection strings.

Determine the selected pytest scope's complete external prerequisites and verify
them before pytest starts. Missing prerequisites leave required verification
unresolved.

### Documentation, Workflow, Configuration, and Tracker Proof

Verify non-code contracts directly. Examples:

* document/ADR/wiki classification/reference/structure;
* cross-skill ownership and handoff consistency;
* fail-closed/re-entry/idempotency behavior;
* tracker hierarchy/dependency/focus/projection rules;
* configuration/workflow syntax;
* exact durable-state rereads.

Apply these repository-policy checks to Spec-owned/Mixed surfaces. Do not turn unrelated inherited-only repository drift into Spec Blocking work.

### Architecture Integrity

Run architecture/wiki checks only when Architecture Impact or manifest obligations make them applicable.

If Living Entity Wiki routing is relevant, invoke `$wiki-lint` and evaluate only Spec-relevant conflict/drift results. `$wiki-lint` owns wiki structural integrity and citation resolution/eligibility; do not duplicate those checks with ad hoc `rg`, `sed`, or similar shell pipelines.

If an applicable wiki proof is not provided by `$wiki-lint`, treat that proof as unresolved or fix the missing audit contract at `$wiki-lint`; do not invent a parallel verifier inside `$verify-spec`.

Use graph queries only when they materially prove affected architecture.

Apply **Accepted ADR Realization Maintenance** before routing `[source-conflict]`.

### Duplication

Invoke `$deduplicate-code` only when Spec-owned/Mixed work introduces or materially changes a behavior for which duplicate implementation is a real risk.

## 6. Prove Every Spec Contract Cell

Maintain a coverage table for the exact manifest:

```text
Cell: <ID>
State: <proven | not-applicable | unresolved>
Evidence: <test/runtime/source/tracker/document evidence>
```

Requirements:

* every manifest ID appears exactly once;
* no receipt row exists for an unknown manifest ID;
* `proven` cites identifiable evidence appropriate to the obligation;
* `not-applicable` cites the exact conditional reason;
* no cell is inferred satisfied merely because related tickets are closed;
* no generic test count substitutes for cell-level proof.

### Direct-Subject Evidence Gate

A cell may be `proven` only when its evidence directly establishes the exact subject, required behavior, and material conditions expressed by that manifest cell. Evidence that merely demonstrates nearby health is supporting evidence, not proof of the cell.

Apply these rules before assigning `proven`:

* identify the concrete runtime, source, tracker, document, interface, test seam, or other authoritative surface that embodies the cell;
* trace the evidence to that surface and to the cell's actual predicate; a nearby file path, closed ticket, successful broad suite, Ruff/Mypy result, or generic repository sweep cannot establish an unrelated semantic obligation by itself;
* for prohibition/absence obligations, perform a bounded negative sweep or equivalent direct proof over the affected semantic domain rather than inferring absence from positive tests;
* for help/default/interface-to-behavior consistency, inspect both the declared interface/default and the effective behavior, plus applicable regression proof;
* for contract migrations involving fakes, fixtures, mocks, monkeypatches, adapters, or test doubles, inspect the affected seams themselves for contract/signature closure; production-path success alone is insufficient;
* when one cell contains multiple required clauses or surfaces, prove every material clause/surface or leave the cell `unresolved`; several precise evidence items are preferable to one generic umbrella result;
* checkpoint inheritance is allowed only when the prior cell's same direct-subject evidence remains immutable and unaffected by the complete checkpoint delta.

Evidence may be concise, but it must be traceable enough that an independent reviewer can determine why it proves this cell rather than merely why the repository appears healthy.

Before success, reconcile counts:

```text
Manifest cells: <n>
Coverage rows: <n>
Proven: <n>
Not applicable: <n>
Unresolved: 0
Missing rows: 0
Unknown rows: 0
```

If the manifest contains 27 numbered User Stories, coverage must map all 27 User Story source items before any other manifest cells are considered complete.

## 7. Failure Handling

For an ordinary failure:

1. determine whether it is:
   * a failed Spec contract obligation;
   * a Spec-owned repository-standard/tooling failure;
   * an inherited-only unrelated repository defect;
2. fix the narrowest authoritative point only for the first two categories;
3. rerun affected proof;
4. continue.

An inherited-only unrelated defect is report-only for this Spec. Do not mutate it merely to make verification green.

If a required Spec/Architecture obligation cannot be safely repaired within current authority, follow Architecture Finding Routing or stop with the exact blocker.

## 8. Architecture Finding Routing

### Accepted ADR Realization Maintenance

When accepted architecture is unambiguous and implementation fully realizes it, stale permitted realization/reference wording may be corrected through `$to-adr-doc` and `$wiki-sync`.

Do not use realization maintenance when implementation is partial/ambiguous, normative ADR content would change, or authorities genuinely disagree.

### Existing Authority Determines the Fix

When current authority establishes the correct state, repair the Spec-owned or Spec-required authoritative surface using its owner:

* implementation → affected implementation surface;
* entity knowledge → `$wiki-sync`;
* new non-ADR documentation → `$to-doc`;
* classification/relocation → `$classify-doc`;
* ADR lifecycle/permitted realization maintenance → `$to-adr-doc`.

### Architecture Decision Required

A new decision is required only when correction requires choosing/changing a durable invariant, owner/path, boundary, dependency direction, lifecycle responsibility, or resolving genuinely conflicting authorities.

Collect all such blockers and halt with:

> ⚠️ **Spec verification is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```

Do not propose the architectural answer.

## 9. Final Verification Pass and Persistence

After verification-owned fixes:

* recompute fixed-baseline integration inventory;
* rerun `$spec-contract` in `build` mode at final `HEAD`;
* require the Spec body/contract to remain valid and reconcile any changed ownership;
* in checkpoint mode, recompute checkpoint delta/invalidation;
* rerun every newly affected gate;
* reapply the **Direct-Subject Evidence Gate** to every `proven` manifest cell;
* reconcile every manifest cell;
* require every required gate passed and `unresolved 0`.

If repository files changed:

1. verify the Spec branch;
2. stage only verification-owned files;
3. invoke `$conventional-commits`;
4. commit;
5. push:

```bash
git push -u origin HEAD
```

Require a clean final worktree.

## 10. Record the Verification Receipt

Re-run the Project Delivery Actionability Guard.

Capture:

```bash
FINAL_HEAD=$(git rev-parse HEAD)
```

Use the final `$spec-contract` result for `SPEC_BODY_HASH`, `SPEC_CONTRACT_HASH`, `DEFAULT_BRANCH`, `DEFAULT_HEAD`, source counts, manifest count, ownership, and the complete ordered manifest. Do not refresh default-branch state independently during receipt persistence.

Persist this body on the Spec:

```markdown
## Spec Verification Receipt

**Status:** passed
**Verified HEAD:** <FINAL_HEAD>
**Verified Baseline:** <BASELINE_COMMIT>
**Branch:** spec-<spec_issue_number>
**Verification mode:** full | checkpoint
**Prior verified checkpoint:** None | <SHA>
**Spec Body Hash:** <SPEC_BODY_HASH>
**Spec Contract Hash:** <SPEC_CONTRACT_HASH>
**Default branch:** <DEFAULT_BRANCH>
**Default branch head used for ownership:** <DEFAULT_HEAD>
**Change surfaces:** <Spec-owned/Mixed surface classes>

### Spec Contract Integrity
- User Stories: <source count>
- Implementation Decisions: <source count>
- Testing Decisions: <source count>
- Out of Scope: <source count>
- Other normative source items: <source count>
- Manifest cells: <n>
- Unmapped source items: 0
- Duplicate source mappings: 0
- Ambiguous source items: 0

### Spec Change Ownership
- Spec-owned repository surfaces: <summary>
- Mixed repository surfaces: <summary>
- Inherited-only integration surfaces: <summary>
- Spec-owned tracker surfaces: <summary>

### Spec Contract Manifest
| Cell | Source | Requirement |
| --- | --- | --- |
| <ID> | <source anchor> | <requirement> |

### Spec Contract Coverage
| Cell | State | Evidence |
| --- | --- | --- |
| <ID> | proven | <evidence> |

### Verification Gates
- <gate>: passed — <fresh evidence>
- <gate>: passed — inherited from checkpoint <SHA>; unaffected by complete invalidation analysis
- <gate>: not-applicable — <reason>

### Unrelated Inherited Findings
- <finding or None>
```

The receipt must contain the complete manifest and exactly one coverage row per manifest cell.

### Atomic Receipt Persistence

1. Render the **complete** receipt into `RECEIPT_FILE=$(mktemp)` before any GitHub mutation. Treat Markdown as data: use Python or `printf`; never use an unquoted heredoc. If a heredoc contains literal Markdown, quote its delimiter (`<<'EOF'`) and write dynamic values separately. Ensure the file ends with exactly one newline.
2. Pre-validate `RECEIPT_FILE` with one Python invocation. Require exact equality for Status, HEAD, baseline, branch, verification mode/checkpoint, body/contract hashes, default branch/head; require all six receipt sections exactly once; require the three manifest-integrity zero lines; parse manifest and coverage IDs matching `(?:US|ID|TD|OOS|NORM)-<n>[.<suffix>]`; require both ordered ID lists to equal the final `$spec-contract` manifest exactly, with no duplicates, coverage count equal to `MANIFEST_CELL_COUNT`, and no `unresolved` state. Do not substitute an improvised `grep`/`sed`/`awk`/regex pipeline.
3. If pre-validation passes, POST the validated body **once**:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
RECEIPT_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

jq -Rs '{body: .}' "$RECEIPT_FILE" > "$RECEIPT_JSON"
gh api --method POST \
  "repos/$REPO/issues/<spec_issue_number>/comments" \
  --input "$RECEIPT_JSON" > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]

gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j '.body' > "$READBACK_FILE"

cmp -s "$RECEIPT_FILE" "$READBACK_FILE"
```

4. Run the same deterministic Python validation against `READBACK_FILE`. Only then is persistence complete. Clean up the temporary files.

Never POST/PATCH a partial receipt, repair a malformed persisted receipt in place, replace its body with a file reference, or create a second corrective receipt in the same invocation. If POST succeeds but exact readback or post-validation fails, verification is incomplete: stop, report `COMMENT_URL`, and do not claim PASS.

Receipt persistence failure means verification is incomplete. Any later commit or Spec-body change makes the receipt stale.

### Successful Lifecycle Transition

A successfully persisted and validated Spec Verification Receipt is the authoritative verification transition for this lifecycle. From that exact receipt and `FINAL_HEAD`, establish the Spec's base lifecycle as:

```text
Artifact Type: Spec
Workflow State: Ready to Review
Work Status: Ready
Next Skill: $review-spec
Root Blocker: None
Completed On: None
```

### Mandatory Project Reconciliation

Immediately after the successful lifecycle state above is established and before Section 11, invoke `$project-tracking` as prescribed internal composition for the Spec.

Supply exactly the base projection established by the validated receipt and `FINAL_HEAD`:

```text
Artifact Type: Spec
Workflow State: Ready to Review
Work Status: Ready
Next Skill: $review-spec
Root Blocker: None
Completed On: None
```

Recover current project-delivery context only after receipt persistence, exact readback, and post-validation succeed. For an intentionally non-Wayfinder Spec, use `Project Delivery State = independent`; for a Wayfinder-managed Spec, supply the current authoritative project-delivery classification recovered from durable project-delivery state. Preserve `Area` and `Priority` unless this invocation has separate authority to change them.

The Project projection and downstream Human Handoff must derive from the same validated receipt and `FINAL_HEAD`. `$verify-spec` owns the lifecycle state supplied to `$project-tracking`; `$project-tracking` owns validation, delivery overlay, and Project mutation. Do not project `Ready to Review` before receipt persistence succeeds, and do not emit `$review-spec` when verification or receipt persistence is incomplete.

`PROJECT TRACKING: DRIFT` does not invalidate the passing verification receipt or revert the authoritative `Ready to Review` lifecycle state. Report projection drift and continue to emit the otherwise-authorized `$review-spec` handoff. Do not infer lifecycle truth from Project fields.

## 11. Reporting and Human Handoff

Report:

* baseline/final `HEAD`;
* verification mode/checkpoint;
* Spec contract counts/hash;
* ownership classification;
* applicable gates;
* complete manifest coverage summary;
* repaired failures;
* unrelated inherited findings;
* commit/push/final worktree;
* receipt;
* Project reconciliation result.

On success:

> ✅ **Spec verification passed.**
>
> The exact verified `HEAD` and Spec Contract Manifest are ready for independent review.
>
> Please run:
>
> ```
> $review-spec - <Spec Title> (<Spec URL>)
> ```

Then stop.

Do not invoke `$review-spec` implicitly.
