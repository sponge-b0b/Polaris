---
name: verify-spec
description: Perform authorized Spec-wide verification against a deterministic Spec contract, reuse safe ancestor checkpoints, repair Spec-owned failures, independently certify semantic proof, and record a passing receipt for the exact final HEAD.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Global Specification Integration & Verification

Verify the completed Spec against its fixed baseline as one integrated acceptance universe.

A successful run records a **Spec Verification Receipt** for the exact final committed `HEAD`. `$review-spec` requires that receipt.

Verification discipline is applicability-driven:

> Repository location does not determine verification discipline. Derive required proof from the deterministic Spec contract and actual Spec-owned change surfaces.

The fixed baseline establishes integration history. It does **not** make every later default-branch change part of the current Spec's repository-standards ownership.

## Session Independence

Assume no prior conversational or agent-session state.

Recover every correctness-critical input from the invocation, repository, durable tracker state, and current skill contracts. Prior-session summaries are routing context only.

If required durable state cannot be recovered, report the missing artifact rather than infer it.

## Deterministic Mechanics Boundary

The reasoning agent owns:

- applicability;
- semantic proof design;
- falsifiers and authoritative domain boundaries;
- Nested Universe reasoning;
- evidence sufficiency candidates;
- proof-policy impact classification;
- repair decisions;
- final lifecycle judgment.

The checked-in verifier utility owns repeatable artifact mechanics:

```text
.agents/skills/verify-spec/scripts/verify_spec_artifacts.py
```

Use it for:

- paginated Spec-comment normalization and baseline/latest-receipt extraction;
- proof-packet structure validation and canonical hashing;
- deterministic certifier-admission checks;
- bounded certification-slice generation;
- carry-forward delta/digest/boundary validation;
- final certification/coverage consistency validation;
- complete receipt rendering;
- byte-for-byte receipt validation before and after GitHub persistence.

Do **not** recreate an operation owned by this utility with ad hoc Python, heredoc scripts, custom `jq` pipelines, or one-off receipt parsers. If the utility rejects valid input or cannot represent a required invariant, fix the utility as verification infrastructure rather than bypassing it.

For deterministic repository checks not owned by this utility, prefer an existing checked-in repository tool. Use inline Python only when no reusable owner exists; keep it short, invoke it through `uv run python`, and avoid heredocs where a stable command/file can express the check. If a heredoc is unavoidable, quote its delimiter.

This boundary is an efficiency rule, not an authority change. Deterministic tooling never supplies semantic certification.

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

Re-run this guard immediately before persisting a passing receipt.

## 3. Select an Incremental Checkpoint

The fixed Spec baseline remains the canonical verification origin.

Use only the `latest_receipt` returned by the deterministic comments summary. Do not search backward for a convenient older receipt.

Checkpoint mode is permitted only when the newest receipt is well formed and all of these hold:

1. `Status: passed`;
2. `Verified Baseline == BASELINE_COMMIT`;
3. receipt branch equals current Spec branch;
4. receipt `Verified HEAD` resolves and is an ancestor of current `HEAD`;
5. receipt `Spec Body Hash == SPEC_BODY_HASH`;
6. receipt `Spec Contract Hash == SPEC_CONTRACT_HASH`;
7. complete per-cell contract coverage exists;
8. complete checkpoint→current repository delta is bounded.

Prove ancestry and inspect the complete delta:

```bash
git merge-base --is-ancestor "$CHECKPOINT_HEAD" HEAD
git log "$CHECKPOINT_HEAD"..HEAD --oneline
git diff --name-status "$CHECKPOINT_HEAD"..HEAD
git diff "$CHECKPOINT_HEAD"..HEAD
```

If any condition fails, use full verification from the fixed baseline.

### Inherit Only Independently Certified Immutable Proof

Never inherit mutable tracker, dependency, project-focus, hierarchy, authorization, lifecycle, runtime, or service truth.

A prior proof object may survive only when:

- its exact object hash is unchanged;
- mapped manifest claims and `SPEC_CONTRACT_HASH` are unchanged;
- current proof policy does not invalidate it;
- its certifier-approved evidence stability is `repository-immutable`;
- the complete certified-HEAD→candidate-HEAD changed-path set has deterministic zero intersection with the certifier-approved invalidation boundary;
- no changed surface has an uncertain transitive relationship to that boundary.

Any uncertainty makes the object stale.

### Proof-Policy Invalidation

Checkpoint invalidation includes proof semantics, not only implementation changes.

If the checkpoint delta contains a normative change to this skill or an invoked proof owner/helper that could change semantic sufficiency, required proof domain, applicability, cell disposition, verifier integrity, object hashing, evidence stability, or invalidation semantics, re-prove the affected objects. If impact cannot be bounded confidently, invalidate all semantic certification.

