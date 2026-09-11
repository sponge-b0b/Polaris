---
name: review-spec
description: Review a verified completed Spec using the existing independent Standards, Spec, and Architecture axes, while preserving provenance when a finding contradicts earlier ticket or Spec certification.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

Review the **exact verified state** of a completed Spec along the applicable independent axes. This `SKILL.md` is the single authoritative procedure for `$review-spec`.

The preserved procedure below remains normative. The hardening sections immediately below strengthen frozen-finding provenance, semantic scope attribution, certified review-proof reuse, certified semantic-domain finality, and the human-facing aggregate format; where those rules conflict with older wording later in this file, the hardening rules win.

## Human-Facing Aggregate Format

The final user-facing review result MUST present the three review axes in this order and MUST always include both `Blocking` and `Advisory` subsections for every axis, even when a subsection has no findings:

```markdown
## Standards

### Blocking
- <findings or None>

### Advisory
- <findings or None>

## Spec

### Blocking
- <findings or None>

### Advisory
- <findings or None>

## Architecture

### Blocking
- <findings or None>

### Advisory
- <findings or None>
```

Use `None.` when a subsection has no findings so the presentation shape remains stable across review runs.

Keep findings under their originating axis and severity. Do not collapse Blocking and Advisory findings into one bullet list, and do not replace this human-facing projection with Root Blocker status, coverage accounting, reviewer-execution metrics, or convergence/effectiveness statistics.

The compact coverage/effectiveness output required below remains required, but it is supplemental and MUST appear after the three-axis findings projection.

Owner-overridden, scope-retired, Root Blocker, provenance, architecture-handoff, remediation, and lifecycle information remains governed by the procedure and may follow the three-axis findings as applicable.

## Reviewer Execution Budget

A normal `$review-spec` invocation may create exactly **one fresh semantic review sub-agent**. That one reviewer executes the applicable review axes sequentially in this fixed order:

1. Standards, when applicable;
2. Spec, always;
3. Architecture, when applicable.

Do not fan out Standards, Spec, and Architecture into separate reviewer agents. Do not automatically create additional challenger agents. Any second independent reviewer or challenger requires **explicit human authorization in the current invocation**.

The three review axes remain semantically independent even though one fresh reviewer executes them:

* freeze each axis's coverage, findings, and proof groups before starting the next axis;
* shared factual repository evidence may be reused across axes;
* another axis's disposition, finding, confidence, or absence of findings is never evidence for the current axis;
* each axis must independently satisfy its own authority, universe, Claim-Proof Integrity, coverage, and invalidation-boundary requirements.

Default execution accounting:

```text
Reviewer execution: single-fresh-subagent-three-axis-passes
Reviewer execution override: None
Automatic reviewer sub-agents: 1
Automatic challenger sub-agents: 0
Cross-axis contextual independence: reduced
Semantic axis independence: required
```

Token/model cost is an execution constraint, never permission to omit coverage, skip required proof, weaken Domain Finality Reconciliation, bypass Attention, or relax the Exit Gate.

## Preserve the Adversarial Boundary

`$review-spec` remains downstream of a passing independently certified `$verify-spec` result.

Do not:

* verify ordinary ticket closure here;
* rerun `$verify-ticket-closure` or `$verify-spec-closure` merely to confirm a review finding;
* repair upstream verifier policy during the review;
* weaken a current **in-domain** finding because an earlier verifier reported PASS.

Prior ticket/Spec certification is historical evidence about member correctness, but a certified semantic closure domain is durable membership authority under **Certified Semantic Domain Finality** below. A current reviewer may challenge behavior inside that domain; it may not silently redefine the domain under unchanged authority.

## Upstream Certification Provenance

After a Blocking finding has been frozen and axis-provenance validated, determine whether it contradicts a prior semantic certification.

For each such finding, recover only the bounded provenance needed to answer:

```text
Review finding
    ↓
Spec contract cell(s), when applicable
    ↓
originating Implementation Ticket(s), when recoverable
    ↓
latest ticket closure certification(s), when present
    ↓
exact Spec Verification Receipt / $verify-spec-closure certification reviewed
```

Use durable sources in this order where available:

1. the immutable review checkpoint / Spec Contract Manifest;
2. parent Spec `Ticket Coverage Manifest`;
3. ticket `Spec obligations` fields;
4. durable `implement-ticket` closure checkpoint/verdict;
5. exact Spec Verification Receipt reviewed.

Do not infer ticket provenance from filenames, commit authorship, or remembered implementation history when durable mapping exists.

### Compact provenance record

For a frozen finding, preserve a concise record:

```text
Upstream certification:
- Spec cells: <IDs | None>
- Originating tickets: <#IDs | Unknown/legacy mapping unavailable>
- Ticket certification: <TICKET CLOSURE PASS reference(s) | legacy self-certified closure | unavailable>
- Spec certification: <exact verified HEAD / receipt identity>
- Contradiction: <what earlier certified claim this finding falsifies>
```

This is process provenance, not a new review axis and not a reason to reject a valid in-domain finding.

