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

`$spec-contract` owns structural contract identity. Its durable identity is `SPEC_CONTRACT_HASH`; the hash binds the exact Spec body plus deterministic Source Unit identity/classification and source-unit-to-cell mapping. Manifest `Source`, `Requirement`, `Named surfaces`, and inventory `Reason` prose are not contract identity.

Consequences for `$verify-spec`:

* loss of the ephemeral `CONTRACT_HANDOFF` is not loss of durable verification state;
* after interruption, rebuild the handoff by invoking `$spec-contract` against the same durable Spec/baseline/branch/HEAD rather than recovering or recreating old model-authored display wording;
* an unchanged Spec with the same source-unit boundaries, classifications, and cell mappings must reproduce the same `SPEC_CONTRACT_HASH` even when explanatory/display wording differs;
* a differing hash is meaningful only when structural contract identity changed or `$spec-contract` is invalid; do not attribute staleness to display-prose differences;
* once a fresh handoff is valid, use that exact handoff for the current invocation's certifier dispatch and finalizer; do not merge display rows from an older handoff or receipt into it;
* require the handoff to carry the deterministic `contract_identity` rows and retain the `CONTRACT_HANDOFF_DIGEST` returned by that exact `$spec-contract` build.

Before consuming a rebuilt handoff after interruption require:

```text
Spec body identity: unchanged or explicitly re-evaluated
Source-unit universe: complete
Unclassified source units: 0
Normative source units without manifest mapping: 0
Cell/source-unit mapping: complete and reconciled
```

Keep these identities separate:

1. `SPEC_CONTRACT_HASH` — durable cross-run semantic/structural identity, reproduced only from deterministic structural rows plus `SPEC_BODY_HASH`. Human-readable display/evidence prose never participates.
2. `CONTRACT_HANDOFF_DIGEST` — SHA-256 of the exact ephemeral handoff bytes used in one certification/finalization transaction. It is invocation-local only, is never persisted as contract authority, and must never be compared across independent builds.
3. `Verification Hash` — checksum of one finalized verification record. Because that record includes human-readable evidence, it may legitimately differ across independent valid verification runs and is not cross-run contract identity.

The parent does not need byte-identical historical `Requirement` prose to continue verification. It does need the same structural acceptance universe.

### Fresh Contract Builder Isolation

This section is authoritative for every `$spec-contract` **build** consumed by `$verify-spec` and supersedes later wording that implies the parent may itself reconstruct the deterministic Spec contract.

The `$verify-spec` parent owns **dispatch and admission** of contract construction; a genuinely fresh `$spec-contract` builder owns the construction itself.

For every build used for semantic certification or finalization:

1. Resolve only the originating Spec identity, fixed baseline, Spec branch, and exact current `HEAD` needed to dispatch the builder. Do **not** inspect prior scratch contract files or reconstruct a prior contract in the parent first.
2. Allocate a new invocation-owned temporary directory and a handoff path that does not yet exist.
3. Spawn exactly one genuinely fresh, non-mutating builder context and require it to execute `$spec-contract` in `build` mode.
4. Pass only the inputs allowed by `$spec-contract` **Build-Mode Isolation Gate**. Do not pass an expected/prior contract hash, prior manifest/source-unit inventory, prior handoff/digest, prior receipt contract table, proof-reuse material, or scratch artifact.
5. Require terminal `SPEC CONTRACT: VALID`, the exact `CONTRACT_HANDOFF_DIGEST`, and the complete Build-Mode Isolation attestation before consuming the handoff.
6. **Only after the fresh builder returns** may the parent recover or compare a historical/persisted `SPEC_CONTRACT_HASH` for reproducibility/staleness checks. A match proves reproduction; it must never guide construction.
7. The parent must not replace a failed or inconvenient child build with ad hoc Python, manual manifest reconstruction, reverse-parsing of a receipt, or inspection of old `/tmp` contract artifacts.
8. If repair changes `HEAD`, or if the certified handoff is lost, dispatch a new fresh builder with a new nonexistent handoff path and follow the existing recertification rules.

A parent that already knows a historical hash from durable lifecycle state does not contaminate the build **provided that value is not passed into or exposed to the fresh builder before its terminal result**.

If a fresh builder primitive is unavailable, the contract build is unresolved and verification fails closed. The same-instance substitute-agent allowance for independent review does not authorize reconstructing a supposedly fresh contract after that same context has already seen prior contract state.

Before any semantic-certifier dispatch require:

```text
Fresh contract builder dispatched: 1
Fresh builder terminal result: SPEC CONTRACT: VALID
Build isolation: PASS
Prior contract representations supplied or inspected by builder: 0
Pre-existing scratch contract artifacts inspected by builder: 0
Handoff path existed before build: no
Historical hash comparison performed before builder terminal result: no
Parent-side substitute contract construction: 0
```

## Semantic Candidate Anchor and Policy-Only Synchronization

The default rule remains exact-candidate verification. The repository-wide **Non-Semantic Workflow-Policy Synchronization** rule in `AGENTS.md` is the only exception.

Before treating a previously passing receipt as stale solely because current branch `HEAD` differs from its `Verified HEAD`, test that exception first.

Let:

```text
SEMANTIC_ANCHOR = receipt Verified HEAD
DELIVERY_TIP = current spec-<n> HEAD
```

If they differ, require all policy-sync predicates from `AGENTS.md`. In particular:

* `SEMANTIC_ANCHOR` must be an ancestor of `DELIVERY_TIP`;
* the anchor→tip changed paths must be workflow/process authority surfaces only;
* every changed branch blob must equal current default-branch policy;
* no Spec/product/test/migration/configuration/architecture/TCM/review-semantic surface may have changed;
* the workflow delta must be non-semantic with respect to the Spec's product/architecture/standards/acceptance obligations.

When the delta includes `$spec-contract` or another contract/certification-construction rule, run current `$spec-contract` validation against the persisted receipt contract. Reuse is legal only when the same Spec Body Hash and Spec Contract Hash are reproduced. Do not invoke `$to-tickets` merely because an older builder and current builder classified a lifecycle/readiness-only source unit differently; current `$spec-contract` semantic-ownership rules control that classification.

If the policy-only reconciliation passes:

* keep `SEMANTIC_ANCHOR` as the receipt's verified product candidate;
* treat `DELIVERY_TIP` as the current authorized branch tip;
* reuse candidate-bound deterministic and semantic PASS evidence whose explicit mutable inputs remain valid;
* do not dispatch a fresh product semantic certifier or rebuild a new verification receipt solely to move `Verified HEAD` to `DELIVERY_TIP`;
* report the exact policy-only anchor→tip delta in the verification handoff.

If it fails or is ambiguous, ordinary exact-HEAD invalidation applies.

This rule supersedes later wording that says any repository `HEAD` mutation automatically invalidates semantic certification; that wording applies to candidate-semantic mutations, not a proven non-semantic policy-only synchronization.

## Cumulative Spec Certification Retry State

This section is authoritative for semantic retries after a valid saturated `SPEC CLOSURE: FAIL`. It supersedes later wording that can be read as wiping all reusable semantic construction when a repair changes `HEAD`, or as allowing proof reuse to skip the mandatory fresh semantic certifier.

A changed candidate always requires:

1. a fresh isolated `$spec-contract` build for the exact new stable `HEAD` under **Fresh Contract Builder Isolation**;
2. a genuinely fresh non-mutating `$verify-spec-closure` certifier for the current candidate;
3. a fresh whole-candidate verdict.

The prior verdict and prior `CONTRACT_HANDOFF` / `CONTRACT_HANDOFF_DIGEST` are stale after candidate mutation and are never reused as current certification. That does **not** imply that independently saturated semantic construction, evidence, domain inventories, or adversarial knowledge must be discarded.

After every valid saturated FAIL that may lead to another attempt, preserve the exact FAIL result, including its `Cumulative Spec Retry State`, in the workflow's compact verification checkpoint **before** repository/tracker mutation. Bind that state to the prior exact baseline, branch, candidate `HEAD`, Spec body hash, Spec contract hash, and attempt number. Preserve every returned finding/falsifier.

On the next attempt:

1. complete parent-owned repairs and rerun only invalidated deterministic/delegated gates, tests, preflight, and failure dispositions;
2. stabilize one clean exact `HEAD`;
3. dispatch the fresh `$spec-contract` builder without exposing any prior retry state, prior contract representation, or proof-reuse material to it;
4. only after `SPEC CONTRACT: VALID` returns, mechanically compare the new `SPEC_BODY_HASH`, `SPEC_CONTRACT_HASH`, deterministic structural identity rows, and relevant mutable authority identities with the prior retry bindings;
5. dispatch one fresh `$verify-spec-closure` certifier and, for Attempt 2+, additionally supply the prior saturated FAIL/retry state, exact prior→current candidate delta or equivalent repair/change summary, and the current fresh contract handoff/digest;
6. let the fresh certifier own semantic invalidation, reuse, re-proof, prior-finding reconciliation, and the new whole-candidate verdict.

