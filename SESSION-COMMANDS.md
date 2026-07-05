# /hud-catchup and /hud-handoff — sharing, using, and what they do NOT do

These are custom Claude Code slash commands that bookend a working session so any
machine (or person) can pick up where the last session left off. This guide covers how to
install them elsewhere, how to run sessions properly, and — most importantly — the gaps
they do **not** cover, so you never *think* something is backed up when it isn't.

The commands are distributed from a public repo — **https://github.com/stocker8/hud-commands**
— so any machine with git can install them (`git clone` + `./install.sh`) and update them
(`/hud-update` inside Claude Code). No GitHub account is needed to install or update.

---

## What each command does

**`/hud-catchup`** — run it as the FIRST thing in a session:
1. Detects a crashed/unfinished previous session: a dirty working tree at start means the
   last session never handed off — it says so loudly and lists what's uncommitted.
2. If the repo has a git remote, fetches and compares: **behind** → `git pull --ff-only`
   (never force, never overwrites local work); **ahead** → the last push failed, so it
   pushes the already-committed work now to bank it. Then **verifies push access** with a
   harmless `git push --dry-run` — broken GitHub auth is caught at the start of the
   session, not at handoff time. If there's **no remote** or **no repo at all**, it says
   so out loud — a project that isn't backed up can never masquerade as one that is.
3. Reads `docs/STATUS.md` (falls back to newest `docs/HANDOFF-*.md`, then `README.md`,
   then `git log`) — and warns if STATUS.md looks older than the latest commits.
4. Summarizes where the project stands, how long since the last activity, the branch if
   it isn't main, and what's open.
5. Asks what you want to work on, and waits. It changes nothing (pushing already-committed
   work in step 2 is backup, not change).

**`/hud-handoff`** — run it as the LAST thing in a session:
1. If the folder isn't a git repo yet, it **`git init`s it** and writes a sensible
   `.gitignore` first (so a brand-new project still gets a proper handoff).
2. Rewrites `docs/STATUS.md` to the current state — headed with the date, which machine,
   and the branch (creates it if missing).
3. Creates or maintains a lean **`CLAUDE.md`** — the file Claude Code auto-loads every
   session: what the project is, how to run it, and a pointer to read `docs/STATUS.md`.
   It only touches this file when something durable changed.
4. Archives the **verbatim** session transcript: finds this session's JSONL under
   `~/.claude/projects/`, gzips it into `docs/log/transcript-<date>-<session-id>.jsonl.gz`,
   and integrity-checks the archive.
5. Safety-checks before committing: `.env`/credential files must be gitignored,
   secret-looking strings stop the commit, and files over 50MB get warned about instead
   of committed. Then `git add -A`, commits with a session summary, pushes if a remote
   exists, and **verifies the push landed** — a failed push is reported in bold, first
   thing. If there's **no remote**, it warns you and offers to create a private GitHub
   repo on the spot (`gh repo create`).
