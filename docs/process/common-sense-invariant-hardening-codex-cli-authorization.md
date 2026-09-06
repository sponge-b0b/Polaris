# Codex CLI Authorization Boundary

This addendum is mandatory ChatGPT-hosted Polaris process-hardening context under `docs/process/session-reconstitution.md`.

## Invariant

ChatGPT must **never invoke, embed, or instruct execution of `codex`, `codex exec`, or any equivalent command that launches the user's Codex CLI unless the repository owner has explicitly authorized that Codex CLI invocation in the current conversation**.

The user's Codex CLI quota, credits, and tokens are owner-controlled resources. ChatGPT does not have standing authority to spend them merely because a workflow could be delegated to Codex or because a local shell command is otherwise available.

In particular:

- a repository skill reference such as `$spec-contract`, `$verify-spec`, or another `$skill` is **not** authorization to launch Codex CLI;
- the owner-authorized in-session substitute-agent override in `docs/process/session-reconstitution.md` is **not** authorization to launch Codex CLI;
- inability to spawn a fresh/independent agent is **not** authorization to launch Codex CLI;
- a connector or local-tool limitation is **not** authorization to launch Codex CLI;
- do not hide a Codex CLI invocation inside a larger Bash block, helper script, subshell, or generated command sequence.

When a workflow step can be completed in the active ChatGPT runtime, through connected tooling, or through ordinary non-Codex local commands, use those mechanisms instead.

If a required step genuinely cannot be completed without invoking Codex CLI, stop before constructing an executable Codex command and ask the owner for explicit authorization. State what Codex would be used for and why the available ChatGPT/connectors/local non-Codex mechanisms are insufficient.

Authorization is specific to the requested invocation and does not create standing permission for later Codex CLI use unless the owner explicitly says otherwise.

## Failure Rule

An accidental or unauthorized Codex CLI invocation is a process defect. Do not repeat it, retry it, or consume additional Codex quota while attempting recovery. Preserve any successful work completed before the invocation, determine whether the Codex attempt mutated state, and continue through non-Codex mechanisms where possible.
