---
status: accepted
---

# 0027. Strategy Advisory Runtime Source Binding

## Context

ADR-0026 established the typed `StrategyAdvisoryResult`, but bound that runtime result to `source_evidence_packet_ids`. Subsequent concrete-contract validation established that the canonical strategy `DecisionEvidencePacket` is assembled after workflow completion from completed-run evidence, while Strategy Advisory executes immediately after canonical strategy synthesis under ADR-0025.

Making the advisory node depend on a packet that does not yet exist would either move durable evidence materialization into the authoritative runtime path solely for an optional advisory capability or require a provisional/two-stage citation mechanism. Both would invert the intended separation between canonical runtime truth and durable evidence proof.

## Decision

Strategy Advisory consumes the canonical runtime strategy artifacts that actually exist at its lifecycle point: the completed `StrategyEvidenceContext`, the bull/bear/sideways `StrategyHypothesis` values, and the resulting `StrategySynthesisDecision`. These runtime/domain artifacts, not a pre-materialized `DecisionEvidencePacket`, are the advisory's source truth during generation.

Polaris binds `StrategyAdvisoryResult` to those consumed runtime sources with code-owned stable source identities or fingerprints sufficient to prove which strategy evidence, hypotheses, and synthesis decision the advisory examined. The exact minimal binding shape is determined with the advisory evidence/reference contract; it must not pretend that a not-yet-materialized packet was consumed.

The remainder of ADR-0026's output contract is carried forward unchanged: one immutable `StrategyAdvisoryResult` with `AVAILABLE`, `DEGRADED`, or `UNAVAILABLE` status; typed status reasons; a code-owned `NON_AUTHORITATIVE` marker; optional narrative; and typed `StrategyAdvisoryFinding` values containing stable finding identity, kind, statement, optional user-facing explanation, subject references, and evidence references. Initial finding kinds remain `CRITIQUE`, `COUNTERARGUMENT`, `MISSING_EVIDENCE`, `SCENARIO`, and `ADVISORY_RECOMMENDATION`.

The advisory semantic contract still excludes canonical strategy-selection fields, numeric advisory confidence, raw evidence payloads, and model/runtime execution provenance. Expected advisory unavailability remains semantic `UNAVAILABLE`; runtime crashes remain runtime failures.

After workflow completion, Strategy Advisory is materialized through the canonical decision-evidence lifecycle as its own claim-bearing output. Its `DecisionEvidencePacket` proves support and reconstructability for advisory claims and may link to the canonical strategy decision/evidence packet once that packet actually exists. The strategy decision packet remains evidence for the canonical Strategy Decision; it is not repurposed as the advisory's own claim packet.

Model reasoning, chain-of-thought, scratchpads, self-generated citation identities, and presentation text never become source truth or evidence merely because they appear in model output.

This ADR supersedes ADR-0026.

## Rationale

Runtime consumers should consume canonical runtime/domain contracts. Durable and externally governed consumers should consume evidence packets derived from those contracts. Preserving that direction keeps an optional downstream LLM capability from changing when upstream evidence becomes durable, avoids a provisional citation subsystem, and lets each claim-bearing output own the evidence packet that proves its claims.

The corrected lifecycle also matches the existing `DecisionEvidencePacket` role: durable claim/evidence binding, reconstruction, retention, and auditability rather than universal internal message passing.

## Consequences

- `StrategyAdvisoryResult` no longer semantically claims to have examined a strategy evidence packet that does not yet exist at runtime.
- Strategy Advisory requires stable code-owned source binding to the runtime strategy artifacts it actually consumed.
- Strategy Advisory requires its own decision-evidence packet when later curated, persisted, governed, or published as a claim-bearing output.
- The advisory evidence/reference decision must define how runtime source identities and advisory finding references map into the later canonical advisory packet without creating a parallel evidence store.
- ADR-0026 is superseded.