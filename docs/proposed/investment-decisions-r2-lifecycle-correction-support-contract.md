# R2 Investment Decision Lifecycle Correction Support Contract

**Status:** Owner-approved; design complete after bounded adversarial closure  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Purpose:** Freeze the complete R2/#296 lifecycle-disposition correction contract without creating a generic correction framework for every Decision fact.

## Authority and supersession

This contract completes and narrows the lifecycle-correction semantics required by:

- `docs/proposed/investment-decisions-lifecycle-model.md`;
- `docs/proposed/application-use-cases-investment-decision-lifecycle.md`;
- `docs/proposed/durable-persistence-investment-decision-history.md`;
- `docs/proposed/investment-decisions-r2-foundation-public-contract.md`;
- `docs/product/requirements-0.2.0-amendment-r2-edge-cases.md`;
- Spec #278 and Ticket #296.

This document supersedes the earlier revision of this same contract that allowed correction to target any lifecycle fact. That broad target rule was internally inconsistent because lifecycle facts contribute different semantic dimensions: lifecycle disposition, work posture, Subject, Scope, and provenance are not one interchangeable status.

For R2 and Ticket #296, **lifecycle correction means correction of supported lifecycle-disposition interpretation only**. A correction never generically rewrites a fact or every semantic contribution carried by that fact.

The R2 foundation public contract is complete. Surviving older proposal text that still calls #299 foundation items unresolved is historical text and not an implementation blocker.

### Scope-correction source conflict resolved

Older proposal text says that an erroneous `ESTABLISHED -> UNRESOLVED` Scope establishment/revision “requires correction” or that historical Subject/Scope correction uses an explicit correction path. For R2, those statements are superseded as follows:

- ordinary `ESTABLISHED -> UNRESOLVED` Scope mutation remains invalid;
- Ticket #296 does **not** correct Decision Scope or Decision Subject;
- erroneous historical Scope/Subject correction is deferred until a future purpose-specific contract actually requires it;
- R2 must not misuse `DecisionLifecycleCorrected` or invent a generic Decision-fact correction abstraction to solve that future problem;
- discovering an erroneous Scope/Subject fact in R2 preserves the immutable history and fails closed for any operation that requires a corrected value until such a purpose-specific contract exists.

This is a deliberate scope boundary, not an implementation omission.

---

## 1. Corrected semantic dimension

The corrected semantic dimension is the Decision's **supported lifecycle disposition**:

```text
UNRESOLVED
SUBSTANTIVELY_RESOLVED
EXTERNALLY_RESOLVED
NEED_RETRACTED_UNSUPPORTED
```

`DecisionLifecycleCorrected` may qualify or disconfirm only a lifecycle-disposition claim contributed by an eligible source fact/correction.

The following ordinary lifecycle facts contribute correctable disposition claims in R2:

- `DecisionInitiated` -> initial `UNRESOLVED` disposition claim only;
- `DecisionSubstantivelyResolved` -> `SUBSTANTIVELY_RESOLVED`;
- `DecisionExternallyResolved` -> `EXTERNALLY_RESOLVED`.

An earlier `DecisionLifecycleCorrected` is also an eligible correction target because correction-of-correction must be append-only.

The following are **not** direct #296 correction targets:

- `DecisionSubjectRevised`;
- `DecisionScopeEstablished`;
- `DecisionScopeRevised`;
- `DecisionDeferred`;
- `DecisionWorkWithdrawn`;
- `DecisionWorkResumed`;
- relationship facts/corrections;
- technical/provenance records;
- the immutable `DecisionNeed` payload itself.

`target_fact_id` still names the immutable source fact/correction, but for an eligible ordinary fact it refers only to that fact's lifecycle-disposition contribution. Other payload and semantic dimensions on the target remain untouched.

### Unsupported Decision Need

R2 represents a later supported finding that the original Decision Need was erroneous/unsupported by a `DecisionLifecycleCorrected` **qualification of the initial `DecisionInitiated` disposition claim** to `NEED_RETRACTED_UNSUPPORTED`.

Older proposal vocabulary listing `DecisionNeedRetractedUnsupported` as a separate ordinary forward lifecycle fact is superseded for R2. Unsupported-Need retraction is corrective by definition and must not create a second competing mechanism for the same semantic outcome.

Direct `DISCONFIRM` of the initial `DecisionInitiated` claim is invalid because every Decision requires an interpretable lifecycle root. If the Need was unsupported, qualify that root to `NEED_RETRACTED_UNSUPPORTED` instead.

---

## 2. Correction fact contract

