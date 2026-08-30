---
name: verify-spec
description: Perform authorized Spec-wide verification against a deterministic Spec contract, run fail-fast deterministic gates, establish complete evidence-backed per-cell proof, repair Spec-owned failures, and record a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec against its fixed baseline as one integrated acceptance universe.

A successful run records a **Spec Verification Receipt** for the exact final committed `HEAD`. `$review-spec` owns the independent adversarial review that follows verification.

Verification discipline is applicability-driven:

> Repository location does not determine verification discipline. Derive required proof from the deterministic Spec contract and actual Spec-owned change surfaces.

The fixed baseline establishes integration history. It does **not** make every later default-branch change part of the current Spec's repository-standards ownership.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the invocation, repository, durable tracker state, and current skill contracts. Prior-session summaries are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## Verification / Review Boundary

`$verify-spec` owns evidence-backed verification of the completed implementation. The verifier may establish semantic proof directly from authoritative current evidence; it does **not** spawn a second agent to certify its own proof.

`$review-spec` is the independent layer. It owns fresh reviewer execution and adversarial re-evaluation after verification.

Do not duplicate `$review-spec` inside `$verify-spec` by spawning proof certifiers, shadow reviewers, or semantic challenger agents.

## Deterministic Mechanics Boundary

The reasoning agent owns:

- applicability;
- semantic proof design;
- falsifiers and authoritative domain boundaries;
- Nested Universe reasoning;
- evidence sufficiency;
- repair decisions;
- final lifecycle judgment.

The checked-in verifier utility owns repeatable artifact mechanics:

```text
.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
```

Use it for:

- paginated Spec-comment normalization and baseline/latest-receipt extraction;
- proof-packet structure validation and canonical hashing;
- final proof/coverage/gate consistency validation;
- complete receipt rendering;
- byte-for-byte receipt validation before and after GitHub persistence.

Do **not** recreate an operation owned by this utility with ad hoc Python, heredoc scripts, custom `jq` pipelines, or one-off receipt parsers. If the utility rejects valid input or cannot represent a required invariant, fix the utility as verification infrastructure rather than bypassing it.

Do not generate a program whose sole purpose is to generate the proof JSON. Construct the packet as data. A temporary 100+ line Python builder for JSON bookkeeping is a workflow defect, not verification evidence.

For deterministic repository checks not owned by this utility, prefer an existing checked-in repository tool. Use inline Python only when no reusable owner exists; keep it short and invoke it through `uv run python`.

## 1. Pin the Fixed Point

Resolve the repository and read the parent Spec's complete durable comment history exactly once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>
ARTIFACT_TOOL=.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
SPEC_COMMENTS_FILE=$(mktemp)
SPEC_COMMENTS_SUMMARY=$(mktemp)

gh api --paginate --slurp \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100" \
  > "$SPEC_COMMENTS_FILE"

uv run python "$ARTIFACT_TOOL" comments \
  --input "$SPEC_COMMENTS_FILE" \
  > "$SPEC_COMMENTS_SUMMARY"