For legacy tickets created before `Spec obligations` / Ticket Coverage Manifest existed, record `legacy mapping unavailable` rather than reconstructing uncertain lineage.

## Persistence Compatibility

Do not change deterministic review utility schemas solely for this provenance field unless the utility already supports it.

When the pending/exit renderer has no dedicated field, fold the compact upstream-certification record into the finding's existing evidence/provenance text without changing its semantic classification or inventing a parallel persistence format.

The review parent may perform this bounded provenance recovery after findings are frozen because it is root/process reconciliation, not semantic re-review of assigned cells.

## Postmortem Signal

A finding that disproves a valid independent ticket or Spec certification is evidence about the upstream certification process.

Preserve that fact, but do not mutate workflow skills during the active review. Workflow hardening remains a separate authorized repository change.

This provenance exists so later postmortems can trace:

```text
Spec obligation
→ ticket decomposition
→ ticket certification
→ Spec certification
→ review contradiction
```

without relying on conversational memory.

## Certified Semantic Domain Finality

This section is authoritative and supersedes later preserved wording that allows a full re-review, a `root-definition gap`, or convergence saturation to replace a previously certified semantic membership boundary merely because a later reviewer adopts a broader plausible interpretation of unchanged authority.

### What certification freezes

A prior semantic PASS does not make implementation behavior permanently correct. It may, however, establish a **Certified Closure Domain**: the independently certified authority identity, membership predicate, source sets/dimensions, and closure criterion that defined which candidates belonged to a material completion claim/root.

When the relevant ticket/root certification contains `<!-- certified-closure-domain:v1 -->`, use those records directly.

For historical certifications predating that marker, treat durable closure evidence as an equivalent frozen domain only when it contains enough state to recover without guesswork:

* exact governing authority;
* explicit membership predicate or equivalent bounded inclusion rule;
* authoritative dimensions/source sets or closure criterion;
* complete construction/disposition evidence;
* enough explicit boundary/out-of-domain evidence to distinguish excluded candidates from omitted in-domain members.

If that state cannot be recovered, no legacy finality claim exists. Do not invent one from memory, implementation shape, or current reviewer intuition.

### Full re-review does not erase frozen domains

Missing/malformed `review-spec-proof-reuse:v1` state may require a full current review. That resets clean-review proof reuse only.

It does **not** erase applicable Certified Closure Domains from prior semantic ticket/root completion.

Likewise, a repository mutation that makes member proof stale does not by itself change domain membership. Domain membership becomes stale only when its recorded governing authority changes or an explicit closure-authority defect is reconciled.

### Domain Finality Reconciliation

After the review agent and any explicitly owner-authorized independent challenger return provisional findings and **before accepting a Blocking finding that would reopen a previously satisfied/closed root or materially enlarge its acceptance domain**, recover the latest applicable Certified Closure Domain and reconcile the candidate.

Do not expose Root Blocker history to the review agent during its primary axis passes. This gate runs only after provisional findings are returned, at the bounded root/provenance reconciliation stage.

For each candidate record:

```text
Candidate: <finding/member>
Prior certified domain: <domain ID / durable certification reference>
Prior authority identity: <identity>
Current authority identity: <identity>
Authority changed: yes | no
Membership under frozen predicate: in-domain | out-of-domain | ambiguous
Exact explicit authority contradiction to frozen predicate: <None | exact source>
Finality disposition:
  in-domain-falsifier
  authority-changed-domain-stale
  closure-authority-defect
  domain-expansion
```

If membership/authority judgment is semantic rather than mechanically decidable, require one bounded self-challenge by the existing review agent limited to this reconciliation question. Spawn a second independent challenger only after explicit human authorization for the current invocation. The parent may orchestrate and validate references; it must not invent a broader domain itself.

#### `in-domain-falsifier`

The candidate satisfies the frozen membership predicate. The finding may remain Blocking. Classify as regression/missed-prior-finding from provenance after ordinary root reconciliation.

Prior PASS does not suppress an in-domain falsifier.

#### `authority-changed-domain-stale`

The governing Spec/root/architecture/contract authority materially changed after certification. The prior domain is stale for the affected claim. A fresh current domain may be built from the changed authority, and ordinary review/remediation may proceed.

The Pending packet must name the actual authority change; “reviewer now interprets it differently” is not authority change.

#### `closure-authority-defect`

Unchanged durable authority contains an **exact explicit contradiction** to the certified membership predicate/source set, such as an authoritative enumerated member omitted from a certification that claimed that exact enumeration.

This is process-integrity evidence about semantic certification. Do not convert it silently into current implementation remediation. Halt the affected root/cell behind explicit authority/domain reconciliation; preserve the implementation observation separately.

A broader plausible reading, thematic similarity, sibling implementation mechanism, lexical adjacency, or reviewer preference is not an explicit authority contradiction.

#### `domain-expansion`

The candidate does not satisfy the frozen membership predicate, governing authority is unchanged, and no exact explicit authority contradiction invalidates the frozen domain.

It is not a current Blocking remediation finding for that closed domain. Preserve it as a **Domain Expansion Observation**. It may be Advisory, future planning input, workflow-hardening evidence, or owner-directed new scope, but it may not reopen the satisfied root or be passed to `$to-tickets`.

