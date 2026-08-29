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

A prior cell disposition may be inherited only through a previously **independently certified Proof Object** whose exact claims, predicate, falsifier, Domain Boundary, Nested Universe witness, assumptions, evidence-bearing state, and certification remain immutable and unaffected. A legacy receipt without independent proof certification cannot supply inheritable semantic cell proof under the current policy. Otherwise rebuild and recertify that proof fresh.

#### Proof-Policy Invalidation

Checkpoint invalidation includes changes to **proof semantics**, not only changes to the implementation or evidence-bearing surfaces.

Inspect the checkpoint→current delta for normative changes to this skill or to an invoked verification owner/helper whose contract governs the affected proof. If such a change alters what counts as sufficient evidence, required proof domain, gate applicability, cell disposition, verifier integrity, or another rule that could change whether prior evidence proves the claim, that prior proof is non-inheritable and must be re-evaluated under the current policy.

A change to universal cell-proof semantics or to the meaning/requirements of `proven` invalidates inherited per-cell proof for the entire manifest; re-prove every manifest cell fresh even when the implementation is unchanged. If a proof-policy change is material but its affected proof set cannot be bounded confidently, fall back to full verification from the fixed baseline.

Presentation-only wording, formatting, or other policy edits that cannot alter proof validity do not invalidate prior proof merely because a verification-policy file changed.

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

### Semantic-First Verification Order

Verification separates **candidate proof work** from **final broad gates** so semantic defects are discovered before repeatedly paying for expensive whole-Spec checks. This changes execution order only; it does not weaken any required gate or final exact-HEAD condition.

#### Candidate Proof Tier

Before semantic proof certification converges, run only the checks needed to construct trustworthy Proof Objects, expose likely counterexamples, and validate a narrow verification-owned repair:

* direct source/runtime/tracker/document inspection required by a manifest predicate;
* targeted tests that are direct evidence for a Proof Object;
* the mandatory service preflight only when a selected candidate-tier test requires that service;
* narrow static/reference checks that directly establish a predicate, nested universe, or repair;
* architecture/wiki checks when they are themselves required semantic evidence.

Do **not** run broad formatter/linter/type-check suites, the complete selected regression pytest scope, or other expensive final gates merely to establish readiness for the first proof certifier unless that exact gate is itself direct evidence for a Proof Object.

When a certifier rejects or leaves a Proof Object unresolved and verification repairs repository state, rerun only the affected candidate-tier checks needed to establish the repair and rebuild affected proof. Do not rerun the complete final gate set between semantic repair iterations.

Semantic proof has **converged** when every current Proof Object is independently certified for the candidate state and there are no rejected, unresolved, stale, or uncertified Proof Objects.

#### Final Gate Tier

After semantic proof convergence, run every applicable final verification gate required by Sections 4 and 5 against the stable candidate `HEAD`. A required final gate that was already executed at that same exact `HEAD`, after the last repository mutation, with its complete final scope may be reused; do not rerun it solely because it was also useful during candidate proof.

If a final-gate failure requires repository mutation, repair narrowly, rerun the affected final gate(s), apply Proof Object invalidation from Section 6.5, and independently recertify only stale Proof Objects. Final PASS still requires every applicable gate and every Proof Object valid at the exact final `HEAD`.

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

## 6. Build and Independently Certify Spec Proof Objects

A manifest cell may not transition to `proven` or `not-applicable` solely from semantic state authored and certified by the parent verifier. The parent constructs candidate proof; a genuinely fresh non-mutating proof certifier determines whether that proof actually establishes the cell.

This is intentionally narrower than `$review-spec`. Proof certification checks whether the current verification evidence entails the already-authoritative Spec Contract claims. It does not perform open-ended product review, create Root Blockers, or replace later independent review.

### 6.1 Build the Cell-to-Proof Map

Maintain exactly one working coverage row for every manifest cell:

