#!/usr/bin/env python3
"""Shared task board for every agent (and person) working in this repo.

The board lives on its own branch, `coord`, on the shared remote. Every change is one commit
pushed there; git rejects a push that isn't based on the latest board, so two agents can never
both take the same task (the loser re-reads the board and gets a clear refusal). The script
never touches your working tree, index or current branch, so it cannot cause merge conflicts.

Everyone:
  python3 coord/coord.py status                    # the whole board: run this first, every session
  python3 coord/coord.py note [ID] "text"          # check-in, on a task or board-wide
Manager:
  python3 coord/coord.py post ID "what" [--for NAME] [--priority 2] [--paths ...] [--cmd ...] [--details ...]
  python3 coord/coord.py assign ID NAME            # (re)assign an open task; NAME '' = anyone
  python3 coord/coord.py note --pin "today: Finals variant parity first, then tuning"
Workers:
  python3 coord/coord.py take [ID]                 # no ID: the best open task for you
  python3 coord/coord.py claim ID "what" --paths bots/dn-v11   # self-started work
  python3 coord/coord.py renew ID [--hours 2]
  python3 coord/coord.py done ID --result "v11 +0.4 ±0.3 vs v10, 20k tables, cloud/results/v11.json"
  python3 coord/coord.py release ID [--why ...]    # a posted task goes back to the queue
  python3 coord/coord.py check PATH...             # exit 2 if someone else holds it
  python3 coord/coord.py whoami [--set NAME]       # your board name for this clone

`--as NAME` (or COORD_NAME) names the agent for one command, for several agents on one clone.
A taken task holds its `paths` until done, released or expired. Paths overlap when one contains
the other. An expired task is STALE: anyone may take it over. Stdlib only; Python 3.8+.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BRANCH = "coord"
REMOTE = os.environ.get("COORD_REMOTE", "origin")
REF = f"refs/remotes/{REMOTE}/{BRANCH}"
FETCH_TTL_S = 90  # hooks reuse a fetch this recent
ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
DONE_SHOWN_H = 24
AS_NAME = ""  # set by --as


class CoordError(Exception):
    pass


# ---------------------------------------------------------------- git plumbing

def git(*args, input=None, env=None, check=True, timeout=30, binary=False):
    r = subprocess.run(["git", *args], cwd=ROOT, input=input, capture_output=True,
                       text=not binary, env=env, timeout=timeout)
    if check and r.returncode:
        err = r.stderr if not binary else r.stderr.decode(errors="replace")
        raise CoordError(f"git {' '.join(args[:2])} failed: {err.strip()}")
    return r


def stamp_file() -> Path:
    return (ROOT / git("rev-parse", "--git-dir").stdout.strip()).resolve() / "coord_fetched"


def fetch(max_age: float = 0, timeout: int = 20) -> str:
    """Refresh the local copy of the board. Returns '' on success, else a warning."""
    stamp = stamp_file()
    if max_age and stamp.exists() and time.time() - stamp.stat().st_mtime < max_age:
        return ""
    try:
        r = git("fetch", "--quiet", REMOTE, f"+refs/heads/{BRANCH}:{REF}", check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "board fetch timed out; showing the last fetched board"
    if r.returncode:
        if "couldn't find remote ref" in r.stderr:  # no board yet
            git("update-ref", "-d", REF, check=False)
        else:
            return f"board fetch failed ({r.stderr.strip()[:200]}); showing the last fetched board"
    stamp.touch()
    return ""


def board_head() -> str | None:
    r = git("rev-parse", "--verify", "--quiet", REF, check=False)
    return r.stdout.strip() or None


def read_board(commit: str | None) -> dict:
    board = {"tasks": {}, "notes": [], "commit": commit}
    if not commit:
        return board
    names = [n for n in git("ls-tree", "-r", "--name-only", commit).stdout.splitlines() if n.endswith(".json")]
    if not names:
        return board
    out = git("cat-file", "--batch", input="".join(f"{commit}:{n}\n" for n in names).encode(),
              binary=True).stdout
    pos = 0
    for name in names:
        nl = out.index(b"\n", pos)
        size = int(out[pos:nl].split()[2])
        data = out[nl + 1: nl + 1 + size]
        pos = nl + 1 + size + 1
        try:
            obj = json.loads(data)
        except ValueError:
            continue
        if name.startswith("tasks/"):
            board["tasks"][obj.get("id", Path(name).stem)] = obj
        elif name.startswith("notes/"):
            board["notes"].append(obj)
    board["notes"].sort(key=lambda n: n.get("at", ""))
    return board


def make_commit(parent: str | None, changes: dict, message: str) -> str:
    with tempfile.TemporaryDirectory() as d:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "index"))
        git("read-tree", *([parent] if parent else ["--empty"]), env=env)
        for path, content in changes.items():
            blob = git("hash-object", "-w", "--stdin", input=content).stdout.strip()
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env).stdout.strip()
        return git("commit-tree", tree, "-m", message, *(["-p", parent] if parent else [])).stdout.strip()


def transact(mutate, message: str):
    """Read the latest board, apply `mutate(board) -> {path: text}`, push; retry if beaten.
    `mutate` may raise CoordError to refuse; it sees a fresh board on every attempt."""
    for attempt in range(10):
        warn = fetch()
        if warn:
            raise CoordError(warn.replace("; showing the last fetched board", ""))
        parent = board_head()
        board = read_board(parent)
        changes = mutate(board)
        commit = make_commit(parent, changes, message)
        r = git("push", "--quiet", REMOTE, f"{commit}:refs/heads/{BRANCH}", check=False, timeout=30)
        if r.returncode == 0:
            git("update-ref", REF, commit)
            stamp_file().touch()
            return board
        if any(s in r.stderr for s in ("rejected", "non-fast-forward", "fetch first", "stale info")):
            time.sleep(0.2 + random.random() * 0.8 * (attempt + 1))
            continue
        raise CoordError(f"push to the board failed: {r.stderr.strip()[:300]}")
    raise CoordError("the board kept changing under us; try again")


# ---------------------------------------------------------------- model

def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def me() -> str:
    for name in (AS_NAME, os.environ.get("COORD_NAME", ""),
                 git("config", "coord.name", check=False).stdout.strip(),
                 git("config", "user.name", check=False).stdout.strip(),
                 os.environ.get("USER", "unknown")):
        if name:
            return name
    return "unknown"


def agent_label() -> str:
    label = os.environ.get("COORD_AGENT", "")
    host = socket.gethostname().split(".")[0]
    return f"{host}/{label}" if label else host


def state(c: dict, t: dt.datetime | None = None) -> str:
    """open (posted, not taken), active, stale (taken but expired), done or released."""
    if c.get("state") in ("open", "done", "released"):
        return c["state"]
    return "stale" if parse(c["expires_at"]) <= (t or now()) else "active"


def norm_path(p: str) -> str:
    p = p.strip().replace("\\", "/")
    if os.path.isabs(p):
        p = os.path.relpath(os.path.realpath(p), os.path.realpath(ROOT))
    p = os.path.normpath(p).replace("\\", "/")
    if p in ("", ".") or p == ".." or p.startswith("../"):
        raise CoordError(f"path {p!r} must be inside the repo, and not the whole repo")
    return p.rstrip("/")


def check_paths(paths: list, broad: bool) -> list:
    paths = [norm_path(p) for p in paths]
    for p in paths:
        if "/" not in p and (ROOT / p).is_dir() and not broad:
            raise CoordError(f"'{p}' is a whole top-level folder, which would block everyone. Name the "
                             f"subfolders or files the work edits, or pass --broad if you mean it.")
    return paths


def overlaps(a: str, b: str) -> bool:
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def holders(board: dict, paths: list, who: str, skip_id: str = "") -> list:
    """(path, task) pairs: active tasks held by someone other than `who` touching `paths`."""
    hits = []
    for c in board["tasks"].values():
        if c["id"] == skip_id or c.get("owner") == who or state(c) != "active":
            continue
        for p in paths:
            if any(overlaps(p, q) for q in c.get("paths", [])):
                hits.append((p, c))
    return hits


def span(s: int) -> str:
    s = abs(int(s))
    if s < 90:
        return f"{s}s"
    if s < 5400:
        return f"{s // 60}m"
    if s < 48 * 3600:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    return f"{s // 86400}d"


def ago(t: str) -> str:
    return span((now() - parse(t)).total_seconds()) + " ago"


def task_file(cid: str) -> str:
    return f"tasks/{cid}.json"


def dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def valid_id(cid: str) -> str:
    if not ID_RE.fullmatch(cid):
        raise CoordError("ID: lowercase letters, digits, '.', '_' or '-', starting with a letter or digit")
    return cid


def log(c: dict, who: str, t: dt.datetime, text: str) -> None:
    c.setdefault("log", []).append({"at": iso(t), "by": who, "text": text})
    c["updated_at"] = iso(t)


def start(c: dict, who: str, t: dt.datetime, hours: float) -> None:
    c.update(owner=who, agent=agent_label(), state="active", claimed_at=iso(t),
             expires_at=iso(t + dt.timedelta(hours=hours)))


def refuse_overlap(board: dict, c: dict, who: str, force: bool) -> None:
    hits = holders(board, c.get("paths", []), who, c["id"])
    if hits and not force:
        lines = "\n".join(f"  {p}  <- '{h['id']}' held by {h['owner']}: {h['title']}" for p, h in hits)
        raise CoordError(f"'{c['id']}' would edit paths someone else holds:\n{lines}\n"
                         f"Wait, ask them, or --force.")
    if hits:
        log(c, who, now(), "forced overlap with " + ", ".join(sorted({h["id"] for _, h in hits})))


# ---------------------------------------------------------------- commands

def cmd_post(a) -> None:
    cid, who, paths = valid_id(a.id), me(), check_paths(a.paths, a.broad)

    def mutate(board):
        t, old = now(), board["tasks"].get(a.id)
        if old and state(old, t) == "active" and not a.force:
            raise CoordError(f"'{cid}' is being worked on by {old['owner']}; post a new ID or --force")
        c = {"id": cid, "title": a.title, "details": a.details or "", "posted_by": who,
             "assignee": a.assignee or "", "priority": a.priority, "paths": paths, "cmd": a.cmd or "",
             "compute": a.compute or "", "state": "open", "owner": "", "agent": "", "posted_at": iso(t),
             "claimed_at": "", "expires_at": "", "result": "", "log": (old or {}).get("log", [])}
        log(c, who, t, ("re-posted" if old else "posted") + (f" for {a.assignee}" if a.assignee else ""))
        return {task_file(cid): dump(c)}

    transact(mutate, f"post {cid} ({who}): {a.title}")
    print(f"posted '{cid}'" + (f" for {a.assignee}" if a.assignee else " (anyone may take it)"))


def cmd_assign(a) -> None:
    def fn(c, who, t):
        if state(c, t) != "open":
            raise CoordError(f"'{c['id']}' is {state(c, t)}; only open tasks can be reassigned")
        c["assignee"] = a.name
        log(c, who, t, f"assigned to {a.name or 'anyone'}")
    update(a.id, fn, f"assign {a.id} -> {a.name or 'anyone'}", owner_only=False)
    print(f"'{a.id}' assigned to {a.name or 'anyone'}")


def pick(board: dict, who: str, t: dt.datetime) -> dict | None:
    """The best posted task for `who` that is open or stale: assigned to them first, then by
    priority, then age. Someone's own expired claim is never picked automatically."""
    ready = [c for c in board["tasks"].values()
             if c.get("posted_by") and state(c, t) in ("open", "stale") and c.get("assignee", "") in ("", who)
             and not holders(board, c.get("paths", []), who, c["id"])]
    ready.sort(key=lambda c: (c.get("assignee") != who, -c.get("priority", 0), c.get("posted_at", "")))
    return ready[0] if ready else None


