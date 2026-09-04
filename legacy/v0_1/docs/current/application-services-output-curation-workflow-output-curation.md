# Workflow Output Curation and Eligibility

## Purpose

Polaris workflows can produce a large volume of node output, including normalized service results, intelligence signals, risk assessments, recommendations, raw model responses, report structures, runtime metadata, and diagnostic information. Not all of this data should become a permanent domain record, and not every permanent domain record should be projected into the RAG stores.

The canonical principle is:

> **Archive broadly, curate deliberately, and embed selectively.**

The completed-run archive preserves the complete replay and audit boundary. Curated PostgreSQL records preserve stable, authoritative domain facts. Qdrant and Neo4j receive only explicit projections of curated records that provide retrieval or relationship value.

## Canonical Data Flow

```text
Workflow node output
    ↓
Completed-run archive for broad runtime evidence
    ↓
Gate 1: Is this a durable domain fact with a registered projector?
    ↓
Curated PostgreSQL record
    ↓
Gate 2: Is this useful and safe for RAG?
    ↓
Curated RAG document
    ↓
Gate 3: Which projections are appropriate?
    ↓
Qdrant and/or Neo4j
```

These are three separate decisions after archival:

1. Whether workflow output deserves a first-class curated record.
2. Whether that record has value as retrieval context.
3. Whether it belongs in semantic search, graph retrieval, both, or neither.

Archival is broad and automatic at workflow completion. Curation is narrow and
policy-driven through registered projectors. Retrieval projections are narrower
still and must be reproducible from PostgreSQL.

PostgreSQL remains the system of record. Qdrant and Neo4j are rebuildable projections, not competing sources of truth.

## Gate 1: Curated Record Eligibility

A workflow output should become a curated record only when it satisfies an explicit domain contract and the following criteria.

### 1. Meaningful Domain Concept

The output must represent a recognized business concept rather than an incidental implementation detail.

Examples include:

- Portfolio state
- Technical signal
- Fundamental assessment
- Risk assessment
- Strategy recommendation
- Trade proposal
- Execution decision
- Market or macro observation
- Financial report

Temporary variables, formatting fragments, orchestration state, and provider response shapes are not domain concepts.

### 2. Durable Historical Value

The record should remain useful after the workflow finishes. Typical historical uses include:

- Comparing decisions over time
- Explaining why a recommendation was made
- Reconstructing portfolio conditions
- Measuring subsequent outcomes
- Supporting attribution and governance review
- Creating deterministic backtest expectations
- Supplying trusted evidence to future workflows

If the data is useful only while one node is executing, it normally remains part of the completed-run archive rather than becoming a curated record.

### 3. Stable, Typed Schema

The candidate must map to a strongly typed domain model with named, meaningful fields. A generic `dict[str, Any]`, miscellaneous metadata payload, or raw serialized node output is not by itself a curated contract.

Important data should receive first-class fields and, when persistent, explicit schema migrations. New information must not be placed into metadata merely because adding a real contract requires more design work.

Metadata is appropriate for incidental, extensible, or boundary-specific context. It is not a substitute for domain modeling.

### 4. Deterministic Identity

The projection layer must be able to identify the record consistently across retries, resume, replay, and repeated projection attempts.

Identity may be based on values such as:

- Workflow execution ID
- Node execution ID
- Symbol or portfolio ID
- Effective timestamp or observation period
- Record type and schema version
- Source record ID

A deterministic identity makes the projection idempotent and prevents retry-driven duplicates.

### 5. Authoritative Temporal Meaning

The record must have a real business timestamp, such as:

- `observed_at`
- `effective_at`
- `generated_at`
- `as_of`
- `period_start`
- `period_end`

The projector must not invent a current timestamp or use a deterministic epoch fallback when the source does not provide temporal meaning. Missing required time data is a contract or quality failure that should be corrected at the source.

### 6. Provenance and Lineage

Every curated record must be attributable to its source. Depending on the record type, lineage should include:

- Workflow name and execution ID
- Source node name and node execution ID
- Source output contract and schema version
- Provider or service source
- Model and prompt version when applicable
- Parent domain records
- Live, simulated, backtest, or replay execution mode

Lineage is essential for replayability, auditability, attribution, and safe RAG retrieval.

### 7. Completeness and Quality

A record must satisfy its required fields and quality policy. Curated persistence should reject, quarantine, or explicitly mark records that are incomplete, stale, structurally invalid, or unsupported.

Silent coercion and metadata stuffing hide data quality problems and should be avoided.

### 8. Non-Redundant Authoritative Ownership

