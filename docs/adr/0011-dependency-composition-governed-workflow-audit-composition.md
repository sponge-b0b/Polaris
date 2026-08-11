---
status: accepted
---

# 0011. Request-Scoped Governed Workflow Audit Composition

## Context

`WorkflowFacade` is the canonical workflow execution boundary, but governed
execution currently relies on optional caller wiring for both its automated
decision audit service and typed audit context. The facade is assembled in
application scope, while `AutomatedDecisionAuditService` is request-scoped
because it owns PostgreSQL-backed audit and review-task writes. A missing audit
context permits allow and warn outcomes to disappear, and cannot create the
evidence-scoped review work required for `REQUIRE_APPROVAL`.

## Decision

Polaris uses a dedicated request-scoped `GovernedWorkflowExecutionService` as
the sole interface-facing entrypoint for governed workflow execution. The
service:

* resolves `AutomatedDecisionAuditService` from the active request scope;
* requires and verifies a canonical `DecisionEvidencePacket` supplied by the
  producing use case;
* derives the stable workflow subject and constructs the typed
  `AutomatedDecisionAuditContext`; and
* passes an opaque execution-audit capability to the application-scoped
  `WorkflowFacade` for `run_workflow` and `run_from_context`.

When policy or governance enforcement is configured, the facade fails closed
without that capability. Runtime-only facade use remains available when neither
enforcement engine is configured. CLI and backtest entrypoints must use the
new service and fail with a typed governed-execution-evidence-required outcome
until they can supply canonical evidence; they must not synthesize authority or
evidence from workflow metadata or retain a direct-facade compatibility path.

`REQUIRE_APPROVAL` retains the lifecycle in ADR-0010: persist the automated
governance audit record and evidence-scoped review task before blocking
execution pending review.

## Rationale

This preserves one canonical runtime while keeping request-scoped persistence
and authoritative evidence validation in the application layer. The opaque
capability prevents governed execution from silently bypassing mandatory audit
composition, without making the runtime façade own database lifecycle or
authority classification.

## Consequences

Existing interface and backtest callers require migration to the service and
must provide provenance-bearing evidence. Direct governed façade callers and
tests must use the service-issued capability or explicitly configure an
unenforced runtime. This realization-required decision is implemented.
