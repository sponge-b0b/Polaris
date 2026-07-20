---
name: implement-ticket
description: "Implement work based on a single ticket."
disable-model-invocation: true
---

- Implement the work in the ticket provided by the user.
- Use the /tdd skill where possible, at pre-agreed seams.
- Use the /format-ticket skill during implementation where necessary.
- Once the work is complete, but before you close the ticket, invoke the /verify-ticket skill to verify the implementation of the ticket.
- Close the ticket once the verification is successful.
- Commit your work to the current branch using the /conventional-commits skill, and push to the remote.
