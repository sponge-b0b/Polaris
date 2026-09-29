---
status: accepted
---

# Expose the R3 Human Investment Decision through a thin CLI

## Context

R3 needs one complete human surface for the SPY decision slice. Human Investment Decision is already a distinct, attributable, authority-bearing fact and must remain separate from Recommendation, Approval, Admissibility, Action Intent, and execution.

## Decision

R3 persists Human Investment Decision as a first-class durable fact with opaque identity, governing Investment Decision, Actor Attribution, time/scope, selected economic disposition or Deferral, relationship to zero or more materially considered Recommendations, optional material rationale, and resolution effect.

It may adopt, modify, reject, differ from, or exist without a Recommendation. None of those cases rewrites the Recommendation. Recommendation rejection alone does not determine resolution. Deliberate hold/no-action may resolve the Investment Decision and creates zero synthetic Action Intents.

R3 realizes only the minimum Investment Authority Regime necessary to validate Human-Investment-Decision power for the one supported Portfolio and attributable human actor. The check is power-, scope-, and time-specific and fails closed when authority cannot be established. R4 retains Approval, Authority Denial, Admissibility, Mandate Exception, Residual-Risk Acceptance, and broader governed-use composition.

The first complete human surface is a small interactive CLI over shared application commands and queries. It presents concise decision state first, with inspectable Decision Context, material Evidence issues, challenge, uncertainty, Portfolio/Risk consequences, Recommendation or withholding, and relevant history. It records Human Investment Decision only through the shared application boundary and never creates alternate CLI-specific business truth.

## Rationale

A CLI is the smallest complete human surface that proves the R3 semantics without adding browser/session architecture. The minimal authority seam preserves the already-required power-specific Human Investment Decision boundary without prematurely implementing R4.

## Considered Options

Web UI was rejected as unnecessary R3 breadth. Email/PDF cannot by themselves provide the canonical interactive command path. API/MCP alone is not the complete human surface required by UX-002. A thin interactive CLI is accepted.
