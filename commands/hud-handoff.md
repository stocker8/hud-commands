---
description: Session end / handoff — update STATUS.md, maintain CLAUDE.md, archive the verbatim transcript, safety-check then commit + push (offering git init / remote setup if missing), print the next-session line.
---
You are wrapping up this session so it can be resumed later — possibly on another machine. Preserve everything durably IN THE REPO (which travels via git and into backups), because Claude's own memory does NOT sync across machines.

Do these in order, reporting each step as you go:

Throughout: Read any existing file BEFORE editing or overwriting it (STATUS.md, CLAUDE.md, anything in docs/) — the Edit/Write tools reject changes to files not yet read this session, and blind retries have burned past handoffs.

0. **Make sure a repo exists.** Run `git rev-parse --is-inside-work-tree`. If this is NOT a git repo: tell the user plainly that nothing here is versioned yet, then `git init`, create a sensible `.gitignore` for the project type (node_modules, build output, .env*, OS junk — this matters because step 4 uses `git add -A`), and continue. Do not skip the handoff over this.

1. **Update `docs/STATUS.md`** (create `docs/` and the file if missing). This is the always-current "start here" pointer. Overwrite it to reflect the CURRENT state, starting with a header line of today's date, which machine this is (e.g. "Windows PC" / "Mac"), and the current branch. Then:
   - one line on what the project is,
   - what's live / committed,
   - what changed this session,
   - a clear **Next / open** list.
   Keep it concise — it's a pointer, not a log.

2. **Maintain `CLAUDE.md`** (project root). Claude Code auto-loads this file at the start of EVERY session, so it must hold only the stable facts — never session state (that's STATUS.md's job):
   - If it does NOT exist and the project has real content: create a SHORT one — one line on what the project is, how to run/build/test it, key file locations — ending with: "Current state and next steps live in `docs/STATUS.md` — read it before starting work."
   - If it exists: update it ONLY if something durable changed this session (new run/build command, new convention, moved files). Otherwise leave it untouched and say so.

3. **Archive the VERBATIM transcript (do NOT summarize it).** Claude Code writes this whole session to a JSONL file on disk. Copy it, lossless, into the repo:
   - Look in `~/.claude/projects/`. The folder for THIS project is named after the project's absolute path with every `/`, `\`, and `:` replaced by `-` (e.g. `F:\Claude-Projects\personal\hudmo` → `F--Claude-Projects-personal-hudmo`). If unsure, list `~/.claude/projects/` and pick the folder whose name ends with this project's folder name.
   - Inside it, the current session is the **newest top-level `*.jsonl`** (ignore the `subagents/` subfolder). If several were modified recently (parallel sessions), pick by matching the session's start time and say which you picked.
   - **Redact secrets first, in one quick pass.** Scan the session file for secret-looking values (`API_KEY=`, `-----BEGIN ... PRIVATE KEY`, token shapes like `sk-…`, `cfut_…`, `ghp_…`, `pplx-…`, long random strings the user pasted). If any are found: make a temp copy with each secret VALUE replaced by `[REDACTED]` (sed or python), archive THAT copy, tell the user which kinds of secrets were seen, and remind them a key pasted into chat should be treated as exposed and rotated. Do not spend the handoff agonizing over this — redact, note it, move on. If nothing matches, archive the original as-is.
   - Compress-copy it with `gzip -c "<that file or its redacted copy>" > "docs/log/transcript-<YYYY-MM-DD>-<session-id>.jsonl.gz"` (keep the session id from the filename; create `docs/log/` if missing), then run `gzip -t` on the archive to confirm it's intact. This keeps the complete record small enough to commit every session. (To read it later: `gunzip`, or just ask Claude to render it.)
   - If you genuinely cannot locate it, say so and continue — do NOT block the handoff.

4. **Safety-check, then commit + push — and verify, loudly.**
   - Before staging, three quick checks on what `git add -A` is about to pick up (`git status --porcelain`):
     - `.env*` or other credential-looking files present but not gitignored → add them to `.gitignore` first and tell the user.
     - Secret-looking content in the about-to-be-committed changes (`API_KEY=`, `-----BEGIN ... PRIVATE KEY`, long random tokens) → STOP and flag it instead of committing. (The transcript archive was already redacted in step 3 — if a secret still shows there, redo that redaction rather than blocking the whole handoff.)
     - Any file over 50MB → warn and gitignore it rather than committing blindly (GitHub hard-rejects files over 100MB, and the push would fail after the fact).
   - `git add -A`, commit with a message summarizing the session.
   - If a remote exists: `git push`, then confirm it actually succeeded (push output + `git status` shows the branch is up to date with the remote). If the push FAILS (auth, network), say so in bold as the very first line of your wrap-up — the user must know this session lives on this machine only until they fix it — and state what to fix.
   - If NO remote exists: do NOT stay silent. Warn that this project exists on this machine only, and ask the user if they want a private GitHub repo created now (`gh repo create <name> --private --source=. --push`; requires `gh auth login` once per machine). If they decline or `gh` isn't available, remind them the commit is local-only.

5. **Print the exact next-session starter** for the user to paste when they resume (here or on the other machine):
   > `/hud-catchup`  — or, if commands aren't installed there yet: `read docs/STATUS.md and catch up`
   If this handoff happened on a branch other than main/master, include `git checkout <branch>` in the starter so the next session lands on the right branch. If this was a brand-new repo pushed for the first time, also print the one-time clone command for the other machine.

Work cross-platform (Mac + Windows): use `git`, `gzip`, and portable shell only — no PowerShell-only or Windows-only paths in what you run.
