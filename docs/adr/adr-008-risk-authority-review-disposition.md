# ADR-008: Risk Authority Spec Review Disposition

## Status

Accepted

## Context

Issue #64 introduced the canonical risk tier and authority contract. The first
spec review for that work compared `1462412...HEAD` and created review parent
#78 plus remediation ticket #79 because the diff contained broad `core/`,
agent-skill, notebook/plugin metadata, provider/client, CLI, and formatting
churn in addition to the risk-authority implementation.

Repository rules require explicit user authorization before modifying `core/`.
The #64 specification required preservation of runtime and workflow boundaries,
but it did not itself provide blanket approval for unrelated `core/` edits or
for runtime contract changes.

The review diff characteristics that triggered #79 were:

- fixed point: `1462412` (`146241227feb77c6b24ca6ace8671e1dee1f726d`)
- review command: `git diff 1462412...HEAD`
- changed files: 963 total
- changed `core/` files: 249 total, with 1,703 added lines and 2,534 deleted
  lines at the time of the #79 disposition
- broad non-authority areas also touched: agent skills, notebooks, plugin
  metadata, provider/client modules, CLI modules, and repository-wide tests

## Decision

The risk-authority remediation trail records that #64 did **not** provide a
pre-existing blanket authorization for broad `core/` churn. #79 does not
retroactively authorize hidden runtime or workflow contract changes.

Instead, the accepted disposition is:

1. Keep any `core/` changes visible in the review history and subject them to
   the #85 re-review exit gate.
2. Treat ordinary formatting or lint-suppression cleanup as separate review
   work, tracked by #80.
3. Treat canonical risk-authority behavior remediation as separate vertical
   work, tracked by #81 through #84.
4. Do not add further `core/` changes during remediation unless the active
   ticket explicitly explains the architectural need and the user authorizes
   that narrower `core/` change.
5. If re-review finds a remaining runtime or workflow contract change without
   an explicit authorization trail, it must be split into a new review finding
   rather than treated as approved by #64 or this ADR.

## Rationale

This makes the review trail explicit without hiding broad churn inside a passing
spec review. It also avoids rewriting large amounts of already-landed work in a
single corrective ticket, while preserving the repository rule that stable core
contracts require explicit user authorization.

The follow-up remediation tickets are intentionally separated so a fresh review
can distinguish:

- architecture authorization and blast-radius disposition (#79)
- formatting/lint-suppression cleanup (#80)
- authority-contract deduplication and dispatch cleanup (#81)
- evaluation fail-closed behavior (#82)
- retention-policy integration (#83)
- MCP/tool-response authority metadata (#84)
- final two-axis review exit gate (#85)

## Consequences

- #64 is not considered blanket approval for broad or unrelated `core/` edits.
- Future `core/` modifications in this remediation series need their own clear
  approval trail.
- The remaining review findings can be addressed without mixing architectural
  authorization, formatting cleanup, and feature behavior in one ticket.
- The #85 review must verify that no unapproved runtime/core contract change is
  hidden inside the final diff.

## Affected Issues

- #64 — Spec: Canonical risk tier and authority contract
- #78 — Spec Review: Canonical risk tier and authority contract
- #79 — Resolve unauthorized core and unrelated churn in the review diff
- #80 — Remove line-length suppressions added by the spec work
- #81 — Centralize authority metadata coercion and tier dispatch
- #82 — Make evaluation readiness fail closed on missing non-baseline authority
- #83 — Drive retention decisions from canonical risk authority metadata
- #84 — Expose canonical authority metadata on MCP tool responses
- #85 — Re-run the spec review exit gate
