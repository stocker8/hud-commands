---
description: Session start — detect crashed sessions, pull latest, verify push access, read docs/STATUS.md, summarize where things stand, and ask what to work on.
---
You are starting a fresh working session in this project. Get fully up to speed BEFORE doing any work, and do NOT change anything yet. (One exception: pushing work that is already committed, step 2 — that is backup, not change.)

Do these in order:

1. **Detect an unclean last session.** If this is a git repo, run `git status --porcelain`. If the working tree is dirty (modified or untracked files), the last session probably ended WITHOUT a handoff — say so loudly, list in a few lines what's sitting uncommitted, and carry it into your summary in step 4. Do NOT commit, stash, or discard anything.

2. **Sync — and surface backup gaps.** Run `git remote`.
   - If there is a remote: run `git fetch`, then compare the local branch with its remote:
     - **Behind:** `git pull --ff-only` and report the result in one line. Never force, reset, or overwrite local changes; if the pull fails because histories diverged, stop and tell the user instead of resolving it yourself.
     - **Ahead:** the last handoff's push FAILED — this committed work exists on this machine only. Run `git push` now to bank it, and report that you did.
     - Then confirm push access works NOW (not at handoff time) with `git push --dry-run` — nothing is actually pushed. One line: "push access OK" or, if it fails for auth/permission reasons, a loud warning that pushes are broken on this machine and what to fix (usually `gh auth login` or stored credentials). An error only about "no upstream branch" is not an auth failure — just note it.
   - If this is a git repo with NO remote: say in one line that this project is not backed up off this machine (offer to fix it at handoff time — don't set it up now).
   - If this is NOT a git repo at all: say in one line that nothing here is versioned or backed up, and note that `/hud-handoff` will set up git at session end.

3. **Read the current state.** Read `docs/STATUS.md` if it exists. If it doesn't, fall back — in this order — to the newest `docs/HANDOFF-*.md`, then `README.md`, then a quick `git log --oneline -15`. If commits exist that are NEWER than STATUS.md's own date line (compare against `git log -1 --format=%cs`), warn that STATUS.md may be stale and lean on the recent `git log` for what actually happened.

4. **Summarize** in a few tight lines: what this project is, what's currently live / in progress, and the listed next steps / open items — plus how long since the last activity (latest commit date) and, if it isn't main/master, the current branch. Name the file you read so the user knows the source.

5. **Ask the user what they want to work on this session,** and wait for their answer before taking any action.

This is orientation, not an audit — keep it brief.
