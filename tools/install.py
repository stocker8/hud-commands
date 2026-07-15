#!/usr/bin/env python3
"""
Install the hud session kit into a target repo. Windows and macOS.

  - Copies hud-handoff and hud-catchup into <repo>/.claude/skills/
  - Retires any old .claude/commands/hud-handoff.md and hud-catchup.md to .bak
  - Installs the pre-commit secret-scan hook (and chmods it on macOS)
  - Adds log-directory safety entries to .gitignore

Usage:
  python3 tools/install.py --repo <path-to>/<a-repo>
  python  tools\\install.py --repo F:\\<path-to>\\<a-repo>

Python 3.8+, standard library only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path

GITIGNORE_BLOCK = [
    "",
    "# --- hud session kit ---",
    "# Transcripts live at ~/claude-logs/<project>/, outside this repo.",
    "# These entries exist only in case one ever lands here by accident.",
    "claude-logs/",
    "*_log[0-9]*.md",
    ".dev.vars",
    ".dev.vars.*",
    ".env",
    ".env.*",
    "!.env.example",
]

SKILLS = ["hud-handoff", "hud-catchup"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=None,
                    help="A git repo to install the pre-commit hook into. Optional. "
                         "Repeat the run for each repo you want guarded.")
    ap.add_argument("--project-scope", action="store_true",
                    help="Install skills into <repo>/.claude/skills instead of "
                         "~/.claude/skills. You almost certainly do not want this.")
    ap.add_argument("--keep-old-commands", action="store_true",
                    help="Leave .claude/commands/hud-*.md in place instead of renaming to .bak")
    args = ap.parse_args()

    kit = Path(__file__).resolve().parent.parent
    repo = Path(args.repo).expanduser().resolve() if args.repo else None

    if args.project_scope and not repo:
        sys.exit("ERROR: --project-scope needs --repo.")
    if repo and not (repo / ".git").exists():
        sys.exit(f"ERROR: not a git repository: {repo}")

    # --- 1. Skills: personal scope by default ------------------------------
    if args.project_scope:
        skills_dest = repo / ".claude" / "skills"
        print(f"Installing skills (THIS REPO ONLY): {skills_dest}\n")
    else:
        skills_dest = Path.home() / ".claude" / "skills"
        print(f"Installing skills (ALL PROJECTS): {skills_dest}\n")
    skills_dest.mkdir(parents=True, exist_ok=True)

    for name in SKILLS:
        src, dst = kit / "skills" / name, skills_dest / name
        if not src.is_dir():
            sys.exit(f"ERROR: kit is missing {src}")
        if dst.exists():
            print(f"  Replacing existing skill: {name}")
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  Installed: {dst}")

    # Exec bit on the bundled script (harmless on Windows).
    script = skills_dest / "hud-handoff" / "scripts" / "export_transcript.py"
    if script.is_file():
        script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # --- 2. Retire old commands -------------------------------------------
    # Skills take precedence over same-named commands, so the old files are
    # already inert. Rename them anyway so there is one source of truth.
    # Check BOTH scopes: the old ones could be personal or project.
    if not args.keep_old_commands:
        dirs = [Path.home() / ".claude" / "commands"]
        if repo:
            dirs.append(repo / ".claude" / "commands")
        for commands in dirs:
            if not commands.is_dir():
                continue
            for old in ("hud-handoff.md", "hud-catchup.md"):
                p = commands / old
                if p.is_file():
                    bak = p.with_suffix(p.suffix + ".bak")
                    p.replace(bak)
                    print(f"  Retired: {p} -> {bak.name}")

    # --- 3. Pre-commit hook (per repo) -------------------------------------
    if not repo:
        print("\n  No --repo given, so no pre-commit hook installed.")
        print("  Run again with --repo <path> for each repo you want guarded.")
        print("\nDone. Restart Claude Code, then /hud-catchup in any project.")
        return 0

    hook_src = kit / "hooks" / "pre-commit"
    hooks_dir = repo / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_dst = hooks_dir / "pre-commit"

    if hook_dst.exists():
        shutil.copy2(hook_dst, hook_dst.with_suffix(".bak"))
        print("  Backed up existing hook -> pre-commit.bak")

    shutil.copyfile(hook_src, hook_dst)
    hook_dst.chmod(hook_dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("  Installed hook: .git/hooks/pre-commit")

    if shutil.which("gitleaks") is None:
        print("\n  WARNING: gitleaks is not installed. The hook FAILS CLOSED —")
        print("           it will block commits until gitleaks is present.")
        print("           Windows: winget install gitleaks")
        print("           macOS:   brew install gitleaks")

    # --- 4. .gitignore -----------------------------------------------------
    # Logs live outside the repo, so this is belt-and-suspenders, not the plan.
    gi = repo / ".gitignore"
    existing = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    header = [ln for ln in GITIGNORE_BLOCK if not ln or ln.startswith("#")]
    needed = [ln for ln in GITIGNORE_BLOCK
              if ln and not ln.startswith("#") and ln not in existing]

    if needed:
        with gi.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(header + needed) + "\n")
        print(f"  Updated .gitignore ({len(needed)} new entries)")
    else:
        print("  .gitignore already covered")

    interp = "python3" if os.name != "nt" else "python"
    print("\nDone. Next:")
    print(f"  1. {interp} {kit / 'tools' / 'probe_jsonl.py'}")
    print("     -> confirm the VERDICT says OK before going further")
    print("  2. Restart Claude Code so the new skills load")
    print("  3. /hud-catchup   to test")
    print("\n  The skills now work in EVERY project. The hook is per-repo —")
    print("  re-run with --repo for each other repo you commit from.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
