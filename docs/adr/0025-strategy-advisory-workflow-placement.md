---
status: accepted
---

# 0025. Strategy Advisory Workflow Placement

## Context

ADR-0024 defines Strategy Advisory as a read-only, non-authoritative consumer of canonical strategy evidence and already-produced strategy artifacts. The canonical strategy lifecycle must remain semantically complete and produce the same authoritative result whether advisory succeeds, fails, is disabled, or does not exist.

Polaris therefore needs a workflow placement that gives advisory generation a first-class runtime boundary without inserting model output into canonical strategy selection, portfolio management, trade packaging, execution-risk guarding, or presentation ownership.

The current morning-report workflow already has a clean authority seam: `StrategySynthesisAgent` produces the canonical `StrategySynthesisDecision`, after which `PortfolioManagerAgent` continues the authoritative portfolio path.

## Decision

Strategy Advisory executes once after canonical strategy synthesis as a dedicated workflow node/operation that is a sibling branch to downstream portfolio management.

Both Strategy Advisory and `PortfolioManagerAgent` may depend on the completed canonical strategy-synthesis output, but neither depends on the other. No canonical strategy, portfolio, recommendation, trade-packaging, execution-risk, governance, or policy operation may depend on Strategy Advisory.

Strategy Advisory may consume completed canonical strategy material read-only, including the strategy evidence context, bull/bear/sideways hypotheses, and the `StrategySynthesisDecision`. The exact typed input and output fields remain subject to the later advisory contract and evidence decisions.

Ownership is separated as follows:

- the Strategy Advisory boundary solely owns advisory-generation semantics;
- the workflow definition/runtime owns invocation, dependency ordering, and execution placement;
- `StrategySynthesisAgent`, bull/bear/sideways perspective agents, portfolio management, report generation, MCP/API/CLI adapters, and future UI surfaces do not own advisory generation; and
- presentation and transport surfaces consume advisory output rather than generating it independently.

Strategy Advisory must not execute per perspective or between perspective generation and canonical synthesis. It must not be placed upstream of `StrategySynthesisAgent` or otherwise become an input to canonical strategy selection.

Strategy Advisory failure or unavailability must not gate or change the authoritative strategy/portfolio path. The later safety and persistence decision may define typed degraded or unavailable advisory states, but it may not make advisory success a prerequisite for canonical strategy progression.

## Rationale

A post-synthesis sibling branch makes the non-authoritative boundary structural rather than conventional. The model can inspect the final deterministic strategy result and provide qualitative critique or recommendations without becoming an input to that result.

A dedicated workflow node also gives advisory generation one canonical runtime execution with independent provenance, observability, replay, evaluation, and failure handling. Generating advisory independently in report, MCP, API, CLI, or UI surfaces would permit divergent model outputs for the same strategy decision and would move intelligence ownership into presentation/transport layers.

Running advisory per perspective or before synthesis would increase model work and create an architectural path for advisory output to influence hypothesis comparison, undermining ADR-0007 and ADR-0024.

## Consequences

- The canonical strategy path continues from `StrategySynthesisAgent` to `PortfolioManagerAgent` without depending on Strategy Advisory.
- Strategy Advisory becomes a separate, optional runtime branch after synthesis.
- Later contract, evidence, model-routing, persistence/publication, and readiness decisions must preserve this placement and dependency direction unless a new architectural decision explicitly reopens it.
- Advisory presentation can be reused consistently across multiple sinks because generation has a single canonical owner.
