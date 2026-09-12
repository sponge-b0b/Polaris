#!/usr/bin/env bash
set -euo pipefail

REPO="sponge-b0b/Polaris"
SPEC=279
REVIEW=310
SPEC_BRANCH="spec-279"
EXPECTED_HEAD="9cae0a1c6bbd5cddd93cfc368ff17b55d418e1b3"
EXPECTED_BASELINE="4daed9034891600597a47c01b6c39d5ebd9914ca"
TITLE="Allow External Resolution for unresolved contested Decisions"

version="$(gh --version | awk 'NR==1 {print $3}')"
if [ "$(printf '%s\n%s\n' "2.94.0" "$version" | sort -V | head -n1)" != "2.94.0" ]; then
  echo "ERROR: gh >= 2.94.0 required; found $version" >&2
  exit 1
fi

# Complete the reusable-branch portion of the Spec Branch Guard in this execution substrate.
git fetch origin "$SPEC_BRANCH"
git checkout -B "$SPEC_BRANCH" "origin/$SPEC_BRANCH"
git branch --set-upstream-to="origin/$SPEC_BRANCH" "$SPEC_BRANCH"
test "$(git branch --show-current)" = "$SPEC_BRANCH"
test "$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}')" = "origin/$SPEC_BRANCH"
test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD"
test -z "$(git status --porcelain)"

gh issue develop --list "$SPEC" | grep -Fq "$SPEC_BRANCH"

metadata="$(gh issue view "$SPEC" --repo "$REPO" --json comments --jq '.comments[].body')"
grep -Fq "## Workspace Metadata" <<<"$metadata"
grep -Fq "**Baseline Commit Hash:** $EXPECTED_BASELINE" <<<"$metadata"
grep -Fq "**Branch:** $SPEC_BRANCH" <<<"$metadata"

test "$(gh issue view "$SPEC" --repo "$REPO" --json state --jq .state)" = "OPEN"
test "$(gh issue view 278 --repo "$REPO" --json state --jq .state)" = "CLOSED"
test "$(gh issue view 303 --repo "$REPO" --json state --jq .state)" = "CLOSED"

review_body="$(gh issue view "$REVIEW" --repo "$REPO" --json body --jq .body)"
test "$(gh issue view "$REVIEW" --repo "$REPO" --json state --jq .state)" = "OPEN"
test "$(grep -c '^### RB-' <<<"$review_body")" -eq 1
test "$(grep -c '| open |' <<<"$review_body")" -eq 1
grep -Fq "### RB-1 — External Resolution admission must remain independent of operative applicability" <<<"$review_body"
grep -Fq "Architecture decision required: No" <<<"$review_body"
grep -Fq 'External / unresolved / `CONTESTED`' <<<"$review_body"

body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT
cat >"$body_file" <<'BODY'
## Parent

Remediation parent: Spec Review #310
Parent Spec: #279

## Spec obligations

US-21, ID-15, ID-16

## Root blocker

RB-1 — External Resolution admission must remain independent of operative applicability

## Architecture context

Application Use Cases and Investment Decisions lifecycle/relationship boundary, governed by Spec #279 US-21/ID-15/ID-16, `docs/proposed/application-use-cases-investment-decision-lifecycle.md` §§6 and 8, and the Decisions-domain `externally_resolve_decision` transition. All architecture and material design decisions currently required by this ticket are accepted; no known implementation-readiness blocker remains unresolved.

## What to build

Correct ordinary External Resolution admission so a determinately unresolved Decision may record attributable external elimination of its Need when relationship-derived operative applicability is `OPERATIVE`, `NON_OPERATIVE`, or `CONTESTED`.

Remove only the contested-applicability veto from the External Resolution path. Preserve the determinate-operative admission rule for Subject/Scope/resume/defer/withdraw/substantive-resolution work and preserve resolved or late-historical External Resolution routing to append-only lifecycle correction.

Do not change `ExternalResolutionBasis`, known Actor Attribution, expected-version/CAS semantics, idempotency semantics, or atomic commit/no-partial-facts behavior.

## Acceptance criteria