A domain fact must have one authoritative producer. Downstream nodes should reference the source fact through lineage rather than persist slightly modified copies of it.

For example, if the technical agent owns the canonical breadth assessment, a strategy recommendation may reference that assessment, but it should not create another competing breadth record.

## Domain Ownership in a Workflow

A morning-report workflow may include many nodes, but each durable fact should be curated from its authoritative producer.

| Authoritative producer | Candidate curated records |
|---|---|
| Portfolio state builder | Portfolio state, holdings, positions, exposures, performance context |
| Fundamental agent | Fundamental signal, valuation and quality assessment, supporting reasoning |
| Technical agent | Technical signal, technical snapshot, market context, breadth assessment |
| News agent | News analysis and references to normalized source articles |
| Sentiment agent | Market or asset sentiment assessment and supporting observations |
| Specialized risk agents | Drawdown, exposure, volatility, concentration, or other focused risk assessments |
| Risk aggregator | Canonical aggregate portfolio risk assessment |
| Bull, bear, and sideways agents | Regime-perspective signals when they have independent historical value |
| Strategy synthesis agent | Unified strategy recommendation and rationale |
| Portfolio manager agent | Allocation or rebalance intent |
| Trade packager | Broker-neutral trade proposal |
| Execution risk guard | Approval, rejection, resize, defer, or escalation decision |
| Report assembler | Final human-readable financial report |

The rule is:

> Persist a fact from the node that authoritatively creates it. Persist downstream conclusions as new domain records that reference their source facts.

This preserves a traceable chain such as:

```text
Technical assessment
    ↓ supports
Aggregate risk assessment
    ↓ constrains
Strategy recommendation
    ↓ informs
Portfolio intent
    ↓ becomes
Trade proposal
    ↓ evaluated by
Execution decision
```

## Data That Normally Remains in the Completed-Run Archive

The completed-run archive should preserve the full workflow execution boundary, including information that is valuable for replay or debugging but does not deserve a first-class domain table.

Typical archive-only content includes:

- Runtime and node timing metadata
- Progress and control events
- Temporary calculations
- Raw provider response dictionaries
- Prompt assembly inputs
- Internal intermediate scores
- Formatting structures used only by report renderers
- Duplicate copies of upstream facts
- Debug features and diagnostics
- Failure payloads and stack context
- Unsupported output contract versions
- Output fields that have not yet been deliberately promoted into a domain contract

Archive-only does not mean disposable. It means the information is retained as execution evidence without being declared an authoritative business fact.

## Raw LLM Responses

Full LLM responses should not be summarized or truncated at the persistence boundary.

The recommended separation is:

1. Preserve the complete raw response in the completed-run output or a dedicated immutable model-response artifact for audit and replay.
2. Parse and validate the response into a typed assessment, signal, rationale, or recommendation.
3. Persist the validated domain object as the curated record.
4. Link the curated record to the raw response through provenance.

A raw response is evidence of model behavior. It is not automatically a curated domain fact. The parsed, validated, and attributable result is the domain record.

## Gate 2: RAG Eligibility

A PostgreSQL record should become a RAG document only when retrieval of the record provides useful context to a future reasoning task.

### Strong RAG Candidates

- Financial reports
- Strategy recommendations and rationales
- Agent reasoning and assessments
- Risk assessments
- Macro summaries
- News analyses
- Allocation decisions
- Trade recommendations
- Execution decisions with explanatory context
- Backtest conclusions and attribution narratives

These records usually contain semantic meaning that benefits from natural-language retrieval.

### Usually PostgreSQL-Only

- Raw OHLCV bars
- Every portfolio equity-history point
- Large arrays of low-level indicator values
- Embedding and projection jobs
- Runtime telemetry and metrics
- Audit records intended for exact filtering
- High-volume normalized observations better retrieved through SQL

These records may support the construction of RAG documents, but embedding every row would add noise, cost, and weak retrieval matches.

### RAG Eligibility Questions

For each curated record, ask:

1. Would semantic retrieval of this record help a future workflow answer a question or make a decision?
2. Does the record contain explanatory context rather than only numeric measurements?
3. Is the record meaningful when retrieved outside its original runtime position?
4. Is semantic search better than an exact SQL query for the intended use?
5. Would embedding this record improve signal, or mostly increase noise and volume?
6. Does the record satisfy security, provenance, freshness, and quality policies?

RAG eligibility should be deterministic and declared by record type. It should not be decided dynamically by an LLM.

## Gate 3: Projection Selection

### Qdrant Projection

Use Qdrant when the record provides semantic text or mixed textual context that should be found by meaning.

