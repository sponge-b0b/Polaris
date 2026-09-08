# R2 Investment Decision Lifecycle Correction Support Contract

**Status:** Owner-approved; design complete after Independent Spec #278 architecture remediation  
**Release:** 0.2.0  
**Primary entity:** `investment-decisions`  
**Purpose:** Freeze the complete R2/#296 lifecycle-disposition correction and temporal-interpretation contract without creating a generic correction framework for every Decision fact.

## Authority and supersession

This contract completes and narrows the lifecycle-correction semantics required by:

- `docs/proposed/investment-decisions-lifecycle-model.md`;
- `docs/proposed/application-use-cases-investment-decision-lifecycle.md`;
- `docs/proposed/durable-persistence-investment-decision-history.md`;
- `docs/proposed/investment-decisions-r2-foundation-public-contract.md`;
- `docs/product/requirements-0.2.0-amendment-r2-edge-cases.md`;
- Spec #278 and Ticket #296.

This document supersedes earlier revisions of this same contract that either allowed correction to target any lifecycle fact or treated lifecycle interpretation as only determinate/contested. Those formulations were incomplete because lifecycle facts contribute different semantic dimensions and temporal queries may legitimately contain zero effective lifecycle-disposition claims.

The Independent Spec #278 remediation additionally completes restoration and whole-result support membership, cross-root lifecycle compatibility, recursive temporal activation, append-time historical validation, explicit observation boundaries, correction replay versus new support, and unsupported-Need target eligibility. Earlier claims of design completeness did not determine these choices. The rules below supersede those incomplete readings, including any interpretation that derives domain “now” from the latest recorded fact or suppresses a distinct correction merely because its claim is equivalent.

For R2 and Ticket #296, **lifecycle correction means correction of supported lifecycle-disposition interpretation only**. A correction never generically rewrites a fact or every semantic contribution carried by that fact.

The R2 foundation public contract is complete. Surviving older proposal text that still calls #299 foundation items unresolved is historical text and not an implementation blocker.

### Scope-correction source conflict resolved

Older proposal text says that an erroneous `ESTABLISHED -> UNRESOLVED` Scope establishment/revision “requires correction” or that historical Subject/Scope correction uses an explicit correction path. For R2, those statements are superseded as follows:

- ordinary `ESTABLISHED -> UNRESOLVED` Scope mutation remains invalid;
- Ticket #296 does **not** correct Decision Scope or Decision Subject;
- erroneous historical Scope/Subject correction is deferred until a future purpose-specific contract actually requires it;
- R2 must not misuse `DecisionLifecycleCorrected` or invent a generic Decision-fact correction abstraction to solve that future problem;
- discovering an erroneous Scope/Subject fact in R2 preserves immutable history and fails closed for any operation that requires a corrected value until such a purpose-specific contract exists.

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

The target must be `DecisionInitiated` itself or an earlier correction whose ultimate ordinary disposition root is that same initiation. `QUALIFY` to `NEED_RETRACTED_UNSUPPORTED` is invalid on `DecisionSubstantivelyResolved`, `DecisionExternallyResolved`, or any correction lineage rooted in either resolution fact. Every permitted unsupported-Need qualification requires `UnsupportedDecisionNeedBasis` in addition to `DecisionLifecycleCorrectionBasis`.

Correction-of-correction within the initiation lineage remains permitted. Unsupported-Need retraction is branch-local: it does not implicitly defeat any independent surviving resolution root. Those roots still participate in the cross-root compatibility rules in Section 4.

Older proposal vocabulary listing `DecisionNeedRetractedUnsupported` as a separate ordinary forward lifecycle fact is superseded for R2. Unsupported-Need retraction is corrective by definition and must not create a second competing mechanism for the same semantic outcome.

Direct `DISCONFIRM` of the initial `DecisionInitiated` claim is invalid because every Decision requires an interpretable lifecycle root once that root is effective. If the Need was unsupported, qualify that root to `NEED_RETRACTED_UNSUPPORTED` instead.

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

The last replacement is permitted only on the initiation lineage defined in Section 1. The other replacement dispositions are permitted on any eligible ordinary root/correction, subject to their typed support requirements. Qualification of a correction, including a disconfirmation, supplies a complete positive replacement claim; it does not inherit the replaced claim's basis.

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

### Recursive branch resolution and independent activation