#### Ambiguous membership

If the historical domain record is malformed or candidate membership cannot be resolved, do not silently broaden it. Record a certification/process-integrity challenge and require explicit reconciliation. Ambiguity is not implementation-remediation authority.

### Root/saturation consequences

For a root with an applicable Certified Closure Domain:

* `missed prior finding` requires `in-domain-falsifier`;
* `regression` requires an in-domain behavior whose previously proven disposition later changed;
* `root-definition gap` may not expand the frozen domain under unchanged authority;
* saturation challenge coverage is limited to the frozen domain plus members newly admitted by an actual governing-authority change;
* the bounded challenge may discover additional **in-domain** siblings omitted by prior execution, but may not replace the membership predicate/source sets with a broader sibling universe;
* `domain-expansion` and `closure-authority-defect` observations are excluded from active remediation until their own finality disposition authorizes otherwise.

A genuinely distinct current obligation not governed by an existing certified root/domain may still become a Candidate new root normally.

### Pending/aggregate state

Only findings that survive Domain Finality Reconciliation count as current Blocking findings, Root Blocker reopenings, convergence triggers, or `$to-tickets` inputs.

Persist non-actionable domain-expansion/process-integrity observations in the Pending packet's provenance/scope/finality section so history is not erased.

## Semantic Attribution and Certified Review Reuse

This section is authoritative and supersedes preserved wording below that treats Git-derived branch-local/mixed provenance as semantic Spec ownership or requires every remediation re-review to rediscover every clean cell from zero.

### Change provenance is not Standards authority

`$spec-contract` / `classify_ownership.py` supplies mechanical **change provenance** only. Read later preserved `Refresh Ownership Only` wording as `Refresh Change Provenance Only`.

Before reviewer dispatch, the parent constructs a complete **provisional Standards candidate universe** without making a semantic ownership judgment. Include:

* every branch-local or mixed-provenance repository surface/group crossed with every deterministic Standards category that could mechanically apply to that artifact class;
* every formal current-Spec tracker transition whose native lifecycle identity makes repository workflow policy applicable.

Assign stable working IDs such as `STD-CAND-1`, `STD-CAND-2`, and require:

```text
Provenance candidates: <n>
Provisional Standards candidates: <n>
Candidates omitted before attribution: 0
```

The parent may group mechanically identical surfaces/categories to control cost, but it may not omit a candidate because it assumes the change is project-level, incidental, inherited in spirit, or unrelated to the Spec. That semantic question belongs to the Standards reviewer.

Give the Standards reviewer the complete provisional candidate universe. For every candidate it must return one **Standards Attribution Manifest** row:

```text
Candidate: <STD-CAND-*>
Surface/group and Standards category
Mechanical provenance
Relevant Spec/architecture/tracker authority
Scope disposition: in-scope | out-of-scope | ambiguous
Evidence/reason
Standards disposition when in-scope: checked-no-finding | blocking | advisory
```

Rules:

* `in-scope` means an exact current Spec obligation, Spec-authorized contract transition, governing architecture requirement, or formal current-Spec tracker transition materially owns the candidate for Standards review;
* `out-of-scope` means the candidate is real branch/integration work but no current Spec authority owns that repository-standard behavior; it remains project/integration context and cannot become a current-Spec Standards blocker merely because it is on the branch;
* `ambiguous` makes Standards review incomplete and prevents Pending/Exit persistence;
* path, directory, file class, commit author, branch locality, or timing alone cannot establish either `in-scope` or `out-of-scope`;
* no repository surface is categorically exempt: a Spec may legitimately own project configuration, workflow files, tests, or source code when its exact contract materially requires changing them;
* Standards Blocking requires both `in-scope` attribution and an actual deterministic Standards violation;
* Spec and Architecture axes remain independent: an out-of-Standards-scope surface may still violate an exact Spec/Architecture obligation when those authorities govern its behavior.

Every provisional candidate remains an explicit current Standards-universe member. `out-of-scope` is counted as an explicit N/A disposition; it does not disappear. Before accepting Standards coverage require:

```text
Provisional Standards candidates: <n>
Attribution rows: <n>
In-scope: <n>
Out-of-scope: <n>
Ambiguous: 0
Missing attribution rows: 0
In-scope candidates without Standards disposition: 0
```

### Conditional Spec cells preserve their trigger

When a persisted Spec manifest cell is materially conditional, the Spec reviewer must preserve the exact source trigger and consume durable decomposition routing evidence when the trigger is inactive.

```text
Condition/trigger: <source condition>
Current trigger state: active | inactive | ambiguous
Deferred routing evidence: <Ticket Coverage Manifest / durable destination | None>
```

* `active` → review the consequent normally;
* `inactive` → do not invent present automation, policy, infrastructure, or other pre-provisioning absent exact Spec authority;
* an inactive cell may be `not-applicable` for the current candidate only when its originating condition is exact and a durable future destination/owner is preserved, normally by a `deferred-conditional` Ticket Coverage Manifest row or equivalent durable authority that already names the future lifecycle/verification destination;
* inactive with no durable destination, or ambiguous trigger state, is unresolved review state and requires a targeted provenance/routing challenge rather than a manufactured implementation blocker;
* when the trigger later becomes active, prior inactive proof is stale.

