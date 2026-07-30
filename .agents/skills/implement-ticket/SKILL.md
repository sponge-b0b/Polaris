---
name: implement-ticket
description: "Implement work based on a single ticket."
disable-model-invocation: true
---

- Implement the work in the ticket provided by the user.
- Use the identified standards source `CODING_STANDARDS.md` to guide implementation.
- Use the /tdd skill where possible, at pre-agreed seams.
- Use the /format-code skill during implementation where necessary.
- Once the work is complete, but before you close the ticket, invoke the /verify-code skill to verify the implementation of the ticket.
- Default ticket verification must be targeted. Run only targeted checks unless the user explicitly authorizes broad verification for the current task.
- Do not escalate from targeted tests to full-suite tests, whole-repo type checks, whole-repo lint checks, full coverage runs, or service-dependent integration suites without explicit user authorization, even if those commands are already approved by the shell permission system.
- Approved shell command prefixes are execution permissions only. They are not task-specific authorization to broaden scope.
- If broader verification seems useful after targeted verification, stop and ask: `I have completed targeted verification. Do you want me to run broader verification? Proposed command: ...` Do not run the proposed broad command until the user says yes.
- In the handoff, report targeted verification separately from any broad verification. State when the full suite, whole-repo mypy, whole-repo lint, or coverage were not run.
- Close the ticket once the verification is successful.
- Commit your work to the current branch using the /conventional-commits skill, and push to the remote.