Resolve a correction relative to its explicit target ancestry on that branch, not to the globally reconciled result before its recording. Sibling correction branches remain independent. Replacing or defeating one sibling never erases another sibling.

Knowledge is a hard prerequisite: the correction and all required target ancestry must be recorded by `K`. Keep that known ancestry available for traversal even when an ancestor's own effect is future-effective. Each correction activates independently when its own `effective_at <= T`; it does not wait for its ancestors to become effective.

An applicable qualification immediately supplies its complete replacement claim, including when the targeted correction is future-effective. An applicable disconfirmation immediately defeats its target correction and restores the preceding branch interpretation, including preempting a known future-effective correction. A branch with future corrections but no applicable correction effect contributes no extra competing alternative merely because those future facts exist.

Restoration can restore either a positive claim or a withdrawal. For example, disconfirming a correction that had restored an ordinary resolution can restore the earlier withdrawal of that resolution. This rule recurses to any finite correction depth; strictly earlier target sequences prevent cycles. Disconfirming a disconfirmation does not mean unconditionally making the ordinary root positive.

Only positive claims effective by `T` and applicable withdrawals participate in reconciliation. A future positive claim cannot create present contest against an applicable withdrawal. Future corrections alone create neither present support nor present contest.

### Surviving branch support

An ordinary positive fact contributes its own `DecisionLifecycleFactId`. A qualification contributes its own ID as a complete replacement positive claim; neither its ordinary root nor replaced corrections automatically remain positive support.

A restored claim exposes its surviving positive/root support plus every currently effective correction fact required to establish that restoration. Apply this recursively. Defeated corrections are excluded from current `support_fact_ids` but remain inspectable in immutable history. A withdrawal likewise retains its surviving correction support, including corrections required to restore that withdrawal. Equivalent surviving branches union their support IDs without counting the number of supporters as authority.

For `F2 -> QUALIFY C1 -> DISCONFIRM C2`, when `C1` would otherwise affect the effective claim, the restored `F2` claim has support `{F2, C2}`, not `{F2}` or `{F2, C1, C2}`. A further `DISCONFIRM C3` targeting `C2` restores `C1`'s replacement with surviving support `{C1, C3}`. Section 5 excludes future-only suppression and support unrelated to the whole-result interpretation.

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

An irreconcilable effective root makes lifecycle interpretation contested/indeterminate for that query. Surviving independent roots must also satisfy the following semantic lifecycle compatibility rules after correction resolution and effective-time filtering.

### Cross-root lifecycle compatibility

Here, a terminal claim has disposition `SUBSTANTIVELY_RESOLVED`, `EXTERNALLY_RESOLVED`, or `NEED_RETRACTED_UNSUPPORTED`.

| Surviving effective positive claims across ordinary roots | Interpretation |
| --- | --- |
| Only `UNRESOLVED` claims | Compatible unresolved history |
| Unresolved claims followed by exactly one terminal claim, after equivalent claims coalesce | Determinate terminal transition |
| Terminal claims with the same disposition and effective instant | Equivalent; coalesce and union surviving support |
| Terminal claims differing in disposition or effective instant | Contested, even if one was recorded later |
| A terminal claim followed by an unresolved claim | Contested; never an implicit reopening |
| A lone terminal claim after correction replaces initiation's initial disposition | May be determinate; no synthetic earlier unresolved claim is required |

Effective time orders claims. At equal effective times, the ordinary root's lifecycle sequence may order otherwise compatible unresolved-to-terminal claims. The replacing correction's sequence is not the root's transition position. Sequence never selects between conflicting terminal claims or competing correction branches. A terminal claim preceding an unresolved claim at the same instant in ordinary-root sequence remains incompatible.

These rules apply to roots after correction regardless of their native disposition. They do not impose a semantic winner by root identity, larger sequence, recording time, or stronger-looking provenance. In particular, qualifying initiation to unsupported-Need retraction does not implicitly withdraw another resolution root.

Compatibility testing does not by itself add historical roots to current `support_fact_ids`; whole-result membership is defined in Section 5.

A valid contested history is not invalid history and must never be collapsed to newest-write-wins certainty.

---

## 5. Temporal result cardinality and lifecycle interpretation

Temporal querying distinguishes **knowledge-universe absence** from a **known Decision with no effective lifecycle-disposition claim yet**.