BASELINE_COMMIT=$(jq -r '.baseline_commit // empty' "$SPEC_COMMENTS_SUMMARY")
```

Do not substitute `gh issue view --json comments` or an unpaginated comment read.

If the baseline is missing and no explicit authoritative baseline was supplied, stop and ask for it.

Require:

- current branch `spec-<spec_issue_number>`;
- `BASELINE_COMMIT` resolves;
- clean worktree.

Capture the complete baseline integration evidence:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

A tracker-only Spec may have an empty repository diff only when durable Spec/ticket evidence proves no repository mutation was required.

## 2. Build the Shared Spec Contract

Resolve the originating Spec from the invocation first, then durable repository/tracker evidence if necessary.

Capture **Architecture Impact** and unresolved architecture questions. A Spec with unresolved material architecture is not ready for verification.

Invoke `$spec-contract` in `build` mode with:

- Spec issue/URL;
- `BASELINE_COMMIT`;
- current Spec branch;
- current `HEAD`.

Require `SPEC CONTRACT: VALID`.

Capture exactly the returned:

- `SPEC_BODY_HASH`;
- `SPEC_CONTRACT_HASH`;
- complete ordered Spec Contract Manifest;
- source counts and integrity counts;
- Spec-owned, Mixed, Inherited-only, and Spec-owned tracker surfaces;
- immutable default branch and default-branch head.

Treat the returned default-branch SHA as `DEFAULT_HEAD`. Do not independently refresh/reinterpret default-branch ownership state inside `$verify-spec`.

### Spec Contract Is the Acceptance Universe

The manifest is the complete verification universe. Do not replace it with a ticket checklist, prose summary, Root Blocker matrix, reviewer history, or ad hoc subset.

Every manifest cell must finish as exactly one of:

```text
proven | not-applicable | unresolved
```

`not-applicable` requires a concrete originating-Spec reason. Any `unresolved` cell prevents PASS.

## Project Delivery Actionability Guard

Before executing verification or mutating repository/tracker state, determine whether the Spec is Wayfinder-managed from durable `wayfinder-source`, `wayfinder-remediation`, and reconciled `Spec Handoff` evidence.

For a Wayfinder-managed Spec:

1. require the Spec open;
2. read its complete native `blocked by` set;
3. stop if any direct blocker is open;
4. recover every current governing Wayfinder; ambiguity fails closed;
5. invoke `$project-delivery-management` `reconcile`;
6. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
7. require at least one `PROJECT DELIVERY GUARD: ALLOWED`.

If no governor is allowed, stop and report the explicit human focus/switch/parallel choices. `$verify-spec` never changes focus.

Do not repeatedly re-read unchanged delivery state during proof construction. Re-run this guard only immediately before persisting a passing receipt, unless a repository/tracker mutation can materially change actionability sooner.

## 3. Exact-HEAD Checkpoint

Use only the `latest_receipt` returned by the deterministic comments summary.

A prior receipt may short-circuit immutable verification work only when it is a passing receipt for the **exact current `HEAD`**, current branch, fixed baseline, `SPEC_BODY_HASH`, and `SPEC_CONTRACT_HASH`.

Even on an exact-HEAD checkpoint:

- revalidate current mutable ticket/hierarchy/dependency/focus state;
- re-run any gate whose authoritative result is mutable or time/service-dependent;
- require the worktree clean;
- repair Project projection drift if needed.

If the prior receipt is for an ancestor rather than exact current `HEAD`, perform full verification. Do not carry semantic proof or gate results across a changed `HEAD`.

This intentionally replaces proof-certification carry-forward machinery with a simpler exact-state rule.

## 4. Classify Surfaces and Gates

Use `$spec-contract` ownership.

- **Spec-owned / Mixed repository surfaces** determine repository Standards/tooling applicability.
- **Spec-owned tracker surfaces** determine tracker-policy verification owned by this Spec.
- **Inherited-only surfaces** are integration context, not automatic current-Spec Standards failures.
- **Spec behavioral proof** may inspect any surface needed to establish a manifest cell.
- **Architecture proof** may inspect any surface needed by the Spec's Architecture Impact/current authority.

Classify as applicable:

- Code;
- Tests;
- Documentation;
- Agent skills / workflow policy;
- Repository configuration;
- CI / automation;
- Data / schema / migrations;
- Tracker-only state.

Every candidate gate is:

```text
required | not-applicable | unresolved
```

Universal obligations:

- branch/baseline/worktree correctness;
- valid `$spec-contract`;
- complete ownership/integration inventory;
- complete per-cell semantic proof;
- current ticket/hierarchy/dependency/focus state;
- applicability reconciliation;
- correction/rerun of Spec-owned failures;
- final-state stability;
- exact-HEAD receipt.

Do not run a gate solely because an Inherited-only surface appears in baseline history.

## 5. Fail-Fast Deterministic Gates

Run cheap deterministic gates **before** model-expensive semantic proof. Machine runtime is cheaper than consuming most of a Codex session before discovering a deterministic failure.

When Spec-owned/Mixed repository content changed:

```bash
git diff --check "$BASELINE_COMMIT"
```

When code quality applies:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

Never use Ruff `--add-noqa`.

If Living Entity Wiki routing is relevant, invoke `$wiki-lint`; do not recreate wiki structural/citation checking inside `$verify-spec`.

Invoke `$deduplicate-code` only when Spec-owned/Mixed work introduces or materially changes behavior for which duplicate implementation is a real risk. When invoked, the transcript must make both Arid and JSCPD execution visible.

Run other deterministic repository/configuration/schema checks when their artifact classes are applicable.

Inherited-only unrelated failures are report-only for this Spec.

### Visible Gate Evidence

The operator must be able to see what ran. For every deterministic or test gate, emit a concise execution record in the transcript:

```text
GATE: <name>
COMMAND: <exact command or owning skill>
RESULT: PASS | FAIL | NOT APPLICABLE
EXIT: <exit code | N/A>
SUMMARY: <concise native result>
```

Do not suppress successful command output solely to save presentation space.

If native output is naturally large, preserve it in a temporary log and show the command, exit code, and meaningful summary rather than injecting the full log into model context. Do not claim a gate ran when only applicability was inferred.

## 6. Acceptance Tests and Service Preflight

Derive the smallest complete pytest scope that directly exercises the Spec acceptance behavior.

Every pytest invocation must set:

```text
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>
```

Before pytest, perform the mandatory exact-scope service preflight from `AGENTS.md` and `docs/process/testing-guide.md`.

For service-backed scopes, verify required environment/configuration and service readiness before pytest. A timeout, connection failure, or skip is not a preflight.

Never expose secrets or authenticated connection strings.

Where multiple required test files share the same service classification and prerequisites, run them in one cohesive pytest invocation rather than serial tiny invocations.

A required check skipped because prerequisites are absent remains unresolved.

Record every pytest invocation through **Visible Gate Evidence**.

## 7. Establish Semantic Proof

Only after fail-fast deterministic gates and required acceptance tests pass, establish semantic proof for every Spec Contract Manifest cell.

Use direct current evidence. Prefer:

1. exact implementation/configuration/document/tracker inspection;
2. already-executed deterministic gate/test evidence;
3. narrow reference/search checks required to exclude a falsifier;
4. CodeGraph or equivalent transitive exploration only when an exact cell requires call-path/blast-radius proof that direct evidence cannot establish cheaply.

Do not perform broad exploratory analysis merely because a tool is available.

### Cell-to-Proof Map

Maintain exactly one coverage row for every manifest cell:

```text
Cell: <ID>
Proof Object: <P-n>
State: proven | not-applicable | unresolved
```

Manifest and coverage order must match exactly. Every manifest cell appears once, no unknown cell exists, every cell maps to one proof object, and every proof object is referenced.

### Proof Object Contract

Group cells only when one predicate/falsifier/domain/evidence set truly proves every mapped claim.

Represent each Proof Object as data:

```json
{
  "proof": "P-1",
  "cells": ["US-1"],
  "predicate": "...",
  "falsifier": "...",
  "domain_boundary": "...",
  "nested_universe": {"mode": "explicit|exhaustive|not-applicable", "...": "..."},
  "evidence": [
    {"kind": "repository", "ref": "path:lines", "path": "path/to/file.py"}
  ],
  "assumptions": [],
  "disposition": "proven|not-applicable|unresolved"
}
```

Semantic rules:

- preserve every material clause, quantifier, condition, exception, and named surface;
- the falsifier must be a real logical counterexample;
- evidence must address the predicate directly;
- `proven` requires the verifier to establish that the falsifier does not survive across the authoritative domain;
- material assumptions must be authoritative/directly proven;
- `not-applicable` requires an exact originating-Spec reason;
- uncertainty is `unresolved`, which blocks PASS.

### Nested Universe Closure

When a predicate quantifies over a finite/discoverable domain (`all`, `every`, `no`, `none`, `only`, `complete`, repository-wide, named complete set, or equivalent), include a Nested Universe witness:

1. `explicit` — enumerate every current member/disposition, or provide a deterministic generator plus member count/digest; or
2. `exhaustive` — name a deterministic/queryable mechanism whose semantics cover the full authoritative boundary and preserve the complete result needed to exclude the falsifier.

Use `not-applicable` only when there is no material exhaustive/domain-closure predicate, with a reason.

A changed-file list, examples, targeted tests, or “searched relevant files” is not exhaustive unless the authoritative domain is exactly that set.

### Deterministic Packet Admission

Construct the packet **as JSON data**, not a generated Python program, with:

```text
spec_issue
head
baseline
spec_body_hash
spec_contract_hash
manifest
coverage
proof_objects
```

Then run:

```bash
PACKET_INPUT=$(mktemp)
PACKET_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" prepare-packet \
  --input "$PACKET_INPUT" \
  --output "$PACKET_FILE"
