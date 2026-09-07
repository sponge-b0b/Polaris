# R2 Investment Decision Lifecycle Correction Support Contract

**Status:** Owner-approved; design complete  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Purpose:** Close the lifecycle-correction reconciliation gap discovered at Ticket #296 implementation entry without broadening R2 scope.

## Authority and synchronization

This contract completes the lifecycle-correction semantics required by:

- `docs/proposed/investment-decisions-lifecycle-model.md`;
- `docs/proposed/application-use-cases-investment-decision-lifecycle.md`;
- `docs/proposed/durable-persistence-investment-decision-history.md`;
- `docs/proposed/investment-decisions-r2-foundation-public-contract.md`;
- `docs/product/requirements-0.2.0-amendment-r2-edge-cases.md`;
- Spec #278 and Ticket #296.

Where the three older proposed lifecycle/application/persistence documents leave lifecycle-correction support or reconciliation underspecified, this contract controls. It does not change their product scope or ownership boundaries.

The R2 foundation public contract is already complete. Any surviving statements in those older proposals saying Decision Subject, canonical `PortfolioId`, Scope equality/order, Actor/provenance typing, public construction/reconstruction, or other #299 foundation items remain unresolved are historical text superseded by `docs/proposed/investment-decisions-r2-foundation-public-contract.md` and the post-#299 synchronization authority on Spec #278. They are not implementation blockers.

---

## 1. Correction fact contract

`DecisionLifecycleCorrected` is an immutable lifecycle fact. It reuses the canonical lifecycle fact identity, metadata, sequence, version, time, Actor Attribution, Trigger Provenance, Technical Provenance, and `OperationId` contracts; it does not introduce a parallel correction-history model.

Every correction has:

- its own fresh `DecisionLifecycleFactId`;
- the immediately next `DecisionLifecycleSequence` for the Decision;
- complete `DecisionLifecycleFactMetadata`;
- exactly one `target_fact_id` naming an earlier lifecycle fact for the same Decision;
- one correction effect: `QUALIFY` or `DISCONFIRM`;
- one purpose-specific typed correction basis that establishes why the correction is semantically supported.

A correction may target either an ordinary lifecycle fact or an earlier `DecisionLifecycleCorrected` fact.

The target must:

- exist in the same reconstructed Decision history;
- have the same `InvestmentDecisionId`;
- have a strictly lower `DecisionLifecycleSequence` than the correction;
- be a lifecycle fact, not a relationship fact or technical execution record.

These rules make the correction target graph acyclic by construction. No generic graph service or separate correction-cycle mechanism is required.

Original facts remain immutable and inspectable. A correction never rewrites the target fact's identity, metadata, Actor Attribution, provenance, basis, effective time, or recorded time.

### `QUALIFY`

`QUALIFY` says that the target branch remains historically present but its prior interpretive claim is replaced by a complete corrected lifecycle claim.

A qualifying correction therefore requires:

- one supported `DecisionLifecycleDisposition`;
- the correction fact's own `effective_at` as the effective time of that corrected interpretation;
- the correction's purpose-specific typed basis as the support for the corrected interpretation.

Using the same disposition with a different effective time or corrected semantic basis is still a qualification. Using a different disposition establishes the corrected supported disposition without deleting the original source fact.

### `DISCONFIRM`

`DISCONFIRM` says that the target branch's interpretive claim is no longer supported from the correction's effective time.

A disconfirming correction:

- does not supply a replacement lifecycle disposition;
- still requires its own truthful Actor Attribution/provenance and purpose-specific typed correction basis;
- preserves the target fact or correction as historical truth.

---

## 2. Correction-chain semantics

Correction targeting creates one or more support branches rooted in ordinary lifecycle facts.

At a given knowledge/effective query boundary, the active leaves of those branches determine the supported interpretation of each root lifecycle fact.

For one branch:

1. no applicable correction after the root -> the root contributes its native interpretive claim;
2. leaf `QUALIFY` -> the branch contributes that correction's complete replacement claim;
3. leaf `DISCONFIRM` targeting the root -> the branch contributes explicit disconfirmation and no positive replacement claim;
4. leaf `DISCONFIRM` targeting an earlier correction -> the targeted correction's effect is defeated and the branch restores the interpretation that existed immediately before that targeted correction.

That fourth rule is deliberate. A correction can itself be wrong. Append-only correction of the correction must be able to restore the previously supported interpretation without mutating or deleting either correction fact.

Example:

```text
F1  native claim: UNRESOLVED
C1  QUALIFY F1 -> EXTERNALLY_RESOLVED
C2  DISCONFIRM C1

supported branch after C2 -> F1's UNRESOLVED claim is restored
```

Restoration is not newest-write authority. It follows the explicit target relationship and correction effect. If another surviving correction branch still qualifies or disconfirms `F1`, that branch remains independently material.

A later `QUALIFY` targeting an earlier correction replaces that correction branch with the later complete replacement claim. This permits correcting disposition, effective time, or semantic basis without mutating the earlier correction.

---

## 3. Reconciliation of competing branches

Recorded recency and larger lifecycle sequence never make one correction semantically authoritative merely because it was recorded later.

For one root lifecycle fact, evaluate every surviving correction branch that is available at the query boundary.

Branch outcomes reconcile as follows:

- materially equivalent positive claims coalesce into one supported claim while preserving all supporting correction/fact references;
- all surviving branches explicitly disconfirming the root produce a determinate disconfirmed root with no positive claim;
- a positive claim competing with an explicit disconfirmation is irreconcilable;
- materially different positive claims are irreconcilable.

