---
status: accepted
---

# Ground R3 Recommendations in projected Portfolio consequences and Risk

## Context

R3 must prove that Polaris is a portfolio decision system rather than a security-opinion generator. The accepted SPY slice asks whether one Portfolio should increase, hold, or reduce SPY exposure over an explicit Investment Horizon.

Current architecture already distinguishes actual Portfolio State from projected state, separates Position, Exposure, Allocation, and Portfolio Risk, requires Projected Portfolio Consequences to remain hypothetical, and requires Portfolio Risk to shape Recommendation formation rather than act as a post-hoc approval stamp.

The remaining architectural question is the minimum durable Portfolio & Risk contract needed to make the first R3 Recommendation genuinely Portfolio-relative without building broad portfolio analytics, execution state, or R4 governance.

## Decision

At every material R3 judgment boundary, Polaris persists or reconstructs a **decision-grade actual Portfolio State** for the scoped Portfolio. The minimum state preserves:

- canonical `PortfolioId`;
- as-of time;
- authoritative source provenance for externally owned Portfolio facts;
- capital / net asset basis needed to interpret Exposure and Allocation;
- materially relevant cash / liquidity;
- current SPY Position quantity/value where applicable;
- current SPY Exposure and Allocation;
- only additional Portfolio facts materially required for the R3 decision.

The retained Portfolio State is a decision-grade representation and does not transfer external books-and-records authority to Polaris.

Each material increase / hold-no-action / reduce Decision Alternative may have an attributable **Projected Portfolio Consequence** and, when materially useful, a Projected Portfolio State. The durable projected consequence preserves:

- the Decision Alternative;
- source Portfolio State identity and as-of boundary;
- explicit Investment Horizon;
- scenario and material assumption basis;
- projected SPY Exposure / Allocation change;
- projected cash / liquidity effect where material;
- material economic benefits and adverse possibilities;
- material Portfolio Risk changes;
- attribution;
- uncertainty and unresolved components where precision is unsupported.

Projected Portfolio State and Projected Portfolio Consequence are hypothetical decision facts. Later actual Portfolio State or Outcome does not rewrite them.

R3 persists attributable, time-specific **Portfolio Risk Assessments** for actual Portfolio State and material projected states where Risk is decision-relevant. A Risk Assessment preserves the State or projection being assessed, Investment Horizon, scenario/basis, materially used Evidence, assumptions, uncertainty, attribution, and the material Risk dimensions used.

For the first SPY slice, only Risk dimensions needed to distinguish increase / hold / reduce must be represented. Depending on materiality, these include:

- SPY Exposure / concentration;
- horizon-relative downside or drawdown sensitivity;
- liquidity / cash-buffer effect;
- market / volatility sensitivity;
- Portfolio-objective shortfall.

A single generic Risk Score may be retained as one measure but cannot be the universal Portfolio Risk semantic.

Portfolio Risk participates **before Recommendation finality**. Recommendation formation consumes the Investment View and Decision Alternatives together with actual Portfolio State, alternative-relative Projected Portfolio Consequences, and Portfolio Risk Assessments. Portfolio Risk is not an approval, Admissibility result, authority act, or post-hoc veto.

If a material Portfolio State fact, Projected Portfolio Consequence, or Portfolio Risk cannot be established with adequate support, the semantic result remains unknown / indeterminate as appropriate. Polaris may withhold a Recommendation under ADR 0007 rather than manufacture precision.

Actual Portfolio State, Projected Portfolio Consequences, Portfolio Risk Assessments, and recognized uncertainty are historical facts/judgments. Later market movement, improved models, or later Outcomes do not destructively rewrite them.

External operational Portfolio facts retain external factual authority. Polaris owns their Portfolio decision meaning and the derived projections and Risk assessments.

R3 does not introduce full portfolio analytics, generic simulation infrastructure, execution/broker state, or R4 Formal Constraint, Admissibility, Approval, or governance machinery.

## Rationale

This is the smallest durable Portfolio/Risk contract that can prove AS-008. The same Investment View can remain fixed while materially different current Portfolio State or Risk produces different projected consequences and, where appropriate, a different supported Recommendation.

The contract preserves portfolio-relative economic reasoning while keeping external factual authority, hypothetical projection, Risk judgment, and governance authority distinct.

## Considered Options

### Use current SPY Position/Exposure plus one generic Risk Score

Rejected because a scalar cannot represent the material adverse possibilities and Portfolio-relative tradeoffs required by the architecture.

### Persist exhaustive projected Portfolio snapshots for every scenario

Rejected because R3 needs only materially decision-relevant consequences and should not overbuild generic simulation or portfolio-model infrastructure.

### Apply Portfolio Risk after Recommendation formation as an approval gate

Rejected because Portfolio Risk is an economic input to judgment and PRT-007 requires it to shape Recommendation formation before finality.

### Persist decision-grade actual state, material projected consequences, and attributable Risk assessments

Accepted because it is sufficient for the first R3 slice while preserving clean ownership and future extensibility.