### Review Proof Reuse Ledger

A complete review may certify clean proof for later remediation reuse. Reuse never comes from the parent’s memory or from the mere fact that a cell was previously reported clean.

The review agent, and any explicitly owner-authorized independent challenger that returns `checked-no-finding` or `not-applicable`, must additionally certify a compact invalidation boundary for each group of clean cells sharing the same evidence/boundary:

```text
Proof group: RPR-<axis>-<n>
Axis: Standards | Spec | Architecture
Cells: <stable cell IDs>
Disposition: checked-no-finding | not-applicable
Evidence identity: <concise durable/current evidence reference>
Evidence stability: repository-immutable | mutable
Invalidation boundary:
- repository surfaces/predicates whose change invalidates this proof
- contract/authority inputs whose change invalidates this proof
- tracker/lifecycle inputs when material
Reviewed HEAD: <sha>
Spec Body Hash: <hash>
Spec Contract Hash: <hash>
```

For Standards, the proof-group identity may use the stable `STD-CAND-*` IDs from the current provisional universe plus its semantic attribution. The reviewer, not the parent, owns semantic sufficiency of the clean proof and boundary. The parent may only validate identity/completeness fields and persist the reviewer-certified result.

When Blocking findings create or update a conventional Spec Review, persist one compact comment after the Pending packet succeeds:

```text
<!-- review-spec-proof-reuse:v1 -->
## Review Proof Reuse Ledger
...
```

POST once, GET that exact comment, and require byte-for-byte equality. This ledger is separate from the Pending renderer because it is reusable proof state, not a finding packet. Do not change `review_spec_artifacts.py` merely to carry it.

The ledger must cover every clean/N/A current review cell exactly once. Blocking/Advisory cells are not reusable clean proof groups. Before persistence require:

```text
Clean/N/A cells: <n>
Proof-reuse cells: <n>
Missing clean/N/A cells: 0
Duplicate proof-reuse cells: 0
Proof groups without invalidation boundary: 0
```

### Remediation re-review

If a canonical Spec Review already contains a valid latest `review-spec-proof-reuse:v1` ledger whose Spec body/contract identity matches the current checkpoint, do not automatically dispatch a fresh reviewer over every prior clean cell.

First derive the complete deterministic delta from the ledger’s `Reviewed HEAD` to the current verified `HEAD`, plus any changed mutable Spec/architecture/tracker authority. For every prior proof group record:

```text
Prior proof group: <ID>
Changed surface/authority set: <complete delta relevant to boundary analysis>
Boundary intersection: zero | non-zero | ambiguous
Reuse state: reused | stale
Evidence: <deterministic intersection/stability witness>
```

Rules:

* `zero` intersection + compatible contract identity + stable evidence → `reused`;
* `non-zero` or `ambiguous` intersection, changed material authority/evidence, or missing boundary state → `stale`;
* active remediation/root cells and any cell whose proof evidence was intentionally changed are stale;
* a missing/malformed ledger or changed Spec contract requires full review for the affected universe rather than guessed reuse;
* reused cells remain explicit members of the current review universe and count as currently dispositioned; omission is not reuse;
* dispatch the single fresh review agent only over stale/uncovered cells plus any new provisional Standards/Architecture candidates created by current provenance or authority, preserving the same sequential axis isolation;
* current coverage = reused cells + freshly reviewed cells; require missing 0 and unchecked 0 across every axis;
* a mutation never forces unrelated clean cells to be semantically rediscovered when their independently certified boundary is provably untouched;
* uncertainty is fail-closed: stale, not reused.

A proposed new finding against a `reused` proof group whose boundary is deterministically untouched is a **review-process integrity contradiction**, not automatically a new remediation root. Do not silently invalidate reusable proof by choosing a different interpretation on unchanged evidence. Instead, halt persistence for that affected group and treat the contradiction as evidence that the prior clean certification or invalidation boundary was unsound; hardening/remediation of that review authority is separate from inventing Spec work. If new durable authority actually changes the claim, that authority change makes the group stale and ordinary current review applies.

On a first review, or when no valid reusable ledger exists, execute the normal complete primaries below and establish reusable clean proof if remediation remains. Any applicable Certified Closure Domain still remains in force during that full review.

## Procedure

Review the **exact verified state** of a completed Spec along the applicable independent axes:

- **Standards** — deterministic repository standards over semantically current-Spec surfaces;
- **Spec** — every cell in the persisted Spec Contract Manifest;
- **Architecture** — current architecture authority governing the affected boundaries.

This skill is review-only. `$verify-spec` owns verification and tool/gate execution. A passing **Spec Verification Receipt** is the immutable contract checkpoint for review; `$review-spec` does not rebuild or re-prove that contract.

## Core Invariants