The parent may decide only mechanical eligibility facts such as identity equality, changed surfaces, and whether durable retry state exists. It must not decide that a prior semantic disposition remains valid, reinterpret a prior FAIL, or mark a finding closed. Those judgments belong to the fresh certifier.

If the structural Spec contract changed, still pass the prior findings/retry state as historical adversarial knowledge, but mark the structural mismatch explicitly. The fresh certifier must reconstruct changed or ambiguous construction and may reuse only substate whose governing authority and proof dependencies remain independently valid.

Every prior finding remains mandatory until the fresh certifier classifies it:

```text
closed | still-open | superseded-by-explicit-authority-change
```

Candidate mutation alone never clears a prior finding.

For Attempt 2 or later, require the certifier's saturation witness to include:

```text
Prior-attempt findings: <n>
closed: <n>
still-open: <n>
superseded-by-explicit-authority-change: <n>
Reused prior dispositions with unresolved invalidation: 0
```

A PASS requires `still-open: 0`. A FAIL must carry forward all `still-open` prior findings plus every newly discovered independently actionable finding.

The compact verification checkpoint for a saturated FAIL must preserve enough of the returned `Cumulative Spec Retry State` to recover unchanged semantic construction after total session/context loss. Counts alone are insufficient when safe reuse depends on stable manifest/domain/member identities or proof dependencies.

> **Fresh builder, fresh certifier, fresh verdict; cumulative integrated evidence and adversarial knowledge.**

## Bounded Execution, Mutation, and Durable Evidence Reuse

This section is authoritative for execution order, repository mutation, and evidence recovery. It supersedes later wording that can be read as authorizing broad repository rediscovery before the candidate is stable.

`$verify-spec` is a **bounded integration verification-and-repair workflow for one exact Spec candidate**, not a general repository audit or cleanup campaign. Spend work only on evidence that can change whether the active Spec candidate deserves PASS.

### Execution order

Follow these phases sequentially:

1. **Minimal preflight** — resolve the Spec, fixed baseline, Spec branch, exact current HEAD, clean/dirty state, direct native blockers/prerequisites, durable governance classification, current Ticket Coverage Manifest, and current remediation/closure state. Do not begin repository-wide audits here.
2. **Repair-capable deterministic/delegated gates** — build the working Verification Scope Manifest from the Spec body, durable coverage state, change provenance, and directly affected consumers. Run applicable Python quality checks, acceptance tests, global deduplication, architecture invariants, and other explicitly applicable gates. Repair only failures authorized below.
3. **Candidate stabilization** — rerun every invalidated gate after repair, commit/push verification-owned mutations through the normal branch workflow, and require one clean stable exact HEAD.
4. **Fresh final contract build** — only after the repair-capable candidate is stable, dispatch one genuinely fresh `$spec-contract` builder for the exact final HEAD and wait for its terminal result. Do not run broad parent-side exploration in parallel with the builder.
5. **Fresh semantic certification** — dispatch one fresh non-mutating `$verify-spec-closure` certifier against that exact final HEAD and exact final contract handoff.
6. **Finalization** — persist the receipt only if all exact-HEAD bindings still match.

Do **not** launch the fresh certification/finalization contract build before repair-capable gates merely to get an early handoff. An early exploratory build may be used only when an exact unresolved scope question cannot be answered from durable Spec/coverage authority; it is disposable and never substitutes for the mandatory final stable-HEAD build.

Any repository mutation after the final contract build invalidates that handoff for certification. Return to candidate stabilization, rerun invalidated gates, and perform a new fresh final build.

### Parent mutation authority

`$verify-spec` itself is intentionally mutating when repair is warranted. Read-only behavior applies to the fresh `$verify-spec-closure` certifier, not to the parent workflow.

The parent must repair a required-gate failure when it is either:

* `spec-relevant` under **Failure causality and repair authority**; or
* explicitly repairable under an applicable delegated repository-wide gate such as architecture or deduplication.

Repairs may touch unchanged/non-Spec files when the leanest correct fix must consume or establish an existing shared owner across a boundary. Path ownership does not override causal repair authority.

After every repair:

* rerun all checks invalidated by that repair;
* preserve the original failure/disposition evidence;
* require a clean worktree and one exact candidate HEAD before final contract construction;
* treat all earlier exact-HEAD semantic certification as stale.

