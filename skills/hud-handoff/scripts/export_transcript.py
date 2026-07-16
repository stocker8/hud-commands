#!/usr/bin/env python3
"""
Export a Claude Code session transcript from its JSONL source, scrub secrets,
and write it to a dated log file in <project-root>/claude-logs/.

The log folder lives inside the project on the data drive (never on C:), and
is kept out of git by a .gitignore entry this script enforces before writing.
The per-repo gitleaks pre-commit hook is the backstop.

Claude Code writes every session to disk incrementally as JSONL. This script
CONVERTS that ground-truth record. It does not ask a model to recall or
reconstruct the conversation.

Scrubbing runs in two passes:
  1. Exact-value replacement using real values read from env files (strongest).
  2. Regex patterns for known key shapes (catches values not in env files).

The script exits non-zero and writes NOTHING if post-scrub verification finds a
known secret value still present in the output.

Python 3.8+, standard library only. Runs on Windows and macOS.

SCHEMA WARNING: the JSONL schema is not a public contract and varies between
Claude Code versions. Run tools/probe_jsonl.py and confirm the field names
before trusting this parser.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

# Locale-independent. strftime("%b") would change on a non-English system.
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

DEFAULT_ENV_FILES = [
    ".dev.vars",
    "backend/.dev.vars",
    ".env",
    ".env.local",
    "ios/Secrets.plist",
]

# Values shorter than this are never treated as secrets. Without this, "true"
# and "8080" get redacted everywhere and the log becomes unreadable.
MIN_SECRET_LEN = 8

SECRET_PATTERNS = [
    r"sk-ant-[A-Za-z0-9_\-]{20,}",                                       # Anthropic
    r"AIza[0-9A-Za-z_\-]{35}",                                           # Google / ARCore
    r"ya29\.[0-9A-Za-z_\-]{20,}",                                        # Google OAuth
    r"gh[pousr]_[A-Za-z0-9]{20,}",                                       # GitHub token
    r"github_pat_[A-Za-z0-9_]{20,}",                                     # GitHub fine-grained PAT
    r"AKIA[0-9A-Z]{16}",                                                 # AWS access key id
    r"xox[baprs]-[A-Za-z0-9\-]{10,}",                                    # Slack
    r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}", # JWT
    r"-----BEGIN[^-]{0,40}PRIVATE KEY-----[\s\S]*?-----END[^-]{0,40}PRIVATE KEY-----",
    r"(?im)^[ \t]*(?:export[ \t]+)?[A-Z][A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIALS?)[ \t]*=[ \t]*\S+",
    r"(?i)\b(?:api[_\-]?key|secret|token|password|bearer)\b[ \t]*[:=][ \t]*[\"']?[^\s\"',;]{12,}",
]

ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")


# ---------------------------------------------------------------------------
# Locate
# ---------------------------------------------------------------------------

def find_jsonl(session_id: str | None) -> Path:
    """
    Claude Code encodes the project path into the directory name under
    ~/.claude/projects/. Rather than reimplement that encoding (which is not
    documented and can change), search recursively for the session file.
    Version-agnostic and works identically on Windows and macOS.
    """
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        sys.exit(f"ERROR: Claude Code projects directory not found: {root}")

    if session_id:
        hits = sorted(root.rglob(f"{session_id}.jsonl"))
        if not hits:
            sys.exit(f"ERROR: no JSONL for session id '{session_id}' under {root}")
        return hits[0]

    print("WARNING: no --session-id given; using most recently modified session.",
          file=sys.stderr)
    files = list(root.rglob("*.jsonl"))
    if not files:
        sys.exit(f"ERROR: no session JSONL files under {root}")
    return max(files, key=lambda p: p.stat().st_mtime)


def read_entries(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("WARNING: skipping unparseable JSONL line.", file=sys.stderr)
                continue
            if isinstance(obj, dict):
                yield obj


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_block(block: Any, include_tool_input: bool) -> str | None:
    if isinstance(block, str):
        return block
    if not isinstance(block, dict):
        return None

    btype = block.get("type")

    if btype == "text":
        return block.get("text") or None

    if btype == "thinking":
        # Excluded. Thinking is noisy and can restate secrets verbatim.
        return None

    if btype == "tool_use":
        name = block.get("name", "?")
        if not include_tool_input:
            # Tool INPUT is summarized, not dumped. Inputs routinely carry file
            # contents and command lines with credentials in them.
            return f"`[tool call: {name}]`"
        payload = json.dumps(block.get("input", {}), indent=2, ensure_ascii=False)
        return f"`[tool call: {name}]`\n\n```json\n{payload}\n```"

    if btype == "tool_result":
        status = "error" if block.get("is_error") else "ok"
        if not include_tool_input:
            return f"`[tool result: {status}]`"
        content = block.get("content")
        body = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        if body and len(body) > 2000:
            body = body[:2000] + "\n… [truncated]"
        return f"`[tool result: {status}]`\n\n```\n{body}\n```"

    if btype == "image":
        return "`[image]`"

    return f"`[{btype}]`" if btype else None


def render(path: Path, project: str, include_tool_input: bool) -> tuple[str, int]:
    out: list[str] = []
    out.append(f"# Session log — {project}\n")
    out.append(f"- Session: `{path.stem}`")
    out.append(f"- Exported: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}")
    out.append(f"- Source: `{path}`")
    out.append(f"- Tool payloads: {'included' if include_tool_input else 'summarized'}\n")
    out.append("> Rendered from the Claude Code JSONL session record. "
               "Secrets scrubbed on export.\n")
    out.append("---\n")

    turns = 0
    for e in read_entries(path):
        etype = e.get("type")
        if etype not in ("user", "assistant"):
            continue  # skips 'summary', 'system', etc.

        msg = e.get("message")
        if not isinstance(msg, dict):
            continue

        role_raw = msg.get("role")
        if not role_raw:
            continue
        role = {"user": "Hud", "assistant": "Claude"}.get(role_raw, role_raw)

        content = msg.get("content")
        parts: list[str] = []
        if isinstance(content, str):
            if content.strip():
                parts.append(content)
        elif isinstance(content, list):
            for block in content:
                rendered = render_block(block, include_tool_input)
                if rendered and rendered.strip():
                    parts.append(rendered)

        if not parts:
            continue

        tag = " _(subagent)_" if e.get("isSidechain") else ""
        ts = e.get("timestamp", "")
        out.append(f"### {role}{tag}  <sub>{ts}</sub>\n")
        for p in parts:
            out.append(p + "\n")
        out.append("---\n")
        turns += 1

    return "\n".join(out), turns


# ---------------------------------------------------------------------------
# Scrub
# ---------------------------------------------------------------------------

def load_known_secrets(env_files: list[str]) -> list[tuple[str, str]]:
    """Returns (key, value) pairs. Longest values first so that a value which
    contains another value gets replaced before its substring does."""
    found: list[tuple[str, str]] = []
    for name in env_files:
        p = Path(name)
        if not p.is_file():
            continue
        print(f"Reading secret values from: {p}")
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lstrip().startswith("#"):
                continue
            m = ENV_LINE.match(line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            if len(val) < MIN_SECRET_LEN:
                continue
            found.append((key, val))
    found.sort(key=lambda kv: len(kv[1]), reverse=True)
    return found


def scrub(text: str, known: list[tuple[str, str]]) -> str:
    # Pass 1: exact values. This is the pass that actually saves you. A regex
    # can miss a novel key format; a literal match on your real value cannot.
    for key, val in known:
        text = text.replace(val, f"[REDACTED:{key}]")

    # Pass 2: patterns, for anything not in an env file.
    for pat in SECRET_PATTERNS:
        text = re.sub(pat, "[REDACTED]", text)

    return text


def verify_exact(text: str, known: list[tuple[str, str]]) -> list[str]:
    """
    Regression tripwire, NOT an independent check. scrub() replaces these exact
    values, so this can only fire if scrub() is later broken. Keep it anyway:
    it costs nothing and it fails loudly if someone edits scrub() badly.
    """
    return [f"{k} ({v[:6]}…)" for k, v in known if v in text]


def verify_gitleaks(text: str) -> tuple[bool, list[str]]:
    """
    The real second opinion. gitleaks has hundreds of detection rules written by
    people who do this for a living. Our regex list has eleven, written by me.
    Running it over the scrubbed text catches key formats we never anticipated.

    Returns (ran, findings).
    """
    exe = shutil.which("gitleaks")
    if not exe:
        return (False, [])

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "log.md"
        tmp.write_text(text, encoding="utf-8", newline="\n")
        report = Path(td) / "report.json"

        proc = subprocess.run(
            [exe, "detect", "--no-git", "--source", str(tmp),
             "--report-format", "json", "--report-path", str(report),
             "--redact", "--no-banner"],
            capture_output=True, text=True,
        )

        # gitleaks exits 1 when it finds leaks, 0 when clean, >1 on error.
        if proc.returncode > 1:
            print(f"WARNING: gitleaks errored, scan inconclusive: {proc.stderr.strip()}",
                  file=sys.stderr)
            return (False, [])

        if not report.is_file():
            return (True, [])

        try:
            findings = json.loads(report.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            return (True, [])

        return (True, [f"{f.get('RuleID', '?')} at line {f.get('StartLine', '?')}"
                       for f in findings])


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def project_root(start: Path) -> Path:
    """The enclosing git repo's root, or `start` itself if not inside a repo.
    Keeps logs in ONE folder per project even when the session was launched
    from a subdirectory (e.g. backend/some_worker)."""
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start


def ensure_gitignored(repo_root: Path) -> None:
    """If repo_root is a git repo, make sure claude-logs/ is gitignored.
    Transcripts must never be committed, even scrubbed ones."""
    if not (repo_root / ".git").exists():
        return
    gi = repo_root / ".gitignore"
    lines = gi.read_text(encoding="utf-8", errors="replace").splitlines() if gi.is_file() else []
    if any(l.strip().rstrip("/") == "claude-logs" for l in lines):
        return
    with gi.open("a", encoding="utf-8", newline="\n") as fh:
        if lines and lines[-1].strip():
            fh.write("\n")
        fh.write("# session transcripts (hud-handoff) — never commit\nclaude-logs/\n")
    print(f"Added claude-logs/ to {gi}")


def machine_tag(explicit: str | None = None) -> str:
    """
    Short identifier for this machine, baked into the log filename.

    Without this, two machines both compute '14Jul2026_log1.md' for the same
    day because the counter is local to each machine's folder. Sync them and
    they collide. Hostname (not platform) because there may be more than one
    Windows box.
    """
    raw = explicit or socket.gethostname().split(".")[0]
    tag = re.sub(r"[^a-z0-9-]", "-", raw.lower()).strip("-")
    tag = re.sub(r"-+", "-", tag)
    return tag or "unknown"


def next_log_path(out_dir: Path, machine: str) -> Path:
    now = datetime.now()
    stamp = f"{now.day:02d}{MONTHS[now.month - 1]}{now.year}"
    n = 1
    while (out_dir / f"{stamp}_{machine}_log{n}.md").exists():
        n += 1
    return out_dir / f"{stamp}_{machine}_log{n}.md"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session-id", default=None,
                    help="Session ID. Pass ${CLAUDE_SESSION_ID} from the skill.")
    ap.add_argument("--project", default=None,
                    help="Project label for the output subfolder. Default: cwd name.")
    ap.add_argument("--machine", default=None,
                    help="Machine tag in the filename. Default: this host's short name. "
                         "Prevents two machines colliding on the same day's log number.")
    ap.add_argument("--out-root", default=None,
                    help="Override the output folder. Default: <project-root>/claude-logs "
                         "(project-local, gitignored).")
    ap.add_argument("--env-file", action="append", default=None,
                    help="Env file whose values get exact-match redacted. Repeatable.")
    ap.add_argument("--include-tool-input", action="store_true",
                    help="Dump tool inputs/results. Higher fidelity, higher leak surface.")
    ap.add_argument("--allow-unverified", action="store_true",
                    help="Write the log even if gitleaks is unavailable to verify it.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print to stdout instead of writing a file.")
    args = ap.parse_args()

    # ${CLAUDE_SESSION_ID} expands to empty if unset; treat that as absent.
    session_id = (args.session_id or "").strip() or None

    jsonl = find_jsonl(session_id)
    print(f"Source: {jsonl}")

    project = args.project or project_root(Path.cwd()).name
    env_files = args.env_file or DEFAULT_ENV_FILES

    text, turns = render(jsonl, project, args.include_tool_input)
    print(f"Rendered {turns} turns.")
    if turns == 0:
        print("ERROR: no conversational turns rendered. The JSONL schema probably "
              "does not match this parser. Run tools/probe_jsonl.py.", file=sys.stderr)
        return 2

    known = load_known_secrets(env_files)
    text = scrub(text, known)

    # Layer 1: regression tripwire on our own scrub.
    leaked = verify_exact(text, known)
    if leaked:
        print("\nSCRUB FAILED. Known secret values survived redaction:", file=sys.stderr)
        for item in leaked:
            print(f"  - {item}", file=sys.stderr)
        print("Nothing was written. scrub() is broken.", file=sys.stderr)
        return 3
    print(f"Exact-value scrub: {len(known)} known values checked, 0 survivors.")

    # Layer 2: independent scan. This is the one that can actually surprise us.
    ran, findings = verify_gitleaks(text)
    if not ran:
        msg = ("gitleaks not found — the scrubbed log was NOT independently verified. "
               "Install it: winget install gitleaks / brew install gitleaks")
        if args.allow_unverified:
            print(f"WARNING: {msg}", file=sys.stderr)
        else:
            print(f"\nERROR: {msg}", file=sys.stderr)
            print("Nothing was written. Pass --allow-unverified to override.", file=sys.stderr)
            return 4
    elif findings:
        print("\nGITLEAKS FOUND SECRETS IN THE SCRUBBED LOG:", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        print("Nothing was written. Add the pattern to SECRET_PATTERNS or the "
              "value's file to --env-file, then re-run.", file=sys.stderr)
        return 5
    else:
        print("gitleaks scan: clean.")

    if args.dry_run:
        sys.stdout.write(text)
        return 0

    if args.out_root:
        out_dir = Path(args.out_root).expanduser()
    else:
        root = project_root(Path.cwd())
        ensure_gitignored(root)
        out_dir = root / "claude-logs"
    out_dir.mkdir(parents=True, exist_ok=True)

    machine = machine_tag(args.machine)
    out_path = next_log_path(out_dir, machine)
    # Explicit newline="\n" so Windows and macOS produce byte-identical logs.
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    print(f"\nWrote {out_path}")
    print(f"({turns} turns, {round(len(text) / 1024)} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
