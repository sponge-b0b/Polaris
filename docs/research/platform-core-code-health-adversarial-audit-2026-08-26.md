# Polaris Platform Core Adversarial Semantic and Migration-Completeness Audit

## Purpose

This audit extends the detector-driven platform core code-health audit in
[`platform-core-code-health-audit-2026-08-25.md`](platform-core-code-health-audit-2026-08-25.md).
It does not replace or reinterpret that historical snapshot. Its purpose is to
find defects that ordinary static analysis, test coverage, complexity metrics,
and duplicate-code scanners are unlikely to detect reliably:

- incomplete ownership migrations;
- stale compatibility surfaces after a canonical replacement;
- production behavior widened for test doubles;
- dead or contradictory public/internal contracts;
- dependency and configuration ownership drift;
- speculative or abandoned subsystem scaffolding;
- documentation/runtime contradictions; and
- bypass or fallback paths that conflict with current architectural authority.

Audit date: 2026-08-26

Audited branch: `main`

Audit head before this addendum: `a3b4aa0d0189f996ab8ff4e28c3e2b20eb400cb8`

The earlier audit remains authoritative for its recorded scanner, complexity,
coverage, hotspot, and structural-candidate measurements. This addendum is a
semantic migration-completeness pass over the current repository and its change
history.

## Method

The audit used an invariant-first review rather than treating text search as the
proof mechanism.

For each ownership-changing or breaking migration, the review asked:

1. What contract or responsibility became canonical?
2. Which superseded contract, dependency, setting, representation, or execution
   path should therefore have disappeared?
3. Which production consumers, tests, test doubles, documentation, package
   declarations, and configuration surfaces were required to migrate with it?
4. Does any surviving path bypass or weaken the new owner?
5. Is a fallback a legitimate boundary/recovery behavior, or compatibility
   residue preserving an obsolete internal contract?
6. If a new defect class is discovered, does the same class exist elsewhere in
   the repository?

Historical commits whose messages contained replacement or migration signals
were sampled adversarially, including `compatibility`, `tolerate`, `legacy`,
`deprecated`, `bypass`, and `fallback`. Current architecture, ownership-ledger,
persistence, configuration, CLI, dependency, test-double, and subsystem surfaces
were then checked against those histories.

A finding was promoted only when current architectural authority and current
source supported it. Suspicious-looking constructs that were valid at an
external boundary or still had an active owner were rejected rather than
normalized into cleanup work.

## Defect taxonomy discovered by the pass

The pass produced five semantic defect classes that were not systematically
covered by the original scanner-driven audit:

1. **Semantic dead API / contract ownership drift** — an API continues to accept,
   expose, or advertise authority that a migration made unreachable or moved to
   another owner.
2. **Test-induced production polymorphism** — production accepts a broader or
   weaker object contract because a test double does not satisfy the real
   production contract.
3. **Dependency-contract drift** — implementation ownership moves, but the
   package/dependency declaration does not migrate with it.
4. **Documentation/runtime contract inversion** — the executable or documented
   interface promises one behavior while implementation deliberately forces the
   opposite.
5. **Ambient configuration ownership drift** — supported behavior is controlled
   through ad hoc environment access outside the canonical typed configuration
   owner.

The pass also expanded the existing stale/speculative-scaffolding class beyond
what the original audit sampled.

## Findings

### CH-POST-002 — CLI governance contract and composition drift

**Disposition:** Refactor Spec

**Confidence:** high

The governed-execution ownership migration exposed two layers of incomplete CLI
conformance.

First, the audit found immediate migration fallout: the CLI was still passing
`execution_id=None` to `GovernedWorkflowExecutionService.run_workflow()` after
that caller-owned argument had been removed. The corresponding unit fake still
expected the removed argument. Those two closure defects were corrected during
this audit:

- `43a4e4d48302806552ee4a4bb8a17f9b46eddc81`
  `fix(cli): align governed execution contract`