```

`prepare-packet` validates complete manifest↔coverage↔proof mapping, Proof Object structure, Nested Universe form, disposition consistency, and stable hashes.

Resolve admission errors locally. No subagent certification step exists.

## 8. Failure and Repair

For an ordinary failure classify it as:

- failed Spec contract obligation;
- Spec-owned repository-standard/tooling failure;
- inherited-only unrelated repository defect.

Fix the narrowest authoritative point only for the first two categories. Inherited-only unrelated defects are report-only.

When accepted architecture unambiguously determines the fix, repair through the authoritative owner:

- implementation → affected implementation surface;
- entity knowledge → `$wiki-sync`;
- new non-ADR documentation → `$to-doc`;
- classification/relocation → `$classify-doc`;
- ADR realization/reference maintenance → `$to-adr-doc`.

If correction requires choosing/changing a durable invariant, owner/path, boundary, dependency direction, lifecycle responsibility, or resolving genuinely conflicting authorities, collect the blockers and halt:

> ⚠️ **Spec verification is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```

Do not propose the architectural answer.

### Repair Economy

If verification changes repository state:

1. repair the narrowest authoritative point;
2. rerun only gates/tests/proof evidence invalidated by the mutation;
3. rebuild affected Proof Objects;
4. require all coverage states resolved at the new candidate `HEAD`;
5. rerun any final mutable guard invalidated by the mutation.

