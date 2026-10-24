---
name: implement-ticket
description: Implement one exact deterministic ticket contract, run applicable technical checks, obtain fresh independent closure proof, and close only the exact certified candidate.
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Implement Ticket

## Authoritative procedure composition

Before executing this skill, read all of these files in full:

1. `.agents/skills/implement-ticket/PROCEDURE.md`
2. `.agents/skills/implement-ticket/EXECUTION_ANCHOR.md`
3. `.agents/skills/implement-ticket/CONTROL_PLANE.md`
4. `.agents/skills/implement-ticket/PRE_IMPLEMENTATION_FEASIBILITY.md`

`PROCEDURE.md` preserves the complete established implementation lifecycle.
`EXECUTION_ANCHOR.md` preserves the accepted Execution Anchor correction.
`CONTROL_PLANE.md` preserves the previously authoritative entrypoint through the protected
control-plane boundary and shared Human Handoff repair.
`PRE_IMPLEMENTATION_FEASIBILITY.md` adds the mandatory fail-fast provider/authority closure
boundary that runs before pre-mutation Attention or substantive candidate mutation.

This `SKILL.md` is now the authoritative entrypoint and adds the durable machine-readable
cell-routing-defect evidence boundary below. On conflict, this file wins. Failure to load any
retained file is a Hard Blocker.

All requirements in the retained files remain mandatory unless explicitly overridden here.

## Fail-fast live recovery and feasibility boundary

The retained lifecycle is strengthened so that `$implement-ticket` proves that the ticket can
legally execute **before** spending implementation or closure-verification work.

### Live recovery donor validation

When durable state contains a current `ticket-reslice-recovery:v1` record naming this ticket,
the existing schema validator is necessary but not sufficient. Before ordinary Ticket-baseline
handling, pre-mutation Attention, donor transplant, or substantive mutation, validate the
**live protected donor checkout** against the durable record.

Execute both validators from exact current default-branch control-plane runtime using the
same clean detached-default-branch rule already required for recovery validation:

```bash
python -m scripts.workflow_reslice_recovery validate \
  --body <recovery-comment-body-file>
python -m scripts.workflow_reslice_donor validate \
  --body <recovery-comment-body-file>
```

Require exact leading receipts:

```text
TICKET RESLICE RECOVERY: VALID
TICKET RESLICE DONOR: VALID
```

The live-donor validator is read-only. It requires the recorded protected checkout to exist
and requires exact durable identity for:

- recorded Source branch attachment (a detached checkout is not equivalent);
- protected donor HEAD / Execution Anchor;
- protected donor candidate-state hash over final tracked/untracked bytes and modes;
- protected donor source-ticket Attention-receipt file SHA-256.

A mismatch is a Hard Blocker **at preflight**. Do not postpone donor fingerprint validation to
pre-closure or Human Handoff. Never repair the donor implicitly; report the exact mismatch and
leave the donor untouched.

### Pre-implementation provider/authority closure

After rebuilding and validating the exact current ticket/remediation contract, but before the
retained Section 4 pre-mutation Attention checkpoint, execute
`PRE_IMPLEMENTATION_FEASIBILITY.md` in full.

This boundary is read-only with respect to the candidate. It must:

1. reconsider materially applicable prior verifier findings against the current contract and
   current production surface;
2. enumerate every required production provider/composition seam for assigned cells;
3. resolve the durable owner and native GitHub dependency relation for each external seam;
4. prove that externally owned seams are already available from an upstream/completed route;
5. distinguish real production providers from fakes, fixtures, mocks, or test-only injection;
6. emit exactly one `IMPLEMENT TICKET FEASIBILITY: PASS` or
   `IMPLEMENT TICKET FEASIBILITY: BLOCKED` receipt.

`BLOCKED` is terminal routing evidence for this invocation. In particular:

- same-Spec cells assigned to the wrong route -> `cell-routing-defect` -> `$to-tickets`;
- no new material semantics, but required production work is absent from an upstream route,
  owned by a downstream Spec/ticket, or omitted from executable planning ->
  `planning-cell-gap` -> `$to-specs`;
- missing/ambiguous material semantic authority -> `contract-authority-gap` -> governing
  semantic owner;
- concrete external/environment/tool failure that prevents the proof -> Hard Blocker.

On a feasibility `BLOCKED` result, do not continue to broad tests, architecture verification,
deduplication, wiki sync, pre-closure Attention, or independent closure verification. Preserve
the candidate as-is and route through the existing durable Human Handoff contract.

An explicit `resume $implement-ticket` does not bypass either live-donor validation or the
feasibility boundary. Existing candidate work may be inspected read-only to classify current
ownership, but it does not authorize additional mutation until feasibility passes.

## Retained control-plane and handoff contract

