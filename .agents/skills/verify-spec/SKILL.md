---
name: verify-spec
description: Verify one completed CCL-backed Spec candidate against its deterministic contract cells, repair implementation-owned failures, obtain one fresh independent closure verdict, and persist the exact passing verification receipt.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Verify Spec

`$verify-spec` owns integrated verification of one completed Spec candidate.

For a CCL-backed software Spec, verification consumes a **frozen deterministic contract**:

```text
OBL-*   exact CCL material semantics
IMP-*   private/mechanical implementation obligations
TEST-*  explicit proof/test obligations
EXC-*   exclusions / decomposition guardrails
```

Verification is independent about **whether the implementation satisfies those cells**.
It is not independent authority to reinterpret Spec prose, rediscover architecture, add a
new contract cell, or strengthen/weaken a CCL assertion.

## 1. Recover exact lifecycle state

Assume no prior chat/session state.

Recover from current durable state:

* parent Spec issue and exact body;
* governance mode from Spec-local provenance markers;
* exactly one Workspace Metadata record, fixed baseline, and `spec-<n>` branch when the
  Spec is branch-backed;
* exact current candidate `HEAD`;
* current `ticket-coverage-manifest:v2` on the parent Spec;
* complete current implementation-ticket set and native dependencies;
* current ticket closure evidence/checkpoints;
* applicable review/remediation state when this is a re-verification;
* current CCL ledger.

Do not use Project fields or chat memory as verification authority.

For Wayfinder-managed Specs, invoke `$project-delivery-management reconcile` and the
current governor guard(s) where the lifecycle requires actionability. Independent Specs
remain outside Wayfinder focus.

Require all native Spec blockers to be closed before final certification. An unresolved
blocker may coexist with verification-owned repairs that do not depend on the missing
authority, but PASS is unreachable while the blocker remains.

## 2. Build the deterministic Spec contract

Take one exact current Spec-body snapshot and require:

```bash
python -m scripts.ccl_spec check <spec-body-file> contracts/ccl/transactions
python -m scripts.spec_contract build <issue-json> <contract-output>
```

Require:

```text
SPEC CONTRACT: VALID
Semantic prose classification performed: 0
```

Retain:

* `SPEC_BODY_HASH`;
* `SPEC_CONTRACT_HASH`;
* complete ordered `cells` array;
* every `cell_hash`;
* exact CCL address set for every `OBL-*`.

Contract construction is deterministic. Do not spawn a semantic contract-builder agent,
construct a Source Unit Inventory, infer `NORM-*` obligations, or reopen ADR/wiki/Decision
prose to decide what the Spec means.

Narrative-only Spec changes may alter `SPEC_BODY_HASH` while leaving
`SPEC_CONTRACT_HASH` unchanged. Treat contract staleness from exact cell identity, not
from prose wording alone.

## 3. Prove decomposition integrity mechanically

Recover exactly one current `ticket-coverage-manifest:v2` and run the deterministic
coverage check against the exact current contract:

```bash
python -m scripts.spec_contract check-coverage <contract.json> <coverage.json>
```

Require exact:

```text
TICKET COVERAGE: VALID
```

Then verify that every routed destination exists, is parented to the Spec, and that each
open/current ticket carries the same assigned cell IDs and exact inherited CCL addresses.
Closed tickets remain immutable historical evidence.

Do **not** independently rebuild an Architecture/Design Source Inventory or create
`ARCHSRC-*` obligations.

Classify a decomposition problem only as one of:

```text
cell-routing-defect
    an exact current Spec cell is missing, duplicated, stale, or routed incorrectly

contract-gap
    required material behavior appears absent from the current OBL/CCL contract

planning-cell-gap
    required private/test/exclusion work appears absent from IMP/TEST/EXC
```

Routing:

* `cell-routing-defect` -> durable `decomposition-defects:v1` -> `$to-tickets`;
* `contract-gap` or `planning-cell-gap` -> `$to-specs` / governing semantic owner;
* never manufacture a new verification-owned obligation.

A report is a falsifier candidate. Persist only when current evidence establishes the
actual defect.

## 4. Build the bounded verification scope

Use exact cells plus implementation provenance to determine what must be tested/inspected.

The contract denominator is already frozen. Scope discovery answers **where and how to
prove it**, not **what the contract is**.

