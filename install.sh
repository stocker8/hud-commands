#!/usr/bin/env bash
# Install the hud session skills (/hud-catchup, /hud-handoff) plus /hud-update.
# Thin wrapper: the real installer is tools/install.py (Python 3 stdlib, works
# on Windows and macOS). Skills go to ~/.claude/skills/ and work in every
# project. Run again with --repo <path> to add the gitleaks pre-commit hook
# to a specific repo.
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  py=python3
elif command -v python >/dev/null 2>&1; then
  py=python
else
  echo "ERROR: Python 3 not found. Install it and re-run." >&2
  exit 1
fi

"$py" "$repo_dir/tools/install.py" "$@"

# /hud-update is a plain command, not a skill; install it alongside.
mkdir -p "$HOME/.claude/commands"
cp "$repo_dir/commands/hud-update.md" "$HOME/.claude/commands/hud-update.md"
echo "  Installed: ~/.claude/commands/hud-update.md"