- `a3b4aa0d0189f996ab8ff4e28c3e2b20eb400cb8`
  `test(cli): align governed execution fake contract`

That closure pass exposed the deeper issue rather than resolving it.

`WorkflowCommandService` contains structural governance detection built around
attributes that may be absent or set to `None`. Its historical origin is the
commit named `fix(cli): tolerate ungoverned facade doubles`. The resulting
production behavior exists so incomplete test doubles can masquerade as a
`WorkflowFacade` shape instead of tests satisfying the production contract.

This is test-induced production polymorphism. Production should not broaden its
accepted internal contract solely to preserve weaker test doubles.

The composition path reinforces the same root problem. Current
`interfaces/cli/bootstrap/container.py` builds `cli_runtime_scope()` through
`application_sync_request_scope`, while current platform architecture identifies
the asynchronous Dishka container as the canonical asynchronous entry point and
reserves synchronous composition for boundaries that require it, including
deterministic backtesting. Governed execution services depend on asynchronous
persistence capabilities, so the CLI's sync request scope and its conditional
fallback behavior form one coherent conformance problem rather than independent
style issues.

The Refactor Spec should:

- make the CLI use the canonical request-scope/composition contract appropriate
  for its async execution model;
- resolve governed execution through the real production contract rather than
  facade-shape duck typing;
- remove production polymorphism whose only consumer is an incomplete test
  double;
- migrate tests/fakes to the canonical production contract rather than preserving
  compatibility behavior in production; and
- preserve legitimate truly-ungoverned runtime behavior where the canonical
  facade itself defines it.

This finding does **not** imply that every direct
`WorkflowFacade.run_workflow()` call is a governance bypass. The facade's
ungoverned execution mode remains legitimate when policy/governance capabilities
are absent by design.

### CH-POST-003 — interactive workflow control migration incomplete

**Disposition:** Refactor Spec, preferably the same CLI governance/control spec as
CH-POST-002

**Confidence:** high

Interactive workflow control remains an accepted current capability. Current
platform architecture lists cooperative pause/resume/cancel as a runtime
capability; the ownership ledger assigns pause/resume/cancel to
`WorkflowControlManager` through `WorkflowFacade`; and the current interface
section describes the Typer CLI as supporting workflow execution and control.

The governed execution-correlation migration removed caller-owned execution IDs
without completing the replacement path for interactive control. Current command
service behavior rejects interactive control because no platform-issued
correlation is available, while the old request fields and control-session
orchestration remain in the source tree. Code that depends on a control session
therefore becomes unreachable once `interactive_control=True` raises.

The public/runtime contract also contradicts itself: the CLI help advertises
interactive workflow control as enabled by default while the relevant command
constructs its request with `interactive_control=False`.

This is simultaneously:

- semantic dead API caused by an incomplete ownership migration; and
- documentation/runtime contract inversion.

The correct remediation is **not** to delete interactive workflow control merely
because the current path cannot use it. Current architecture still assigns and
advertises that capability. The Refactor Spec should restore control using the
platform-issued execution correlation and the canonical
`WorkflowControlManager`/`WorkflowFacade` boundary, then delete the now-obsolete
compatibility/dead branches that existed only because correlation ownership was
incomplete.

### CH-POST-004 — direct Ollama dependency survived the LiteLLM ownership migration

**Disposition:** Direct cleanup after an exact implementation-time import sweep

**Confidence:** high

The LiteLLM migration established the proxy/gateway as the application LLM
boundary and removed the direct Ollama application client. The completed
migration plan records that `core/llm/ollama_client.py` and
`Settings.OLLAMA_HOST` were removed, active application code no longer imported
Ollama directly, and Ollama became a LiteLLM backend rather than a Polaris core
application dependency.

Current `pyproject.toml` nevertheless still declares the Python `ollama` package
as a direct Polaris dependency. The canonical gateway communicates with the
LiteLLM proxy through the OpenAI-compatible client, so the package declaration
survived after implementation ownership moved.

This is dependency-contract drift.

