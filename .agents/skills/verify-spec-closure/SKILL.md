---
name: verify-spec-closure
description: Independently certify or reject the semantic Spec contract at the exact stable HEAD prepared by `$verify-spec`. This is a fresh non-mutating leaf verifier; `$verify-spec` retains orchestration, gates, repairs, and receipt persistence.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Verify Spec Closure

Independently certify or reject semantic completion of the exact stable Spec candidate prepared by `$verify-spec`.

This skill exists to prevent `$verify-spec` from authorizing its own semantic PASS after it has also selected gates, interpreted failures, repaired the candidate, and assembled proof evidence.

It is not `$review-spec`:

* `$verify-spec-closure` asks whether the integrated candidate satisfies the authoritative Spec contract;
* `$review-spec` remains the later independent Standards / Spec / Architecture adversarial review and convergence layer.

## Conditional Claim Discipline

This section is authoritative for any manifest cell whose requirement contains a material condition, trigger, phase, future event, or other predicate controlling when its consequent applies.

Preserve the source condition exactly. Do not silently transform:

```text
when X occurs, Y must happen
```

into:

```text
build a mechanism now that guarantees Y for every future X
```

unless the originating Spec itself requires that present mechanism/pre-provisioning.

For every materially conditional cell, record concise proof state:

```text
Condition/trigger: <exact authoritative trigger>
Current trigger state: active | inactive | ambiguous
Trigger evidence: <current evidence>
Deferred routing evidence: <durable destination/owner | None>
```

Apply these rules:

* `active` → certify the consequent normally; current behavior must satisfy the cell;
* `inactive` → current implementation of the consequent is not required unless the source explicitly requires pre-provisioning;
* an inactive cell may be `not-applicable` for the current candidate only when the originating source establishes the condition and durable decomposition/lifecycle evidence preserves a future destination/owner for the obligation;
* the preferred routing evidence is the parent Spec's current `Ticket Coverage Manifest` row with a `deferred-conditional` disposition; equivalent durable authority is acceptable only when it clearly names the future lifecycle/verification destination;
* `inactive` without durable future routing is `unproven`, not silently complete, because the obligation would otherwise escape by omission;
* `ambiguous` trigger state is `unproven`;
* when the trigger later becomes active, any prior inactive/not-applicable proof is stale by definition and may not be reused;
* the verifier must not invent CI, automation, project policy, a new workflow owner, or another durable mechanism merely to make an inactive conditional cell provable.

This extends `not-applicable`; it does not weaken Out-of-Scope handling. A conditional inactive disposition still requires exact originating-Spec authority plus durable routing evidence.

## Invocation Integrity

Execute only in one genuinely fresh non-mutating verifier subagent dispatched by the `$verify-spec` parent at a stable exact HEAD.

The verifier:

* did not implement or repair the candidate;
* receives the immutable Spec contract handoff, its invocation-local `CONTRACT_HANDOFF_DIGEST`, exact baseline/branch/HEAD, ownership, and already-executed gate/test evidence;
* independently proves semantic cells rather than accepting parent proof conclusions;
* may read/search/inspect and run narrowly necessary non-mutating checks;
* must not edit repository/tracker/Git state, invoke remediation, or delegate.

Candidate mutation or verifier mutation invalidates the run. Do not emit PASS/FAIL from an invalid run.

`CONTRACT_HANDOFF_DIGEST` is SHA-256 of the exact ephemeral handoff bytes supplied by `$verify-spec` for this certification transaction. It is transport binding only: it is not semantic identity, is not persisted as contract authority, and must never be compared across independent `$spec-contract` builds.

## Cumulative Retry Semantics

This section is authoritative for Attempt 2 or later after a valid saturated `SPEC CLOSURE: FAIL`. It supersedes later wording that can be read as requiring a fresh verifier to rebuild an unchanged semantic universe, or as permitting reuse of an old verdict instead of obtaining a fresh one.

A genuinely fresh verifier is independent from candidate authorship, parent repair, and prior verifier execution; it is **not** a blank-slate verifier.

