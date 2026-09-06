# Certified Semantic Domain Finality Hardening Addendum

**Status:** Active process hardening record  
**Date:** 2026-09-06  
**Governing record:** `docs/process/common-sense-invariant-hardening.md`

## Purpose

This addendum closes a convergence loophole that remains even after universe-closure and review-proof-reuse hardening:

> A later semantic actor can accept the same unchanged authority, choose a broader membership interpretation than a previously certified closure domain, and convert that reinterpretation into new Blocking remediation.

That failure produces non-monotonic lifecycle progress. A verifier can certify a bounded domain complete, remediation can close it, and a later reviewer can move the boundary outward without any change to the governing contract.

The rule below is generic. It does not name a particular Spec, root, language construct, API family, repository path, or historical defect.

## Core Invariant — Certified Semantic Domain Finality

> **When an independent semantic completion transition certifies a material domain as closed, that domain membership interpretation is durable while its governing authority is unchanged. Later actors may challenge correctness inside the certified domain, but they may not silently enlarge the domain and turn the enlargement into ordinary remediation.**

A certification does **not** make implementation behavior unquestionable. It freezes the semantic membership boundary that the completion transition used.

This distinction is mandatory:

```text
frozen membership boundary
        ≠
proof that every member is forever correct
```

A later actor may still find:

* a regression of an in-domain member;
* a previously missed falsifier that already satisfies the frozen membership predicate;
* evidence that governing authority materially changed after certification.

Those can reopen work normally.

A later actor may not create current remediation merely because it can imagine or discover another adjacent/sibling/alternate candidate that the frozen predicate did not include.

## Transition State — Certified Closure Domain

For every material finite/discoverable semantic domain whose closure contributes to PASS, the independent completion certifier must preserve a compact durable record:

```text
Certified Closure Domain: <stable domain ID>
Parent claim/root: <acceptance cell / Spec cell / Root Blocker>
Authority identity: <exact durable source identities/hashes when available>
Membership predicate: <what makes a candidate a member>
Dimensions / authoritative source sets: <bounded sets or sources>
Closure criterion: <expected count or independently checkable open-world criterion>
Expected/generated/inspected/dispositioned: <counts when finite>
Material out-of-domain boundary observations: <concise families/candidates when needed to make the edge explicit>
Finality: frozen-under-unchanged-authority
```

This is transition state, not private reasoning.

PASS is illegal when a required material domain was used to establish semantic completeness but its closure boundary cannot be durably recovered.

## Later Domain Challenge Reconciliation

Before a later review/remediation transition may reopen a previously satisfied root/cell from a proposed new candidate, it must reconcile that candidate against the latest applicable certified closure domain.

Use:

```text
Candidate: <finding surface/member>
Prior certified domain: <ID/reference>
Prior authority identity: <identity>
Current authority identity: <identity>
Authority changed: yes | no
Membership under frozen predicate: in-domain | out-of-domain | ambiguous
Exact explicit authority contradiction to frozen predicate: <None | exact clause/source>
Disposition:
  in-domain-falsifier
  authority-changed-domain-stale
  closure-authority-defect
  domain-expansion
```

### `in-domain-falsifier`

The candidate satisfies the frozen membership predicate. A current defect/regression may become Blocking normally.

The fact that prior verification passed is process provenance, not suppression authority.

### `authority-changed-domain-stale`

The governing Spec/root/architecture/contract authority materially changed after certification. The prior domain is stale for the affected claim. Rebuild and certify the domain under the new authority before closure.

### `closure-authority-defect`

Unchanged durable authority contains an **explicit, mechanically identifiable contradiction** to the frozen membership predicate or source set—for example, an exact enumerated member/source clause was omitted even though the certification claimed that exact enumeration as authoritative.

This is a semantic-certification integrity failure. It does not silently become current implementation remediation. Halt the affected lifecycle boundary and require explicit authority/domain reconciliation. Preserve the implementation observation, but do not authorize `$to-tickets` from it until the authoritative domain conflict is resolved.

A broader plausible reading, lexical sibling, thematic similarity, implementation adjacency, or reviewer preference is **not** an explicit authority contradiction.

### `domain-expansion`

The candidate does not satisfy the frozen predicate, current authority is unchanged, and no explicit authority contradiction invalidates the frozen domain.

The candidate is non-actionable for the current closed domain. Preserve it as a domain-expansion observation; it may become Advisory, future planning input, workflow-hardening evidence, or owner-directed new scope. It cannot reopen the satisfied root or create current remediation by itself.

### Ambiguous membership

If the old domain record is malformed or membership cannot be resolved, do not silently expand it. Treat the situation as certification/process-integrity debt and require explicit reconciliation. The ambiguity itself does not authorize implementation remediation.

## Root and Review Convergence

Certified semantic domain finality is independent of review-proof reuse.

A missing clean-proof reuse ledger may require a full fresh review, but **full review does not erase previously certified closure-domain boundaries**.

Likewise, a stale review proof because implementation changed does not authorize the reviewer to rebuild a previously closed semantic domain from unchanged English.

For a previously satisfied root:

* `missed prior finding` is legal only for an `in-domain-falsifier`;
* `regression` is legal only for an in-domain behavior that was previously proven and later changed;
* `root-definition gap` may not enlarge a frozen domain under unchanged authority;
* saturation challengers must sweep the frozen domain and any newly admitted members caused by an actual authority change, not a reviewer-invented sibling universe.

A new root remains legal for a genuinely distinct current obligation that was not already governed by a certified root/domain.

## Legacy Certification Compatibility

Historical certifications may predate the explicit `Certified Closure Domain` record.

A historical PASS may be treated as an equivalent frozen domain only when its durable evidence is sufficient to recover all material pieces needed for later membership reconciliation, including:

* exact governing authority;
* an explicit membership predicate or equivalent bounded inclusion rule;
* authoritative dimensions/source sets or closure criterion;
* complete construction/disposition evidence;
* enough explicit boundary evidence to distinguish out-of-domain candidates from omitted in-domain members.

If those cannot be recovered, do not invent a legacy domain from memory or from the implementation. No finality claim is available from that historical certification.

## Earliest Enforcement Points

Apply locally:

* `$verify-ticket-closure` — freeze every material ticket/root closure domain at semantic PASS;
* `$review-spec` — reconcile proposed findings against applicable frozen domains before accepting them as Blocking/root-reopening evidence;
* `$review-spec-remediation` — consume only findings that survived domain-finality reconciliation; never turn a domain-expansion observation into a `root-definition gap`;
* future semantic completion/review skills that create/consume bounded certified domains should adopt the same pattern at their own transition boundary.

Do not build a universal helper that replaces local transition ownership.

## Non-Goals

This hardening does not:

* claim prior certification makes implementation permanently correct;
* suppress regressions or missed falsifiers that were already inside a certified domain;
* prevent explicit authority changes from expanding or replacing a domain;
* make an incorrect explicit enumeration immortal when unchanged authority mechanically contradicts it;
* turn every newly imagined edge case into a process blocker;
* require private chain-of-thought persistence;
* encode historical defect families into workflow policy.

The goal is monotonic semantic progress: exhaustive certification remains adversarial, but the definition of a completed domain cannot move merely because a later actor reads unchanged broad language more expansively.