Examples:

- Recommendations and rationales
- Risk narratives
- Market or macro summaries
- News analysis
- Financial reports
- Backtest conclusions

The embedding vector size must match the configured embedding model. For the current BGE-M3 embedding model, Polaris uses a 1024-dimensional dense vector; this is a model contract, not an arbitrary storage preference.

### Neo4j Projection

Use Neo4j when the value lies in relationships, lineage, dependency paths, and multi-hop traversal.

Examples:

```text
Recommendation → derived from → Risk assessment
Recommendation → applies to → Symbol
Risk assessment → evaluates → Portfolio
News analysis → references → News article
Trade proposal → implements → Strategy recommendation
Report → summarizes → Workflow execution
Curated record → produced by → Runtime node
```

### Projection Combinations

A curated record may be:

- Projected to Qdrant only
- Projected to Neo4j only
- Projected to both
- Retained only in PostgreSQL

The PostgreSQL record remains authoritative in every case. Qdrant and Neo4j projections must be reproducible from canonical records.

## Declarative Projection Policy

Eligibility and mapping should be defined in an explicit projector catalog rather than scattered conditionals or node-name conventions.

A representative typed descriptor is:

```python
@dataclass(frozen=True, slots=True)
class ProjectionDescriptor:
    projector_name: str
    output_contract: str
    output_schema_version: int
    source_node_names: frozenset[str]
    target_record_types: tuple[str, ...]
    required_fields: frozenset[str]
    identity_strategy: str
    timestamp_strategy: str
    quality_policy: str
    execution_modes: frozenset[str]
```

A descriptor should answer:

- Which typed output contract is supported?
- Which schema version can be projected?
- Which node or nodes may authoritatively produce it?
- Which curated record type is created?
- Which fields are mandatory?
- How is identity calculated?
- Which source field provides temporal meaning?
- What quality checks are required?
- Is the record valid for live, replay, simulated, or backtest executions?
- Is it eligible for Qdrant, Neo4j, both, or neither?

This makes curation reviewable, testable, versioned, and deterministic.

## Execution-Mode Isolation

Curated records must preserve execution mode. Simulated, backtest, replay, and live data must never become indistinguishable.

Unless a record contract explicitly supports cross-mode storage, backtest and simulated outputs should use dedicated record types, partitions, or clearly enforced mode fields. They must not pollute live operational history or live RAG retrieval.

Deterministic backtesting also requires projectors to preserve full numeric precision and authoritative timestamps. Rounding is allowed only in presentation layers.

## Practical Eligibility Test

Before promoting a node output into a curated record, answer these questions:

1. Is this a recognized business concept?
2. Is there one authoritative producer?
3. Is there a typed, versioned record contract?
4. Is there a stable and deterministic identity?
5. Is there an authoritative business timestamp?
6. Can the record be traced to its workflow, node, and source inputs?
7. Is it complete and trustworthy enough to persist?
8. Does it avoid duplicating an existing authoritative record?
9. Will the platform query, compare, audit, attribute, or reason over it later?
10. Is its correct destination PostgreSQL, RAG, telemetry, an artifact, or only the completed-run archive?

If questions 1 through 8 do not have clear answers, the output should remain in the completed-run archive until a deliberate domain contract and projection policy are approved.

## Governance Rule

No LLM, report formatter, generic serializer, or arbitrary projector should decide at runtime which output is “worthy.” Curation is a platform policy expressed through typed contracts, projector registration, schema versions, validation, and tests.

Adding a new curated record type should require:

1. A named domain concept and owner.
2. A typed model and schema version.
3. A deterministic identity and timestamp strategy.
4. Provenance and execution-mode rules.
5. A PostgreSQL persistence contract and migration when needed.
6. Explicit RAG and graph eligibility decisions.
7. Unit and integration tests covering idempotency, replay, and failure behavior.
8. Telemetry for projection attempts, successes, rejections, and failures.

## Summary

Polaris should retain the complete workflow execution for replay and audit, but only promote outputs that have stable domain meaning, authoritative ownership, deterministic identity, temporal meaning, provenance, and sufficient quality.

The resulting architecture is:

```text
Complete RuntimeContext and node outputs
    → completed-run archive for replay and audit

Eligible typed node outputs
    → deterministic projection layer
    → curated PostgreSQL records

RAG-eligible curated records
    → curated RAG documents
    → Qdrant semantic projection
    → Neo4j relationship projection
```

This separation prevents the platform from treating every serialized value as knowledge while ensuring that valuable workflow conclusions become durable, attributable, replayable, and retrievable platform memory.
