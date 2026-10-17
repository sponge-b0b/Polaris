---
name: contract-ledger
description: "Own CCL admission, bounded owner decisions, immutable lookup, and append-only persistence."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Contract Ledger

`$contract-ledger` is the sole writer for Canonical Contract Ledger (CCL) transactions:

```text
contracts/ccl/transactions/
```

Schema and deterministic mechanics:

```text
contracts/ccl/schema/ccl-v1.schema.json
scripts/ccl.py
scripts/ccl_ledger.py
```

The CCL records material semantics. It does not plan projects, write Specs, decompose
tickets, implement code, or perform review.

## Invariants

* accepted transaction files are append-only and immutable;
* semantic change creates a new full-snapshot revision;
* `retire` is terminal in CCL v1;
* typed assertions are semantic authority;
* `display` / `annotations` are non-authoritative and excluded from the proposal hash;
* absence of an assertion never authorizes downstream semantic invention;
* one transaction may revise several coupled contracts atomically, but never more than one
  revision of the same contract;
* every assertion is addressed as `<contract-id>@<revision>#<assertion-id>`.

Never edit, replace, rename, or delete an accepted transaction to change its meaning.

## Modes

### `lookup`

Read-only exact/latest contract or assertion lookup:

```bash
python -m scripts.ccl_ledger lookup \
  contracts/ccl/transactions \
  <contract-id> \
  [--revision <n>] \
  [--assertion <assertion-id>]
```

When an exact CCL address exists, consume it instead of reinterpreting source prose.

### `existing-authority`

Register semantics already fixed completely by current durable governing/constraint
authority.

No new semantic choice or human decision is legal here. Every proposed assertion must be
entailed at exactly the proposed strength.

Illegal strengthening includes:

* `may` → `must`;
* examples → required/closed taxonomy;
* optional → required relationship/cardinality;
* general durability → invented required public field;
* open vocabulary → closed enum;
* unspecified dimension → chosen default.

If normalization requires any such choice, return `CCL ADMISSION: UNSUPPORTED`.

### `owner-decision`

Resolve one bounded independent semantic coupling group through explicit human acceptance.

Legal only when all are true:

```text
Unresolved semantic coupling groups: 1
Dependent material choices after this decision: 0
Cross-domain planning required: no
Research/prototype campaign required: no
Project partition/dependency planning required: no
One acceptance transaction can completely close the choice: yes
```

Otherwise return `CCL DECISION REQUIRES WAYFINDER`.

A durable source artifact must host the proposal and acceptance receipt. Conversational
acceptance alone is not durable authority.

### `wayfinder-decision`

Support, but never replace, a Wayfinder decision. Prepare the exact typed semantic
revisions, proposal hash, and generated human-readable rendering before the human gate.
After the Wayfinder records acceptance of that exact hash, validate/persist the accepted
transaction. `$contract-ledger` never chooses the Wayfinder answer.

## Authority admission

For every proposed assertion establish:

```text
Contract/assertion: <coordinate>
Typed candidate: <kind + subject + exact constraint>
Applicable source: <exact durable source>
Source role: governing | constraint | rationale | evidence
Normalized claim: <typed claim | unsupported>
Entailment: exact | unsupported
```

Only governing/constraint sources establish material semantics. Rationale/evidence may
explain them but cannot strengthen them.

When governing/constraint sources normalize differently at the same coordinate, return:

```text
CCL SOURCE CONFLICT
Contract/assertion: <coordinate>
Sources: <exact conflicting sources>
Normalized claims: <typed difference>
Routing owner: <governing semantic owner>
```

Do not choose a winner.

## Proposal and human gate

CCL revisions are complete snapshots, not semantic patches. The semantic proposal is the
exact `revisions` payload and deterministic hash. Human-facing prose is a generated view.

For `owner-decision` and `wayfinder-decision`, human acceptance binds the exact proposal
hash. Approval of nearby prose is never approval of a different hash.

`existing-authority` has no new human semantic gate because it is registration, not a new
decision.

## Ledger admission

Before writing:

```bash
python -m scripts.ccl_ledger validate-ledger contracts/ccl/transactions
python -m scripts.ccl_ledger admit \
  contracts/ccl/transactions <candidate.json>
```

Admission requires valid hash-derived filenames, unique proposal hashes, one revision per
contract per transaction, revision 1 = `create`, contiguous revisions, exact immediate
`supersedes_revision`, and no revision after `retire`.

`ALREADY-PRESENT` is idempotent success. Malformed accepted history is
`CCL LEDGER CORRUPTION`; stop rather than normalizing it.

## Persistence

CCL authority is canonical on `main`.

When this skill owns persistence, use a clean isolated worktree from frozen current
`origin/main`, validate candidate + ledger, create only the admitted transaction file,
commit under repository policy, recheck canonical-main concurrency, push without force,
read back, rerun ledger validation, and prove the caller checkout unchanged.

When an authorized parent already owns an isolated canonical-main authority transaction,
`$contract-ledger` may contribute the exact admitted transaction file and return its
path/hash/revisions without committing. The parent may commit that file but may not alter
its semantic payload.

## Return

Success:

```text
CCL TRANSACTION: PERSISTED | ALREADY-PRESENT | CONTRIBUTED
Proposal hash: <sha256:...>
Mode: existing-authority | owner-decision | wayfinder-decision
Contracts: <contract@revision list>
Path: <transaction path>
Ledger validation: PASS
```

Unsupported registration:

```text
CCL ADMISSION: UNSUPPORTED
Contract/assertion: <coordinate>
Missing semantic authority: <exact missing choice>
Routing: owner-decision | wayfinder
```

Hard non-semantic failure:

```text
CCL HARD BLOCKER
Reason: <ledger corruption | persistence/concurrency/tool failure>
```

Keep the CCL boring: one typed semantic truth, immutable revisions, one writer.
