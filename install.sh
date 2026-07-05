#!/usr/bin/env bash
# Install the slash commands in commands/ into ~/.claude/commands/.
# The repo is the source of truth: installed copies are overwritten on drift.
set -euo pipefail

repo_dir="$(cd "$(dirname "$0")" && pwd)"
dest="$HOME/.claude/commands"

mkdir -p "$dest"

for src in "$repo_dir"/commands/*.md; do
  name="$(basename "$src")"
  target="$dest/$name"
  if [ -f "$target" ]; then
    if cmp -s "$src" "$target"; then
      echo "ok: $name already up to date"
      continue
    fi
    echo "drift: installed $name differed from repo — overwriting (if you hot-fixed it in ~/.claude, port that edit back to the repo)"
  fi
  cp "$src" "$target"
  echo "installed: $name -> $target"
done

# The pre-hud names are superseded; remove stale installed copies.
for legacy in catchup.md handoff.md; do
  if [ -f "$dest/$legacy" ]; then
    rm "$dest/$legacy"
    echo "removed legacy: $legacy (superseded by hud-$legacy)"
  fi
done