The implementation batch should perform one exact repository import/reference
sweep before deleting the dependency because GitHub's code-search index returned
incomplete/empty results during this audit and is not sufficient evidence by
itself. The migration's own completed import audit, current gateway ownership,
and current package declaration are sufficient to promote the finding; the final
local sweep is the deletion guard.

This finding concerns the **Python application dependency** only. It does not
remove or prohibit Ollama as a configured backend behind LiteLLM.

Related dependency hypotheses were rejected:

- `langgraph` remains an active RAG orchestration dependency;
- `uvicorn` remains active through the MCP Streamable HTTP transport; and
- the Python `litellm` package was not classified as dead because current
  evaluation integration uses LiteLLM-backed evaluation support.

### CH-POST-005 — morning-report persistence bypasses typed configuration ownership

**Disposition:** Direct conformance

**Confidence:** high

`interfaces/cli/commands/morning_report_command.py` reads
`POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE` directly from `os.environ` through a
private helper. The switch therefore lives outside the repository's canonical
typed settings authority.

The feature itself is valid and current. PostgreSQL persistence documentation
explicitly documents `POLARIS_ENABLE_POSTGRES_REPORT_PERSISTENCE`, and reports
have a canonical application persistence boundary. This is not evidence that the
feature should be removed.

The defect is ambient configuration ownership drift: a supported production
behavior is configured through an ad hoc interface-local environment lookup
rather than canonical typed configuration.

Direct conformance should:

- add the supported switch to its canonical typed settings owner;
- consume that typed setting at the appropriate application/interface boundary;
- remove the interface-local `os.environ` parser; and
- retain the existing report-persistence ownership and governed release checks.

A stronger hypothesis — that CLI morning-report persistence duplicates the
workflow-output projection subsystem — was rejected. Workflow-output projection
curates eligible typed domain outputs; the CLI path publishes a rendered
`MorningReportDocument`. They are different persistence responsibilities.

### CH-POST-006 — speculative subsystem scaffolding is broader than the original audit recorded

**Disposition:** Direct cleanup after reachability/reference confirmation

**Confidence:** high for the empty subsystem skeletons; normal deletion guard
required before each batch

The original code-health audit identified isolated empty bootstrap modules. An
independent adversarial interface sample found a substantially broader stale
surface.

The HTTP API tree under `interfaces/api/` consists of empty implementation
scaffolding, including the main/auth/dependency modules, named route modules, and
the websocket live-updates module. The sampled UI surface under `interfaces/ui/`
is likewise namespace scaffolding without an implemented user interface. The
LLM package also contains long-lived zero-byte named placeholders including:

- `core/llm/embeddings.py`;
- `core/llm/model_router.py`; and
- `core/llm/reranker.py`.

History shows the sampled API/UI/LLM placeholders originated with the initial
repository import and were not subsequently developed into supported
responsibilities.

Current architecture documentation explicitly calls the HTTP API tree
non-production scaffolding and states that API/scheduler/UI surfaces are not
production interfaces until intentionally implemented. That description is
useful evidence of current status, but it is not a reason to retain empty
implementation topology indefinitely. Current coding standards prohibit
speculative abstractions/public APIs and temporary scaffolding that has no
present requirement.

Cleanup should remove only proven-unreferenced empty scaffolding and update
current descriptive documentation in the same batch so documentation does not
continue to claim a skeleton exists after deletion. Future API/UI work should
create the required structure when a concrete feature owns it rather than
pre-allocating a speculative subsystem.

No package should be removed merely because it appears related to an empty
subsystem. For example, `uvicorn` has an independent live MCP owner. Dependency
cleanup requires its own consumer proof.

## Negative controls and rejected hypotheses

The audit deliberately kept negative controls so suspicious syntax or migration
history was not automatically promoted to work.

- The Firecrawl to Crawl4AI/SearXNG replacement was sampled and showed no active
  Firecrawl contract in the authoritative settings/dependency surfaces checked.
