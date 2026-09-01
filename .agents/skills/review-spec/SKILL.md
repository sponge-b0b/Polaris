---
name: review-spec
description: Review a verified completed Spec using the existing independent Standards, Spec, and Architecture axes, while preserving provenance when a finding contradicts earlier ticket or Spec certification.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

# Review Spec

Perform the existing independent adversarial review. This hardening does **not** turn `$review-spec` into an implementation verifier; it adds upstream-certification provenance so a downstream finding can identify which earlier certification it disproved.

## Base Procedure

Read this file first, then read in full:

```text
.agents/skills/review-spec/procedure.md
```

The base procedure remains normative for checkpoint pinning, ownership refresh, delivery guards, review-state recovery, Standards/Spec/Architecture universes, fresh reviewer execution, parent orchestration boundaries, targeted challenge, finding freeze/provenance validation, Root Blocker reconciliation, convergence saturation, pending remediation, exit, and persistence.

This file strengthens frozen-finding provenance and the human-facing aggregate format. On conflict, this file wins.

## Human-Facing Aggregate Format

The final user-facing review result MUST present the three review axes in this order and MUST always include both `Blocking` and `Advisory` subsections for every axis, even when a subsection has no findings:

```markdown
## Standards

### Blocking
- <findings or None>

### Advisory
- <findings or None>

## Spec

### Blocking
- <findings or None>

### Advisory
- <findings or None>

## Architecture

### Blocking
- <findings or None>

### Advisory
- <findings or None>
```

Use `None.` when a subsection has no findings so the presentation shape remains stable across review runs.

Keep findings under their originating axis and severity. Do not collapse Blocking and Advisory findings into one bullet list, and do not replace this human-facing projection with Root Blocker status, coverage accounting, reviewer-execution metrics, or convergence/effectiveness statistics.

The compact coverage/effectiveness output required by the base procedure remains required, but it is supplemental and MUST appear after the three-axis findings projection.

Owner-overridden, scope-retired, Root Blocker, provenance, architecture-handoff, remediation, and lifecycle information remains governed by the base procedure and may follow the three-axis findings as applicable.

## Preserve the Adversarial Boundary

`$review-spec` remains downstream of a passing independently certified `$verify-spec` result.

Do not:

* verify ordinary ticket closure here;
* rerun `$verify-ticket-closure` or `$verify-spec-closure` merely to confirm a review finding;
* repair upstream verifier policy during the review;
* weaken a current finding because an earlier verifier reported PASS.

Prior ticket/Spec certification is historical evidence. A current reviewer finding is evaluated from its own axis authority under the base procedure.

## Upstream Certification Provenance

After a Blocking finding has been frozen and axis-provenance validated, determine whether it contradicts a prior semantic certification.

For each such finding, recover only the bounded provenance needed to answer:

```text
Review finding
    ↓
Spec contract cell(s), when applicable
    ↓
originating Implementation Ticket(s), when recoverable
    ↓
latest ticket closure certification(s), when present
    ↓
exact Spec Verification Receipt / $verify-spec-closure certification reviewed
```

Use durable sources in this order where available:

1. the immutable review checkpoint / Spec Contract Manifest;
2. parent Spec `Ticket Coverage Manifest`;
3. ticket `Spec obligations` fields;
4. durable `implement-ticket` closure checkpoint/verdict;
5. exact Spec Verification Receipt reviewed.

Do not infer ticket provenance from filenames, commit authorship, or remembered implementation history when durable mapping exists.

### Compact provenance record

For a frozen finding, preserve a concise record:

```text
Upstream certification:
- Spec cells: <IDs | None>
- Originating tickets: <#IDs | Unknown/legacy mapping unavailable>
- Ticket certification: <TICKET CLOSURE PASS reference(s) | legacy self-certified closure | unavailable>
- Spec certification: <exact verified HEAD / receipt identity>
- Contradiction: <what earlier certified claim this finding falsifies>
```

This is process provenance, not a new review axis and not a reason to reject a valid finding.

For legacy tickets created before `Spec obligations` / Ticket Coverage Manifest existed, record `legacy mapping unavailable` rather than reconstructing uncertain lineage.

## Persistence Compatibility

Do not change deterministic review utility schemas solely for this provenance field unless the utility already supports it.

When the pending/exit renderer has no dedicated field, fold the compact upstream-certification record into the finding's existing evidence/provenance text without changing its semantic classification or inventing a parallel persistence format.

The review parent may perform this bounded provenance recovery after findings are frozen because it is root/process reconciliation, not semantic re-review of assigned cells.

## Postmortem Signal

A finding that disproves a valid independent ticket or Spec certification is evidence about the upstream certification process.

Preserve that fact, but do not mutate workflow skills during the active review. Workflow hardening remains a separate authorized repository change.

This provenance exists so later postmortems can trace:

```text
Spec obligation
→ ticket decomposition
→ ticket certification
→ Spec certification
→ review contradiction
```

without relying on conversational memory.