Every retry still requires a fresh isolated `$spec-contract` build for the exact current stable HEAD before this verifier is dispatched. Never reuse a prior `CONTRACT_HANDOFF`, `CONTRACT_HANDOFF_DIGEST`, or prior verdict across a candidate mutation. The parent may supply prior retry state only **after** the fresh current contract build has returned validly; prior retry state must never be exposed to or used by the fresh contract builder.

For Attempt 2 or later, recover the exact prior saturated verifier result and its `Cumulative Spec Retry State` before reconstructing semantic state. Compare the current fresh structural contract identity and current mutable authority with the prior retry bindings. When the governing Spec body/structural contract and relevant authority remain unchanged, reuse rather than rediscover:

* stable manifest-cell identities and authoritative obligation mappings;
* architecture/design decomposition construction already saturated by an independent prior verifier;
* domain-construction manifests, membership predicates, authoritative source sets, member inventories, and independently recoverable closure criteria;
* prior out-of-domain boundary observations;
* every prior finding and exact falsifier;
* explicit proof-dependency mappings sufficient to determine which prior dispositions a repair invalidated.

Freshness does not invalidate those authority-derived artifacts merely because a different verifier actor is running.

A prior cell, nested-member, decomposition, or domain-membership **disposition** is reusable only when all material inputs to that proof remain unchanged, including:

* governing authority and current structural contract identity;
* candidate-dependent evidence inputs;
* implementation/composition surface on which the proof depends;
* relevant runtime, tracker, configuration, dependency, and conditional-trigger state.

Determine invalidation from the actual candidate delta plus the proof dependencies preserved in the prior retry state. Re-prove every cell/domain/member whose predicate could materially be affected by the repair or its blast radius. When uncertainty remains, invalidate and re-prove the smallest semantic surface that resolves the uncertainty.

Every prior finding is a mandatory regression target. Attempt N+1 must explicitly classify each earlier unresolved finding as:

```text
closed | still-open | superseded-by-explicit-authority-change
```

Candidate mutation alone can never make a prior finding disappear. `closed` requires direct current evidence against the exact prior falsifier plus any materially adjacent state exposed by the repair. `superseded-by-explicit-authority-change` requires exact durable authority identifying the change; a different implementation or verifier opinion is not supersession.

After reconciling prior findings, independently sweep the repair blast radius and every acceptance/decomposition obligation whose proof was invalidated. The final verdict remains a verdict over the **whole current Spec candidate**. Reusing unchanged semantic construction is evidence economy, not partial certification.

If prior durable retry state lacks enough authority, construction, inventory, or proof-dependency detail for safe reuse, reconstruct only the missing or ambiguous state. Do not rebuild an unchanged universe merely because the verifier actor is fresh, and do not pretend reuse is valid when the durable state is insufficient.

On Attempt 2 or later, the Section 4 saturation witness additionally requires:

```text
Prior-attempt findings: <n>
closed: <n>
still-open: <n>
superseded-by-explicit-authority-change: <n>
Reused prior dispositions with unresolved invalidation: 0
```

A PASS requires `still-open: 0`. A FAIL may retain prior findings as `still-open`, but must carry them forward together with every new independently actionable finding.

Every valid saturated FAIL that can lead to another attempt must also return this compact durable state:

```text
Cumulative Spec Retry State:
Prior candidate HEAD: <sha>
Prior Spec body hash: <hash>
Prior Spec contract hash: <hash>
Authority identity: <durable authority/source identities proving the acceptance/decomposition boundary>
Manifest identity: <stable cell/source-unit identities sufficient to reconcile a fresh current contract>
Architecture/decomposition state: <stable obligation/manifest identities and closure state sufficient for reuse>
Domain construction state: <stable ND identities plus authority, membership predicate, generation/closure mechanism, and recoverable member inventory/criterion>
Candidate-dependent proof dependencies: <cell/ND/member groups -> implementation/evidence/runtime/tracker/configuration dependencies>
Reusable prior dispositions: <cell/ND/member groups whose dependencies were unchanged at the end of this attempt>
Mandatory falsifiers for next attempt: <finding IDs / exact falsifiers>
```

