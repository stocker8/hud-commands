#!/usr/bin/env python3
"""Print repository state for the hud skills' environment blocks.

Never exits non-zero and never dies in a non-repo folder — a ```! block that
fails aborts the whole skill, which is exactly what must not happen just
because a project has no git repo (yet).

Usage: repo_state.py [--fetch]   (--fetch: refresh origin first, for catchup)
"""
import subprocess
import sys


def git(*args):
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True, timeout=30)
        return p.returncode, p.stdout.rstrip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, f"(git unavailable: {e})"


def main():
    code, inside = git("rev-parse", "--is-inside-work-tree")
    if code != 0 or inside != "true":
        print("NOT A GIT REPOSITORY — no commits/branches to report; "
              "skip all git steps.")
        return 0

    if "--fetch" in sys.argv[1:]:
        git("fetch", "-q")

    print("--- branch vs origin ---")
    _, sb = git("status", "-sb")
    print(sb.splitlines()[0] if sb else "(unknown)")
    print("--- working tree ---")
    _, short = git("status", "--short")
    print(short if short else "(clean)")
    print("--- recent commits ---")
    _, log = git("log", "--oneline", "-10")
    print(log if log else "(no commits yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