`DecisionLifecycleCorrected` is an immutable lifecycle fact using the established lifecycle fact identity, metadata, sequence, time, Actor Attribution, Trigger Provenance, Technical Provenance, and `OperationId` contracts.

Every correction has:

- its own fresh `DecisionLifecycleFactId`;
- the immediately next `DecisionLifecycleSequence`;
- complete `DecisionLifecycleFactMetadata`;
- exactly one `target_fact_id` naming an earlier eligible same-Decision disposition-bearing fact/correction;
- one effect: `QUALIFY` or `DISCONFIRM`;
- one required `DecisionLifecycleCorrectionBasis` carrying a non-empty purpose-specific reference explaining why this interpretive correction is supported;
- for `QUALIFY`, one complete replacement lifecycle-disposition claim as defined below.

The target must exist in the reconstructed history, belong to the same `InvestmentDecisionId`, be an eligible target under Section 1, and have a strictly lower lifecycle sequence. These constraints make correction targeting acyclic by construction.

Original facts/corrections remain permanently inspectable. Correction never rewrites the target's identity, metadata, Actor Attribution, provenance, business basis, effective time, or recorded time.

### Replacement support typing

A `QUALIFY` correction always carries:

- replacement `DecisionLifecycleDisposition`;
- correction fact `effective_at`, which is the effective time of the replacement disposition claim;
- required `DecisionLifecycleCorrectionBasis`.

Additional replacement support is disposition-specific:

- `UNRESOLVED` -> no additional disposition basis; the correction basis supports restoration/qualification of unresolved interpretation;
- `SUBSTANTIVELY_RESOLVED` -> required `TrustedHumanInvestmentDecisionBasis` with `SUBSTANTIVELY_RESOLVING` effect;
- `EXTERNALLY_RESOLVED` -> required `ExternalResolutionBasis`;
- `NEED_RETRACTED_UNSUPPORTED` -> required `UnsupportedDecisionNeedBasis` carrying the attributable support that the original Need determination was unsupported.

No generic `BusinessBasis(kind, identifier)` is introduced.

### `QUALIFY`

`QUALIFY` replaces the target branch's prior lifecycle-disposition claim with the correction's complete replacement claim. It may change disposition, effective time, or supporting basis while preserving all original history.

### `DISCONFIRM`

`DISCONFIRM` withdraws the target branch's lifecycle-disposition claim and supplies no replacement disposition or replacement disposition basis. It still requires its own truthful correction basis, Actor Attribution, and provenance.

---

## 3. Correction-chain semantics

Correction targeting creates support branches rooted in eligible ordinary disposition-bearing facts.

At a query boundary:

1. root with no applicable correction contributes its native disposition claim;
2. leaf `QUALIFY` contributes that correction's complete replacement claim;
3. leaf `DISCONFIRM` targeting an ordinary non-initiation disposition fact withdraws that branch's positive claim;
4. leaf `DISCONFIRM` targeting an earlier correction defeats that correction and restores the branch interpretation that existed immediately before the targeted correction;
5. `QUALIFY` targeting an earlier correction replaces that branch with the later complete replacement claim.

Example:

```text
F1  DecisionInitiated -> UNRESOLVED
F2  DecisionSubstantivelyResolved -> SUBSTANTIVELY_RESOLVED
C1  QUALIFY F2 -> EXTERNALLY_RESOLVED effective earlier
C2  DISCONFIRM C1

supported F2 branch after C2 -> F2's SUBSTANTIVELY_RESOLVED claim is restored
```

Restoration follows explicit target/effect semantics, never recorded recency.

If an ordinary resolution fact is directly disconfirmed, interpretation falls back to the surviving earlier disposition timeline; it does not manufacture a new `UNRESOLVED` fact.

---

## 4. Reconciliation of competing support

Recorded recency and larger lifecycle sequence never make one correction semantically authoritative merely because it was recorded later.

For each disposition-bearing root, evaluate every surviving correction branch available at the query boundary.

- materially equivalent positive claims coalesce while preserving all support fact IDs;
- all surviving branches disconfirming a non-initiation root determinately withdraw that root claim;
- positive support competing with explicit disconfirmation is irreconcilable;
- materially different positive claims are irreconcilable.

Positive claims are materially equivalent only when they establish the same disposition and effective time. Different valid typed support references may jointly support the same claim and remain separately inspectable.

Any irreconcilable root makes lifecycle interpretation contested/indeterminate for that query. If every root is determinate but surviving independent roots still imply incompatible lifecycle histories, overall interpretation is contested/indeterminate.

