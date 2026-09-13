---
name: verify-spec
description: Perform authorized Spec-wide integration verification and repairs, including applicable repository-wide invariant gates, then obtain fresh independent semantic certification before persisting a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify a completed Spec as one integrated acceptance universe and record a passing receipt only after a fresh independent `$verify-spec-closure` certifier proves the exact stable HEAD.

This `SKILL.md` is the single authoritative procedure for `$verify-spec`. The preserved integration/gate/repair/finalization procedure later in this file remains normative except where the hardening sections immediately below explicitly supersede older wording.

## Session-Stable Spec Contract Consumption

This section is authoritative for contract reconstruction and supersedes preserved wording that treats model-authored manifest display prose as contract identity.

`$spec-contract` owns structural contract identity. Its current V2 `SPEC_CONTRACT_HASH` binds the exact Spec body plus deterministic Source Unit identity/classification and source-unit-to-cell mapping; manifest `Source`, `Requirement`, `Named surfaces`, and inventory `Reason` prose are not contract identity.

Consequences for `$verify-spec`:

* loss of the ephemeral `CONTRACT_HANDOFF` is not loss of durable verification state;
* after interruption, rebuild the handoff by invoking `$spec-contract` against the same durable Spec/baseline/branch/HEAD rather than recovering or recreating old model-authored display wording;
* an unchanged Spec with the same source-unit boundaries, classifications, and cell mappings must reproduce the same V2 `SPEC_CONTRACT_HASH` even when explanatory/display wording differs;
* a differing hash is meaningful only when structural contract identity changed or `$spec-contract` is invalid; do not attribute staleness to display-prose differences;
* an old V1 contract hash is not comparable to V2 identity and must be rebuilt before semantic certification/finalization;
* once a fresh V2 handoff is valid, use that exact handoff for the current invocation's certifier dispatch and finalizer; do not merge display rows from an older handoff or receipt into it.

Before consuming a rebuilt handoff after interruption require:

```text
Spec body identity: unchanged or explicitly re-evaluated
Source-unit universe: complete
Unclassified source units: 0
Normative source units without manifest mapping: 0
Cell/source-unit mapping: complete and reconciled
SPEC_CONTRACT_HASH encoding: V2
```

The parent does not need byte-identical historical `Requirement` prose to continue verification. It does need the same structural acceptance universe.

## Authorized Verification Scope and Repair Attribution

This section is authoritative and supersedes preserved wording that treats Git-derived `Spec-owned/Mixed` labels as semantic ownership, uses repository-wide Ruff/Mypy scope by default, or allows a gate failure to authorize repair merely because the affected file changed on the Spec branch.

`$spec-contract` now supplies **change provenance**, not semantic lifecycle ownership. Preserve the complete `branch-local`, `mixed-provenance`, `inherited-only`, and `unchanged/named` candidate universe it returns.

Before executing any scope-sensitive gate, build one working **Verification Scope Manifest** from that provenance plus exact Spec obligations and directly affected consumer/contract surfaces:

```text
Gate: <gate identity>
Candidate: <repository/tracker/consumer surface>
Provenance: <branch-local | mixed-provenance | inherited-only | unchanged/named>
Scope disposition: <target | excluded | unresolved>
Authority/reason: <exact contract/impact reason>
```

Rules:

* every candidate relevant to a gate receives exactly one disposition; omission is not exclusion;
* `target` means the gate must include the candidate;
* `excluded` requires durable authority or independently checkable evidence that the candidate cannot affect the active Spec verification claim; path/category/branch locality alone is insufficient;
* `unresolved` blocks PASS;
* contract-impact discovery may add unchanged consumers when they can observe a Spec-relevant transition;
* do not invent repository-wide scope merely because a tool accepts `.`;
* repository-wide scope is legal only when an exact active Spec obligation/contract transition is itself repository-wide or another authoritative gate contract explicitly requires whole-repository execution;
* when repository-wide scope is not authorized, later preserved examples using `ruff ... .` or `mypy .` are superseded.

For Python quality gates, the ordinary target universe is the union of:

1. branch-local and mixed-provenance Python candidates that the Verification Scope Manifest classifies `target` from exact Spec/impact authority;
2. unchanged Python consumers classified `target` by direct contract-impact closure;
3. directly affected tests classified `target` because they are required to type/format/lint the active transition coherently.

Branch-local Python work classified `excluded` is not part of the current Spec quality gate merely because it shares the branch.

Use:

```bash
uv run --locked ruff format --check <authorized_python_targets>
uv run --locked ruff check <authorized_python_targets>
uv run --locked mypy --explicit-package-bases <authorized_python_targets_and_affected_tests>
```

