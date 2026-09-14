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

Before a later review/remediation transition reopens a previously satisfied root/cell from a proposed candidate, distinguish **upstream decomposition integrity** from **downstream semantic-domain finality**.

### Upstream decomposition takes precedence

A ticket/root Certified Closure Domain freezes membership only inside the implementation obligation that was correctly decomposed to that ticket/root.

If current governing architecture/design contains a material implementation obligation that is absent from, incompletely represented by, or misrouted in the current parent-Spec Architecture/Design Obligation Disposition Manifest or ticket mapping, the condition is a **decomposition defect**.

A historical ticket/Spec PASS cannot suppress that upstream obligation and does not need to be rewritten before forward remediation.

Route the defect to the current `$to-tickets` source owner:

* no active conventional Spec Review remediation owner → canonical `DD-*` record on the parent Spec → `$to-tickets #<Spec>`;
* active conventional Spec Review remediation owner → canonical `DD-*` record on that Spec Review → `$to-tickets #<Spec Review>`.

`$to-tickets` independently validates the defect report against current architecture/design authority and the parent manifest before creating/reconciling ticket coverage.

### Correctly decomposed semantic domains

When decomposition is complete for the affected obligation, reconcile later candidates against the latest applicable Certified Closure Domain:

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
  explicit-authority-invalidates-prior-domain
  domain-expansion
```

#### `in-domain-falsifier`

The candidate satisfies the frozen membership predicate. A current defect/regression may become Blocking normally. Prior certification is process provenance, not suppression authority.

#### `authority-changed-domain-stale`

The governing Spec/root/architecture/contract authority materially changed after certification. The prior domain is stale for the affected claim. Rebuild and certify the domain under the new authority before closure.

#### `explicit-authority-invalidates-prior-domain`

Unchanged durable authority explicitly contradicts the frozen membership predicate/source set. The prior finality claim is invalid for the affected claim.

If that contradiction proves an architecture/design obligation was omitted or misrouted during decomposition, classify it as `decomposition-defect` and route it to `$to-tickets`.

Otherwise the later current finding may proceed as an ordinary Blocking missed-prior-finding under the explicit authority. Preserve the historical PASS as historical evidence; do not rewrite it.

#### `domain-expansion`

The candidate does not satisfy the frozen predicate, current authority is unchanged, and no explicit authority contradiction invalidates the boundary. Preserve it as non-actionable planning/advisory input; do not reopen the satisfied root merely because a later actor prefers a broader reading.

#### Ambiguous membership

If the old domain record is malformed or membership cannot be resolved, do not silently expand it. Review/closure remains unresolved until current authority can determine the boundary.

This model keeps semantic completion monotonic without letting an erroneous ticket decomposition erase an explicit upstream obligation.

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

* `$to-tickets` — own the complete Architecture/Design Obligation Disposition Manifest and reconcile decomposition defects forward without rewriting closed historical tickets;
* `$verify-ticket-closure` — freeze material semantic domains at PASS only inside correctly decomposed ticket obligations, while independently checking architecture/design decomposition integrity;
* `$verify-spec` / `$verify-spec-closure` — independently compare the integrated Spec's bounded architecture/design authority against the shared parent manifest and route decomposition defects back to `$to-tickets`;
* `$review-spec` — perform the same decomposition challenge as the final defense, then reconcile correctly decomposed findings against applicable frozen semantic domains;
* `$review-spec-remediation` — preserve decomposition defects for `$to-tickets` and consume ordinary findings that survived semantic-domain finality; never turn a domain-expansion observation into a `root-definition gap`;
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