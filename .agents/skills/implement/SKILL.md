---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Keep implementation scope tied to the requested product or process work. Do not
bundle unrelated agent workflow, skill, or repository-process changes with a
feature implementation unless the active ticket explicitly asks for them. If
such process changes are necessary, split them into their own governed tracker
item before continuing.

Use /tdd where possible, at pre-agreed seams.

Verify with targeted checks tied directly to the files changed, affected
boundaries, and known regression risks. Do not run the full test suite by
default; first determine whether full-suite verification is necessary for the
change scope. Prefer single relevant test files, focused type checks, and
service-free verification when the work is documentation or process guidance.
Before any integration or live-service test, identify the required services and
report optional live validation separately from required service-free checks.

<!--Once done, use /code-review to review the work.-->

Commit your work to the current branch.
