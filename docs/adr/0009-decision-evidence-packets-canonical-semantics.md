---
status: accepted
---

# 0009. Canonical Decision Evidence Packet Semantics

Date: 2026-07-29

## Context and Problem Statement

Enhanced and Vigilant Polaris outputs can influence risk, recommendations,
reporting, RAG answers, evaluation gates, future MCP responses, or other
AI-adjacent decision surfaces. Those outputs need a canonical evidence packet
that lets operators answer three different questions without conflating them:

1. Can Polaris reconstruct the packet provenance from durable platform records?
2. Does each material claim cite enough support to be output-ready?
3. Is the cited support acceptable, or is correctness blocked by rejected or
   unresolved conflicting evidence?

Prior remediation work implemented typed decision-evidence packets,
claim-reference bindings, reconstruction validation, retained support snapshots,
materiality tiers, and output-boundary checks. This ADR records the canonical
semantics so future report, recommendation, RAG, evaluation, and transport work
uses the implemented contract instead of recreating an interface-specific
evidence store.

## Decision Outcome

Chosen option: "PostgreSQL-backed decision evidence packets with separated provenance reconstruction, claim support, and correctness readiness", because it preserves one canonical evidence contract while allowing output boundaries to fail closed for the exact missing or invalid decision-evidence dimension.

`DecisionEvidencePacket` is the canonical typed packet for Enhanced and Vigilant
risk-authority outputs that require durable decision evidence. The packet binds:

- the producing output identity and `RiskAuthorityContract`;
- typed material claims;
- supporting, conflicting, constraint, uncertainty, and limitation evidence;
- durable reconstruction references;
- retention and support-snapshot policy; and
- schema-versioned packet constraints.

The packet audit record persisted in PostgreSQL is the durable authority for
packet identity, claim/evidence bindings, reconstruction identifiers, authority
metadata, retention metadata, and redacted support snapshots. Workflow node
outputs and completed-run archives are runtime evidence. RAG chunks, Qdrant
vectors, Neo4j graph records, rendered files, report artifacts, and linked
external artifacts are projections or artifacts unless explicitly curated through
an owning PostgreSQL record.

No report renderer, recommendation projector, RAG interface, MCP transport, or
other edge component may create a parallel evidence store or declare rendered text
to be the source of truth for decision support.

## Packet semantics

A decision evidence packet separates claim text from evidence and reconstruction
semantics:

- `MaterialClaim` records the claim, its materiality tier, and claim/evidence
  bindings.
- `EvidenceReference` records support, conflict, constraints, uncertainties,
  limitations, and rejected evidence without making every citation a claim.
- `ReconstructionReference` records how to rehydrate or verify the durable source
  used by a packet.
- `EvidenceClaimReference` is the reference-only presentation binding used by
  reports, recommendations, RAG answers, and tool responses. It may repeat claim
  text for display, but it must not copy canonical evidence payloads into the
  presentation layer as a competing authority.

The canonical packet can be serialized, persisted, rehydrated, and validated by
application decision-evidence services. Interfaces consume packet summaries and
claim references; they do not own packet assembly, persistence, reconstruction,
or readiness decisions.

## Materiality tiers and conflict blocking

Polaris recognizes two claim materiality tiers in the canonical packet contract:

| Tier | Semantics | Readiness behavior |
| --- | --- | --- |
| `contextual` | Explanatory, background, or narrative claims that do not gate an Enhanced or Vigilant decision. | Audit unsupported or conflicting context, but do not block output readiness unless the producing contract promotes the claim to `readiness_gating`. |
| `readiness_gating` | Material claims whose absence, unsupported state, or conflict could change a risk, recommendation, report, RAG answer, evaluation gate, or transport response. | Fail closed when required support, reconstruction references, or correctness checks are missing or invalid. |

The material flag is derived from materiality. Readiness-gating claims must have
supporting evidence and reconstruction references before they can cross an output
boundary. Contextual claims may be retained for audit and explanation, but they
must not silently downgrade a material decision claim to avoid readiness checks.

Unresolved material conflicting evidence blocks readiness even when the claim has
supporting evidence. Conflict blocking is a correctness/readiness failure, not a
provenance reconstruction failure. A packet can therefore be fully reconstructable
while still failing output readiness because a material conflict remains
unresolved.

Rejected evidence may not be cited as support for a readiness-gating claim. If a
material claim depends on rejected support, the packet fails closed with an
observable readiness failure rather than treating the rejected evidence as a weak
citation.

## Provenance reconstruction versus claim support

Packet readiness has three independent dimensions:

