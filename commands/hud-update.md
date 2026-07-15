---
description: Update the hud session commands (/hud-catchup, /hud-handoff, /hud-update) — pull the latest from the public hud-commands repo and reinstall.
---
Update the hud session commands to the latest version. This only touches the skills in `~/.claude/skills/` and this command file in `~/.claude/commands/` — it does not affect the current project.

The public source repo is: **https://github.com/stocker8/hud-commands** (no login needed to clone or pull).

1. **Find the local clone of hud-commands.** Check the likely spots in order:
   - `F:\Claude-Projects\personal\hud-commands` (Windows),
   - `~/Claude-Projects/personal/hud-commands` or `~/hud-commands` (Mac/Linux).
   If none exist, ask the user whether they cloned it somewhere else — and if they never cloned it, offer to set it up now with `git clone https://github.com/stocker8/hud-commands "<the standard spot above for this OS>"` (public repo, works without any GitHub account). If they decline, stop.

2. **Record where we are, then pull.** `git -C "<repo>" rev-parse --short HEAD`, then `git -C "<repo>" pull --ff-only`. If the pull fails, report why (no network, diverged history) in one plain line and stop — do not force anything. (A fresh clone from step 1 is already current — skip the pull.)

3. **Reinstall.** Run `bash "<repo>/install.sh"` and show its output (it reports each command as installed/up-to-date and removes superseded legacy files).

4. **Report what changed:** `git -C "<repo>" log --oneline <old-HEAD>..HEAD` — or say "already up to date" if nothing moved. If the command files themselves changed, remind the user that already-open Claude Code sessions keep the old version; new sessions get the update.
