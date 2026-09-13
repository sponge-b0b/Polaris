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
* receives the immutable Spec contract handoff, exact baseline/branch/HEAD, ownership, and already-executed gate/test evidence;
* independently proves semantic cells rather than accepting parent proof conclusions;
* may read/search/inspect and run narrowly necessary non-mutating checks;
* must not edit repository/tracker/Git state, invoke remediation, or delegate.

Candidate mutation or verifier mutation invalidates the run. Do not emit PASS/FAIL from an invalid run.

## 1. Recover and Bind the Spec Contract

Require exact:

* Spec issue and body identity/hash;
* fixed baseline;
* `spec-<n>` branch;
* stable candidate HEAD;
* deterministic `$spec-contract` manifest and contract hash;
* Spec-owned/Mixed/inherited ownership classifications;
* current architecture impact/authority needed by manifest cells;
* executed deterministic/delegated gate evidence and acceptance-test evidence supplied by `$verify-spec`.

The manifest is the outer acceptance universe. Do not add or remove originating Spec obligations locally.

A newly discovered originating-Spec obligation absent from the deterministic contract is a contract defect and invalidates certification; return it to `$verify-spec` rather than silently expanding the manifest.

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

### PASS

```text
SPEC CLOSURE: PASS
Spec: #<n>
Baseline: <sha>
Branch: spec-<n>
HEAD: <sha>
Spec body hash: <hash>
Spec contract hash: <hash>
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
Spec contract hash: <hash>
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

Certification applies only to the exact baseline, Spec body/contract hashes, branch, HEAD, and authoritative mutable inputs certified.

Any repository repair changes HEAD and makes prior semantic certification stale. Mutable architecture/tracker authority changes may also invalidate affected cells.

Reuse is legal only when an already-independent certifier established an explicit invalidation boundary and deterministic fail-closed delta analysis proves the proof object and evidence remain valid. Otherwise recertify.