def cmd_take(a) -> None:
    who, taken = me(), {}

    def mutate(board):
        t = now()
        if a.id:
            c = board["tasks"].get(a.id)
            if not c:
                raise CoordError(f"no task '{a.id}' on the board")
            st = state(c, t)
            if st == "active":
                raise CoordError(f"'{a.id}' is already being worked on by {c['owner']}" +
                                 (" (you)" if c["owner"] == who else ""))
            if st == "done" and not a.force:
                raise CoordError(f"'{a.id}' is done: {c.get('result', '')}")
            if c.get("assignee") not in ("", who) and not a.force:
                raise CoordError(f"'{a.id}' is assigned to {c['assignee']}; --force to take it anyway")
        else:
            c = pick(board, who, t)
            if not c:
                raise CoordError("no open task for you right now (status shows the board)")
        if state(c, t) == "stale":
            log(c, who, t, f"took over from {c['owner']} (expired)")
        refuse_overlap(board, c, who, a.force)
        start(c, who, t, a.hours)
        log(c, who, t, "taken")
        taken["c"] = c
        return {task_file(c["id"]): dump(c)}

    transact(mutate, f"take {a.id or '(next)'} ({who})")
    c = taken["c"]
    print(f"took '{c['id']}' for {a.hours:g}h: {c['title']}")
    for k in ("details", "cmd", "compute"):
        if c.get(k):
            print(f"  {k}: {c[k]}")
    if c.get("paths"):
        print("  paths: " + ", ".join(c["paths"]))