If verification made repository changes:

1. verify Spec branch;
2. stage only verification-owned files;
3. invoke `$conventional-commits`;
4. commit;
5. push with `git push -u origin HEAD`;
6. rebuild final contract/packet/state for the new exact `HEAD`.

Do not preserve proof across an uncertain mutation.

## 9. Establish Final State

At the stable candidate `HEAD`:

1. rerun `$spec-contract` in `build` mode;
2. require body/contract validity and reconcile ownership;
3. require every applicable gate passed or explicitly not applicable;
4. require every manifest cell `proven` or `not-applicable`;
5. require current ticket/hierarchy/dependency state valid;
6. require clean worktree;
7. rebuild the packet through `prepare-packet` if any binding changed.

Build one final JSON state containing:

```text
packet
verification
```

`verification` must include at least:

```text
final_head
branch
mode
prior_checkpoint
default_branch
default_head
change_surfaces
source_counts
ownership
gates
unrelated_inherited_findings
```

Every gate row must contain:

```text
name
status
command
evidence
```

Run deterministic validation:

```bash
FINAL_STATE=$(mktemp)

uv run python "$ARTIFACT_TOOL" validate-final \
  --input "$FINAL_STATE"
```

No certification or carry-forward state exists.

## 10. Receipt Rendering and Persistence

Do not hand-author the receipt or construct another Markdown parser.

Render and validate the complete receipt:

```bash
RECEIPT_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" render-receipt \
  --input "$FINAL_STATE" \
  --output "$RECEIPT_FILE"

uv run python "$ARTIFACT_TOOL" validate-receipt \
  --input "$FINAL_STATE" \
  --receipt "$RECEIPT_FILE"
```

The rendered receipt contains:

- fixed bindings/hashes;
- Spec Contract Integrity counts;
- ownership summary;
- ordered Spec Contract Manifest;
- evidence-backed Proof Objects;
- ordered Spec Contract Coverage;
- exact commands/results for verification gates;
- unrelated inherited findings.

### Atomic Receipt Persistence

Re-run the Project Delivery Actionability Guard, then POST the already validated receipt once:

```bash
RECEIPT_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

jq -Rs '{body: .}' "$RECEIPT_FILE" > "$RECEIPT_JSON"

gh api --method POST \
  "repos/$REPO/issues/$SPEC_NUMBER/comments" \
  --input "$RECEIPT_JSON" \
  > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]

gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j '.body' > "$READBACK_FILE"

cmp -s "$RECEIPT_FILE" "$READBACK_FILE"

uv run python "$ARTIFACT_TOOL" validate-receipt \
  --input "$FINAL_STATE" \
  --receipt "$READBACK_FILE"
```

Because the local receipt was generated from validated final state, exact byte equality plus deterministic re-render validation proves persisted-body integrity.

Never POST/PATCH a partial receipt, repair a malformed persisted receipt in place, replace it with a file reference, or create a second corrective receipt in the same invocation.

If POST succeeds but exact readback/validation fails, verification is incomplete: report `COMMENT_URL` and stop.

Any later Spec-body change or candidate commit makes the receipt stale.

## 11. Successful Lifecycle Transition

A successfully persisted and readback-validated receipt establishes:

```text
Artifact Type: Spec
Workflow State: Ready to Review
Work Status: Ready
Next Skill: $review-spec
Root Blocker: None
Completed On: None
```

## Mandatory Project Reconciliation

Immediately after the authoritative receipt transition and before Human Handoff, invoke `$project-tracking` as prescribed internal composition for the Spec with exactly that base projection.

Recover project-delivery context only after receipt persistence succeeds.

- intentionally non-Wayfinder Spec → `Project Delivery State = independent`;
- Wayfinder-managed Spec → current authoritative classification recovered from durable project-delivery state.

Preserve `Area` and `Priority` unless separately authorized to change them.

`PROJECT TRACKING: DRIFT` does not invalidate the passing receipt or roll back `Ready to Review`. Report projection drift and continue the otherwise-authorized handoff.

## 12. Reporting and Human Handoff

Report concisely:

- baseline/final `HEAD`;
- verification mode/checkpoint;
- Spec contract counts/hash;
- ownership classification;
- every applicable gate and exact result;
- manifest coverage summary;
- proof-object count/hash;
- repaired failures;
- unrelated inherited findings;
- commit/push/final worktree;
- receipt URL;
- Project reconciliation result.

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

Then stop. Do not invoke `$review-spec` implicitly.
