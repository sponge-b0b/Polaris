# `$implement-ticket` pre-implementation feasibility boundary

This document is retained `$implement-ticket` policy. It is read-only with respect to the
product candidate and runs **after the exact current ticket/remediation contract is rebuilt
and before pre-mutation Attention or any substantive candidate mutation**.

Its purpose is fail-fast correctness: do not spend implementation, broad-verification,
deduplication, wiki-sync, or independent-verifier work on a ticket whose required production
providers or durable authority cannot yet exist at its current native position.

## 1. Reconsider durable prior findings

An archived or stale-candidate closure checkpoint is not current candidate authority, but its
findings remain historical evidence. Before implementation, enumerate prior verifier findings
that could still apply to the current contract or production seams.

For each materially similar finding, classify it from current durable state as one of:

- `RESOLVED_UPSTREAM` — current committed production state proves the missing seam now exists;
- `OWNED_BY_CURRENT_TICKET` — the current exact assigned cells authorize this ticket to provide
  the missing implementation/proof;
- `ROUTING_OR_PLANNING_GAP` — the required capability belongs outside the current route or is
  scheduled after the current ticket;
- `NO_LONGER_APPLICABLE` — current exact cells no longer require the behavior;
- `AMBIGUOUS` — ownership or applicability cannot be established without a material choice.

Do not silently discard a prior finding merely because its old candidate checkpoint was
archived. Do not silently carry the old finding forward as a current defect either; current
contract and production evidence decide.

## 2. Build the production provider-closure matrix

For every assigned cell that requires another owner, persistence adapter, query/service,
transaction participant, authoritative reader, composition root, or other production
collaborator, enumerate the **production** seam required for the cell to execute and be
proved.

Test fixtures, fakes, mocks, manually injected test-only readers, and future integrated tests
are evidence about a contract but do **not** by themselves count as a production provider.

For every seam record:

```text
Provider seam: <typed port/capability/composition boundary>
Required by cells: <exact OBL/IMP/TEST IDs>
Durable owner: <current Spec/ticket/domain authority>
Native dependency relation: <upstream | same-route | downstream | independent | unknown>
Production implementation: <path/symbol/commit evidence | absent>
Composition owner: <Spec/ticket | None>
Status: PRESENT_UPSTREAM | OWNED_BY_CURRENT_TICKET | DEFERRED_COMPOSITION | MISSING_UPSTREAM | AMBIGUOUS_OWNER
Basis: <durable sources>
```

`PRESENT_UPSTREAM` requires a real production implementation available to the current route.
A Protocol, interface, accepted CCL assertion, test fake, or downstream planned provider is
not sufficient.

`OWNED_BY_CURRENT_TICKET` requires exact current ticket cells that authorize implementing the
seam without importing another domain's ownership or inventing new semantics.

`DEFERRED_COMPOSITION` is legal only for a capability ticket whose exact current planning
authority explicitly separates **capability implementation/certification** from a later
cross-domain composition Spec. It requires all of the following:

1. the current ticket owns only its domain/provider implementation or a role-narrow consumer
   against an already fixed inward port;
2. the exact current Spec/ticket does **not** claim production composition, end-to-end
   availability, or integrated proof for the deferred seam;
3. durable planning authority names the later composition owner and that owner is downstream
   by design rather than accidentally missing upstream;
4. the current ticket can be completed and certified without synthesizing another domain's
   facts, absences, semantics, or authority; and
5. every domain-owned provider that the current ticket itself promises to expose remains
   `PRESENT_UPSTREAM` or `OWNED_BY_CURRENT_TICKET` as applicable.

A test fake may exercise the inward port for component certification under
`DEFERRED_COMPOSITION`, but the fake is **not** evidence that the later production composition
exists. Record the exact durable composition owner separately.

`MISSING_UPSTREAM` means durable authority requires the production provider to exist for this
current ticket's own completion/proof, assigns the seam outside the current ticket, and the
provider is not available at the current native execution position.

