# Common-Sense Invariant Hardening Audit

**Status:** Active hardening record  
**Canonical index updated:** 2026-09-08

This file is the canonical entry point for workflow invariant hardening. The detailed record is split so the previously audited doctrine remains byte-stable while later postmortem evidence can extend it without rewriting the historical analysis.

Before modifying or evaluating workflow `SKILL.md` files, read **all** documents below in order:

1. `docs/process/common-sense-invariant-hardening-base.md` — original audit, failure modes, cross-skill principles, audit results, and prior implementation notes.
2. `docs/process/common-sense-invariant-hardening-spec-68-addendum.md` — Spec #68 postmortem evidence and the independent semantic-certification hardening derived from it.
3. `docs/process/common-sense-invariant-hardening-attribution-and-reuse-addendum.md` — generic hardening for change provenance vs semantic ownership, authorized verification scope, conditional/deferred obligation routing, and review-proof invalidation/reuse.
4. `docs/process/common-sense-invariant-hardening-semantic-domain-finality-addendum.md` — generic hardening that makes independently certified semantic closure domains durable under unchanged authority and prevents later review from silently moving the completion boundary.
5. `docs/process/common-sense-invariant-hardening-attention-design-boundary.md` — owner-approved always-on Attention/design-boundary doctrine, including Polaris-wide meta-level Attention and formal workflow checkpoints.
6. `docs/process/common-sense-invariant-hardening-public-domain-naming.md` — public/domain naming as an Attention concern when bounded-context meaning would otherwise be hidden.
7. `docs/process/common-sense-invariant-hardening-attention-propagation-addendum.md` — proactive downstream-contract propagation Attention after material semantic, authority, architecture, vocabulary, or sequencing changes, while preserving the boundary that Attention grants no mutation authority.

Together they are the current hardening record. No document may be used to narrow another.

The governing test remains:

> **Could the agent produce every artifact currently required by the skill and take the authorized transition while the stated reasoning invariant was actually false?**

If yes, the transition remains bypassable.

Current generic hardening principles include:

* Transition-Bound Reasoning;
* Universe Closure;
* Explicit Escape Disposition;
* No Self-Certifying Semantic Transition;
* Nested Universe Closure;
* Certified Invalidation Boundaries;
* Semantic-First Cost Control;
* Local Enforcement;
* Versioned Durable Identity Coherence;
* Preserve Lean Workflows;
* Polaris-Wide Meta-Level Attention;
* Mandate-Bound Structural Change;
* Downstream Contract Propagation Attention;
* independent semantic certification at the earliest candidate-owned completion transition;
* per-obligation evidence entailment;
* production-composition proof when operational behavior depends on composition;
* meaningful falsifier proof for fail-closed claims;
* change provenance must not be substituted for semantic lifecycle ownership;
* verification scope must be explicitly authorized from the active change/impact universe;
* conditional obligations must preserve both trigger state and durable destination;
* clean review proof may be reused only through certifier-approved invalidation boundaries and fail-closed delta analysis;
* independently validated nonterminal review findings are durable transition state: ## Review Finding Continuity them, and every prior finding must receive an explicit terminal disposition before review PASS;
* review Exit must fail closed mechanically against the cumulative finding ledger, with zero unaccounted prior findings and zero unresolved continuity cells;
* independently certified semantic closure domains remain the membership authority for correctly decomposed obligations while their governing authority is unchanged;
* a certified ticket/root domain cannot suppress an explicit upstream architecture/design obligation that `$to-tickets` omitted or misrouted; that condition is a decomposition defect routed back to `$to-tickets`;
* later review may reopen a correctly decomposed closed domain only for an in-domain falsifier, an actual governing-authority change, or an explicit authority contradiction—not by silently adopting a broader plausible interpretation.

**Versioned Durable Identity Coherence** means that a durable hash whose encoding can evolve is not a complete identity unless its encoding/version is persisted with it. Any consequential transition that consumes multiple durable representations of the same semantic contract must mechanically require compatible encodings plus equality of the canonical identity bindings before PASS, publication, review, remediation, or handoff. Matching body text, cell counts, cell-ID sets, routing counts, or other derived subsets may support reconciliation but may never be used to infer equality between different or unversioned contract hashes. A legacy/unversioned identity is explicitly incomparable until the owning workflow rebuilds the current canonical identity and performs an authority-bounded deterministic reconciliation; downstream actors may not self-declare the mismatch harmless.

**Mandate-Bound Structural Change** means that engineering principles govern how authorized work is performed but do not expand its scope. Optional refactors or structural changes to canonical authority artifacts require explicit owner authorization, with a pre-mutation mandate check and post-change authorized-delta reconciliation.

Do not add defect-specific workflow rules until the failure has first been tested against these generic principles and enforced at the earliest authoritative transition owner.