def cmd_claim(a) -> None:
    cid, who, paths = valid_id(a.id), me(), check_paths(a.paths, a.broad)

    def mutate(board):
        t, old = now(), board["tasks"].get(cid)
        if old and state(old, t) == "open":
            raise CoordError(f"'{cid}' is a posted task: use `take {cid}`")
        if old and state(old, t) == "active":
            raise CoordError(f"'{cid}' is held by {old['owner']} ({old['agent']}) until {old['expires_at']}"
                             + (" (it's yours: use renew)" if old["owner"] == who else f": {old['title']}"))
        c = {"id": cid, "title": a.title, "details": a.details or "", "posted_by": "", "assignee": "",
             "priority": 0, "paths": paths, "cmd": a.cmd or "", "compute": a.compute or "",
             "posted_at": "", "result": "", "log": (old or {}).get("log", [])}
        if old:
            log(c, who, t, f"took over from {old['owner']} ({state(old, t)})")
        refuse_overlap(board, c, who, a.force)
        start(c, who, t, a.hours)
        log(c, who, t, "claimed")
        return {task_file(cid): dump(c)}

    transact(mutate, f"claim {cid} ({who}): {a.title}")
    print(f"claimed '{cid}' for {a.hours:g}h" + (f", holding {', '.join(paths)}" if paths else ""))


