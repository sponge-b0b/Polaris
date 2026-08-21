---
status: accepted
---

# 0028. Strategy Advisory Evidence and Reference Validation

## Context

Strategy Advisory is a read-only, non-authoritative consumer of completed canonical strategy runtime artifacts under ADR-0024, ADR-0025, and ADR-0027. Its findings may make material claims that later become durable or published, so those claims must be grounded without allowing model output to invent evidence, citation identities, or a parallel evidence store.

ADR-0027 established that advisory runtime execution consumes `StrategyEvidenceContext`, bull/bear/sideways `StrategyHypothesis` values, and `StrategySynthesisDecision` directly. The advisory's own `DecisionEvidencePacket` is materialized later through the canonical evidence lifecycle. Evidence/reference validation must therefore preserve the distinction between runtime domain truth and later durable evidence proof.

## Decision

Strategy Advisory receives a closed, code-owned source view containing only canonical runtime strategy artifacts and any supplemental canonical evidence explicitly supplied through Polaris application or RAG boundaries. The model may inspect that view and select references from it, but it may not mint source identities, evidence identities, URLs, citations, or provenance.

`StrategyAdvisoryResult` carries a code-owned source binding sufficient to identify the exact canonical strategy artifacts consumed. Existing canonical fingerprints or identities are reused where sufficient; otherwise Polaris derives deterministic content identity from canonical serialization. Source binding must preserve the temporal identity of the consumed sources and must not depend on projection-specific or not-yet-materialized durable record identifiers.

Each `StrategyAdvisoryFinding` uses typed Strategy Advisory References. A subject reference identifies the canonical supplied artifact or element the finding discusses. An evidence reference identifies supplied canonical support for the finding. Reference validity is closed-world: a returned reference is valid only when Polaris supplied that identity for the current advisory input and the reference is used in an allowed evidentiary role.

Canonical runtime reference targets may include strategy evidence context, individual strategy evidence, input-quality state, strategy hypotheses, strategy assumptions, strategy invalidation conditions, and the strategy synthesis decision. Supplemental curated or RAG evidence may be referenced only when Polaris supplied it through canonical application or RAG boundaries. Rebuildable projection identifiers such as Qdrant point IDs or Neo4j node IDs are not evidence authority and must resolve through their canonical source records when applicable.

Subject and evidence roles are not interchangeable merely because a reference exists. A hypothesis may be the subject of a critique without thereby proving the critique. A strategy decision may support a factual assertion about Polaris's own decision state, but it is not by itself evidence that the external market state asserted by that decision is true.

Every material advisory finding requires validated supporting evidence. A `MISSING_EVIDENCE` finding is valid only when canonical supplied state represents the absence or degradation, such as typed input-quality state; omission from the model's visible context is not proof that evidence does not exist. Missing-evidence findings may assert only the represented absence or degradation, not the truth of an opposite market condition.

Citation-shaped text in `narrative`, `statement`, or `explanation` has no evidentiary authority. Human-facing citations are rendered from validated typed references. Narrative and explanations may summarize or explain validated findings but must not introduce independent material factual claims outside the structured findings.

Model reasoning, chain-of-thought, scratchpads, prompt text, self-generated citations, remembered sources, and arbitrary URLs cannot become advisory evidence, source truth, retained support, or reconstruction evidence merely because they appear in model output.

After workflow completion, material advisory findings are mapped into the Strategy Advisory's own canonical `DecisionEvidencePacket`. The packet binds advisory claims to validated evidence and reconstruction references and may carry lineage to the canonical Strategy Decision and its later-materialized evidence packet. The Strategy Decision packet remains the proof for the canonical Strategy Decision; the Strategy Advisory packet remains the proof for advisory claims.

## Rationale

A closed-world reference model makes hallucinated or substituted citations mechanically rejectable while keeping runtime consumers dependent on canonical runtime/domain contracts rather than persistence artifacts. Separating subject identity from evidentiary support prevents authority leakage from canonical strategy objects into model-authored critique.

Materializing the advisory's own evidence packet after execution preserves the established Polaris lifecycle: runtime correctness first, durable evidence proof second, publication/governance readiness afterward. This avoids provisional packets, duplicated citation systems, and coupling advisory semantics to rebuildable retrieval projections.

## Consequences

- Advisory generation requires a code-owned source view and deterministic source binding.
- Model-returned references are valid only when they match identities Polaris supplied for that advisory execution and satisfy their allowed role.
- All material advisory claims remain structured findings; free-form narrative cannot bypass evidence validation.
- Supplemental RAG or curated evidence remains usable without making Qdrant, Neo4j, arbitrary URLs, or model memory evidence authority.
- Strategy Advisory receives its own `DecisionEvidencePacket` when its claims cross the applicable durable or publication boundary.
