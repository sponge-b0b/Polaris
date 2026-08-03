# Polaris Codex Command Guard

This directory contains PATH shims used to prevent accidental broad verification
commands during ticket implementation. The guard blocks broad commands such as
`uv run pytest -q`, `uv run mypy .`, and `uv run ruff check .` unless the owner
explicitly authorizes broad verification for the current task with
`POLARIS_BROAD_VERIFY_AUTHORIZED`.

Install or refresh the integration:

```bash
scripts/install_codex_command_guard.sh
```

Uninstall and restore the previous user-local launchers:

```bash
scripts/install_codex_command_guard.sh uninstall
```

The guard is an accident-prevention layer, not a security sandbox.
