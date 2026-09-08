# Common-Sense Invariant Hardening — Attention Propagation Addendum

**Status:** Active hardening record  
**Added:** 2026-09-07

## Observed failure

A material Polaris contract change can be implemented and locally verified correctly while known downstream artifacts still carry superseded assumptions. If the active Polaris agent waits for the repository owner to notice and request each downstream audit, the immediate task may be correct while the delivery system remains internally inconsistent.

The observed failure mode is therefore not unauthorized mutation. It is **failure to surface propagation risk** after a material durable change.

Examples include changes to:

- frozen public/domain contracts;
- architecture or ownership boundaries;
- authority semantics;
- canonical domain vocabulary;
- lifecycle or relationship semantics;
- persistence/application contracts;
- dependency or implementation sequencing.

These changes can invalidate or stale downstream Specs, Tickets, design documents, acceptance artifacts, roadmap wording, tests, wiki/glossary material, or process artifacts even when the changed artifact itself is correct.

## Invariant — Downstream Contract Propagation Attention

After a material durable change to a frozen contract, architecture boundary, authority model, canonical vocabulary, public API/domain contract, or implementation/dependency sequence, the active Polaris agent must proactively inspect the **known downstream artifact chain** before treating the change as locally complete.

The duty is to surface likely propagation work, not to assume authority over it.

At minimum:

1. identify the smallest known downstream artifact universe that could materially depend on the changed contract;
2. determine which artifacts are likely unaffected, which warrant audit, and which are already demonstrably stale;
3. tell the repository owner about material downstream audit/update candidates **without waiting for the owner to discover them independently**;
4. distinguish an Attention recommendation from an authorized mutation or scope expansion;
5. do not mutate additional artifacts unless the active workflow already authorizes that mutation or the repository owner authorizes it;
6. when the owner authorizes synchronization, propagate the contract in dependency order and re-check downstream readiness/baselines afterward.

A useful propagation model is:

```text
material contract / architecture / authority change
        ↓
child implementation tickets
        ↓
downstream Specs and their dependency/readiness state
        ↓
application / persistence / acceptance contracts
        ↓
roadmap, glossary/wiki, tests, and process artifacts where materially affected
```

This is not a requirement to perform a broad repository audit after every edit. The trigger is a **material semantic or sequencing change** with a plausible downstream contract surface.

## Boundary — Attention is not authority

Attention grants **zero** design, mutation, implementation, or scope authority.

An agent may and should say, for example:

> This foundation change likely affects Tickets X–Y and downstream Specs A–C; I recommend auditing them before implementation continues.

That statement does not authorize the agent to rewrite those artifacts unless mutation is already permitted by the active workflow or the owner explicitly authorizes it.

Likewise, the owner may decline or defer the suggested audit. If so, preserve any material known risk in the appropriate durable place rather than silently treating the downstream chain as synchronized.

## Earliest enforcement point

Enforce this invariant at the **post-change / pre-handoff boundary** where the material durable change becomes known, not later when a downstream implementation or verification step finally discovers the stale contract.

The practical question is:

> **What known downstream artifact could reasonably still encode the contract or sequencing assumption that just changed?**

If the answer names plausible artifacts, surface the audit before continuing to the next implementation step.

## Failure test

The Attention propagation duty fails when all of the following are true:

1. a material durable contract/architecture/authority/sequencing change occurred;
2. one or more known downstream artifacts plausibly depend on that changed meaning;
3. the active Polaris agent proceeds as though the local change is complete without surfacing those downstream audit candidates; and
4. the owner later has to independently notice and request the obvious propagation audit.

The owner having to ask does not make the eventual audit wrong; it demonstrates that the proactive Attention obligation was missed.

## Relationship to other hardening principles

This addendum complements, rather than replaces:

- **Universe Closure** — once an audit is authorized, close the relevant downstream artifact universe before claiming synchronization complete;
- **Transition-Bound Reasoning** — enforce propagation attention before the next consequential handoff or implementation transition;
- **Local Enforcement** — place durable fixes in the artifacts that actually own the stale contract;
- **Preserve Lean Workflows** — do not convert this into unconditional whole-repository review after ordinary edits.

The desired behavior is simple: **notice semantic blast radius early, surface it explicitly, and wait for authority before expanding mutation scope.**