- Recover durable state; do not rely on prior conversation.
- The newest passing Spec Verification Receipt for the exact current `HEAD` is the review contract.
- Do not rerun Ruff, mypy, pytest, duplicate scanners, wiki lint, or other `$verify-spec` gates merely to strengthen a review finding.
- Fresh current change provenance/semantic attribution is still required because the default branch may advance after verification.
- One genuinely fresh semantic review agent per invocation is the default; it performs the applicable Standards, Spec, and Architecture passes sequentially with axis isolation.
- Automatic challenger sub-agents are forbidden; any second independent reviewer requires explicit human authorization for the current invocation.
- After review-agent dispatch, the parent orchestrates; it does not become a second semantic reviewer.
- Persist only provenance-valid, **domain-finality-valid** findings and compact lifecycle state.

## Finding Taxonomy

- **Blocking** — must be remediated before review closes and has survived applicable Certified Semantic Domain Finality reconciliation.
- **Advisory** — useful but non-blocking.
- **Owner-overridden** — explicitly accepted/rejected by the owner.
- **Scope-retired** — historical root/cell proven no longer owned or required by this Spec; history remains durable.
- **Domain Expansion Observation** — current observation outside an applicable certified semantic domain under unchanged authority; preserved but non-actionable for current remediation.
- **Closure Authority Defect** — explicit conflict between a certified domain and unchanged durable authority; process/authority reconciliation required before implementation remediation.

Exact Spec mismatches are Blocking only after applicable semantic attribution/conditional/domain-finality gates. Deterministic Standards violations are Blocking only on semantically current-Spec surfaces. Architecture violations returned under current architecture authority are Blocking unless an applicable frozen domain proves the proposed member is a non-actionable expansion of an already closed current-Spec root.

## 1. Pin the Verified Checkpoint Once

Read the complete parent-Spec comment history once through the same deterministic comment parser used by `$verify-spec`, then validate the latest receipt mechanically through the review artifact utility:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
SPEC_NUMBER=<spec_issue_number>
CURRENT_HEAD=$(git rev-parse HEAD)
CURRENT_BRANCH=$(git branch --show-current)
VERIFY_TOOL=.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
REVIEW_TOOL=.agents/skills/review-spec/scripts/review_spec_artifacts.py
SPEC_COMMENTS_FILE=$(mktemp)
SPEC_COMMENTS_SUMMARY=$(mktemp)
SPEC_BODY_FILE=$(mktemp)
REVIEW_CHECKPOINT=$(mktemp)

gh api --paginate --slurp \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  "repos/$REPO/issues/$SPEC_NUMBER/comments?per_page=100" \
  > "$SPEC_COMMENTS_FILE"

python "$VERIFY_TOOL" comments \
  --input "$SPEC_COMMENTS_FILE" \
  > "$SPEC_COMMENTS_SUMMARY"

gh issue view "$SPEC_NUMBER" --repo "$REPO" --json body --jq .body \
  > "$SPEC_BODY_FILE"

python "$REVIEW_TOOL" checkpoint \
  --comments-summary "$SPEC_COMMENTS_SUMMARY" \
  --spec-body "$SPEC_BODY_FILE" \
  --spec "$SPEC_NUMBER" \
  --head "$CURRENT_HEAD" \
  --branch "$CURRENT_BRANCH" \
  > "$REVIEW_CHECKPOINT"
```

Require the expected `spec-<n>` branch and a clean worktree before review begins.

The checkpoint utility fails closed unless the newest verification receipt is passed, bound to the exact current Spec/HEAD/baseline/branch/body hash, contains one complete manifest, maps every manifest cell exactly once to proven/not-applicable coverage, and has zero unresolved cells.

Do **not** independently parse receipt Markdown, walk backward to an older receipt, or rebuild the source-unit/manifest proof inside review. Any checkpoint failure routes back to fresh `$verify-spec`.

The checkpoint JSON is the immutable review contract for this invocation. Retain exactly its baseline, body/contract hashes, manifest, verification hash, and receipt identity.

## 2. Refresh Change Provenance Only

The verification receipt proves the immutable contract; review needs fresh mechanical change provenance against the **current** default branch.

Use the canonical `$spec-contract` provenance helper:

```bash
OWNERSHIP_FILE=$(mktemp)

python \
  .agents/skills/spec-contract/scripts/classify_ownership.py \
  --baseline "$(jq -r .baseline "$REVIEW_CHECKPOINT")" \
  --branch "$CURRENT_BRANCH" \
  --head "$CURRENT_HEAD" \
  > "$OWNERSHIP_FILE"
