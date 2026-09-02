# Common-Sense Invariant Hardening Audit

**Status:** Active hardening record  
**Canonical index updated:** 2026-09-01

This file is the canonical entry point for workflow invariant hardening. The detailed record is split so the previously audited doctrine remains byte-stable while later postmortem evidence can extend it without rewriting the historical analysis.

Before modifying or evaluating workflow `SKILL.md` files, read **both** documents in order:

1. `docs/process/common-sense-invariant-hardening-base.md` — original audit, failure modes, cross-skill principles, audit results, and prior implementation notes.
2. `docs/process/common-sense-invariant-hardening-spec-68-addendum.md` — Spec #68 postmortem evidence and the independent semantic-certification hardening derived from it.

Together they are the current hardening record. Neither document may be used to narrow the other.

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
* Preserve Lean Workflows;
* independent semantic certification at the earliest candidate-owned completion transition;
* per-obligation evidence entailment;
* production-composition proof when operational behavior depends on composition;
* meaningful falsifier proof for fail-closed claims.

Do not add defect-specific workflow rules until the failure has first been tested against these generic principles and enforced at the earliest authoritative transition owner.