```text
Cell: <ID>
Claim: <authoritative manifest requirement>
Proof Object: <P-<n>>
State: <pending-certification | proven | not-applicable | unresolved>
```

Before certification:

* every manifest ID appears exactly once;
* no unknown manifest ID exists;
* every cell maps to exactly one proof object;
* every proof object is referenced by at least one cell;
* `proven` and `not-applicable` are illegal states; use `pending-certification` until independent certification returns.

### 6.2 Construct Proof Objects

A **Proof Object** is the smallest reusable semantic proof that genuinely establishes one or more manifest cells.

```text
Proof: P-<n>
Cells: <manifest IDs>
Claims: <exact assigned manifest claims>
Predicate: <normalized proposition sufficient for every assigned claim>
Falsifier: <concrete current state that would make any assigned claim false>
Domain Boundary: <authoritative semantic boundary>
Nested Universe: <explicit members/dispositions | equivalent exhaustive mechanism | not-applicable-with-reason>
Evidence: <direct current evidence>
Assumptions: <None | material assumption + authority/direct proof>
Invalidation Boundary: <complete repository paths/patterns and durable evidence surfaces whose change could invalidate this proof>
Evidence Stability: <repository-immutable | mutable>
Proof Object Hash: <sha256 of canonical semantic proof object excluding this hash>
```

Rules:

* Group cells only when one proof object actually establishes every mapped claim. Shared files, tests, terminology, or convenient evidence reuse are not sufficient reasons to group claims.
* `Predicate` must preserve every material clause, quantifier, condition, exception, and surface from every mapped claim. A broader-sounding summary that drops a clause is invalid.
* `Falsifier` must be a real logical counterexample to the mapped predicate, not merely a known historical bug pattern.
* Evidence must address the proof object's subject and predicate directly. Nearby repository health is supporting evidence only.
* `Invalidation Boundary` must include every direct and transitive repository/durable-evidence surface whose mutation could make the certified predicate false while the proof object's own wording remained unchanged. Use deterministic path/pattern semantics; vague labels such as `related code` are invalid.
* `Evidence Stability: repository-immutable` is allowed only when every material evidence fact needed for certification is recoverable from immutable repository state bound by the object. Tracker/runtime/service/time-dependent evidence is `mutable` unless an authoritative immutable snapshot makes it otherwise.
* The parent may propose evidence, domain witnesses, invalidation boundaries, and stability, but it does **not** assign semantic sufficiency, survivability, or the final cell disposition. The fresh certifier validates those proposed boundaries too.

#### Nested Universe Closure

Outer manifest completeness does not prove completeness inside a quantified claim.

When a proof predicate quantifies over a finite or discoverable domain — for example `all`, `every`, `no`, `none`, `only`, `complete`, `repository-wide`, a named surface set, or equivalent closure language — the proof object must include a **Nested Universe** witness.

A Nested Universe witness must use one of these forms:

1. **explicit enumeration** — identify the authoritative boundary, enumerate every current member, and disposition every member against the predicate; for a large deterministic set, a reproducible generation method plus canonical member count and member-set digest may stand in for printing every member when the certifier independently recomputes and validates that exact set; or
2. **equivalent exhaustive mechanism** — identify a deterministic/queryable mechanism whose semantics cover the full authoritative boundary and record the complete result needed to exclude the falsifier.

`searched relevant files`, a changed-file list, a known-bad-pattern grep, targeted tests, or examples are not exhaustive mechanisms unless the claim's authoritative domain is explicitly limited to exactly that set.

For an open-world predicate, define the strongest authoritative boundary available and the unresolved remainder. If the falsifier cannot be excluded over the claim's actual domain, the proof object cannot certify `proven`.

A claim may use `Nested Universe: not-applicable` only when it has no material exhaustive/domain-closure predicate; record the reason.

### 6.3 Render and Validate the Proof Packet

Before any proof-certifier dispatch, render the complete candidate proof packet to a temporary structured file. JSON is preferred.

