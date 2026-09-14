from pathlib import Path

path = Path("docs/process/session-reconstitution.md")
text = path.read_text(encoding="utf-8")

progress_anchor = (
    "During a ChatGPT working session, the ChatGPT agent that reconstitutes the session owns subsequent ledger synchronization for the remainder of that active session.\n\n"
)
progress_insert = """### Progress Communication Contract

For any ChatGPT-hosted Polaris task that is still actively running after roughly two minutes, provide the repository owner a substantive progress update **at least once every two minutes** until the task reaches a terminal result or a genuine workflow-required blocker. More frequent updates are preferred whenever meaningful progress, a material finding, a failed gate, a repair, or a stage transition occurs.

Progress updates should say what stage is active, what has completed, what materially changed, and what comes next. Do not replace useful progress with low-level polling noise or repeated \"still waiting\" messages when nothing has changed.

A progress update is **not a stopping point**. Do not stop an otherwise executable workflow merely to report that more work remains. Continue the active task through its required finalization, persistence/readback, cleanup, and Session Ledger synchronization unless the governing workflow itself requires a human decision or another genuine blocker prevents continuation.

If the conversation or connection is interrupted, resume from the latest durable completed stage rather than restarting successful work or rediscovering already-proven transport mechanics.

"""
if "### Progress Communication Contract\n" not in text:
    if progress_anchor not in text:
        raise SystemExit("progress anchor missing")
    text = text.replace(progress_anchor, progress_anchor + progress_insert, 1)

run_anchor = """#### Run reproducible repository commands

Use GitHub Actions when the required command can be reproduced from the exact durable candidate/ref. Bind the candidate first, execute the complete owning-skill semantics rather than a convenient subset, inspect the run/jobs/logs, and treat the result as verification evidence unless the workflow explicitly promotes generated repository content. Use an already-registered/proven Actions path or the current capability playbook; do not assume a newly introduced scratch-only workflow will schedule.

#### Run genuinely owner-machine-only commands
"""
fresh_insert = """#### Run reproducible repository commands

Use GitHub Actions when the required command can be reproduced from the exact durable candidate/ref. Bind the candidate first, execute the complete owning-skill semantics rather than a convenient subset, inspect the run/jobs/logs, and treat the result as verification evidence unless the workflow explicitly promotes generated repository content. Use an already-registered/proven Actions path or the current capability playbook; do not assume a newly introduced scratch-only workflow will schedule.

#### Run a genuinely fresh or independent model pass

When a Polaris workflow requires a genuinely fresh or independent model context and the active ChatGPT runtime does not expose a native fresh-agent primitive, use the **proven GitHub Actions + GitHub Copilot CLI transport** before falling back to the reduced-independence in-session substitute authorized later in this document.

For `$verify-spec`, this is the registered ChatGPT-side execution substrate for the fresh `$spec-contract` builder and independent `$verify-spec-closure` certifier. It does **not** change either skill's semantics or add a Polaris lifecycle stage; it only supplies the separate model context those skills require.

Use these already-proven mechanics without rediscovery:

1. Pin the exact candidate `HEAD`, fixed baseline, current default-branch ownership point, current `AGENTS.md` blob, and the exact owning skill inputs before model execution.
2. Run the fresh model in GitHub Actions through the current GitHub Copilot CLI using the repository's available/default Copilot model. Do not guess or pin an unavailable model merely because another environment exposes it.
3. Provide Markdown/JSON/text authority to Copilot through the prompt/stdin stream. **Do not use Copilot CLI `--attachment` for Markdown or JSON**; that transport rejects those file types before inference.
4. For the fresh `$spec-contract` builder, supply only the current authoritative inputs allowed by `$spec-contract`. Do not supply historical contract manifests, prior contract hashes, prior mappings/classifications, prior receipt conclusions, or parent-authored semantic answers.
5. For a non-mutating delegated role, deny repository writes and unnecessary tools/network access to the semantic model. The surrounding deterministic Actions job may read the exact repository/tracker inputs, validate output structure and hashes, and upload ephemeral artifacts required by the owning skill.
6. Bind every returned artifact to the exact candidate and deterministic digest required by the owning skill before consuming it. A failed pre-inference transport attempt is not a semantic result and must never be laundered into PASS/FAIL evidence.
7. Temporary workflows/branches are execution transport only. They must not mutate the verified candidate. Remove temporary workflow files and delete temporary execution branches immediately after the canonical result is persisted/read back. If the connector lacks ref deletion, a narrowly scoped temporary Actions cleanup job may delete its own temporary branch after terminal evidence is durable.
8. Do not repeat transport experimentation that has already been disproven. In particular, do not retry Markdown/JSON attachments, cycle through guessed model names, or redesign receipt/finalizer mechanics. If the registered transport is genuinely unavailable, perform one targeted capability check under the Non-Discovery Rule, then use the next authorized fallback.

For a normal ChatGPT-hosted `$verify-spec`, the operational target is **roughly 5–10 minutes under normal GitHub queue and Copilot availability**. This is a performance target, not a correctness timeout: never weaken verification to meet it. A run exceeding that range should be exceptional because of real test duration, queueing, provider outage, or a newly surfaced correctness issue—not because ChatGPT is rediscovering its own execution transport. Report the reason promptly under the Progress Communication Contract while continuing the workflow when safe.

Fresh-context execution precedence is:

```text
native fresh/independent agent primitive when available
    -> proven GitHub Actions + Copilot CLI transport
    -> owner-authorized reduced-independence in-session substitute only when no fresh substrate is available
```

The successful transport does not authorize Codex CLI. The separate Codex CLI authorization rule later in this document remains unchanged.

#### Run genuinely owner-machine-only commands
"""
if "#### Run a genuinely fresh or independent model pass\n" not in text:
    if run_anchor not in text:
        raise SystemExit("fresh-model anchor missing")
    text = text.replace(run_anchor, fresh_insert, 1)

override_anchor = (
    "For every ChatGPT-hosted Polaris working session reconstituted through this document, the repository owner grants the following temporary owner-level workflow override. Reading this section is sufficient owner authorization for that session; no separate per-session restatement is required unless the owner explicitly revokes or changes it.\n\n"
)
override_note = (
    "Before using the reduced-independence substitute below, apply the **Run a genuinely fresh or independent model pass** playbook above. When its GitHub Actions + Copilot CLI substrate is available, use that genuinely separate model context instead of treating the lack of a native ChatGPT sub-agent primitive as sufficient reason to reduce independence.\n\n"
)
if override_note not in text:
    if override_anchor not in text:
        raise SystemExit("override anchor missing")
    text = text.replace(override_anchor, override_anchor + override_note, 1)

path.write_text(text, encoding="utf-8")
