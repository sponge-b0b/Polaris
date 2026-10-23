---
name: to-tickets
description: Decompose one deterministic Spec contract or structured Spec Review remediation contract into executable tickets with human-approved slicing and exact machine coverage.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# To Tickets

## Authoritative procedure composition

Before executing this skill, read `.agents/skills/to-tickets/PROCEDURE.md` in full. That
file preserves the complete current `$to-tickets` procedure. This `SKILL.md` is the
entrypoint and owns the transition override below; on conflict, this file wins. Failure to
load the retained procedure is a hard blocker.

The retained procedure continues to own Human approval, the Spec Branch Guard,
`Ticket baseline: Pending`, native children, `ready-for-agent`, Publication/readback,
Frontier handoff, `polaris.review-remediation-contract/v1`,
`python -m scripts.review_remediation build`, and `Review Remediation Contract Hash`.

## 9A. Routed architecture-blocker finalization

For an ordinary Spec reconciliation that includes existing open implementation tickets,
inspect every such ticket for the machine-managed marker:

```text
<!-- architecture-blocker:v1 -->
```

Require exactly zero or one marker comment per open reconciliation ticket. More than one is
contradictory durable state and fails closed. Classify the one marker, when present, using
the current `unresolved | routed | resolved` lifecycle owned by
`$architecture-remediation`.

* `unresolved` — the material choice still lacks durable resolving authority. Do not ask for
  ticket-publication approval; route the exact blocker through `$architecture-remediation`.
* `routed` — re-evaluate the complete persisted blocker question against current accepted
  authority and the current Parent Spec. If the governing decision/authority is not
  terminal and current, the Parent Spec has not consumed the resolving authority, any
  persisted blocker question remains unanswered, or the evidence is ambiguous, do not
  mutate the marker and do not classify the ticket design-ready. Route stale Spec projection
  to `$to-specs`; route unresolved material authority to `$architecture-remediation`.
* `resolved` — require a non-empty disposition naming the controlling accepted authority
  and continue. A malformed or authority-free resolved marker fails closed.

A `routed` marker is eligible for deterministic finalization only when all persisted blocker
questions are directly determined by current accepted authority, that authority is durable,
the current Parent Spec has consumed the resolving state, and no material ticket-owned
design choice remains. For every eligible `routed -> resolved` transition:

1. preserve the existing marker, source workflow/artifact, Parent Spec, governing Wayfinder
   when present, blocker questions, evidence, material consequences, blocked cells, and
   routing provenance exactly;
2. update only `**Status:** routed` to `**Status:** resolved` and the `### Disposition` text
   needed to name the exact controlling decision/CCL/ADR/Spec-reconciliation authority;
3. PATCH that same managed comment in place — never create a replacement blocker report;
4. GET the exact comment back and require the persisted body to equal the intended body;
5. retain this current-run receipt:

```text
ARCHITECTURE BLOCKER FINALIZATION: PASS
Ticket: #<n>
Transition: routed -> resolved
Controlling authority: <exact durable authority>
Parent Spec consumes authority: yes
Readback exact: yes
```

This is deterministic lifecycle-state reconciliation, not approval or publication of new
ticket semantics. It is the only pre-approval mutation authorized by this gate. Do not
change the ticket body, labels, dependencies, hierarchy, coverage manifest, branch/baseline,
or implementation candidate here. Outside an active `$architecture-remediation` routing
invocation, this is the only downstream `$to-tickets` authority to mutate an
`architecture-blocker:v1` report. `$implement-ticket` never self-resolves an `unresolved` or
`routed` marker.

Before the formal pre-publication `$attention` checkpoint and before asking for human
approval, require:

```text
Architecture blocker markers inspected: <n>/<n open reconciliation tickets>
Routed blockers requiring finalization: <n>
Routed blockers finalized/read-back: <n>/<n>
Unresolved/routed blockers remaining on design-ready tickets: 0
```