```

This is a provenance refresh, not contract validation and not semantic ownership. The Semantic Attribution section above owns current-Spec Standards scope.

## 3. Project Delivery Guard

For a Wayfinder-managed Spec, before reviewer dispatch:

1. require the Spec open and all direct blockers closed;
2. recover governing Wayfinder(s) from durable lineage;
3. invoke `$project-delivery-management` `reconcile` once when required by that skill;
4. invoke `$project-delivery-management` `guard <Wayfinder>` for each governor;
5. require at least one `PROJECT DELIVERY GUARD: ALLOWED`.

Do not reproduce the guard with custom `sed`, `awk`, regex parsing, Project-field logic, or a parallel frontier implementation.

Immediately before Pending or Exit persistence, invoke `guard <Wayfinder>` again for the already-resolved governor(s). That is mutable-state **revalidation**, not a second delivery-analysis phase. Do not rediscover lineage or explicitly rerun broader reconciliation unless intervening durable mutation invalidated those inputs.

## 4. Recover Durable Review State

A conventional **Spec Review** issue exists only for blocker/remediation history. A clean first-pass review does not create one; the parent Spec owns the final Exit Receipt.

Resolve an existing conventional Spec Review from one paginated issues read and the exact body marker:

```text
**Parent Spec:** #<n>
```

There must be zero or one matching issue titled `Spec Review: ...`; multiple matches fail closed. Do not infer review identity from Project fields, labels, title similarity alone, or prior conversation.

When Blocking findings require first-time remediation, create the conventional Spec Review **once**, then boundedly re-resolve the same canonical query. Never POST a second review issue because of read-after-write delay.

If a conventional Spec Review exists, recover privately:

- existing `RB-*` IDs/stable invariants;
- active/satisfied/owner-overridden/scope-retired/domain-excluded cells;
- cumulative acceptance matrix and semantic surfaces;
- prior reviewed/satisfied heads and Owner Overrides;
- applicable durable ticket/root closure certifications sufficient to recover Certified Closure Domains.

Do not expose root history/domain conclusions to the review agent during its primary axis passes. Domain Finality Reconciliation happens after provisional findings return.

### Scope Attribution Gate

An historical root/cell may scope-retire only when all are proven:

1. implicated surface is inherited-only or otherwise outside this Spec ownership;
2. no manifest cell requires the behavior;
3. no current architecture authority requires the behavior for this Spec;
4. retirement does not remove another active Spec-owned obligation.

Pre-existing behavior is not automatically out of scope.

## 5. Build the Review Universes

Build routing coverage before dispatch.

### Standards

Use the provisional Standards candidate universe and semantic attribution procedure defined above. Do not substitute raw branch-local/Mixed labels for semantic ownership.

### Spec

Use the checkpoint manifest **exactly**. Each persisted manifest cell is one Spec review cell. Require no missing/unknown cells before dispatch.

A reviewer-discovered originating-Spec obligation absent from the manifest is a **contract defect**. Halt and require fresh `$verify-spec`; do not silently expand the universe.

### Architecture

Create `ARCH-*` cells covering current affected architecture authorities, canonical owner/path/boundary/lifecycle/source-of-truth, semantically affected participants, and sibling/alternate/named surfaces that current authority independently requires to obey the same rule. `$review-architecture` owns architecture evidence procedure.

Architecture universe construction does not itself override a Certified Closure Domain governing an already satisfied current-Spec root; that reconciliation occurs after provisional findings return.

## 6. Reviewer Execution Integrity

A fresh reviewer is a genuinely separate context that did not participate in parent orchestration and receives the bounded review inputs necessary to execute the three axis-isolated passes, without Root Blocker history, Certified Closure Domain conclusions, or prior reviewer conclusions.

Default mode:

```text
Reviewer execution: single-fresh-subagent-three-axis-passes
Reviewer execution override: None
```

If genuinely fresh contexts are unavailable, halt before review/persistence unless the human explicitly authorizes same-agent fallback for the current invocation. The override waives independence only; it never accepts or suppresses findings.

Canonical authorization:

```text
OWNER REVIEWER EXECUTION OVERRIDE: authorize same-agent reviewer fallback for this review
```

Under fallback, execute the same axis-isolated passes sequentially in the parent context and disclose reduced reviewer independence. Never describe same-context execution as fresh.

## 7. Dispatch One Review Agent

Dispatch exactly one fresh semantic review sub-agent for the invocation. It must execute the applicable axes sequentially in this fixed order:

1. Standards, when applicable;
2. Spec, always;
3. Architecture, when applicable.

Give the reviewer only:

- the complete authority and cell universe for each applicable axis;
- relevant evidence pointers/semantically current surfaces;
- no Root Blocker history, Certified Closure Domain conclusions, or prior reviewer conclusions.

Before starting the next axis, freeze the current axis's coverage, findings, and proof groups. Shared factual evidence may be reused, but a prior axis's semantic conclusion is never evidence for a later axis.

The reviewer must disposition every supplied cell and continue after discovering a blocker. Do not fan out axes into separate agents.

Coverage states:

```text
checked-no-finding | blocking | advisory | not-applicable
```

`not-applicable` requires exact authority/reason.

### Claim-Proof Integrity

For every material cell, the reviewer must internally establish claim/predicate/domain/falsifier/evidence and exclude the falsifier before `checked-no-finding`. Material assumptions must themselves be proven.

Do **not** serialize full predicate/falsifier prose for clean cells merely for bookkeeping. Return compact coverage groups plus full provisional findings. A useful per-axis result is:

```text
Coverage: <cell IDs grouped by disposition>; missing 0; unchecked 0
Blocking: <full provisional finding records>
Advisory: <records>
N/A: <cells + reasons>
Challenge triggers: <None | exact cell/question>
```

Axis blocker authority remains necessary but is not sufficient for a finding that would reopen an applicable certified root; Domain Finality Reconciliation must also survive.

## 8. Parent Orchestration Boundary

After review-agent dispatch, the parent is an **orchestrator**, not another reviewer.

While the reviewer runs, the parent may:

- wait/collect the reviewer result;
- recover tracker/remediation state not exposed to the reviewer;
- prepare compact persistence metadata;
- deduplicate returned records mechanically.

The parent must **not**:

- independently re-review assigned semantic cells;
- explore implementation to search for additional findings in parallel;
- rerun pytest/Ruff/mypy/Arid/JSCPD/wiki lint or other verification gates;
- use a passing/failing test as substitute review authority;
- preempt a reviewer by reaching its own semantic disposition.

After results return, parent inspection is allowed only at these narrow boundaries:

1. **Axis-Provenance validation** — confirm that the cited native authority exists and applies to the cited surface/cell;
2. **concrete challenge trigger** — require the review agent to perform the bounded self-challenge defined below; use a second independent challenger only after explicit human authorization, never an open-ended parent review;
3. **root/domain reconciliation** — inspect only historical root/Certified Closure Domain evidence implicated by provisional findings.

If accepting/rejecting a finding would require broad semantic exploration, require the bounded review-agent self-challenge instead. If genuine second-context independence is materially required, halt for explicit human authorization rather than spawning another agent automatically.

## 9. Conditional Challenge

For a concrete trigger, require one bounded challenge over only the affected cell/question. By default the existing review agent performs that challenge as an axis-scoped self-challenge; do not create another sub-agent:

1. coverage gap/materially omitted applicable cell;
2. authority conflict/ambiguity;
3. contradictory or materially insufficient finding evidence;
4. Domain Finality Reconciliation requiring semantic membership/authority judgment;
5. convergence trigger after finality-valid root reconciliation.

Challenge only the affected cell/question. For the default self-challenge, the reviewer must restate the question from governing authority/evidence and actively attempt to falsify its current disposition without treating its earlier conclusion as evidence. Apply the same Claim-Proof Integrity. A genuinely independent challenger may be spawned only after explicit human authorization for the current invocation and should not be given the primary conclusion intentionally. If a required challenge remains unresolved, review is incomplete and nothing is persisted as PASS/remediation-ready.

## 10. Freeze Findings and Validate Provenance

Coverage is complete only when every supplied cell is dispositioned, no manifest cell is missing, no applicable Standards/Architecture cell is unchecked, and every N/A has a reason.

First freeze/deduplicate **provisional** findings and validate their axis authority. Then apply Certified Semantic Domain Finality to every finding implicated by a prior satisfied/closed root/domain.

Only finality-surviving findings become current Blocking findings. Preserve rejected domain-expansion/closure-authority-defect observations explicitly; do not silently delete them or move them to another axis.

## 11. Reconcile Durable Roots

Only after findings survive axis provenance **and Domain Finality Reconciliation** may the parent use them to mutate Root Blocker state.

Map a finding to an existing root only when the stable invariant and applicable certified domain already derive it, or when an actual changed authority has made the prior domain stale. Otherwise mark `Candidate new root` only for a genuinely distinct current obligation, not as an escape hatch around domain finality.

For a newly accepted violation against a previously satisfied/closed root, classify only from implicated history:

- **Missed prior finding** — must be `in-domain-falsifier`;
- **Regression** — must be in-domain and provenance must show the behavior changed after proof;
- **Origin uncertain** — permitted only for an in-domain finding whose temporal origin cannot be recovered.

Previously satisfied sibling cells remain satisfied unless directly contradicted.

### Convergence Saturation

A finality-valid Missed prior finding proves incomplete prior **member disposition/execution** inside the frozen domain. Before persistence:

1. recover the applicable Certified Closure Domain rather than deriving a broader root universe from scratch;
2. execute exactly one bounded saturation self-challenge by the existing review agent under the originating axis over that frozen domain and any newly admitted members caused by an actual governing-authority change;
3. require every authorized domain item checked and `unchecked 0`;
4. provenance-validate new **in-domain** findings and merge them before persistence.

A second independent saturation challenger requires explicit human authorization for the current invocation. A `root-definition gap` cannot broaden a frozen domain under unchanged authority. A challenge-discovered candidate outside the frozen predicate becomes a Domain Expansion Observation, not another remediation obligation.

Do not run another generic full-axis review.

## 12. Aggregate

Report the three axes using **Human-Facing Aggregate Format** above, then compact coverage/effectiveness:

```text
Reviewer execution: <mode>
Standards: <coverage>; unchecked 0
Spec: <manifest count>; unchecked 0
Architecture: <coverage>; unchecked 0
Targeted challengers: <n>
Domain-finality challengers: <n>
Saturation challengers: <n>
Primary validated findings: <n>
Finality-surviving Blocking findings: <n>
Domain-expansion observations: <n>
Closure-authority defects: <n>
Targeted-only validated findings: <n>
Saturation-only in-domain findings: <n>
```

If any finality-surviving Blocking Architecture finding requires an architecture decision, halt with `$architecture-remediation`; do not invent the decision.

## 13. Pending Review Remediation

If architecture-conforming finality-surviving Blocking findings remain, Scope corrections must update existing durable review state, or prior persisted findings require Domain Finality correction:

1. revalidate Project Delivery guard for the already-resolved governor(s);
2. require `HEAD` still equals the verification checkpoint;
3. create/re-resolve the conventional Spec Review only when Blocking remediation requires one;
4. render/persist the Pending packet through the deterministic review utility where possible; fold Domain Finality Reconciliation into existing provenance/root/scope/saturation text when the utility has no dedicated field rather than changing its schema solely for this hardening;
5. POST once, GET that exact comment, and require byte-for-byte equality;
6. invoke `$review-spec-remediation` only after persistence succeeds.

The Pending packet must make the active/non-actionable distinction recoverable:

```text
Domain Finality Reconciliation:
- <candidate> -> <finality disposition> -> actionable yes|no -> evidence
```

Do not hand-build a parallel root-remediation packet that bypasses the deterministic renderer's existing checkpoint bindings.

If remediation remains active and `$review-spec-remediation` returns `$to-tickets`, present that handoff from durable review/remediation state without eager GitHub Project projection; the repository-wide `$project-tracking` cadence remains authoritative.

## 14. Exit Gate

PASS requires:

- current `HEAD` and Spec body still match the checkpoint;
- reviewer execution integrity satisfied;
- every Spec/Standards/Architecture review cell dispositioned;
- no unresolved targeted/domain-finality/saturation coverage;
- zero finality-surviving current Blocking findings;
- all existing roots `satisfied`, `owner-overridden`, or `scope-retired` after domain-excluded cells are ignored for active remediation;
- zero Candidate new roots;
- zero unresolved Closure Authority Defects.

The immutable contract itself does not need to be rebuilt again at Exit. Re-read current `HEAD`, clean worktree, Spec body hash, and mutable delivery guard; if any checkpoint binding changed, require fresh `$verify-spec`.

### Persist Exit Receipt

Revalidate Project Delivery guard, render the Exit Receipt through the same deterministic utility, POST it to the **parent Spec**, GET the exact comment, and require byte equality.

```bash
EXIT_INPUT=$(mktemp)
EXIT_FILE=$(mktemp)
EXIT_JSON=$(mktemp)
COMMENT_JSON=$(mktemp)
READBACK_FILE=$(mktemp)