- The structured strategy-contract replacement showed deliberate migration
  closure and no evidence that a generic legacy strategy compatibility contract
  had been reintroduced.
- `AliasChoices` is not intrinsically compatibility debt. Environment/boundary
  aliases may be legitimate external compatibility when the internal canonical
  contract remains singular.
- Direct `WorkflowFacade.run_workflow()` is not intrinsically a governance
  bypass. A genuinely ungoverned facade may execute directly according to the
  facade's own invariant.
- Morning-report publication is not the same durable responsibility as
  workflow-output curation merely because both ultimately use PostgreSQL.
- LangGraph and Uvicorn remain live dependencies in current RAG/MCP ownership.
- `litellm` was not declared a dead package solely because the core gateway uses
  an OpenAI-compatible client; evaluation integration still provides a material
  LiteLLM-related consumer.
- A historical `tolerate` hit in RAG/model-output handling was retained as
  external-model normalization rather than treated as internal compatibility
  residue.
- `compatibility`, `legacy`, `deprecated`, `bypass`, and `fallback` history
  sampling produced no additional semantic defect class after the findings
  above. Most fallback/bypass references were legitimate recovery,
  circuit-breaker, renderer, policy/governance, or boundary behavior.

These rejected hypotheses are part of the audit evidence. The goal is migration
completeness and correct ownership, not maximal deletion.

## Saturation result

The audit reached semantic saturation when independent history/interface samples
stopped producing new defect classes. Subsequent observations mapped into the
already-known stale/speculative-scaffolding family or were rejected as legitimate
boundary/recovery behavior.

The saturated taxonomy is therefore:

- semantic dead API / contract ownership drift;
- test-induced production polymorphism;
- dependency-contract drift;
- documentation/runtime contract inversion;
- ambient configuration ownership drift; and
- stale/speculative scaffolding.

This does not claim that no undiscovered defect can ever exist. It means the
adversarial passes stopped discovering new *classes* of semantic migration defect
at the current repository state, and an independent keyword/history sample did
not reopen the taxonomy.

## Revised remediation order

The semantic audit changes the order of the remaining code-health work:

1. Preserve the completed behavioral/static baseline and standards hardening.
2. Complete direct conformance and dead-surface cleanup:
   - stale `web` packaging/configuration residue from the original audit;
   - original empty bootstrap modules;
   - expanded API/UI/LLM speculative scaffolding;
   - verified dead symbols from the original audit;
   - the direct Python `ollama` dependency after the implementation-time sweep;
   - typed ownership for the report-persistence switch.
3. Create one focused CLI governance/control Refactor Spec covering CH-POST-002
   and CH-POST-003:
   - canonical CLI DI/composition;
   - removal of fake-driven production polymorphism;
   - platform-issued governed execution correlation; and
   - restoration of supported interactive pause/resume/cancel behavior.
4. Continue the previously identified structural Refactor Specs:
   - durable-job claim-transition duplication;
   - workflow-output projection orchestration;
   - decision-evidence persistence decomposition; and
   - local risk-authority-gate decomposition.
5. Run the zero-unsuppressed-duplication campaign after scanner semantics are
   frozen/verified for the intended Arid release.
6. Perform an independent residual saturation/random sample after structural and
   duplication remediation.
7. Finish with the full behavioral, static, migration, and code-health baseline.

No new Wayfinder is required by this audit. Current architecture already defines
the owners needed to route these findings; the unresolved work is conformance,
migration completion, and focused refactoring rather than architectural
ambiguity.

## Closure rule carried forward

A migration is not complete when the new owner compiles or its immediate tests
pass. It is complete only when every affected production consumer, test, test
double, dependency declaration, configuration surface, documentation contract,
and obsolete representation has either migrated to the canonical owner or been
explicitly proven to remain a valid independent boundary.

That rule is the durable lesson from this audit. The two CLI governed-execution
closure commits above were found precisely because the migration was re-audited
from its contract boundary rather than from the file initially changed.
