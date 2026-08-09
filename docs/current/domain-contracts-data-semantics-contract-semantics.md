# Contract Semantics

## Purpose and status

This document owns the current Polaris data-contract semantics for value classification, typed boundary rules, numeric precision, score families, score conversions, and approved serialization or mapping boundaries. It is current architectural authority for these semantics.

Historical audit evidence and migration sequencing are preserved separately in [`../reference/domain-contracts-data-semantics-step-5-data-contract-inventory.md`](../reference/domain-contracts-data-semantics-step-5-data-contract-inventory.md).

## Canonical data classification

Every platform value belongs to one of these classes:

| Class | Meaning | Persistence policy |
| --- | --- | --- |
| 1. Canonical state | Authoritative business state, decisions, signals, inputs required for audit, or historical facts that cannot be recreated reliably | Persist with stable typed ownership. Frequently queried dimensions use explicit relational columns; complete nested source data may use purpose-named JSON payloads at the persistence boundary. |
| 2. Reproducible derived data | Values deterministically recomputable from persisted canonical inputs and a versioned algorithm | Persistence is optional. Persist when required for audit, historical model comparison, or performance; otherwise recompute. Record algorithm/model version when persisted. |
| 3. Transient runtime or presentation data | Runtime routing, renderer-only formatting, CLI state, temporary aggregation, or human-readable projection | Do not treat as system-of-record. Serialize only at runtime, report, artifact, or transport boundaries. |
| 4. Telemetry or diagnostic data | Timing, retries, trace identity, provider status, failure details, fallback provenance, and operational counters | Persist through telemetry/runtime observability stores, not business-state tables unless the value is also a business decision. |

## Risk-authority metadata

AI-adjacent outputs carry canonical risk and authority metadata through `domain.authority.RiskAuthorityContract`. That contract is orthogonal to the data class above: content type does not determine authority by itself.

The contract records the `Baseline`, `Enhanced`, `Vigilant`, or `Prohibited / Outside Authority` tier; authority of effect; canonical owner; source-of-truth category; intended sink; and gate profile. The deterministic classifier escalates from platform-known facts such as capital relevance, durable authority, external visibility, governance impact, evidence sufficiency, and sink type.

Model output or model-provided metadata must not self-declare authority, production readiness, governance approval, residual-risk acceptance, or a lower tier.

## Boundary and precision rules

1. Application services and intelligence components must exchange typed domain objects. A typed wrapper whose primary payload is `dict[str, Any]` does not satisfy the internal contract rule.
2. Dictionaries are valid at vendor, HTTP, runtime serialization, telemetry, checkpoint, report, artifact, and database JSON boundaries.
3. Stable, queryable business dimensions must not be hidden only in generic `metadata`, `raw`, `inputs`, `outputs`, or undifferentiated JSON blobs.
4. Purpose-named JSON/JSONB columns remain appropriate for complete nested source payloads when the nested members are not stable query dimensions.
5. Internal calculations preserve full precision. `round()` is permitted only in CLI, Markdown, PDF, web, and other human-presentation renderers.
6. Fallback values must be identified as fallback or unavailable state. They must not be persisted or reported as indistinguishable canonical observations.

## Score semantics

Polaris score fields are part of the data-contract surface, not incidental implementation details. New scoring code must name the score family explicitly, validate the correct range at the typed boundary, and convert between families only with an explicit formula. Do not infer a score's polarity from the word `score` alone.

### Canonical score families

