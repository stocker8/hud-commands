#!/usr/bin/env python3
"""
Inspect the Claude Code session JSONL schema on THIS machine, at THIS version.

The schema is not a public contract and changes between versions. Run this
before trusting export_transcript.py's parser. If the reported field names do
not match what the exporter reads, fix the exporter.

Output is structural only: field names, types, and counts. It does not print
message bodies, so it is safe to paste into a chat.

Python 3.8+, standard library only. Runs on Windows and macOS.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# What export_transcript.py assumes. Compared against reality below.
EXPECTED_TOP = {"type", "timestamp", "isSidechain", "message"}
EXPECTED_MSG = {"role", "content"}
EXPECTED_BLOCKS = {"text", "thinking", "tool_use", "tool_result", "image"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session-id", default=None)
    ap.add_argument("--sample", type=int, default=500, help="Lines to sample.")
    args = ap.parse_args()

    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        sys.exit(f"ERROR: not found: {root}")

    sid = (args.session_id or "").strip() or None
    if sid:
        hits = sorted(root.rglob(f"{sid}.jsonl"))
        if not hits:
            sys.exit(f"ERROR: no JSONL for session '{sid}'")
        jsonl = hits[0]
    else:
        files = list(root.rglob("*.jsonl"))
        if not files:
            sys.exit(f"ERROR: no session JSONL under {root}")
        jsonl = max(files, key=lambda p: p.stat().st_mtime)

    top: set[str] = set()
    msg_fields: set[str] = set()
    entry_types: Counter = Counter()
    roles: Counter = Counter()
    shapes: Counter = Counter()
    blocks: Counter = Counter()
    lines = 0

    with jsonl.open("r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            if lines >= args.sample:
                break
            raw = raw.strip()
            if not raw:
                continue
            lines += 1
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                entry_types["(unparseable)"] += 1
                continue
            if not isinstance(e, dict):
                continue

            top.update(e.keys())
            entry_types[str(e.get("type", "(none)"))] += 1

            m = e.get("message")
            if not isinstance(m, dict):
                continue
            msg_fields.update(m.keys())
            if "role" in m:
                roles[str(m["role"])] += 1

            if "content" not in m:
                continue
            c = m["content"]
            if isinstance(c, str):
                shapes["string"] += 1
            elif isinstance(c, list):
                shapes["array"] += 1
                for b in c:
                    if isinstance(b, str):
                        blocks["(bare string)"] += 1
                    elif isinstance(b, dict):
                        blocks[str(b.get("type", "(untyped)"))] += 1
                    else:
                        blocks[f"(python {type(b).__name__})"] += 1
            elif c is None:
                shapes["null"] += 1
            else:
                shapes[type(c).__name__] += 1

    def section(title: str, items) -> None:
        print(f"\n=== {title} ===")
        if isinstance(items, Counter):
            for k, v in items.most_common():
                print(f"  {k} : {v}")
        else:
            for k in sorted(items):
                print(f"  {k}")

    print("=== FILE ===")
    print(f"  Path       : {jsonl}")
    print(f"  Size       : {round(jsonl.stat().st_size / 1024)} KB")
    print(f"  Lines read : {lines}")

    section("TOP-LEVEL FIELDS", top)
    section("ENTRY TYPES", entry_types)
    section("message.* FIELDS", msg_fields)
    section("ROLES", roles)
    section("message.content SHAPE", shapes)
    section("CONTENT BLOCK TYPES", blocks)

    # --- verdict ------------------------------------------------------------
    print("\n=== VERDICT ===")
    problems = []

    missing_top = EXPECTED_TOP - top
    if missing_top:
        problems.append(f"Missing expected top-level fields: {sorted(missing_top)}")

    missing_msg = EXPECTED_MSG - msg_fields
    if missing_msg:
        problems.append(f"Missing expected message.* fields: {sorted(missing_msg)}")

    if not ({"user", "assistant"} & set(entry_types)):
        problems.append("No 'user'/'assistant' entry types. The exporter renders nothing.")

    unknown = set(blocks) - EXPECTED_BLOCKS - {"(bare string)", "(untyped)"}
    if unknown:
        problems.append(f"Unhandled content block types (will render as `[type]`): {sorted(unknown)}")

    if problems:
        print("  MISMATCH — fix export_transcript.py before using it:")
        for p in problems:
            print(f"    - {p}")
        return 1

    print("  OK — schema matches what export_transcript.py expects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