Counts alone are insufficient. When reuse depends on a finite member inventory, preserve that inventory itself or an independently recoverable deterministic identity/manifest for it.

> **Spec verifier attempts are cumulative in integrated evidence and adversarial knowledge, but independent in verdict. Rebuild the current contract binding; do not rediscover an unchanged semantic universe. Re-certify the candidate.**

## 1. Recover and Bind the Spec Contract

Require exact:

* Spec issue and body identity/hash;
* fixed baseline;
* `spec-<n>` branch;
* stable candidate HEAD;
* deterministic `$spec-contract` manifest, deterministic V2 structural identity rows, and contract hash;
* invocation-local `CONTRACT_HANDOFF_DIGEST` for the exact handoff bytes supplied by the parent;
* Spec-owned/Mixed/inherited ownership classifications;
* current architecture impact/authority needed by manifest cells;
* the current parent-Spec `Ticket Coverage Manifest`, including the Architecture/Design Obligation Disposition Manifest and exact relevant ticket `Architecture obligations` mappings;
* executed deterministic/delegated gate evidence and acceptance-test evidence supplied by `$verify-spec`.

The manifest is the outer acceptance universe. Do not add or remove originating Spec obligations locally.

A newly discovered originating-Spec obligation absent from the deterministic contract is a contract defect and invalidates certification; return it to `$verify-spec` rather than silently expanding the manifest.

## Architecture / Design Decomposition Integrity

Before certifying Spec cells, independently challenge the complete bounded architecture/design decomposition used by the integrated candidate.

Re-derive materially applicable architecture/design obligations from the exact governing sources supplied by `$verify-spec`; do not accept the parent's manifest counts or dispositions as semantic proof. Compare the independently derived set with the current parent-Spec Architecture/Design Obligation Disposition Manifest and relevant ticket `Architecture obligations` mappings.

Record:

```text
Architecture/design obligations: <n>
Manifest rows: <n>
Missing: <n>
Ambiguous: <n>
Misrouted: <n>
Implementation obligations without durable ticket coverage: <n>
Ticket mappings inconsistent with manifest: <n>
```

A missing, ambiguous, or misrouted architecture/design obligation is an independently actionable finding with:

```text
Finding classification: decomposition-defect
Finding owner: $to-tickets
Governing source: <exact durable source + section>
Missing/misrouted obligation: <requirement>
Current manifest state: absent | incomplete | misrouted
```

Continue the bounded semantic sweep so the parent receives the complete independently observable failure set. The finding blocks PASS; the leaf remains non-mutating and does not edit tickets or manifests.

## 2. Per-Cell Semantic Certification

Independently disposition every manifest cell:

```text
Spec cell: <US-* | ID-* | TD-* | OOS-* | other stable cell>
Claim: <exact manifest requirement>
Domain: <authoritative domain>
Domain authority: <durable source(s) defining membership>
Membership predicate: <what makes a candidate part of this domain>
Nested domains: <None | domain construction manifests>
Predicate: <what must be true>
Falsifier: <concrete state that makes the claim false>
Evidence: <current evidence excluding the falsifier>
State: <unchecked | proven | violated | unproven | not-applicable>
```

This is concise proof state, not private reasoning.

### Exact entailment

A proof may cover multiple cells only when the same predicate/evidence genuinely entails every mapped requirement.

Do not map a narrower externally visible claim to a broader upstream architectural fact unless the evidence proves the externally visible claim itself.

Do not infer operational behavior from component capability when canonical production composition is material.

Ask for each cell:

> Could every cited check pass while this exact Spec requirement is still false?

If yes, it is not proven.

### Authoritative domain membership

Before proving any material cell whose domain can produce finite, discoverable, alternate, sibling, or adversarial candidates, bind the boundary that determines which candidates belong:

```text
Domain authority: <durable source(s) that define the boundary>
Membership predicate: <what makes a candidate a member>
```

