#!/usr/bin/env python3
"""Print each new line of a session's inbox as it arrives: run it under Claude Code's Monitor tool.

  python3 scripts/feed.py builder          # in BUILDER's Monitor
  python3 scripts/feed.py research         # in RESEARCH's Monitor
  python3 scripts/feed.py research --from-start | --from-end

One printed line = one wake-up, so it prints nothing else (no heartbeat). It checks the inbox every second.

Where it starts: the very first run starts at the end of the inbox. It remembers how far it got
(state/feed-<name>.pos), so when an expired Monitor is re-armed it first prints the lines that arrived while it
was down (the newest 200 at most; older ones are summed up in one line). --from-end skips them; --from-start
replays the whole inbox.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATCH_UP_MAX = 200


def load_pos(path: Path):
    try:
        d = json.loads(path.read_text())
        return int(d["pos"]), int(d.get("ino", 0))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def save_pos(path: Path, pos: int, ino: int) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"pos": pos, "ino": ino, "at": time.time()}))
        os.replace(tmp, path)
    except OSError:
        pass


def emit(lines) -> None:
    for ln in lines:
        sys.stdout.write(ln + "\n")
    sys.stdout.flush()


def read_from(path: Path, pos: int):
    """Complete lines from byte `pos` on: (lines, new position). A half-written line waits for the next check."""
    with open(path, "rb") as f:
        f.seek(pos)
        data = f.read()
    end = data.rfind(b"\n")
    if end < 0:
        return [], pos
    chunk = data[:end + 1]
    lines = [b.decode("utf-8", errors="replace").rstrip("\r") for b in chunk.split(b"\n")[:-1]]
    return [ln for ln in lines if ln.strip()], pos + len(chunk)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", choices=["builder", "research"])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--from-start", action="store_true", help="print the whole inbox first")
    g.add_argument("--from-end", action="store_true", help="skip anything already in the inbox")
    ap.add_argument("--interval", type=float, default=1.0, help=argparse.SUPPRESS)
    a = ap.parse_args(argv)

    inbox = ROOT / "inbox" / f"{a.name}.log"
    posf = ROOT / "state" / f"feed-{a.name}.pos"
    inbox.parent.mkdir(parents=True, exist_ok=True)
    inbox.touch(exist_ok=True)
    st = inbox.stat()
    ino, size = st.st_ino, st.st_size
    saved = load_pos(posf)
    if a.from_start:
        pos = 0
    elif a.from_end or saved is None:
        pos = size
    elif saved[1] != ino:
        pos = 0               # the inbox was replaced: everything in the new one is unread
    else:
        pos = min(saved[0], size)

    try:
        lines, pos = read_from(inbox, pos)
        if len(lines) > CATCH_UP_MAX and not a.from_start:
            emit([f"(feed: {len(lines) - CATCH_UP_MAX} older unread inbox lines skipped; see inbox/{a.name}.log)"])
            lines = lines[-CATCH_UP_MAX:]
        if lines:
            emit(lines)
        save_pos(posf, pos, ino)
        while True:
            time.sleep(a.interval)
            try:
                st = inbox.stat()
            except FileNotFoundError:
                continue      # being replaced; it will reappear
            if st.st_ino != ino or st.st_size < pos:   # replaced or truncated: read the new one from the top
                ino, pos = st.st_ino, 0
            if st.st_size == pos:
                continue
            lines, pos = read_from(inbox, pos)
            if lines:
                emit(lines)
            save_pos(posf, pos, ino)
    except (KeyboardInterrupt, BrokenPipeError):
        try:
            sys.stdout = open(os.devnull, "w")   # no traceback noise when the Monitor closes the pipe
        except OSError:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