Do not replace those targets with `.` unless the Verification Scope Manifest explicitly proves repository-wide scope is required.

A broad exploratory command may still be useful, but it is not automatically a required Spec gate. If an executed required check observes a failure, retain that failure exactly as required by **Observed Failure Disposition** below.

### Failure causality and repair authority

Failure disposition is semantic relevance, not Git provenance. For preserved failure rows, use:

```text
Disposition: spec-relevant | non-spec | unresolved
```

* `spec-relevant` means the active Spec obligation, Spec-authorized contract transition, or directly affected consumer owns the failed behavior; repair is required;
* `non-spec` means the failure is real but no current Spec obligation/authorized transition owns it; it is report-only for this Spec;
* `unresolved` blocks PASS.

A `non-spec` disposition requires independently checkable causal evidence. Valid witnesses include baseline reproduction, deterministic delta/impact proof, exact absence from the active Spec/consumer contract combined with a stable external/project owner, or fresh non-mutating semantic certification when causality remains judgmental.

Branch-local provenance is **never** sufficient evidence for `spec-relevant`; inherited provenance is **never** sufficient evidence for `non-spec`.

Only `spec-relevant` failures authorize `$verify-spec` repository repair. Do not edit a file merely to make a broad command green when the failure is outside the active Spec's semantic/impact universe.

After a `non-spec` failure is causally dispositioned, rerun the authorized target scope when needed to obtain the actual Spec gate result. The original observed failure remains recorded; the narrower authorized rerun does not erase it.

### Delegated repository-wide deduplication exception

`$deduplicate-code` is an explicit repository-wide delegated quality gate when this workflow classifies it applicable.

When invoked:

* the child skill owns its whole-repository Arid/JSCPD scan scope and terminal zero-unsuppressed-findings contract;
* the child skill may perform only the narrowly bounded consolidation or justified source-suppression repairs its own contract requires, including on files outside the active Spec's semantic ownership;
* those child-owned repairs are authorized by the delegated deduplication gate itself and are **not** prohibited by the ordinary `non-spec = report-only` rule above;
* child-internal duplicate findings that are fully resolved inside `$deduplicate-code` do not each become parent `Observed Failure Disposition` rows; the parent consumes the child's terminal result and records repository mutation/evidence normally;
* any unresolved child result remains a required delegated-gate failure and blocks PASS;
* repository-wide deduplication repair does not broaden Ruff, Mypy, Pytest, acceptance-test, or unrelated cleanup authority.

If `$deduplicate-code` mutates the repository, treat those mutations as verification-owned changes for branch/candidate/commit handling. Any prior exact-HEAD semantic certification becomes stale under the normal Exact-HEAD Invalidation rule.

### Delegated repository-wide architecture invariant exception

`$verify-architecture` is an explicit repository-wide delegated invariant gate when the integrated Spec can affect mechanically enforced Polaris architecture.

Classify it applicable when Spec-owned/Mixed work changes current Python under `src/polaris/`, current tests under `tests/`, current migration Python scanned by `tests/architecture_guard.py`, the architecture guard/tests themselves, or accepted architecture authority whose mechanically enforceable rule is represented by the guard.

When invoked:

* the child skill owns its complete architecture-suite scope and terminal zero-failures/zero-live-violations contract;
* the child may perform only narrowly bounded repairs for repository architecture violations, architecture-guard defects, or realization of an architecture change already established by current accepted authority, including on files outside ordinary Spec semantic repair ownership;
* those child-owned repairs are authorized by the delegated architecture gate itself and are **not** prohibited by the ordinary `non-spec = report-only` rule above;
* child-internal architecture failures that are fully resolved inside `$verify-architecture` do not each become parent `Observed Failure Disposition` rows; the parent consumes the child's terminal result and records repository mutation/evidence normally;
* if correct repair would require inventing or changing durable architectural semantics, the child returns `ARCHITECTURE INVARIANT: UNRESOLVED`; route that blocker set to `$architecture-remediation` rather than making a pass-only repair;
* repository-wide architecture repair does not broaden ordinary Ruff, Mypy, acceptance-test, deduplication, or unrelated cleanup authority.

When this gate runs inside `$verify-spec`, use the committed locked Polaris environment required by `$verify-architecture`. `uv` may synchronize `.venv` and build/install Polaris as generated local state, but `uv run --locked` must not rewrite `uv.lock`; missing or stale lock state is a dependency-state blocker rather than verification-owned cleanup.