The packet must bind:

```text
Spec issue
Verified candidate HEAD
BASELINE_COMMIT
SPEC_BODY_HASH
SPEC_CONTRACT_HASH
Complete ordered manifest IDs and claims
Complete cell-to-proof map
Complete proof objects
```

Do **not** include:

* a parent-authored `proven`/`not-applicable` conclusion;
* expected certification results;
* prior Spec Review findings or Root Blocker history;
* language telling the certifier which objects are believed to pass.

Pre-validate the packet deterministically before dispatch. Require:

```text
Manifest cells == cell-to-proof rows
Missing manifest cells: 0
Unknown manifest cells: 0
Duplicate cell mappings: 0
Unreferenced proof objects: 0
Missing proof-object required fields: 0
```

Compute each object's semantic identity before the packet hash:

```text
PROOF_OBJECT_HASH[P-<n>] = sha256(canonical proof object bytes excluding Proof Object Hash)
PROOF_PACKET_HASH = sha256(canonical proof packet bytes)
```

`PROOF_PACKET_HASH` binds the complete candidate packet to its exact global state. `PROOF_OBJECT_HASH` is the reusable semantic identity for one proof object. A packet hash change does **not** by itself invalidate an unchanged already-certified Proof Object; Section 6.5 determines whether that certification survives the actual delta.

If a Proof Object's hash changes, that object requires a **new fresh proof certifier**. Do not ask the certifier that rejected or evaluated the prior version of that object's lineage to approve the revised version. Unchanged objects are not recertified merely because another object or the packet-level `HEAD` binding changed.

### 6.4 Independent Proof Certification Integrity

Semantic proof certification is an independent verification role, not parent self-certification.

A **fresh proof certifier** means a genuinely separate agent/subagent context that:

* did not participate in implementation, parent verification, proof-object construction, or prior certification for any assigned Proof Object lineage in the current invocation;
* receives the authoritative global bindings plus only the assigned manifest claims, assigned Proof Objects, and evidence references needed to inspect those objects at the exact candidate `HEAD`; unrelated Proof Objects are omitted;
* is non-mutating;
* may not delegate or spawn another certifier;
* does not receive prior Spec Review findings, Root Blocker history, the parent's intended verdict, or prior certifier conclusions for the objects it is asked to certify.

Generate a deterministic **certification slice** for the currently stale/uncertified Proof Objects. Bind the slice to the Spec issue, exact candidate `HEAD`, `SPEC_CONTRACT_HASH`, assigned manifest claims, assigned `PROOF_OBJECT_HASH` values, and only their required evidence references. Compute `CERTIFICATION_SLICE_HASH`.

Default to one fresh proof certifier for all currently stale/uncertified objects when that slice is bounded. If context limits or unrelated evidence domains make partitioning materially cheaper, partition deterministically and assign each stale object to exactly one fresh certifier. Never resend already-valid retained Proof Objects merely to make the slice complete, and do not create overlapping certifiers merely to vote on the same proof.

If the execution environment cannot create the required genuinely fresh context, fail closed before receipt persistence:

```text
VERIFICATION PROOF CERTIFICATION: INDEPENDENCE UNAVAILABLE
Status: verification incomplete
Required: genuinely fresh non-mutating proof certifier
```

There is **no same-agent or owner override** for semantic proof certification. Such an override would recreate the self-certifying transition this gate exists to prevent.

For every assigned proof object, the certifier independently verifies:

1. every mapped manifest claim is represented by the proposed Predicate without dropped material clauses;
2. the proposed Falsifier is a valid counterexample to that predicate;
3. the Domain Boundary is authoritative and not silently narrowed;
4. every required Nested Universe witness is complete, or its claimed exhaustive mechanism really covers the full domain;
5. direct current evidence establishes the predicate rather than merely nearby health;
6. all material assumptions are authoritative or directly proven;
7. after independent inspection of current `HEAD`, no counterexample survives;
8. the proposed Invalidation Boundary is complete enough to capture direct and transitive repository/durable-evidence mutations that could invalidate the proof;
9. the proposed Evidence Stability classification is correct.