For every cell, identify enough implementation/evidence surfaces to test the relevant
falsifier:

```text
Cell: <OBL/IMP/TEST/EXC>
Cell hash: <hash>
Current owner ticket(s): <#n | historical>
Implementation/evidence surfaces: <compact set>
Applicable deterministic/test checks: <commands/evidence>
```

Group cells when they share one proof surface. Do not build a second semantic matrix.

### OBL-* proof

Verify the candidate implements the exact CCL assertion set for the cell.

The verifier may derive concrete falsifying runtime states from the typed assertion, but
may not reinterpret an assertion's modality, cardinality, vocabulary closure, temporal
meaning, authority, or persistence contract.

### IMP-* cells

Verify the exact private/mechanical obligation is realized. If the implementation uses a
materially different private mechanic that remains implementation-equivalent and the
cell no longer describes reality, reconcile the Spec through `$to-specs` rather than
pretending the stale planning cell passed.

### TEST-* cells

Verify the required proof exists and exercises the intended exact contract behavior.
Passing a test that does not falsify the assigned behavior is insufficient.

The proof must preserve contract strength. A TEST cell does not independently forbid a
state that the assigned OBL/CCL contract permits. In particular, when CCL permits a feature
as one measure but forbids it from becoming the universal/sole semantic or authority, the
proof must distinguish those states; it may not reject the feature merely because it exists
as a field, property, helper, or derived value.

### EXC-* cells

Verify the candidate did not introduce the excluded behavior when that exclusion is
observable from the changed implementation. Do not create implementation work merely to
"implement" an exclusion.

## 5. Run applicable technical and repository gates

Run the smallest complete set of current mandatory gates whose input universe includes
the candidate, including as applicable:

* Ruff / formatting;
* Mypy;
* selected pytest scopes, after the repository Pytest Service Preflight;
* migration/database lifecycle checks;
* architecture/static invariant checks;
* deduplication and other explicitly applicable repository gates;
* wiki synchronization/validation when current changes require it.

Use `uv run --locked` for project-declared tools as required by `AGENTS.md`.

Reuse still-valid candidate-bound evidence. After a mutation rerun only checks whose
inputs may have changed.

### Technical-gate causality and default-branch inheritance

The fixed Spec baseline is immutable lineage/contract history. It is **not** sufficient by
itself to attribute repository technical debt to a long-lived Spec branch.

Before path-scoped quality gates or differential repository gates, fetch current default
branch state and build the exact attribution manifest:

```bash
git fetch origin main
python .agents/skills/verify-spec/scripts/verify_spec_attribution.py build \
  --repo . \
  --default-ref origin/main \
  --candidate-ref HEAD \
  --output <verify-spec-attribution.json>
```

Require exact:

```text
VERIFY-SPEC ATTRIBUTION: VALID
```

Bind all technical-gate causality to that manifest and the exact stable candidate HEAD.

For Ruff, formatting, Mypy, and other path-addressable technical failures:

* failures on `candidate_attributable_paths` are candidate failures and may block PASS;
* failures confined to branch-side paths whose exact candidate blobs are listed in
  `inherited_default_equivalent_paths` are inherited upstream/default-branch failures;
* failures on default-branch-only paths that the candidate did not change are likewise
  unrelated to this Spec candidate;
* operational/tooling failure to execute a mandatory gate remains blocking regardless of
  attribution.

For whole-repository relational scanners such as Arid/JSCPD, invoke `$deduplicate-code` in
its current `spec-differential` mode and supply the same attribution manifest. Scanner scope
remains whole-repository; candidate blocking/repair attribution follows that skill's current
rules.

An inherited/default-equivalent technical finding is an `unrelated failure`: report it with
causality and continue verification when the applicable candidate gate is otherwise green.
Do not turn historical Spec-baseline distance into Spec-owned cleanup. Conversely, a path
that diverges from current default branch remains candidate-attributable even when it is a
workflow/control-plane path; do not use this rule to hide actual branch-local divergence.

After any candidate mutation, rebuild this attribution manifest because exact candidate
identity changed.

## 6. Repair only owned implementation failures

`$verify-spec` may repair a defect when current authority already determines the correct
behavior and the failure is implementation/test/integration work within the verified
Spec contract.