If `$verify-architecture` mutates the repository, treat those mutations as verification-owned changes, rerun every invalidated parent gate/test/evidence, commit/push through the normal verification-owned mutation path, refresh exact-HEAD contract bindings, and obtain fresh semantic certification. Any prior exact-HEAD semantic certification is stale.

### Conditional/deferred evidence handoff

When the current Spec contract contains a materially conditional obligation, recover its current decomposition disposition from the parent `Ticket Coverage Manifest` when available and pass that evidence to `$verify-spec-closure`.

Do not strengthen an inactive condition into present implementation/automation merely to prove the cell. Do not silently treat it as absent either. The semantic certifier owns whether the trigger is active and whether a valid inactive/deferred disposition is entailed by the source and durable routing evidence.

Before finalization require:

```text
Verification-scope candidates: <n>
Verification-scope rows: <n>
Unclassified scope candidates: 0
Unresolved scope candidates: 0
Repository-wide gates without explicit authority: 0
Observed failures without causal disposition: 0
Repairs without spec-relevant or explicit delegated-gate authority: 0
```

## Separation of Authority

The `$verify-spec` parent owns:

* deterministic Spec Contract construction;
* change-provenance recovery and verification-scope attribution;
* delivery/actionability guards;
* deterministic and delegated gate execution;
* acceptance-test execution and service preflight;
* observed-failure disposition;
* Spec-relevant repair and explicitly delegated repository-wide gate repair;
* stabilizing the exact candidate HEAD;
* deterministic receipt assembly/persistence after certification.

The parent does **not** own final semantic certification of the candidate it has just verified/repaired.

A genuinely fresh non-mutating `$verify-spec-closure` subagent owns:

* per-manifest-cell semantic entailment;
* authoritative/nested domain construction and closure;
* falsifier exclusion;
* production-composition proof where required by the claim;
* negative/fail-closed semantic proof;
* complete failure saturation for the bounded authoritative universe;
* one complete `SPEC CLOSURE: PASS | FAIL` for the exact stable HEAD.

`$review-spec` remains the later independent adversarial Standards / Spec / Architecture review. Do not duplicate its multi-axis review, root reconciliation, or challenge/saturation procedure here.

## Semantic Candidate Gate

Follow the procedure below through deterministic/delegated gates, acceptance tests, observed-failure disposition, and all actionable Spec-relevant repairs.

At the point where older wording below would establish semantic proof itself:

1. finish all parent-owned gates and failure disposition;
2. require a clean worktree;
3. pin exact `BASELINE_COMMIT`, branch, current `HEAD`, Spec body hash, Spec contract hash, current change provenance/scope state, architecture impact, and native gate/test evidence;
4. rebuild/refresh the `$spec-contract` handoff if prior repair changed HEAD;
5. treat that exact state as the immutable semantic-certification candidate.

The parent may prepare **evidence pointers** for each manifest cell, but it must not mark the semantic cell proven/not-applicable from its own judgment.

## Fresh Spec Certifier Dispatch

The existing human invocation of `$verify-spec` authorizes semantic certification; no second human handoff is required.

At stable candidate HEAD, the parent enters dispatcher-only mode for semantic certification.

It may only:

1. capture the exact candidate bindings;
2. spawn exactly one genuinely fresh verifier subagent;
3. pass:
   * Spec issue/body identity;
   * exact baseline/branch/HEAD;
   * deterministic `$spec-contract` handoff/manifest and hashes;
   * change-provenance and Verification Scope Manifest state;
   * applicable current architecture authority/context;
   * native deterministic/delegated gate results;
   * acceptance-test/preflight evidence;
   * observed-failure disposition state;
   * concise evidence pointers collected by the parent;
4. require that subagent to execute `$verify-spec-closure` as a non-mutating leaf;
5. receive one complete `SPEC CLOSURE: PASS | FAIL` or one explicit invalid/incomplete certification result;
6. re-read exact HEAD/worktree and mutable contract-critical state needed to establish the verifier did not mutate the candidate;
7. mechanically validate the returned saturation witness below before consuming PASS or FAIL;
8. consume a complete verdict without semantic override.

While dispatcher-only, the parent must not perform a parallel semantic proof, search for evidence to overturn the verifier, mutate the candidate, repair findings, or dispatch shadow certifiers/reviewers.

A verifier-integrity failure or incomplete saturation witness invalidates the attempt and must be resolved before certification can continue.

## Certifier Proof Contract

`$verify-spec-closure` independently certifies every manifest cell from the exact authoritative claim.

The following are hard requirements before **either PASS or FAIL** is consumable:

* exact evidence entailment per cell;
* no broad proof object silently certifies materially heterogeneous claims;
* every finite/discoverable nested quantified domain has durable authority and a membership predicate;
* every required Domain Construction Manifest is complete;
* finite expected/generated/inspected/dispositioned counts reconcile, or the declared open-world exhaustive mechanism satisfies its closure criterion;
* remaining authoritative members are zero;
* violated cells with incomplete nested sweeps are zero;
* ambiguous/undispositioned domain-membership candidates are zero;
* unexplored authoritative siblings are zero;
* every independently actionable defect found by the saturated sweep appears in the returned findings;
* production-path claims reach canonical composition, not merely component capability;
* negative/fail-closed claims receive meaningful adversarial falsifier proof;
* every material assumption bridging evidence to conclusion is proven;
* `unchecked=0`.

Passing parent tests/gates remain evidence of what they actually establish. They are not semantic proof of unrelated or stronger claims.

### Certifier Saturation Witness

Before consuming either semantic verdict, require the child result to carry enough mechanically checkable state to establish that universe construction and sweep saturation completed:

```text
Manifest cells: <n>
Nested domains required: <n>
Domain construction manifests complete: <n>/<n>
Generated authoritative members: <n>
Inspected authoritative members: <n>
Dispositioned authoritative members: <n>
Remaining authoritative members: 0
Violated cells with incomplete domain sweep: 0
Domain-membership candidates: <n>
in-domain: <n>
out-of-domain: <n>
ambiguous membership: 0
Undispositioned domain candidates: 0
Independent actionable findings: <n>
Unexplored authoritative siblings: 0
Unproven material assumptions: 0
```

The parent validates identities and counts only. It does not decide whether a candidate belongs to a semantic domain or whether evidence entails a claim; those judgments remain owned by the fresh certifier.

Missing, contradictory, or non-zero incomplete-saturation fields make the certification result invalid/incomplete. Do not reinterpret it as PASS or FAIL, do not enter the repair loop from a partial finding set, and do not persist a receipt.

## FAIL Loop

`SPEC CLOSURE: FAIL` is non-terminal and does not authorize a Spec Verification Receipt.

Consume FAIL only after exact candidate binding, verifier integrity, and the Certifier Saturation Witness are valid and complete.

After a complete verifier FAIL returns:

1. exit dispatcher-only mode;
2. retain every returned independently actionable finding as current verification state;
3. classify whether each finding is Spec-relevant repair, unresolved architecture, external/environmental blocker, or a deterministic contract defect requiring the owning workflow;
4. repair every actionable Spec-relevant finding through the normal procedure and required owner skills;
5. rerun only invalidated gates/tests/failure dispositions;
6. refresh exact-HEAD `$spec-contract` bindings;
7. obtain another fresh semantic certification for the new stable candidate.

Do not drop a prior semantic failure merely because a narrower rerun passes. It remains current until the exact falsifier/claim is re-proven or explicitly superseded by authoritative contract change.

If a finding requires a new durable architecture decision, use the architecture-remediation handoff below; the certifier does not invent that decision.

## PASS Consumption

Accept `SPEC CLOSURE: PASS` only when:

* Spec/baseline/branch/HEAD/body hash/contract hash match dispatch exactly;
* candidate and required mutable authority did not change unexpectedly during certification;
* certifier was genuinely fresh, non-mutating, and non-delegating;
* the Certifier Saturation Witness is present, internally reconciled, and complete;
* every manifest cell is `proven` or valid originating-Spec `not-applicable`;
* no violated/unproven/unchecked cell remains;
* all required nested domains are closed;
* remaining authoritative members are zero;
* ambiguous/undispositioned domain candidates and unexplored authoritative siblings are zero;
* independent actionable findings are zero.

The parent may validate identities/counts/hashes mechanically. It may not reinterpret a semantic FAIL into PASS.

## Finalizer Integration

After valid independent PASS, construct the compact `PROOFS_INPUT` required below **from the certifier's returned coverage**, not from parent-authored semantic conclusions.

The parent may mechanically group cells only when the certifier returned the same state and same supporting evidence for those cells. It must not broaden the certifier's entailment claim while compacting the receipt.

`GATES_INPUT` remains parent-owned and follows the procedure below.

Then execute the unchanged finalization and receipt persistence mechanics.

The receipt should identify the semantic certification owner/result concisely, for example in a gate/evidence line:

```text
Independent semantic closure: PASS — $verify-spec-closure at exact HEAD <sha>; manifest <n>; violated 0; unproven 0; unchecked 0; domain construction <n>/<n> complete; remaining authoritative members 0; open nested domains 0
```