### Decision not known at the knowledge cutoff

If `DecisionInitiated.recorded_at > K`, the Decision is not part of the historical knowledge universe at `known_at=K`.

That outcome is **not** a `DecisionLifecycleInterpretation` variant. The historical query returns the existing domain/application not-found-at-cutoff semantic outcome because there is no known Decision to interpret at that knowledge boundary.

Do not fabricate `UNRESOLVED`, `NOT_YET_EFFECTIVE`, or `CONTESTED` for a Decision that was not yet known.

### Decision known but not yet effective

If `DecisionInitiated.recorded_at <= K` but, after correction resolution and effective-time filtering, zero supported positive lifecycle-disposition claims are effective at `T`, the Decision is known but **not yet effective** at that temporal boundary.

This is valid lifecycle interpretation, distinct from both `UNRESOLVED` and contest.

The public semantic result is equivalent to:

```text
DecisionLifecycleInterpretation =
    NotYetEffectiveDecisionLifecycleInterpretation
  | DeterminateDecisionLifecycleInterpretation(
        disposition,
        support_fact_ids,
    )
  | ContestedDecisionLifecycleInterpretation(
        support_fact_ids,
    )
```

`NotYetEffectiveDecisionLifecycleInterpretation` has no disposition and no effective support fact-ID set. The known raw initiation/correction history remains inspectable separately.

A determinate result has one reconciled effective disposition and immutable duplicate-free supporting `DecisionLifecycleFactId` values. A contested result preserves the immutable duplicate-free support fact IDs whose effective support cannot reconcile.

### Whole-result support membership

`support_fact_ids` is semantically unordered and represents the minimal surviving support directly establishing the current whole-result interpretation, not complete historical ancestry. “Minimal” excludes irrelevant history; it does not select one minimum-cardinality witness and discard other equivalent or conflicting surviving support.

| Result | Positive/conflicting support retained |
| --- | --- |
| Determinate unresolved | Support of the latest effective unresolved claim; union equivalent unresolved claims at that effective instant |
| Determinate terminal | Union of equivalent terminal-claim support establishing the result |
| Contested | Union of every effective branch participating in a conflict, including applicable withdrawal support; exclude unrelated compatible history |
| `NOT_YET_EFFECTIVE` | No effective support set |

In a determinate result, also retain surviving applicable withdrawal support when necessary to suppress an otherwise-effective claim. Thus `F1: UNRESOLVED`, `F2: SUBSTANTIVELY_RESOLVED`, `C1: DISCONFIRM F2` yields unresolved support `{F1, C1}` when `F2` would otherwise be effective. `F2` remains historical, not current positive support. Future-only suppressed claims contribute no present support. This also applies to preemption of a future-effective correction: its preemption does not add current support solely to explain an effect that has not become effective yet.

For contest, retain all effective conflict participants, coalescing equivalent contributors by union. Within a root, positive-vs-withdrawal and differing-positive conflicts retain their participating branch support. Across roots, retain the support of incompatible claims under Section 4. Do not pad the contested set with unrelated compatible roots or defeated ancestry. Every resulting current support-set change is concurrency-relevant under Section 9.

### Public observation boundary

Every public lifecycle interpretation is explicitly bound to the timezone-aware `(effective_at=T, known_at=K)` it represents, including `NOT_YET_EFFECTIVE`. The temporal boundary is observable alongside the result kind and any disposition/support, whether carried on the value or its purpose-specific containing view. Query semantics compare instants, not timezone spelling.

The pure Decision domain reads no wall clock and derives no implicit “now” from fact timestamps. Any current-view convenience requires a caller-supplied observation instant and uses `T=K` at that instant. `as_known_at(K)` is exactly `effective_at(K, known_at=K)`. A history-only reconstruction signature in the older foundation contract describes the validation boundary; it does not authorize an unbound current interpretation. A public surface returning interpreted state must receive and expose its observation boundary.

`InvestmentDecision.lifecycle_interpretation` is the canonical current lifecycle result. A determinate-disposition convenience may exist, but operations requiring one effective disposition must fail explicitly when interpretation is either `NOT_YET_EFFECTIVE` or contested.

Contested and not-yet-effective interpretation are queryable states; neither is invalid history.

### Cardinality closure

After knowledge filtering and correction/effective-time resolution, the lifecycle query universe is closed as:

```text
Decision unknown at K
    -> not found at knowledge cutoff; no lifecycle interpretation

Decision known at K, zero effective positive claims at T
    -> NOT_YET_EFFECTIVE

Decision known at K, one reconciled effective interpretation at T
    -> DETERMINATE

Decision known at K, irreconcilable effective support at T
    -> CONTESTED
```

No fourth implicit/nullable state is left to implementation.

---

## 6. Work-posture consequences

Work posture remains an independent semantic dimension and is **not corrected directly by #296**.

When lifecycle interpretation at `(T, K)` is:

- `NOT_YET_EFFECTIVE` -> no effective work posture exists and ordinary Decision work cannot proceed;
- determinately `UNRESOLVED` and applicability is determinately operative -> reconstruct work posture independently from applicable immutable work-posture history;
- determinately non-`UNRESOLVED` -> work posture is not applicable;
- contested -> no deterministic work posture may authorize ordinary work.

For determinately `UNRESOLVED`, replay the work-posture facts that are known by `K`, effective by `T`, and were valid domain acts under the knowledge available when they were recorded. Their semantics remain:

```text
no applicable posture fact -> ACTIVE
DecisionDeferred           -> DEFERRED
DecisionWorkWithdrawn       -> WITHDRAWN
DecisionWorkResumed         -> ACTIVE
```

Choose the latest effective applicable posture fact, ordered by `effective_at` and then lifecycle sequence for equal-effective-time ties. This interpretation ordering does not replace append-time validation. Applicability remains an independently established domain input; lifecycle correction does not manufacture operative authority.

Thus correcting a later resolution does not invent a posture transition. If history was `Deferred -> Resolved -> correction disconfirms Resolved`, the restored unresolved posture is `DEFERRED`. If history was `Deferred -> Resumed -> Resolved -> correction`, the restored posture is `ACTIVE`.

---

## 7. Historical validity and hindsight

Later correction may change today's supported understanding of an earlier effective interval without making a previously valid historical act retroactively invalid.

Raw-history validation asks whether an ordinary fact was valid under the facts/corrections **known when that act was appended**. Effective interpretation asks what disposition is supported for `T` using knowledge cutoff `K`. These are related but distinct questions.

`recorded_at` is non-decreasing by lifecycle sequence; equal recording timestamps are permitted. Validate each ordinary fact against its strictly earlier lifecycle-sequence prefix, not all facts with the same recording timestamp and never later history. Public `known_at=K` queries still include all facts recorded by `K`; the strict prefix is the append-admission boundary, not an additional public timestamp-cutoff rule.

Using only that preceding knowledge, an ordinary act must satisfy its transition prerequisites both at its recording-time interpretation and at its proposed effective-time interpretation. It must not introduce an incompatible lifecycle into any already-known portion of the effective timeline, including known future intervals. Reject such ordinary reinterpretation through typed invalid-transition semantics; it requires explicit lifecycle correction where eligible. Same-time later sequence facts cannot justify or invalidate an earlier act.

Historical reconstruction applies those admission rules to each ordinary fact's own prefix. Later corrections may change current effective applicability, including by backdating, without retroactively invalidating an ordinary act that passed its append-time checks.

Corrections bypass the ordinary unresolved/operative work gate and remain available in terminal, contested, and not-yet-effective states. They still satisfy correction-specific target, knowledge, operation, eligibility, typed support, attribution, and metadata requirements. This exception does not authorize out-of-scope Subject, Scope, work-posture, or relationship correction.

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

1. determine whether `DecisionInitiated.recorded_at <= K`; if not, return not-found-at-knowledge-cutoff and do not construct lifecycle interpretation;
2. select only other lifecycle facts/corrections with `recorded_at <= K`;
3. preserve raw immutable history and correction target graph;
4. independently activate correction effects with their own `effective_at <= T`, retaining known target ancestry for recursive branch resolution under Section 3;
5. evaluate surviving positive disposition claims with claim `effective_at <= T` and applicable withdrawals; future-only support cannot produce current contest;
6. reconcile effective within-root branches and cross-root lifecycle compatibility under Section 4;
7. derive `NOT_YET_EFFECTIVE` when zero effective positive claims remain, otherwise derive determinate/contested lifecycle interpretation and exact whole-result support under Section 5;
8. only if determinately `UNRESOLVED`, derive work posture independently under Section 6.

