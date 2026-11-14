#!/usr/bin/env python3
"""Post one message to a session's inbox, or only log it.

  python3 scripts/say.py <builder|research|both> "<one message>" [--from NAME]
  python3 scripts/say.py --record <builder|research|both> "<the message you sent>"

Default: appends one line `HH:MM:SS [from] text` to inbox/<name>.log (newlines become " / ") and a copy to
state/events.log; the session's Monitor (scripts/feed.py) prints the line, which wakes it. With --record: only the
state/events.log copy (for a message already sent with Claude Code's SendMessage, so it doesn't arrive twice).
One message per point, with numbers and file paths; never acknowledgements. The clock and the portal watcher post
through post() here. Subagents never use this: they report to whoever spawned them.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ("builder", "research")
MAX_CHARS = 4000


def clean(text: str) -> str:
    """One line: newlines become ' / ', control characters (bells, escapes) go, at most MAX_CHARS."""
    t = str(text if text is not None else "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    t = " / ".join(x.strip() for x in t.split("\n") if x.strip())
    t = re.sub(r"[\x00-\x1f\x7f]", "", t)
    return t if len(t) <= MAX_CHARS else t[:MAX_CHARS - 1] + "…"


def append(path: Path, line: str) -> None:
    """One write() on an O_APPEND file: lines from several writers never interleave."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)


def targets(to: str) -> tuple:
    to = (to or "").strip().lower()
    if to in ("both", "all"):
        return NAMES
    if to not in NAMES:
        raise ValueError(f"unknown inbox {to!r}: use builder, research or both")
    return (to,)


def post(to: str, text: str, frm: str = "?", root: Path | None = None, record_only: bool = False) -> str:
    """Append the message to the inbox(es) and state/events.log (record_only: the log alone); returns the line."""
    root = Path(root) if root else ROOT
    names = targets(to)
    body = clean(text)
    frm = re.sub(r"[\[\]\s]+", "-", str(frm or "?").strip()) or "?"
    now = time.time()
    stamp = time.strftime("%H:%M:%S", time.localtime(now))
    line = f"{stamp} [{frm}] {body}"
    if not record_only:
        for n in names:
            append(root / "inbox" / f"{n}.log", line + "\n")
    who = "both" if len(names) > 1 else names[0]
    rec = f"{time.strftime('%Y-%m-%d', time.localtime(now))} {stamp} [{frm} -> {who}{' (sent directly)' if record_only else ''}] {body}\n"
    try:
        append(root / "state" / "events.log", rec)
    except OSError:
        if record_only:
            raise
        # the record is a copy; the inbox line is what matters
    return line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("to", choices=["builder", "research", "both"])
    ap.add_argument("text", nargs="+", help="the message (quote it)")
    ap.add_argument("--from", dest="frm", default=None,
                    help="sender name (default: the other session; 'human' for both)")
    ap.add_argument("--record", action="store_true",
                    help="only log it in state/events.log (the message was already sent with SendMessage)")
    a = ap.parse_args(argv)
    frm = a.frm or os.environ.get("AVALON_FROM") or {"builder": "research", "research": "builder"}.get(a.to, "human")
    try:
        post(a.to, " ".join(a.text), frm, record_only=a.record)
    except (OSError, ValueError) as e:
        print(f"say.py: not {'recorded' if a.record else 'posted'}: {e}", file=sys.stderr)
        return 1
    print(f"recorded (to {a.to}) in state/events.log" if a.record else f"posted to {a.to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