A valid contested history is not invalid history and must never be collapsed to newest-write-wins certainty.

---

## 5. Determinate and contested interpretation contract

The public semantic result is explicitly either determinate or contested. Semantics are equivalent to:

```text
DecisionLifecycleInterpretation =
    DeterminateDecisionLifecycleInterpretation(
        disposition,
        support_fact_ids,
    )
  | ContestedDecisionLifecycleInterpretation(
        support_fact_ids,
    )
```

Support IDs are immutable, duplicate-free `DecisionLifecycleFactId` values sufficient to explain the current determination/contest.

`InvestmentDecision.lifecycle_interpretation` is the canonical current lifecycle result. A determinate-disposition convenience may exist, but any operation requiring one disposition must fail with the typed `DecisionLifecycleInterpretationContested` semantic failure when interpretation is contested.

Contested interpretation is queryable state, not an exception merely because uncertainty exists.

---

## 6. Work-posture consequences

Work posture remains an independent semantic dimension and is **not corrected directly by #296**.

When lifecycle interpretation at `(T, K)` is:

- determinately `UNRESOLVED` and applicability is determinately operative -> reconstruct work posture independently from the applicable immutable work-posture history;
- determinately non-`UNRESOLVED` -> work posture is not applicable;
- contested -> no deterministic work posture may authorize ordinary work.

For determinately `UNRESOLVED`, replay the work-posture facts that are known by `K`, effective by `T`, and were valid domain acts under the knowledge available when they were recorded. Their semantics remain:

```text
no applicable posture fact -> ACTIVE
DecisionDeferred           -> DEFERRED
DecisionWorkWithdrawn       -> WITHDRAWN
DecisionWorkResumed         -> ACTIVE
```

Thus correcting a later resolution does not invent a posture transition. If history was `Deferred -> Resolved -> correction disconfirms Resolved`, the restored unresolved posture is `DEFERRED`. If history was `Deferred -> Resumed -> Resolved -> correction`, the restored posture is `ACTIVE`.

---

## 7. Historical validity and hindsight

Later correction may change today's supported understanding of an earlier effective interval without making a previously valid historical act retroactively invalid.

Raw-history validation asks whether an ordinary fact was valid under the facts/corrections **known when that act was recorded**. Effective interpretation asks what disposition is supported for `T` using knowledge cutoff `K`. These are related but distinct questions.

Example:

```text
10:00 Decision initiated
10:05 human Deferral recorded while Decision was known as UNRESOLVED
10:30 correction recorded establishing EXTERNALLY_RESOLVED effective 10:03
```

`as_known_at(10:05)` preserves the Deferral as a valid historical act. Current best interpretation may nevertheless say `EXTERNALLY_RESOLVED` effective 10:03. The Deferral remains attributable history but does not create effective work posture during an interval now understood as resolved.

Reconstruction must therefore not validate the entire raw history solely against today's corrected hindsight interpretation.

---

## 8. Temporal evaluation order

For `effective_at(T, known_at=K)`:

1. select only lifecycle facts/corrections with `recorded_at <= K`;
2. preserve raw immutable history and correction target graph;
3. resolve only correction effects with correction `effective_at <= T`;
4. reconcile correction branches under Sections 3-4;
5. evaluate surviving positive disposition claims with claim `effective_at <= T`;
6. derive determinate/contested lifecycle interpretation;
7. only if determinately `UNRESOLVED`, derive work posture independently under Section 6.

Do not discard a known target merely because its original effective time is later than `T` before correction resolution; a qualification may establish an earlier supported effective time.

Among sequential compatible surviving ordinary disposition claims, effective time determines temporal transition order. Lifecycle sequence is the deterministic tie-break only for otherwise compatible claims with the same effective instant; sequence never resolves competing correction support.

`as_known_at(K)` remains exactly:

```text
as_known_at(K) = effective_at(T=K, known_at=K)
```

Consequences:

- later-recorded earlier-effective correction affects only knowledge cutoffs at/after its recording;
- known future-effective correction does not apply early;
- correction-of-correction applies only when both known and effective;
- earlier `as_known_at` results remain stable.

---

## 9. Lifecycle sequence and Decision version

Every committed correction appends one lifecycle fact and always receives the immediately next `DecisionLifecycleSequence`.

`DecisionLifecycleSequence` and `DecisionVersion` are not numerically coupled.

`DecisionLifecycleFactMetadata.decision_version` records the Decision version resulting from that committed fact. Across lifecycle history, metadata versions are **non-decreasing**, not required to strictly increase on every fact.