`AMBIGUOUS_OWNER` means current durable authority does not establish who may provide the seam
or whether the seam is local capability work versus deferred composition.

## 3. Prove dependency and composition closure

For every provider whose durable owner is another ticket or Spec, inspect **native GitHub
dependencies**, not prose order and not recovery metadata.

A current ticket is feasible when each externally owned seam required for **this ticket's own
production completion** is already available from an upstream/completed route, or when the
seam qualifies exactly as `DEFERRED_COMPOSITION` under Section 2.

A downstream provider does not become locally available merely because a later integration
Spec will exercise it. Conversely, a deliberately downstream composition root is not an
upstream-provider defect when current accepted planning explicitly leaves production assembly
to that later composition Spec and the current capability ticket does not claim integrated
closure.

In particular, a complete typed query/composition contract that requires authoritative
selected-or-absent results from a closed owner set cannot be silently treated as a local
capability dependency. The planning projection must say whether the current ticket owns that
complete production composition or only contributes/consumes an inward port whose production
assembly is deferred. If the ticket claims complete composition, every required owner must be
available now; if composition is deferred, the ticket must not claim complete production
proof.

## 4. Classify fail-fast defects

After the matrix is complete:

- exact current same-Spec cells exist but are assigned to the wrong current route ->
  `cell-routing-defect` -> `$to-tickets`;
- a material cell mixes current-ticket-owned semantics with sibling-consumed semantics such
  that ownership cannot be represented without changing the Spec projection ->
  `planning-cell-gap` -> `$to-specs`;
- no new material semantics are required, but the current Spec/ticket claims production
  completion that depends on work absent from an upstream route, owned by a downstream Spec,
  or omitted from executable planning -> `planning-cell-gap` -> `$to-specs`;
- correct implementation requires a new or changed material semantic choice not fixed by
  current authority -> `contract-authority-gap` -> the governing semantic decision path;
- concrete environment/tool/permission failure prevents the read-only proof -> Hard Blocker.

Do not implement another domain's missing provider merely to make this ticket pass. Do not
weaken a complete-provider contract to fit the current delivery order. Do not treat a
legitimate deferred composition seam as missing merely because its production root is later.
Route the planning or authority defect when the current projection does not make that boundary
explicit.

## 5. Required receipt

Before pre-mutation Attention, emit exactly one feasibility receipt.

Success:

```text
IMPLEMENT TICKET FEASIBILITY: PASS
Required production seams: <n>
Present upstream: <n>
Owned by current ticket: <n>
Deferred composition: <n>
Missing upstream: 0
Ambiguous owner: 0
Prior findings reconsidered: <n>
```

A PASS requires every required seam to be `PRESENT_UPSTREAM`,
`OWNED_BY_CURRENT_TICKET`, or lawfully `DEFERRED_COMPOSITION`, and every materially applicable
prior finding to have a current disposition.

Failure:

```text
IMPLEMENT TICKET FEASIBILITY: BLOCKED
Classification: <cell-routing-defect | planning-cell-gap | contract-authority-gap | hard-blocker>
Provider seam: <exact seam or None>
Required by cells: <exact cells or None>
Durable owner: <exact durable owner or Unknown>
Native dependency relation: <relation or Unknown>
Reason: <concrete durable contradiction>
Route: <owning workflow or None>
```

On `BLOCKED`, perform **no substantive candidate mutation and no broad technical verification,
deduplication, wiki sync, pre-closure Attention, or independent closure dispatch**. Persist
any routing/planning evidence required by the owning workflow and produce the normal verified
Human Handoff when that classification requires one.

## 6. Resume behavior

An explicit `resume $implement-ticket` does not skip this boundary. Reuse only durable/current
proof that remains exact; otherwise rebuild the provider matrix cheaply. A nonterminal journal
or an existing dirty candidate does not authorize further mutation until the current
feasibility boundary passes.
