# hud-commands

Three Claude Code slash commands that bookend every working session so any machine
(or person) can pick up exactly where the last session left off:

- **`/hud-catchup`** — run FIRST each session: detects a crashed previous session,
  pulls the latest (and rescues commits whose push failed), verifies GitHub push
  access, reads the project's `docs/STATUS.md`, summarizes where things stand, and
  asks what to work on.
- **`/hud-handoff`** — run LAST each session: rewrites `docs/STATUS.md`, maintains a
  lean `CLAUDE.md`, archives the verbatim session transcript into the repo,
  safety-checks for secrets/oversized files, commits + pushes with verification —
  and sets up git/GitHub for brand-new projects along the way.
- **`/hud-update`** — run any time: pulls this repo and reinstalls the commands.

Full guide (scenarios, gaps, checklist): [SESSION-COMMANDS.md](SESSION-COMMANDS.md)

## Install

**With git** (Mac, or Windows via Git Bash — comes with [git](https://git-scm.com)):

```bash
git clone https://github.com/stocker8/hud-commands
cd hud-commands
./install.sh
```

**Without git:** click **Code → Download ZIP** on this page, extract it, then
double-click `install.bat` (Windows) or run `bash install.sh` (Mac).

Restart Claude Code; typing `/` now shows the three commands. They install to
`~/.claude/commands/`, so they work in every project on the machine.

Prerequisites for full use: [Claude Code](https://claude.com/claude-code), git, and —
so `/hud-handoff` can create private backup repos for your projects — the
[GitHub CLI](https://cli.github.com) logged in once (`gh auth login`).

## Update

Type **`/hud-update`** in any Claude Code session. (Manual: `git pull && ./install.sh`
in this folder. Downloaded as ZIP instead of cloning? Re-download and reinstall, or
let `/hud-update` clone the repo for you so future updates are automatic.)

## What's here

- `commands/` — the three command files (markdown instructions Claude Code loads)
- `install.sh` / `install.bat` — copy them into `~/.claude/commands/`
- `SESSION-COMMANDS.md` — the full usage guide

Development happens in a private workshop repo; this repo carries released versions.
