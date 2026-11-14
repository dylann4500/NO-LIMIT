#!/usr/bin/env python3
"""The schedule and the reminders. One clock for both sessions; a human starts the daemon in its own terminal tab.

  python3 scripts/clock.py start [now|HH:MM[:SS]] [--scale S]   minute 0 ("2:05" typed at 14:07 means 14:05)
  python3 scripts/clock.py format [--build 60] [--gap 20] [--scored 6] [--scale S]
  python3 scripts/clock.py pin scored3 15:40      a round's real time: it and the later rounds move (also
  python3 scripts/clock.py pin practice5 15:30    round3, r3, round2.5, p5); minute 0 and the past don't
  python3 scripts/clock.py show                   minute 0, every round's time, the next steps (= state/clock.md)
  python3 scripts/clock.py reset                  clears the clock (schedule, sent steps, cut-offs)
  python3 scripts/clock.py run [--scale S]        the daemon (scale < 1 only for rehearsals: 1 event-minute
                                                  = S*60 real seconds)
  python3 scripts/clock.py pre builder|research   the pre-event research tasks ("start the research")

Model (as in hub.py): scored rounds at minute `build`, then every `gap`; practices 1-4 at minutes 20/30/40/50
counted back from scored round 1; one practice 10 event-minutes before each later scored round. A scored round's
real start (from the portal, or `pin`) moves it and every later round. The daemon posts each step of
scripts/timeline.json ONCE to the right inbox, prints the humans' steps loudly here (with a bell), keeps
state/clock.md current, pins scored rounds the portal saw start off-schedule, holds a window whose previous round
hasn't started, and judges the cut-offs from files. Cut-offs change WHAT we do when a step runs late, never how
carefully: nobody is told to hurry.
State: state/schedule.json, state/clock_sent.json, state/clock_guard.json, state/clock.md.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from say import post  # noqa: E402

DEFAULTS = {"build": 60, "gap": 20, "scored": 6, "scale": 1.0}
EARLY = ("b0", "b10", "b15")      # build steps that still fire when minute 0 is set late
SHAPE = ("start", "build", "gap", "scored", "scale", "round_at")


# ------------------------------------------------------------------ files
def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def write_text(path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_json(path, obj) -> None:
    write_text(path, json.dumps(obj, indent=1))


def sp(root, name: str) -> Path:
    return Path(root) / "state" / name


class Lock:
    """Serialises read-modify-write of the clock's state between the daemon and the commands."""

    def __init__(self, root, name=".clock.lock"):
        self.path = sp(root, name)

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        finally:
            self.f.close()


# ------------------------------------------------------------------ small helpers
def hhmm(t) -> str:
    return time.strftime("%H:%M", time.localtime(t)) if t else "--:--"


def hms(t) -> str:
    return time.strftime("%H:%M:%S", time.localtime(t)) if t else "--:--:--"


def num(x) -> str:
    return f"{float(x):g}"


def norm_bot(x) -> str:
    """'releases/v3.zip', 'v3 (1).zip' (a browser's second download) -> 'v3'."""
    return re.sub(r"\s*\(\d+\)$", "", re.sub(r"\.zip$", "", str(x or "").strip().split("/")[-1].lower()).strip())


def same_bot(a, b) -> bool:
    return bool(norm_bot(a)) and norm_bot(a) == norm_bot(b)


def norm_stage(t) -> str:
    """'Practice-1', 'practice 1', 'round2.5', 'R2', '05-round-2' -> 'Practice 1', 'Round 2.5', 'Round 2'."""
    m = re.search(r"(practice|round|r)\W*(\d+(?:\.5)?)(?![\d.])", str(t or ""), re.I)
    if not m:
        return str(t or "").strip()
    return ("Practice " if m.group(1).lower() == "practice" else "Round ") + m.group(2)


def stage_slug(stage: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", str(stage)).strip("-")


def stage_of_round(kind: str, n: int) -> str:
    if kind == "practice":
        return f"Practice {n}" if n <= 4 else f"Round {n - 4}.5"
    return f"Round {n}"


def event_label(kind: str, n: int) -> str:
    if kind == "scored":
        return f"Scored round {n}"
    return f"Practice {n}" if n <= 4 else f"Practice {n} (Round {n - 4}.5)"


def parse_clock_time(text: str, now: float | None = None, ref: float | None = None) -> float:
    """'now', 'HH:MM', 'HH:MM:SS', '2:05pm'. Without am/pm, '2:05' is the reading closest to now (14:05 in the
    afternoon), or to `ref` when given (a pinned round: closest to its scheduled time); yesterday and tomorrow count
    too (00:05 typed at 23:58 is in 7 minutes)."""
    now = time.time() if now is None else now
    t = str(text or "").strip().lower().replace(" ", "")
    if t in ("", "now"):
        return now
    near = now if ref is None else ref
    m = re.fullmatch(r"(\d{1,2})[:.h](\d{2})(?::(\d{2}))?(am|pm)?", t)
    if not m:
        raise ValueError(f"can't read the time {text!r}: use now, HH:MM or HH:MM:SS (24-hour; 2:05 = closest to now)")
    h, mi, se, ap = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), m.group(4)
    if h > 23 or mi > 59 or se > 59 or (ap and not 1 <= h <= 12):
        raise ValueError(f"not a time: {text!r}")
    hours = [h % 12 + (12 if ap == "pm" else 0)] if ap else ([h, h + 12] if h < 12 else [h])
    lt = time.localtime(near)
    cands = [time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday + d, hh, mi, se, 0, 0, -1)) for d in (-1, 0, 1) for hh in hours]
    return min(cands, key=lambda c: abs(c - near))


# ------------------------------------------------------------------ schedule maths (ported from hub.py)
def started(s) -> bool:
    return bool(s) and s.get("start") is not None


def unit(s) -> float:
    """Real seconds per event-minute (less than 60 only in sped-up rehearsals)."""
    return 60.0 * float((s or {}).get("scale") or 1.0)


