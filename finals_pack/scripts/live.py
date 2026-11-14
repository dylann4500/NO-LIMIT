#!/usr/bin/env python3
"""Declare which bot should be active on the portal. BUILDER runs this; Dylan does the click or upload.

  python3 scripts/live.py v7 "why, in a few words" [--by builder] [--force]
  python3 scripts/live.py                  # show the live bot and what the portal runs now

Writes state/live.json {bot, file, why, by, at, sha256, prev} and posts to both inboxes:
"LIVE BOT is now v7 (why) — Dylan: make it active on the portal ...". Refuses unless releases/v7.zip exists and is
a zip (--force overrides).

What live.json means: the bot for the next SCORED round (in the build hour: the bot for the next practice). For
the practice round inside a window (T-12 to T-9) don't declare the challenger: tell Dylan to activate it; at T-9
the clock reminds him to put the live bot back. The clock's upload reminders and the portal watcher's
"wrong active bot" checks compare the portal with this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from clock import ROOT, hhmm, load_json, norm_bot, same_bot, write_json  # noqa: E402
from say import post  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bot_name(arg: str) -> str:
    """'releases/v7.zip', 'v7.zip', 'v7 (1).zip' -> 'v7' (the case of the file name is kept)."""
    n = Path(arg.strip()).name
    n = re.sub(r"\.zip$", "", n, flags=re.I)
    return re.sub(r"\s*\(\d+\)$", "", n).strip()


def portal_view(root: Path) -> dict:
    """What the portal watcher last saw: active bot, uploads, when."""
    st = load_json(root / "state" / "portal.json", {})
    return {"active": (st.get("active") or {}), "uploads": st.get("uploads") or [], "ok_at": st.get("last_ok") or 0}


def show(root: Path) -> int:
    live = load_json(root / "state" / "live.json", None)
    pv = portal_view(root)
    act = pv["active"].get("filename")
    if not live:
        print("No live bot declared yet (state/live.json is empty).")
    else:
        f = root / live.get("file", "")
        prev = (live.get("prev") or {}).get("bot")
        print(f"LIVE: {live.get('bot')} ({live.get('file')}, {'exists' if f.exists() else 'MISSING'}) — {live.get('why')} "
              f"— by {live.get('by')} at {hhmm(live.get('at', 0))}" + (f"; previous: {prev}" if prev else ""))
    if pv["ok_at"]:
        age = time.time() - pv["ok_at"]
        match = ""
        if live and act:
            match = " (matches the live bot)" if same_bot(live.get("bot", ""), act) else " (NOT the live bot)"
        print(f"Portal runs: {act or 'NO active bot'}{match} — checked {hhmm(pv['ok_at'])} ({age:.0f} s ago)")
    else:
        print("Portal: the portal watcher hasn't reported yet (state/portal.json).")
    return 0


def declare(root: Path, arg: str, why: str, by: str, force: bool) -> int:
    name = bot_name(arg)
    if not name:
        print("live.py: give a bot name, e.g. v7", file=sys.stderr)
        return 2
    rel = f"releases/{name}.zip"
    zp = root / rel
    digest = ""
    if not zp.exists():
        if not force:
            print(f"live.py: NOT declared: {rel} doesn't exist. Only released, tested zips go live (platform releases "
                  "them). Use --force only if the file is coming and you know why.", file=sys.stderr)
            return 2
    else:
        if not zipfile.is_zipfile(zp) and not force:
            print(f"live.py: NOT declared: {rel} isn't a valid zip.", file=sys.stderr)
            return 2
        try:
            with zipfile.ZipFile(zp) as z:
                if "agent.py" not in z.namelist():
                    print(f"live.py: warning: {rel} has no agent.py at its root (check the kit's upload rules).",
                          file=sys.stderr)
        except zipfile.BadZipFile:
            pass
        digest = sha256(zp)
    old = load_json(root / "state" / "live.json", None) or {}
    if old.get("bot") and norm_bot(old["bot"]) != norm_bot(name):
        prev = {k: old[k] for k in ("bot", "file", "why", "by", "at", "sha256") if k in old}
    else:
        prev = old.get("prev")
    now = time.time()
    live = {"bot": name, "file": rel, "why": why, "by": by, "at": now, "at_hhmm": time.strftime("%H:%M:%S"),
            "sha256": digest, "prev": prev}
    write_json(root / "state" / "live.json", live)

    pv = portal_view(root)
    act = pv["active"].get("filename")
    fresh = pv["ok_at"] and now - pv["ok_at"] < 180
    hint = ""
    if fresh and act and same_bot(name, act) and (not digest or not pv["active"].get("sha256")
                                                  or pv["active"]["sha256"] == digest):
        hint = f" [the portal already runs {act}: nothing to do]"
    else:
        up = next((u for u in pv["uploads"] if u.get("status") == "ready" and (
            (digest and u.get("sha256") == digest) or norm_bot(u.get("filename", "")) == norm_bot(name))), None)
        if up:
            hint = f" [already uploaded as {up.get('filename')}: a click on Make active]"
        elif fresh:
            hint = " [not on the portal yet: upload it]"
        if fresh:
            hint += f" · the portal runs {act or 'NO bot'} now"
    msg = (f"LIVE BOT is now {name} ({why}) — Dylan: make it active on the portal (click it if already uploaded, "
           f"else upload {rel}){hint}. If a round that should play another bot is about to start, wait until it has "
           "started (BUILDER says when)")
    post("both", msg, "live")
    print(msg)
    if prev:
        print(f"(previous live bot: {prev.get('bot')})")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bot", nargs="?", help="vN (or releases/vN.zip)")
    ap.add_argument("why", nargs="*", help="why, in a few words")
    ap.add_argument("--by", default=os.environ.get("AVALON_FROM") or "builder")
    ap.add_argument("--force", action="store_true", help="declare even if the zip isn't there (yet)")
    a = ap.parse_args(argv)
    if not a.bot:
        return show(ROOT)
    return declare(ROOT, a.bot, " ".join(a.why).strip() or "no reason given", a.by, a.force)


if __name__ == "__main__":
    sys.exit(main())