It may not repair by making a new material semantic decision.

### Contract-strength preservation for verifier-owned repairs

Before changing implementation or tests in response to a verifier finding, independently
admit the finding against the frozen contract:

1. identify the exact cell and, for OBL-backed behavior, exact CCL address;
2. state the concrete hypothetical state the verifier says must fail;
3. prove that state actually violates the exact cell/CCL;
4. challenge the proposed repair with every explicit optional/MAY/permitted state in the
   same contract surface.

If the hypothetical state remains contract-compliant, the closure finding is
**inadmissible verifier strengthening**. Do not mutate the candidate to satisfy it, do not
persist it as a candidate defect, and do not treat that closure verdict as a valid FAIL.
Discard that closure attempt and obtain a fresh independent closure verdict over the same
stable candidate.

A verification-owned test repair is itself a `test/proof-defect` when it rejects a state
that the frozen contract explicitly permits. Relax that proof to distinguish the actual
forbidden state from permitted variants, then rerun only invalidated checks.

On resumed verification, audit verification-owned test/proof repairs made by prior
`$verify-spec` attempts. Candidate-bound evidence from those attempts is reusable only after
those repairs pass this contract-strength preservation check.

Classify failures:

```text
implementation-defect
    repair here, rerun invalidated proof

test/proof-defect
    repair here when the Spec already fixes the behavior

cell-routing-defect
    persist/reroute to $to-tickets

contract-gap / unresolved semantic choice / CCL source conflict
    route to $to-specs / $contract-ledger / governing $wayfinder

unrelated failure
    report with causality; do not silently broaden scope
```

An upstream blocker does not excuse independently correctable verification-owned defects.
Finish safe repairs before handing off when their correctness does not depend on the
unresolved authority.

After any repository mutation:

1. rerun invalidated checks;
2. commit/push under the existing Spec branch rules;
3. require one clean stable exact `HEAD`;
4. rebuild the deterministic Spec contract;
5. rerun exact v2 coverage validation;
6. rebuild the exact verify-spec attribution manifest.

## 7. Independent closure certification

Only after the candidate is stable, dispatch exactly one fresh, non-mutating
`$verify-spec-closure` verifier.

Supply:

* exact Spec/body identity;
* baseline, branch, stable HEAD;
* exact deterministic contract handoff/cells/hashes;
* current v2 coverage manifest and ticket mappings;
* concise implementation evidence index;
* terminal technical/delegated check results;
* prior unresolved verifier findings when this is a retry.

The child independently proves implementation conformance to the **same frozen cell
universe**. It does not rebuild the contract from prose or architecture sources.

Require one terminal:

```text
SPEC CLOSURE: PASS | FAIL
```

and exact candidate/contract identity match before admitting the result. Dispatch or
successful child completion is never itself a verdict.

A closure FAIL is admissible only when every finding includes both:

```text
Contract violation: <exact cell/CCL address + condition violated>
Permitted-state challenge: PASS
```

The parent must independently confirm those claims before repairing the candidate. A
finding whose supposed falsifier is still permitted by the frozen contract is verifier
overreach, not a candidate defect; reject the verdict and do not mutate the candidate.

A valid FAIL returns implementation ownership to this parent. Preserve every admissible
finding as a mandatory retry target until the next fresh verifier classifies it `closed`,
`still-open`, or `superseded-by-explicit-contract-change`.

Every candidate mutation requires a fresh deterministic contract build and fresh closure
verdict. Unchanged evidence may be reused when its exact proof inputs remain valid.

## 8. Attention and final consistency

Before PASS finalization invoke `$attention` over the exact candidate with emphasis on:

* cross-ticket integration failures;
* evidence that a cell was satisfied only on a non-production path;
* accidental material behavior outside the CCL contract;
* contract/decomposition drift;
* stale ticket/coverage bindings;
* repository-wide correctness concerns materially implicated by the candidate.

Attention may expose a blocker. It does not add semantic authority.

Immediately before persisting PASS require:

```text
Stable HEAD: unchanged
Spec contract: VALID
Ticket coverage v2: VALID
Verify-spec attribution: VALID and current
Unresolved exact contract cells: 0
Open verifier findings: 0
Known implementation/test failures: 0
Contract-permitted states rejected by verification-owned tests: 0
Unresolved cell-routing defects: 0
Unresolved contract/planning gaps: 0
Applicable candidate-attributable mandatory technical gates: PASS
```

