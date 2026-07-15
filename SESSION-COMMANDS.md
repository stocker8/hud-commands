# /hud-catchup and /hud-handoff — how to use them, and what they do NOT do

Two Claude Code skills that bookend a working session, distributed from
**https://github.com/stocker8/hud-commands** (public — no GitHub account needed
to install or update).

## The daily rhythm

```
/hud-catchup     at the start   -> shows you where you left off
...work...
/hud-handoff     at the end     -> saves the transcript, updates HANDOFF.md, commits
```

In any project. That's the whole thing.

## Where things land

```
~/claude-logs/<project>/15Jul2026_<machine>_log1.md   <- readable transcripts, OUTSIDE git
<project>/HANDOFF.md                                  <- in git, orients the next session
```

Two different jobs. `HANDOFF.md` is short, lives in the repo, and travels with
your code — it's what makes the next session (on any machine) oriented. The
transcripts are for you to read later; they never enter a session's context and
never enter git.

## How the transcript stays safe

1. Claude Code itself records every session to disk as JSONL — ground truth.
2. `/hud-handoff` runs `export_transcript.py`, which converts that record to
   markdown. The model never writes (or rewrites) the log.
3. Tool inputs/outputs are summarized to `[tool call: Read]` — file contents
   and command lines are where secrets live. Your words and Claude's replies
   are verbatim.
4. Scrubbing: exact secret values read from your env files are redacted first,
   then known key patterns (Anthropic, GitHub, AWS, Google, Slack, JWT, …).
5. gitleaks then scans the scrubbed output with its own independent ruleset.
   Any finding → the script exits non-zero and **writes nothing**.

## Multi-machine

`HANDOFF.md` moves through git: machine A's `/hud-handoff` pushes it, machine
B's `/hud-catchup` pulls and reads it. Transcripts stay on the machine that
made them; filenames carry a machine tag so they merge cleanly if you ever
sync them yourself.

## If you forget to run /hud-handoff

`/hud-catchup` compares the newest on-disk session record against the last
`HANDOFF.md` commit. A session that ended without a handoff → it says STALE and
tells you what it does and doesn't know, instead of confidently reporting old
news. It also lists commits that landed after the handoff was written — that's
how it catches the *other* machine skipping a handoff.

## What this does NOT do

- **Not a backup.** Transcripts live in one folder on one disk. Add
  `~/claude-logs` to your own backup routine.
- **No cross-machine transcript sync.** By design; see above.
- **The gitleaks pre-commit hook is per-repo.** Installing the skills does not
  protect any repo's commits until you run
  `python tools/install.py --repo <path>` for it.
- **The JSONL schema is not a public contract.** After a Claude Code update,
  if handoff misbehaves, run `python tools/probe_jsonl.py` and read its verdict.