Positive claims are materially equivalent only when they establish the same lifecycle disposition and the same effective time. Different typed support references may jointly support the same claim and do not create conflict by themselves; all such support remains inspectable.

Different disposition or different effective time is materially different because it changes lifecycle history, even if two claims happen to yield the same present-day disposition after both effective times have passed.

Any irreconcilable root interpretation makes lifecycle interpretation **contested/indeterminate** for the affected query. A valid contested state is not an invalid history and must not be converted into last-writer-wins certainty.

If every root interpretation is determinate, replay the surviving interpreted lifecycle claims under the existing lifecycle semantics. If independently supported roots still imply incompatible lifecycle interpretations at the query boundary and no explicit correction relationship resolves them, the overall lifecycle interpretation is contested/indeterminate.

---

## 4. Temporal evaluation order

Historical interpretation keeps knowledge time and effective time separate.

For `effective_at(T, known_at=K)`:

1. select only lifecycle facts/corrections with `recorded_at <= K`;
2. preserve their target graph and raw history;
3. at `T`, apply only correction effects whose correction `effective_at <= T`;
4. resolve correction branches and reconciliation under Sections 2-3;
5. interpret the surviving lifecycle claims at `T`.

Do not discard a known target fact merely because its original effective time is after `T` before correction resolution. A later-recorded correction may establish that the supported interpretation was actually effective earlier.

`as_known_at(K)` remains exactly:

```text
as_known_at(K) = effective_at(T=K, known_at=K)
```

Consequences:

- a later-recorded earlier-effective correction changes historical interpretation only for knowledge cutoffs at or after its `recorded_at`;
- a known future-effective correction does not affect state before its `effective_at`;
- a correction-of-correction changes only query boundaries at which that later correction is both known and effective;
- earlier `as_known_at` results remain stable.

---

## 5. Sequence and Decision-version behavior

Every committed correction appends a lifecycle fact and therefore always receives the immediately next `DecisionLifecycleSequence`.

`DecisionLifecycleSequence` and `DecisionVersion` remain separate concepts.

A committed correction increments `DecisionVersion` exactly once **only when the correction changes the Decision's current concurrency-protected derived state at commit/recorded time**. Examples include changing the current determinate disposition or changing current interpretation from determinate to contested or vice versa.

A valid correction that changes only an earlier historical interval or only a future-effective interval may append the next lifecycle sequence without changing `DecisionVersion` because current concurrency-protected state did not change.

No correction may increment `DecisionVersion` more than once. A semantic retry/no-op does not manufacture another correction fact merely to advance either counter.

---

## 6. Invalid correction vs valid contested interpretation

Reject correction creation/reconstruction as invalid when, among other ordinary metadata/history failures:

- `target_fact_id` is missing or unknown;
- target belongs to another Decision;
- target is not a lifecycle fact;
- target sequence is not strictly earlier;
- correction fact identity is duplicated;
- `QUALIFY` lacks a supported disposition;
- `DISCONFIRM` supplies a replacement disposition;
- correction basis is missing, empty, wrong-purpose, or otherwise invalid;
- ordinary live correction creation lacks known Actor Attribution;
- required time/provenance metadata is invalid.

Historical reconstruction may preserve truthful unknown or contested Actor Attribution under the completed foundation contract.

By contrast, a well-formed history with irreconcilable surviving support is valid history with contested/indeterminate lifecycle interpretation. Querying that state is not itself exceptional. An operation that requires one deterministic lifecycle disposition fails through the existing typed contested-interpretation semantic failure.

---

## 7. Application and persistence consequences

Application/use-case behavior must expose correction support rather than hide it behind a current status field.

History/query surfaces preserve at least:

- raw original lifecycle facts;
- correction fact identity;
- `target_fact_id`;
- correction effect;
- qualifying replacement disposition when present;
- correction basis;
- effective/recorded time;
- Actor Attribution and provenance;
- the support references explaining determinate or contested interpretation.

Durable persistence must store enough to reconstruct this target graph and must never implement correction semantics as `ORDER BY recorded_at DESC LIMIT 1`, maximum sequence wins, mutable overwrite, or a latest-status row as sole authority.

A current projection/cache may be maintained, but it is derived state and must be reproducible from immutable lifecycle facts/corrections under this contract.

No generic support graph, event-sourcing framework, or platform-wide correction abstraction is introduced by R2.

---

## 8. Required R2 correction fixtures

R2 domain verification must cover at least:

1. unsupported-Need correction after prior lifecycle/human history preserves every original fact;
2. qualifying correction changes current supported disposition;
3. qualifying correction preserves disposition while correcting effective time or semantic basis;
4. disconfirming an ordinary source fact removes that source branch's positive support;
5. disconfirming a qualifying correction restores the interpretation immediately preceding that correction;
6. qualifying a prior correction replaces that branch with the new complete claim;
7. equivalent sibling qualifying corrections coalesce without false contest;
8. conflicting sibling qualifying corrections produce contested/indeterminate interpretation;
9. positive qualification competing with explicit disconfirmation produces contested/indeterminate interpretation;
10. later-recorded earlier-effective correction affects only `known_at` boundaries at/after recording;
11. known future-effective correction does not apply early;
12. `as_known_at(K) = effective_at(K, known_at=K)`;
13. historical-only/future-only correction advances lifecycle sequence without incorrectly advancing current `DecisionVersion`;
14. current-state-changing correction advances `DecisionVersion` exactly once;
15. invalid/cross-Decision/forward correction targets are rejected;
16. original and correction Actor Attribution/provenance remain separately inspectable.

This closes the correction-support design gap that blocked Ticket #296. No unresolved lifecycle-correction design choice is delegated to implementation.