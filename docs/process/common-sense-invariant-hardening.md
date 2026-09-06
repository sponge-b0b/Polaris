# Common-Sense Invariant Hardening Audit

**Status:** Active hardening record  
**Canonical index updated:** 2026-09-06

This file is the canonical entry point for workflow invariant hardening. The detailed record is split so the previously audited doctrine remains byte-stable while later postmortem evidence can extend it without rewriting the historical analysis.

Before modifying or evaluating workflow `SKILL.md` files, read **all** documents below in order:

1. `docs/process/common-sense-invariant-hardening-base.md` — original audit, failure modes, cross-skill principles, audit results, and prior implementation notes.
2. `docs/process/common-sense-invariant-hardening-spec-68-addendum.md` — Spec #68 postmortem evidence and the independent semantic-certification hardening derived from it.
3. `docs/process/common-sense-invariant-hardening-attribution-and-reuse-addendum.md` — generic hardening for change provenance vs semantic ownership, authorized verification scope, conditional/deferred obligation routing, and review-proof invalidation/reuse.

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
* Preserve Lean Workflows;
* independent semantic certification at the earliest candidate-owned completion transition;
* per-obligation evidence entailment;
* production-composition proof when operational behavior depends on composition;
* meaningful falsifier proof for fail-closed claims;
* change provenance must not be substituted for semantic lifecycle ownership;
* verification scope must be explicitly authorized from the active change/impact universe;
* conditional obligations must preserve both trigger state and durable destination;
* clean review proof may be reused only through certifier-approved invalidation boundaries and fail-closed delta analysis.

Do not add defect-specific workflow rules until the failure has first been tested against these generic principles and enforced at the earliest authoritative transition owner.