Do not discard a known target merely because its original effective time is later than `T` before correction resolution; a qualification may establish an earlier supported effective time.

Among compatible surviving ordinary-root disposition claims, effective time determines temporal transition order. The ordinary root's lifecycle sequence is the deterministic tie-break only for otherwise compatible claims with the same effective instant; sequence never resolves competing correction support. Posture ordering follows Section 6.

`as_known_at(K)` remains exactly:

```text
as_known_at(K) = effective_at(T=K, known_at=K)
```

Examples for initiation recorded at 10:00 and effective at 11:00:

```text
as_known_at(09:30) -> not found at knowledge cutoff
as_known_at(10:30) -> NOT_YET_EFFECTIVE
as_known_at(11:00) -> DETERMINATE(UNRESOLVED)
```

A later correction recorded at 12:00 that qualifies initiation to `UNRESOLVED` effective at 09:00 does not change `as_known_at(10:30)`, because it was not yet known. But `effective_at(10:30, known_at=12:30)` may then be `DETERMINATE(UNRESOLVED)`.

Consequences:

- later-recorded earlier-effective correction affects only knowledge cutoffs at/after its recording;
- known future-effective initiation/correction does not apply early;
- correction-of-correction applies only when both known and effective;
- earlier `as_known_at` results remain stable.

---

## 9. Lifecycle sequence and Decision version

Every committed correction appends one lifecycle fact and always receives the immediately next `DecisionLifecycleSequence`.

`DecisionLifecycleSequence` and `DecisionVersion` are not numerically coupled.

`DecisionLifecycleFactMetadata.decision_version` records the Decision version resulting from that committed fact. Across lifecycle history, metadata versions are **non-decreasing**, not required to strictly increase on every fact.

Commands reconstruct authoritative state at their own recording boundary and may not rely on a stale materialized view. Determine an append's version consequence by comparing its strictly preceding history and appended history at the same recording boundary (`T=K=recorded_at`). For a correction, increment `DecisionVersion` exactly once if this comparison changes current concurrency-protected interpretation. Current concurrency-relevant interpretation includes:

- `NOT_YET_EFFECTIVE` vs determinate vs contested result;
- current determinate disposition when one exists;
- the support fact-ID set that establishes the current determinate/contested result.

Therefore a currently effective correction that changes `NOT_YET_EFFECTIVE -> DETERMINATE`, `DETERMINATE -> CONTESTED`, disposition, or current support set advances version exactly once.

A historical-only or future-effective correction may append lifecycle sequence while repeating the prior `DecisionVersion` because current concurrency-protected interpretation did not change at commit time.

Crossing a future initiation/correction `effective_at` due only to passage of time does **not** manufacture a synthetic fact or version increment. `DecisionVersion` is a commit concurrency token, not a clock token. Commands must evaluate authoritative temporal interpretation at their command-time boundary in addition to checking expected version; version alone cannot certify that a time-dependent interpretation is still applicable.

Exact idempotent replay is the only correction append no-op: the same operation/request returns the existing result without appending; reuse of that idempotency identity for a different request is an idempotency conflict. Application/persistence owns request receipts and transactional idempotency; #296 introduces no separate domain receipt framework.

Every distinct, valid, attributable correction act appends a fresh immutable correction fact, even if its replacement disposition, effective instant, and typed support are equivalent to existing surviving support. Equivalent branches coalesce at interpretation time and retain their distinct surviving IDs. Appending history and changing current interpretation are separate questions: a distinct act may advance lifecycle sequence while retaining `DecisionVersion`. Ordinary Subject/Scope semantic no-op rules are unchanged and are not a basis for suppressing an equivalent correction act.

---

## 10. Invalid correction vs valid temporal/contested interpretation

Reject correction creation/reconstruction as invalid when, among ordinary metadata/history failures:

- target is missing or unknown;
- target belongs to another Decision;
- target is not an eligible disposition-bearing fact/correction from Section 1;
- target sequence is not strictly earlier;
- correction fact identity is duplicated;
- direct `DISCONFIRM` targets `DecisionInitiated`;
- `QUALIFY` to `NEED_RETRACTED_UNSUPPORTED` targets a resolution-root lineage rather than initiation's lineage;
- `QUALIFY` lacks a complete replacement disposition/support contract;
- `DISCONFIRM` supplies replacement disposition/support;
- correction or replacement basis is missing/wrong-purpose;
- live correction creation lacks known Actor Attribution;
- required temporal/provenance metadata is invalid.