def update(cid: str, fn, message: str, owner_only: bool = True, force: bool = False) -> dict:
    who, out = me(), {}

    def mutate(board):
        c = board["tasks"].get(cid)
        if not c:
            raise CoordError(f"no task '{cid}' on the board")
        if owner_only and c.get("owner") != who and not force:
            raise CoordError(f"'{cid}' is held by {c.get('owner') or 'nobody'}, not {who} (--force to override)")
        fn(c, who, now())
        out["c"] = c
        return {task_file(cid): dump(c)}

    transact(mutate, f"{message} ({who})")
    return out["c"]


def cmd_renew(a) -> None:
    def fn(c, who, t):
        if state(c, t) in ("open", "done", "released"):
            raise CoordError(f"'{c['id']}' is {state(c, t)}; take or claim it instead")
        c["expires_at"] = iso(t + dt.timedelta(hours=a.hours))
        log(c, who, t, f"renewed {a.hours:g}h")
    c = update(a.id, fn, f"renew {a.id}", force=a.force)
    print(f"'{a.id}' now expires {c['expires_at']}")


def cmd_done(a) -> None:
    def fn(c, who, t):
        c["state"], c["result"] = "done", a.result
        log(c, who, t, "done: " + a.result)
    update(a.id, fn, f"done {a.id}: {a.result[:60]}", force=a.force)
    print(f"'{a.id}' marked done")