A universal change to the meaning of `proven` or cell-proof sufficiency invalidates all inherited manifest proof.

Presentation-only edits that cannot affect proof validity do not invalidate proof merely because a verification-policy file changed.

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

## 5. Candidate Proof Tier

Semantic proof is deliberately performed before expensive broad final gates.

Before certification convergence, run only evidence needed to build or falsify Proof Objects:

- direct source/runtime/tracker/document inspection;
- targeted tests that are direct proof evidence;
- mandatory service preflight only for selected tests that require it;
- narrow static/reference checks that establish a predicate, Nested Universe, or repair;
- applicable architecture/wiki proof.

Do not run broad formatter/linter/type suites or the complete regression scope merely to prepare the first certifier unless that exact gate is direct evidence for a Proof Object.

When a certifier rejects an object or verification repairs repository state, rerun only affected candidate-tier evidence and rebuild only affected objects.

## 6. Build Proof Objects

The parent verifier constructs candidate semantic proof. It may not self-certify it.

### 6.1 Cell-to-Proof Map

Maintain exactly one coverage row for every manifest cell:

```text
Cell: <ID>
Proof Object: <P-n>
State: pending-certification
```

Before certification:

- manifest and coverage order must match exactly;
- every manifest cell appears once;
- no unknown cell exists;
- every cell maps to one proof object;
- every proof object is referenced;
- `proven` and `not-applicable` are forbidden before independent certification.

### 6.2 Structured Proof Object Contract

Represent each working Proof Object in the machine packet as:

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
  "invalidation_boundary": ["path/to/file.py", "tests/area/**"],
  "evidence_stability": "repository-immutable|mutable"
}
```

For non-repository evidence use its actual kind (`tracker`, `runtime`, `service`, `time`, etc.). Such evidence is mutable unless `immutable_snapshot: true` identifies an authoritative immutable snapshot.

The semantic rules remain:

- group cells only when one predicate/falsifier/domain/evidence set truly establishes every mapped claim;
- shared files or vocabulary alone do not justify grouping;
- preserve every material clause, quantifier, condition, exception, and named surface;
- the falsifier must be a real logical counterexample;
- evidence must address the predicate directly;
- invalidation boundaries must include every direct/transitive repository or durable-evidence surface whose mutation could falsify the certified predicate while wording remained unchanged;
- `repository-immutable` is permitted only when every material evidence fact is recoverable from immutable repository state or an authoritative immutable snapshot;
- semantic sufficiency, boundary authority, transitive completeness, and final disposition remain certifier judgments.

### Conservative Grouping

Prefer smaller semantically cohesive Proof Objects over aggressive packing.

The artifact utility warns when one object maps more than 12 cells. A warning is not an automatic failure, but it requires explicit cohesion review before dispatch. Split the object unless one predicate/falsifier/domain/boundary genuinely proves every assigned cell without conditional subdomains.

This rule intentionally trades a modest increase in object count for fewer expensive rejected-certifier iterations.

### Nested Universe Closure

When a predicate quantifies over a finite/discoverable domain (`all`, `every`, `no`, `none`, `only`, `complete`, repository-wide, named complete set, or equivalent), include a Nested Universe witness:

1. `explicit` — enumerate every current member/disposition, or provide a deterministic generator plus member count/digest; or
2. `exhaustive` — name a deterministic/queryable mechanism whose semantics cover the full authoritative boundary and preserve the complete result needed to exclude the falsifier.

Use `not-applicable` only when there is no material exhaustive/domain-closure predicate, with a reason.

A changed-file list, examples, targeted tests, or “searched relevant files” is not exhaustive unless the authoritative domain is exactly that set.

## 7. Deterministic Certifier Admission

Write the working packet input once as JSON with these top-level bindings:

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

`prepare-packet` is the mandatory admission gate before **every** certifier dispatch. It deterministically checks at least:

- exact manifest↔coverage order and cardinality;
- no missing/unknown/duplicate cell mappings;
- no unreferenced Proof Objects;
- required Proof Object fields;
- valid Nested Universe structural form;
- every repository evidence path is covered by the proposed invalidation boundary;
- `repository-immutable` is rejected when non-immutable tracker/runtime/service/time evidence is present;
- stable canonical `PROOF_OBJECT_HASH` values;
- stable canonical `PROOF_PACKET_HASH`.

Resolve every admission error before spending a fresh certifier context.

Do not ask the certifier to discover packet bookkeeping defects that deterministic admission can prove locally.

The utility cannot prove semantic sufficiency or transitive boundary completeness. Those remain independent-certifier responsibilities.

## 8. Independent Proof Certification

A manifest cell may transition to `proven` or `not-applicable` only from a genuinely fresh non-mutating certifier.

A **fresh proof certifier**:

- did not participate in implementation, parent verification, proof construction, or prior certification for any assigned object lineage in the current invocation;
- receives only the global bindings plus assigned manifest claims, assigned Proof Objects, and evidence references needed for those objects;
- is non-mutating;
- may not delegate/spawn another certifier;
- does not receive prior review findings, Root Blocker history, parent intended verdict, or prior conclusions for the object lineage.

### Bounded Certification Slices

After admission, generate the exact stale/uncertified slice with the utility:

```bash
SLICE_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" make-slice \
  --packet "$PACKET_FILE" \
  --proof P-1 \
  --proof P-2 \
  --output "$SLICE_FILE"