### Outstanding-owner blockers do not end repair-capable verification

Discovering a valid blocker owned by another workflow does **not** by itself terminate `$verify-spec`.

When a decomposition, manifest, architecture-authority, tracker, or other upstream defect prevents final certification:

1. persist/route that blocker through its owning durable workflow record immediately;
2. mark only the proofs/gates that actually depend on the unresolved authority as blocked;
3. continue every independently actionable verification-owned repair whose correctness does not require inventing or assuming the unresolved authority;
4. finish applicable delegated repair-capable gates such as `$deduplicate-code`, `$verify-architecture`, and bounded `$wiki-sync` work when their repair authority is independently established;
5. rerun evidence invalidated by those repairs;
6. stop at the required Human Handoff only when the upstream blocker is the remaining reason this invocation cannot legally reach certification, or when another genuine Human Handoff / Hard Blocker independently applies.

Do not use an upstream manifest/decomposition defect as a reason to leave candidate-introduced duplication, stale wiki realization, or another independently owned repair known-but-unfixed.

This continuation rule does not authorize guessing semantics from the defective manifest. Any repair whose correct behavior depends on the unresolved authority remains blocked.

### Durable evidence reuse

Reuse durable lifecycle records instead of reconstructing already-closed work from scratch.

Prefer, in order:

* the parent Spec `Ticket Coverage Manifest` and Architecture/Design Obligation mappings;
* passing ticket/spec closure checkpoints and receipts bound to exact candidate identities;
* Finding Continuity and Decomposition Defect records;
* native issue state/parent/dependency metadata;
* current Workspace Metadata / explicit governance classification.

For a closed implementation/remediation ticket, normally validate only the ticket identity/state, required parent/dependency relation, closure-record identity, and exact persisted commit/candidate binding. Do **not** reread every ticket body, every ticket comment, or reconstruct the ticket's full proof unless a durable record is missing, stale, internally inconsistent, or the integrated certifier needs an exact unresolved acceptance detail.

Closed ticket certification is evidence input, not a substitute for integrated Spec certification. `$verify-spec-closure` still proves composition and entailment against the exact final Spec HEAD; it should consume concise closure evidence pointers rather than force the parent to reproduce each ticket investigation.

### Governance discovery bound

Resolve governance from durable local lifecycle evidence first.

* If current Workspace Metadata or another authoritative current Spec record explicitly classifies the Spec as `Independent`, and no current `wayfinder-source`, `wayfinder-remediation`, native parent, or conflicting governance marker invalidates that classification, accept it. Do not enumerate every Wayfinder or scan unrelated Wayfinder comment histories merely to prove absence.
* Enumerate/reconcile governing Wayfinders only when the Spec is positively Wayfinder-managed or durable governance evidence is missing, stale, or conflicting.

### Wiki applicability bound

Living Entity Wiki verification is applicable only when the active Spec changes wiki knowledge/source authority, changes a source that the current wiki is required to synchronize, or carries an explicit wiki obligation under the routing rules.

Do not run a repository-wide wiki audit merely to discover whether wiki routing applies. Determine applicability from the Spec/change-impact universe and durable routing authority first. Incidental baseline-identical wiki drift observed by another check is `non-spec` for this invocation unless the active Spec causally owns it.

### Runtime qualification applicability bound

Cross-runtime or interpreter qualification is **not** implied merely because the repository supports multiple runtimes, free-threaded Python, or runtime qualification tooling.

Run a runtime matrix only when at least one of the following is true:

* the active Spec contract explicitly requires behavior across those runtimes/interpreter modes;
* the candidate changes runtime policy, runtime selection/configuration, concurrency/runtime infrastructure, or code whose acceptance claim materially depends on interpreter/runtime variation; or
* another authoritative gate contract explicitly requires that exact runtime matrix for this candidate.

When applicable, run only the smallest authoritative matrix that proves the active claim. Reuse an already-installed qualifying runtime/environment when possible. Do not install additional interpreters or construct extra environments merely because they are available or potentially interesting.

If cross-runtime qualification is not applicable, record it as excluded in the Verification Scope Manifest with the exact authority/reason; do not silently omit it and do not execute it speculatively.

### Resumability and execution-budget bound

Do not start a new broad evidence domain, fresh builder/certifier, runtime installation, or repository-wide delegated gate when the execution environment has signaled that the remaining context/usage budget is unlikely to carry that phase through its required terminal result.