The certifier returns exactly one result per proof object:

```text
Proof: P-<n>
Proof Object Hash: <PROOF_OBJECT_HASH>
Certified HEAD: <exact candidate HEAD inspected>
Certification Slice Hash: <CERTIFICATION_SLICE_HASH>
Certification: <certified | rejected | unresolved>
Disposition: <proven | not-applicable | unresolved>
Certification Evidence: <concise direct evidence / counterexample / insufficiency>
```

Rules:

* `certified + proven` means the evidence excludes the falsifier over the required domain.
* `certified + not-applicable` requires the certifier to establish the exact authoritative condition that makes every mapped claim inapplicable.
* `rejected` means the proposed proof is logically unsound, materially incomplete, or contradicted by a counterexample.
* `unresolved` means sufficiency cannot be established from current authority/evidence.
* The parent may not upgrade, reinterpret, suppress, or override a certifier's `rejected`/`unresolved` result.
* If one grouped proof object cannot yield one valid disposition for all mapped cells, certification rejects the grouping; split the proof object and recertify.

A real omitted originating-Spec obligation discovered during certification is a Spec Contract defect. Halt with `SPEC CONTRACT: INCOMPLETE`; do not silently expand the verified manifest.

### 6.5 Derive Coverage State from Certification

Only after complete certification may the parent derive manifest coverage:

```text
certified + proven         -> proven
certified + not-applicable -> not-applicable
rejected / unresolved      -> unresolved
missing certification      -> unresolved
```

The parent does not independently assign a stronger state.

#### Incremental Proof Object Invalidation

After any repository mutation, proof-packet revision, candidate `HEAD` change, or relevant evidence refresh, rebuild the current Proof Objects and compute a **Proof Certification Invalidation Matrix** before dispatching another certifier.

For every previously certified Proof Object record:

```text
Proof: <P-n>
Prior Proof Object Hash: <hash>
Current Proof Object Hash: <hash>
Certified HEAD: <sha>
Candidate HEAD: <sha>
Evidence Stability: <repository-immutable | mutable>
Repository delta: <complete changed-path set/digest from Certified HEAD..Candidate HEAD>
Invalidation Boundary intersection: <0 | nonzero | uncertain>
Proof-policy impact: <none | invalidating | uncertain>
Certification state: <retained-certified | stale>
Reason: <deterministic result>
```

A certification may become `retained-certified` only when **all** of these are true:

1. current `PROOF_OBJECT_HASH` exactly equals the certified hash;
2. mapped manifest claims and `SPEC_CONTRACT_HASH` are unchanged for that object;
3. current proof policy does not invalidate that object's certification;
4. `Evidence Stability` is `repository-immutable`;
5. the complete repository changed-path set from `Certified HEAD..Candidate HEAD` has deterministic zero intersection with the certifier-approved Invalidation Boundary;
6. no changed surface has an uncertain transitive relationship to that boundary.

Otherwise the object is `stale` and returns to `pending-certification`. `Evidence Stability: mutable` fails closed to `stale` whenever the candidate state advances or the relevant external evidence could have changed. If delta-to-boundary matching cannot be computed confidently, mark the object stale; never preserve certification by optimistic interpretation.

A global proof-policy change that alters semantic sufficiency, nested-universe requirements, certifier integrity, object hashing, invalidation semantics, or the meaning of `proven` invalidates every affected object; if impact cannot be bounded, invalidate all semantic certification.

Only stale/uncertified objects are sent to a **new fresh proof certifier**. Retained certifications remain valid without consuming another semantic-review context. This is proof-object-granular reuse, not same-agent self-certification: the original fresh certifier approved the semantic proof and its invalidation boundary; the parent performs only deterministic delta-to-boundary invalidation afterward.

