---
status: accepted
---

# Assemble Decision Context from durable Evidence bindings

## Context

R3 introduces the first coherent human Investment Decision slice. The architecture already distinguishes Decision Context from Evidence, preserves external factual authority, requires judgment-relative Judgment-Time Availability and use-specific freshness, and requires historical reconstruction without hindsight.

The remaining architectural question is how much of this context becomes durable business truth. Persisting a complete Decision Context snapshot for every judgment would duplicate facts owned by Decisions, Portfolio & Risk, Evidence, Investment Intelligence, Governance, and Learning. At the other extreme, persisting only mutable source references would allow later source changes, retrieval loss, or changed fitness rules to rewrite historical meaning.

## Decision

Decision Context is an assembled, time-specific historical view over canonical domain facts rather than a separately authoritative persisted aggregate.

Material Evidence used by R3 is persisted as durable first-class Evidence observations with opaque identity, source provenance and source-authority attribution, subject/reference identity, observation/acquisition time, applicable as-of/effective time when available, and enough retained representation or immutable verification reference to reconstruct what Polaris actually observed.

Judgment-Time Availability, material use, Evidence role, applicable Freshness Requirement/basis, historical freshness result, and related material qualifications are persisted as judgment-relative Evidence bindings. Availability is tri-state: `AVAILABLE | UNAVAILABLE | UNKNOWN`. Historical freshness is `FRESH | STALE | INDETERMINATE`.

Evidence sufficiency is judgment/use-relative and preserves `SUFFICIENT | INSUFFICIENT | INDETERMINATE`. Missing, unknown, disputed, or indeterminate material requirements are represented as missing support, not fabricated Evidence.

Material Conflicting Evidence remains inspectable through explicit conflicting Evidence roles/bindings to the affected material judgment or claim. R3 does not introduce a generic Evidence-conflict graph.

External specialist systems remain authoritative for facts inside their responsibility domains. Polaris persists what it observed and how that information was used or interpreted; normalization, caching, derivation, or retention do not transfer factual authority to Polaris.

Later-acquired, corrected, or reclassified information may change current support or later evaluation but does not retroactively change what was available, used, fresh, or supportable at an earlier judgment. Historical correction is append-only rather than destructive overwrite.

A Decision Context historical query must separately expose:

1. what actually applied at the requested time; and
2. what information about that context was available to the particular judgment.

Provider breadth, generic ingestion frameworks, R4 governed-use readiness, and R6 Attention ingestion are not part of this decision.

## Rationale

This preserves one owner for each business fact while still making judgment-time Evidence semantics directly reconstructable. It avoids a duplicate context aggregate, avoids turning all acquired information into Evidence, and prevents current source state or later knowledge from rewriting historical judgment support.

The design also keeps the Evidence contract narrow enough for the SPY R3 slice while leaving provider and ingestion mechanisms behind infrastructure ports.

## Considered Options

### Persist complete Decision Context snapshots

Rejected because snapshots would duplicate canonical facts from multiple domains and could become a competing source of historical authority.

### Persist only source references and reconstruct Evidence semantics later

Rejected because mutable or unavailable sources and later changes to fitness rules could rewrite what Polaris actually knew or relied on.

### Persist every acquired information item as Evidence

Rejected because information is not automatically Evidence and this would turn the Evidence boundary into a generic data-ingestion store.

### Persist durable Evidence observations and judgment-relative bindings

Accepted because it preserves provenance, historical judgment semantics, and cross-domain ownership without duplicating complete context.
