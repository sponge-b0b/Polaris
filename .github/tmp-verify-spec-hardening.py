from pathlib import Path


def insert_before(path: str, anchor: str, block: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    heading = block.splitlines()[0]
    if heading in text:
        raise SystemExit(f"hardening block already present in {path}: {heading}")
    if text.count(anchor) != 1:
        raise SystemExit(f"anchor must occur exactly once in {path}: {anchor!r}")
    file_path.write_text(text.replace(anchor, block.rstrip() + "\n\n" + anchor, 1), encoding="utf-8")


def insert_after(path: str, anchor: str, block: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    heading = block.splitlines()[0]
    if heading in text:
        raise SystemExit(f"hardening block already present in {path}: {heading}")
    if text.count(anchor) != 1:
        raise SystemExit(f"anchor must occur exactly once in {path}: {anchor!r}")
    file_path.write_text(text.replace(anchor, anchor + block.rstrip() + "\n\n", 1), encoding="utf-8")


spec_contract_isolation = r'''### Build-Mode Isolation Gate

This section is authoritative for `build` mode. It supersedes any later preserved wording that permits an independent build attempt to reuse or overwrite a prior handoff path.

A `build` result is admissible only when contract construction occurs in a **genuinely fresh agent/process context** that has not seen any prior representation of the same Spec contract. The caller supplies only:

* originating Spec issue/URL;
* fixed `BASELINE_COMMIT`;
* current Spec branch;
* current `HEAD`;
* `mode=build`;
* a newly allocated invocation-owned `handoff-output` path that **does not exist before dispatch**.

For a fresh build, create an invocation-owned directory and pass a nonexistent child path, for example:

```bash
CONTRACT_BUILD_DIR=$(mktemp -d)
CONTRACT_HANDOFF="$CONTRACT_BUILD_DIR/contract.json"
test ! -e "$CONTRACT_HANDOFF"
```

Before returning terminal `SPEC CONTRACT: VALID`, the builder must **not** receive, search for, enumerate, read, compare against, or reconstruct from any of the following:

* a prior or expected `SPEC_CONTRACT_HASH`;
* a prior Source Unit Inventory, manifest, structural identity row set, or source-to-cell mapping;
* a prior `CONTRACT_HANDOFF` or `CONTRACT_HANDOFF_DIGEST`;
* a prior verification receipt, review proof, proof-reuse ledger, or rendered contract table used as construction input;
* pre-existing `/tmp`, workspace, cache, artifact, transcript, or other scratch files containing prior contract state;
* conversational or agent-session memory of prior contract counts, source-unit boundaries, mappings, or hashes.

Durable repository/tracker state needed to resolve the originating Spec, fixed baseline, branch, current `HEAD`, default branch, and change provenance remains valid input. A historical representation of the contract itself is not.

The caller may retain a historical hash or receipt **outside the fresh builder context**, but it must not reveal or compare that state until after the fresh builder has returned its complete terminal result. Reproducibility is tested by post-build comparison; an expected value is never a construction target.

If the builder becomes contaminated before completing construction—for example by inspecting a prior handoff, prior manifest, expected hash, or scratch contract artifact—the attempt is invalid. Return:

```text
SPEC CONTRACT: INVALID
Reason: build isolation contaminated by prior contract state
```

Discard that attempt's handoff. Do not continue in the same context by promising to ignore what was seen. A new build requires a new fresh context and a new nonexistent handoff path.

Every valid build terminal result must include:

```text
Build isolation: PASS
Prior contract representations supplied or inspected: 0
Pre-existing scratch contract artifacts inspected: 0
Handoff path existed before build: no
```

Missing or contradictory isolation evidence makes the build invalid even if its resulting hash matches a historical value.'''

verify_contract_isolation = r'''### Fresh Contract Builder Isolation

This section is authoritative for every `$spec-contract` **build** consumed by `$verify-spec` and supersedes later wording that implies the parent may itself reconstruct the deterministic Spec contract.

The `$verify-spec` parent owns **dispatch and admission** of contract construction; a genuinely fresh `$spec-contract` builder owns the construction itself.

For every build used for semantic certification or finalization:

1. Resolve only the originating Spec identity, fixed baseline, Spec branch, and exact current `HEAD` needed to dispatch the builder. Do **not** inspect prior scratch contract files or reconstruct a prior contract in the parent first.
2. Allocate a new invocation-owned temporary directory and a handoff path that does not yet exist.
3. Spawn exactly one genuinely fresh, non-mutating builder context and require it to execute `$spec-contract` in `build` mode.
4. Pass only the inputs allowed by `$spec-contract` **Build-Mode Isolation Gate**. Do not pass an expected/prior contract hash, prior manifest/source-unit inventory, prior handoff/digest, prior receipt contract table, proof-reuse material, or scratch artifact.
5. Require terminal `SPEC CONTRACT: VALID`, the exact `CONTRACT_HANDOFF_DIGEST`, and the complete Build-Mode Isolation attestation before consuming the handoff.
6. **Only after the fresh builder returns** may the parent recover or compare a historical/persisted `SPEC_CONTRACT_HASH` for reproducibility/staleness checks. A match proves reproduction; it must never guide construction.
7. The parent must not replace a failed or inconvenient child build with ad hoc Python, manual manifest reconstruction, reverse-parsing of a receipt, or inspection of old `/tmp` contract artifacts.
8. If repair changes `HEAD`, or if the certified handoff is lost, dispatch a new fresh builder with a new nonexistent handoff path and follow the existing recertification rules.

A parent that already knows a historical hash from durable lifecycle state does not contaminate the build **provided that value is not passed into or exposed to the fresh builder before its terminal result**.

If a fresh builder primitive is unavailable, the contract build is unresolved and verification fails closed. The same-instance substitute-agent allowance for independent review does not authorize reconstructing a supposedly fresh contract after that same context has already seen prior contract state.

Before any semantic-certifier dispatch require:

```text
Fresh contract builder dispatched: 1
Fresh builder terminal result: SPEC CONTRACT: VALID
Build isolation: PASS
Prior contract representations supplied or inspected by builder: 0
Pre-existing scratch contract artifacts inspected by builder: 0
Handoff path existed before build: no
Historical hash comparison performed before builder terminal result: no
Parent-side substitute contract construction: 0
```'''

delegated_execution = r'''#### Child-Owned Execution Requirement

A required delegated gate is **not invoked** merely because the parent reads the child `SKILL.md` and runs commands that resemble its procedure. The owning skill must execute as an actual child/nested skill operation and must return its own current terminal result.

Use either a distinct child context or a native nested-skill mechanism that preserves the complete owner-skill contract. Execute mutation-capable delegated gates sequentially when they share the same worktree. The parent may prepare inputs and consume returned evidence, but it may not substitute its own abbreviated implementation of the child gate.

A direct parent command may provide supporting evidence, but it cannot satisfy the delegated gate unless the owner skill itself explicitly defines that command output as its terminal result and the owner skill invocation returns that result.

Before finalization require:

```text
Required delegated gates: <n>
Owner-skill invocations completed: <n>
Valid owner terminal results captured: <n>
Parent-substituted delegated gates: 0
Required delegated gates without owner terminal result: 0
```

If a required child skill was only read, paraphrased, or manually emulated by the parent, classify that delegated gate `unresolved` and block PASS.'''

insert_before(
    ".agents/skills/spec-contract/SKILL.md",
    "## Reproducible Contract Identity",
    spec_contract_isolation,
)
insert_before(
    ".agents/skills/verify-spec/SKILL.md",
    "## Authorized Verification Scope and Repair Attribution",
    verify_contract_isolation,
)
insert_after(
    ".agents/skills/verify-spec/SKILL.md",
    "### Delegated Gate Ownership\n\n",
    delegated_execution,
)