This is not permission to stop for ordinary partial progress. Continue normally while the authorized lifecycle can still complete. But an actual platform usage/context limit that prevents safe completion is a Hard Blocker and must preserve a durable recovery point instead of consuming the remainder of the invocation on work that cannot reach a legal terminal state.

Before an unavoidable limit is reached:

1. finish the current atomic mutation/check when safe;
2. do not begin another unrelated discovery or repair domain;
3. persist/reuse the compact verification checkpoint supported by this workflow, bound to exact baseline/branch/HEAD and current gate/repair state;
4. record completed gates, outstanding gates, observed-failure dispositions, verification-owned repairs, whether a fresh final contract build is still required, and whether semantic certification has started;
5. on resumption, consume that checkpoint plus durable lifecycle evidence and continue from the first invalidated/uncompleted phase rather than reconstructing completed work.

A checkpoint created because the execution environment is exhausted is **not PASS** and is not a semantic receipt. It exists only to prevent repeated repository archaeology and repeated deterministic work after a real external limit interruption.

### Evidence-driven expansion

Broad discovery is a fallback for unresolved evidence, not the default proof strategy. In particular, do not by default:

* fetch every closed ticket body/comment history when durable closure records already bind the implementation;
* enumerate every Wayfinder to reconfirm an explicit Independent classification;
* reconstruct accepted architecture prose already represented by exact current architecture authority/manifest mappings;
* audit unrelated artifact classes solely because a tool exists for them.

Expand only the unresolved evidence domain, record why expansion was required, and return to the bounded phase sequence above.

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

Deduplication detection remains **whole-repository** whenever this gate is applicable. Duplication is relational: new Spec code can duplicate unchanged code anywhere else in the repository, so changed-file or Spec-only scanning is forbidden.

Invoke `$deduplicate-code` in its `spec-differential` integration mode with the fixed `BASELINE_COMMIT` and exact candidate HEAD.

The child must scan the normal configured repository scope globally for both Arid and JSCPD, then classify candidate findings against the fixed Spec baseline as exactly one of:

```text
candidate-introduced
candidate-expanded
baseline-identical
unresolved
```

Rules:

* `candidate-introduced` includes a new duplicate relation between changed/new Spec code and unchanged code elsewhere in the repository. Cross-boundary duplication is still candidate-caused.
* `candidate-expanded` means pre-existing duplicate debt gained a new occurrence, larger matching region, new semantic coupling, or newly invalid suppression because of the candidate.
* `baseline-identical` means the same duplicate relation and material occurrence set existed at the fixed baseline and was not expanded or made newly actionable by the candidate. It is durable inherited debt for this Spec invocation, not opportunistic cleanup authority.
* `unresolved` blocks PASS.

Candidate-introduced and candidate-expanded findings must be consolidated or narrowly/justifiably suppressed under `$deduplicate-code` rules. The correct repair may touch unchanged or otherwise non-Spec files when that is necessary to consume or establish the real shared owner.

Baseline-identical findings remain visible in the dedup evidence summary but do not enter the `$verify-spec` repair loop merely to make historical repository debt disappear. Do not semantically re-investigate every baseline-identical group once machine correlation has established unchanged identity unless the candidate changes detector configuration, suppression state, or another fact that invalidates the comparison.

The final Spec dedup gate requires:

```text
candidate-introduced findings: 0
candidate-expanded findings: 0
unresolved causality: 0
stale/newly-invalid suppressions attributable to candidate: 0
scanner operational/source-processing errors: 0
```

This changes **repair attribution**, not scan scope. Both scanners still run globally after every dedup repair. Repository-wide deduplication repair does not broaden Ruff, Mypy, Pytest, acceptance-test, or unrelated cleanup authority.

If deduplication mutates the repository, treat those mutations as verification-owned changes for branch/candidate/commit handling. Any prior exact-HEAD semantic certification or final contract handoff becomes stale.


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
5. retain that exact handoff together with the `CONTRACT_HANDOFF_DIGEST` returned by the same build and treat the pair as the immutable semantic-certification candidate.

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
   * deterministic `$spec-contract` handoff/manifest, deterministic structural identity rows, and hashes;
   * the invocation-local `CONTRACT_HANDOFF_DIGEST` for those exact handoff bytes;
   * change-provenance and Verification Scope Manifest state;
   * the current parent-Spec `Ticket Coverage Manifest`, including the Architecture/Design Obligation Disposition Manifest and exact ticket `Architecture obligations` mappings;
   * applicable current architecture authority/context;
   * native deterministic/delegated gate results;
   * acceptance-test/preflight evidence;
   * observed-failure disposition state;
   * concise evidence pointers collected by the parent;