If a final-gate repair later changes repository state, run this same matrix again and recertify only newly stale objects.

Checkpoint inheritance may reuse a prior certified proof object only when the durable receipt contains the same independently certified Proof Object hash, certifier-approved Invalidation Boundary/Evidence Stability, and enough exact-HEAD provenance to apply these same fail-closed invalidation rules across the checkpoint delta. Any uncertainty requires fresh proof construction/certification.

Before success reconcile:

```text
Manifest cells: <n>
Coverage rows: <n>
Proof objects: <n>
Proof packet hash: <PROOF_PACKET_HASH>
Certified proof objects: <n>
Freshly certified proof objects at candidate HEAD: <n>
Retained certified proof objects: <n>
Proof invalidation rows: <n>
Stale proof objects: 0
Rejected proof objects: 0
Unresolved proof objects: 0
Missing proof certifications: 0
Proven cells: <n>
Not applicable cells: <n>
Unresolved cells: 0
Missing rows: 0
Unknown rows: 0
```

A deterministic packet/receipt validator checks structural integrity. The fresh certifier supplies the semantic authorization. Neither substitutes for the other.

## 7. Failure Handling

For an ordinary failure:

1. determine whether it is:
   * a failed Spec contract obligation;
   * a Spec-owned repository-standard/tooling failure;
   * an inherited-only unrelated repository defect;
2. fix the narrowest authoritative point only for the first two categories;
3. rerun the narrow affected candidate-tier checks;
4. rebuild affected Proof Objects, apply the Proof Certification Invalidation Matrix, and recertify only stale objects;
5. continue semantic convergence without rerunning unaffected expensive final gates.

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

Use this order after any verification-owned semantic repair:

1. **Converge semantic proof first.**
   * recompute the fixed-baseline integration inventory and `$spec-contract` state required by the repair;
   * rebuild changed Proof Objects and their hashes;
   * apply the Proof Certification Invalidation Matrix;
   * run only affected candidate-tier evidence checks;
   * dispatch new fresh certifier(s) only for stale/uncertified objects;
   * repeat until rejected/unresolved/stale/uncertified Proof Objects are all zero at a stable candidate `HEAD`.
2. **Run the Final Gate Tier once semantic proof has converged.**
   * execute every applicable broad/non-semantic final gate not already valid at the same post-mutation `HEAD`;
   * preserve exact command/service evidence required by the final receipt.
3. **If a final gate requires another repository repair, invalidate narrowly.**
   * repair the narrowest authoritative point;
   * rerun the failed/affected final gate(s) and any required targeted checks;
   * rerun `$spec-contract`/ownership only when the mutation can affect them;
   * apply the Proof Certification Invalidation Matrix from each object's certified `HEAD` to the new candidate `HEAD`;
   * retain only deterministically unaffected repository-immutable certifications and use new fresh certifier(s) for stale objects.
4. **Establish the exact final state.**
   * rerun `$spec-contract` in `build` mode at final `HEAD`;
   * require the Spec body/contract to remain valid and reconcile any changed ownership;
   * in checkpoint mode, recompute checkpoint delta/invalidation, including **Proof-Policy Invalidation**;
   * render and deterministically validate the complete final proof packet and compute `PROOF_PACKET_HASH`;
   * require every Proof Object either freshly certified at final `HEAD` or retained through a complete valid invalidation row to final `HEAD`;
   * require stale/rejected/unresolved/missing proof certifications `0`, manifest `unresolved 0`, and every applicable final gate passed at the exact final `HEAD`.

Do not rerun a whole final suite simply because one semantic Proof Object changed when that suite was not affected. Conversely, token/runtime economy never permits retaining a certification or gate when impact is uncertain.

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
**Proof Packet Hash:** <PROOF_PACKET_HASH>
**Proof certification execution:** independent-subagent
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

