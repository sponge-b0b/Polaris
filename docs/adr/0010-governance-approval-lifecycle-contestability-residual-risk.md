---
status: accepted
---

# 0010. Governance Approval Contestability and Residual Risk

Date: 2026-08-03

## Context and Problem Statement

Polaris now records automated governance decisions, review tasks, human or
organizational review outcomes, residual-risk acceptance, and governed-output
release decisions. These semantics touch runtime governance, report publication,
workflow-output projection, future MCP transports, RAG answers, recommendation
surfaces, and audit reconstruction. Without one documented owner and writer,
interfaces could accidentally create their own approval queues, treat model text
as approval, reuse residual-risk acceptance across broader evidence, or publish
capital-relevant outputs while review work remains unresolved.

The architecture must preserve the policy/governance distinction: policy answers
"May this happen?" with `ALLOW` or `DENY`; governance answers "Should this
happen?" with `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, or `SKIP`. Human or
organizational review is a governance lifecycle above automated governance, not
a replacement policy engine and not model-declared readiness.

## Decision Outcome

Chosen option: "PostgreSQL-backed governance approval lifecycle owned by `AutomatedDecisionAuditService`", because it keeps automated governance evidence, review tasks, contestability outcomes, residual-risk acceptance, and governed-output release checks in one canonical application-service lifecycle while allowing interfaces and future MCP tools to remain thin transports.

`AutomatedDecisionAuditService` is the authoritative application owner for:

- automated governance audit records;
- evidence-scoped governance review tasks;
- approval-state read models;
- immutable review decisions for approval, denial, contest, requested changes,
  and override;
- explicit scoped residual-risk acceptance; and
- governed-output release decisions for capital-relevant publication or durable
  promotion.

`AutomatedDecisionAuditRepository` is the canonical persistence boundary, and
its PostgreSQL implementation writes the durable audit records. Logs, metrics,
traces, runtime events, report files, CLI output, MCP responses, Qdrant, and
Neo4j are observability, presentation, or projection surfaces rather than
approval sources of truth.

## Automated policy and governance outcomes

Policy and governance remain separate:

| Layer | Question | Automated outcomes | Approval semantics |
| --- | --- | --- | --- |
| Policy | May this happen? | `ALLOW`, `DENY` | Does not store human governance approval. |
| Governance | Should this happen? | `ALLOW`, `WARN`, `DENY`, `REQUIRE_APPROVAL`, `SKIP` | `REQUIRE_APPROVAL` can create a scoped review task when decision evidence exists. |

`ALLOW` and `WARN` are durable automated governance recommendations. `DENY` and
`SKIP` are durable and observable automated outcomes; they do not become pending
approval tasks by themselves. `REQUIRE_APPROVAL` records the automated
governance outcome and creates a review task keyed by subject, evidence packet,
evidence version, review scope, requested action, and intended sink when the
audit record includes the required evidence.

## Review task and contestability semantics

Governance review work is represented by a durable review task and immutable
review decision records. A reviewer may resolve a task with one of these
outcomes:

- `approved`
- `denied`
- `contested`
- `changes_requested`
- `overridden`

The externally visible approval states are derived from task status:
`pending_review`, `review_approved`, `review_denied`, `review_contested`,
`changes_requested`, `review_overridden`, and
`residual_risk_acceptance_required`.

A denial, contest, request for changes, or override never deletes or rewrites the
automated governance audit record. It appends an attributable decision record
with reviewer identity, actor type, rationale, reviewed evidence, requested
remediation when applicable, and resulting task status. Requested changes block
approval and publication until later canonical review work resolves the task.
An override is an attributable governance review outcome; it is not a model
escape hatch or an interface-local bypass.

## Residual-risk acceptance semantics

Residual-risk acceptance is human or organizational, scoped, explicit,
attributable, evidence-versioned, and durable.

For Vigilant risk tasks, an `approved` or `overridden` review with residual risk
remaining requires an explicit residual-risk acceptance before approval can take
effect. The acceptance record carries:

- reviewer identity and actor type;
- rationale;
- reviewed subject and risk tier;
- review scope;
- residual-risk scope;
- evidence packet ID and evidence version;
- acceptance timestamp; and
- optional validated metadata.

A residual-risk acceptance records the reviewed subject, review scope,
residual-risk scope, evidence packet, and evidence version. A later packet
version, different action, different sink, or broader residual-risk scope must be
represented by a new explicit acceptance rather than by mutating or
reinterpreting an old record. Model-generated text or metadata may not declare
residual risk accepted.

## Publication and durable-promotion blocking

Capital-relevant Enhanced and Vigilant outputs that are externally visible,
durably authoritative, or governance-impacting must pass the governed-output
release check before publication or durable promotion. The release check reads
canonical review tasks and residual-risk acceptance records. Release is blocked
when review evidence is missing, no matching approved/overridden task exists,
the matching task is pending, denied, contested, changes-requested, or cancelled,
or a required scoped residual-risk acceptance is absent for the evidence version.

Report persistence and workflow-output projection call the canonical release
service and preserve a blocked or skipped result instead of publishing, promoting,
or inventing local approval state.

## Audit reconstruction

A complete governance approval reconstruction begins with PostgreSQL records:

automated governance audit record -> governance review task -> immutable review
decision history -> residual-risk acceptance records -> governed-output release
decision, plus the decision evidence packet identifiers referenced by those
records.

`ApprovalLifecycleObservability` emits structured logs, counters, telemetry, and
trace-linked events for required approval, review resolution, review failure,
blocked release, automated denial, and automated skip. Those signals help
diagnose and discover the lifecycle, but they do not replace the durable audit
records.

## Future MCP and interface guidance

Future MCP, API, scheduler, or UI work must be a thin transport over the
canonical application services resolved through Dishka request scopes. If a
transport needs review listing, approval, denial, contest, requested changes,
overrides, residual-risk acceptance, or publication release checks, it must call
`AutomatedDecisionAuditService` or a canonical query service that delegates to
it. The interface must not implement an approval queue, residual-risk table,
publication gate, direct repository writer, RAG approval store, vector/graph
approval projection, or retry/resume/clear state machine outside the canonical
service.

## Consequences

- There is one authoritative owner and canonical writer for governance approval
  lifecycle records.
- Human and organizational reviewers remain attributable; model output cannot
  approve, contest, override, request changes, accept residual risk, or lower
  risk tier.
- Governed outputs fail closed when review state or residual-risk acceptance is
  missing, stale, or blocking.
- Interface and MCP work stays thin and compositional rather than becoming a
  second governance subsystem.
- Audit reconstruction can rely on PostgreSQL records and decision-evidence
  references instead of telemetry or presentation artifacts.