1. **Provenance reconstruction completeness** — whether the packet can be
   rehydrated and verified from durable reconstruction identifiers, retained
   support snapshots, and canonical platform records.
2. **Claim support completeness** — whether each readiness-gating claim has the
   required support and reconstruction references.
3. **Correctness support completeness** — whether the cited support is allowed
   and no unresolved material conflict blocks the claim.

These dimensions must not be collapsed into a single boolean explanation.
Missing, malformed, stale, substituted, or tampered reconstruction sources are
provenance reconstruction failures. Missing support links or reconstruction
references on a material claim are claim support failures. Rejected support and
unresolved material conflicts are correctness support failures.

A report, recommendation, RAG answer, or future MCP/tool response may describe a
packet as reconstructable only when provenance reconstruction succeeds. It may
claim that a material decision is supported only when claim support and
correctness support both succeed.

## Reconstruction reference coverage and failure behavior

The canonical reconstruction contract covers the durable source kinds needed by
implemented remediation work:

- `completed_workflow_run`
- `workflow_node_output`
- `canonical_domain_record`
- `rag_retrieval_context`
- `rag_citation_context`
- `evaluation_run`
- `evaluation_metric_result`
- `trace_context`
- `linked_artifact`

Reconstruction prefers canonical durable PostgreSQL records and completed-run
runtime evidence. RAG contexts, evaluation records, trace context, and linked
artifacts are used only through their typed reconstruction references and never
become a second source of truth for the business concept they describe.

Per-kind reconstruction behavior is:

| Reference kind | Canonical source | Reconstruction behavior | Failure behavior |
| --- | --- | --- | --- |
| `completed_workflow_run` | Completed-run archive runtime evidence. | Reconstructable from archived completed-run identity. A retained material snapshot may satisfy reconstruction only when the archive record is missing. | Missing archive without a valid retained snapshot, malformed identifiers, or stale run identity fail closed. |
| `workflow_node_output` | Completed-run archive node output. | Reconstructable from archived node output plus content digest. A retained material snapshot may satisfy reconstruction only when the archive node is missing. | Missing archive/node without a valid retained snapshot, substituted node/run identity, or stale digest fail closed. |
| `evaluation_run` | Canonical evaluation run record in PostgreSQL. | Reconstructable from the evaluation run record and provenance digest; retained material snapshots are fallback for missing canonical records. | Missing record without a valid retained snapshot, substituted run identity, or stale digest fail closed. |
| `evaluation_metric_result` | Canonical evaluation metric result attached to an evaluation run. | Reconstructable from the evaluation run snapshot ID, metric result ID, and metric digest; retained material snapshots are fallback for missing canonical metric records. | Missing metric without a valid retained snapshot, substituted run linkage, malformed run snapshot IDs, or stale digest fail closed. |
| `rag_retrieval_context` | Canonical RAG query log metadata retaining retrieved context payloads, or a retained material snapshot. | Reconstructable from the durable query log and retrieved context payload. Validation recomputes the retrieval-context digest from context ID, retrieval route, canonical source lineage, and text rather than trusting only IDs, digests, or source labels. | Missing query/context without a valid retained snapshot, substituted query identity, malformed payloads, or stale context digest fail closed. |
| `rag_citation_context` | Canonical RAG document/chunk records, or a retained material snapshot. | Reconstructable from durable RAG document/chunk lineage. Validation checks source table, source ID, document ID, chunk ownership, and citation digest rather than accepting structural citation IDs alone. | Missing document/chunk without a valid retained snapshot, substituted source lineage/chunk ownership, malformed source IDs, or stale citation digest fail closed. |
| `linked_artifact` | Typed artifact record when the identifier names a canonical artifact; otherwise source-of-truth-labeled audit metadata. | Evaluation artifacts using `evaluation-artifact:<run_id>:<artifact_id>` are reconstructable from canonical evaluation artifact records. Other linked artifacts are audit-only until an owning repository-backed artifact contract is added. | Canonical evaluation artifact refs fail closed on missing artifact, substituted run linkage, or stale digest. Generic audit-only artifact refs must still identify a permitted source of truth and cannot claim reconstructability. |
| `trace_context` | Durable telemetry trace record, or a retained material snapshot. | Reconstructable when a telemetry trace repository is available; otherwise only retained material snapshots can satisfy reconstruction. Validation checks trace record ID, trace ID, and trace digest. | Missing trace without a valid retained snapshot, missing validator, substituted trace identity, malformed trace IDs, or stale trace digest fail closed. |
| `canonical_domain_record` | Source-of-truth-labeled canonical domain record. | Audit-only structural validation until a concrete repository-backed record kind is introduced. New canonical business concepts require first-class typed fields and repository-backed validators before they can claim source-record verification. | Audit-only refs may pass structural validation but cannot claim source-record reconstructability; invalid source-of-truth categories fail closed. |