| Family | Range | Neutral/default | Polarity | Representative fields |
| --- | --- | --- | --- | --- |
| Unit certainty/quality | `0.0` to `1.0` | context-specific, commonly `0.0` or `0.5` | higher means more certain, reliable, strong, complete, ready, aligned, or high-quality | `confidence`, `confidence_score`, `reliability`, `evidence_strength`, `hypothesis_strength`, `setup_quality`, `signal_quality`, `trade_quality_score`, `position_sizing_hint` |
| Unit risk/intensity | `0.0` to `1.0` | commonly `0.0` for no pressure or `0.5` for neutral breadth context | higher means worse, more risky, more intense, or more defensive pressure | `risk_score` when non-directional, `breadth_risk_score`, `volatility_risk_score`, `adjusted_risk_score`, `risk_pressure` in the aggregate/breadth paths |
| Unit stability | `0.0` to `1.0` | `1.0` when fully stable | higher means better or more stable | `stability`, `stability_score` |
| Signed directional market signal | `-1.0` to `1.0` | `0.0` | negative means bearish, defensive, risk-off, short, or unfavorable to the asset/posture; positive means bullish, aggressive, risk-on, long, or favorable | `directional_score`, `directional_bias`, `entry_bias`, `final_directional_bias` |
| Signed sentiment signal | `-1.0` to `1.0` | `0.0` | negative means bearish sentiment; positive means bullish sentiment | `sentiment_score`, `news_sentiment_score`, `market_sentiment_score`, `social_sentiment_score`, `composite_sentiment` |
| Signed attribution signal | `-1.0` to `1.0` | `0.0` | negative means detractor or adverse contribution; positive means contributor or favorable contribution | `contribution_score` |

`core.storage.persistence.validation.validation_checks.DEFAULT_SCORE_VALIDATION_SPECS` encodes the persistence-boundary field families for `confidence`, `setup_quality`, `risk_score`, sentiment fields, `directional_score`, and `contribution_score`. Strategy hypothesis contracts validate `directional_bias` as signed and `confidence`, hypothesis strength, evidence strength, and reliability as unit-interval values.

### Required conversions

Stability and risk are opposite unit-interval semantics. Convert them explicitly:

```python
risk = 1.0 - stability
stability = 1.0 - risk
```

Signed scores must not be passed to unit-score consumers without an explicit conversion. When the desired unit value is magnitude or alignment rather than direction, use a formula that states that intent, for example:

```python
directional_magnitude = abs(directional_score)
directional_alignment = 1.0 - abs(directional_score)
```

When converting risk pressure to a market-directional output, preserve the polarity in code rather than relying on naming. Existing runtime risk adaptation uses defensive risk pressure as negative directional market posture:

```python
directional_score = composite_risk * -1.0
```

### Risk intensity and directional posture

Risk intensity fields are unit-interval values. `volatility_risk`, `drawdown_risk`, `exposure_risk`, `composite_risk`, `risk_pressure`, `risk_score`, and `adjusted_*risk*` fields use `0.0` to `1.0`, where higher means more risk, intensity, or defensive pressure. `stability_score` remains a unit-interval stability value where higher means more stable. Favorable or risk-on conditions must be represented by lower risk, higher stability, `risk_bias`, regime labels, recommendations, or an explicit signed directional field; they must not be represented by negative risk values.

Signed values remain appropriate for market posture, sentiment, and attribution families. When a unit risk value must feed a signed market-directional consumer, the conversion must be explicit, for example the runtime risk adapter's `directional_score = composite_risk * -1.0` mapping.

## Approved serialization and mapping boundaries

Mappings and dictionaries are approved at architectural boundaries where Polaris must adapt to external, serialized, or projection-oriented shapes. These boundary uses include:

- vendor/client raw responses before provider normalization;
- HTTP and external transport payloads;
- runtime output, checkpoint, replay, event, and completed-run serialization;
- telemetry attributes and diagnostic metadata;
- PostgreSQL purpose-named JSON/JSONB payloads;
- report structured-content and artifact serialization;
- backtest node outputs and artifacts;
- CLI, web, and other human or external transport serialization.

Stable internal semantics must be promoted into typed requests, results, signals, domain records, runtime context, or persistence models before they cross internal platform boundaries. Truly extension-only inputs may remain in typed mapping fields only while their semantics are intentionally open-ended; once semantics stabilize, promote them to explicit typed fields.