def cmd_release(a) -> None:
    def fn(c, who, t):
        back = bool(c.get("posted_by")) and not a.drop
        c["state"] = "open" if back else "released"
        if back:
            c.update(owner="", agent="", expires_at="", claimed_at="")
        log(c, who, t, ("returned to the queue" if back else "released") + (": " + a.why if a.why else ""))
    c = update(a.id, fn, f"release {a.id}", force=a.force)
    print(f"'{a.id}' " + ("is back in the queue" if c["state"] == "open" else "released"))


def cmd_note(a) -> None:
    who, posted = me(), {}

    def mutate(board):
        t = now()
        words = list(a.words)
        cid = words.pop(0) if len(words) >= 2 and words[0] in board["tasks"] else ""
        text = " ".join(words).strip()
        if not text:
            raise CoordError("nothing to say")
        changes = {}
        if cid:
            c = board["tasks"][cid]
            log(c, who, t, text)
            changes[task_file(cid)] = dump(c)
        slug = re.sub(r"[^a-z0-9]+", "-", who.lower()).strip("-") or "x"
        name = f"notes/{t.strftime('%Y%m%dT%H%M%SZ')}-{slug}-{random.randrange(16 ** 4):04x}.json"
        changes[name] = dump({"at": iso(t), "by": who, "agent": agent_label(), "task": cid, "text": text,
                              "pin": a.pin})
        posted["cid"] = cid
        return changes

    transact(mutate, f"note ({who}): {' '.join(a.words)[:60]}")
    print("pinned" if a.pin else "posted" + (f" on '{posted['cid']}'" if posted["cid"] else ""))


def render(board: dict, warn: str, show_all: bool, brief: bool) -> str:
    t, you = now(), me()
    tasks = list(board["tasks"].values())
    by = {k: [c for c in tasks if state(c, t) == k] for k in ("open", "active", "stale", "done", "released")}
    head = (board["commit"] or "")[:7] or "empty"
    lines = [f"TASK BOARD ({REMOTE}/{BRANCH} @ {head})   you: {you}   {iso(t)}"]
    if warn:
        lines.append(f"  ! {warn}")
    if not tasks and not board["notes"]:
        lines.append("  (empty) Nothing posted or claimed yet.")

    def row(c, extra=""):
        who = c.get("owner") or (f"for {c['assignee']}" if c.get("assignee") else "anyone")
        mark = " <- YOU" if you in (c.get("owner"), c.get("assignee")) else ""
        out = [f"  {c['id']:<26} {who}{extra}{mark}", f"      {c['title']}"]
        if c.get("paths"):
            out.append("      paths: " + ", ".join(c["paths"]))
        if not brief:
            for k in ("details", "cmd", "compute"):
                if c.get(k):
                    out.append(f"      {k}: {c[k]}")
        if c.get("result"):
            out.append("      result: " + c["result"])
        notes = [l for l in c.get("log", []) if l["text"] not in ("taken", "claimed", "posted")
                 and not l["text"].startswith(("done:", "renewed", "posted for", "re-posted"))]
        if notes and not brief:
            n = notes[-1]
            out.append(f"      last: {n['text']}  ({n['by']}, {ago(n['at'])})")
        return out

    pins = [n for n in board["notes"] if n.get("pin")][-5:]
    if pins:
        lines.append("PINNED")
        for n in reversed(pins):
            lines.append(f"  {n['text']}  ({n['by']}, {ago(n['at'])})")
    if by["open"]:
        lines.append("OPEN TASKS (take with `take ID`, or `take` for the best one for you)")
        for c in sorted(by["open"], key=lambda c: (-c.get("priority", 0), c.get("posted_at", ""))):
            lines += row(c, f"   p{c.get('priority', 0)}, posted by {c.get('posted_by')} {ago(c['posted_at'])}")
    if by["active"]:
        lines.append("IN PROGRESS (their paths are off-limits to everyone else)")
        for c in sorted(by["active"], key=lambda c: c["expires_at"]):
            lines += row(c, f" @ {c['agent']}, expires in {span((parse(c['expires_at']) - t).total_seconds())}")
    if by["stale"]:
        lines.append("STALE (expired: anyone may take it over)")
        for c in by["stale"]:
            lines += row(c, f" @ {c['agent']}, expired {ago(c['expires_at'])}")
    recent = [c for c in by["done"] + by["released"]
              if show_all or (t - parse(c["updated_at"])).total_seconds() < DONE_SHOWN_H * 3600]
    if recent:
        lines.append("FINISHED" + ("" if show_all else f" (last {DONE_SHOWN_H}h; --all for everything)"))
        for c in sorted(recent, key=lambda c: c["updated_at"], reverse=True)[: (5 if brief else None)]:
            lines += row(c, f"   {c['state']} {ago(c['updated_at'])}")
    notes = [n for n in board["notes"] if not n.get("pin")][-(4 if brief else 12):]
    if notes:
        lines.append("RECENT CHECK-INS")
        for n in reversed(notes):
            on = f" [{n['task']}]" if n.get("task") else ""
            lines.append(f"  {ago(n['at']):>9}  {n['by']}{on}: {n['text']}")
    return "\n".join(lines)