```

The slice contains only assigned manifest claims, assigned Proof Objects/evidence, exact candidate `HEAD`, `SPEC_CONTRACT_HASH`, object hashes, and `CERTIFICATION_SLICE_HASH`.

Default to one fresh certifier for all stale objects when the slice is bounded. Partition deterministically only when unrelated evidence domains/context size make multiple smaller slices materially cheaper.

Never resend already-valid retained objects merely to make a slice complete.

If a required fresh context cannot be created, fail closed:

```text
VERIFICATION PROOF CERTIFICATION: INDEPENDENCE UNAVAILABLE
Status: verification incomplete
Required: genuinely fresh non-mutating proof certifier
```

There is no same-agent/owner override.

### Certifier Judgment

For every assigned Proof Object the certifier independently verifies:

1. mapped claims are fully represented by the predicate;
2. the falsifier is a real counterexample;
3. the domain boundary is authoritative;
4. Nested Universe evidence is complete where required;
5. direct current evidence establishes the predicate;
6. material assumptions are authoritative/directly proven;
7. no counterexample survives current `HEAD` inspection;
8. the invalidation boundary includes direct/transitive invalidators;
9. evidence stability is correctly classified.

Return exactly one result per object:

```text
Proof: P-<n>
Proof Object Hash: <hash>
Certified HEAD: <sha>
Certification Slice Hash: <hash>
Certification: certified | rejected | unresolved
Disposition: proven | not-applicable | unresolved
Certification Evidence: <concise direct evidence/counterexample/insufficiency>
```

The parent may not upgrade, suppress, reinterpret, or override `rejected`/`unresolved`.

If a grouped object cannot receive one valid disposition for all cells, split it and use a **new fresh certifier** for revised object lineages.

If certification exposes an omitted originating-Spec obligation, halt with `SPEC CONTRACT: INCOMPLETE`; do not silently add it.

### Retry Economy

A rejected object does not invalidate unrelated certified objects.

For a proof-construction rejection:

1. revise only rejected/unresolved objects;
2. rerun deterministic admission;
3. preserve unchanged certified object hashes only when Section 3 invalidation rules permit;
4. create a new slice containing only revised/stale objects;
5. dispatch a new fresh certifier only for those objects.

Do not rerun broad gates or resend unrelated proof because an object boundary/grouping was corrected.

## 9. Semantic Convergence and Final Gates

Semantic proof converges when every current Proof Object is independently certified, with:

```text
Stale proof objects: 0
Rejected proof objects: 0
Unresolved proof objects: 0
Missing proof certifications: 0
Unresolved manifest cells: 0
```

Only after convergence run every applicable final gate at the stable candidate `HEAD`.

### Repository Diff Hygiene

When Spec-owned/Mixed repository content changed:

```bash
git diff --check "$BASELINE_COMMIT"
```

Fix only deterministic Spec-owned whitespace defects that are semantics-preserving.

### Code Quality

When applicable:

```bash
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff format --check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> uv run ruff check .
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number> \
  uv run mypy . --explicit-package-bases
