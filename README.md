# hud-commands

Claude Code session bookends: two skills that start and end every working
session so any machine (or person) can pick up exactly where the last session
left off — plus a readable, secret-scrubbed transcript of every session.

- **`/hud-catchup`** — run FIRST each session: reads the project's handoff
  notes, checks whether the previous session ended without a handoff (and says
  so instead of confidently reporting stale news), summarizes where things
  stand, and asks what to work on.
- **`/hud-handoff`** — run LAST each session: exports the session transcript
  with a script, updates the handoff notes, commits + pushes.
- **`/hud-update`** — run any time: pulls this repo and reinstalls.

## The design rule

**The model never writes the transcript, and transcripts never go in git.**

Claude Code already writes every session to disk verbatim (JSONL). The handoff
runs a Python script that *converts* that record to markdown — asking a model
to "write out the chat log" produces a reconstruction, not a record, and
reliably leaks secrets. The export is scrubbed twice (exact values from your
env files, then pattern rules) and then verified with an independent
[gitleaks](https://github.com/gitleaks/gitleaks) scan; if anything survives,
**nothing is written**. Logs land in `~/claude-logs/<project>/`, outside every
repo, so they can never be committed or pushed.

## Install

Prerequisites: [Claude Code](https://claude.com/claude-code), git, Python 3,
and gitleaks (`winget install gitleaks` / `brew install gitleaks`).

```bash
git clone https://github.com/stocker8/hud-commands
cd hud-commands
./install.sh          # Mac, or Windows Git Bash
```

Windows without git: **Code → Download ZIP**, extract, double-click
`install.bat`.

Skills install to `~/.claude/skills/` and work in every project on the
machine. Restart Claude Code afterwards.

**Per-repo (optional but recommended):** add a gitleaks pre-commit hook that
blocks any commit containing a secret:

```bash
python tools/install.py --repo /path/to/your/repo
```

Git hooks aren't shared or versioned, so run that once per repo you commit
from. Existing hooks are backed up, never destroyed.

## After a Claude Code update

The session-record format Claude Code writes is undocumented and can change
between versions. If `/hud-handoff` ever reports zero turns or a schema error:

```bash
python tools/probe_jsonl.py
```

It prints a PASS/MISMATCH verdict (structure only, no message bodies — safe to
share) telling you whether the exporter still matches your Claude Code version.

## Update

Type **`/hud-update`** in any Claude Code session, or manually:
`git pull && ./install.sh`. Already-open sessions keep the old version; new
sessions get the update.

Full guide: [SESSION-COMMANDS.md](SESSION-COMMANDS.md)
