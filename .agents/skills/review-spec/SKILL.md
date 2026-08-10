---
name: review-spec
description: Review the changes of the provided spec since a fixed point (commit, branch, tag, or merge-base) along three independent axes — Standards, Spec, and Architecture — then aggregate the findings and close the review loop.
compatibility: product=codex product=claude-code system=git system=python system=gh network=required
disable-model-invocation: true
---

Three-axis review of the diff between `HEAD` and a fixed point:

* **Standards** — does the code conform to this repo's documented coding standards?
* **Spec** — does the code faithfully implement the originating issue/spec?
* **Architecture** — does the aggregate implementation conform to the resolved architecture and current architectural authorities?

All axes run as **parallel sub-agents** so they do not pollute each other's context. The review loop closes when there are zero **Blocking** findings, even if Advisory notes remain.

This is a **review-only** workflow, not a verification workflow. Do not run `pytest`, `ruff`, `mypy`, graph updates, duplication scans, `$wiki-lint`, or other static/test verification commands here. If spec-wide verification is needed, invoke `$verify-spec` separately.

The issue tracker should have been provided — run `$setup-matt-pocock-skills` if `docs/agents/issue-tracker.md` is missing.

## Finding Taxonomy

Every finding must be classified before it is counted or ticketed:

* **Blocking** — must be remediated before the review can close. Includes spec mismatches, implemented-wrong behavior, missing required acceptance tests/docs, hard documented-standard violations, and material architecture violations.
* **Advisory** — useful but non-blocking observations, including smell heuristics, maintainability concerns, and speculative cleanup.
* **Owner-overridden** — findings explicitly accepted, authorized, or rejected by the owner. Do not count or ticket them, and do not re-raise them as blockers on later passes.

Classification rules:

* Spec-axis mismatches are Blocking by default.
* Deterministic documented-standard violations are Blocking by default.
* Architecture findings are Blocking when `$review-architecture` identifies a violation of applicable architectural authority or an unresolved material architecture change introduced by the implementation.
* For Blocking Architecture findings, `Architecture decision required: Yes | No` controls routing, not severity.
* Smell-baseline findings are Advisory by default unless explicitly promoted.
* Explicitly authorized scope creep is Owner-overridden.
* Skip issues tooling should reliably catch unless tooling cannot reasonably detect the problem in this diff.

## Process

### 1. Pin the Fixed Point

The fixed point is automatically stored in the parent specification issue on GitHub unless explicitly overridden.

1. **Extract Baseline Metadata**: `$to-tickets` posts it as a comment:

   ```bash id="26zi7k"
   BASELINE_COMMIT=$(gh issue view <spec_issue_number> --json comments -q '.comments[].body' \
     | grep -oP '(?<=\*\*Baseline Commit Hash:\*\* )\S+' | tail -1)
   ```

2. **Fallback**: If missing and no explicit ref was provided, ask the user.

3. **Verify Branch Checked Out**:

   ```bash id="w3yku4"
   CURRENT_BRANCH=$(git branch --show-current)
   if [ "$CURRENT_BRANCH" != "spec-<spec_issue_number>" ]; then
     echo "❌ Expected spec-<spec_issue_number> to be checked out, but current branch is $CURRENT_BRANCH."
     exit 1
   fi
   ```

4. **Validate the Ref**:

   ```bash id="4k1lqa"
   git rev-parse <fixed-point>
   ```

   Halt if it does not resolve.

5. **Capture Diff and Log**:

   * `git diff <fixed-point>...HEAD`
   * `git log <fixed-point>..HEAD --oneline`

6. **Pre-Flight Check**: The diff must be non-empty.

### 2. Identify the Spec Source

Look for the originating spec, in order:

1. Issue references in commit messages.
2. A path passed by the user.
3. A matching spec under `docs/`, `specs/`, or `.scratch/`.
4. If none is found, ask the user. If no spec exists, skip the Spec axis and report that.

Capture the spec's **Architecture Impact** when present.

### 3. Identify Review Sources

For **Standards**, use `$coding-standards` and applicable repository guidance such as `CONTRIBUTING.md`.

For **Architecture**, use `$review-architecture` as the owner of the architecture audit procedure. Provide it the full aggregate diff, commit list, spec Architecture Impact, and affected architectural context. Do not duplicate its rules here.

### 4. Spawn All Review Sub-Agents in Parallel

Send one message containing the parallel sub-agent calls.

**Main-agent orchestration boundary:** after spawning, do not independently perform any of the three reviews. Do not inspect additional hunks, run verification commands, or search for new findings while they run.

**Standards sub-agent prompt** — include:

* full diff command and commit list;
* standards sources and smell baseline;
* Finding Taxonomy;
* brief: identify documented-standard violations and relevant baseline smells, labeling each Blocking or Advisory. Skip tooling-enforced issues. Under 400 words. If clean, say `No findings.`

**Spec sub-agent prompt** — include:

* full diff command and commit list;
* spec contents;
* Finding Taxonomy;
* brief: identify missing/partial requirements, unauthorized behavior, and apparently incorrect implementations. Cite the spec requirement. Label findings Blocking, Advisory, or Owner-overridden. Under 400 words. If clean, say `No findings.`

