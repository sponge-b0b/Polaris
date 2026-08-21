---
status: accepted
---

# 0029. Strategy Advisory Model Routing and Prompt Ownership

## Context

Strategy Advisory is a read-only, non-authoritative workflow sibling that runs once after canonical strategy synthesis under ADR-0024 and ADR-0025. ADR-0027 gives it a dedicated typed `StrategyAdvisoryResult`, and ADR-0028 constrains advisory evidence to a closed, code-owned source view with Polaris-issued references.

Polaris already centralizes model access behind typed LLM boundaries and LiteLLM-backed profile routing. The accepted provider-neutral alias decision from Wayfinder #169/#170 establishes that canonical model aliases describe required capabilities rather than provider, concrete model, hardware, hosting location, or cost tier. The corresponding implementation spec is #171; until that migration lands, existing `polaris-local-*` names are transitional rather than architectural identities.

Strategy Advisory therefore needs one durable decision for which semantic capability it requests, where advisory prompt semantics live, and what happens to the older bull/bear/sideways prompt artifacts that predate the deterministic structured-hypothesis architecture in ADR-0007.

## Decision

Strategy Advisory performs one model-assisted advisory generation over the completed canonical strategy artifacts and requests the provider-neutral `polaris-synthesis` capability alias.

`polaris-synthesis` expresses the semantic purpose of the call: combining completed canonical strategy evidence, hypotheses, and the canonical `StrategySynthesisDecision` into one coherent non-authoritative advisory interpretation. The fact that Strategy Advisory returns a typed `StrategyAdvisoryResult` is an output-contract requirement and does not make `polaris-structured` the semantic capability. Structured parsing and validation remain separate from capability selection.

Strategy Advisory must not select concrete providers, models, hosting locations, hardware tiers, cost tiers, alternate capability aliases, or fallback routes. The model gateway/profile boundary resolves `polaris-synthesis` to the operator-selected provider and model. Strategy Advisory does not implement alias fallback such as retrying through `polaris-reasoning`, `polaris-fast`, or another capability when `polaris-synthesis` is unavailable. Advisory degraded or unavailable behavior is resolved by the separate lifecycle decision in #41 rather than by silently changing semantic capability.

Strategy Advisory owns its advisory-generation prompt semantics. Its prompt contract may instruct the model to remain non-authoritative, use only the supplied source view, select only supplied reference identities, avoid inventing citation authority, and return the required typed result. Those instructions are behavioral guidance, not the enforcement boundary. Typed parsing, code-owned authority fields, closed-world reference validation, canonical evidence materialization, and downstream safety/governance policy enforce the corresponding invariants.

The model gateway owns capability resolution, provider/model binding, request execution, provider normalization, and transport concerns. The workflow owns invocation and dependency ordering. Reports, MCP/API/CLI adapters, and future presentation surfaces consume the canonical advisory result rather than owning advisory prompts or generating separate advisory variants.

Strategy Advisory uses one advisory prompt family for the completed canonical strategy. It does not run separate model-authored bull, bear, and sideways personas and does not recreate a model debate or second hypothesis-selection system. Bull/bear/sideways `StrategyHypothesis` values remain deterministic canonical inputs to the advisory rather than model roles owned by it.

Legacy bull/bear/sideways prompt artifacts are not reused or rewritten as Strategy Advisory prompts. During remediation, obsolete prompt artifacts and callers whose only purpose is the pre-ADR-0007 model-driven perspective path are removed rather than archived in the live repository. Git history is sufficient archival history. If repository evidence establishes an independently legitimate surviving use for a legacy prompt, that prompt remains with its actual owning capability rather than being relabeled as Strategy Advisory.

Prompt identity/version or fingerprint, the requested capability alias, resolved provider/model identity, and request/runtime configuration are execution provenance. They remain outside `StrategyAdvisoryResult` and are recorded through the appropriate runtime/model provenance mechanisms needed for replay, evaluation, and observability.

Implementation of Strategy Advisory targets the canonical `polaris-synthesis` capability contract. It must not introduce a new durable dependency on the transitional `polaris-local-synthesis` name; implementation sequencing may therefore depend on or be coordinated with the provider-neutral alias migration in #171/#172.

## Rationale

Choosing a capability alias by semantic purpose keeps application code stable when operators change inference infrastructure. Choosing `polaris-structured` merely because the result is typed would conflate response-shape requirements with the reason the model is being invoked.

One post-synthesis advisory invocation preserves the authority and workflow decisions already accepted: the deterministic strategy lifecycle remains complete on its own, while the model adds explanation, critique, counterarguments, and missing-evidence observations without becoming another strategy-selection participant.

Keeping prompt semantics in Strategy Advisory prevents infrastructure and presentation layers from acquiring investment-domain behavior. Treating prompt text as guidance rather than enforcement also prevents architectural authority from depending on model compliance.

Removing obsolete perspective prompts avoids leaving misleading live artifacts that future contributors or coding agents could mistake for canonical architecture. Preserving only independently valid callers keeps the cleanup evidence-driven rather than destructive by name alone.

## Consequences

- Strategy Advisory has one semantic model route: `polaris-synthesis`.
- Typed structured output remains mandatory but is enforced independently of the selected semantic alias.
- Concrete provider/model selection and fallback policy remain outside Strategy Advisory.
- Prompt ownership is local to the Strategy Advisory boundary; gateway and presentation layers do not own advisory-domain prompts.
- Separate bull/bear/sideways LLM personas are not part of the advisory architecture.
- Obsolete legacy perspective prompts are removed during remediation instead of being archived or repurposed.
- Prompt/model execution metadata remains provenance rather than semantic advisory payload.
- #41 still owns reasoning-trace safety enforcement, persistence/publication behavior, and degraded/unavailable lifecycle handling.
- #42 must validate the accepted routing, prompt-ownership, legacy-cleanup, and no-silent-alias-fallback invariants as part of implementation readiness.
