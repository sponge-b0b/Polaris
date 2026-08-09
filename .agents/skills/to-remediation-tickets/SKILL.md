---
name: to-remediation-tickets
description: Invoked only by `$to-tickets` during a Spec Review remediation re-invocation — not a standalone command. Recovers or synthesizes the Root Blocker Ledger from a `$review-spec` parent issue and performs strict delta analysis against existing child tickets before any new remediation tickets are drafted.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Remediation Tickets

This skill is invoked by `$to-tickets` partway through its Step 3 ("Draft vertical slices"), specifically when the source issue is a `$review-spec` parent issue (title prefixed `Spec Review: `) rather than a fresh spec. It replaces ordinary vertical-slice drafting for that case — the rest of `$to-tickets`'s process (Steps 1–2, and Steps 4–5 onward) still applies as normal. Once this skill hands back a ticket list, return to `$to-tickets` and continue at Step 4 (Quiz the user).

## Recover the Root Blocker Ledger

When the source issue is a `$review-spec` parent issue (`Spec Review: ...`), do
not slice directly from the latest finding bullets. First recover or synthesize
the parent issue's **Root Blocker Ledger**:

* Preserve the review's stable root IDs (`RB-1`, `RB-2`, ...), or create them if
  an older review issue predates the ledger format.
* Treat dated review bullets as evidence for roots. A bullet becomes a separate
  ticket only when it represents a distinct root invariant or a necessary
  independently-verifiable stage of that root.
* For each root, identify affected surfaces/reference kinds, the production path
  that must prove the invariant, and the acceptance-matrix cells that remain
  unproven or regressed.
* For Architecture roots, preserve `Architecture decision required` and
  `Governing authority` from the Root Blocker Ledger.
* `Architecture decision required: No` is ordinary remediation: slice the root
  normally and carry the governing ADR/doc references into the ticket's
  Architecture context.
* If any root has `Architecture decision required: Yes`, halt and return the
  unresolved architecture upstream. Do not resolve or ticket it here.
* Ticket the smallest root-complete remediation track: one ticket when a fresh
  context can fix and prove the root, or a short sequence when a prefactor/test
  harness must land before surface-by-surface fixes.

Each Spec Review remediation ticket must include:

* the root blocker ID and invariant it is meant to close;
* the sibling surfaces/reference kinds the implementer must audit;
* acceptance criteria that prove the real production path, not only a helper,
  validator, serializer, or isolated unit seam;
* negative/regression tests that would have failed for the root cause; and
* a requirement to report any remaining unproven root cells in the final handoff.

Do not create one issue per symptom when several symptoms share the same root.
Do not mark a closed matching ticket as sufficient unless current source truth
proves the root invariant across the affected production paths.

A Blocking Architecture finding is not itself evidence that architecture is
unresolved; only `Architecture decision required: Yes` blocks remediation slicing.

Use `$to-tickets`'s `local-ticket-template` or `issue-template` to publish these tickets — the `Root blocker` field exists specifically for this case.

## Delta Slicing Rules (For Re-Review Headers)

If the target input issue contains multiple dated review headers (e.g., `## Initial Findings`, `## Re-review Findings [2026-07-22]`), you must perform a strict delta analysis before generating any GitHub issues. This is exactly the case that routes execution here in the first place — the tickets drafted below still land on the *original* spec's branch, resolved by the Spec Branch Rule's Step 0 in `$to-tickets`, not a new one:

1. **Scan Linked Tree:** Pull the list of existing child issues already linked to this parent issue, including each issue's title, body, comments, state, and closing note when available.
2. **Recover the Root Ledger:** Read the Root Blocker Ledger and acceptance matrix from the parent issue (see above). If the parent predates the ledger format, synthesize stable root IDs by grouping the initial and dated Blocking findings by shared invariant before ticketing anything.
3. **Isolate the Newest Delta:** Focus detailed text parsing on the bullet points listed under the most recent chronological date header, then map each bullet to `new root`, `child symptom`, or `regression` in the ledger. Do not ignore older root text; use it to decide whether the newest bullet is really a new ticket or unfinished root evidence.
4. **Cross-Reference:** Compare the root and newest text findings against the titles/descriptions of the child issues that are already open or closed.
5. **Verify Closed Matches Against Current Truth:** A closed matching ticket is not automatically stale. Before skipping it, verify the finding against the current source of truth and the root invariant:

   * If the finding cites source code, inspect the current cited files/symbols and any named tests.
   * If the finding cites a standards, migration, documentation, branch, or tracker rule, inspect the current authoritative file, command output, or issue metadata for that rule.
   * If the finding is a child symptom of a root, inspect enough sibling surfaces/reference kinds to decide whether the closed ticket proved the root or only fixed the cited symptom.
   * If current evidence is ambiguous, treat the closed match as still actionable and create a regression ticket rather than skipping it.
6. **De-duplicate by State and Evidence:**

   * If a finding matches an **open** child ticket -> **Skip it as already tracked.**
   * If a finding matches a **closed** child ticket and current evidence shows the violation is fixed -> **Skip it as a stale duplicate.**
   * If a finding matches a **closed** child ticket and current evidence still confirms the violation, or a sibling surface proves the root was not completed -> **Graduate it into a new child ticket titled with a `Regression:` prefix.** Reference the older closed ticket and root blocker ID as historical context, but do not reopen or edit the closed ticket.
   * If a finding has no matching child ticket -> **Graduate it into a brand new root-scoped child ticket.**
7. **Report the Delta:** Print a summary telling the user exactly how many *new* tickets were added, how many *open duplicates* were skipped, how many *closed-and-fixed stale duplicates* were ignored, how many *closed-but-still-confirmed regressions* were added, and which root blocker IDs still have unproven acceptance-matrix cells.