A correction increments `DecisionVersion` exactly once when, at its recorded/commit boundary, it changes current concurrency-protected interpretation. Current concurrency-relevant interpretation includes:

- determinate vs contested result;
- current determinate disposition when one exists;
- the support fact-ID set that establishes that current result.

Therefore a currently effective correction that adds/removes material current support advances version even when the displayed disposition remains the same.

A historical-only or future-effective correction may append lifecycle sequence while repeating the prior `DecisionVersion` because current concurrency-protected interpretation did not change at commit time.

Crossing a future correction's `effective_at` due only to passage of time does **not** manufacture a synthetic fact or version increment. `DecisionVersion` is a commit concurrency token, not a clock token. Commands must evaluate authoritative temporal interpretation at their command-time boundary in addition to checking expected version; version alone cannot certify that a time-dependent interpretation is still applicable.

Same-operation/same-request replay never appends another correction. A semantic no-op does not manufacture history merely to move sequence/version.

---

## 10. Invalid correction vs valid contested interpretation

Reject correction creation/reconstruction as invalid when, among ordinary metadata/history failures:

- target is missing or unknown;
- target belongs to another Decision;
- target is not an eligible disposition-bearing fact/correction from Section 1;
- target sequence is not strictly earlier;
- correction fact identity is duplicated;
- direct `DISCONFIRM` targets `DecisionInitiated`;
- `QUALIFY` lacks a complete replacement disposition/support contract;
- `DISCONFIRM` supplies replacement disposition/support;
- correction or replacement basis is missing/wrong-purpose;
- live correction creation lacks known Actor Attribution;
- required temporal/provenance metadata is invalid.

Historical reconstruction may preserve truthful unknown or contested Actor Attribution.

By contrast, well-formed irreconcilable support is valid contested history. Operations requiring a deterministic disposition fail through `DecisionLifecycleInterpretationContested`; historical/query surfaces remain available.

---

## 11. Application and persistence consequences

History/query surfaces preserve at least:

- every raw original lifecycle fact;
- correction fact identity;
- `target_fact_id`;
- effect;
- replacement disposition and replacement basis when applicable;
- correction basis;
- effective/recorded time;
- Actor Attribution and provenance;
- support fact IDs explaining determinate or contested interpretation.

Durable persistence must reconstruct this target graph and must never implement correction as mutable overwrite, maximum sequence wins, `ORDER BY recorded_at DESC LIMIT 1`, or a latest-status row as sole authority.

A projection/cache remains derived and reproducible from immutable history.

R2 introduces no generic support graph, generic Subject/Scope/work-posture correction, event-sourcing framework, or platform-wide correction abstraction.

---

## 12. Required #296 closure fixtures

Domain verification must cover at least:

1. late External Resolution qualifies a prior resolution/initial claim without deleting history;
2. unsupported Need qualifies the initial disposition claim to `NEED_RETRACTED_UNSUPPORTED`;
3. direct `DISCONFIRM` of initiation is rejected;
4. Subject/Scope/work-posture/relationship facts are rejected as lifecycle-correction targets;
5. qualification may correct disposition, effective time, and typed replacement support;
6. disconfirming an ordinary resolution falls back to the surviving prior disposition timeline;
7. disconfirming a correction restores the immediately preceding branch interpretation;
8. qualifying a correction replaces that branch;
9. equivalent sibling positive claims coalesce;
10. conflicting positive siblings are contested;
11. positive-vs-disconfirm siblings are contested;
12. `Deferred -> Resolved -> correction` restores `UNRESOLVED + DEFERRED`;
13. `Deferred -> Resumed -> Resolved -> correction` restores `UNRESOLVED + ACTIVE`;
14. later backdated correction preserves the validity/attribution of acts that were valid under earlier knowledge;
15. later-recorded earlier-effective correction affects only knowledge cutoffs at/after recording;
16. known future-effective correction does not apply early;
17. `as_known_at(K) = effective_at(K, known_at=K)`;
18. valid contested state is queryable and deterministic operations fail typed;
19. correction identity/sequence is fresh/contiguous while metadata `DecisionVersion` may repeat for historical/future-only correction;
20. currently effective support-set change advances `DecisionVersion` exactly once;
21. clock passage across future `effective_at` creates no synthetic version/fact;
22. original/correction Actor Attribution, correction basis, replacement basis, Trigger Provenance, and Technical Provenance remain separately inspectable;
23. no #296 path corrects Scope/Subject/work posture or introduces a generic correction framework.

This bounded closure exhausts the #296 correction semantic universe. No remaining lifecycle-disposition correction choice is delegated to implementation.