Derive membership from durable authority such as the exact manifest requirement, normative definitions, explicit enumerations, and authoritative composition/ownership boundaries. Do not derive it from changed files, implementation structure, existing tests, known defects, lexical similarity, subsystem proximity, or verifier intuition.

Discovery may reveal a candidate. Discovery does not create authority.

If a material candidate's membership cannot be resolved from current authority, the candidate is `ambiguous` and the affected cell/domain remains `unproven`; do not silently widen or narrow the claim.

### Nested Universe Closure

For `all`, `every`, `none`, `only`, `complete`, `highest practical`, all profiles, all surfaces, all consumers, or equivalent finite/discoverable domains, materialize and close the nested domain.

Examples:

* profile × applicable rendering/transport seam;
* semantic contract transition × consumer/composition path;
* external response shape × constructor/adapter/schema/transport producer;
* authoritative presentation owner × all required sinks;
* workflow invariant × entry/re-entry/fallback path.

Each nested domain carries its own authority, membership predicate, and Domain Construction Manifest:

```text
Domain: ND-<n>
Authority: <durable source>
Membership predicate: <predicate>
Expected / closure criterion: <n | criterion>
Generated: <n>
Inspected: <n>
Dispositioned: <n>
Remaining authoritative members: 0
Construction complete: yes
Sweep complete: yes
```

For a finite domain, expected/generated/inspected/dispositioned counts must reconcile exactly. For a discoverable/open-world domain, the declared exhaustive mechanism must satisfy its closure criterion.

Passing tests over selected files do not establish a different semantic matrix. `unchecked = 0` over an incompletely constructed domain is not proof.

A parent Spec cell becoming `violated` does not close, waive, or disposition the rest of its nested domain. Continue generating, inspecting, and dispositioning every remaining authoritative member so the same run accumulates all independently observable failures.

When the nested universe cannot be established exhaustively, mark the cell `unproven`.

### Production-path proof

If the Spec claim says behavior is observable, emitted, persisted, enforced, routed, or available in the application, inspect the canonical production path required for that behavior.

A class supporting telemetry is not proof that the production DI path wires telemetry. A renderer receiving metadata upstream is not proof that it exposes that metadata externally.

Apply this principle generically to the relevant composition mechanism.

### Negative/fail-closed proof

For negative obligations, derive meaningful falsifying states and inspect/test the responsibility of the boundary being certified.

Do not certify `cannot bypass` using only well-formed canonical-path examples. Do not make thin transports rerun upstream policy when their responsibility is only to refuse an inconsistent or non-presentable result.

## 3. Use Parent Gate Evidence Without Trusting Parent Conclusions

The `$verify-spec` parent owns execution of deterministic/delegated gates, service preflight, acceptance tests, observed-failure disposition, and repair.

Treat those native terminal results as evidence of exactly what they mechanically establish.

Do not rerun broad Ruff/Mypy/pytest/dedup/wiki gates merely to duplicate `$verify-spec`.

Run only narrow non-mutating inspection/checks needed to determine semantic entailment or close a bounded domain not established by existing evidence.

A parent assertion that a cell is proven is not evidence.

## 4. Completeness and Failure Saturation

Continue the bounded Spec scan after semantic failures so the parent receives all independently observable closure defects in one certification attempt.

A first falsifier changes **verdict polarity** to FAIL; it does not establish **verification completion**. PASS and FAIL require the same universe-construction and sweep-saturation gates. A violated parent cell remains open for search until every authoritative nested member and sibling has been generated and dispositioned.

Before either verdict require:

```text
Manifest cells: <n>
proven: <n>
not-applicable: <n>
violated: <n>
unproven: <n>
unchecked: 0
Nested domains required: <n>
Domain construction manifests complete: <n>/<n>
Nested domains closed: <n>
Open nested domains: 0
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
Architecture/design missing obligations: 0
Architecture/design ambiguous obligations: 0
Architecture/design misrouted obligations: 0
Architecture implementation obligations without durable ticket coverage: 0
```

Preserve a compact Domain Membership Manifest for inspected candidates:

```text
Candidate: <surface/path/member>
Parent: <Spec cell | nested-domain cell>
Domain authority: <durable source>
Membership predicate: <predicate>
Disposition: in-domain | out-of-domain | ambiguous
Evidence / authority: <why the disposition follows>
```

Apply dispositions mechanically:

* `in-domain` → the candidate becomes part of the cell/nested-domain sweep and must be dispositioned before verdict;
* `out-of-domain` → preserve the observation, but it does not become a Spec obligation merely because it is adjacent, similar, or hypothetically exploitable;
* `ambiguous` → the affected cell/domain remains `unproven`; do not silently broaden durable authority.

`not-applicable` requires exact originating-Spec authority, normally an Out of Scope or explicit exclusion cell.

Every independently actionable defect discovered during the saturated sweep must appear as a finding even when several findings violate the same Spec cell. Derivative cell failures may reference one root defect rather than duplicating it, but they do not replace independently actionable findings.

Any `violated`, `unproven`, `unchecked`, incomplete domain construction, incomplete nested sweep, ambiguous/undispositioned domain candidate, unexplored authoritative sibling, or unproven material assumption blocks PASS. Any incomplete construction or sweep also blocks FAIL; return an invalid/incomplete certification result rather than a partial failure set.

## 5. Verdict

Return one semantic verdict only after Section 4 saturation is complete.

Every consumable verdict must echo the exact `CONTRACT_HANDOFF_DIGEST` received from `$verify-spec`. A missing or changed digest makes the result invalid/incomplete rather than PASS or FAIL.

### PASS

```text
SPEC CLOSURE: PASS
Spec: #<n>
Baseline: <sha>
Branch: spec-<n>
HEAD: <sha>
Spec body hash: <hash>
Spec contract encoding: V2
Spec contract hash: <hash>
Contract handoff digest: <sha256>
Manifest: <n>; proven <n>; not-applicable <n>; violated 0; unproven 0; unchecked 0
Nested domains: <n>; closed <n>; open 0
Domain construction: <n>/<n> complete; remaining authoritative members 0
Domain membership: <n>; in-domain <n>; out-of-domain <n>; ambiguous 0
Independent actionable findings: 0
Coverage:
- <cell IDs grouped only when identical evidence truly entails each claim> — <compact evidence>
```

### FAIL

```text
SPEC CLOSURE: FAIL
Spec: #<n>
Baseline: <sha>
Branch: spec-<n>
HEAD: <sha>
Spec body hash: <hash>
Spec contract encoding: V2
Spec contract hash: <hash>
Contract handoff digest: <sha256>
Manifest: <n>; proven <n>; not-applicable <n>; violated <n>; unproven <n>; unchecked 0
Nested domains: <n>; closed <n>; open <n>
Domain construction: <n>/<n> complete; remaining authoritative members 0
Domain membership: <n>; in-domain <n>; out-of-domain <n>; ambiguous 0
Independent actionable findings: <n>
Findings:
1. <cell / exact requirement / falsifier or missing proof / current evidence / correction needed>
...
```

Do not emit PASS or FAIL when construction/saturation is incomplete. Return an invalid/incomplete certification result to `$verify-spec` instead.

Return the verdict to `$verify-spec`. Do not repair or persist a Spec Verification Receipt.

## 6. Binding and Reuse

Certification applies only to the exact baseline, Spec body hash, `Spec contract encoding: V2`, Spec contract hash, branch, HEAD, authoritative mutable inputs, and exact contract handoff bytes certified. Echo `CONTRACT_HANDOFF_DIGEST` unchanged in the verdict so the parent can bind finalization to those same bytes.

The digest is invocation-local transport binding only. It does not replace `SPEC_CONTRACT_HASH`, does not become durable contract identity, and must never be compared across independent `$spec-contract` builds.

Any repository repair changes HEAD and makes prior semantic certification stale. Mutable architecture/tracker authority changes may also invalidate affected cells.

Reuse is legal only when an already-independent certifier established an explicit invalidation boundary and deterministic fail-closed delta analysis proves the proof object and evidence remain valid. Otherwise recertify.