6. Prints the line to paste when you resume (`/hud-catchup`, or "read docs/STATUS.md and
   catch up" on a machine without the commands installed) — including the branch to check
   out if the session ended off main, plus the clone command if the repo was just pushed
   for the first time.

**`/hud-update`** — run it any time, in any project:
Finds your clone of the hud-commands repo (offers to create one if missing — it's public,
no login needed), pulls the latest, reinstalls the commands, and reports what changed.

---

## Installing / sharing the commands

The commands are just markdown files. Claude Code loads any `.md` file in the
**user-level commands folder** as a slash command, on every project on that machine:

| Machine | Folder |
|---|---|
| Windows | `C:\Users\<name>\.claude\commands\` |
| Mac / Linux | `~/.claude/commands/` |

**With git (preferred — gets you `/hud-update`):**
```bash
git clone https://github.com/stocker8/hud-commands
cd hud-commands
./install.sh
```

**Without git:** on the repo page, **Code → Download ZIP**, extract, then double-click
`install.bat` (Windows) or run `bash install.sh` (Mac).

Either way the installer copies the three `hud-*.md` files into the folder above and
removes the old pre-hud `catchup.md`/`handoff.md` if present. Restart Claude Code (or
start a new session) and `/hud-catchup`, `/hud-handoff`, `/hud-update` appear when you
type `/`. The files contain nothing personal or machine-specific, so sharing the repo
link is all it takes to set someone else up.

**Alternative — per-project commands:** putting the files in a repo's `.claude/commands/`
folder makes them available only inside that project, but they then travel with
`git push`/`git pull` automatically. User-level (`~/.claude/commands/`) is what we use,
because it works in every project.

---

## Scenarios — the exact steps

### A. Brand-new project (empty folder, nothing in it)
1. Create the folder (e.g. `F:\Claude-Projects\personal\myidea`) and start Claude Code in it.
2. Type `/hud-catchup`. It will report "nothing here is versioned yet" — expected. Tell it
   what you want to build and work normally.
3. When done, type `/hud-handoff`. It will: `git init` + write a `.gitignore` + write
   `docs/STATUS.md` + start a `CLAUDE.md` + archive the transcript + commit — then **ask
   if you want a private GitHub repo created. Say yes.** It pushes and prints the clone
   command for other machines.
4. Done. From now on this project behaves like any existing one (scenario B).

*(One-time per machine, ever: `gh auth login` must have been run for step 3's repo
creation to work.)*

### B. Existing project, same machine, fresh session
1. Start Claude Code in the project folder → `/hud-catchup`.
2. It pulls, reads STATUS.md, summarizes, and asks what to work on. Answer, work.
3. End with `/hud-handoff`. Glance at its report: push confirmed = fully backed up.

### C. Switching machines (Windows → Mac, or Mac → Windows)
On the machine you're LEAVING:
1. `/hud-handoff` — and confirm its report says the **push succeeded**. The push is the
   bridge; without it the other machine sees nothing new.

On the machine you're ARRIVING at (already set up):
2. Start Claude Code in the project folder → `/hud-catchup` (it pulls automatically —
   and if the other machine's push had failed, it tells you the moment it can) → work
   → `/hud-handoff`.

First time EVER on that machine, do this once before step 2:
- Install Claude Code + git, and run `gh auth login` (or otherwise sign in to GitHub —
  needed for YOUR private project repos, not for the commands themselves).
- Install the commands: `git clone https://github.com/stocker8/hud-commands && cd
  hud-commands && ./install.sh`
- `git clone <project repo URL>` into the same layout (e.g. `~/Claude-Projects/personal/myidea`).
- (No commands installed yet? The manual equivalent of `/hud-catchup` is telling Claude:
  "read docs/STATUS.md and catch up".)

### D. You quit last time WITHOUT running /hud-handoff (or the session crashed)
Nothing is lost — it's just not committed/pushed yet. `/hud-catchup` will now DETECT this
(dirty working tree) and tell you first thing.
1. Start Claude Code in the project → type `/hud-handoff` FIRST. It commits everything
   still sitting in the working tree and archives the newest transcript. (The crashed
   session's transcript is still on disk; if you want that specific one archived, say so —
   e.g. "also archive the previous session's transcript".)
2. Then `/hud-catchup` and work as normal. Rule of thumb: **uncommitted work gets banked
   before new work starts.**

### E. Quick question / read-only session (you changed nothing)
`/hud-handoff` is optional. If nothing changed, there's nothing to back up — you can just
quit. Run it anyway if you want the conversation transcript preserved in `docs/log/`
(e.g. the session contained decisions or research worth keeping).

### F. Setting someone else up from scratch (new person, new machine)
1. Send them the repo link: https://github.com/stocker8/hud-commands — they clone +
   `./install.sh` (or Download ZIP + run the installer), restart Claude Code.
2. One-time on their machine: install git, set their identity (`git config --global
   user.name` / `user.email`), and `gh auth login` with THEIR GitHub account.
3. They start any project with `/hud-catchup` and end with `/hud-handoff` — their projects
   push to their own GitHub. (If you ever share one project repo, they need to be added
   as a collaborator on github.com first.)
4. Updates, forever after: they type `/hud-update`.

---

## What still needs a human (the honest gap list)

- **Saying yes to the remote.** `/hud-handoff` offers to create the GitHub repo but won't
  do it without your OK. Until a remote exists, every commit is local-only. Check any
  project with `git remote -v`.
- **`gh auth login` / git credentials** must be set up once per machine. `/hud-handoff`
  can't log in to GitHub for you.
- **A failed push still needs your eyes.** `/hud-handoff` verifies the push and reports a
  failure in bold — and `/hud-catchup` will also catch it (and repair it) at the START
  of the next session on that machine. But between those two moments, the work lives on
  one machine only.
- **Claude's memory does not sync.** Anything saved to Claude's per-machine auto-memory
  stays on that machine. That's exactly why `/hud-handoff` writes everything into the
  repo — `docs/STATUS.md` is the source of truth, not Claude's memory.
- **The transcript copy is near-verbatim, not perfect.** `/hud-handoff` copies the session
  log *while the session is still running*, so the last few lines (the handoff itself)
  aren't in the archived copy. The work discussion always is.
- **Parallel sessions can confuse the transcript step.** It archives the *newest* session
  file for the project; with two Claude Code windows open on the same project it tries
  to match by session start time and tells you which file it picked — still, one window
  per project at handoff time is the safe habit.
- **⚠️ Transcripts capture everything said in the session.** If a password, TOTP secret,
  API key, or private message was ever pasted or displayed in the chat, it is in the
  archived transcript **in the repo**. (The pre-commit secret scan checks project files
  and diffs — it cannot un-say something inside the transcript itself.) Keep repos with
  transcripts private, don't paste secrets in sessions you don't have to, and never make
  such a repo public without scrubbing `docs/log/` first.

---

## End-of-session confidence checklist

After `/hud-handoff` says it's done, everything below should be true. Spot-check when in doubt:

1. `git status` → clean ("nothing to commit"). Anything listed = not committed = not backed up.
2. `git log --oneline -1` → the handoff commit is there with today's summary.
3. `git remote -v` shows an origin **and** the push succeeded (Claude's report says
   pushed; for certainty, check the commit on github.com).
4. `docs/STATUS.md` header date is today.
5. `docs/log/` has a `transcript-<today>-*.jsonl.gz`.
6. Any second backup layer (e.g. a nightly cloud-sync job) is personal to each machine —
   if a machine has none, the git push IS the backup there, which makes item 3
   non-optional.

The layered picture when everything is working: **repo on the machine → GitHub (private)
→ plus whatever extra backup a machine has.** STATUS.md carries the state, `docs/log/`
carries the full history of every session, and git carries both across machines.