If the spec is missing, skip this sub-agent.

**Architecture sub-agent prompt** — include:

* full diff command and commit list;
* spec Architecture Impact;
* affected entities and governing ADR/doc references when available;
* Finding Taxonomy;
* instruction to invoke `$review-architecture` and return only its review findings, preserving `Architecture decision required: Yes | No` and routing for every Blocking finding. Under 400 words. If clean, say `No findings.`

### 5. Aggregate

Lightly validate cited findings before reporting them. Validation is limited to confirming cited evidence; it is not permission for a fresh review.

* Confirm Blocking Standards findings cite a deterministic documented rule.
* Confirm Spec scope-creep findings were not owner-authorized.
* Confirm Architecture findings are supported by `$review-architecture` evidence and current architectural authority.
* Confirm every Blocking Architecture finding includes `Architecture decision required: Yes | No`.
* Confirm Owner-overridden findings are not counted or ticketed.
* Inspect only evidence necessary to validate an existing finding.
* Do not run tests, static checks, graph updates, `$wiki-lint`, or duplication scans.
* Keep all three axes independent.

Present:

```text id="36fhgs"
## Standards

## Spec

## Architecture
```

Within each axis, use `### Blocking` and `### Advisory` when both exist.

End with one line counting Blocking and Advisory findings separately for each axis and naming the worst Blocking issue in each, if any.

If one or more Blocking Architecture findings have `Architecture decision required: Yes`, do not send those findings into `$review-spec-remediation` or `$to-tickets`. Halt with the Architecture Human Handoff Intercept below.

Otherwise, if any Blocking findings remain, invoke `$review-spec-remediation`; do not synthesize root blockers or create tracking issues directly here.

### Architecture Human Handoff Intercept

Collect every independent Blocking Architecture finding with `Architecture decision required: Yes`.

De-duplicate by underlying architectural question. Multiple findings or evidence examples of the same unresolved issue produce one blocker; independent unresolved questions remain separate.

Preserve the finding context so `$architecture-remediation` does not have to rediscover it.

For each blocker include:

* concise unresolved architecture question or conflict;
* finding evidence;
* why a new architecture decision is required;
* affected entities and governing ADR/doc references already known.

Also include:

* parent Spec title and URL;
* Spec Review issue title and URL when one already exists.

Do not propose or imply an architectural resolution.

Use:

> ⚠️ **Spec review is blocked by unresolved architecture.**
>
> Please run:
>
> ```
> $architecture-remediation - <Parent Spec Title> (<Spec URL>) — <concise blocker-set summary>
> ```
>
> **Architecture blockers:**
>
> 1. **<unresolved question or conflict>**
>
>    * Evidence: <concise finding evidence>
>    * Material consequence: <ownership/path, boundary, dependency direction, lifecycle responsibility, source conflict, or other unresolved consequence>
>    * Governing context: <affected entities / ADRs / docs when known>
> 2. **<unresolved question or conflict>**
>
>    * ...
>
> **Spec Review:** <title and URL, when applicable>

Then stop. `$architecture-remediation` owns lineage recovery, blocker de-duplication against existing Wayfinder children, and Wayfinder re-entry.

Blocking Architecture findings with `Architecture decision required: No` remain review-remediation findings. Preserve them for `$review-spec-remediation` after architecture resolution; do not convert them into Wayfinder decisions.

## Why Three Axes

A change may satisfy any two while failing the third:

* Correct style, wrong behavior → **Standards pass, Spec fail**
* Correct behavior, broken conventions → **Spec pass, Standards fail**
* Correct behavior and clean code, wrong architectural ownership/boundary → **Spec and Standards pass, Architecture fail**

Keeping the axes independent prevents one form of correctness from masking another.

## Remediation Loop

Do not make in-flight file edits.

Blocking Architecture findings with `Architecture decision required: No` are ordinary remediation blockers and follow the same `$review-spec-remediation` path as Blocking Standards or Spec findings.

Blocking Architecture findings with `Architecture decision required: Yes` require the Architecture Human Handoff Intercept. All independent unresolved architecture blockers discovered in that review pass must be preserved in the handoff and resolved through the existing Wayfinder effort before review remediation can continue.

If Blocking findings remain and none require architecture resolution, invoke `$review-spec-remediation` in full.

That skill owns root-blocker synthesis, tracking, human handoff, recursive passes, and Owner Overrides.

Advisory-only findings do not trigger remediation unless the user promotes them.

Once remediation completes, return to the Exit Gate.

## The Exit Gate

Proceed to `$spec-merge-cleanup` only when a complete review returns exactly zero **Blocking** findings across all three axes and any Root Blocker Ledger / acceptance matrix has no open or regressed root cells.

Advisory findings may remain. Owner-overridden findings remain suppressed.

Do not close the Spec issue here. `$spec-merge-cleanup` owns closure through its merge/no-branch paths.

Do not close the parent Spec Review issue here either. `$spec-merge-cleanup` owns that closure after successful completion.