Do not serialize private reasoning transcripts.

## Exact-HEAD Invalidation

Any repair that changes repository HEAD invalidates prior semantic certification.

A mutable architecture/tracker authority change that affects a certified cell also invalidates that cell/certification.

Reuse is legal only when a prior independent certifier established an explicit invalidation boundary and deterministic fail-closed delta analysis proves the exact proof remains valid. Otherwise recertify.

The exact-HEAD receipt short-circuit below remains legal only when its independent semantic certification is part of the matching receipt and all mutable revalidation requirements still pass.

## Downstream Boundary

A passing `$verify-spec` result means:

> The exact integrated Spec candidate passed deterministic/integration verification and fresh semantic certification against the full Spec contract.

It does not replace `$review-spec`.

The next lifecycle remains the handoff to `$review-spec`, which independently challenges Standards, Spec conformity, architecture, and prior closure confidence.

## Procedure

Verify a completed Spec against its fixed baseline as one integrated acceptance universe. A passing run records a **Spec Verification Receipt** for the exact final `HEAD`; `$review-spec` owns the independent adversarial review that follows.

## Core Invariants

- Recover correctness-critical state from the repository and durable tracker, not prior conversation.
- The `$spec-contract` manifest is the complete acceptance universe.
- Every manifest cell ends `proven`, `not-applicable`, or `unresolved`; any `unresolved` blocks PASS.
- Spec-owned/Mixed surfaces determine repository-standards ownership. Inherited-only unrelated defects are report-only.
- Every observed failure must receive an explicit causal disposition before it can be excluded from PASS.
- A required delegated skill owns its gate procedure and terminal result; the parent may not substitute an ad hoc local implementation.
- Final semantic certification belongs to one fresh `$verify-spec-closure` verifier; the `$verify-spec` parent may prepare evidence but may not self-certify semantic PASS.
- A first semantic falsifier determines verdict polarity only; complete bounded domain construction and sweep saturation are required before the parent may consume either PASS or FAIL.
- Reason about predicates, falsifiers, authoritative domains, Nested Universe closure, assumptions, and evidence, but do **not** serialize that reasoning merely for bookkeeping.

## Deterministic Utility Boundary

Use:

```text
.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
```

It owns only:

- paginated Spec-comment normalization, canonical Workspace Metadata parsing, and latest-receipt extraction;
- contract/proof/gate final-state assembly from the exact `$spec-contract` handoff;
- compact finalization validation;
- complete manifest-to-proof coverage validation;
- one canonical Verification Hash;
- compact receipt rendering.

Do not recreate those mechanics with ad hoc Python, custom parsers, multi-stage `jq`, or a model-authored final-state wrapper. If the utility cannot represent a required invariant, fix it rather than bypassing it.

## 1. Pin the Fixed Point

Read the complete Spec comment history once:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>
ARTIFACT_TOOL=.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
SPEC_COMMENTS_FILE=$(mktemp)
SPEC_COMMENTS_SUMMARY=$(mktemp)
CONTRACT_HANDOFF=$(mktemp)

gh api --paginate --slurp \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100" \
  > "$SPEC_COMMENTS_FILE"

python "$ARTIFACT_TOOL" comments \
  --input "$SPEC_COMMENTS_FILE" \
  > "$SPEC_COMMENTS_SUMMARY"

BASELINE_COMMIT=$(jq -r '.baseline_commit' "$SPEC_COMMENTS_SUMMARY")
```

The utility recognizes exactly one authoritative baseline source: one comment containing the standalone header `## Workspace Metadata` and exactly this field format:

```text
**Baseline Commit Hash:** <40 lowercase hex SHA>
```

The SHA is not backticked, shortened, uppercased, or decorated. A baseline label in any other comment is informational only and never baseline authority. Missing, duplicate, or malformed Workspace Metadata fails closed. Do not parse or recover a baseline independently.

Do not substitute an unpaginated comment read. This is the invocation's one full comment-history read; do not repeat it after receipt persistence merely to rediscover the comment just posted.

Require:

- current branch `spec-<spec_issue_number>`;
- resolvable `BASELINE_COMMIT`;
- clean worktree.

Capture:

```bash
git diff "$BASELINE_COMMIT"...HEAD
git log "$BASELINE_COMMIT"..HEAD --oneline
```

A tracker-only Spec may have an empty diff only when durable evidence proves no repository mutation was required.

## 2. Build the Contract and Guard Delivery

