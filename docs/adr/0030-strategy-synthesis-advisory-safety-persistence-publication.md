---
status: accepted
---

# 0030. Strategy Advisory Safety, Persistence, and Publication

## Context

Strategy Advisory is a read-only, non-authoritative workflow sibling under ADR-0024 and ADR-0025. ADR-0027 defines its runtime source-binding lifecycle, ADR-0028 restricts its evidence to a closed Polaris-issued reference set, and ADR-0029 assigns it one provider-neutral `polaris-synthesis` model route and one advisory-owned prompt contract.

The remaining trust boundary is what happens after the model responds. Polaris already has a shared reasoning-trace safety boundary, canonical decision-evidence materialization, risk-tiered readiness architecture, governed presentation/sink controls, and explicit actor attribution for protected durable actions. Strategy Advisory must compose those platform boundaries without allowing model contamination, partial validation, or presentation code to create a parallel trust model.

## Decision

Raw model output is an untrusted candidate and is not a `StrategyAdvisoryResult`. A candidate becomes a semantic advisory result only after reasoning-trace safety, typed schema validation, code-owned authority validation, deterministic source binding, and closed-world reference validation all succeed.

Provider-private reasoning that is carried in a provider-specific channel may be discarded by the gateway/provider boundary before the semantic candidate is formed. If model-internal reasoning, chain-of-thought, scratchpad material, reasoning-bearing fields, or ambiguous reasoning markers appear inside the candidate advisory payload itself, Polaris rejects the entire semantic candidate. Strategy Advisory does not obtain canonical status by stripping, redacting, repairing, or otherwise salvaging the remainder of a contaminated candidate. Shared sanitization remains a containment mechanism for preventing leakage into errors, logs, telemetry, or external surfaces; it is not a semantic repair mechanism for Strategy Advisory.

Safety or validation rejection fails closed for Strategy Advisory only. The advisory normalizes expected inability to produce a trusted result to `UNAVAILABLE` with code-owned status and reason information, while the canonical deterministic strategy, portfolio, recommendation, trade-packaging, execution-risk, governance, and policy paths remain unaffected. True runtime crashes remain runtime failures under the existing runtime contract.

An `UNAVAILABLE` advisory contains no surviving model-authored narrative, findings, explanations, citations, or other semantic residue. Safe code-owned status, reason codes, correlation identity, and execution provenance may be retained through their owning operational boundaries. An unavailable advisory does not require an empty or synthetic claim-bearing `DecisionEvidencePacket` because it contains no material advisory claims.

`DEGRADED` is reserved for an otherwise fully trusted advisory whose legitimate canonical input or operating context is explicitly degraded or incomplete. A degraded advisory must still satisfy all safety, typing, source-binding, authority, and reference-validation requirements. `DEGRADED` must not represent stripped reasoning, dropped invalid findings, repaired schema output, ignored references, citation substitution, unsafe-content redaction, silent capability fallback, or any other partially accepted model result.

Semantic acceptance, durable materialization, and publication eligibility are separate gates. Safe code-owned operational/audit facts may be durable when generation fails. Claim-bearing advisory content becomes durable only after semantic acceptance and is materialized through the Strategy Advisory's own canonical `DecisionEvidencePacket` under ADR-0028. Raw prompts, contaminated completions, model-private reasoning, scratchpads, secrets, unsafe provider error payloads, and rejected model content do not become canonical advisory records, retained evidence, reconstruction evidence, ordinary telemetry payloads, or external output.

A valid `StrategyAdvisoryResult` and its evidence packet do not automatically make the advisory externally publishable. Reports, future MCP responses, API/CLI output, Markdown/PDF rendering, and other external surfaces consume Strategy Advisory through the common governed sink-control boundary established by the presentation architecture. Those sinks preserve the code-owned non-authoritative identity of Strategy Advisory and must not reinterpret advisory findings as canonical strategy selection, recommendation eligibility, portfolio intent, position sizing, execution-risk approval, governance approval, production readiness, or capital action.

Human-facing citations and provenance are rendered from validated typed references and canonical evidence, never inferred from citation-shaped model prose, arbitrary URLs, or presentation text. If Strategy Advisory is unavailable, presentation surfaces may omit it or render a safe code-owned unavailable state according to shared sink policy; raw provider errors and rejected model text are never used as customer-facing explanations.

External publication additionally requires readiness evidence appropriate to the active risk/authority profile and exact operating mode. A valid internal advisory may therefore be withheld from an external sink. A `DEGRADED` advisory may be published externally only when that degraded mode is explicitly covered by qualifying readiness evidence and the shared sink-control policy permits it. Missing required readiness, governance, approval, evidence, or authority state fails closed at the publication boundary rather than being interpreted as success.

Prompt identity/version, requested capability alias, resolved provider/model identity, runtime configuration, retries, latency, token usage, and execution correlations remain execution provenance outside `StrategyAdvisoryResult`. Evidence/readiness/governance/sink state remains publication context outside the advisory semantic payload. External surfaces may expose only the safe allowlisted subset required by the common sink contract.

Actor-sensitive durable materialization or publication actions reuse the canonical Polaris principal and audit-attribution contracts. Strategy Advisory does not define advisory-local user, actor, or authorization identities and does not use system identity as a convenience bypass for protected operations.

## Rationale

Rejecting a contaminated semantic candidate instead of salvaging it preserves honest provenance: a canonical advisory result is what passed the contract, not an edited remainder of a response that violated the trust boundary. Keeping fail-closed behavior local to the advisory preserves the stronger architectural invariant that optional model assistance cannot become an availability dependency for canonical strategy decisions.

Separating semantic validity, persistence, evidence materialization, readiness, and publication prevents each boundary from smuggling authority into the next. Reusing the shared reasoning-safety, evidence, readiness, sink-control, and identity seams also avoids advisory-specific policy stacks that future reports, MCP, API, or UI code could bypass or inconsistently reimplement.

## Consequences

- Strategy Advisory accepts only fully validated model candidates; contaminated or partially valid candidates are rejected rather than repaired into canonical advisory content.
- Expected safety/validation rejection produces an `UNAVAILABLE` advisory with code-owned status only and never changes the canonical strategy path.
- `DEGRADED` means trusted advisory content over an explicitly degraded legitimate context, not partially repaired model output.
- Operational failure facts may be durable without making rejected model content durable.
- Claim-bearing advisory persistence requires the Advisory's own canonical `DecisionEvidencePacket`.
- Durable advisory content is not automatically externally publishable; readiness and common sink controls remain separate publication gates.
- Degraded external publication requires explicit readiness qualification for that degraded mode.
- Human-facing citations derive only from validated canonical references and evidence.
- Reports, MCP/API/CLI, and other external surfaces preserve Strategy Advisory's non-authoritative identity through the shared presentation/sink boundary.
- Execution provenance, publication context, and advisory semantic content remain separate contracts.
- Actor-sensitive persistence/publication reuses canonical Polaris principal and authorization/audit attribution rather than introducing advisory-specific identity semantics.