def round_starts(s) -> list:
    """When each scored round starts: minute `build`, then every `gap`; a pinned round (s['round_at']) and the
    rounds after it follow from its real time."""
    if not started(s):
        return []
    U, t0 = unit(s), float(s["start"])
    B, G = float(s.get("build", 60)), float(s.get("gap", 20))
    pins = {}
    for k, v in (s.get("round_at") or {}).items():
        try:
            pins[int(k)] = float(v)
        except (TypeError, ValueError):
            pass
    out: list = []
    for k in range(1, int(s.get("scored", 6)) + 1):
        out.append(pins[k] if k in pins else (out[-1] + G * U if out else t0 + B * U))
    return out


def round_ts(s, k: int):
    r = round_starts(s)
    return r[k - 1] if 1 <= k <= len(r) else None


def build_ts(s, mi: float) -> float:
    """A build-hour mark: minutes 0-15 count from minute 0; minute 16 on counts back from scored round 1, so a longer
    build or a late round 1 moves the practice rounds with it."""
    return float(s["start"]) + mi * unit(s) if mi < 16 else round_starts(s)[0] - (60 - mi) * unit(s)


def practice_ts(s, k: int):
    """The practice round in the window before scored round k+1 (10 event-minutes before it)."""
    nxt = round_ts(s, k + 1)
    return nxt - 10 * unit(s) if nxt else None


def events(s) -> list:
    """[(kind, n, ts)]: practices 1-4 in the build, scored round k, practice 4+k before scored round k+1."""
    if not started(s):
        return []
    out = [("practice", n, build_ts(s, mi)) for n, mi in enumerate((20, 30, 40, 50), 1)]
    rs = round_starts(s)
    for k, ts in enumerate(rs, 1):
        out.append(("scored", k, ts))
        if k < len(rs):
            out.append(("practice", 4 + k, rs[k] - 10 * unit(s)))
    return sorted(out, key=lambda e: e[2])


def stage_of(s, t: float) -> str:
    """The stage at time t: Build, Practice 1-4, Round k, Round k.5 (the practice after scored round k)."""
    if not started(s) or t < float(s["start"]):
        return "Before the start"
    rs = round_starts(s)
    if not rs or t < rs[0]:
        p = [build_ts(s, mi) for mi in (20, 30, 40, 50)]
        return "Build" if t < p[0] else f"Practice {sum(1 for x in p if x <= t)}"
    k = sum(1 for x in rs if x <= t)
    if k >= len(rs):
        return f"Round {len(rs)}"
    return f"Round {k}.5" if t >= rs[k] - 10 * unit(s) else f"Round {k}"


def expected_start(s, stage: str):
    """When the clock expects a stage's round to start (Practice 1-4, Round k, Round k.5)."""
    st = norm_stage(stage)
    m = re.fullmatch(r"Practice (\d+)", st)
    if m:
        n = int(m.group(1))
        return build_ts(s, 10 + 10 * n) if 1 <= n <= 4 else None
    m = re.fullmatch(r"Round (\d+)(\.5)?", st)
    if m:
        k = int(m.group(1))
        return practice_ts(s, k) if m.group(2) else round_ts(s, k)
    return None


def pin(s: dict, k: int, when: float) -> dict:
    """Scored round k really starts at `when`; later rounds follow from it (their own pins are dropped)."""
    s = dict(s)
    pins = {kk: v for kk, v in (s.get("round_at") or {}).items() if int(kk) < k}
    pins[str(k)] = float(when)
    s["round_at"], s["at"] = pins, time.time()
    return s


def same_shape(a, b) -> bool:
    if not started(a) or not started(b):
        return started(a) == started(b)
    if int(float(a["start"])) != int(float(b["start"])):
        return False
    for f in SHAPE[1:]:
        va, vb = a.get(f, DEFAULTS.get(f)), b.get(f, DEFAULTS.get(f))
        if f == "round_at":
            va = {str(k): round(float(v), 1) for k, v in (va or {}).items()}
            vb = {str(k): round(float(v), 1) for k, v in (vb or {}).items()}
        elif va is not None and vb is not None:
            va, vb = float(va), float(vb)
        if va != vb:
            return False
    return True


# ------------------------------------------------------------------ timeline (scripts/timeline.json)
_TL_CACHE: dict = {}


def load_timeline(root=None) -> dict:
    """The steps file; a broken edit keeps the last good copy (and says so once)."""
    path = Path(root or ROOT) / "scripts" / "timeline.json"
    if not path.exists():
        path = HERE / "timeline.json"
    try:
        mt = path.stat().st_mtime
        if _TL_CACHE.get("path") == str(path) and _TL_CACHE.get("mtime") == mt:
            return _TL_CACHE["tl"]
        tl = json.loads(path.read_text())
        for st in tl.get("steps", []) + tl.get("human", []):
            parse_when(st["when"])
        for st in tl.get("steps", []):
            if st.get("to") not in ("builder", "research", "both"):
                raise ValueError(f"step {st.get('when')}: 'to' must be builder, research or both")
        _TL_CACHE.update(path=str(path), mtime=mt, tl=tl)
        return tl
    except (OSError, ValueError, KeyError, TypeError) as e:
        if _TL_CACHE.get("err") != str(e):
            _TL_CACHE["err"] = str(e)
            print(f"[clock] WARNING: {path} can't be used ({e}); keeping the last good copy", flush=True)
        return _TL_CACHE.get("tl") or {"steps": [], "human": [], "pre": []}


def parse_when(w) -> tuple:
    m = re.fullmatch(r"\s*([bBtT])\s*-?\s*(\d+)\s*", str(w))
    if not m:
        raise ValueError(f"bad 'when': {w!r} (use b<minute> or T<minutes before>)")
    return m.group(1).lower(), int(m.group(2))


def marks(s, tl) -> list:
    """Every clock mark: {'key': 'b20' | 's3-13', 'at', 'kind', ...}, in time order."""
    if not started(s):
        return []
    U, rs = unit(s), round_starts(s)
    bm, tm = set(), set()
    for st in tl.get("steps", []) + tl.get("human", []):
        kind, n = parse_when(st["when"])
        (bm if kind == "b" else tm).add(n)
    out = [{"key": f"b{mi}", "at": build_ts(s, mi), "kind": "b", "mi": mi} for mi in sorted(bm)]
    for k, ts in enumerate(rs, 1):
        for o in sorted(tm, reverse=True):
            if k == 1 and o > 9:
                continue   # round 1: the build hour covers T-20..T-10
            if k > 1 and ts - o * U < rs[k - 2] - 1e-6:
                continue   # before the previous round even starts (a short gap)
            out.append({"key": f"s{k}-{o}", "at": ts - o * U, "kind": "T", "k": k, "o": o, "ts": ts})
    return sorted(out, key=lambda m: (m["at"], m["key"]))