4. require that subagent to execute `$verify-spec-closure` as a non-mutating leaf;
5. receive one complete `SPEC CLOSURE: PASS | FAIL` or one explicit invalid/incomplete certification result and require every consumable verdict to echo the exact same `CONTRACT_HANDOFF_DIGEST`;
6. re-read exact HEAD/worktree and mutable contract-critical state needed to establish the verifier did not mutate the candidate;
7. mechanically validate the returned saturation witness below before consuming PASS or FAIL;
8. consume a complete verdict without semantic override.

While dispatcher-only, the parent must not perform a parallel semantic proof, search for evidence to overturn the verifier, mutate the candidate, repair findings, or dispatch shadow certifiers/reviewers.

A verifier-integrity failure, handoff-digest mismatch, or incomplete saturation witness invalidates the attempt and must be resolved before certification can continue.

## Architecture / Design Decomposition Integrity

`$verify-spec` is the integrated decomposition backstop.

### Spec Contract Coherence Gate

Before trusting Ticket Coverage Manifest routing, dispatching the semantic certifier, or persisting a passing Spec Verification Receipt, mechanically reconcile the fresh current contract with the parent Spec's current Ticket Coverage Manifest.

Require:

```text
Spec Body Hash equal: yes
Spec Contract Hash equal: yes
```

The TCM must persist both identity fields explicitly: `Spec Body Hash` and `Spec Contract Hash`. A different hash is never made coherent by equal manifest counts, equal cell-ID sets, equal ticket mappings, or apparently equivalent display prose.

If this gate fails, **no Spec Verification Receipt is legal**. Continue independently actionable verification-owned repair that does not depend on the conflict, but route the contract-identity defect to the current `$to-tickets` decomposition owner. When current contract cells/routing are otherwise unchanged, `$to-tickets` may perform its deterministic current-contract reconciliation; otherwise ordinary decomposition remediation applies. After reconciliation, obtain a fresh exact-HEAD contract build and semantic certification before finalization.

Recover the exact current `$spec-contract` manifest and the parent Spec's current `Ticket Coverage Manifest`. For a conventional fresh-Spec decomposition, mechanically compare the Spec-cell ID sets before trusting any routing row:

```text
source Spec-cell IDs = exact IDs from the current bound $spec-contract manifest
TCM Spec-cell IDs = exact Spec-cell IDs in the Ticket Coverage Manifest

missing source-derived cells = source - TCM
extra/non-source-derived cells = TCM - source
```

Require both differences to be empty and the counts equal. A TCM containing every real source cell plus one synthetic cell is a decomposition defect even when all implementation tickets are closed and semantically valid.

A Spec-cell identity mismatch blocks certification and routes to the current `$to-tickets` decomposition owner, but it does **not** terminate independently actionable repair-capable verification under **Outstanding-owner blockers do not end repair-capable verification**.

Then recover the complete Architecture/Design Obligation Disposition Manifest and the exact `Architecture obligations` IDs on all relevant implementation/remediation tickets.

Before semantic PASS, independently validate the bounded governing architecture/design sources for the completed Spec against that manifest and ticket routing. The manifest is reused as accounting state; it is not trusted as proof of its own completeness.

Require:

```text
Material architecture/design obligations: <n>
Manifest disposition rows: <n>
Missing obligations: 0
Ambiguous obligations: 0
Misrouted obligations: 0
Implementation obligations without durable ticket coverage: 0
Ticket architecture mappings inconsistent with manifest: 0
```

Pass the exact manifest/ticket mappings and governing source pointers to the fresh `$verify-spec-closure` certifier so that leaf independently challenges the same decomposition boundary.

If either the parent or fresh certifier establishes a decomposition defect, no Spec Verification Receipt is legal. Do not create ticket scope or repair implementation locally against an incomplete decomposition.

The `$verify-spec` parent must:

1. preserve the complete semantic FAIL;
2. resolve the current decomposition owner: active conventional Spec Review if one currently owns remediation, otherwise the parent Spec;
3. create/update that owner's single `<!-- decomposition-defects:v1 -->` record with stable unresolved `DD-*` entries and exact source/manifest/ticket provenance;
4. read the record back exactly;
5. register the required Human Handoff to the current decomposition owner, but do not terminate while independently actionable verification-owned repair remains;
6. after those independent repairs/gates are exhausted, stop at Human Handoff if the decomposition defect still prevents certification:

```text
$to-tickets - <Current Decomposition Owner Title> (<Current Decomposition Owner URL>)
```

Use the parent Spec title/URL when the parent Spec is the current decomposition owner, or the conventional Spec Review title/URL when that Spec Review owns remediation. The handoff blocks certification, not unrelated repair-capable verification work.

Historical ticket certification remains provenance and does not suppress the missing upstream obligation.

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
3. classify whether each finding is Spec-relevant repair, architecture/design decomposition defect, unresolved architecture, external/environmental blocker, or another deterministic contract defect requiring the owning workflow;
4. route every architecture/design decomposition defect to the current `$to-tickets` source owner through the canonical `decomposition-defects:v1` record; repair every other actionable Spec-relevant finding through the normal procedure and required owner skills;
5. if a routed decomposition/authority finding remains unresolved, continue every independent repair-capable gate/finding whose correctness does not depend on that unresolved authority; do not stop merely because the final receipt is already blocked;
6. rerun only invalidated gates/tests/failure dispositions;
7. refresh exact-HEAD `$spec-contract` bindings when the governing contract is valid enough to do so;
8. obtain another fresh semantic certification for the new stable candidate only after all upstream blockers required for certification are resolved.

Do not drop a prior semantic failure merely because a narrower rerun passes. It remains current until the exact falsifier/claim is re-proven or explicitly superseded by authoritative contract change.

If a finding requires a new durable architecture decision, halt at a Human Handoff to the durable architecture-remediation source established by this workflow:

```text
$architecture-remediation - <Architecture Remediation Source Title> (<Source URL>)
```

Present the blocker set separately from the invocation line. The certifier does not invent the decision.

## PASS Consumption

Accept `SPEC CLOSURE: PASS` only when:

* Spec/baseline/branch/HEAD/body hash/contract encoding/contract hash match dispatch exactly;
* returned `CONTRACT_HANDOFF_DIGEST` matches the exact digest supplied at dispatch;
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

Finalization must consume the same exact `CONTRACT_HANDOFF` bytes and `CONTRACT_HANDOFF_DIGEST` that the certifier saw. Do not rerun `$spec-contract` merely to finalize after PASS. If the handoff/digest pair is lost or changed, rebuild through `$spec-contract` and obtain fresh semantic certification before finalization.

The receipt should identify the semantic certification owner/result concisely, for example in a gate/evidence line:

```text
Independent semantic closure: PASS — $verify-spec-closure at exact HEAD <sha>; manifest <n>; violated 0; unproven 0; unchecked 0; domain construction <n>/<n> complete; remaining authoritative members 0; open nested domains 0
```

Do not serialize private reasoning transcripts.

## Exact-HEAD Invalidation

Any repair or mutation that changes candidate-semantic repository state invalidates prior semantic certification. A branch-tip advance proven to satisfy **Semantic Candidate Anchor and Policy-Only Synchronization** does not invalidate the semantic anchor merely because the Git SHA changed.

A mutable architecture/tracker authority change that affects a certified cell also invalidates that cell/certification.

Any candidate mutation that invalidates semantic certification also invalidates the current contract handoff/digest pair. Rebuild through `$spec-contract` and recertify; do not carry an old digest onto new bytes.

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
- exact handoff-byte digest validation for finalization;
- independent reproduction of `SPEC_CONTRACT_HASH` from deterministic structural identity rows;
- compact finalization validation;
- complete manifest-to-proof coverage validation;
- one canonical per-receipt Verification Hash;
- compact human-readable receipt rendering and producer→`$review-spec` manifest round-trip validation.

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
- `CONTRACT_HANDOFF_DIGEST` for the exact handoff bytes from this build;
- deterministic `contract_identity` rows embedded in `CONTRACT_HANDOFF`;
- ordered manifest;
- source counts/integrity counts;
- ownership classifications;
- immutable default branch/head.

`$spec-contract` owns serialization of the finalizer-facing contract handoff while the canonical manifest is already in context. Do not independently recreate, pretty-print, copy, or re-key the manifest/source-count/identity payload later in this workflow.

Retain the exact `CONTRACT_HANDOFF` file and `CONTRACT_HANDOFF_DIGEST` as one pair. If either is lost, rebuild through `$spec-contract`; do not reconstruct them from a prior receipt, independent Spec parsing, or conversational state.