### Spec Proof Objects
| Proof | Object Hash | Cells | Predicate | Falsifier | Domain / Nested Universe | Evidence / Assumptions | Invalidation Boundary | Evidence Stability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P-1 | <hash> | <IDs> | <predicate> | <falsifier> | <authoritative boundary + nested-universe witness> | <direct evidence + proven assumptions> | <certifier-approved boundary> | repository-immutable |

### Independent Proof Certification
| Proof | Object Hash | Certified HEAD | Slice Hash | Certification | Disposition | Certification Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| P-1 | <hash> | <sha> | <CERTIFICATION_SLICE_HASH> | certified | proven | <fresh certifier evidence> |

### Proof Certification Carry-Forward
| Proof | From HEAD | To HEAD | Repository Delta Digest | Boundary Intersection | Result |
| --- | --- | --- | --- | --- | --- |
| P-1 | <certified sha> | <final sha> | <digest> | 0 | retained-certified |

### Spec Contract Coverage
| Cell | State | Proof |
| --- | --- | --- |
| <ID> | proven | P-1 |

### Verification Gates
- <gate>: passed — <fresh evidence>
- <gate>: passed — inherited from checkpoint <SHA>; unaffected by complete invalidation analysis
- <gate>: not-applicable — <reason>

### Unrelated Inherited Findings
- <finding or None>
```

The receipt must contain the complete manifest, the complete durable Proof Object set with object hashes/invalidation boundaries/evidence stability, exactly one independent certification row per Proof Object, exactly one coverage row per manifest cell, and a carry-forward row for every object whose `Certified HEAD` differs from final `HEAD`. Freshly certified-at-final-HEAD objects do not need a carry-forward row. The durable Proof Object and provenance sections are the independently checkable semantic witness; do not replace them with a parent-authored summary such as `survivability excluded` or aggregate zero counts.

### Atomic Receipt Persistence

1. Render the **complete** receipt into `RECEIPT_FILE=$(mktemp)` before any GitHub mutation. Treat Markdown as data: use Python or `printf`; never use an unquoted heredoc. If a heredoc contains literal Markdown, quote its delimiter (`<<'EOF'`) and write dynamic values separately. Ensure the file ends with exactly one newline.
2. Pre-validate `RECEIPT_FILE` with one Python invocation. Require exact equality for Status, HEAD, baseline, branch, verification mode/checkpoint, body/contract hashes, `PROOF_PACKET_HASH`, proof-certification execution, default branch/head; require every required receipt section exactly once; require the three manifest-integrity zero lines; parse manifest and coverage IDs matching `(?:US|ID|TD|OOS|NORM)-<n>[.<suffix>]`; require both ordered ID lists to equal the final `$spec-contract` manifest exactly with no duplicates; require every coverage row to reference exactly one declared Proof Object; require every Proof Object to be referenced; require exactly one certification row per Proof Object with matching Object Hash, exact Certified HEAD, and non-empty Certification Slice Hash; require every certification to be `certified` with disposition equal to the derived coverage state for all mapped cells; for every certification whose `Certified HEAD` differs from final `HEAD`, require a complete carry-forward chain to final `HEAD`, recompute each repository delta and digest, require `Evidence Stability: repository-immutable`, require deterministic zero intersection with the certified Invalidation Boundary, and reject any chain containing an invalidating/uncertain proof-policy change; require no `stale`, `rejected`, `unresolved`, missing certification, or unknown Proof Object; reconstruct the canonical proof packet from the persisted receipt fields that bind it — exact HEAD/baseline/body/contract hashes, ordered manifest IDs and claims, cell-to-proof map, and complete Proof Object data — and require that hash to equal `PROOF_PACKET_HASH`. Do not substitute an improvised `grep`/`sed`/`awk`/regex pipeline.
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
* proof-object count/hash and independent proof-certification summary, including fresh-versus-retained certification counts;
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
