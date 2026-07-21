# Strategy Advisory Architecture Analysis

## Current Architecture

Polaris currently treats analyst and research agents as LLM-enriched evidence producers, while bull, bear, sideways, and strategy synthesis components are deterministic, code-owned strategy hypothesis producers.

Analyst and research agents such as `TechnicalAgent`, `FundamentalAgent`, `NewsAgent`, and `SentimentAgent` call `LLMService` after canonical services have produced source data. Their LLM calls provide interpretation, summaries, and narrative enrichment. The underlying service outputs remain the source of truth.

The bull, bear, and sideways strategy agents do not inject or call `LLMService`. They build hypotheses through deterministic policy functions over `StrategyEvidenceContext`, then publish typed `StrategyHypothesis` output. Current strategy metadata explicitly records that model aliases are configured lane references, not executed model calls:

- `strategy_model_execution_mode=not_executed`
- `calculation_authority=code`
- `llm_output_authority=none`
- `strategy_model_alias_purpose=configured_lane_reference`

The legacy prompt files for bull, bear, and sideways agents indicate an older or intended LLM-backed strategy-agent shape, but they are not wired into current strategy execution.

## Architectural Assessment

The current deterministic strategy core is appropriate for Polaris because strategy hypotheses sit close to portfolio intent and recommendation formation. Code-owned hypotheses preserve replayability, auditability, testability, governance compatibility, and stable authority boundaries. Model drift should not silently change strategy scores, eligibility, invalidation conditions, or risk posture.

The current architecture is weaker as an intelligence platform because it lacks a governed model-advisory lane for qualitative strategic reasoning. A purely deterministic perspective engine can miss useful model contributions such as adversarial critique, missing-evidence detection, human-readable thesis framing, and scenario-risk narration.

The ambiguity created by unused bull, bear, and sideways prompt files should be resolved as part of any advisory design. Either those prompts should become explicitly non-authoritative advisory prompts, or they should be archived/removed to avoid implying model execution that does not happen.

## Recommended Balance

The superior balance for Polaris is a deterministic-core / model-advisory-shell architecture:

```text
canonical evidence
→ code-owned bull/bear/sideways StrategyHypothesis
→ optional non-authoritative strategy advisory critique
→ code-owned synthesis/recommendation/governance
→ sanitized customer-facing explanation
```

Deterministic code should remain authoritative for:

- strategy scoring and weighting
- confidence and hypothesis strength
- evidence eligibility
- invalidation rules
- risk flags and recommendation eligibility
- portfolio intent and execution-safety inputs
- governance and policy outcomes

Model output may be useful for:

- advisory thesis narrative
- counterarguments and fragile assumptions
- missing-evidence warnings
- qualitative scenario risks
- reviewer notes and human-facing explanation drafts
- evidence-grounded critique that cites existing evidence IDs

Model output must not become authoritative for canonical scores, eligibility, sizing, execution, approval, or unsupported evidence claims.

## Planning Destination

The next architectural destination is an explicitly non-authoritative strategy advisory component. The component should make Polaris feel more like an intelligence platform while preserving the deterministic strategy core as the source of truth.

The design should settle:

- where advisory generation fits in the strategy workflow
- which typed contract carries advisory output
- how model aliases and prompt assets are used
- how advisory evidence references are validated
- how failures, reasoning-trace safety, persistence, reports, and MCP/customer-facing sinks treat advisory text
- how tests prove advisory execution is distinguishable from code-owned hypothesis authority