An ordinary `$implement-ticket` invocation still has zero authority to alter repository
workflow/control-plane or semantic-authority files. There is deliberately **no `$implement-ticket` bypass flag**.
The retained `scripts.workflow_candidate_guard check` and `restore-protected` mechanics remain mandatory.

Every terminal **Human Handoff** from `$implement-ticket` still uses the shared handoff gate.
This includes verifier `cell-routing-defect` -> `$to-tickets`, verifier `planning-cell-gap` -> `$to-specs`,
and `contract-authority-gap` routing to its exact semantic owner.

The retained downstream artifact rules remain exact:

- `$to-tickets` receives the exact current Parent Spec issue.
- `$to-specs` receives the exact current planning source for the Parent Spec.
- A current Spec issue is a durability source, not a substitute planning source.
- `$implement-ticket` receives each exact current actionable ticket issue.
- `$verify-spec` receives the exact current Parent Spec issue.

The shared gate remains:

```bash
python -m scripts.workflow_handoff generate \
  --manifest <handoff-manifest.json> \
  > <handoff-output.txt>
python -m scripts.workflow_handoff verify \
  --manifest <handoff-manifest.json> \
  --output <handoff-output.txt>
```

and still requires `WORKFLOW HANDOFF: VALID`. The terminal output remains byte-for-byte generated output.
A recommendation, prose instruction, or bare downstream skill command is **not** a Human Handoff.
Do not emit a bare `$to-specs`, `$to-tickets`, `$architecture-remediation`, `$implement-ticket`, or `$verify-spec` line as a terminal Human Handoff.

For a normal post-closure frontier, evaluate the complete current actionable ticket frontier.
Do not stop after the first actionable ticket. Emit one manifest handoff entry per actionable ticket.

## Durable cell-routing-defect evidence boundary

A `cell-routing-defect` is correctness-critical planning evidence. It must not exist only as
free-form prose that a later `$to-tickets` or `$to-specs` session can overlook.

Before any terminal Human Handoff caused by a `cell-routing-defect`, persist or update exactly
one durable ticket comment containing a machine-readable `workflow-routing-defect:v1` marker.
The marker must be validated before it is posted.

Create the marker JSON outside the repository candidate and run:

```bash
python -m scripts.workflow_routing_defects validate-marker \
  --file <routing-defect-marker.json>
```

Require exact:

```text
WORKFLOW ROUTING DEFECT MARKER: VALID
```

Then persist the exact validated object inside this comment marker:

```text
<!-- workflow-routing-defect:v1
{
  "schema": "polaris.workflow-routing-defect/v1",
  "defect_id": "<stable id>",
  "status": "open",
  "classification": "cell-routing-defect",
  "source_ticket": <current ticket>,
  "parent_spec": <current parent Spec>,
  "affected_cells": ["<exact current Spec cell>", "..."],
  "required_local_provider_cells": ["<exact same-Spec provider cell>", "..."],
  "reason": "<why the current assigned route cannot complete/prove the affected cell>",
  "basis": ["<durable ticket/spec/verification source>", "..."]
}
-->
```

Rules:

- `defect_id` is stable across retries of the same defect; do not create duplicate open
  markers for one defect.
- `affected_cells` names the exact current Spec cells whose present route is defective.
- When completion depends on existing cells elsewhere in the same Parent Spec,
  `required_local_provider_cells` must name those exact provider cells. Do not record
  historical ticket numbers or execution-unit IDs as the provider authority.
- If a routing defect is proven but the exact same-Spec provider cells cannot yet be
  identified without making a planning choice, use an empty `required_local_provider_cells`
  list. This intentionally causes the upstream `$to-specs` routing-defect gate to fail closed
  rather than allowing the defect to be silently omitted.
- `reason` and `basis` must make the completion/proof dependency recoverable from durable
  state without chat context.
- Read the comment back after POST/PATCH and require the exact marker object to be present.
- Include that exact comment URL in the outbound shared-handoff durability sources.

This marker does not change semantic authority, ticket coverage, Spec topology, or native
GitHub dependencies. It is durable defect evidence only. `$implement-ticket` must not mark it
`resolved` merely because implementation stopped. The owning reconciliation workflow may
resolve/replace the routing state only after durable topology/coverage readback proves the
defect no longer blocks the current route.

## Interaction with existing routing

The retained classification still applies:

```text
cell-routing-defect -> $to-tickets
```

The machine marker does not skip `$to-tickets`. It ensures that if deterministic ticket
projection reveals that the defect is actually upstream Spec-topology infeasibility, a later
`$to-specs` run can mechanically discover and enforce the already-proven dependency instead
of relying on a prompt reminder or model memory.

No terminal routing handoff for a `cell-routing-defect` is valid unless the marker-validation
receipt, durable comment readback, and shared `WORKFLOW HANDOFF: VALID` receipt all exist.