Invoke `$spec-contract` in `build` mode with the Spec, baseline, branch, current `HEAD`, and `handoff-output = CONTRACT_HANDOFF`. Require `SPEC CONTRACT: VALID`, a non-empty `CONTRACT_HANDOFF`, and retain exactly the returned:

- `SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH`;
- ordered manifest;
- source counts/integrity counts;
- ownership classifications;
- immutable default branch/head.

`$spec-contract` owns serialization of the finalizer-facing contract handoff while the canonical manifest is already in context. Do not independently recreate, pretty-print, copy, or re-key the manifest/source-count payload later in this workflow.

Do not independently refresh or reinterpret default-branch ownership.

Capture Architecture Impact. Unresolved material architecture blocks verification and routes to `$architecture-remediation`.

For a Wayfinder-managed Spec, before substantive verification:

1. require the Spec open and all direct native blockers closed;
2. recover every governing Wayfinder; ambiguity fails closed;
3. invoke `$project-delivery-management` `reconcile`;
4. invoke `$project-delivery-management` `guard <Wayfinder>` for every governor;
5. require at least one `PROJECT DELIVERY GUARD: ALLOWED`.

Do not change focus. Re-run the guard only when mutation may change actionability and immediately before persisting a passing receipt.

## 3. Exact-HEAD Checkpoint

Use only `latest_receipt` from the deterministic comment summary.

A passing receipt may short-circuit immutable work only when it matches the exact current:

- `HEAD`;
- branch;
- baseline;
- `SPEC_BODY_HASH`;
- `SPEC_CONTRACT_HASH`.

Even then, revalidate mutable hierarchy/dependency/focus state, mutable/time-dependent gates, and clean worktree. An ancestor receipt never carries proof forward across a changed `HEAD`.

## 4. Classify and Run Fail-Fast Gates

Use `$spec-contract` ownership to classify applicable Code, Tests, Documentation, Agent-skill/workflow, Configuration, CI/automation, Data/schema/migrations, and Tracker-only surfaces.

Every candidate gate is `required`, `not-applicable`, or `unresolved`. Do not run a gate solely because an Inherited-only surface appears in integration history.

Run cheap deterministic gates before semantic proof. When repository content changed:

```bash
git diff --check "$BASELINE_COMMIT"
```