def carry(sent: set, old, new, now: float, tl) -> set:
    """The schedule moved (hub.py's Clock.carry). A step already sent stays sent only if it is the same occurrence
    (moved 5 event-minutes or less) or its new time is already over; a step now in the future fires at its new time;
    a long-past step that never fired doesn't fire now (no burst). A false start corrected later still gets the real
    minute 0."""
    if not started(old) or not started(new) or same_shape(old, new):
        return set(sent)
    otk, ntk, U = int(float(old["start"])), int(float(new["start"])), unit(new)
    ot = {m["key"]: m["at"] for m in marks(old, tl)}
    out = set(sent)
    for m in marks(new, tl):
        step, t_new = m["key"], m["at"]
        was = f"{otk}:{step}" in out
        moved = t_new - ot.get(step, t_new)
        premature = step in EARLY and moved > 5 * U   # sent at a false start: the real one still fires
        if was and not premature and (abs(moved) <= 5 * U or t_new < now - U):
            out.add(f"{ntk}:{step}")
        elif not was and t_new < now - U and step not in EARLY:
            out.add(f"{ntk}:{step}")
        elif was and t_new >= now - U and otk == ntk:
            out.discard(f"{ntk}:{step}")   # a pinned round moved this step later: it fires again at its new time
    return out


# ------------------------------------------------------------------ what the portal watcher saw
def read_seen(root) -> dict:
    """state/rounds_seen.json -> {stage: {'at', 'exact', ...}} (the portal watcher writes it)."""
    d = load_json(sp(root, "rounds_seen.json"), {})
    r = d.get("rounds") if isinstance(d, dict) else None
    return r if isinstance(r, dict) else {}


def portal_active(root, now=None):
    """(filename or None, known?) from the portal watcher's state; unknown if it hasn't answered for 3 minutes."""
    now = time.time() if now is None else now
    st = load_json(sp(root, "portal.json"), {})
    ok = st.get("last_ok") or 0
    if not ok or now - ok > 180:
        return None, False
    return (st.get("active") or {}).get("filename"), True


def live_bot(root):
    live = load_json(sp(root, "live.json"), None)
    return live if isinstance(live, dict) and live.get("bot") else None


def held(s, k: int, seen: dict, now: float) -> bool:
    """Window k waits while round k-1 hasn't been seen starting 3 event-minutes after its time (only when the
    portal watcher is reporting rounds at all)."""
    if k <= 1 or not seen or f"Round {k - 1}" in seen:
        return False
    t = round_ts(s, k - 1)
    return t is not None and now > t + 3 * unit(s)


def autopin(s, seen: dict, now: float):
    """A scored round the portal saw start more than 90 s (1.5 event-min; at least 45 s in fast rehearsals) off the
    schedule: pin its real start, so later rounds and deadlines follow. Returns (schedule, [messages])."""
    U = unit(s)
    thr = max(1.5 * U, 45.0)
    auto = dict(s.get("auto_pinned") or {})
    for k, ts in enumerate(round_starts(s), 1):
        e = seen.get(f"Round {k}")
        if not isinstance(e, dict) or not e.get("exact") or not e.get("at"):
            continue
        at = float(e["at"])
        if abs(float(auto.get(str(k), -1e18)) - at) < 1:
            continue   # already pinned to this sighting (a later human pin stands)
        if thr < abs(at - ts) < 45 * U:
            new = pin(s, k, at)
            new["auto_pinned"] = dict(auto, **{str(k): at})
            later = [f"round {i} {hhmm(t)}" for i, t in enumerate(round_starts(new), 1) if i > k]
            msg = (f"scored round {k} really started at {hhmm(at)} (the clock had {hhmm(ts)}); later rounds and "
                   f"deadlines follow" + (": " + ", ".join(later) if later else "") + ". Times quoted earlier are out of date.")
            return new, [msg]
    return s, []


def drift_notes(s, seen: dict, sent: set) -> list:
    """The build's practice rounds (or a scored round too far off to pin) started minutes away from the clock:
    minute 0 or the format is probably wrong. [(sent key, message)], each once per minute 0."""
    U, out, tk = unit(s), [], int(float(s["start"]))
    for stage, e in seen.items():
        if not isinstance(e, dict) or not e.get("exact") or not e.get("at"):
            continue
        st = norm_stage(stage)
        exp = expected_start(s, st)
        if exp is None or not (re.fullmatch(r"Practice [1-4]", st) or re.fullmatch(r"Round \d+", st)):
            continue
        drift = float(e["at"]) - exp
        pinnable = st.startswith("Round") and abs(drift) < 45 * U
        key = f"{tk}:drift:{st}"
        if abs(drift) > max(180, 6 * U) and not pinnable and key not in sent:
            t0 = float(s["start"]) + drift
            out.append((key, f"{st} started at {hms(float(e['at']))} but the clock expected {hhmm(exp)}: the clock looks "
                             f"off by about {abs(drift) / U:.0f} event-min. If the portal is right and the format is right, "
                             f"minute 0 was {hms(t0)}: python3 scripts/clock.py start {hms(t0)} (or fix the format: "
                             "clock.py format --build N / --gap N). Every step and deadline moves with it."))
    return out


# ------------------------------------------------------------------ messages
class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def fmt(text: str, d: dict) -> str:
    try:
        return str(text).format_map(_Safe(d))
    except (ValueError, IndexError, AttributeError):
        return str(text)


def placeholders(s, m: dict, root) -> dict:
    U, rs = unit(s), round_starts(s)
    live = live_bot(root)
    d = {"r1": hhmm(rs[0]) if rs else "?", "live": (live or {}).get("bot") or "(none declared)"}
    for n, mi in enumerate((20, 30, 40, 50), 1):
        d[f"p{n}"] = hhmm(build_ts(s, mi))
    if m.get("kind") == "b":
        d["mi"] = m["mi"]
    else:
        k, ts = m["k"], m["ts"]
        d.update(k=k, prev=k - 1, ts=hhmm(ts), pt=hhmm(ts - 10 * U), t3=hhmm(ts - 3 * U), t5=hhmm(ts - 5 * U),
                 t8=hhmm(ts - 8 * U), t9=hhmm(ts - 9 * U))
    return d