python "$REVIEW_TOOL" render-exit \
  --input "$EXIT_INPUT" \
  --output "$EXIT_FILE"

jq -Rs '{body: .}' "$EXIT_FILE" > "$EXIT_JSON"
gh api --method POST \
  "repos/$REPO/issues/$SPEC_NUMBER/comments" \
  --input "$EXIT_JSON" > "$COMMENT_JSON"

COMMENT_ID=$(jq -r .id "$COMMENT_JSON")
COMMENT_URL=$(jq -r .html_url "$COMMENT_JSON")
[ -n "$COMMENT_ID" ] && [ "$COMMENT_ID" != "null" ]
gh api "repos/$REPO/issues/comments/$COMMENT_ID" \
  | jq -j .body > "$READBACK_FILE"
cmp -s "$EXIT_FILE" "$READBACK_FILE"
```

Do not create a conventional Spec Review on a clean PASS path.

A persisted Exit Receipt establishes the parent Spec base lifecycle:

```text
Artifact Type: Spec
Workflow State: Ready to Merge
Work Status: Ready
Next Skill: $spec-merge-cleanup
Root Blocker: None
Completed On: None
```

GitHub Project projection is deferred to the repository-wide `$project-tracking` cadence, normally `$spec-merge-cleanup`, or an explicit human-requested board refresh. Project drift does not invalidate the durable review receipt.

## 15. Human Handoff

On PASS:

> ✅ **Spec review passed.**
>
> The verified and reviewed `HEAD` is ready for merge and cleanup.
>
> Please run:
>
> ```
> $spec-merge-cleanup - <Spec Title> (<Spec URL>)
> ```

Do not close the Spec or Spec Review here; `$spec-merge-cleanup` owns merge/closure/branch cleanup.

## Transition-Bound Review Proof State

Every reviewer role must maintain enough working proof to justify each disposition:

```text
Cell
Claim/predicate/domain
Falsifier
Evidence
Survivability: excluded | survives
Material assumptions
Disposition
```

`checked-no-finding` requires excluded falsifier and no unproven material assumption. The parent must require complete universe coverage, no unknown/missing/unresolved cells, no incomplete clean dispositions, and no unresolved Domain Finality Reconciliation before PASS/remediation handoff.

These records are **working reasoning state**, not mandatory serialized output. The review agent and any explicitly owner-authorized independent challenger should return compact grouped coverage and full findings rather than dumping one verbose proof object per clean cell. Fresh reviewer independence remains mandatory unless explicitly owner-overridden for the current invocation.
