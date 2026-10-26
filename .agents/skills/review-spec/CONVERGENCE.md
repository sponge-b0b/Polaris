# Review Convergence

This file is authoritative procedure for `$review-spec` completeness convergence. It exists to prevent serial blocker discovery across repeated fix/re-review loops.

## Procedure precedence

The initial Reviewer A + Reviewer B pair required by `SKILL.md` remains mandatory. For convergence recovery only, this procedure is the explicit narrow exception to `SKILL.md`'s "exactly two fresh reviewers" count: when the final challenger changes the material review universe, dispatch one additional fresh non-mutating challenger at a time until the fixed-point gate passes. Do not skip the initial A/B pair, and do not add extra challengers once convergence is valid.

## Trigger

Every `$review-spec` run must prove review convergence before any terminal PASS or remediation handoff.

A **review completeness regression** exists when a re-review discovers a Blocking finding on a materially relevant implementation/proof/temporal/composition surface that already existed at the previously terminally reviewed candidate. A completeness regression does not erase the finding. It changes the review obligation: remain in `$review-spec`, saturate the implicated family, and reach a fixed point before routing remediation.

## Cross-cutting family saturation

When any reviewer discovers a Blocking finding whose mechanism is cross-cutting (for example clock authority, transaction boundary, owner-version validation, stale-basis handling, lifecycle admission, read/write symmetry, or composition), the reviewer must identify the smallest complete sibling family implicated by that mechanism and inspect every materially distinct member before the finding can leave review.

Do not stop at the first falsifier. Do not route one blocker while obvious same-mechanism siblings remain unchecked.

Examples of bounded sibling-family dimensions include:

- read versus write;
- initial act versus correction;
- process clock versus database clock;
- `recorded_at`, `known_at`, and `effective_at` ownership;
- ahead/equal/behind clock directions;
- commit-time versus query-time interpretation;
- each concrete command/owner path governed by the same frozen cell.

Saturation cannot create a new contract cell or semantic requirement. Every discovered defect must still bind to the frozen Spec contract.

## Complete challenger rounds

Reviewer A produces one complete `polaris.review-coverage/v1` artifact.

Reviewer B performs the existing full-contract coverage/finding challenge and produces a new complete coverage artifact after every correction or expansion it makes.

After Reviewer B, build convergence from the complete round artifacts:

```bash
python .agents/skills/review-spec/scripts/review_convergence.py build \
  <spec-contract.json> \
  <review-convergence.json> \
  <round-1-coverage.json> \
  <round-2-coverage.json> [<round-N-coverage.json> ...]
```

If the command fails because the final challenger changed the material review universe, dispatch a **fresh non-mutating challenger** over the exact same candidate and frozen contract. Give that challenger the current reconciled coverage and finding state plus any cross-cutting saturation family already identified. It must complete the full contract, not only the changed family.

Append its complete coverage artifact and rerun the command. Repeat until it returns exactly:

```text
REVIEW CONVERGENCE: VALID
```

The fixed point is reached only when the final two complete challenger rounds have identical normalized:

- material review surfaces;
- adversarial probes/falsifiers/evidence;
- finding-to-cell links.

A new or removed surface, probe, or finding link means the review universe changed and another fresh complete challenger round is mandatory.

## Durable convergence artifact

Persist exactly one active convergence comment on the conventional Spec Review issue:

```markdown
<!-- review-spec-convergence:v1
<exact polaris.review-convergence/v1 JSON>
-->
## Review Convergence Receipt

<exact machine receipt>
```

Read it back exactly and rerun:

```bash
python .agents/skills/review-spec/scripts/review_convergence.py validate \
  <read-back-review-convergence.json>
```

Require the same `Review Convergence SHA-256` before PASS or FAIL handoff.

The final convergence round must bind the exact final `Review Coverage SHA-256` used by finding adjudication and terminal handoff.

## Exit and remediation gate

Neither PASS nor remediation handoff is allowed until convergence is valid.

A newly discovered pre-existing Blocking finding is retained in the finding ledger, but `$to-tickets` remains blocked until the convergence fixed point is reached. Once converged, route the complete open blocker set together through the normal finding/remediation rules.

The Human Handoff durability set must include the convergence comment in addition to finding ledger, coverage, adjudication, and Session Ledger sources.

Finalize only with:

```bash
python .agents/skills/review-spec/scripts/review_spec_handoff.py finalize \
  --manifest <handoff-manifest.json> \
  --coverage <final-review-coverage.json> \
  --convergence <read-back-review-convergence.json> \
  --output <handoff-output.txt>
```

The finalizer fails closed when convergence is absent, stale, non-fixed-point, or bound to a different final coverage artifact.