def when_of(m: dict) -> str:
    """The timeline key of a mark: 'b20' or 't13' (as parse_when reads a step's 'when')."""
    return f"b{m['mi']}" if m["kind"] == "b" else f"t{m['o']}"


def step_messages(s, m: dict, tl, root) -> list:
    """[(to, text)] for one mark: one inbox line per step."""
    d, w, out = placeholders(s, m, root), when_of(m), []
    head = f"b{m['mi']} ({hhmm(m['at'])})" if m["kind"] == "b" else f"T-{m['o']} before scored round {m['k']} ({hhmm(m['ts'])})"
    for st in tl.get("steps", []):
        if "%s%d" % parse_when(st["when"]) != w:
            continue
        body = fmt(st.get("text", ""), d)
        tasks = [t for t in (st.get("tasks") or []) if isinstance(t, (list, tuple)) and len(t) == 2]
        if tasks:
            body += " TASKS: " + " ".join(f"({i}) {ag}: {fmt(t, d)}" for i, (ag, t) in enumerate(tasks, 1))
        out.append((st["to"], f"{head}: {body}"))
    return out


def human_lines(s, m: dict, tl, root, now: float) -> list:
    """[(text, loud)] the clock prints in its own terminal for the humans at this mark."""
    d, w, out = placeholders(s, m, root), when_of(m), []
    live = (live_bot(root) or {}).get("bot")
    act, known = portal_active(root, now)
    act_s = (act or "NO bot") if known else "unknown (the portal watcher isn't reporting)"
    for h in tl.get("human", []):
        if "%s%d" % parse_when(h["when"]) != w:
            continue
        who = {"dylan": "DYLAN", "samuel": "SAMUEL"}.get(str(h.get("who", "dylan")).lower(), "DYLAN + SAMUEL")
        kind, text = h.get("kind", "say"), fmt(h.get("text", ""), d)
        if kind == "practice":
            if live and not (known and same_bot(live, act)):
                line = (f"{who}: {text}. Make {live} active (click it if already uploaded, else upload releases/{live}.zip), "
                        f"unless BUILDER named another bot for this practice. The portal runs {act_s}.")
            else:
                line = (f"{who}: {text}. The portal runs {act_s}" + (" (= the declared bot)" if live else "") +
                        ". If BUILDER named another bot for this practice, activate it now; otherwise nothing to do.")
            out.append((line, True))
        elif kind == "live":
            if not live:
                out.append((f"{who}: {text}: no bot is declared yet (state/live.json): ask BUILDER which file. "
                            f"The portal runs {act_s}.", True))
            elif known and same_bot(live, act):
                out.append((f"{who}: {text}: the portal already runs {act} (the live bot). Nothing to do.", False))
            else:
                out.append((f"{who}: {text} — make {live} active (click it if already uploaded, else upload "
                            f"releases/{live}.zip). The portal runs {act_s}.", True))
        else:
            out.append((f"{who}: {text}", True))
    return out


def loud(text: str, now: float | None = None) -> None:
    bar = "=" * 78
    sys.stdout.write(f"\a\n{bar}\n>>> {hms(now or time.time())}  {text}\n{bar}\n\n")
    sys.stdout.flush()


def quiet(text: str, now: float | None = None) -> None:
    print(f"    {hms(now or time.time())}  {text}", flush=True)


# ------------------------------------------------------------------ cut-offs (hub.py's GUARD + DeadlineGuard)
# Cut-offs change WHAT we do when a step runs late, never HOW CAREFULLY. Before a cut-off only the owner session
# hears (to re-scope); at the cut-off it is told the pre-registered fallback. Nobody is told to hurry.
# (id, owner session, cut-off T-, heads-up T- or None, what, fallback, line for the humans or None)
GUARD = [
    ("data", "research", 10, None, "the previous scored round's results and hand data have landed (data/rounds/)",
     "no new data this window. The live bot plays with only changes already supported by earlier rounds (persistent "
     "leaks, validated LEDGER lines); analyst works from pooled earlier rounds; nothing waits for this data. When it "
     "lands it feeds the next window",
     "round data hadn't landed by T-10. The live bot plays with already-validated changes only."),
    ("card", "research", 8, None, "the round card is written (within 3 event-minutes of the data landing)",
     "stop fixing the card script. analyst computes the numbers the decision needs (the challenger's practice score vs "
     "the live bot's last comparable round, the top leak's size and z) with a one-off script, 3-minute cap; the card "
     "script gets fixed after T-3 for the next window", None),
    ("change", "research", 8, 10, "this window's one-change is recorded in notes/LEDGER.md ('one-change <stage>')",
     "no change from this window's new data goes into the live bot. Record what you have as a hypothesis with the same "
     "'one-change <stage>' key; it goes to the challenger or the next practice round to be measured. The live bot "
     "plays with changes that were already validated", None),
    ("challenger", "builder", 12, 14, "a new challenger is released (a new releases/*.zip since the window opened)",
     "keep building at normal care; don't pack it in a hurry. The practice round plays the most informative bot "
     "already released and upload-tested (else the live bot). The challenger's next slot is the next window's T-12",
     "no new challenger this window. Leave the live bot active for the practice round (or the released bot BUILDER names)."),
    ("note", "builder", 7, None, "the 'Which bot?' question for this round is in state/decisions.md",
     "the live bot is the default. Ask the question now only if a released, upload-tested challenger has numbers "
     "before T-5; otherwise the live bot plays",
     "no 'Which bot?' question by T-7: the live bot plays unless BUILDER brings the numbers before T-5."),
    ("chosen", "builder", 4, 6, "the bot chosen at T-8 is released and upload-tested (state/live.json's zip exists)",
     "the chosen bot doesn't play this round: the previous live bot (active since T-9) plays and nothing is uploaded. "
     "Put it back in state/live.json (python3 scripts/live.py <previous> \"cut-off\"). Stop packing the chosen bot for "
     "this round; it plays the next practice round instead",
     "the chosen bot wasn't ready by T-4. Upload nothing: the live bot already active plays."),
]
ONE_CHANGE = re.compile(r"one[-_ ]?change", re.I)


