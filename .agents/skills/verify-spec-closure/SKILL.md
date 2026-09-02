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
Nested domains: <None | closed domain manifests>
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

### Nested Universe Closure

For `all`, `every`, `none`, `only`, `complete`, `highest practical`, all profiles, all surfaces, all consumers, or equivalent finite/discoverable domains, materialize and close the nested domain.

Examples:

* profile × applicable rendering/transport seam;
* semantic contract transition × consumer/composition path;
* external response shape × constructor/adapter/schema/transport producer;
* authoritative presentation owner × all required sinks;
* workflow invariant × entry/re-entry/fallback path.

Passing tests over selected files do not establish a different semantic matrix.

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

## 4. Completeness Gate

Continue the bounded Spec scan after semantic failures so the parent receives all independently observable closure defects in one certification attempt.

Before verdict require:

```text
Manifest cells: <n>
proven: <n>
not-applicable: <n>
violated: <n>
unproven: <n>
unchecked: 0
Nested domains required: <n>
Nested domains closed: <n>
Open nested domains: 0
Unproven material assumptions: 0
```

`not-applicable` requires exact originating-Spec authority, normally an Out of Scope or explicit exclusion cell.

Any `violated`, `unproven`, `unchecked`, incomplete nested domain, or unproven material assumption blocks PASS.

## 5. Verdict

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
Manifest: <n>; proven <n>; not-applicable <n>; violated <n>; unproven <n>; unchecked 0
Findings:
1. <cell / exact requirement / falsifier or missing proof / current evidence / correction needed>
...
```

Return the verdict to `$verify-spec`. Do not repair or persist a Spec Verification Receipt.

## 6. Binding and Reuse

Certification applies only to the exact baseline, Spec body/contract hashes, branch, HEAD, and authoritative mutable inputs certified.

Any repository repair changes HEAD and makes prior semantic certification stale. Mutable architecture/tracker authority changes may also invalidate affected cells.

Reuse is legal only when an already-independent certifier established an explicit invalidation boundary and deterministic fail-closed delta analysis proves the proof object and evidence remain valid. Otherwise recertify.