def cmd_status(a) -> None:
    warn = fetch(max_age=FETCH_TTL_S if a.cached else 0)
    board = read_board(board_head())
    print(json.dumps(board, indent=2) if a.json else render(board, warn, a.all, a.brief))


def cmd_check(a) -> int:
    fetch(max_age=FETCH_TTL_S, timeout=8)
    hits = holders(read_board(board_head()), [norm_path(p) for p in a.paths], me())
    for p, c in hits:
        print(f"{p} is held by {c['owner']} ('{c['id']}': {c['title']}) until {c['expires_at']}", file=sys.stderr)
    return 2 if hits else 0


def cmd_whoami(a) -> None:
    if a.set:
        git("config", "coord.name", a.set)
    print(f"{me()} @ {agent_label()}")


PROTOCOL = ("Board protocol (AGENTS.md, 'Working in parallel'): take a posted task or claim your own work "
            "with its --paths BEFORE editing files or launching an eval/training run; check in with `note`; "
            "finish with `done --result`. Never edit paths another agent holds. "
            "Commands: python3 coord/coord.py status|take|claim|note|renew|done|release")


def cmd_hook_session(a) -> None:
    """SessionStart hook: put the board in the agent's context. Never fails the session."""
    try:
        warn = fetch(timeout=10)
        print(render(read_board(board_head()), warn, False, True))
        print(PROTOCOL)
    except Exception as e:  # noqa: BLE001
        print(f"(task board unavailable: {e}) {PROTOCOL}")


