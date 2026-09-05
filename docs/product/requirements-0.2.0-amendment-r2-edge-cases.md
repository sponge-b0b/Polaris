# Polaris 0.2.0 Requirements Amendment — R2 Decision-Lifecycle Edge Cases

**Status:** Proposed  
**Release:** 0.2.0  
**Purpose:** Amend the approved `requirements-0.2.0.md` only where the R2 adversarial pre-Spec audit exposed contradictions or missing load-bearing lifecycle semantics.

## Authority

This proposed amendment is subordinate to the frozen product/domain doctrine in [`domain-model.md`](./domain-model.md) and [`../../CONTEXT.md`](../../CONTEXT.md). If approved, it will take precedence over only the clauses of [`requirements-0.2.0.md`](./requirements-0.2.0.md) explicitly amended below.

No other approved requirement is weakened.

---

# 1. Scope may remain unresolved during initiation

### DEC-013 — Decision Scope may be unresolved during initiation

An Investment Decision MAY be initiated while its Decision Scope remains unresolved when a genuine Decision Need and coherent Decision Subject already warrant deliberate judgment.

Unresolved or partially established Scope MUST remain explicit. Polaris MUST NOT invent Portfolio applicability merely to complete an initiation path.

Before a final Capital-Relevant Investment Recommendation or Human Investment Decision is formed, applicable Portfolio scope MUST be established sufficiently for that consequential use.

---

# 2. Decision work withdrawal is not investment judgment

### DEC-014 — Withdrawal of decision work does not resolve the investment choice

Polaris MUST be able to preserve that active work on an unresolved Investment Decision was explicitly stopped or withdrawn while the underlying Decision Need remains unresolved.

Stopping, dismissing, or withdrawing Polaris work MUST NOT by itself be represented as a Human Investment Decision, Deferral, substantive resolution, External Resolution, or Supersession.

If the same coherent unresolved choice later resumes, Polaris MAY continue the same Investment Decision identity when the underlying Decision Need remains valid and no later lifecycle fact requires a new Decision.

---

# 3. Erroneous or unsupported Decision Needs remain historical

### DEC-015 — Unsupported Decision Need determination is corrected non-destructively

When Polaris later establishes that an earlier Decision Need determination was erroneous or unsupported rather than eliminated by changed circumstances, the original Decision Need and Investment Decision history MUST remain attributable.

Polaris MUST represent the later correction explicitly and MUST NOT misclassify the case as External Resolution merely because active decision work should stop.

A later genuinely supported choice follows normal Decision Need and Investment Decision identity rules; the corrected historical Decision MUST NOT be silently reactivated as though the erroneous Need had always been valid.

---

# 4. Supersession is orthogonal to historical lifecycle disposition

### DEC-016 — Supersession does not replace lifecycle disposition

Supersession MUST be represented as an explicit relationship affecting continuing applicability or operative investment basis.

An Investment Decision MAY be superseded while unresolved or after substantive or External Resolution.

Supersession MUST NOT erase, replace, or falsify an earlier lifecycle disposition, Deferral/withdrawal history, Human Investment Decision, Recommendation history, or other attributable fact.

The relationship model MUST NOT assume one-to-one Supersession cardinality unless a later domain requirement explicitly establishes that restriction.

---

# 5. Concurrent initiation must fail closed on continuity ambiguity

### DEC-017 — Concurrent initiation preserves one coherent unresolved choice

When initiation work discovers or could race with another unresolved Investment Decision that may represent the same coherent choice, Polaris MUST re-evaluate continuity before committing a distinct new Investment Decision.

If continuity cannot be determined reliably, Polaris MUST preserve the ambiguity and withhold automatic creation of another Decision rather than silently manufacturing duplicate identity.

Technical idempotency by operation ID alone is insufficient because independently initiated operations can use different operation IDs.

---

# 6. Late lifecycle facts and corrections

### DEC-018 — Late-discovered lifecycle facts preserve both effective truth and prior knowledge

A lifecycle-relevant fact MAY be recorded after the time at which it is currently understood to have been effective.

When later information changes the supported understanding of an earlier lifecycle disposition, Polaris MUST:

- preserve the originally recorded fact and what was known at the time;
- preserve the later correction or qualification as a new attributable fact;
- preserve effective time separately from recorded/known time;
- avoid silently rewriting a Human Investment Decision or other historical act merely because later information changes lifecycle interpretation;
- preserve unresolved or contested interpretation when available facts do not support one deterministic effective disposition.

Historical queries MUST distinguish what Polaris knew at an earlier cutoff from the lifecycle disposition currently understood to have been effective at an earlier time.

---

# 7. Actor Attribution is distinct from trigger provenance

### DEC-019 — Decision Need and lifecycle acts preserve actor and trigger separately

Where Actor Attribution materially applies, Polaris MUST preserve who formed or performed the relevant domain act separately from the observation, request, schedule, source event, model/provider call, workflow attempt, or other trigger/provenance that caused work to occur.

A user request MAY be the trigger for a Polaris-attributed Decision Need determination; conversely, a human MAY directly form an attributable Decision Need. Technical model/provider/workflow identity MUST NOT be substituted for Actor Attribution.

---

# 8. Decision-to-Decision context is hindsight-safe

### MEM-011 — Prior-Decision context binds the historical state actually used

When a prior Investment Decision is materially used as Decision Context for a later Investment Decision, Polaris MUST preserve enough temporal/version information to reconstruct the prior Decision state that was actually available or used.

Later changes to the prior Decision MUST NOT silently alter the historical meaning of the later Decision's context binding.

Candidate retrieval or present-day similarity MUST NOT be represented as historical material use.

---

# 9. Acceptance-scenario correction

## AS-003 — Deferral and later resumption — proposed amendment

Replace the original AS-003 wording with:

> **AS-003 — Deferral and later resumption**  
> An attributable human Deferral leaves the same Investment Decision unresolved. A later awaited condition, newly available material Evidence, or other material event may cause Attention to resume that same coherent unresolved choice. A **Review Condition**, by contrast, belongs to a substantively resolved Decision and causes Attention to evaluate whether a renewed Decision Need exists; it does not resume the resolved Decision.

This preserves:

```text
deferred unresolved Decision
    + awaited condition
    -> same Decision may resume

resolved Decision
    + Review Condition
    -> Attention evaluates possible new Decision Need
```

---

# 10. Milestone acceptance interpretation

R2 is responsible for **foundational acceptance evidence** for the Decision-kernel portions of `AS-001` through `AS-005` and full evidence for `AS-022`.

R2 MUST NOT claim full closure of an acceptance scenario whose required participants are intentionally deferred to later milestones, including Attention, Evidence, full Decision Context, Governance-owned Human Investment Decision, or another not-yet-implemented owner.

Final scenario closure occurs only when every material participant required by that scenario is present and the scenario is exercised end to end.