def data_landed(root, stage: str) -> float:
    """When a stage's hand data landed (the first hands file's time), 0 if it hasn't. From data/rounds/ (each round
    folder's round.json, else its name), else the portal watcher's record."""
    best = 0.0
    base = Path(root) / "data" / "rounds"
    try:
        dirs = [d for d in base.iterdir() if d.is_dir()]
    except OSError:
        dirs = []
    for d in dirs:
        meta = load_json(d / "round.json", None)
        st = norm_stage((meta or {}).get("stage") or re.sub(r"^\d+-", "", d.name))
        if st != stage:
            continue
        try:
            ts = [f.stat().st_mtime for f in d.glob("hands-*.jsonl.gz") if f.stat().st_size > 100]
        except OSError:
            ts = []
        if ts:
            best = max(best, min(ts))
    if not best:
        best = float((load_json(sp(root, "portal.json"), {}).get("landed_at") or {}).get(stage) or 0)
    return best


def ledger_one_changes(root) -> list:
    try:
        text = (Path(root) / "notes" / "LEDGER.md").read_text(errors="replace")
    except OSError:
        return []
    return [ln.strip() for ln in text.splitlines() if ONE_CHANGE.search(ln)]


def line_id(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def met(gid: str, k: int, start: float, U: float, root, now: float, snap: dict):
    """True: done. False: not done. None: nothing to judge yet. Files only, never anyone's say-so."""
    root, prev = Path(root), f"Round {k - 1}"
    if gid == "data":
        return data_landed(root, prev) > start - 2 * U
    if gid == "card":
        landed = data_landed(root, prev)
        if landed <= start - 2 * U:
            return None   # no data, no card due ("data" covers it)
        try:
            for f in (root / "analysis").rglob("*card*.md"):
                if "fp" in f.relative_to(root / "analysis").parts[:-1] or "fp" in f.name.lower():
                    continue
                if f.stat().st_mtime > landed - 60:
                    return True
        except OSError:
            pass
        return None if now < landed + 3 * U else False
    if gid == "change":
        lines = ledger_one_changes(root)
        for ln in lines:
            st = norm_stage(ln[ONE_CHANGE.search(ln).end():][:40])
            if st in (prev, f"Round {k - 1}.5"):
                return True
        if snap.get("late"):
            return bool(lines)
        old = set(snap.get("oc") or [])
        return any(line_id(ln) not in old for ln in lines)
    if gid == "challenger":
        try:
            return any(f.stat().st_mtime > start - 2 * U for f in (root / "releases").glob("*.zip"))
        except OSError:
            return False
    if gid == "note":
        f = root / "state" / "decisions.md"
        try:
            if f.stat().st_mtime <= start:
                return False
            return bool(re.search(rf"\bround\s*#?\s*{k}(?![\d.])|\br{k}\b", f.read_text(errors="replace"), re.I))
        except OSError:
            return False
    if gid == "chosen":
        live = live_bot(root)
        if not live or float(live.get("at") or 0) <= start:
            return True   # nothing new chosen this window: the live bot plays as it is
        act, known = portal_active(root, now)
        if known and same_bot(live["bot"], act):
            return True   # already active on the portal
        return (root / (live.get("file") or f"releases/{live['bot']}.zip")).exists()
    return True


def window_start(s, k: int, ts: float) -> float:
    U, rs = unit(s), round_starts(s)
    return ts - (10 * U if k == 1 else min(20 * U, ts - rs[k - 2]))


def guard_tick(s, root, now: float, gst: dict, seen: dict) -> list:
    """[(to, text, human_line_or_None)] for heads-ups and cut-offs due now; updates gst (done keys, snapshots)."""
    U, rs, tk = unit(s), round_starts(s), int(float(s["start"]))
    done, snaps, out = set(gst.get("done") or []), dict(gst.get("snap") or {}), []
    for k, ts in enumerate(rs, 1):
        start = window_start(s, k, ts)
        if not (start <= now < ts) or held(s, k, seen, now):
            continue
        wid = f"{tk}:r{k}"
        if wid not in snaps:   # what the LEDGER held when this window opened (a late look is lenient)
            snaps[wid] = {"oc": [line_id(x) for x in ledger_one_changes(root)], "at": now, "late": now > start + 2 * U}
        for gid, owner, cut, warn, what, fallback, human in GUARD:
            key = f"{wid}:{gid}"
            if key in done or (k == 1 and gid not in ("note", "chosen")):
                continue
            if gid == "card" and f"{wid}:data:cut" in done:
                continue
            judge_at = ts - (warn or cut) * U
            if gid in ("note", "chosen") and now < judge_at:
                continue   # these can change until their cut-off: judge them only from the heads-up on
            m = met(gid, k, start, U, root, now, snaps[wid])
            if m:
                if gid not in ("note", "chosen") or now >= ts - cut * U:
                    done.add(key)
                continue
            if m is False and (gid == "card" or now >= ts - cut * U):
                done.update((key, key + ":cut"))
                when = "within 3 event-minutes of the data landing" if gid == "card" else f"by T-{cut} ({hhmm(ts - cut * U)})"
                tail = ("" if gid in ("data", "challenger") else
                        " Stop that work for this round, record what you have in notes/LEDGER.md (a hypothesis, or a "
                        "result if measured), and take your next task; note the cause for the next T-20 sync.")
                out.append((owner, f"[CUT-OFF] scored round {k} ({hhmm(ts)}): '{what}' didn't happen {when}. The "
                                   f"pre-registered fallback plays: {fallback}; this is not a request to hurry.{tail}",
                            f"Before scored round {k}: {human}" if human else None))
                continue
            if m is None:
                continue
            if warn and now >= ts - warn * U and key + ":warn" not in done:
                done.add(key + ":warn")
                out.append((owner, f"[deadline] scored round {k}: '{what}' isn't done; its cut-off is T-{cut} "
                                   f"({hhmm(ts - cut * U)}). If it matters this window, re-scope now: cut it to the smallest "
                                   "useful version, or give it a helper. Do NOT tell anyone to hurry or skip a test. If it "
                                   f"misses, this fallback plays, and it is fine: {fallback}.", None))
    gst["done"], gst["snap"] = sorted(done), {w: v for w, v in snaps.items() if w.startswith(f"{tk}:")}
    return out


# ------------------------------------------------------------------ state/clock.md
def short(t: str, n: int) -> str:
    t = re.sub(r"\s+", " ", str(t)).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def render_md(root, s, now: float, tl=None, seen=None, sent=None) -> str:
    tl = tl or load_timeline(root)
    seen = read_seen(root) if seen is None else seen
    out = [f"# Clock (written {hms(now)})", ""]
    fmt_line = (f"build {num((s or {}).get('build', 60))} min · scored rounds every {num((s or {}).get('gap', 20))} min · "
                f"{int((s or {}).get('scored', 6))} scored rounds")
    if s and float(s.get("scale") or 1) != 1:
        fmt_line += f" · REHEARSAL SPEED: 1 event-minute = {unit(s):g} real seconds"
    if not started(s):
        out += ["**No clock set.** Set minute 0 with `python3 scripts/clock.py start now` (or `start 14:02`).", "",
                f"Format: {fmt_line}"]
        return "\n".join(out) + "\n"
    U, rs, t0 = unit(s), round_starts(s), float(s["start"])
    mnow = (now - t0) / U
    out.append(f"Minute 0: **{hms(t0)}** · {fmt_line}")
    if mnow < 0:
        out.append(f"Now {hhmm(now)}: before the start (minute 0 in {-mnow:.0f} min).")
    else:
        nxt = next(((k, ts) for k, ts in enumerate(rs, 1) if ts > now), None)
        win = f" · next: scored round {nxt[0]} at {hhmm(nxt[1])} (T-{(nxt[1] - now) / U:.0f})" if nxt else ""
        if not nxt and now > rs[-1] + 20 * U:
            win = " · the event is over"
        out.append(f"Now {hhmm(now)}: minute {mnow:.0f} · stage **{stage_of(s, now)}**{win}")
    live = (live_bot(root) or {}).get("bot")
    act, known = portal_active(root, now)
    out.append(f"Live bot (state/live.json): **{live or 'none declared'}** · the portal runs: "
               f"{(act or 'NO bot') if known else 'unknown (portal watcher not reporting)'}")
    out += ["", "## Rounds", "", "| Round | Starts | |", "|---|---|---|"]
    first_future = True
    for kind, n, ts in events(s):
        stage = stage_of_round(kind, n)
        note = []
        if kind == "scored" and str(n) in (s.get("round_at") or {}):
            note.append("pinned (portal)" if str(n) in (s.get("auto_pinned") or {}) else "pinned")
        e = seen.get(stage)
        if isinstance(e, dict) and e.get("at"):
            note.append(f"started {hms(float(e['at']))}" if e.get("exact") else "seen on the portal")
        elif ts <= now:
            note.append("not seen on the portal" if seen else "past")
        elif first_future:
            note.append("**next**")
            first_future = False
        lbl = event_label(kind, n)
        out.append(f"| {'**' + lbl + '**' if kind == 'scored' else lbl} | {hhmm(ts)} | {' · '.join(note)} |")
    out += ["", "## Next steps", ""]
    sent = sent if sent is not None else set((load_json(sp(root, "clock_sent.json"), {}) or {}).get("sent") or [])
    tk, shown = int(t0), 0
    for m in marks(s, tl):
        if m["at"] < now - 1 or f"{tk}:{m['key']}" in sent:
            continue
        msgs = step_messages(s, m, tl, root)
        hum = [h for h, _ in human_lines(s, m, tl, root, now)]
        if not msgs and not hum:
            continue
        lab = f"b{m['mi']}" if m["kind"] == "b" else f"T-{m['o']} of round {m['k']}"
        out.append(f"- **{hhmm(m['at'])}** ({lab})")
        for to, text in msgs:
            out.append(f"  - to {to}: {short(text.split(': ', 1)[-1], 170)}")
        for h in hum:
            out.append(f"  - humans: {short(h, 170)}")
        shown += 1
        if shown >= 3:
            break
    if not shown:
        out.append("- (none left)")
    return "\n".join(out) + "\n"


def write_md(root, s, now, **kw) -> None:
    try:
        write_text(sp(root, "clock.md"), render_md(root, s, now, **kw))
    except OSError as e:
        print(f"[clock] couldn't write state/clock.md: {e}", flush=True)


# ------------------------------------------------------------------ the daemon
class Daemon:
    def __init__(self, root=None, echo: bool = True):
        self.root = Path(root or ROOT)
        self.started_at = time.time()
        self.echo = echo
        self.last_md = 0.0

    def say(self, to: str, text: str) -> None:
        post(to, text, "clock", root=self.root)
        if self.echo:
            quiet(f"-> {to}: {short(text, 150)}")

    def tick(self, now: float | None = None) -> list:
        """One pass: carry-over, auto-pin, due steps, cut-offs, clock.md. Returns the step keys fired."""
        now = time.time() if now is None else now
        root, tl = self.root, load_timeline(self.root)
        fired: list = []
        with Lock(root):
            s = load_json(sp(root, "schedule.json"), None)
            sst = load_json(sp(root, "clock_sent.json"), {}) or {}
            sent, last = set(sst.get("sent") or []), sst.get("sched")
            gst = load_json(sp(root, "clock_guard.json"), {}) or {}
            if not started(s):
                if now - self.last_md > 15:
                    write_md(root, s, now, tl=tl, seen={}, sent=set())
                    self.last_md = now
                return fired
            changed = False
            if last and started(last) and not same_shape(last, s):
                sent, changed = carry(sent, last, s, now, tl), True
                if self.echo:
                    quiet(f"schedule changed: minute 0 {hms(float(s['start']))}, scored rounds at "
                          + ", ".join(hhmm(t) for t in round_starts(s)))
            seen = read_seen(root)
            s2, notes = autopin(s, seen, now)
            if notes:
                write_json(sp(root, "schedule.json"), s2)
                sent, s, changed = carry(sent, s, s2, now, tl), s2, True
                for n_ in notes:
                    self.say("both", n_)
            tk, U = int(float(s["start"])), unit(s)
            for key, msg in drift_notes(s, seen, sent):
                sent.add(key)
                changed = True
                self.say("both", msg)
            rs = round_starts(s)
            for m in marks(s, tl):
                key = f"{tk}:{m['key']}"
                if key in sent:
                    continue
                grace = max(5 * U, rs[0] - m["at"]) if m["key"] in EARLY else 5 * U
                if not (m["at"] <= now < m["at"] + grace):
                    continue
                if m["kind"] == "T" and held(s, m["k"], seen, now):
                    hk = f"{tk}:hold{m['k']}"
                    if hk not in sent:
                        sent.add(hk)
                        changed = True
                        exp = round_ts(s, m["k"] - 1)
                        self.say("both", f"Scored round {m['k'] - 1} hasn't started on the portal (expected {hhmm(exp)}). "
                                         f"The steps and deadlines for round {m['k']}'s window wait; the clock moves when the "
                                         f"portal starts it, or pin the real time: python3 scripts/clock.py pin "
                                         f"scored{m['k'] - 1} HH:MM.")
                    continue
                late = ""
                if m["at"] < self.started_at and now - m["at"] > 1.5 * U:
                    late = f"(LATE: due at {hhmm(m['at'])} while the clock was stopped) "
                for to, text in step_messages(s, m, tl, root):
                    self.say(to, late + text)
                for text, is_loud in human_lines(s, m, tl, root, now):
                    if self.echo:
                        (loud if is_loud else quiet)(text, now)
                sent.add(key)
                fired.append(m["key"])
                changed = True
            gbefore = json.dumps(gst, sort_keys=True)
            for to, text, human in guard_tick(s, root, now, gst, seen):
                self.say(to, text)
                if human and self.echo:
                    loud(human, now)
            changed = changed or json.dumps(gst, sort_keys=True) != gbefore
            if changed:
                write_json(sp(root, "clock_sent.json"), {"sent": sorted(sent), "sched": s, "at": now})
                write_json(sp(root, "clock_guard.json"), gst)
            if changed or fired or now - self.last_md > 15:
                write_md(root, s, now, tl=tl, seen=seen, sent=sent)
                self.last_md = now
        return fired

    def run(self) -> int:
        s = load_json(sp(self.root, "schedule.json"), None)
        print(f"Clock running in {self.root} (Ctrl-C stops it; restart it any time: it resumes from state/).", flush=True)
        if started(s):
            print(f"Minute 0 {hms(float(s['start']))}; scored rounds at " + ", ".join(hhmm(t) for t in round_starts(s))
                  + (f"; 1 event-minute = {unit(s):g} s" if unit(s) != 60 else ""), flush=True)
        else:
            print("No minute 0 yet: waiting for `python3 scripts/clock.py start ...`.", flush=True)
        errs = 0
        while True:
            try:
                self.tick()
                errs = 0
            except KeyboardInterrupt:
                raise
            except Exception:  # noqa: BLE001   one bad tick must not stop the clock
                errs += 1
                if errs <= 3 or errs % 60 == 0:
                    traceback.print_exc()
            s = load_json(sp(self.root, "schedule.json"), None)
            time.sleep(min(1.0, max(0.05, unit(s) / 8)) if started(s) else 1.0)


# ------------------------------------------------------------------ commands
def cur_sched(root) -> dict:
    s = load_json(sp(root, "schedule.json"), None)
    return s if isinstance(s, dict) else {}


def times_line(s) -> str:
    rs = round_starts(s)
    return (f"minute 0 {hms(float(s['start']))}; practices " + ", ".join(hhmm(build_ts(s, mi)) for mi in (20, 30, 40, 50))
            + "; scored rounds " + ", ".join(hhmm(t) for t in rs)) if rs else "no clock set"


def cmd_start(a, root) -> int:
    by = os.environ.get("AVALON_FROM") or "human"
    with Lock(root):
        old = cur_sched(root)
        t0 = parse_clock_time(a.time or "now")
        new = {k: old.get(k, v) for k, v in DEFAULTS.items()}
        if a.scale:
            new["scale"] = a.scale
        new.update(start=t0, set_by=by, at=time.time())
        pins = {k: v for k, v in (old.get("round_at") or {}).items() if float(v) >= t0}   # real starts stay true
        if pins:
            new["round_at"] = pins
            new["auto_pinned"] = {k: v for k, v in (old.get("auto_pinned") or {}).items() if k in pins}
        write_json(sp(root, "schedule.json"), new)
    rs = round_starts(new)
    if started(old) and abs(float(old["start"]) - t0) > 1:
        msg = (f"minute 0 is now {hms(t0)} (was {hms(float(old['start']))}). Scored round 1 at {hhmm(rs[0])}, the last "
               f"scored round at {hhmm(rs[-1])}. Every step and deadline moves with it; times quoted earlier are out of date.")
    elif not started(old):
        msg = f"minute 0 set: {hms(t0)}. Scored round 1 at {hhmm(rs[0])}, the last scored round at {hhmm(rs[-1])}."
    else:
        msg = ""
    if msg:
        post("both", msg, "clock", root=root)
    print(msg or "minute 0 unchanged.")
    print(times_line(new))
    write_md(root, new, time.time())
    return 0


def cmd_format(a, root) -> int:
    with Lock(root):
        old = cur_sched(root)
        new = dict(old)
        for f in ("build", "gap", "scored", "scale"):
            v = getattr(a, f)
            if v is not None:
                if v <= 0:
                    print(f"clock.py: --{f} must be positive", file=sys.stderr)
                    return 2
                new[f] = int(v) if f == "scored" else v
        for f, v in DEFAULTS.items():
            new.setdefault(f, v)
        write_json(sp(root, "schedule.json"), new)
    diff = ", ".join(f"{f} {num(new[f])} (was {num(old.get(f, DEFAULTS[f]))})" for f in ("build", "gap", "scored", "scale")
                     if float(new[f]) != float(old.get(f, DEFAULTS[f])))
    if not diff:
        print("format unchanged: " + ", ".join(f"{f} {num(new[f])}" for f in ("build", "gap", "scored", "scale")))
        return 0
    if started(new):
        rs = round_starts(new)
        post("both", f"format changed: {diff}. Scored round 1 at {hhmm(rs[0])}, the last scored round at {hhmm(rs[-1])}. "
                     "Every step and deadline moves with it; times quoted earlier are out of date.", "clock", root=root)
        print(times_line(new))
    print(f"format changed: {diff}")
    write_md(root, new, time.time())
    return 0


def parse_round(spec: str) -> tuple:
    """'scored3', 'round 3', 'r3', 's3' -> ('scored', 3); 'practice5', 'p5' -> ('practice', 5); 'round2.5' -> ('practice', 6)."""
    t = re.sub(r"[\s_-]+", "", str(spec).lower())
    m = re.fullmatch(r"(?:scored|scoredround|round|r|s)(\d+)\.5", t)
    if m:
        return "practice", 4 + int(m.group(1))
    m = re.fullmatch(r"(?:scored|scoredround|round|r|s)(\d+)", t)
    if m:
        return "scored", int(m.group(1))
    m = re.fullmatch(r"(?:practice|practiceround|p)(\d+)", t)
    if m:
        return "practice", int(m.group(1))
    raise ValueError(f"which round is {spec!r}? use scored3, practice5, round2.5")


def cmd_pin(a, root) -> int:
    kind, n = parse_round(a.round)
    with Lock(root):
        s = cur_sched(root)
        if not started(s):
            print("clock.py: no minute 0 yet: run `clock.py start ...` first", file=sys.stderr)
            return 2
        U = unit(s)
        k = n if kind == "scored" else (1 if n <= 4 else n - 3)
        if not 1 <= k <= int(s.get("scored", 6)) or n < 1:
            print(f"clock.py: there is no such round in the format ({int(s.get('scored', 6))} scored rounds)", file=sys.stderr)
            return 2
        exp = expected_start(s, stage_of_round(kind, n))
        when = parse_clock_time(a.time, ref=exp)          # "15:40" = the reading nearest the round's scheduled time
        if kind == "scored":
            t = when
        elif n <= 4:
            t = when + (50 - 10 * n) * U    # practice n is (60 - (10 + 10n)) event-minutes before round 1
        else:
            t = when + 10 * U               # practice 4+j plays 10 event-minutes before scored round j+1
        before = round_ts(s, k)
        floor = round_ts(s, k - 1) if k > 1 else float(s["start"])
        if t <= floor:
            print(f"clock.py: NOT pinned: that puts scored round {k} at {hms(t)}, before "
                  + (f"scored round {k - 1} ({hhmm(floor)})" if k > 1 else f"minute 0 ({hms(floor)})")
                  + ". Check the time (24-hour) or pin the earlier round first.", file=sys.stderr)
            return 2
        new = pin(s, k, t)
        new.setdefault("auto_pinned", {}).pop(str(k), None)
        write_json(sp(root, "schedule.json"), new)
    later = [f"round {i} {hhmm(x)}" for i, x in enumerate(round_starts(new), 1) if i > k]
    what = f"{event_label(kind, n)} at {hhmm(when)}" + (f", so scored round {k} at {hhmm(t)}" if kind != "scored" else "")
    msg = (f"{what} (scored round {k} was {hhmm(before)}; set by a human)."
           + (f" Later rounds follow: {', '.join(later)}." if later else "")
           + " Every deadline in those windows moves with them; times quoted earlier are out of date.")
    post("both", msg, "clock", root=root)
    print(msg)
    print(times_line(new))
    write_md(root, new, time.time())
    return 0


def cmd_reset(a, root) -> int:
    with Lock(root):
        had = started(cur_sched(root))
        for name in ("schedule.json", "clock_sent.json", "clock_guard.json"):
            try:
                sp(root, name).unlink()
            except FileNotFoundError:
                pass
    write_md(root, None, time.time())
    if had:
        post("both", "the clock was reset: no schedule until minute 0 is set again (python3 scripts/clock.py start ...).",
             "clock", root=root)
    print("clock reset: schedule, sent steps and cut-offs cleared.")
    return 0


def cmd_show(a, root) -> int:
    s = cur_sched(root) or None
    now = time.time()
    text = render_md(root, s, now)
    write_text(sp(root, "clock.md"), text)
    print(text)
    return 0


def cmd_pre(a, root) -> int:
    tl = load_timeline(root)
    rows = [p for p in tl.get("pre", []) if not a.session or p.get("to") == a.session]
    print("Pre-event research (when a human says 'start the research'): spawn these in ONE message, all with "
          "run_in_background: true. Notes only, NO bot code.")
    for p in rows:
        print(f"- [{p.get('to')}] {p.get('agent')}: {p.get('text')}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start", help="set minute 0")
    p.add_argument("time", nargs="?", default="now")
    p.add_argument("--scale", type=float, default=None, help="rehearsals only: 1 event-minute = scale*60 s")
    p = sub.add_parser("format", help="build length, gap between scored rounds, number of scored rounds")
    p.add_argument("--build", type=float)
    p.add_argument("--gap", type=float)
    p.add_argument("--scored", type=int)
    p.add_argument("--scale", type=float)
    p = sub.add_parser("pin", help="a round's real time, e.g. pin scored3 15:40")
    p.add_argument("round")
    p.add_argument("time")
    sub.add_parser("reset", help="clear the clock")
    sub.add_parser("show", help="print state/clock.md (refreshed)")
    p = sub.add_parser("run", help="the daemon")
    p.add_argument("--scale", type=float, default=None)
    p = sub.add_parser("pre", help="print the pre-event research tasks")
    p.add_argument("session", nargs="?", choices=["builder", "research"])
    a = ap.parse_args(argv)
    root = ROOT
    try:
        if a.cmd == "run":
            if a.scale:
                with Lock(root):
                    s = cur_sched(root)
                    if float(s.get("scale") or 1) != a.scale:
                        s = dict(s or {}, scale=a.scale)
                        for f, v in DEFAULTS.items():
                            s.setdefault(f, v)
                        s.setdefault("start", None)
                        write_json(sp(root, "schedule.json"), s)
            return Daemon(root).run()
        return {"start": cmd_start, "format": cmd_format, "pin": cmd_pin, "reset": cmd_reset, "show": cmd_show,
                "pre": cmd_pre}[a.cmd](a, root)
    except ValueError as e:
        print(f"clock.py: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nclock stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