def cmd_hook_edit(a) -> int:
    """PreToolUse hook for Edit/Write/NotebookEdit: block edits to paths another agent holds."""
    try:
        ti = json.load(sys.stdin).get("tool_input") or {}
        path = ti.get("file_path") or ti.get("notebook_path")
        if not path:
            return 0
        real, root = os.path.realpath(path), os.path.realpath(ROOT)
        if not real.startswith(root + os.sep):
            return 0
        rel = os.path.relpath(real, root).replace("\\", "/")
        fetch(max_age=FETCH_TTL_S, timeout=8)
        hits = holders(read_board(board_head()), [rel], me())
        if not hits:
            return 0
        c = hits[0][1]
        print(f"Blocked by the task board: {rel} is held by {c['owner']} ({c['agent']}) for '{c['id']}' "
              f"until {c['expires_at']}: {c['title']}. Editing it now risks a merge conflict. Run "
              f"`python3 coord/coord.py status` and pick other work, or post a note asking {c['owner']} "
              f"to release it.", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 - a broken hook must never stop work
        return 0


def main(argv=None) -> int:
    global AS_NAME
    p = argparse.ArgumentParser(prog="coord.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--as", dest="as_name", default="", help="act as this agent name for one command")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("status", help="show the board")
    s.add_argument("--all", action="store_true", help="include old finished tasks")
    s.add_argument("--brief", action="store_true")
    s.add_argument("--json", action="store_true")
    s.add_argument("--cached", action="store_true", help=f"skip the fetch if one ran in the last {FETCH_TTL_S}s")

    def work_args(s, hours=True):
        s.add_argument("--paths", nargs="*", default=[], help="repo paths the work edits (held while active)")
        s.add_argument("--cmd", help="the command to run, so nobody repeats it")
        s.add_argument("--compute", help="where it runs, e.g. 'modal 40x4cpu' or 'mac'")
        s.add_argument("--details", help="anything the worker needs to know")
        s.add_argument("--broad", action="store_true", help="allow a whole top-level folder in --paths")
        s.add_argument("--force", action="store_true")

    s = sub.add_parser("post", help="(manager) post a task to the queue")
    s.add_argument("id")
    s.add_argument("title")
    s.add_argument("--for", dest="assignee", default="", help="only this agent should take it")
    s.add_argument("--priority", type=int, default=1, help="higher is taken first (default 1)")
    work_args(s)
    s = sub.add_parser("assign", help="(manager) reassign an open task; '' = anyone")
    s.add_argument("id")
    s.add_argument("name")
    s = sub.add_parser("take", help="take a posted task (no ID: the best one for you)")
    s.add_argument("id", nargs="?")
    s.add_argument("--hours", type=float, default=4.0, help="expiry; renew while working (default 4)")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("claim", help="claim self-started work and the paths it edits")
    s.add_argument("id")
    s.add_argument("title")
    s.add_argument("--hours", type=float, default=4.0, help="expiry; renew while working (default 4)")
    work_args(s)
    for name, helptext in (("renew", "extend your task"), ("done", "finish with a result"),
                           ("release", "give it up (a posted task returns to the queue)")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("id")
        s.add_argument("--force", action="store_true", help="act on someone else's task")
        if name == "renew":
            s.add_argument("--hours", type=float, default=4.0)
        if name == "done":
            s.add_argument("--result", required=True, help="one line: what came out of it, and where")
        if name == "release":
            s.add_argument("--why", default="")
            s.add_argument("--drop", action="store_true", help="don't return a posted task to the queue")
    s = sub.add_parser("note", help="check in: note [ID] TEXT, or note --pin TEXT for direction")
    s.add_argument("words", nargs="+")
    s.add_argument("--pin", action="store_true", help="pin it to the top of the board")
    s = sub.add_parser("check", help="exit 2 if another agent holds any of these paths")
    s.add_argument("paths", nargs="+")
    s = sub.add_parser("whoami", help="your board name")
    s.add_argument("--set", help="set it for this clone (git config coord.name)")
    sub.add_parser("hook-session", help=argparse.SUPPRESS)
    sub.add_parser("hook-edit", help=argparse.SUPPRESS)

    a = p.parse_args(argv)
    AS_NAME = a.as_name
    handlers = {"status": cmd_status, "post": cmd_post, "assign": cmd_assign, "take": cmd_take,
                "claim": cmd_claim, "renew": cmd_renew, "done": cmd_done, "release": cmd_release,
                "note": cmd_note, "check": cmd_check, "whoami": cmd_whoami,
                "hook-session": cmd_hook_session, "hook-edit": cmd_hook_edit}
    try:
        return handlers[a.command](a) or 0
    except CoordError as e:
        print(f"coord: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