When code quality applies:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run --locked ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run --locked ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run --locked mypy . --explicit-package-bases
```

Never use Ruff `--add-noqa`.

Run the deterministic verifier self-test when this workflow utility is in scope:

```bash
python "$ARTIFACT_TOOL" self-test
```

Invoke the `$wiki-lint` skill when Living Entity Wiki routing applies. Invoke the `$deduplicate-code` skill only when Spec-owned/Mixed work creates a real duplicate-implementation risk; when invoked, both Arid and JSCPD must be visible.

Invoke `$verify-architecture` when the integrated Spec can affect mechanically enforced architecture under the applicability rule above. Its complete architecture suite is intentionally repository-wide even when ordinary Python quality targets are narrower. Do not substitute an individual architecture test or direct guard call for the child skill.

Run other deterministic checks only when their artifact classes apply.

Inherited-only unrelated failures are report-only only after **Observed Failure Disposition** below proves that causal classification. Surface ownership alone is not causal evidence.

### Delegated Gate Ownership

When this workflow requires another skill to decide or execute a gate, that child skill owns the procedure and terminal result. The parent must not search for a same-named script, recreate a subset of the child procedure with shell commands, or substitute its own ad hoc audit and then report the delegated gate as passed.

Maintain a working delegated-gate inventory:

```text
Delegated gate: DG-<n>
Owner skill: $<skill>
Applicability: <required | not-applicable>
Execution: <executed | unavailable>
Terminal result: <valid child result | unresolved | not-applicable>
Evidence/reason: <native child-skill result/reference or exact N/A reason>
```

Rules:

- `required` means the exact owner skill must be invoked and its current contract followed;
- `unavailable` leaves the gate `unresolved`; it does not authorize parent substitution;
- `not-applicable` requires the same concrete applicability reason the parent uses for the gate;
- a gate may enter final `GATES_INPUT` as PASS only when the owning skill produced a valid terminal result supporting PASS;
- a delegated gate may not disappear because local commands appeared equivalent or because the parent believes it can reproduce the child skill's checks more cheaply.

Before finalization require:

```text
Delegated gate candidates: <n>
Delegated gate rows: <n>
Unclassified delegated gates: 0
Required delegated gates without valid terminal result: 0
```

### Transcript Discipline

The native command/skill transcript is the execution record. Do **not** echo separate `GATE`, `COMMAND`, `RESULT`, `EXIT`, or `SUMMARY` blocks after commands run.

Successful native output may remain visible. For very large output, capture it to `/tmp` and surface only the useful tail/summary while preserving the real command and exit status in the native transcript.

## 5. Acceptance Tests and Service Preflight

Derive the smallest complete pytest scope that directly exercises the Spec acceptance behavior. Every pytest command must set:

```text
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>
```

Before pytest, perform the exact-scope service preflight from `AGENTS.md` and `docs/process/testing-guide.md`. A timeout, connection failure, or skip is not a preflight. Missing prerequisites leave the check unresolved.

Group test files that share the same service classification/prerequisites into one cohesive invocation. Never expose secrets or authenticated connection strings.

## 6. Prepare Semantic Evidence

After deterministic gates and required tests pass, prepare concise current evidence pointers for every manifest cell for the fresh `$verify-spec-closure` certifier.

Prefer, in order:

1. exact implementation/config/document/tracker inspection;
2. already-executed gate/test evidence;
3. narrow searches needed to expose relevant domain members;
4. CodeGraph/transitive exploration only when direct evidence cannot establish the required call-path or blast-radius evidence cheaply.

For each cell preserve every material clause, quantifier, condition, exception, and named surface in the handoff. The parent must not turn these pointers into its own semantic `proven`/`not-applicable` verdict. The fresh certifier independently derives falsifiers, closes authoritative and nested domains, evaluates assumptions, and decides semantic state.

Parent-prepared evidence may be grouped only when the same evidence genuinely applies to every mapped claim. Passing tests, examples, or targeted searches remain evidence pointers, not semantic certification.

## 7. Failure and Repair

Every failure observed from a required deterministic gate, delegated gate, service preflight, acceptance-test invocation, or independent semantic certification enters the working **Observed Failure Disposition** universe immediately. A later narrower rerun does not erase the earlier observation.

For every observed failure record:

```text
Failure: VF-<n>
Origin: <gate/test/preflight/delegated-skill/certifier identity>
Observed failure: <concise exact failure>
Affected contract/behavior: <boundary or obligation implicated>
Disposition: <spec-owned | inherited-unrelated | unresolved>
Witness: <independently checkable causal evidence>
```

Disposition rules:

- `spec-owned` covers a failed Spec obligation or Spec-owned/Mixed repository-standard/tooling failure and requires repair;
- `inherited-unrelated` is report-only, but requires evidence that the failure is causally independent of the Spec change; ownership classification alone is insufficient;
- valid independence witnesses include deterministic reproduction at the immutable baseline, deterministic delta analysis excluding interaction with the Spec change, or fresh non-mutating semantic certification when causal independence is not mechanically decidable;
- `unresolved` blocks PASS;
- a failure may not disappear because the verifier narrows a later command, removes a failing file from a selected test set, calls the surface inherited, or obtains a passing rerun over a smaller universe.

Before finalization require:

```text
Observed failures: <n>
Failure disposition rows: <n>
Undispositioned failures: 0
Unresolved failures: 0
Spec-owned failures remaining: 0
Inherited exclusions without sufficient witness: 0
```

When no failure was observed, record `Observed failures: 0`; do not manufacture rows.

Repair only Spec-owned failures at the narrowest authoritative point **except for repository-wide repairs explicitly owned and completed by an applicable delegated invariant gate such as `$deduplicate-code` or `$verify-architecture`**. Use the owning skill where required (`$wiki-sync`, `$to-doc`, `$classify-doc`, `$to-adr-doc`, etc.). A fix that requires choosing/changing a durable architecture invariant routes to `$architecture-remediation`; do not invent the decision locally.

After a repair:

1. rerun only invalidated gates/tests/evidence;
2. update the affected failure dispositions rather than deleting prior observed-failure rows;
3. refresh only affected evidence pointers;
4. require a fresh `$verify-spec-closure` certification for the new stable candidate unless an independently certified invalidation boundary proves reuse safe;
5. rerun mutable guards invalidated by the change.

If verification changes the repository, verify branch, stage only verification-owned files, invoke `$conventional-commits`, commit, push, then refresh exact-HEAD contract bindings and affected evidence. Do not preserve proof across uncertain mutation.

## 8. Finalize Once

At stable candidate `HEAD`, after valid `SPEC CLOSURE: PASS`:

1. rerun `$spec-contract` in `build` mode with the same `handoff-output = CONTRACT_HANDOFF`, replacing the handoff only after the refreshed contract is valid;
2. require valid body/contract and reconciled ownership;
3. require every applicable gate PASS or NOT APPLICABLE;
4. require Delegated Gate Ownership closure complete;
5. require Observed Failure Disposition closure complete;
6. require the certifier coverage to map every manifest cell to `proven` or valid originating-Spec `not-applicable` with `violated=0`, `unproven=0`, and `unchecked=0`, and require the Certifier Saturation Witness to remain complete with zero remaining authoritative members, ambiguous membership, or unexplored authoritative siblings;
7. require current hierarchy/dependency state valid;
8. require clean worktree.

Create only the two genuinely verification-owned compact arrays:

```text
PROOFS_INPUT = [<proof groups derived from certifier-returned coverage>]
GATES_INPUT = [<gate outcomes>]
```

Rules:

- do not copy the manifest, source counts, hashes, baseline, branch, `HEAD`, or default ownership point into another wrapper; those already exist in `CONTRACT_HANDOFF`;
- proofs contain only `cells`, `state`, and `evidence` or `reason`, preserving the certifier's actual entailment result;
- gates contain only `name`, `status`, and concise native `evidence`; commands are already in the transcript;
- include closure outcomes for delegated-gate ownership, observed-failure disposition, and independent semantic closure when applicable, with their required counts in concise gate evidence;
- serialize the two arrays compactly; do not pretty-print them merely for bookkeeping;
- do not create `FINALIZE_INPUT`, a giant intermediate packet, or a second final-state object.

Run one deterministic assembly/finalization operation:

```bash
PROOFS_INPUT=$(mktemp)
GATES_INPUT=$(mktemp)
RECEIPT_FILE=$(mktemp)

