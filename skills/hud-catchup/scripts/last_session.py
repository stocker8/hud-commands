#!/usr/bin/env python3
"""
Did a session run after the last /hud-handoff?

Claude Code writes each session to disk live, as it happens. So a session that
ended without a handoff still left a file behind, even though it left no
transcript and no commit. That file is the evidence.

Compares:
  A) when HANDOFF.md was last committed
  B) the newest session file for this project, excluding the current one

If B is newer, work happened that HANDOFF.md does not describe. Local only —
no sync, no network, no transcript reading.

Python 3.8+, standard library only.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def git(args: list[str], cwd: Path) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                           text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def ago(dt: datetime) -> str:
    secs = int((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds())
    if secs < 0:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"


def session_cwd(path: Path) -> str | None:
    """Read the 'cwd' field from the first usable line. Returns None if the
    schema has no cwd field — in which case we fall back to dir-name matching
    rather than guessing."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for _ in range(5):
                line = fh.readline()
                if not line:
                    break
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get("cwd"):
                    return str(obj["cwd"])
    except OSError:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exclude-session", default=None,
                    help="Current session id. Pass ${CLAUDE_SESSION_ID} — otherwise "
                         "this session is itself the newest and the check always fires.")
    args = ap.parse_args()

    repo = Path.cwd()
    exclude = (args.exclude_session or "").strip() or None

    # --- A: last handoff ---------------------------------------------------
    handoff_iso = git(["log", "-1", "--format=%cI", "--", "HANDOFF.md"], repo)
    handoff_dt = None
    if handoff_iso:
        try:
            handoff_dt = datetime.fromisoformat(handoff_iso)
        except ValueError:
            pass

    if not (repo / "HANDOFF.md").is_file():
        print("last handoff : HANDOFF.md is missing from the working tree")
    elif handoff_dt:
        print(f"last handoff : {handoff_dt:%Y-%m-%d %H:%M} ({ago(handoff_dt)})")
    else:
        print("last handoff : HANDOFF.md has never been committed")

    # --- B: newest prior session for this repo -----------------------------
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        print("last session : no session records found")
        return 0

    candidates = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    repo_str = str(repo).replace("\\", "/").rstrip("/").lower()
    repo_name = repo.name.lower()

    # Pass 1: match on the cwd field. This is exact and cannot match the wrong
    # project. Track whether ANY session carries a cwd, so we know if the
    # fallback below is even warranted.
    newest = None
    matched_by = None
    schema_has_cwd = False

    for p in candidates:
        if exclude and p.stem == exclude:
            continue
        cwd = session_cwd(p)
        if cwd is None:
            continue
        schema_has_cwd = True
        if cwd.replace("\\", "/").rstrip("/").lower() == repo_str:
            newest, matched_by = p, "cwd"
            break

    # Pass 2: only if this Claude Code version writes no cwd at all. Folder-name
    # matching is fuzzy — a repo name is a substring of its own encoded dir name AND of
    # any "<name>-backup" or "old-<name>" dir — so it is a last resort, never a supplement.
    if newest is None and not schema_has_cwd:
        for p in candidates:
            if exclude and p.stem == exclude:
                continue
            if repo_name in p.parent.name.lower():
                newest, matched_by = p, "folder name"
                break

    if not newest:
        print("last session : none found for this project (before this one)")
        print("\nverdict      : nothing to compare. If this is your first session here,")
        print("               that is expected.")
        return 0

    sess_dt = datetime.fromtimestamp(newest.stat().st_mtime).astimezone()
    note = "" if matched_by == "cwd" else "  [matched by folder name, not cwd — weaker]"
    print(f"last session : {sess_dt:%Y-%m-%d %H:%M} ({ago(sess_dt)}){note}")

    # --- Work committed after the handoff ---------------------------------
    # This is the cross-machine check. Local session records only exist on the
    # machine that made them, so the Mac's dead session is invisible from
    # Windows. Git is not: if the other machine committed work and skipped the
    # handoff, the commits arrive and HANDOFF.md doesn't describe them.
    commits_after: list[str] = []
    if handoff_iso:
        handoff_sha = git(["log", "-1", "--format=%H", "--", "HANDOFF.md"], repo)
        if handoff_sha:
            after = git(["log", "--oneline", f"{handoff_sha}..HEAD"], repo)
            if after:
                commits_after = after.splitlines()
                print()
                print(f"since handoff: {len(commits_after)} commit(s) landed after HANDOFF.md")
                print("               was last written:")
                for ln in commits_after[:8]:
                    print(f"                 {ln}")
                if len(commits_after) > 8:
                    print(f"                 … and {len(commits_after) - 8} more")

    print()
    if not handoff_dt:
        print("verdict      : cannot compare — HANDOFF.md has no commit history.")
        return 0

    # 5 min: the handoff commit lands shortly after the session file's last write.
    if (sess_dt - handoff_dt).total_seconds() > 300:
        print("verdict      : STALE. A session ran on THIS machine after the last")
        print("               HANDOFF.md commit and ended without /hud-handoff. HANDOFF.md")
        print("               does not describe what it did, and no transcript was")
        print("               exported for it. Check `git log` and the working tree before")
        print("               trusting the handoff. The session record is still on disk:")
        print(f"               {newest}")
        return 0  # verdict is in the text; non-zero would abort the skill's ```! block

    if commits_after:
        print("verdict      : PARTIAL. No stale session on this machine, but the commits")
        print("               listed above landed after HANDOFF.md was written — most")
        print("               likely another machine committed work and skipped")
        print("               /hud-handoff. Read those commits before trusting HANDOFF.md")
        print("               to describe current state.")
        return 0  # verdict is in the text; non-zero would abort the skill's ```! block

    print("verdict      : OK. HANDOFF.md is newer than your last session, and no commits")
    print("               landed after it. It should describe where you actually left off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