- [ ] Ordinary External Resolution succeeds for determinately unresolved Decisions with `OPERATIVE`, `NON_OPERATIVE`, and `CONTESTED` applicability.
- [ ] `CONTESTED` applicability alone does not raise `DecisionOperativeStatusContested` or otherwise block ordinary External Resolution.
- [ ] Already-resolved and late-historical External Resolution remains rejected from the ordinary forward path and remains correction-owned.
- [ ] Substantive resolution remains determinately-operative gated: unresolved-operative succeeds; resolved, `NON_OPERATIVE`, and `CONTESTED` retain their current rejection behavior.
- [ ] Typed External Resolution basis, known Actor Attribution, expected-version/CAS, idempotent replay/conflict, and atomic commit/no-partial-state semantics remain intact.
- [ ] The complete frozen eight-member resolution-admission matrix closes with missing 0 and unchecked 0.
- [ ] `$verify-ticket-closure` certifies the combined remediation + preservation universe and persists required closure-domain evidence.

## Verification obligations

- Re-prove exactly #303's frozen `ND-2 — Resolution command/admission` domain: `{substantive, External} × {valid unresolved-operative, resolved, non-operative, contested}`.
- Prove resolved and late-historical External Resolution still commits no ordinary mutation.
- Prove substantive-resolution admission behavior is unchanged.
- After this remediation ticket closes, fresh `$verify-spec` must certify the repaired exact `spec-279` HEAD before `$review-spec` is rerun. This is downstream Spec lifecycle work, not this ticket's closure prerequisite.

## Preservation obligations

- External / unresolved / `OPERATIVE` remains satisfied.
- External / unresolved / `NON_OPERATIVE` remains satisfied.
- External / already resolved or late historical remains correction-owned.
- Substantive / unresolved / `OPERATIVE` remains satisfied.
- Substantive / resolved remains rejected from ordinary resolution.
- Substantive / `NON_OPERATIVE` remains rejected.
- Substantive / `CONTESTED` remains rejected.

These are established behaviors that remediation must preserve, not new implementation work.

## Root-complete sweep required for closure

Reclose exactly ticket #303's Certified Closure Domain `ND-2 — Resolution command/admission` under unchanged authority. The eight-member Cartesian partition must be generated, inspected, and dispositioned 8/8/8, with violated 0, unproven 0, and unchecked 0 after remediation. Do not broaden the frozen domain.

## Blocked by

None — can start immediately.

## Ticket branch

spec-279

## Ticket baseline

Pending
BODY

mapfile -t matches < <(
  gh issue list --repo "$REPO" --state open --limit 200 --json number,title,body \
    | jq -r --arg title "$TITLE" --arg marker "Remediation parent: Spec Review #310" \
      '.[] | select(.title == $title and (.body | contains($marker))) | .number'
)

if [ "${#matches[@]}" -gt 1 ]; then
  echo "ERROR: multiple active remediation tickets match the approved proposal: ${matches[*]}" >&2
  exit 1
fi

if [ "${#matches[@]}" -eq 0 ]; then
  issue_url="$(gh issue create --repo "$REPO" --title "$TITLE" --body-file "$body_file" --parent "$REVIEW" --label ready-for-agent)"
  issue_number="${issue_url##*/}"
else
  issue_number="${matches[0]}"
  issue_url="https://github.com/$REPO/issues/$issue_number"
fi

current_body="$(mktemp)"
gh issue view "$issue_number" --repo "$REPO" --json body --jq .body >"$current_body"
diff -u "$body_file" "$current_body"

test "$(gh issue view "$issue_number" --repo "$REPO" --json state --jq .state)" = "OPEN"
gh issue view "$issue_number" --repo "$REPO" --json labels --jq '.labels[].name' | grep -Fxq ready-for-agent

test "$(gh issue view "$issue_number" --repo "$REPO" --json parent --jq '.parent.number')" = "$REVIEW"
gh issue view "$REVIEW" --repo "$REPO" --json subIssues --jq '.subIssues[].number' | grep -Fxq "$issue_number"

printf 'PUBLISHED_ISSUE_NUMBER=%s\n' "$issue_number"
printf 'PUBLISHED_ISSUE_URL=%s\n' "$issue_url"
printf 'SPEC_BRANCH_HEAD=%s\n' "$(git rev-parse HEAD)"
printf 'GH_VERSION=%s\n' "$version"