```

Never use Ruff `--add-noqa`.

Inherited-only unrelated failures are report-only for this Spec.

### Tests, Services, and Persistence

Every pytest invocation must set:

```text
POLARIS_BROAD_VERIFY_AUTHORIZED=verify-spec-<spec_issue_number>
```

Before pytest, perform the mandatory exact-scope service preflight from `AGENTS.md` and `docs/process/testing-guide.md`.

For service-backed scopes, verify required environment/configuration and service readiness before pytest. A timeout, connection failure, or skip is not a preflight.

Never expose secrets or authenticated connection strings.

A required check skipped because prerequisites are absent remains unresolved.

### Documentation / Workflow / Architecture

Verify non-code contracts directly where applicable. Use owning skills rather than parallel ad hoc implementations.

If Living Entity Wiki routing is relevant, invoke `$wiki-lint`; do not recreate wiki structural/citation checking inside `$verify-spec`.

Invoke `$deduplicate-code` only when Spec-owned/Mixed work introduces or materially changes behavior for which duplicate implementation is a real risk.

### Final-Gate Repair

If a final gate requires repository mutation:

1. repair the narrowest authoritative point;
2. rerun only affected final/candidate evidence;
3. rebuild affected Proof Objects;
4. apply proof invalidation from the prior certified `HEAD` to the new candidate;
5. recertify only stale objects with new fresh certifiers;
6. rerun only final gates invalidated by the mutation.

Token/runtime economy never permits retaining a proof/gate when impact is uncertain.

## 10. Failure and Architecture Routing

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

## 11. Establish Final State

After semantic convergence and final gates:

1. rerun `$spec-contract` in `build` mode at final `HEAD`;
2. require body/contract validity and reconcile ownership;
3. recompute checkpoint delta/proof-policy invalidation if checkpoint mode;
4. rebuild the final packet through `prepare-packet`;
5. require every Proof Object freshly certified at final `HEAD` or retained through a complete valid carry-forward result;
6. require every applicable final gate passed at exact final `HEAD`;
7. require clean worktree.

If verification made repository changes:

1. verify Spec branch;
2. stage only verification-owned files;
3. invoke `$conventional-commits`;
4. commit;
5. push with `git push -u origin HEAD`;
6. rebuild final packet/state for the new exact `HEAD` and invalidate/recertify as required.

## 12. Deterministic Final State and Receipt

Build one final JSON state containing:

```text
packet
verification
certifications
carry_forward
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

Each certification row must contain:

```text
proof
proof_object_hash
certified_head
certification_slice_hash
certification
disposition
evidence
```

For any object certified before final `HEAD`, the parent must first classify proof-policy impact for that object as exactly one of:

```text
none | invalidating | uncertain
```

Do not hand-calculate repository delta digests or boundary intersections. Generate carry-forward rows deterministically:

```bash
CERTIFICATIONS_FILE=$(mktemp)
POLICY_IMPACT_FILE=$(mktemp)
CARRY_FORWARD_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" build-carry-forward \
  --packet "$PACKET_FILE" \
  --certifications "$CERTIFICATIONS_FILE" \
  --policy-impact "$POLICY_IMPACT_FILE" \
  --final-head "$FINAL_HEAD" \
  --repo-root . \
  --output "$CARRY_FORWARD_FILE"
```

The utility recomputes the complete Git changed-path set, delta digest, and invalidation-boundary intersection. Any intersection, mutable evidence, invalidating/uncertain proof-policy impact, or unresolvable Git delta fails closed.

Run final deterministic validation:

```bash
FINAL_STATE=$(mktemp)

uv run python "$ARTIFACT_TOOL" validate-final \
  --input "$FINAL_STATE" \
  --repo-root .
```

Final validation derives cell dispositions from certification. The parent does not assign a stronger state.

### Receipt Rendering

Do not hand-author the receipt or construct another Markdown parser.

Render the complete backward-compatible receipt from final state:

```bash
RECEIPT_FILE=$(mktemp)

uv run python "$ARTIFACT_TOOL" render-receipt \
  --input "$FINAL_STATE" \
  --repo-root . \
  --output "$RECEIPT_FILE"

uv run python "$ARTIFACT_TOOL" validate-receipt \
  --input "$FINAL_STATE" \
  --receipt "$RECEIPT_FILE" \
  --repo-root .
```

The rendered receipt contains the complete:

- fixed bindings/hashes;
- Spec Contract Integrity counts;
- ownership summary;
- ordered Spec Contract Manifest;
- Proof Objects and object hashes;
- independent certifications;
- carry-forward rows;
- ordered Spec Contract Coverage;
- verification gates;
- unrelated inherited findings.

This preserves the durable contract required by `$review-spec` while removing repeated LLM-authored serialization/parsing work.

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
  --receipt "$READBACK_FILE" \
  --repo-root .
```

Because the local receipt was generated from validated final state, exact byte equality plus deterministic re-render validation proves persisted-body integrity. Do not create a second custom parser to reconstruct the same packet again.

Never POST/PATCH a partial receipt, repair a malformed persisted receipt in place, replace it with a file reference, or create a second corrective receipt in the same invocation.

If POST succeeds but exact readback/validation fails, verification is incomplete: report `COMMENT_URL` and stop.

Any later Spec-body change or candidate commit makes the receipt stale.

## 13. Successful Lifecycle Transition

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

## 14. Reporting and Human Handoff

Report concisely:

- baseline/final `HEAD`;
- verification mode/checkpoint;
- Spec contract counts/hash;
- ownership classification;
- applicable gates;
- manifest coverage summary;
- proof-object count/hash and fresh-versus-retained certification summary;
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
