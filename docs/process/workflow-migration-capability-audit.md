# Workflow Migration Capability Audit

## Scope

This audit compares the last pre-CCL-cutover workflow state
`1aef553b36f2907dbe7d811de4d6d5456b243952` with the pre-repair current state
`c3ddbfdda26fc8d825ba5a6fdab58e754e212a93`.

The audit is semantic rather than line-count based. A removed file/section is safe only when
its capability is still present, has a current equivalent owner, or was explicitly retired
with a durable replacement. Omission is not retirement evidence.

Status vocabulary:

- `PRESERVED` — the same lifecycle guarantee has a current owner.
- `REPLACED-EQUIVALENT` — the old mechanism was replaced, but the lifecycle guarantee is
  still owned and enforced.
- `INTENTIONALLY RETIRED` — the old capability/mechanism was explicitly retired and its
  surviving responsibility is named.
- `LOST / DEFECT` — the migration removed a required capability without a current owner.
- `AMBIGUOUS` — evidence was insufficient to classify safely.

The machine-readable companion is `.agents/skills/workflow-capabilities.json`.

## Result

The audit found three unresolved migration losses, all in the cross-skill Human Handoff
family:

1. lifecycle-boundary classification (internal composition / ordinary return / in-skill
   HITL / Human Handoff);
2. canonical artifact handoff command format;
3. fresh-session durability before a Human Handoff.

This recovery restores those three as one shared cross-skill invariant and adds
`scripts/workflow_handoff.py` as the deterministic generator/validator. The existing
Wayfinder Route Clarity gate delegates its artifact invocation line to that shared
renderer.

No core lifecycle capability remains `AMBIGUOUS`. All other audited pre-cutover capabilities
are preserved, replaced equivalently, or have explicit retirement evidence.

## Capability ledger

| Capability | Classification | Current owner / replacement evidence |
| --- | --- | --- |
| Cross-skill authority layering | PRESERVED | `AGENTS.md`; `.agents/skills/README.md` |
| Human Handoff boundary classification | LOST / DEFECT → restored | Shared README rule + `scripts/workflow_handoff.py` |
| Canonical artifact Human Handoff format | LOST / DEFECT → restored | Shared README rule + deterministic shared gate |
| Fresh-session Handoff durability | LOST / DEFECT → restored | Shared README rule + required durability receipt in shared gate manifest |
| Workflow architecture requires owner authorization | PRESERVED | `AGENTS.md` mandate/structural-mutation guard; current README change control |
| Proactive Attention checkpoint roster | PRESERVED | `AGENTS.md`; `$attention` |
| `$implement-ticket` Attention fail-closed behavior | PRESERVED / hardened after cutover | `c82e272d112f37480330667323fc9415c57ca58e` |
| Intake promotion remains human-owned | REPLACED-EQUIVALENT | Current lifecycle permits Wayfinder or bounded Independent CCL path; no automatic promotion |
| Lifecycle re-entry/backward routing | PRESERVED | `$architecture-remediation`; `$to-specs`; review remediation routes |
| Project focus distinct from dependency | PRESERVED / strengthened | `$project-delivery-management`; executable `scripts.project_delivery` guard |
| Open Spec reconciliation in place | REPLACED-EQUIVALENT | Permanent `$to-specs` reconciliation rule; `14d4dbd4...` |
| Current ticket reconciliation | REPLACED-EQUIVALENT | Current `$to-tickets` deterministic coverage/topology reconciliation |
| Live-WIP ticket reslicing | PRESERVED | `$to-tickets` Section 9; `ticket-reslice-recovery:v1` |
| Exactly one conventional Spec Review owner | PRESERVED | `$review-spec`; `$spec-merge-cleanup` |
| Review finding continuity | REPLACED-EQUIVALENT | `review-spec-finding-ledger:v2` / `polaris.review-findings/v2` |
| Decomposition-defect durable routing | REPLACED-EQUIVALENT | `decomposition-defects:v1`; `$to-tickets` / `$to-specs` routing |
| Durable architecture-blocker report | PRESERVED | `$architecture-remediation`; `architecture-blocker:v1` |
| Closed Wayfinder authoritative re-entry | PRESERVED | `$architecture-remediation` reopens exact governing map when required |
| Separate Root Blocker closure verifier | INTENTIONALLY RETIRED | `f699a1c6...`: current review remediation uses `review-remediation-contract/v1` + `$verify-ticket-closure` |
| `$review-spec-remediation` helper | INTENTIONALLY RETIRED | v2 finding ledger is consumed directly by current `$to-tickets` |
| `$to-remediation-specs` helper | INTENTIONALLY RETIRED | Permanent in-place `$to-specs` reconciliation; `14d4dbd4...` |
| `$to-remediation-tickets` helper | INTENTIONALLY RETIRED | Current `$to-tickets` owns ordinary/review reconciliation directly |
| Idempotent/fail-closed Spec completion recovery | PRESERVED | `$spec-merge-cleanup` pre/post-completion phase detection and cleanup recovery |
| Project board is projection, not lifecycle authority | PRESERVED | `AGENTS.md`; current README; `$project-tracking` |
| Native dependency relationships are execution truth | PRESERVED | `AGENTS.md`; `$to-specs`; `$project-delivery-management` |
| Independent Specs do not acquire synthetic Wayfinders | PRESERVED | `AGENTS.md`; `$architecture-remediation` |
| Ticket closure uses independent proof | PRESERVED | `$implement-ticket` / `$verify-ticket-closure` v3 boundary |
| Integrated Spec closure uses independent proof | PRESERVED | `$verify-spec` / `$verify-spec-closure` |
| Review remains independent/adversarial | PRESERVED | `$review-spec` fresh non-mutating reviewer contract |
| Issue open/closed state is not sufficient lifecycle authority | PRESERVED | `$spec-merge-cleanup` exact recovery classification; Project remains downstream |
| Provenance does not substitute for hierarchy/dependency truth | PRESERVED | `AGENTS.md`; `$to-specs`; Project Delivery rules |
| Branch/baseline/readiness gates | PRESERVED / restored after cutover | `9802faf6...`; current `$to-tickets`, `$to-specs`, `$implement-ticket` |
| Wayfinder Route Clarity terminal enforcement | PRESERVED / hardened after cutover | `c3ddbfdd...`; now delegates artifact line rendering to shared gate |

## Retirement evidence

The audit treats a removed helper as intentional only when the migration history states the
replacement explicitly. Examples:

- `14d4dbd4bdd2ff92c34c5e781b809ec460ca17d0` makes Spec reconciliation permanent in
  `$to-specs` rather than a migration/remediation helper.
- `f699a1c6f96a6bf5883d59366f68da84893cdd1d` removes `$verify-root-closure` only after the
  compatibility skill itself states that current review remediation is certified through
  `review-remediation-contract/v1` and `$verify-ticket-closure`.
- The v2 review-remediation cutover replaces semantic Root Blocker synthesis with stable
  `RF-*` findings and deterministic remediation contracts.

## Regression rule

Future workflow migrations must update `.agents/skills/workflow-capabilities.json` and keep
all capability-level tests green. A migration may not make a capability disappear merely by
removing its prose/file. It must classify the capability as preserved, replaced-equivalent,
or intentionally retired with an explicit current owner/replacement.

For artifact Human Handoffs, the shared gate is now the canonical enforcement boundary.
Workflow-specific gates may add stricter checks but must not duplicate or redefine the
artifact invocation grammar.