## 9. Persist the Spec Verification Receipt

Persist one new passing receipt on the parent Spec for the exact candidate:

```markdown
## Spec Verification Receipt

**Status:** passed
**Verified HEAD:** <full SHA>
**Verified Baseline:** <full Spec baseline SHA>
**Branch:** spec-<n>
**Spec Body Hash:** <hash>
**Spec Contract Hash:** <hash>
**Contract cells:** <n>
**Material CCL cells:** <n>
**Implementation cells:** <n>
**Testing cells:** <n>
**Exclusion cells:** <n>
**Ticket Coverage:** v2 valid
**Independent closure:** passed
**Open verifier findings:** 0
**Unresolved decomposition defects:** 0
**Unresolved contract gaps:** 0
**Technical verification:** passed
```

The receipt is evidence bound to that exact candidate and contract. It is not semantic
authority.

A later candidate-semantic mutation invalidates it. A policy-only synchronization may be
reused only under the repository-wide non-semantic workflow-policy synchronization rule
and only when current deterministic contract validation reproduces the receipt-bound
`SPEC_BODY_HASH` and `SPEC_CONTRACT_HASH` as required by that rule.

## 10. Outbound Human Handoff boundary

Every terminal **Human Handoff** from `$verify-spec` uses the shared
`polaris.workflow-handoff/v1` gate. A recommendation, prose instruction, bare downstream
skill command, or statement such as `resume $verify-spec after ...` is **not** a Human
Handoff and does not satisfy a lifecycle terminal condition.

Before generating a handoff, resolve the exact downstream artifact from current durable
state:

* PASS -> `$review-spec` receives the exact current Parent Spec issue;
* `cell-routing-defect` -> `$to-tickets` receives the exact current Parent Spec issue;
* `contract-gap` / `planning-cell-gap` -> `$to-specs` receives the exact current planning
  source for the Parent Spec: its governing Wayfinder when Wayfinder-managed, otherwise its
  exact Independent planning source;
* another semantic/architecture route receives only the exact artifact required by that
  owning workflow's current routing contract.

If no downstream lifecycle owner exists for a genuine operational/environment blocker, do
not invent a Human Handoff. Remain at `$verify-spec` and report the exact blocker and
candidate identity.

Every handoff manifest uses:

```text
schema: polaris.workflow-handoff/v1
boundary: human-lifecycle
durability.verified: true
```

Durability sources must be canonical, unique, and sufficient for a fresh downstream
session to reconstruct all correctness-critical state. Include at minimum the exact current
Parent Spec URL and any additional durable defect/authority artifact required by the route.

`$verify-spec` must use its fail-closed handoff finalizer, which composes the shared
`polaris.workflow-handoff/v1` renderer and validator in one operation:

```bash
python .agents/skills/verify-spec/scripts/verify_spec_handoff.py finalize \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require the command itself to exit zero and emit exact:

```text
WORKFLOW HANDOFF: VALID
```

Only after that exact receipt may `$verify-spec` read `<handoff-output.txt>` and reproduce it
as the user-visible Human Handoff block. The block must match the validated file
**byte-for-byte**.

Do not call `scripts.workflow_handoff generate` and `verify` as separate ad hoc steps from
`$verify-spec`; the skill-owned finalizer exists specifically so `READY` output cannot be
surfaced before validation succeeds. Do not manually reconstruct a handoff and do not emit
a bare `$review-spec`, `$to-tickets`, `$to-specs`, `$architecture-remediation`, or
`$verify-spec` line.

If the finalizer emits `WORKFLOW HANDOFF: INVALID`, returns nonzero, or does not produce the
validated output file, the lifecycle remains at `$verify-spec`. Do not surface `READY` and
do not claim a Human Handoff.

Do not invoke review implicitly.

## Non-goals

`$verify-spec` does not:

* reinterpret Spec narrative prose into acceptance obligations;
* infer new architecture requirements from ADR/wiki/implementation prose;
* create `ARCHSRC-*` or `NORM-*` cells;
* change CCL;
* redesign ticket decomposition;
* let a fresh verifier redefine the contract universe;
* treat Project state as correctness authority.
