---
status: superseded by ADR-0027
---

# 0026. Strategy Advisory Output Contract

## Context

ADR-0024 defines Strategy Advisory as read-only and non-authoritative, and ADR-0025 places it after canonical strategy synthesis as a dedicated sibling workflow branch. Polaris therefore needs a typed advisory result that can carry model-assisted critique and recommendations without duplicating `StrategyHypothesis`, `StrategySynthesisDecision`, canonical evidence storage, or runtime execution provenance.

The contract must also distinguish advisory availability from runtime failure, preserve the non-authoritative boundary when the result is detached from its runtime envelope, and give later evidence-validation and publication decisions explicit reference points.

## Decision

Polaris defines one immutable `StrategyAdvisoryResult` semantic contract with:

- `status`: `AVAILABLE`, `DEGRADED`, or `UNAVAILABLE`;
- typed `status_reasons` for expected inability to produce or retain trustworthy advisory content;
- a code-owned `NON_AUTHORITATIVE` authority marker;
- `source_evidence_packet_ids` referencing the canonical strategy decision/evidence packets examined;
- optional human-readable `narrative`; and
- zero or more typed `StrategyAdvisoryFinding` values.

Each `StrategyAdvisoryFinding` contains:

- stable `finding_id`;
- typed `kind`;
- concise `statement`;
- optional user-facing `explanation` that is not a reasoning trace;
- typed `subject_references` identifying canonical artifacts the finding discusses; and
- typed `evidence_references` identifying canonical evidence supporting the finding.

Initial finding kinds are `CRITIQUE`, `COUNTERARGUMENT`, `MISSING_EVIDENCE`, `SCENARIO`, and `ADVISORY_RECOMMENDATION`. These are advisory semantics only and do not create canonical strategy hypotheses or decisions.

Expected advisory unavailability is represented semantically as `UNAVAILABLE`; runtime crashes remain runtime failures. `DEGRADED` means a valid advisory result exists but some content was omitted or rejected. Initial status-reason families are `INPUT_UNAVAILABLE`, `GENERATION_UNAVAILABLE`, `INVALID_OUTPUT`, `REFERENCE_VALIDATION_FAILED`, and `SAFETY_REJECTED`. Later safety handling may refine behavior without changing this separation of semantic availability from runtime failure.

The advisory contract must not carry canonical strategy authority fields such as perspective selection, directional score/bias, hypothesis strength, candidate score, synthesis weight/rank, numeric advisory confidence, allocation, sizing, eligibility, approval, invalidation conditions, portfolio actions, or execution actions.

Advisory evidence references are identifiers into canonical evidence/reconstruction authority. The result must not copy raw evidence payloads or invent a parallel citation store. Exact allowed reference kinds and validation rules are delegated to the later evidence/citation decision.

Model/provider identity, model alias, prompt/config identity, latency, token usage, trace data, and other execution provenance remain code-owned runtime/execution metadata rather than LLM-authored advisory semantics.

The LLM may supply advisory content, but Polaris supplies status normalization, authority, identity, provenance, reference validation, and lifecycle semantics.

## Rationale

A small top-level result plus one typed finding structure gives advisory content enough shape for validation, replay, evaluation, and presentation without reproducing the canonical hypothesis or synthesis models. Typed finding kinds preserve semantic distinctions while avoiding a family of nearly identical contracts.

Binding advisory output to existing evidence packet and evidence identities keeps PostgreSQL/runtime evidence authority single-sourced and makes later citation validation possible without copying source data into model output.

Separating semantic advisory availability from runtime failure preserves ADR-0025's failure-isolated sibling topology, while excluding numeric confidence and canonical decision fields prevents advisory metadata from becoming a backdoor ranking or decision signal.

## Consequences

- The advisory implementation requires dedicated typed result/finding/status contracts, but implementation remains pending.
- Evidence/citation validation must resolve and validate the contract's subject and evidence references rather than parsing citations from prose.
- Model-routing, safety/persistence/publication, and readiness decisions must preserve the separation between advisory semantics and runtime/execution metadata.
- Advisory recommendation text may guide human review but cannot encode or become a canonical portfolio, risk, governance, or execution action.