Invalid reconstruction includes decreasing `recorded_at` in lifecycle sequence and ordinary acts that fail their own strict-prefix temporal admission checks. A later correction producing valid contested interpretation is not such an admission failure. Missing required known target ancestry cannot be replaced with a guessed branch.

Historical reconstruction may preserve truthful unknown or contested Actor Attribution.

By contrast:

- Decision absent from the knowledge universe is a historical-query not-found outcome, not invalid history;
- a known Decision with zero effective disposition claims is valid `NOT_YET_EFFECTIVE` interpretation;
- well-formed irreconcilable support is valid contested interpretation.

Operations requiring a deterministic effective disposition fail through explicit typed semantics for not-yet-effective or contested interpretation; historical/query surfaces remain available.

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
- temporal result kind (`NOT_YET_EFFECTIVE | DETERMINATE | CONTESTED`) for a known Decision;
- the explicit effective and knowledge boundaries of every interpreted result;
- support fact IDs explaining determinate or contested interpretation.

Application/query behavior must distinguish not-found-at-knowledge-cutoff from `NOT_YET_EFFECTIVE`; neither may be encoded as `UNRESOLVED` or `CONTESTED`.

Durable persistence must reconstruct the correction target graph and temporal result and must never implement correction as mutable overwrite, maximum sequence wins, `ORDER BY recorded_at DESC LIMIT 1`, or a latest-status row as sole authority.

A projection/cache remains derived and reproducible from immutable history.

Application supplies the observation instant for current reads and trusted command recording time. It reevaluates authoritative interpretation at the command boundary in addition to expected-version/CAS checks. Persistence preserves non-decreasing recording time and exact lifecycle sequence so equal-time prefix validation is reconstructable. It must retain the target ancestry required for independently effective correction descendants, not discard future-effective ancestors before resolution. Receipts distinguish exact replay from a distinct equivalent correction act. No projection may substitute full historical ancestry for the minimal surviving support set or select a terminal claim by recency.

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
14. later backdated correction preserves validity/attribution of acts valid under earlier knowledge;
15. initiation not recorded by `K` yields not-found-at-knowledge-cutoff and no lifecycle interpretation;
16. initiation recorded by `K` but future-effective at `T` yields `NOT_YET_EFFECTIVE`, not `UNRESOLVED`, `CONTESTED`, or not-found;
17. `NOT_YET_EFFECTIVE` exposes no work posture and ordinary work requiring an effective disposition fails explicitly;
18. later correction may establish an earlier effective initiation only for knowledge cutoffs at/after correction recording;
19. later-recorded earlier-effective correction affects only knowledge cutoffs at/after recording;
20. known future-effective correction does not apply early;
21. `as_known_at(K) = effective_at(K, known_at=K)`;
22. valid contested state is queryable and deterministic operations fail typed;
23. correction identity/sequence is fresh/contiguous while metadata `DecisionVersion` may repeat for historical/future-only correction;
24. currently effective `NOT_YET_EFFECTIVE`/determinate/contested/disposition/support-set change caused by a committed correction advances `DecisionVersion` exactly once;
25. clock passage across future initiation/correction `effective_at` creates no synthetic version/fact;
26. original/correction Actor Attribution, correction basis, replacement basis, Trigger Provenance, and Technical Provenance remain separately inspectable;
27. no #296 path corrects Scope/Subject/work posture or introduces a generic correction framework.

Additional fixtures required by the Independent Spec remediation:

28. `F2 -> QUALIFY C1 -> DISCONFIRM C2` restores `{F2, C2}`; disconfirming `C2` restores `{C1, C3}`; defeated IDs remain inspectable but absent from current support;
29. nested correction can restore withdrawal as well as positive support; qualification of a withdrawal supplies a complete positive claim;
30. branch-local restoration preserves competing siblings, including equivalent siblings and siblings that become contested after restoration;
31. applicable qualification of a known future-effective correction applies independently; unknown required ancestry cannot participate;
32. effective disconfirmation preempts a known future-effective correction; future-only suppression adds no present support, and later effective-boundary passage creates no synthetic version;
33. future corrections alone add neither current branches/support nor contest; future positive versus applicable withdrawal does not create present contest;
34. unresolved-only histories select the latest effective unresolved support, union equivalent same-instant support, and exclude older compatible roots;
35. compatible unresolved-to-terminal history exposes terminal support, not every predecessor ID;
36. same-disposition/same-instant terminal roots coalesce; same-disposition/different-instant and different-disposition terminal roots contest;
37. terminal-before-unresolved histories contest, including equal-time ordinary-root ordering; correction sequence cannot manufacture a different root order or select a terminal winner;
38. a lone corrected terminal initiation may be determinate; unsupported-Need initiation does not implicitly defeat an independent resolution;
39. determinate fallback includes necessary withdrawal support but excludes the withdrawn positive root; future-only suppressed claims add no present support;
40. contested results union all effective conflict participants, including withdrawal branches, and exclude unrelated compatible history;
41. every public result, including `NOT_YET_EFFECTIVE`, exposes `(T,K)`; current views require supplied time and queries never read a domain clock or infer now from the latest fact;
42. stale views cannot authorize commands; both sides of the append/version comparison use the command recording boundary;
43. equal-recorded-time histories admit an act using only its earlier sequence prefix; decreasing recording timestamps fail reconstruction;
44. ordinary acts fail if recording-time or proposed-effective-time prerequisites fail, or if they introduce incompatibility in an already-known future interval;
45. later backdated correction preserves admission validity, while effective posture is selected independently by `(effective_at, sequence)`;
46. corrections can operate in terminal, contested, not-yet-effective, non-operative, and contested-applicability states while all correction-specific validity rules remain enforced;
47. distinct equivalent correction operations append separate IDs and union surviving support; exact replay does not append; changed-request reuse conflicts at the application/persistence idempotency boundary;
48. support-only changes increment current version once; append-only changes outside the current interpretation do not; query or clock passage never changes the committed version;
49. unsupported-Need qualification accepts initiation and nested initiation-lineage targets with both required bases, rejects both resolution roots and their nested lineages, and retains the ban on direct initiation disconfirmation.

The receipt/idempotency boundary in fixture 47 is an application/persistence obligation; pure #296 tests prove distinct correction admission and support/version effects without implementing receipts.

## 13. Bounded design-completeness closure

The owner resolved the two reported decisions (restoration support membership and cross-root compatibility) and six additional coupled decisions found by the bounded sweep. The latter cover recursive temporal activation, whole-result support membership, append-time historical validity, explicit observation boundaries/posture ordering, correction replay versus distinct support, and unsupported-Need lineage eligibility.

| Semantic universe | Governing sections |
| --- | --- |
| Domain owner, immutable identities, attribution/provenance and purpose-specific trusted bases | 1–2, 10–11 |
| All eligible/ineligible target kinds, initiation/resolution lineages, zero/one/many siblings and arbitrary finite correction depth | 1–4, 10 |
| Positive replacement, withdrawal, restoration of positive/withdrawal, defeated ancestry and equivalent/conflicting support | 3–5 |
| Unknown-at-K, known zero-positive, determinate and contested results; before/equal/after effective and recording boundaries | 3–5, 8 |
| Cross-root unresolved/terminal compatibility, same/different disposition and instant, equal-time ordering and no reopening | 4 |
| Exact whole-result support, fallback, conflict participants and future-only exclusion | 5 |
| Work-posture applicability, ordering, stale views and independent historical validity | 6–9 |
| Strict append prefix, same-time recording, ordinary admission versus correction admission and hindsight | 7, 10 |
| Fresh append versus replay, current support/version comparison and clock-only changes | 9, 11 |
| Typed invalid-history/operation outcomes versus valid absence/not-yet-effective/contested results; downstream reconstruction | 5, 10–11 |

```text
Reported blocker coupling groups: 2
Owner-resolved coupling groups: 8
New material choices discovered by closure: 6
Unresolved material choices after closure: 0
Material implementation-delegated architecture choices: 0
```

The closure is bounded to #296's lifecycle-disposition correction and temporal interpretation. It does not certify implementation, relationship-correction design, or future Subject/Scope/work-posture correction. Private helper structure, equivalent algorithms, code layout, and test mechanics remain implementation-owned. Spec #278 incorporates this authority; existing ticket contracts must be reconciled by `$to-tickets` before implementation resumes.
