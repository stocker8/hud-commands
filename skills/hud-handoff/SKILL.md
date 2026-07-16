---
name: hud-handoff
description: End-of-session handoff. Exports the session transcript via script, syncs the log repo, rewrites HANDOFF.md, then commits and pushes.
disable-model-invocation: true
allowed-tools: Bash(python3 *) Bash(python *) Bash(git add *) Bash(git commit *) Bash(git status *) Bash(git push *) Bash(git pull *) Bash(git diff *) Bash(git log *)
---

# Session handoff

## Environment

```!
python3 "${CLAUDE_SKILL_DIR}/scripts/repo_state.py" 2>/dev/null || python "${CLAUDE_SKILL_DIR}/scripts/repo_state.py"
```

If it reports NOT A GIT REPOSITORY, still export the transcript (step 1) and
rewrite HANDOFF.md (step 2), but skip the commit/push step.

## Steps

Run in order.

### 1. Export the transcript

Try `python3` first (macOS); if it is not found, use `python` (Windows):

```
python3 "${CLAUDE_SKILL_DIR}/scripts/export_transcript.py" --session-id "${CLAUDE_SESSION_ID}"
```

Report the path it printed.

Exit codes:
- `2` — JSONL schema mismatch. Run `tools/probe_jsonl.py` and report. Do not
  patch around it silently.
- `3` — `scrub()` is broken. Report and stop.
- `4` — gitleaks unavailable, log unverified. Report and stop. Do **not** pass
  `--allow-unverified` on my behalf; that is my call, not yours.
- `5` — gitleaks found a secret in the scrubbed output. Nothing was written.
  Report immediately and stop. Do not retry, do not disable the check, do not
  write the log by hand.

If the script fails for any reason, stop. Never fall back to writing the
transcript yourself.

### 2. Rewrite HANDOFF.md

Replace the file completely. Do not append. Sections:

- **State** — what works right now, verified.
- **Machine** — which machine this session ran on, and anything machine-specific
  left half-done (a build not yet run on the Mac, a Worker not yet deployed).
- **Changed this session** — what moved, and why.
- **Next** — the specific next action, concrete enough to start cold on the
  other machine.
- **Open questions** — decisions not yet made.
- **Dead ends** — approaches tried and rejected, with the reason. This section
  saves the most time later. Do not omit it.

### 3. Commit and push the project

Stage source files and HANDOFF.md. Run `git status` and show me the staged list
before committing. Then commit with a summary of the session's work and push.

## Rules

- The transcript is produced by the script, never by you. You do not have
  reliable verbatim recall of this conversation, and after auto-compaction you
  would be summarizing a summary. Reconstruction is not a transcript.
- Never write secrets, API keys, tokens, or the contents of `.dev.vars`,
  `.env`, or `wrangler.toml` into HANDOFF.md, a commit message, or any file.
  Refer to them by name only.
- Never `git add -A`, never `git add -f`, never `--no-verify`.
- If `git status` shows a file you do not recognize, ask before staging it.