Failure behavior is fail-closed and observable:

- a missing packet or missing referenced source raises a reconstruction failure;
- malformed reconstruction identifiers are rejected instead of guessed;
- stale references fail when the durable source no longer matches the recorded
  reconstruction identity;
- substituted references fail when the source identity resolves to different
  content or authority metadata than the packet recorded; and
- tampered support snapshots fail digest validation.

Telemetry, structured logs, and reconstruction-failure events must preserve the
packet ID, failed reference IDs, failure type, and traceback where useful for
operator diagnosis. Telemetry failures remain non-fatal to correctly rejected
domain output, but they must not convert a failed reconstruction into an allowed
material claim.

## Retained supporting-evidence snapshots

Readiness-gating support must retain a durable redacted support snapshot or an
equivalent canonical durable source. A `SupportingEvidenceSnapshot` records the
support content needed for later reconstruction, a digest used to detect
tampering, redaction metadata, source identity, and retention metadata.

Snapshots are not hidden chain-of-thought, credentials, or raw authenticated
payload dumps. They are the minimum durable, redacted support content needed to
reconstruct why a material claim was allowed after projections, caches, retrieved
contexts, or linked artifacts have changed.

Reconstruction should prefer canonical durable records when they exist and still
match the packet. If a projection or artifact used for material support is no
longer available, the retained snapshot may satisfy reconstruction only when its
recorded digest and source metadata validate. Missing or tampered snapshots for
material support fail closed.

## Report, recommendation, and RAG output boundaries

Output boundaries enforce packet readiness before material claims leave the
canonical application service layer:

- **Reports** may persist published report records and artifacts only after
  material claims have bound packet, evidence, and reconstruction references.
  Material claims with missing packet references are rejected or withheld; they
  are not persisted as unsupported prose.
- **Recommendations** may project material recommendation explanations only when
  their `EvidenceClaimReference` bindings point back to durable packet support.
  Missing material support links fail closed at the recommendation output
  boundary.
- **RAG answers** assemble evidence packets from typed generated-claim data that
  carries citations, supporting citation IDs, materiality, sanitized context IDs,
  and rejected context IDs. Rendered RAG answer text is presentation output, not
  the claim source of truth and not an extraction source for canonical packet
  claims.

Non-material contextual content can be persisted or displayed with audit
metadata when policy allows it, but it must remain classified as contextual and
must not stand in for a readiness-gating claim.

## Architectural alignment

This decision preserves the Polaris inside-out architecture:

- typed domain packet contracts define the semantics;
- application decision-evidence services own assembly, persistence,
  reconstruction, and readiness checks;
- PostgreSQL remains the durable authority for packet audit records and curated
  claim/evidence bindings;
- completed workflow runs remain runtime evidence rather than domain records;
- workflow outputs become durable report, recommendation, RAG, or evaluation
  records only through explicit typed curation and projection policy;
- Qdrant, Neo4j, rendered reports, caches, retrieved contexts, and linked files
  remain rebuildable projections or artifacts; and
- external transports, including a future MCP server, stay thin over
  Dishka-resolved application services.

No future implementation should add interface-local evidence persistence,
metadata-only canonical fields, best-effort rendered-text claim extraction, or a
second retrieval/ranking/graph store to satisfy decision-evidence readiness.

## Consequences

- Material claims fail closed at output boundaries unless packet support,
  reconstruction references, and correctness checks all pass.
- Operators can distinguish reconstructability from support and correctness when
  triaging packet failures.
- Retained redacted support snapshots keep material claims auditable after
  rebuildable projections or linked artifacts change.
- RAG, reports, recommendations, evaluations, and future tool responses share one
  canonical packet model instead of implementing local evidence semantics.
- New durable decision-evidence concepts require first-class typed fields,
  application persistence, and schema evolution rather than arbitrary metadata or
  interface-owned storage.

## Affected Issues

- #99 — parent remediation work for decision evidence packets
- #102 — add claim materiality tiers and block unresolved material conflicts
- #103 — separate provenance reconstruction readiness from claim support readiness
- #104 — preserve supporting evidence snapshots for retained material claims
- #105 — fail closed at report and recommendation output boundaries when material provenance is missing
- #106 — replace RAG presentation-text claim extraction with typed generated claims
- #107 — document canonical decision evidence packet and reconstruction semantics
- #114 — validate non-workflow evidence references during reconstruction
