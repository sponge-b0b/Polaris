---
name: contract-ledger
description: "Own CCL admission, bounded owner decisions, immutable lookup, and append-only persistence."
compatibility: product=codex product=claude-code system=python system=git system=gh network=required
disable-model-invocation: true
---

# Contract Ledger

`$contract-ledger` is the **sole writer** for Canonical Contract Ledger (CCL)
transactions:

```text
contracts/ccl/transactions/
```

Schema and deterministic mechanics:

```text
contracts/ccl/schema/ccl-v1.schema.json
scripts/ccl.py
scripts/ccl_ledger.py
```

The CCL records material semantics. It does not plan projects, write Specs,
decompose tickets, implement code, or perform review.

No existing lifecycle skill is implicitly migrated by this skill's existence.
Until explicit integration, invoke `$contract-ledger` only when the human or an
already-authorized parent workflow requests it.

## Invariants

* accepted transaction files are append-only and immutable;
* semantic change creates a new full-snapshot revision;
* `retire` is terminal in CCL v1;
* typed assertions are semantic authority;
* `display` / `annotations` are non-authoritative and excluded from the
  proposal hash;
* absence of an assertion never authorizes downstream semantic invention;
* one transaction may revise several coupled contracts atomically, but never
  more than one revision of the same contract;
* every assertion is addressed as
  `<contract-id>@<revision>#<assertion-id>`.

Never edit, replace, rename, or delete an accepted transaction to change its
meaning.

## Modes

Resolve exactly one mode.

### `lookup`

Read-only exact/latest contract or assertion lookup:

```bash
python scripts/ccl_ledger.py lookup \
  contracts/ccl/transactions \
  <contract-id> \
  [--revision <n>] \
  [--assertion <assertion-id>]
```

When an exact CCL address exists, consume it rather than reinterpreting source
prose.

### `existing-authority`

Register semantics already fixed completely by current durable authority.

No new semantic choice or human decision is legal here. Every proposed
assertion must be entailed at exactly the proposed strength by current
governing/constraint authority.

Illegal strengthening includes:

* `may` -> `must`;
* examples -> required/closed taxonomy;
* optional -> required relationship/cardinality;
* general durability -> invented required public field;
* open vocabulary -> closed enum;
* unspecified dimension -> chosen default.

If normalization requires any such choice, return `CCL ADMISSION: UNSUPPORTED`.

### `owner-decision`

Resolve one bounded independent semantic coupling group through explicit human
acceptance.

Legal only when all are true:

```text
Unresolved semantic coupling groups: 1
Dependent material choices after this decision: 0
Cross-domain planning required: no
Research/prototype campaign required: no
Project partition/dependency planning required: no
One acceptance transaction can completely close the choice: yes
```

Otherwise return:

```text
CCL DECISION REQUIRES WAYFINDER
```

A durable source artifact must exist to host the decision/acceptance receipt.
Do not use conversational acceptance as the only durable authority.

### `wayfinder-decision`

Support, but never replace, a Wayfinder decision.

Before the Wayfinder yes/no gate, prepare the exact typed semantic revisions,
proposal hash, and generated human-readable rendering.

After Wayfinder durably records acceptance of that exact hash, validate and
persist the final transaction. `$contract-ledger` never chooses the Wayfinder
answer.

## Authority Admission

For every proposed assertion establish:

```text
Contract/assertion: <coordinate>
Typed candidate: <kind + subject + exact constraint>
Applicable source: <exact durable source>
Source role: governing | constraint | rationale | evidence
Normalized claim: <typed claim | unsupported>
Entailment: exact | unsupported
```

Only `governing` and `constraint` sources establish material semantics.
Rationale/evidence may explain them but cannot strengthen them.

For `existing-authority`, any `unsupported` assertion blocks admission.

When applicable governing/constraint sources normalize differently for the same
coordinate, use the deterministic authority check and return:

```text
CCL SOURCE CONFLICT
Contract/assertion: <coordinate>
Sources: <exact conflicting sources>
Normalized claims: <typed difference>
Routing owner: <governing semantic owner>
```

Do not choose a winner.

A later owner/Wayfinder decision may deliberately resolve such a conflict. The
accepted new decision then becomes governing authority for the new CCL
revision; conflicting older sources remain history, not equivalent current
authority.

## Proposal and Human Gate

CCL revisions are complete snapshots, not semantic patches.

The semantic proposal is the exact `revisions` payload and its deterministic
hash. Human-facing prose is a generated view of those typed semantics.

For `owner-decision` and `wayfinder-decision`, the human accepts the **exact
proposal hash**.

For `owner-decision`:

1. persist a compact proposal on the durable source artifact;
2. include the proposal hash and generated rendering;
3. state recommendation and material alternatives;
4. ask whether the owner approves that exact semantic proposal;
5. `no` means revise, rehash, persist the new proposal, and ask again;
6. `yes` means durably record acceptance before CCL persistence.

Approval of nearby prose is never approval of a different proposal hash.

`existing-authority` has no new human gate because it is registration, not a
new decision.

## Ledger Admission

Before writing:

```bash
python scripts/ccl_ledger.py validate-ledger contracts/ccl/transactions

python scripts/ccl_ledger.py admit \
  contracts/ccl/transactions \
  <candidate.json>
```

Admission deterministically requires:

* individually valid transactions and hash-derived filenames;
* unique proposal hashes;
* at most one revision per contract in one transaction;
* revision 1 is `create`;
* contiguous revisions thereafter;
* exact immediate `supersedes_revision`;
* no revision after `retire`.

`ALREADY-PRESENT` is idempotent success. Never rewrite its metadata.

Malformed accepted history is `CCL LEDGER CORRUPTION`; stop rather than
normalizing it.

## Persistence

CCL authority is canonical on `main`.

### Direct

When this skill owns persistence:

1. preserve the caller checkout;
2. fetch/freeze `origin/main`;
3. use a clean isolated worktree at that exact base;
4. validate the candidate and current ledger;
5. create the transaction only with:

   ```bash
   python scripts/ccl_ledger.py persist \
     contracts/ccl/transactions \
     <candidate.json>
   ```

6. stage only the returned transaction path;
7. commit through repository conventional-commit policy;
8. fetch and require `origin/main` still equals the frozen base;
9. push normally, never force;
10. fetch/read back `main` and rerun `validate-ledger`;
11. prove the caller checkout remained unchanged.

If `main` moved, discard only the isolated candidate state and rebuild
admission from the new canonical base.

### Parent-owned atomic contribution

A future parent workflow may explicitly request contribution when it already
owns a clean isolated canonical-main worktree and needs one atomic authority
commit.

Then `$contract-ledger` performs semantic/ledger admission and creates only the
CCL transaction file. It returns the exact path/hash/revisions and does not
commit or push. The parent owns its existing commit/concurrency/readback
transaction.

The parent may commit the file, but it may not construct or alter CCL
transaction semantics itself.

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

Unsupported semantic registration:

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

Do not turn a persistence/integrity failure into a product decision.

## Non-Goals

Do not:

* create Specs/tickets or implementation work;
* maintain consumer mappings;
* use implementation precedent as missing semantic authority;
* automatically migrate historical architecture;
* make Wayfinder mandatory for decision-complete Independent work;
* reopen accepted semantics because another wording is imaginable.

Keep the CCL boring: one typed semantic truth, immutable revisions, one writer.