Immediately after the final stable-HEAD build, execute the deterministic coherence gate before semantic certifier dispatch:

```bash
CONTRACT_COHERENCE=$(mktemp)

python "$ARTIFACT_TOOL" contract-coherence \
  --comments-summary "$SPEC_COMMENTS_SUMMARY" \
  --contract-input "$CONTRACT_HANDOFF" \
  > "$CONTRACT_COHERENCE"

test "$(jq -r .status "$CONTRACT_COHERENCE")" = "PASS"
```

Any nonzero exit or non-PASS result is a contract-identity blocker owned by the decomposition lifecycle. Do not dispatch `$verify-spec-closure` while it remains.

Do not independently refresh or reinterpret default-branch ownership.

Capture Architecture Impact. Unresolved material architecture blocks verification and routes to `$architecture-remediation`.

Resolve whether the Spec is Wayfinder-managed from durable current governance evidence before performing discovery. An explicit current `Independent` classification is sufficient unless contradicted by a current governance marker or native relationship; absence of a contradiction does not require an all-Wayfinder scan.

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

Invoke the `$wiki-lint` skill only after the bounded Wiki applicability rule above proves Living Entity Wiki routing applies; do not run a whole-wiki discovery audit merely to decide applicability. Invoke the `$deduplicate-code` skill only when Spec-owned/Mixed work creates a real duplicate-implementation risk; when invoked, use its `spec-differential` integration mode and keep both Arid and JSCPD whole-repository scans visible.

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

1. retain the **same exact** `CONTRACT_HANDOFF` and `CONTRACT_HANDOFF_DIGEST` supplied to and echoed by the certifier; do not rerun `$spec-contract` merely for finalization. If the pair is lost or changed, rebuild through `$spec-contract` and obtain fresh semantic certification before finalization;
2. require valid body/contract and reconciled ownership from that certified handoff;
3. require every applicable gate PASS or NOT APPLICABLE;
4. require Delegated Gate Ownership closure complete;
5. require Observed Failure Disposition closure complete;
6. require the certifier coverage to map every manifest cell to `proven` or valid originating-Spec `not-applicable` with `violated=0`, `unproven=0`, and `unchecked=0`, and require the Certifier Saturation Witness to remain complete with zero remaining authoritative members, ambiguous membership, or unexplored authoritative siblings;
7. re-fetch the parent Spec comments, rebuild `SPEC_COMMENTS_SUMMARY`, and rerun `contract-coherence` against the **same certifier-bound** `CONTRACT_HANDOFF`; require PASS so tracker identity could not drift during certification;
8. require current hierarchy/dependency state valid;
9. require clean worktree.

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
  --contract-digest "$CONTRACT_HANDOFF_DIGEST" \
  --proofs-input "$PROOFS_INPUT" \
  --gates-input "$GATES_INPUT" \
  --mode <full|checkpoint> \
  --receipt-output "$RECEIPT_FILE" \
  [--prior-checkpoint <checkpoint>] \
  [--repair <repair>]... \
  [--inherited-finding <finding>]...
```

`finalize-parts` first requires the exact contract-input bytes to match the certifier-bound `CONTRACT_HANDOFF_DIGEST`, independently recomputes `SPEC_CONTRACT_HASH` from deterministic `contract_identity` rows, then assembles the already-owned proof/gate pieces, validates bindings/coverage/gates, rejects unresolved cells, computes one Verification Hash, renders the human-readable receipt, and requires the rendered manifest to round-trip exactly through the current `$review-spec` parser before writing the receipt file. The parent must already have rerun deterministic TCM/contract coherence against those same handoff bytes immediately before this operation. There is no model-authored wrapper, reconstructed manifest, separate packet admission, or second receipt renderer.

Direct `finalize` is not a valid lifecycle path.

## 9. Persist the Compact Receipt

The receipt is a checkpoint/binding record, not a transcript of semantic reasoning. It remains deliberately human-readable. It retains the manifest/source counts needed by `$review-spec`, compact derived coverage, gate outcomes, repairs, inherited findings, and one per-receipt Verification Hash. It omits proof prose, proof hashes, duplicate coverage structures, and commands already visible in the transcript.

`Verification Hash` is a checksum of this one finalized verification record and may differ across independent valid runs because human-readable evidence may differ. It is not cross-run contract identity and must never be compared as though it were `SPEC_CONTRACT_HASH`.

The receipt renderer owns Markdown-safe display encoding. Callers must never pre-escape receipt fields or reconstruct manifest display rows from a previous receipt.

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