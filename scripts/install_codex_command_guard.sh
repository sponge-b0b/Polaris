#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
GUARD_BIN="$REPO_ROOT/.agents/command-guard/bin"
USER_BIN="$HOME/.local/bin"
REAL_BIN_DIR="$USER_BIN/.polaris-command-guard-real"
START_MARKER="# >>> Polaris Codex command guard >>>"
END_MARKER="# <<< Polaris Codex command guard <<<"
WRAPPER_MARKER="# Polaris Codex command guard managed launcher"
MODE="${1:-install}"

if [ "$MODE" != "install" ] && [ "$MODE" != "--uninstall" ] && [ "$MODE" != "uninstall" ]; then
  echo "Usage: $0 [install|uninstall|--uninstall]" >&2
  exit 2
fi

managed_block=$(cat <<EOF
$START_MARKER
if [ -n "\${CODEX_THREAD_ID:-}\${CODEX_CI:-}" ]; then
  POLARIS_GUARD_BIN="$GUARD_BIN"
  if [ -d "\$POLARIS_GUARD_BIN" ]; then
    case ":\$PATH:" in
      *":\$POLARIS_GUARD_BIN:"*) ;;
      *) export PATH="\$POLARIS_GUARD_BIN:\$PATH" ;;
    esac
  fi
fi
$END_MARKER
EOF
)

remove_profile_block() {
  local profile_path="$1"
  if [ ! -f "$profile_path" ] || ! grep -Fq "$START_MARKER" "$profile_path"; then
    return 0
  fi
  python3 - "$profile_path" "$START_MARKER" "$END_MARKER" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
start_marker = sys.argv[2]
end_marker = sys.argv[3]
text = path.read_text()
start = text.index(start_marker)
end = text.index(end_marker, start) + len(end_marker)
updated = text[:start].rstrip() + "\n" + text[end:].lstrip("\n")
path.write_text(updated)
PY
}

install_profile_block() {
  local profile_path="$1"
  touch "$profile_path"
  if grep -Fq "$START_MARKER" "$profile_path"; then
    python3 - "$profile_path" "$START_MARKER" "$END_MARKER" "$managed_block" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
start_marker = sys.argv[2]
end_marker = sys.argv[3]
replacement = sys.argv[4]
text = path.read_text()
start = text.index(start_marker)
end = text.index(end_marker, start) + len(end_marker)
updated = text[:start].rstrip() + "\n\n" + replacement + "\n" + text[end:].lstrip("\n")
path.write_text(updated)
PY
  else
    printf '\n%s\n' "$managed_block" >> "$profile_path"
  fi
}

install_user_bin_wrapper() {
  local executable="$1"
  local env_name="$2"
  local target="$USER_BIN/$executable"
  local real_target="$REAL_BIN_DIR/$executable"

  mkdir -p "$USER_BIN" "$REAL_BIN_DIR"

  if [ -e "$target" ] || [ -L "$target" ]; then
    if grep -Fq "$WRAPPER_MARKER" "$target" 2>/dev/null; then
      :
    elif [ ! -e "$real_target" ] && [ ! -L "$real_target" ]; then
      mv "$target" "$real_target"
    else
      echo "Refusing to overwrite existing real executable backup: $real_target" >&2
      exit 1
    fi
  elif [ ! -e "$real_target" ] && [ ! -L "$real_target" ]; then
    echo "Skipping $executable wrapper; no existing $target executable found." >&2
    return 0
  fi

  cat > "$target" <<EOF
#!/usr/bin/env bash
$WRAPPER_MARKER
set -euo pipefail
GUARD_PY="$REPO_ROOT/tools/agent_command_guard/guard.py"
if [ ! -f "\$GUARD_PY" ]; then
  exec "$real_target" "\$@"
fi
export $env_name="$real_target"
exec python3 "\$GUARD_PY" "$executable" "\$@"
EOF
  chmod +x "$target"
}

restore_user_bin_wrapper() {
  local executable="$1"
  local target="$USER_BIN/$executable"
  local real_target="$REAL_BIN_DIR/$executable"

  if [ ! -e "$real_target" ] && [ ! -L "$real_target" ]; then
    return 0
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    if grep -Fq "$WRAPPER_MARKER" "$target" 2>/dev/null; then
      rm "$target"
    else
      echo "Refusing to replace unmanaged executable: $target" >&2
      exit 1
    fi
  fi
  mv "$real_target" "$target"
}

if [ "$MODE" = "uninstall" ] || [ "$MODE" = "--uninstall" ]; then
  remove_profile_block "$HOME/.bashrc"
  remove_profile_block "$HOME/.profile"
  restore_user_bin_wrapper uv
  restore_user_bin_wrapper mypy
  restore_user_bin_wrapper ruff
  restore_user_bin_wrapper pytest
  echo "Uninstalled Polaris Codex command guard integration."
  exit 0
fi

if [ ! -d "$GUARD_BIN" ]; then
  echo "Missing guard shim directory: $GUARD_BIN" >&2
  exit 1
fi

for executable in uv pytest mypy ruff; do
  if [ ! -x "$GUARD_BIN/$executable" ]; then
    echo "Missing executable guard shim: $GUARD_BIN/$executable" >&2
    exit 1
  fi
done

install_profile_block "$HOME/.bashrc"
install_profile_block "$HOME/.profile"
install_user_bin_wrapper uv POLARIS_REAL_UV
install_user_bin_wrapper mypy POLARIS_REAL_MYPY
install_user_bin_wrapper ruff POLARIS_REAL_RUFF
if [ -e "$USER_BIN/pytest" ] || [ -L "$USER_BIN/pytest" ]; then
  install_user_bin_wrapper pytest POLARIS_REAL_PYTEST
fi

echo "Installed Polaris Codex command guard integration."
echo "PATH shim directory: $GUARD_BIN"
echo "User launcher directory: $USER_BIN"
echo "Real executable backups: $REAL_BIN_DIR"
CODEX_CI=1 PATH="$GUARD_BIN:$PATH" command -v uv