A blocker-state change under this gate does not change the frozen deterministic ticket
partition. If its re-evaluation instead reveals a material semantic or planning change, the
proposal is stale: stop at the owning workflow rather than finalizing the marker.

## 10. Human approval

Section 10 of the retained procedure remains authoritative with this additional hard
precondition: the Section 9A finalization gate above completes before the formal
`Checkpoint: $to-tickets pre-publication` Attention result and before approval is requested.
Validate that exact formal result through the shared machine consumer boundary:

```bash
python -m scripts.workflow_attention validate \
  --result <attention-result-file> \
  --checkpoint '$to-tickets pre-publication' \
  --require-nonblocking
```

A nonzero result prevents approval. The mandatory Pre-publication workflow receipts must
additionally include exactly:

```text
Architecture blocker markers inspected: <n>/<n open reconciliation tickets>
Routed blockers requiring finalization: <n>
Routed blockers finalized/read-back: <n>/<n>
Unresolved/routed blockers remaining on design-ready tickets: 0
```

These four lines must reflect exact current-run inspection/readback under Section 9A; they
may not be inferred from ticket labels, proposed wording, or remembered state.

### Pre-publication Spec Branch Guard

The retained guard is unchanged. Human approval authorizes the approved ticket delta;
it does not waive branch lifecycle
safety. `SPEC BRANCH GUARD: PASS`, `## Workspace Metadata`, GitHub Development linkage,
and `origin/SPEC_BRANCH` remain mandatory. A failed predicate still stops with zero ticket-publication
mutations.

## 11. Publication/readback

The retained publication/readback procedure is unchanged. `ready-for-agent` remains
readiness projection, not authority. Do not
apply it before the branch guard or before exact ticket/body/hierarchy/dependency validation. Re-read
label state after mutation.

## 12. Frontier handoff

After publication/readback is complete, evaluate the **complete actionable frontier**. Use
the retained Section 12 actionability predicates for every current open ticket in the
current `$to-tickets` scope. Do not stop after the first actionable ticket and do not use
`ready-for-agent` alone as actionability authority.

Collect every ticket that satisfies all current predicates. Preserve deterministic ordering:

* ordinary tickets: ordinary destination/topology order (`T1`, `T2`, ...), restricted to the
  currently actionable subset;
* review-remediation tickets: review-remediation proposal alias order, restricted to the
  currently actionable subset.

If zero tickets are actionable, do not emit an implementation Human Handoff and do not
invent an empty manifest. Report the exact durable blocker/dependency state that prevents a
frontier and remain at the owning workflow boundary.

If one or more tickets are actionable, create one `polaris.workflow-handoff/v1` manifest
with:

```text
boundary: human-lifecycle
durability.verified: true
handoffs: one handoff entry for every actionable ticket
```

Every handoff entry uses destination `$implement-ticket` and the ticket's exact current
tracker title plus canonical GitHub issue URL. The durability sources must be sufficient for
a fresh `$implement-ticket` session to recover all correctness-critical state. At minimum
include the current Parent Spec URL and every actionable ticket URL; include additional
durable managed-comment/artifact URLs when they are required for fresh-session recovery.
Sources must be canonical and unique.

Generate the terminal handoff only through the shared gate:

```bash
python -m scripts.workflow_handoff generate \
  --manifest <handoff-manifest.json> \
  > <handoff-output.txt>
python -m scripts.workflow_handoff verify \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

Require exact:

```text
WORKFLOW HANDOFF: VALID
```

The user-visible terminal Human Handoff block must then reproduce the generated
`<handoff-output.txt>` **byte-for-byte**. It therefore begins with `WORKFLOW HANDOFF: READY`,
contains one `$implement-ticket - <Ticket Title> (<Ticket URL>)` line for **every**
actionable frontier ticket in the deterministic order above, and ends with the verified
fresh-session durability receipt and manifest SHA-256.

Do not emit a bare `$implement-ticket` line, do not manually reconstruct the generated
block, do not omit a second or later independently actionable ticket, and do not terminate
this invocation as a successful Human Handoff if generation or verification fails.
