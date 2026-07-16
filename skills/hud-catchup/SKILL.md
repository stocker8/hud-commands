---
name: hud-catchup
description: Start-of-session orientation. Loads HANDOFF.md, recent commits, and working tree state.
disable-model-invocation: true
allowed-tools: Bash(python3 *) Bash(python *) Bash(git status *) Bash(git log *) Bash(git diff *) Bash(git fetch *)
---

# Session catchup

Everything below was resolved before you saw it. It is current, not recalled.

## Is HANDOFF.md trustworthy?

```!
python3 "${CLAUDE_SKILL_DIR}/scripts/last_session.py" --exclude-session "${CLAUDE_SESSION_ID}" 2>&1 || \
  python "${CLAUDE_SKILL_DIR}/scripts/last_session.py" --exclude-session "${CLAUDE_SESSION_ID}" 2>&1
```

## HANDOFF.md

Read `HANDOFF.md` from the project root with the Read tool. If it does not
exist, note that plainly — do not guess at state.

## Repository state

```!
python3 "${CLAUDE_SKILL_DIR}/scripts/repo_state.py" --fetch 2>/dev/null || python "${CLAUDE_SKILL_DIR}/scripts/repo_state.py" --fetch
```

If it reports NOT A GIT REPOSITORY, say so plainly — this folder has no git
history to orient from; HANDOFF.md (if present) is the only record. For the
machine check in the instructions below, use the platform you are running on
(from your environment) — Windows PC vs Mac is the distinction that matters.

## Instructions

1. **If the verdict above is not OK, lead with that.**
   - **STALE** — a session ran on this machine after the last handoff and ended
     without one. HANDOFF.md describes an older state.
   - **PARTIAL** — commits landed after HANDOFF.md was written. The other machine
     almost certainly did work and skipped /hud-handoff. Read those commits and
     tell me what they actually changed.
   Either way, do not summarize HANDOFF.md as though it were current. Say what it
   is, then help me reconstruct the gap from `git log` and the working tree.
2. Summarize in three bullets: where we left off, what the next action is, and
   anything flagged as an open question.
3. Check the **Machine** section of HANDOFF.md against the machine above. If the
   last session ran elsewhere, say so — the next action may only be possible on
   the other machine (Xcode builds and TestFlight on the Mac, Worker deploys
   from Windows).
4. If the branch is behind origin, say so before anything else happens.
5. Call out any dead end in HANDOFF.md relevant to the next action, so it does
   not get re-walked.
6. If the working tree is dirty, say so and ask whether it is intentional.
7. If HANDOFF.md is missing, say so plainly rather than guessing at state.
8. Stop there. Do not begin work until I say so.