python "$ARTIFACT_TOOL" finalize-parts \
  --contract-input "$CONTRACT_HANDOFF" \
  --proofs-input "$PROOFS_INPUT" \
  --gates-input "$GATES_INPUT" \
  --mode <full|checkpoint> \
  --receipt-output "$RECEIPT_FILE" \
  [--prior-checkpoint <checkpoint>] \
  [--repair <repair>]... \
  [--inherited-finding <finding>]...
```

`finalize-parts` assembles the already-owned contract/proof/gate pieces, validates bindings/coverage/gates through the same canonical finalizer, rejects unresolved cells, computes one Verification Hash, and renders the receipt. There is no model-authored wrapper, separate packet admission, final-state validation, receipt rendering, or pre-persistence receipt-validation phase.

## 9. Persist the Compact Receipt

The receipt is a checkpoint/binding record, not a transcript of semantic reasoning. It retains the manifest/source counts needed by `$review-spec`, compact derived coverage, gate outcomes, repairs, inherited findings, and one Verification Hash. It omits proof prose, proof hashes, duplicate coverage structures, and commands already visible in the transcript.

Immediately before persistence, invoke `$project-delivery-management` `guard <Wayfinder>` again for the already-resolved governing Wayfinders. This is revalidation, not a second delivery-analysis phase: do not explicitly invoke another `reconcile`, rediscover lineage, inspect Project schema, or repeat broader frontier analysis before the guard unless repository/tracker mutation since the prior guard invalidated those inputs. The guard remains authoritative for its own canonical reads and any reconciliation it requires.

Then persist exactly once:

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
```

Exact byte equality proves persisted-body integrity because only a successful canonical finalization can produce the local receipt. `COMMENT_ID` plus successful exact readback is also sufficient proof that this invocation's receipt is durably persisted; do not reread the full paginated Spec comment history or rerun the comment-summary utility afterward merely to prove the newly posted receipt is latest.

Never patch a malformed persisted receipt or create a second corrective receipt in the same invocation. If POST succeeds but readback differs, report `COMMENT_URL` and stop. Any later Spec-body change or candidate commit makes the receipt stale.

## 10. Lifecycle Transition

A successfully persisted receipt establishes:

```text
Artifact Type: Spec
Workflow State: Ready to Review
Work Status: Ready
Next Skill: $review-spec
Root Blocker: None
Completed On: None
```

This lifecycle state is authoritative immediately. GitHub Project projection remains deferred to the repository-wide `$project-tracking` cadence and is not part of this transition.

## 11. Human Handoff

Report concisely:

- baseline/final `HEAD` and verification mode;
- Spec contract count/hash;
- applicable gate results, including `$verify-architecture` when required;
- coverage summary;
- proof-group count and Verification Hash;
- repairs and unrelated inherited findings;
- commit/push/final worktree;
- receipt URL.

On success:

> ✅ **Spec verification passed.**
>
> Please run:
>
> ```
> $review-spec - <Spec Title> (<Spec URL>)
> ```

Then stop. Do not invoke `$review-spec` implicitly.