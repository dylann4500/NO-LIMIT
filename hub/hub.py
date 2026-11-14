"""Team avalon's agent hub: one per laptop.

  ./hub/start.sh samuel ~/nolimit-rehearsal [--portal-base URL --portal-key-file PATH]   # open http://127.0.0.1:7777

Runs this laptop's agents as Claude Code sessions (Claude Agent SDK, your own login), serves the UI,
asks before risky commands, moves messages between agents on both laptops (bus.py), and runs two
services: the clock (round schedule and deadlines) and, where configured, the portal watcher.
The UI listens on 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import hashlib
import json
import math
import shutil
import gzip
import os
import re
import subprocess
import time
import traceback
import urllib.request
from pathlib import Path

from aiohttp import web
from claude_agent_sdk import (query as sdk_query, HookMatcher, AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
                              PermissionResultDeny, ResultMessage, SystemMessage, TextBlock, ToolResultBlock,
                              ToolUseBlock, UserMessage, create_sdk_mcp_server, tool)

from bus import Bus, atomic_write, load_json, new_id
from roster import COMMON_RULES, DECISION_RULES, KICKOFF, PEOPLE, PROTOCOL, ROSTER, team_directory

HERE = Path(__file__).resolve().parent
STATES = ("working", "waiting", "blocked", "done", "idle")
DANGER = re.compile("|".join([
    r"\brm\s+(-\S*[rR]|--recursive)", r"\bfind\b[^\n]*\s-delete\b", r"rmtree", r"\bunlink\b",
    r"git\s+push\b[^\n]*(--force|\s-f\b|\s\+\S)", r"git\s+reset\s+--hard", r"git\s+clean\s+-\S*f",
    r"git\s+(stash|restore|rebase)\b", r"git\s+checkout\s+(--\s|\.\s*$|-f\b)", r"git\s+commit\b[^\n]*--amend",
    r"git\s+branch\s+-D", r"\bsudo\b", r"\bmkfs", r"curl[^|\n]*\|\s*(ba|z)?sh", r"chmod\s+-R\s+777",
    r"\bdd\s+if=", r">\s*/dev/sd", r"\bkillall\b", r"\bkill\s+(-\S+\s+)*-1\b",
    r"\bpkill\b(?![^\n]*-f\s+\S*(poker|spar|play|modal|run_|bench|test))",   # broad pkill can kill the agents themselves
    r"modal\s+(app\s+delete|volume\s+(rm|delete)|secret\s+delete)",
    r"(pokerbot\.sequoiacap\.com|/tournament/api)[^\n]*(-X\s*(POST|PATCH|PUT|DELETE)|--data|\s-d\s)",
    r"(-X\s*(POST|PATCH|PUT|DELETE)|--data|\s-d\s)[^\n]*(pokerbot\.sequoiacap\.com|/tournament/api)",
    r"\.(post|patch|put|delete)\([^\n]*(sequoiacap|tournament/api)",
]))
HUB_TOOLS = ["send_message", "share_file", "list_agents", "read_agent", "set_status", "notify_human", "start_agent", "stop_agent",
             "declare_live", "set_schedule", "propose", "update_proposal", "list_proposals", "codex_task", "register_bot",
             "record", "verify", "invalidate", "set_rules", "ledger", "next_bot_name",
             "queue_post", "queue_claim", "queue_done", "fetch_file", "report_progress"]
ROSTER_NAMES = {a["name"] for agents in ROSTER.values() for a in agents}
API_KEY_FILE = Path.home() / ".config" / "avalon-hub" / "anthropic-api-key"
KINDS = ("idea", "build", "live", "analysis", "bot", "question", "research", "finding", "change", "decision")
BUILD_NOTES = [  # (person, agent, name): one progress tile per build-hour work stream, created at minute 0
    ("dylan", "d-platform", "v1 and the platform"),
    ("dylan", "d-builder", "Styles A, B, C"),
    ("dylan", "d-challenger", "Challenger"),
    ("samuel", "s-tester", "Test rig"),
    ("samuel", "s-data", "Round card script"),
    ("samuel", "s-data", "Maths tables"),
    ("samuel", "s-scout", "Fingerprinting"),
]


async def one_shot(prompt: str, options, timeout: float) -> str:
    """A single model call that can't hang its caller (the narrator holds a lock; a report holds an HTTP request)."""
    async def run():
        out = ""
        async for m in sdk_query(prompt=prompt, options=options):
            if isinstance(m, ResultMessage):
                out = m.result or ""
        return out
    return await asyncio.wait_for(run(), timeout)


def merge_note(a: dict, b: dict) -> dict:
    """Two laptops' copies of one note: keep every message from both (a note's conversation must never lose a
    line), and the newer copy's fields. A removal or a human decision is never undone by an older copy."""
    new, old = (b, a) if b.get("updated", 0) >= a.get("updated", 0) else (a, b)
    seen, thread = set(), []
    for t in sorted((a.get("thread") or []) + (b.get("thread") or []), key=lambda t: t.get("at", 0)):
        k = (round(t.get("at", 0), 2), t.get("who"), str(t.get("text"))[:80])
        if k not in seen:
            seen.add(k)
            thread.append(t)
    m = dict(new, thread=thread)
    if old.get("status") == "removed" or (old.get("status") in ("approved", "rejected") and new.get("status") in ("needs_call", "revise", "expired")
                                          and not (new.get("conflict") and not old.get("conflict"))):   # opposite answers reopen it
        m["status"] = old["status"]
        m["decided_by"] = old.get("decided_by", m.get("decided_by"))
    if not m.get("body") and old.get("body"):
        m["body"] = old["body"]
    return m


def stage_rank(st: str) -> float:
    st = st or ""
    if st == "Build":
        return 0
    m = re.match(r"Practice (\d+)", st)
    if m:
        return int(m.group(1))
    m = re.match(r"Round (\d+)(\.5)?", st)
    return 10 + 2 * int(m.group(1)) + (1 if m.group(2) else 0) if m else -1


def persistent_leaks(items: list[dict]) -> list[dict]:
    """Leaks (results tagged leak:<slug>) seen in two or more different rounds' data with the same sign: real, not
    noise. Returns [{slug, stages, effects, ids}] strongest first."""
    by: dict[str, list[dict]] = {}
    for x in items:
        if x.get("type") not in ("result", "hypothesis") or x.get("status") in ("invalidated", "disputed"):
            continue
        for t in x.get("tags") or []:
            if isinstance(t, str) and t.startswith("leak:") and isinstance(x.get("effect"), (int, float)):
                by.setdefault(t[5:], []).append(x)
    out = []
    for slug, xs in by.items():
        data_stage = {}
        for x in xs:
            st = x.get("data_stage") or x.get("stage")
            data_stage.setdefault(st, x)
        signs = {1 if x["effect"] > 0 else -1 for x in data_stage.values() if x["effect"]}
        if len(data_stage) >= 2 and len(signs) == 1:
            ordered = sorted(data_stage.items(), key=lambda kv: stage_rank(kv[0]))
            out.append({"slug": slug, "stages": [k for k, _ in ordered], "effects": [v["effect"] for _, v in ordered],
                        "ids": [v["id"] for _, v in ordered]})
    return sorted(out, key=lambda r: -abs(sum(r["effects"]) / len(r["effects"])))


def disagreements(items: list[dict]) -> list[str]:
    """Answers to the same question from different lenses/models that point different ways: the escalation signal."""
    by_q: dict[str, list[dict]] = {}
    for x in items:
        if x.get("type") == "result" and x.get("question") and x.get("status") not in ("invalidated",) and \
                isinstance(x.get("effect"), (int, float)) and x.get("lens") != "aggregate":
            by_q.setdefault(x["question"], []).append(x)
    out = []
    for q, xs in by_q.items():
        if len(xs) < 2:
            continue
        signs = {1 if x["effect"] > 0 else -1 if x["effect"] < 0 else 0 for x in xs}
        apart = any(abs(a["effect"] - b["effect"]) > 2 * ((a.get("se") or 0) ** 2 + (b.get("se") or 0) ** 2) ** 0.5
                    for i, a in enumerate(xs) for b in xs[i + 1:] if a.get("se") is not None and b.get("se") is not None)
        if len(signs - {0}) > 1 or apart:
            out.append(f"- DISAGREE on '{q}': " + "; ".join(
                f"{x.get('lens') or '?'}/{x.get('model') or '?'} {x['effect']:+g}±{x.get('se', '?')} ({x['id']})" for x in xs))
    return out


def sched_unit(s: dict | None) -> float:
    """Real seconds per event-minute (less than 60 only in sped-up simulations)."""
    return 60 * (s or {}).get("scale", 1.0)


def round_starts(s: dict | None) -> list[float]:
    """When each scored round starts. Default: minute `build` (60), then one every `gap` (20) event-minutes. A round
    whose real start is known (the portal saw it start, or a human gave its time) is pinned in s['round_at'], and the
    rounds after it follow from there, so a late round moves every later deadline with it."""
    if not s:
        return []
    U, t0 = sched_unit(s), s["start"]
    B, G = s.get("build", 60), s.get("gap", 20)
    pins = {int(k): float(v) for k, v in (s.get("round_at") or {}).items()}
    out: list[float] = []
    for k in range(1, int(s.get("scored", 6)) + 1):
        out.append(pins[k] if k in pins else (out[-1] + G * U if out else t0 + B * U))
    return out


def round_ts(s: dict | None, k: int) -> float | None:
    r = round_starts(s)
    return r[k - 1] if 1 <= k <= len(r) else None


def build_ts(s: dict, mi: int) -> float:
    """A build-hour mark: the first steps (v1, the rig) count from minute 0; the practice-round marks (minute 17 on)
    count back from scored round 1, so a longer build or a late round 1 moves them with it."""
    return s["start"] + mi * sched_unit(s) if mi < 16 else round_starts(s)[0] - (60 - mi) * sched_unit(s)


def practice_ts(s: dict, k: int) -> float | None:
    """The practice round in the window before scored round k+1 (10 event-minutes before it)."""
    nxt = round_ts(s, k + 1)
    return nxt - 10 * sched_unit(s) if nxt else None


def stage_of(sch: dict | None, t: float) -> str:
    """The competition stage at time t: Build, Practice 1-4, Round k, Round k.5 (the practice after round k)."""
    if not sch or t < sch["start"]:
        return "Before the start"
    rs = round_starts(sch)
    if not rs or t < rs[0]:
        p = [build_ts(sch, mi) for mi in (20, 30, 40, 50)]
        return "Build" if t < p[0] else f"Practice {sum(1 for x in p if x <= t)}"
    k = sum(1 for x in rs if x <= t)
    if k >= len(rs):   # nothing is played after the last scored round
        return f"Round {len(rs)}"
    return f"Round {k}.5" if t >= rs[k] - 10 * sched_unit(sch) else f"Round {k}"


def stage_of_round(kind: str, n: int) -> str:
    """Stage label for the n-th practice or scored round on the portal."""
    if kind == "practice":
        return f"Practice {n}" if n <= 4 else f"Round {n - 4}.5"
    return f"Round {n}"


def bot_name(filename: str) -> str:
    return re.sub(r"\.zip$", "", Path(filename or "").name) or "?"

OPEN = ("new", "planned", "running", "needs_call", "revise")
QUICK_PRESETS = {"Do the suggestions", "Explain the biggest leak in plain words", "What's still running?", "How far along is it?",
                 "Anything blocked?", "How was it tested?", "What's the risk?", "What's the status?"}
REPORT_MODEL = os.environ.get("AVALON_REPORT_MODEL", "claude-sonnet-5-5")
NARRATOR_MODEL = os.environ.get("AVALON_NARRATOR_MODEL", "claude-haiku-5-5")
LONG_TURN_S = 25 * 60   # one turn this long: the Overseer checks it's progressing (output alone isn't progress)
STALL_S = 12 * 60   # longer than any single foreground tool call (Bash caps at 10 min)
# Context sizes (tokens) above which an agent compacts between turns (never T-9..T-2). Quality drops well before
# the window is full ("context rot") and every turn re-reads the whole context, so both stay lean; the ledger and
# each agent's PLAN file carry what compaction drops.
COMPACT_AT_OVERSEER = int(os.environ.get("AVALON_COMPACT_AT", 150_000))
COMPACT_AT_WORKER = int(os.environ.get("AVALON_COMPACT_AT", 100_000))
COMPACT_KEEP = ("Summarize for yourself to continue the day without loss. Keep, exactly: your role and current "
                "assignments; the event phase and schedule; the declared live bot (exact file) and every candidate "
                "with its status, test results and file path; every human decision and instruction, near-verbatim; "
                "open notes on the board by id; numbers from analyses with sample sizes and confidence; what is "
                "running where (subagents, Modal app ids, Codex job ids) and where results will land; promises you "
                "made to other agents; the ledger ids you depend on or cite; open questions. Drop: raw tool output, logs, superseded plans, chit-chat.")
LIMIT_RX = re.compile(r"usage limit|rate.?limit|overloaded|429|quota|limit reached|too many requests", re.I)
# a real allowance limit (wait for the reset or switch model/key), as opposed to a brief 429/overloaded (retry in a minute)
HARD_LIMIT_RX = re.compile(r"usage limit|limit reached|quota|resets? (?:at|in)|out of (?:extra )?usage|allowance", re.I)
APPROVAL_TIMEOUT = 120


class LimitHit(Exception):
    pass
EVENT_CAP = 4000


# "Upload v4.zip now", "**Upload v4 now**", "upload **v13.zip** now (greenlit ...)": an ask to upload, not a report about one
UPLOAD_ASK = re.compile(r"upload\W{0,3}(v\d+)(?:\.zip)?\W{0,3}(?:now|by|before|immediately|asap)\b", re.I)


# a greenlight that sets a condition ("approve if the tester passes it", "only once...", "provided ...")
CONDITIONAL = re.compile(r"\b(if|once|only when|only after|provided|as long as|unless|assuming|conditions?|after (?:the|s-|it))\b", re.I)


# "the competition starts now", "it's starting", "we're live", "the variant was announced (at 14:02)"
START_RX = re.compile(r"\b(competition|event|variant|tournament|finals?)\b[^.?!\n]{0,40}\b(start(?:s|ed|ing)?|begin(?:s|ning)?|began|"
                      r"announced|is live|kick(?:s|ed)? off|has started|is on)\b|^\s*(go|start|we'?re live|it'?s on|"
                      r"it'?s (?:starting|started|begun)|it (?:starts|started|begins|began)(?: now)?)\s*[.!]*\s*$", re.I)
AT_RX = re.compile(r"\b(?:at|was|@)\s*(\d{1,2}:\d{2}(?::\d{2})?)\b")
PREP_RX = re.compile(r"\b(start|begin|kick off|run)\s+(the\s+)?(pre-?event\s+|morning\s+)?research\b", re.I)
PREFLIGHT_RX = re.compile(r"^\s*(?:please\s+)?(?:run (?:the |a )?(?:pre-?flight|check|checks|pre-?flight check)|pre-?flight|"
                          r"check (?:that )?everything(?: works)?|check it all)\s*(?:now|please)?\s*[.!]*\s*$", re.I)


def norm_bot(x: str) -> str:
    """'releases/v3.zip', 'v3 (1).zip' (a browser's second download) -> 'v3'."""
    return re.sub(r"\s*\(\d+\)$", "", re.sub(r"\.zip$", "", (x or "").strip().split("/")[-1].lower()).strip())


def same_bot(declared: str, active: str) -> bool:
    """Compare a declared live-bot name with the portal's active file name, ignoring folders and .zip."""
    norm = lambda x: norm_bot(x)   # noqa: E731
    d, a = norm(declared), norm(active)
    return d == a or d in ("agent.py", "bot", "") or a == ""


def tmp_scrub(cmd: str) -> str:
    """Drop `rm` commands whose every target is inside /tmp (no '..'); leave everything else for the risk check."""
    import shlex
    parts = re.split(r"(&&|\|\||;|\||\n)", cmd)
    out = []
    for part in parts:
        try:
            toks = shlex.split(part)
        except ValueError:
            out.append(part)
            continue
        if toks and toks[0] == "rm":
            targets = [t for t in toks[1:] if not t.startswith("-")]
            if targets and all(re.match(r"^((/private)?/tmp/|\$\{?TMPDIR\}?/)", t) and ".." not in t for t in targets):
                continue
        out.append(part)
    return "".join(out)


def schema(required, props):
    return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()}, "required": required}


def short(x, n=400):
    if isinstance(x, list):
        x = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in x)
    s = x if isinstance(x, str) else json.dumps(x, default=str)
    return s if len(s) <= n else s[:n] + "…"


def hhmm(t):
    return time.strftime("%H:%M", time.localtime(t))


# ======================================================================== hub
class Hub:
    def __init__(self, person: str, repo: Path, data: Path, namespace: str, model: str | None):
        self.person, self.repo, self.data = person, repo, data
        self.model_override = model
        self.subs: set[asyncio.Queue] = set()
        self.approvals: dict[str, dict] = {}
        self.alerts: list[dict] = load_json(data / "alerts.json", [])
        self.bus = Bus(person, data, self.deliver, self.bounce, namespace)
        self.bus.merge = lambda key, local, remote: merge_note(local, remote)   # a note changed on both laptops keeps both changes
        self.bus.on_merge = lambda key, v: self.emit("prop", {"prop": v})
        self.agents: dict[str, Agent] = {s["name"]: Agent(self, s) for s in ROSTER[person]}
        self.bus.local_names = set(self.agents)
        self.bus.all_names = {a["name"] for agents in ROSTER.values() for a in agents} | {"s-portal", "s-clock", "d-clock", "hub"}
        self.services: dict[str, dict] = {}
        self.local_props: dict[str, dict] = load_json(data / "props.json", {})
        self.clock = Clock(self)
        self.codex: Codex | None = None
        self.portal: PortalWatcher | None = None
        self.portal_data = Path.home() / "portal-data"
        self.default_scale = 1.0
        self.report_busy: set[str] = set()
        self.last_landed = 0.0
        self.worker_model: str | None = None
        self.view_only = False
        self.traffic: list = []
        self.plan_challenges: set[str] = set()
        self.boot_at = time.time()
        self.card_ok = False
        self.landed_at: dict[str, float] = {}
        self.note_pending: dict[str, dict] = {}   # note id -> a human's question there with no answer yet
        self.checked_issues: dict[str, float] = {}   # contradiction text -> when it was raised   # stage -> when its results/hands landed (the deadline guard reads it)

    def note_error(self, where: str, e: BaseException):
        """Record a background failure (hub/errors.log) without stopping anything; shown in the Hub service."""
        try:
            with (self.data / "errors.log").open("a") as f:
                f.write(f"{time.strftime('%H:%M:%S')} {where}: {type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}\n")
        except Exception:  # noqa: BLE001
            pass

    async def forever(self, name: str, fn):
        """Run a long-lived loop; if it ever raises, record it and start it again (it must never die silently)."""
        while True:
            try:
                await fn()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                self.note_error(name, e)
                await asyncio.sleep(3)

    def emit(self, kind: str, payload: dict):
        ev = {"kind": kind, **payload}
        for q in list(self.subs):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                self.subs.discard(q)  # the stream loop notices and tells the page to resync

    async def deliver(self, msg: dict) -> bool:
        a = self.agents.get(msg["to"])
        if a is None:
            return False
        await a.receive(msg)
        return True

    async def bounce(self, msg: dict, why: str):
        a = self.agents.get(msg.get("from"))
        if a:
            await a.add_item({"kind": "hub", "wake": False, "text": f"Your message to {msg['to']} {why}."})

    def overseer(self) -> "Agent":
        return next(a for a in self.agents.values() if a.name.endswith("overview"))

    async def add_alert(self, agent: str, text: str, urgent: bool):
        now = time.time()
        for a in self.alerts:
            if a["agent"] == agent and a["text"] == text and now - a["at"] < 600:
                return
        if agent.endswith("overview"):   # one live note per Overseer: a new one replaces the old
            for a in [x for x in self.alerts if x["agent"] == agent]:
                urgent = urgent or (a.get("urgent") and now - a["at"] < 300)
                self.dismiss(a["id"])
        al = {"id": new_id(), "agent": agent, "text": text, "urgent": urgent, "at": now}
        self.alerts = (self.alerts + [al])[-50:]
        atomic_write(self.data / "alerts.json", json.dumps(self.alerts))
        self.emit("alert", al)

    def dismiss(self, aid: str):
        self.alerts = [a for a in self.alerts if a["id"] != aid]
        atomic_write(self.data / "alerts.json", json.dumps(self.alerts))
        self.emit("alert_done", {"id": aid})

    # ---------------- Decisions board (shared by both laptops through the bus)
    def props(self) -> list[dict]:
        out = {}
        for k, v in list(self.bus.shared.items()):
            if k.startswith("prop:") and isinstance(v, dict):
                out[v["id"]] = v
        for v in self.local_props.values():
            out[v["id"]] = merge_note(out[v["id"]], v) if v["id"] in out else v
        return sorted(out.values(), key=lambda p: p.get("updated", 0), reverse=True)

    def get_prop(self, pid: str) -> dict | None:
        return next((p for p in self.props() if p["id"] == pid), None)

    def mirror_note(self, p: dict):
        """Each note's full text as a file, so agents can read a whole conversation by path (external memory)."""
        try:
            d = self.data / "board"
            d.mkdir(exist_ok=True)
            txt = (f"# {p.get('title')}\n\nStage: {p.get('stage', '')} · kind: {p.get('kind')} · status: {p.get('status')} · "
                   f"owner: {p.get('owner')}\n\n" + (f"## Summary\n\n{p['body']}\n\n" if p.get("body") else "") +
                   "## Conversation\n\n" + "\n\n".join(f"**{t['who']}** ({hhmm(t['at'])}): {t['text']}" for t in p.get("thread", [])))
            atomic_write(d / f"{p['id']}.md", txt)
        except Exception:  # noqa: BLE001
            pass

    async def save_prop(self, p: dict):
        other = self.bus.shared.get("prop:" + p["id"])
        if isinstance(other, dict) and other is not p:   # the other laptop may have added to it meanwhile
            p.update(merge_note(other, p))
        p["updated"] = time.time()
        self.mirror_note(p)
        self.local_props[p["id"]] = p
        self.bus.shared["prop:" + p["id"]] = p
        if len(p.get("thread") or []) > 50:   # the link carries the newest 50 messages; the full thread stays here
            p = dict(p, thread=[dict(t, text=str(t.get("text", ""))[:4000]) for t in p["thread"][-50:]])
        atomic_write(self.data / "props.json", json.dumps(self.local_props))
        self.emit("prop", {"prop": p})
        await self.bus.set_shared("prop:" + p["id"], p)

    # ---------------- ledger: typed, prioritised context shared by both laptops
    def ledger(self) -> list[dict]:
        out = [v for k, v in self.bus.shared.items() if k.startswith("led:") and isinstance(v, dict)]
        return sorted(out, key=lambda x: x.get("at", 0))

    def note_ledger(self) -> dict:
        """Per note: the ledger items that belong to it (by note id, or a question naming its stage), compact."""
        out: dict[str, list] = {}
        notes = {p["id"]: p for p in self.props() if p.get("status") != "removed"}
        stage_note = {p.get("stage"): pid for pid, p in notes.items() if p.get("kind") == "analysis"}
        for x in self.ledger():
            if x.get("type") == "human":
                continue
            nid = x.get("note") if x.get("note") in notes else None
            if not nid and x.get("question"):
                nid = next((v for k, v in stage_note.items() if k and k in x["question"]), None)
            if nid:
                out.setdefault(nid, []).append({k: x.get(k) for k in ("id", "type", "status", "lens", "by", "effect", "se", "n")}
                                                | {"claim": str(x.get("claim", ""))[:140]})
        return out

    def rules(self) -> dict:
        return self.bus.shared.get("rules") or {}

    async def put_item(self, it: dict):
        it["updated"] = time.time()
        self.bus.shared["led:" + it["id"]] = it
        await self.bus.set_shared("led:" + it["id"], it)

    def rule_conflict(self, it: dict) -> str:
        """A result or method that contradicts the rules card is rejected when it is written."""
        r = self.rules()
        if it.get("scope") == "subgame":   # a deliberate study of part of the game (heads-up endgame, later blinds)
            return "" if it.get("players") not in (None, "") else "a subgame study must state its own players"
        for k in ("players", "stack", "big_blind", "hands_per_match"):
            if r.get(k) not in (None, "") and it.get(k) not in (None, ""):
                try:
                    differ = abs(float(it[k]) - float(r[k])) > 1e-9
                except (TypeError, ValueError):
                    differ = str(it[k]) != str(r[k])
                if differ:
                    return f"{k}={it[k]} contradicts the rules card ({k}={r[k]})"
        if r.get("players") and it.get("type") in ("method",) and it.get("players") in (None, ""):
            return "a method must state players (per table); the rules card says " + str(r["players"])
        return ""

    async def record_item(self, it: dict, by: str) -> tuple[str, str]:
        typ = it.get("type", "result")
        if typ not in ("result", "method", "hypothesis", "commitment", "human"):
            return "", "type must be result, method, hypothesis or commitment"
        if typ in ("result", "method"):
            bad = self.rule_conflict(it)
            if bad:
                return "", f"REJECTED: {bad}. Re-run it under the rules card, or ask d-platform to correct the card."
            if typ == "result" and (it.get("n") in (None, "") or not (it.get("method") or it.get("method_id"))):
                return "", "A result needs n and method (or record it as a hypothesis)."
        if it.get("question") and not it.get("lens"):
            return "", "An answer to a question needs lens= (leaks, sizing, opponent:<team>, twist, aggregate, ...)."
        stage = stage_of(self.bus.shared.get("schedule"), time.time())
        n = sum(1 for x in self.ledger() if x.get("type") == typ) + 1
        iid = f"{typ[0].upper()}{n}-{by.split('-')[0]}{int(time.time()) % 10000:04d}"
        it = {k: v for k, v in it.items() if v not in (None, "", [])}
        if any(isinstance(t, str) and t.startswith("leak:") for t in (it.get("tags") or [])):
            asyncio.create_task(self.flag_persistent())
        if by == "s-data" and "card" in (it.get("tags") or []):
            asyncio.create_task(self.route("card_ready", it.get("stage") or stage, stage=it.get("stage") or stage,
                                           card=it.get("file") or "analysis/<stage>/card.md", note_id=it.get("note")))
        q_ = str(it.get("question") or "")
        if q_.lower().startswith("one-change") and (it.get("lens") == "aggregate" or by == "s-data"):
            st_ = norm_stage(q_[len("one-change"):].strip()) or stage
            asyncio.create_task(self.tile("analysis-" + stage_slug(st_), f"{st_} analysis", "done", owner="s-data", stage=st_))
        it.update({"id": iid, "type": typ, "by": by, "stage": it.get("stage") or stage, "at": time.time(),
                   "status": "validated" if typ in ("human", "commitment") else "proposed"})
        await self.put_item(it)
        if it.get("note") and typ in ("result", "hypothesis"):
            await self.note_append(it["note"], by, f"**{'Result' if typ == 'result' else 'Hypothesis'}:** {it.get('claim', '')}"
                                   + (f" ({it.get('effect')} ± {it.get('se')}, n={it.get('n')})" if it.get("n") else ""), action="update")
        return iid, ""

    async def flag_persistent(self):
        await asyncio.sleep(1)
        for r in persistent_leaks(self.ledger()):
            key = "persist:" + r["slug"] + ":" + str(len(r["stages"]))
            if self.bus.shared.get(key):
                continue
            await self.bus.set_shared(key, {"at": time.time(), "updated": time.time()})
            an = max((p for p in self.props() if p.get("kind") == "analysis" and p.get("status") != "removed"),
                     key=lambda p: p.get("created", 0), default=None)
            text = (f"Persistent leak: **{r['slug']}** shows up in {len(r['stages'])} rounds' data, same direction ("
                    + ", ".join(f"{st} {e:+g}" for st, e in zip(r["stages"], r["effects"])) + "). By our rules that's "
                    "strong evidence: the fix should ship this window.")
            if an:
                await self.note_append(an["id"], "Hub", text)
            for ov in ("s-overview", "d-overview"):
                try:
                    await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": ov, "kind": "fyi",
                                         "priority": "high", "text": text})
                except Exception:  # noqa: BLE001
                    pass

    async def verify_item(self, iid: str, verdict: str, reason: str, by: str) -> str:
        it = self.bus.shared.get("led:" + iid)
        if not it:
            return f"No ledger item {iid}."
        it = dict(it, status=verdict, verified_by=by, verify_reason=reason[:600])
        await self.put_item(it)
        if verdict == "disputed":
            await self.flag(it, f"DISPUTED by {by}: {iid} \"{it.get('claim', '')[:120]}\": {reason[:300]}")
        return f"{iid}: {verdict}."

    async def invalidate(self, iid: str, reason: str, by: str) -> list[str]:
        """Mark an item and everything built on it (depends_on, transitively) invalid, and tell everyone who used them."""
        items = {x["id"]: x for x in self.ledger()}
        if iid not in items:
            return []
        bad, frontier = {iid}, [iid]
        while frontier:
            cur = frontier.pop()
            for x in items.values():
                if x["id"] not in bad and cur in (x.get("depends_on") or []) or (x.get("method_id") == cur and x["id"] not in bad):
                    bad.add(x["id"])
                    frontier.append(x["id"])
        for b in bad:
            await self.put_item(dict(items[b], status="invalidated", invalid_reason=f"{reason[:300]} (via {iid})"))
        msg = (f"INVALIDATED by {by}: {', '.join(sorted(bad))}. Reason: {reason[:400]}. Re-run or drop anything that used "
               "them; don't cite them.")
        users = {items[b].get("by") for b in bad} | {a.name for a in self.agents.values() if bad & a.led_seen}
        for u in {x for x in users if x}:
            try:
                await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": u, "kind": "task", "text": msg,
                                     "priority": "high"})
            except Exception:  # noqa: BLE001
                pass
        for b in bad:
            if items[b].get("note"):
                await self.note_append(items[b]["note"], "Skeptic", "⚠ " + msg, action="update")
        return sorted(bad)

    async def flag(self, it: dict, text: str):
        for u in {it.get("by"), self.owner_overseer("samuel"), self.owner_overseer("dylan")}:
            if u:
                try:
                    await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": u, "kind": "fyi", "text": text,
                                         "priority": "high"})
                except Exception:  # noqa: BLE001
                    pass
        if it.get("note"):
            await self.note_append(it["note"], "Skeptic", text, action="update")

    async def human_item(self, text: str, note: str | None = None):
        """Human instructions (not questions) become top-priority ledger items every agent sees, near-verbatim."""
        body = text.split(": ", 1)[-1].strip()
        if len(body) < 3 or body.endswith("?") or body in QUICK_PRESETS:
            return
        await self.record_item({"type": "human", "claim": f"{PEOPLE[self.person]}: {text.strip()[:600]}", "note": note},
                               PEOPLE[self.person].lower())

    # ---------------- work queue: idle experts pull (expert-choice routing; balances load by construction)
    def queue(self) -> list[dict]:
        xs = [v for k, v in self.bus.shared.items() if k.startswith("queue:") and isinstance(v, dict)]
        return sorted(xs, key=lambda x: (x.get("priority") != "crit", x.get("at", 0)))

    def queue_for(self, agent: str) -> list[dict]:
        return [x for x in self.queue() if not x.get("claimed_by") and not x.get("done")
                and (not x.get("for") or agent in x["for"] or agent.split("-", 1)[-1] in x["for"])]

    async def queue_post(self, task: str, for_: list, priority: str, note: str | None, by: str) -> str:
        qid = "Q" + new_id()[1:7].upper()
        await self.bus.set_shared("queue:" + qid, {"id": qid, "task": task[:2000], "for": for_ or [], "note": note,
                                                   "priority": "crit" if priority == "crit" else "opt", "by": by,
                                                   "at": time.time(), "updated": time.time()})
        for a in self.agents.values():   # wake an idle expert who can take it
            if a.state in ("idle", "done") and not a.name.endswith("overview") and self.queue_for(a.name) \
                    and qid not in a.queue_nudged and (not for_ or a.name in for_ or a.name.split("-", 1)[-1] in for_):
                a.queue_nudged.add(qid)
                await a.add_item({"kind": "hub", "wake": True, "text": f"A queued task is waiting for you ({qid}): call queue_claim."})
                break
        return qid

    async def queue_claim(self, agent: str) -> dict | None:
        for x in self.queue_for(agent):
            won = True
            if self.bus.d is not None:   # atomic across both laptops: the first claim wins
                try:
                    won = await asyncio.wait_for(self.bus.d.put.aio("claim:" + x["id"], agent, skip_if_exists=True), 10)
                except Exception:  # noqa: BLE001
                    won = False
            if won:
                x = dict(x, claimed_by=agent, claimed_at=time.time(), updated=time.time())
                await self.bus.set_shared("queue:" + x["id"], x)
                return x
        return None

    async def queue_done(self, qid: str, result: str, agent: str) -> str:
        x = self.bus.shared.get("queue:" + qid)
        if not x:
            return f"No queued task {qid}."
        await self.bus.set_shared("queue:" + qid, dict(x, done=True, result=result[:600], updated=time.time()))
        if x.get("by") and x["by"] != agent:
            try:
                await self.bus.send({"id": new_id(), "from": agent, "from_kind": "agent", "to": x["by"], "kind": "fyi",
                                     "text": f"Queued task {qid} done: {result[:600]}"})
            except Exception:  # noqa: BLE001
                pass
        return f"{qid} done."

    async def route(self, event: str, key: str, **ctx):
        """Send an event straight to its experts (once per key), with an fyi for their Overseer's digest."""
        done = self.bus.shared.get("routed:" + event + ":" + key)
        if done:
            return
        await self.bus.set_shared("routed:" + event + ":" + key, {"at": time.time(), "updated": time.time()})
        for who, kind, text in ROUTES.get(event, []):
            try:
                body = text.format(**{k: ctx.get(k, "") for k in ("stage", "card", "bot", "status", "by", "note")})
            except (KeyError, IndexError):
                body = text
            try:
                await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": who, "kind": kind,
                                     "note": ctx.get("note_id"), "text": "[routed by the hub] " + body})
            except Exception:  # noqa: BLE001
                pass
        for ov in ("s-overview", "d-overview"):
            if any(w.startswith(ov[0]) for w, _, _ in ROUTES.get(event, [])):
                try:
                    await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": ov, "kind": "fyi",
                                         "text": f"[routed] {event} {key}: sent to "
                                                 + ", ".join(f"{w} ({k})" for w, k, _ in ROUTES.get(event, []))
                                                 + ". No need to re-dispatch; check it lands."})
                except Exception:  # noqa: BLE001
                    pass

    async def ensure_note(self, pid: str, **fields) -> dict:
        """Create a hub-made note once (deterministic id, so a restart or the other laptop doesn't duplicate it)."""
        p = self.get_prop(pid)
        if p:
            return p
        sch = self.bus.shared.get("schedule")
        p = {"id": pid, "status": "running", "created": time.time(), "thread": [], "body": "", "headline": "",
             "author_person": self.person, "stage": stage_of(sch, time.time()), **fields}
        p.setdefault("decider", p.get("author_person"))
        await self.save_prop(p)
        return p

    async def build_notes(self, t0: int):
        mine = [(i, x) for i, x in enumerate(BUILD_NOTES, 1) if x[0] == self.person]
        for i, (who, agent, name) in mine:
            task = next((t for (pp, pr, ag, t) in DISPATCH.get("b0", []) if ag == agent), "")
            if task:
                first = f"Started at minute 0. Plan: {task}"
            else:   # this agent's first task comes later in the build hour
                at = next((int(k[1:]) for k in sorted(DISPATCH, key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)
                           if k.startswith("b") and any(ag == agent for (_, _, ag, _) in DISPATCH[k])), None)
                t1 = next((t for k in DISPATCH if k == f"b{at}" for (_, _, ag, t) in DISPATCH[k] if ag == agent), "")
                first = (f"Starts at minute {at}: {t1}" if at is not None else "Starts when its first task arrives.")
            await self.tile(f"build-{i}", f"Build · {name}", "in progress" if task else "starts later", owner=agent, stage="Build")
            continue
            await self.ensure_note(f"B{i}-{t0}", kind="build", stage="Build", owner=self.owner_overseer(who),
                                   status="running" if task else "planned",
                                   author=agent, title=f"Build {i} of {len(BUILD_NOTES)} · {name}",
                                   headline=f"{name}: {agent.split('-', 1)[1].title()} is on it.",
                                   thread=[{"who": "Clock", "at": time.time(), "action": "update",
                                            "text": first}])

    # ---------------- the progress board: plain tiles ("Round 1 data · in progress"), no prompting, no context
    def tiles(self) -> list[dict]:
        out = [v for k, v in self.bus.shared.items() if k.startswith("tile:") and isinstance(v, dict)]
        return sorted(out, key=lambda t: t.get("updated", 0), reverse=True)

    async def tile(self, tid: str, label: str, state: str, owner: str | None = None, stage: str | None = None):
        """Create or update one progress tile (shared by both laptops). Clicking it opens its owner agent."""
        cur = self.bus.shared.get("tile:" + tid) or {}
        if cur.get("state") == state and cur.get("label") == label:
            return
        t = {"id": tid, "label": label, "state": state, "owner": owner or cur.get("owner"),
             "stage": stage or cur.get("stage") or stage_of(self.bus.shared.get("schedule"), time.time()),
             "created": cur.get("created") or time.time(), "updated": time.time()}
        self.bus.shared["tile:" + tid] = t
        self.emit("shared", {"tiles": True})
        await self.bus.set_shared("tile:" + tid, t)

    async def close_build_notes(self, sch: dict):
        """Build notes end on their own: Build 1 once a bot is active on the portal, Build 4 once the round card has run,
        and every Build note at minute 60 (the build hour is over; open work moves to the round notes)."""
        t0 = int(sch["start"])
        over = time.time() >= sch["start"] + 60 * 60 * sch.get("scale", 1.0)
        act = (self.bus.shared.get("portal_active") or {}).get("filename")
        for i, (who, agent, name) in enumerate(BUILD_NOTES, 1):
            if who != self.person:
                continue
            t = self.bus.shared.get(f"tile:build-{i}") or {}
            if not t or t.get("state") == "done":
                continue
            if (agent == "d-platform" and act and "v1" in name) or (agent == "s-data" and self.card_ok and "card" in name.lower()) or over:
                await self.tile(f"build-{i}", t["label"], "done")

    async def note_append(self, pid: str, who: str, text: str, action: str = "update", **fields):
        if who not in PEOPLE.values() and who not in ("Portal", "Clock", "Hub"):
            self.note_pending.pop(pid, None)   # an agent answered in this note
        p = self.get_prop(pid)
        if not p or p.get("status") == "removed":
            return
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": action, "text": text[:12000]})
        p.update(fields)
        await self.save_prop(p)

    def bots_for_menu(self) -> list[dict]:
        """The newest 40 bots, plus the live and the active bot whatever their age (Dylan must always find them)."""
        allb = self.bots()
        keep = {norm_bot((self.bus.shared.get("live") or {}).get("filename")), norm_bot((self.bus.shared.get("portal_active") or {}).get("filename"))}
        top = allb[:40]
        return top + [b for b in allb[40:] if norm_bot(b["name"]) in keep]

    def bots(self) -> list[dict]:
        out = [dict(v, name=k[4:]) for k, v in self.bus.shared.items() if k.startswith("bot:") and isinstance(v, dict)]
        return sorted(out, key=lambda b: b.get("at", 0), reverse=True)

    async def register_bot(self, file: str, status: str, note: str = "", by: str = ""):
        name = bot_name(file)
        if name.lower() in ("live", "latest", "current", "active", "best", "agent", "agent.py", "bot", "?"):
            return   # an alias or a source file, not a bot
        prev = self.bus.shared.get("bot:" + name) or {}
        v = {"file": file, "status": status, "note": note[:300] or prev.get("note", ""), "by": by or prev.get("by", ""),
             "at": prev.get("at") or time.time(), "updated": time.time()}
        f = self.find_bot_file(file)
        if prev.get("status") == v["status"] and prev.get("file") == v["file"] and not note and \
                (not f or status != "ready" or prev.get("size") == f.stat().st_size):
            return
        if f and status == "ready":
            v["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
            v["size"] = f.stat().st_size
            asyncio.create_task(self.store_bot_file(name, f))
        self.bus.shared["bot:" + name] = v
        asyncio.create_task(self.tile("bot-" + name, f"Bot {name}", {"building": "in progress", "testing": "testing", "ready": "done",
                                                                      "failed": "failed"}.get(status, status), owner=by if by in self.agents or by in ROSTER_NAMES else "d-platform"))
        self.emit("shared", {"bots": True})
        await self.bus.set_shared("bot:" + name, v)
        if status == "ready" and f and not self.bus.shared.get("live") and self.person == "dylan" and re.fullmatch(r"v\d+", name):
            await self.make_live(file, "hub: the first legal bot", "the first released bot; upload it so we never score zero", tell=True)

    def find_bot_file(self, file: str) -> Path | None:
        """The bot's zip on this laptop: the path as given (repo-relative), else any releases/<name>.zip in the repo
        or an agent's worktree."""
        cands = [self.repo / file, self.repo / "releases" / (bot_name(file) + ".zip")]
        cands += [a.cwd / "releases" / (bot_name(file) + ".zip") for a in self.agents.values()]
        return next((c for c in cands if c.is_file() and c.suffix == ".zip"), None)

    def file_store(self):
        import modal
        return modal.Dict.from_name("avalon-files" + self.bus.ns, create_if_missing=True)

    async def take_upload(self, name: str, data: bytes, who: str, notify: bool = True) -> dict:
        """A file a human dropped into the Chat: saved here, copied to the shared store (both laptops can fetch it),
        and handed to the Chat with instructions to route it."""
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name)[:80] or "file"
        fid = "F" + new_id()[1:7].upper()
        d = self.repo / "inbox"
        d.mkdir(exist_ok=True)
        path = d / f"{fid}-{safe}"
        path.write_bytes(data)
        shared = len(data) <= 80_000_000
        if shared:   # copied for the other laptop in the background: the Chat must not wait on the link
            async def share():
                try:
                    await asyncio.wait_for(self.file_store().put.aio(fid, {"name": safe, "data": data}), 120)
                except Exception as e:  # noqa: BLE001
                    self.note_error("file-share", e)
            asyncio.create_task(share())
        kind = ("hand data" if re.search(r"\.(gz|jsonl|csv|json|txt|log)$", safe, re.I) else
                "image" if re.search(r"\.(png|jpe?g|gif|webp|heic)$", safe, re.I) else "file")
        ov = next((a for a in self.agents.values() if a.name.endswith("overview")), None)
        if ov and notify:
            await ov.human(f"[attached {kind}: {safe}, {len(data) // 1024} KB, saved at {path}"
                           + (f", shared as file id {fid} (agents on the other laptop: fetch_file('{fid}'))" if shared else "")
                           + "] Route it to the right agent now (see your role).", who)
        return {"id": fid, "path": str(path), "shared": shared, "kind": kind, "name": safe, "kb": len(data) // 1024}

    def bot_store(self):
        import modal
        return modal.Dict.from_name("avalon-botfiles" + self.bus.ns, create_if_missing=True)

    async def store_bot_file(self, name: str, f: Path):
        """Keep a copy of each ready bot where both laptops can download it (fetched only on demand)."""
        try:
            data = f.read_bytes()
            if len(data) <= 8_000_000:
                await asyncio.wait_for(self.bot_store().put.aio(name, data), 60)
        except Exception:  # noqa: BLE001
            pass

    async def bot_bytes(self, name: str) -> bytes | None:
        b = self.bus.shared.get("bot:" + name) or {}
        f = self.find_bot_file(b.get("file") or name)
        if f:
            return f.read_bytes()
        try:
            return await asyncio.wait_for(self.bot_store().get.aio(name), 25)
        except Exception:  # noqa: BLE001
            return None

    async def scan_releases(self):
        """Every zip in the repo's releases/ is a bot that exists (Platform packs releases there)."""
        await self.bus.synced.wait()
        while True:
            try:
                for z in sorted((self.repo / "releases").glob("*.zip")):
                    if z.is_symlink() or not re.fullmatch(r"v\d+", z.stem):
                        continue   # aliases, not bots
                    cur = self.bus.shared.get("bot:" + bot_name(z.name)) or {}
                    if cur.get("status") != "failed" and (cur.get("status") != "ready" or cur.get("size") != z.stat().st_size):
                        await self.register_bot(cur.get("file") or "releases/" + z.name, "ready", by=cur.get("by") or "releases/")
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(30)

    async def make_live(self, file: str, who: str, note: str = "", tell: bool = True) -> dict:
        old = self.bus.shared.get("live") or None
        v = {"filename": Path(file).name, "file": file, "sha256": "", "note": note or f"made live by {who}",
             "by": who, "at": time.time(),
             "prev": {k: old[k] for k in ("filename", "file", "by", "at") if k in old} if old else None}
        await self.bus.set_shared("live", v)
        self.emit("shared", {"live": v})
        if not tell:
            return v
        try:
            await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": "d-overview", "kind": "task",
                                 "text": f"{who} made {file} the live bot. Make sure Dylan uploads exactly that file on the "
                                         "portal and makes it active now (the portal watcher will confirm)."})
        except Exception:  # noqa: BLE001
            pass
        return v

    async def chat_ping(self, text: str):
        """Put a highlighted message in this laptop's Chat (the place the humans look), besides the bell."""
        ov = next((a for a in self.agents.values() if a.name.endswith("overview")), None)
        if ov:
            await ov.ov_log("Hub", text, urgent=True)

    async def alert_all(self, agent: str, text: str, urgent: bool, chat: bool = False):
        """An alert for both screens (the portal watcher runs on one laptop, but Dylan's hands do the uploads)."""
        await self.add_alert(agent, text, urgent)
        if urgent:
            await self.chat_ping(text)
        aid = new_id()
        await self.bus.set_shared("palert:" + aid, {"id": aid, "agent": agent, "text": text, "urgent": urgent,
                                                    "chat": chat, "from": self.person, "updated": time.time()})

    async def watch_live(self):
        """Dylan's laptop: when the live bot changes and the portal isn't running it yet, ask Dylan to upload it."""
        await self.bus.synced.wait()
        seen = (self.bus.shared.get("live") or {}).get("at")
        pseen = {k for k in self.bus.shared if k.startswith("palert:")}
        while True:
            await asyncio.sleep(3)
            rq = self.bus.shared.get("research_req")
            if isinstance(rq, dict) and rq.get("at", 0) > getattr(self, "research_done", self.boot_at) and rq.get("from") != self.person:
                self.research_done = rq["at"]
                asyncio.create_task(self.start_research(rq.get("who", "the other laptop"), relay=False))
            req = self.bus.shared.get("preflight_req")
            if isinstance(req, dict) and req.get("at", 0) > getattr(self, "preflight_done", self.boot_at - 120) and req.get("from") != self.person:
                self.preflight_done = req["at"]
                asyncio.create_task(self.preflight(req.get("who", "the other laptop"), relay=False, lag=time.time() - req["at"]))
            for k, v in list(self.bus.shared.items()):
                if k.startswith("palert:") and k not in pseen and isinstance(v, dict):
                    pseen.add(k)
                    if v.get("from") != self.person and time.time() - v.get("updated", 0) < 900:
                        await self.add_alert(v.get("agent", "s-portal"), v.get("text", ""), bool(v.get("urgent")))
                        if v.get("urgent"):
                            await self.chat_ping(v.get("text", ""))
                        elif v.get("chat"):
                            ov = next((a for a in self.agents.values() if a.name.endswith("overview")), None)
                            if ov:
                                await ov.ov_log("Hub", v.get("text", ""))
            live = self.bus.shared.get("live") or {}
            act = (self.bus.shared.get("portal_active") or {}).get("filename")
            if live.get("filename") and norm_bot(act) == norm_bot(live.get("filename")):
                for al in [x for x in self.alerts if "Upload " in x.get("text", "") and live["filename"] in x.get("text", "")]:
                    self.dismiss(al["id"])
            for al in [x for x in self.alerts if UPLOAD_ASK.search(x.get("text", "")) and not re.search(r"reject", x.get("text", ""), re.I)]:
                want = UPLOAD_ASK.search(al["text"]).group(1)
                if live.get("filename") and norm_bot(want) != norm_bot(live["filename"]):
                    self.dismiss(al["id"])   # superseded: another bot is live now
            if live.get("at") and live.get("at") != seen:
                seen = live["at"]
                act = (self.bus.shared.get("portal_active") or {}).get("filename")
                if self.person == "dylan" and norm_bot(act) != norm_bot(live.get("filename")) and live.get("by") != "deadline guard":
                    await self.add_alert("hub", f"**Upload {live['filename']} now** and make it active on the portal "
                                         f"({live.get('note') or 'new live bot'}). Download it from the Live menu (top right).", True)

    async def narrate(self, ag: "Agent", buf: list, chat_notes: set, final: bool, since: int = 1, refs: set | None = None):
        """Turn an Overseer's activity into note updates. A note chat's answer goes in word for word; everything else
        is summarized from the Overseer's own words by a fast model, so each note shows live progress."""
        async with ag.narr_lock:
            texts = [x for k, x in buf if k == "text"]
            verbatim = set()
            if final and len(chat_notes) == 1 and texts:
                nid = next(iter(chat_notes))
                await self.note_append(nid, ag.title, "\n\n".join(texts), action="reply")
                verbatim.add(nid)
            buf = buf[:1] + buf[max(1, since):]          # only what the per-minute updates haven't covered
            outputs = [x for k, x in buf if k in ("text", "msg_out", "msg_in", "tool")]
            if not outputs:
                return
            now = time.time()
            refs = set(refs if refs is not None else ag.turn_note_refs) | set(chat_notes)
            notes = [p for p in self.props() if p["id"] in refs and p["id"] not in verbatim
                     and p.get("status") not in ("removed",)][:6]   # only notes this work referred to: no guessing
            if not notes:
                return
            listing = "\n".join(f"- {p['id']}: {p.get('stage', '')} · {p['kind']} · {p['title']} (status {p['status']}); last: "
                                 + (str((p.get("thread") or [{}])[-1].get("text", ""))[:200]) for p in notes)
            act = "\n".join(f"[{k}] {x}" for k, x in buf)[-14000:]
            prompt = (f"You keep a team's board of notes up to date from what their lead agent (the Overseer) just did. "
                      f"Notes:\n{listing}\n\nThe Overseer's activity (its input, its own words, messages to/from other "
                      f"agents, tools it used):\n{act}\n\nFor each note this activity is about, write an update for the "
                      "humans: use the Overseer's and agents' own wording and every number, say what happened, what is "
                      "running and who is doing it, and what comes next. 2-6 sentences, plain language, no ids. Skip notes "
                      "it isn't about; skip anything already said in the note's last line; general news (the clock, team-wide status) "
                      "belongs to no note. Answer with JSON only: "
                      '[{"id": "<note id>", "update": "<text>"}] (an empty list if nothing new).')
            try:
                out = await one_shot(prompt, ClaudeAgentOptions(
                        model=NARRATOR_MODEL, tools=[], max_turns=1, setting_sources=[], cwd=str(self.data),
                        system_prompt="You write short, faithful progress updates. Output JSON only."), 75)
                js = json.loads(out[out.index("["):out.rindex("]") + 1]) if "[" in out else []
            except Exception as e:  # noqa: BLE001
                ag.record({"type": "note", "text": f"Note updates skipped this time ({type(e).__name__})."})
                return
            ids = {p["id"] for p in notes}
            for u in js:
                if isinstance(u, dict) and u.get("id") in ids and str(u.get("update", "")).strip():
                    await self.note_append(u["id"], ag.title, str(u["update"]).strip())

    async def note_report(self, pid: str) -> dict:
        """Answer 'what's going on with this note right now?' in readable prose, as the agents would if asked:
        a model reads the note, the owner Overseer's recent work, every agent's brief and the note's files."""
        p = self.get_prop(pid)
        if not p:
            raise ValueError("That note no longer exists.")
        if pid in self.report_busy:
            return p
        self.report_busy.add(pid)
        try:
            ov = self.agents.get(p.get("owner") or "")
            work = "" if ov else ((self.bus.shared.get("ovwork:" + (p.get("owner") or "")) or {}).get("text") or "")
            if ov:
                rows = []
                for e in ov.events[-160:]:
                    t = e.get("type")
                    if t == "text" and not e.get("sub"):
                        rows.append(f"[{hhmm(e['t'])}] Overseer: {e['text'][:1500]}")
                    elif t in ("msg_in", "msg_out"):
                        rows.append(f"[{hhmm(e['t'])}] {'from ' + str(e.get('from')) if t == 'msg_in' else 'to ' + str(e.get('to'))}: {str(e.get('text'))[:900]}")
                work = "\n".join(rows)[-16000:]
            briefs = "\n".join(f"- {a.name} ({a.state}{', status ' + str(int((time.time() - a.status_at) / 60)) + ' min old' if a.status_at else ''}): "
                               f"{a.task} | {(a.summary or '')[:500]}" for a in self.agents.values())
            briefs += "\n" + "\n".join(f"- {n} ({v.get('state')}): {v.get('task', '')} | {(v.get('summary') or '')[:500]}"
                                         for n, v in self.bus.directory.items() if v.get("person") != self.person and not v.get("service"))
            thread = "\n".join(f"[{hhmm(t['at'])}] {t['who']}: {str(t['text'])[:1200]}" for t in p.get("thread", [])[-40:])
            live = self.bus.shared.get("live") or {}
            act = self.bus.shared.get("portal_active") or {}
            prompt = (f"You are the voice of team avalon's agents in a live pokerbot competition. A teammate opened the note "
                      f"\"{p['title']}\" ({p.get('stage', '')}, {p['kind']}, status {p['status']}) and is asking: "
                      f"\"What's going on with this right now?\"\n\nAnswer them as the agents would: clear, specific, "
                      "readable prose for a smart human who hasn't been watching. Markdown with these short sections: "
                      "**Where it stands** (2-4 sentences), **What we found** (the key numbers with sample sizes and how "
                      "sure we are; say plainly when something is weak or only a hypothesis), **What's running now** (who is "
                      "doing what, and when it should land), **What's next**, and **What we need from you** (or 'Nothing "
                      "right now'). Use only facts below: never give a bot, file or person a role (challenger, live bot, ...) the material doesn't state; if the agents disagree or something was corrected, say so. No "
                      "ids or jargon a human wouldn't know; name agents by role (the analyst, the tester, the builder). "
                      f"Keep it under 350 words.\n\nLive bot chosen: {live.get('filename', 'none')}; active on the portal: "
                      f"{act.get('filename', 'unknown')}. Time now {hhmm(time.time())}.\n\nNOTE SUMMARY:\n{p.get('body') or '(none yet)'}"
                      f"\n\nNOTE CONVERSATION (latest last):\n{thread or '(empty)'}\n\nTHE OVERSEER'S RECENT WORK (latest last):\n"
                      f"{work or '(not on this laptop)'}\n\nEVERY AGENT'S CURRENT BRIEF:\n{briefs}")
            out = (await one_shot(prompt, ClaudeAgentOptions(
                    model=REPORT_MODEL, tools=[], max_turns=1, setting_sources=[], cwd=str(self.data),
                    system_prompt="You write clear, faithful status reports from the material given. Never invent facts."), 120)).strip()
            if out:
                p = self.get_prop(pid) or p
                p["report"] = {"text": out, "at": time.time(), "n": len(p.get("thread", []))}
                await self.save_prop(p)
            return p
        finally:
            self.report_busy.discard(pid)

    def owner_overseer(self, person: str) -> str:
        return ("s-" if person == "samuel" else "d-") + "overview"

    async def decision_conflict(self, p: dict, st: str, who: str, text: str) -> str:
        """Samuel and Dylan answered the same decision opposite ways: say so to both, and the rule's answer stands until
        they agree (never silently 'last click wins')."""
        other = p.get("decided_by")
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": "answer (in the Chat)", "text": text[:600]})
        p["status"], p["conflict"] = "needs_call", True
        ra = p.get("rule_answer")
        live = (self.bus.shared.get("live") or {}).get("filename")
        if ra and not same_bot(ra, live or ""):
            await self.make_live(ra, "the rule (the humans disagree)", f"decision #{p['id']}: answers conflict", tell=False)
        await self.save_prop(p)
        msg = (f"Samuel and Dylan disagree on \"{p['title']}\": {other} said {'yes' if st == 'rejected' else 'no'}, {who} "
               f"said {'yes' if st == 'approved' else 'no'}. Until you agree, the rule's answer stands"
               + (f" ({bot_name(ra)})" if ra else "") + ". Talk now and answer once in either Chat.")
        await self.alert_all(f"{self.person[0]}-clock", msg, True, chat=True)
        return msg

    async def human_act(self, pid: str, action: str, text: str) -> dict:
        p = self.get_prop(pid)
        if not p:
            raise ValueError("That note no longer exists.")
        who = PEOPLE[self.person]
        if action in ("approve", "reject") and p.get("deadline") and time.time() > p["deadline"]:
            raise ValueError("Too late: the deadline for this decision has passed, so the rule's answer applies.")
        if action in ("approve", "reject") and p.get("status") in ("approved", "rejected") and p.get("decided_by") != who and \
                (p["status"] == "approved") != (action == "approve"):
            await self.decision_conflict(p, "approved" if action == "approve" else "rejected", who, text or action)
            return p
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": action, "text": text})
        if action in ("approve", "reject", "comment"):
            await self.human_item(f"{action} on note \"{p['title']}\"" + (f": {text}" if text else ""), p["id"])
        target = p.get("owner") or p.get("author")
        if action == "approve" and p.get("deadline") and time.time() > p["deadline"]:
            raise ValueError("Too late: the deadline for this decision has passed, so the default applies.")
        if action == "approve" and p.get("bot") and CONDITIONAL.search(text or ""):
            # "yes, once the tester passes it": not live yet, so no upload ask until the Overseer confirms the condition
            p["status"], p["decided_by"], p["condition"] = "approved", who, text
            note = (f"GREENLIT ON A CONDITION by {who}: #{p['id']} use {p['bot']} only if: \"{text}\". It is NOT live yet "
                    "and Dylan has not been asked to upload. Check the condition; when it holds, declare_live it (that asks "
                    "Dylan to upload) and say so in the note; if it can't hold by T-3, the live bot stays and say why.")
        elif action == "approve" and p.get("bot"):
            await self.make_live(p["bot"], who, f"greenlit on note #{p['id']}", tell=False)
            p["status"], p["decided_by"] = "approved", who
            p.pop("conflict", None)
            note = f"GREENLIT by {who}: #{p['id']} use {p['bot']}. It is now the declared live bot; Dylan uploads it."
        elif action == "approve":
            p["status"], p["decided_by"] = "approved", who
            note = f"GREENLIT by {who}: #{p['id']} \"{p['title']}\"." + (f" Note: {text}" if text else "") + " Go ahead."
        elif action == "reject":
            p["status"], p["decided_by"] = "rejected", who
            p.pop("conflict", None)
            note = f"REJECTED by {who}: #{p['id']} \"{p['title']}\"." + (f" Reason: {text}" if text else "") + " Don't do it."
        elif action == "comment":
            if p["status"] == "needs_call":
                p["status"] = "revise"
            note = f"{who} on #{p['id']} \"{p['title']}\": {text}"
        elif action == "remove":
            was = p["status"]
            p["status"], p["decided_by"] = "removed", who
            note = ((f"{who} closed note #{p['id']} \"{p['title']}\" (still open work: stop it unless it's needed elsewhere, "
                     f"and tell the agents). Its full conversation is in {self.data / 'board' / (p['id'] + '.md')}; fold "
                     "anything still relevant into your PLAN file.") if was in OPEN or was == "blocked" else "")
        elif action == "close":
            p["status"] = "done"
            note = f"{who} closed #{p['id']} \"{p['title']}\"." + (f" {text}" if text else "")
        else:
            raise ValueError("unknown action")
        await self.save_prop(p)
        if action == "remove":
            target = p.get("owner") if str(p.get("owner", "")).endswith("overview") else self.owner_overseer(p.get("author_person") or self.person)
        if note and target and target.startswith(("s-", "d-")):
            try:
                await self.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": target,
                                     "kind": "fyi" if action == "remove" else "task", "note": p["id"],
                                     "text": note + ("" if action == "remove" else " (Update the note with update_proposal.)")})
            except Exception:  # noqa: BLE001
                pass
        return p

    async def card_ask(self, pid: str, text: str) -> dict:
        p = self.get_prop(pid)
        if not p:
            raise ValueError("That note no longer exists.")
        who = PEOPLE[self.person]
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": "ask", "text": text})
        await self.human_item(f"on note \"{p['title']}\": {text}", p["id"])
        await self.save_prop(p)
        ov = p.get("owner") if str(p.get("owner", "")).endswith("overview") else self.owner_overseer(p.get("author_person") or self.person)
        recent = "\n".join(f"  {t['who']}: {str(t['text'])[:400]}" for t in p["thread"][-7:-1])
        self.note_pending[p["id"]] = {"at": time.time(), "who": who, "text": text[:300], "to": ov}
        deciding = p.get("status") in ("needs_call", "revise") and p.get("kind") in ("bot", "question")
        decide = ("\nTHIS NOTE IS WAITING FOR THE HUMANS' DECISION. If this message clearly decides it (yes or no; which bot), "
                  f"record it now: update_proposal(id='{p['id']}', status='approved' or 'rejected', decided_by='{who}')"
                  + (" (approved on a Which-bot note makes that bot live and asks Dylan to upload it)" if p.get("bot") else "") +
                  ". If it sets a condition, record 'approved' only once the condition holds and say so here. If it is a "
                  "question or unclear, answer it plainly and ask for a clear decision. Never record a decision the human "
                  "didn't make.\n") if deciding else ""
        await self.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": ov, "kind": "task", "note": p["id"], "text": (
            f"[note #{p['id']} \"{p['title']}\" ({p.get('stage', '')}) chat] {who}: {text}\n" + decide
            + (f"Recent in this note:\n{recent}\n" if recent else "") +
            "\nYour reply text in this turn is shown in the note word for word, so answer the human directly and fully "
            "in plain language (no update_proposal needed for the answer). If this turn has messages from more than one "
            "note, answer each one with update_proposal(id, note=<answer>) instead. If it's an instruction or question that needs "
            "work, send it to the right agent(s) now, say who is doing what, and post the result here when it's back "
            "(update_proposal(id, note=...)).")})
        return p

    def thread_text(self, p: dict, limit: int = 9000) -> str:
        rows = [f"[{hhmm(t['at'])}] {t['who']}: {t['text']}" for t in p.get("thread", [])]
        txt = (f"Summary: {p['body']}\n" if p.get("body") else "") + "\n".join(rows)
        return txt[-limit:]

    async def new_idea(self, title: str, body: str, for_person: str) -> dict:
        p = {"id": "P" + new_id()[1:7].upper(), "kind": "idea", "title": title[:160], "body": body[:6000],
             "author": PEOPLE[self.person], "author_person": self.person, "owner": self.owner_overseer(for_person),
             "status": "new", "created": time.time(), "thread": [],
             "stage": stage_of(self.bus.shared.get("schedule"), time.time())}
        await self.save_prop(p)
        await self.bus.send({"id": new_id(), "from": PEOPLE[self.person], "from_kind": "human", "to": p["owner"],
                             "kind": "task", "note": p["id"], "text": (
            f"NEW IDEA from {PEOPLE[self.person]} (note #{p['id']}): {p['title']}\n{body}\n\nHuman ideas come first. "
            "Your reply text is posted in that note word for word: say what you'll do and who runs it. Run it with your "
            "workers / subagents / Modal and post results in the same note (update_proposal(id, note=..., summary=...)). "
            "If it leads to a new bot, ask with propose(kind='bot', bot=...).")})
        return p

    # ---------------- the Chat: commands the hub handles itself (no model in the loop)
    async def chat_command(self, text: str, who: str) -> str | None:
        """'The competition starts now' starts the clock (once); 'run the check' runs the pre-flight. Returns what the
        hub did, or None to leave the message to the Chat."""
        if re.fullmatch(r"\s*reset the clock\s*[.!]*\s*", text, re.I):
            if (self.bus.shared.get("rounds_seen") or {}) and any(k.startswith("Round") for k in self.bus.shared.get("rounds_seen")):
                return "A scored round has already been seen on the portal, so I won't clear the clock. Give the right time instead."
            await self.bus.set_shared("schedule", {})   # empty, not None: the other laptop only takes non-None values
            return "Clock cleared on both laptops. Say 'the competition starts now' (or the announcement time) at minute 0."
        if PREFLIGHT_RX.search(text) and len(text) < 120:
            asyncio.create_task(self.preflight(who))
            return "Running the pre-flight check on both laptops; results appear here in about a minute."
        hm = re.search(r"\bhands?(?:[- ]history)?\s+(?:link|url)\s*[:=]?\s*(https?://\S+)", text, re.I)
        if hm:
            if not self.portal:
                return "The portal watcher runs on Samuel's laptop: paste the hands link into Samuel's Chat."
            return self.portal.set_hands_url(hm.group(1))
        if PREP_RX.search(text) and len(text) < 160 and "?" not in text and \
                not re.search(r"\b(don'?t|do not|not|never|did|have you|has it|was it|yet)\b", text, re.I):
            prev = self.bus.shared.get("research_req") or {}
            if prev.get("at") and time.time() - prev["at"] < 12 * 3600:
                return f"The research already started at {hhmm(prev['at'])} ({prev.get('who')}); its notes are in notes/pre/."
            n = await self.start_research(who)
            return (f"Pre-event research started: {n} workers on this laptop have their topics (notes only, no bot code); "
                    "the other laptop's workers start theirs too. Notes land in notes/pre/.")
        if not self.bus.shared.get("schedule") and START_RX.search(text) and "?" not in text and \
                not re.search(r"\b(in \d+\s*(?:min|minutes|m)\b|will|when|soon|later|tomorrow|until|by \d)", text, re.I):
            m = AT_RX.search(text)
            try:
                s = await self.start_now(who, at=m.group(1) if m else None)
            except ValueError as e:
                return f"Couldn't read that time ({e}). Say e.g. 'the variant was announced at 14:02'."
            return f"Clock started: {s} Both laptops now follow it, and your Overseer has the game plan."
        return None

    async def pull_round_files(self):
        """Dylan's laptop: each round's results and hand sample, copied from the store into a local folder, and the
        agents that need them told the paths (the portal watcher runs on Samuel's laptop only)."""
        if self.portal:
            return
        rf = self.bus.shared.get("round_files") or {}
        got = getattr(self, "pulled", None)
        if got is None:
            got = self.pulled = set(load_json(self.data / "pulled.json", []))
        for stage, v in rf.items():
            if stage in got or not isinstance(v, dict) or time.time() - v.get("at", 0) > 4 * 3600:
                continue
            got.add(stage)
            atomic_write(self.data / "pulled.json", json.dumps(sorted(got)))
            out = self.portal_data / "from-samuel" / stage_slug(stage)
            paths = []
            try:
                out.mkdir(parents=True, exist_ok=True)
                for name, fid in (v.get("files") or {}).items():
                    d = await asyncio.wait_for(self.file_store().get.aio(fid), 60)
                    if d:
                        (out / name).write_bytes(d["data"])
                        paths.append(str(out / name))
            except Exception as e:  # noqa: BLE001
                self.note_error("pull-round", e)
                got.discard(stage)   # try again next time
                continue
            for nm in ("d-challenger", "d-builder", "d-overview"):
                ag = self.agents.get(nm)
                if ag and paths:
                    await ag.add_item({"kind": "portal", "wake": nm == "d-challenger", "text": f"Round data for {stage} is on "
                                       f"this laptop: {v.get('line', '')}\n" + "\n".join(f"File: {x}" for x in paths) +
                                       "\n(Copied from Samuel's laptop; hand data stays out of git.)"})

    async def start_research(self, who: str, relay: bool = True) -> int:
        """Part 0: each worker's pre-event research topic (notes only). Started by a human, on both laptops, once."""
        if relay:
            await self.bus.set_shared("research_req", {"at": time.time(), "from": self.person, "who": who})
        n = 0
        for ag_name, _, task in worker_tasks("pre", self.person):
            ag = self.agents.get(ag_name)
            if ag is None:
                continue
            await ag.add_item({"kind": "clock", "wake": True, "text": f"[pre-event, asked by {who}] Your task now: {task}\n"
                               "report_progress(item, 'in progress') now and 'done' when finished; tell your Chat the path."})
            await self.tile(f"pre-{ag_name}", f"Pre-event research · {ag.title}", "in progress", owner=ag_name, stage="Before the start")
            if ag.state == "stopped" and not ag.paused:
                await ag.start()
            n += 1
        ov = next((a for a in self.agents.values() if a.name.endswith("overview")), None)
        if ov:
            await ov.add_item({"kind": "hub", "wake": False, "text": (
                f"{who} started the pre-event research: each worker has a topic (DISPATCH 'pre'), notes in notes/pre/. "
                + ("When they land, merge them into notes/plan.md (5 minutes, one page): what we expect today, what we'd "
                   "do differently from the plan, open questions. " if self.person == "samuel" else "")
                + "Read the contrarian memo (d-challenger) before minute 0.")})
        return n

    async def start_now(self, who: str, at: str | None = None) -> str:
        """Minute 0 (now, or at HH:MM), the Overseer told to start the plan. Only when no clock is set."""
        s = await self.clock.set_start(at or "", 6, self.default_scale, t0=None if at else time.time())
        await self.overseer().human("Start building: the variant is announced" + (f" (at {at})" if at else " now") +
                                    " (minute 0). Kick off the build-hour plan.", who)
        return s

    async def preflight(self, who: str, relay: bool = True, lag: float | None = None):
        """Check, for real, everything Sunday depends on; post the results in this laptop's Chat (and ask the other
        laptop to run its own)."""
        if relay:
            await self.bus.set_shared("preflight_req", {"at": time.time(), "from": self.person, "who": who})
        rows = []
        def row(ok_, what, detail=""):
            rows.append(f"{'✅' if ok_ else '❌'} **{what}**" + (f": {detail}" if detail else ""))
        other = [n for n, v in self.bus.directory.items() if v.get("person") != self.person and not v.get("service")
                 and time.time() - v.get("seen", 0) < 120]
        row(self.bus.online and bool(other), "Link to the other laptop",
            f"{len(other)} of its agents seen" if other else ("link up, but the other laptop's hub isn't running"
                                                            if self.bus.online else self.bus.error or "down"))
        if self.portal:
            P = self.portal
            try:
                await asyncio.wait_for(P.identify(), 30)
                rounds = (await P.aget(f"/competitions/{P.cid}/tournaments"))["items"]
                team = await P.aget(f"/teams/{P.team}")
                row(True, "Portal: read access", f"team {P.team_name}, competition {P.comp_name}, {len(rounds)} round(s) listed, "
                    f"active bot {team.get('active_filename') or 'none'}")
                done = sorted([r for r in rounds if r.get("completed_at")], key=lambda r: r["created_at"])
                if done:
                    tmp = self.data / "preflight"
                    tmp.mkdir(exist_ok=True)
                    files = await asyncio.wait_for(P.fetch_hands(done[-1]["id"], tmp, small_first=True), 120)
                    row(bool(files), "Portal: hand-history download",
                        f"{Path(files[0]).stat().st_size // 1024} KB saved and verified" if files else
                        "FAILED. On the real portal, copy the Download link after practice 1 and paste it into Samuel's Chat as 'hands link: <the link>' (SUNDAY.md step 7)")
                else:
                    row(True, "Portal: hand-history download", "no finished round to try yet; the watcher downloads each round as it ends")
            except Exception as e:  # noqa: BLE001
                row(False, "Portal", f"{type(e).__name__}: {e} (check the key file and --portal-base)")
        else:
            row(True, "Portal", "watched from Samuel's laptop")
        try:
            out = await one_shot("Reply with exactly: OK", ClaudeAgentOptions(model=NARRATOR_MODEL, tools=[], max_turns=1,
                                 setting_sources=[], cwd=str(self.data), system_prompt="Reply OK."), 90)
            row("OK" in out.upper(), "Claude", "answering" if "OK" in out.upper() else f"unexpected reply: {out[:80]}")
        except Exception as e:  # noqa: BLE001
            row(False, "Claude", f"{type(e).__name__}: is `claude` logged in on this laptop?")
        if self.codex:
            row(not self.codex.broken and bool(self.codex.bin), "Codex", self.codex.broken or ("ready" if self.codex.bin else "not installed (optional)"))
        try:
            r = await asyncio.to_thread(subprocess.run, ["git", "-C", str(self.repo), "status", "--short"], capture_output=True, text=True, timeout=20)
            probe = self.repo / ".preflight"
            probe.write_text("ok")
            probe.unlink()
            want = ["START_HERE.md", "DECISION_RULES.md", "FIRST_PROMPT.md", "TWIST_NOTES.md", "FINGERPRINTING.md"]
            miss = [f for f in want if not (self.repo / f).exists() and not (self.repo / "docs" / f).exists()]
            row(r.returncode == 0 and not miss, "Team repo", "git works, writable" + (f"; MISSING {', '.join(miss)}" if miss else ", plan docs present"))
        except Exception as e:  # noqa: BLE001
            row(False, "Team repo", f"{type(e).__name__}: {e}")
        free = shutil.disk_usage(str(self.data)).free / 1e9
        row(free > 5, "Disk space", f"{free:.0f} GB free")
        sch = self.bus.shared.get("schedule")
        stale = bool(sch) and time.time() - sch["start"] > 10 * 3600
        row(not stale, "Clock", ("set on an earlier day (minute 0 was " + time.strftime('%a %H:%M', time.localtime(sch['start']))
                                 + "): type 'reset the clock' before the event") if stale else
            f"minute 0 = {time.strftime('%H:%M:%S', time.localtime(sch['start']))}" if sch else
            "not started (tell the Chat 'the competition starts now' at the announcement)")
        mine, theirs = self.bus.shared.get("codever:" + self.person), next(
            (v for k, v in self.bus.shared.items() if k.startswith("codever:") and k != "codever:" + self.person), None)
        if theirs:
            row(mine == theirs, "Same hub code on both laptops", f"{mine} here, {theirs} there" + ("" if mine == theirs else
                ": the older one runs `git pull` and restarts its hub"))
        if lag is not None and lag < 300:
            row(-5 < lag < 60, "Laptop clocks agree", f"the request took {lag:.0f} s to arrive" if -5 < lag < 60 else
                f"they differ by about {abs(lag):.0f} s: System Settings → General → Date & Time → Set automatically, on both")
        bad = sum(r.startswith("❌") for r in rows)
        ov = next((a for a in self.agents.values() if a.name.endswith("overview")), None)
        if ov:
            await ov.ov_log("Hub", f"**Pre-flight check on {PEOPLE[self.person]}'s laptop: "
                            + ("everything works.**" if not bad else f"{bad} problem(s).**") + "\n\n" + "\n".join("- " + r_ for r_ in rows), urgent=bool(bad))
        if bad:
            await self.add_alert("hub", f"Pre-flight: {bad} problem(s) on this laptop. See the Chat.", True)

    # ---------------- nothing a human asks goes unanswered
    async def watch_unanswered(self):
        now = time.time()
        for a in self.agents.values():
            if not a.pending_q:
                continue
            q = a.pending_q[0]
            age = now - q["at"]
            if not a.name.endswith("overview"):   # a worker the person messaged directly
                replying = a.state == "working" and getattr(a, "turn_started", 0) > q["at"] and getattr(a, "turn_text_n", 0)
                if age > 150 and not q.get("nudged") and not replying:
                    q["nudged"] = True
                    await a.add_item({"kind": "hub", "wake": True, "urgent": False, "text": f"{q['who']} asked you at {hhmm(q['at'])} "
                                      f"and hasn't had a reply: \"{q['text']}\". Reply now in plain text: the answer, or 'Working "
                                      "on it: <what>, ready by HH:MM'. Then carry on."})
                    if a.state == "stopped" and not a.paused:
                        await a.start()
                elif age > 360 and not q.get("told"):
                    q["told"] = True
                    ov = next((x for x in self.agents.values() if x.name.endswith("overview")), None)
                    if ov:
                        await ov.ov_log("Hub", f"{a.title} still hasn't replied to {q['who']}'s message from {hhmm(q['at'])} "
                                        f"(\"{q['text'][:80]}\"). I've asked it again; open {a.title} to see its work.")
                continue
            if age > 150 and a.state in ("idle", "done", "stopped", "error") and not q.get("nudged"):
                q["nudged"] = True   # it finished a turn without answering: ask again
                await a.add_item({"kind": "hub", "wake": True, "text": f"You haven't answered {q['who']}'s message from "
                                  f"{hhmm(q['at'])}: \"{q['text']}\". Answer it now, plainly; if it's an instruction, say "
                                  "who is doing it and when it will be done."})
                if a.state == "stopped" and not a.paused:
                    await a.start()
            elif age > 360 and not q.get("told"):
                q["told"] = True
                await a.ov_log("Hub", f"Still no answer to your message from {hhmm(q['at'])} (\"{q['text'][:80]}\"). "
                               + ("The Chat is busy with a long turn; it answers when that ends." if a.state == "working"
                                  else "I've asked it again."))
        for pid, q in list(self.note_pending.items()):
            age = now - q["at"]
            if age > 300 and not q.get("nudged"):
                q["nudged"] = True
                try:
                    await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": q["to"], "kind": "task",
                                         "note": pid, "text": f"{q['who']} asked in note #{pid} at {hhmm(q['at'])} and has no "
                                         f"answer yet: \"{q['text']}\". Answer it in the note now (update_proposal(id='{pid}', "
                                         "note=...)); if work is needed, say who is doing it and when."})
                except Exception as e:  # noqa: BLE001
                    self.note_error("note-nudge", e)
            elif age > 900 and not q.get("told"):
                q["told"] = True
                await self.chat_ping(f"No answer yet to {q['who']}'s question in note #{pid} (\"{q['text'][:80]}\"). "
                                     "I've reminded the Overseer; ask in the Chat if it's urgent.")

    # ---------------- contradictions surface on their own
    async def consistency_check(self):
        """Every 4 minutes once the event runs: a cheap model reads the facts on screen and names any two that can't
        both be true (clock vs portal, live vs active bot, a summary vs a later result, an instruction not followed)."""
        sch = self.bus.shared.get("schedule")
        now = time.time()
        if not sch or now - getattr(self, "last_consistency", 0) < 240 or self.view_only:
            return
        self.last_consistency = now
        live, act = self.bus.shared.get("live") or {}, self.bus.shared.get("portal_active") or {}
        facts = [f"Time now {hhmm(now)}; clock minute 0 {hhmm(sch['start'])}; 1 event-minute = {60 * sch.get('scale', 1.0):.0f} real "
                 f"seconds (so 'minute N' is minute 0 + N event-minutes); stage {stage_of(sch, now)}; next step: "
                 f"{(self.clock.next_step() or (0, 'none'))[1]}",
                 f"Declared live bot: {live.get('filename') or 'none'} (set {hhmm(live['at']) if live.get('at') else '-'}); "
                 f"active on the portal: {act.get('filename') or 'unknown'}"]
        for p in [p for p in self.props() if p.get("status") in OPEN][:8]:
            facts.append(f"Note #{p['id']} [{p.get('kind')}/{p.get('status')}] {p.get('title')}: summary: {(p.get('body') or '')[:300]} | "
                         f"latest: " + " / ".join(f"{t.get('who')}: {str(t.get('text'))[:160]}" for t in (p.get("thread") or [])[-2:]))
        for a in self.agents.values():
            facts.append(f"Agent {a.name} [{a.state}] status {(now - a.status_at) / 60:.0f} min old: {a.task[:160]}" if a.status_at
                         else f"Agent {a.name} [{a.state}]: {a.task[:160]}")
        humans = [x for x in self.ledger() if x.get("type") == "human"][-6:]
        facts += [f"Human instruction ({hhmm(x.get('at', 0))}): {str(x.get('claim'))[:200]}" for x in humans]
        prompt = ("These are the facts on a team's screen during a live competition. List only real contradictions that "
                  "could change a decision or an action in the next 20 minutes: two statements that can't both be true now "
                  "(different bots, times, numbers or results for the same thing), or a human instruction that the current "
                  "state ignores. Ignore note statuses (running/planned/done) and agent states (idle/stopped/working): those "
                  "lag by design; so do agents' briefs vs what they're doing. A declared live bot that isn't active yet "
                  "within 10 minutes of being declared is an upload in progress, not a conflict. Not stale wording, not "
                  "style. At most 1 (the most important). For each: what conflicts "
                  "and what to check or fix, in one plain sentence each. JSON only: [{\"issue\": \"...\", \"fix\": \"...\"}] "
                  "or [] if none.\n\n" + "\n".join(facts))
        try:
            out = await one_shot(prompt, ClaudeAgentOptions(model=NARRATOR_MODEL, tools=[], max_turns=1, setting_sources=[],
                                 cwd=str(self.data), system_prompt="You find contradictions. Output JSON only."), 90)
            items = json.loads(out[out.index("["):out.rindex("]") + 1]) if "[" in out else []
        except Exception as e:  # noqa: BLE001
            self.note_error("consistency", e)
            return
        self.checked_issues = {k: t for k, t in self.checked_issues.items() if now - t < 1800}
        words = lambda x: set(re.findall(r"[a-z0-9.]+", x.lower())) - {"the", "a", "and", "is", "to", "of", "but", "for", "in", "it"}   # noqa: E731
        new = []
        for it in items[:1]:
            if not isinstance(it, dict) or not it.get("issue"):
                continue
            key = re.sub(r"\W+", " ", str(it["issue"]).lower())[:120]
            w = words(key)
            if any(len(w & words(k)) / max(1, len(w | words(k))) > 0.45 for k in self.checked_issues):
                continue   # the same issue, reworded
            self.checked_issues[key] = now
            new.append(f"- {it['issue']} → {it.get('fix', '')}")
        if new:
            text = "**Something doesn't add up:**\n" + "\n".join(new)
            ov = next((a for a in self.agents.values() if a.name.endswith("overview")), None)
            if ov:
                await ov.ov_log("Hub", text)
            await self.overseer().add_item({"kind": "hub", "wake": False, "text": "[consistency check] " + text +
                                            "\nResolve each (check the facts, fix the wrong one, tell the humans in a note)."})

    async def watch_stalls(self):
        """An agent whose turn has produced nothing for STALL_S (a hung connection, a stuck tool) is interrupted, then
        disconnected if that doesn't end it; its input is retried (the retry tells it to check what already happened)."""
        now = time.time()
        for a in self.agents.values():
            if a.state != "working" or a.client is None or not a.last_msg_at:
                continue
            quiet = now - a.last_msg_at
            long_turn = now - (a.turn_started or now)
            if long_turn > LONG_TURN_S and getattr(a, "long_warned", 0) != a.turn_started and not a.name.endswith("overview"):
                a.long_warned = a.turn_started   # busy but maybe not progressing: the Overseer looks, nobody is rushed
                await self.overseer().add_item({"kind": "hub", "wake": False, "text": (
                    f"{a.title} has been on one turn for {long_turn / 60:.0f} min (task: {a.task[:120]}). Read its brief: if "
                    "it's progressing, leave it; if it's looping or the job is too big, split it (a helper, Modal, Codex) "
                    "or re-scope. Don't tell it to hurry.")})
            if quiet > (6 * 60 if a.name.endswith("overview") else STALL_S) and not a.stall_kicked:   # a lead runs no long tools
                a.stall_kicked = now
                a.record({"type": "error", "text": f"No output for {quiet / 60:.0f} min: interrupting (stall watchdog)."})
                a.interrupted = False
                try:
                    await asyncio.wait_for(a.client.interrupt(), 20)
                except Exception:  # noqa: BLE001
                    pass
                await self.overseer().add_item({"kind": "hub", "wake": False, "text": f"{a.title} produced nothing for "
                                                f"{quiet / 60:.0f} min and was interrupted; its input will be retried."})
            elif a.stall_kicked and now - a.stall_kicked > 90 and a.last_msg_at < a.stall_kicked:
                a.stall_kicked = now + 3600   # once
                try:
                    await asyncio.wait_for(a.client.disconnect(), 10)   # the turn loop sees the error and retries
                except Exception:  # noqa: BLE001
                    pass
                await self.add_alert(a.name, f"{a.title} was stuck (no output for {quiet / 60:.0f} min); the hub "
                                     "restarted its connection and it retries.", False)

    async def expire_decisions(self):
        now = time.time()
        for p in self.props():
            if p.get("status") in ("needs_call", "revise") and p.get("deadline") and now > p["deadline"] and \
                    (p.get("author") in self.agents):
                p["status"] = "expired"
                ra = p.get("rule_answer") if p.get("kind") == "bot" else None
                live = (self.bus.shared.get("live") or {}).get("filename")
                if ra and not same_bot(ra, live or ""):   # the hub applies the rule itself: no LLM hop at T-5
                    await self.make_live(ra, "the rule (no answer by the deadline)", f"decision #{p['id']}: the rule's answer", tell=True)
                    p.setdefault("thread", []).append({"who": "Hub", "at": now, "action": "rule",
                                                       "text": f"No answer: the rule's answer {bot_name(ra)} is now the declared live bot."})
                    await self.alert_all(f"{self.person[0]}-clock", f"No answer on \"{p['title']}\": the rule's answer "
                                         f"{bot_name(ra)} plays. Dylan uploads it.", True, chat=True)
                await self.tile("decide-" + p["id"], ("Bot choice: " + bot_name(p["bot"])) if p.get("bot") else ("Question: " + p["title"][:60]),
                                "no answer: the rule decides")
                p.setdefault("thread", []).append({"who": "Hub", "at": now, "action": "expire",
                                                   "text": "No human answer before the deadline: the pre-registered rule decides."})
                await self.save_prop(p)
                a = self.agents[p["author"]]
                await a.add_item({"kind": "hub", "wake": True, "urgent": True, "text": (
                    f"Decision #{p['id']} \"{p['title']}\" got no human answer before its deadline. " +
                    (f"The hub applied its rule answer: {bot_name(ra)} is the declared live bot; tell Dylan in one line."
                     if ra and not same_bot(ra, live or "") else
                     f"The rule's answer ({bot_name(ra)}) is already the live bot; tell Dylan nothing changes." if ra else
                     "Apply the pre-registered rule (How we decide §3) NOW: if it says this bot plays, declare_live it and tell "
                     "Dylan to upload it; otherwise the live bot plays. Say which in one line."))})

    def set_service(self, name: str, title: str, state: str, task: str, summary: str = ""):
        s = self.services.setdefault(name, {"name": name, "title": title, "log": []})
        s.update(state=state, task=task, updated=time.time())
        if summary:
            s["summary"] = summary
        s["log"] = (s["log"] + [{"t": time.time(), "text": task}])[-60:]
        self.emit("service", {k: v for k, v in s.items()})
        self.bus.publish(name, {"title": title + " (hub)", "state": state, "task": task,
                                "summary": s.get("summary", ""), "service": True})

    def remote_view(self):
        now = time.time()
        return [dict(name=k, **v, stale=now - v.get("seen", 0) > 120) for k, v in sorted(self.bus.directory.items())
                if v.get("person") != self.person]

    def state(self):
        return {"me": self.person, "people": PEOPLE, "agents": [a.view() for a in self.agents.values()],
                "services": [{k: v for k, v in s.items()} for s in self.services.values()],
                "remote": self.remote_view(),
                "approvals": [{k: v for k, v in a.items() if k != "future"} for a in self.approvals.values()],
                "alerts": self.alerts, "schedule": self.bus.shared.get("schedule"), "round_starts": round_starts(self.bus.shared.get("schedule")),
                "live": self.bus.shared.get("live"), "clock": self.clock.next_text(), "tiles": self.tiles()[:200],
                "props": [dict(p, thread=(p.get("thread") or [])[-60:], thread_n=len(p["thread"])) if len(p.get("thread") or []) > 60 else p
                          for p in self.props()[:200]],
                "bots": self.bots_for_menu(), "portal_active": self.bus.shared.get("portal_active"),
                "overviews": {k[7:]: v.get("items", []) for k, v in self.bus.shared.items()
                              if k.startswith("ovchat:") and isinstance(v, dict)},
                "noteled": self.note_ledger(),
                "stage": stage_of(self.bus.shared.get("schedule"), time.time()),
                "next_step": self.clock.next_step(),
                "bus": {"online": self.bus.online, "error": self.bus.error, "outbox": len(self.bus.outbox),
                        "oldest": round(self.bus.oldest_unsent_age())}}


async def _subagent_foreground(inp, tool_use_id, ctx):
    """Subagents run in the foreground (still in parallel when launched together), so their results land in the
    agent's turn instead of arriving after it ends. Their own tool calls still go through can_use_tool."""
    ti = inp.get("tool_input") or {}
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                   "updatedInput": dict(ti, run_in_background=False)}}


# ======================================================================== agent
class Agent:
    def __init__(self, hub: Hub, spec: dict):
        self.hub, self.spec = hub, spec
        self.name, self.title = spec["name"], spec["title"]
        self.dir = hub.data / "agents" / self.name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.dir / "events.jsonl"
        self.events: list[dict] = []
        if self.log_file.exists():
            for line in self.log_file.open():
                try:
                    self.events.append(json.loads(line))
                except ValueError:
                    pass
        self.events = self.events[-EVENT_CAP:]
        self.next_i = (self.events[-1]["i"] + 1) if self.events else 0
        m = load_json(self.dir / "meta.json", {})
        self.session_id = m.get("session_id")
        self.task, self.summary = m.get("task", ""), m.get("summary", "")
        self.policy, self.cost = m.get("policy", "auto"), m.get("cost", 0.0)
        self.was_running = m.get("running", False)
        self.items: list[dict] = load_json(self.dir / "inbox.json", [])   # pending inputs, saved
        for i in self.items:
            i.pop("taken", None)   # a hard kill mid-turn: process these again
        self.wake = asyncio.Event()
        if any(i.get("wake", True) for i in self.items):
            self.wake.set()
        self.state = "stopped"
        self.substate = ""        # e.g. "retrying at 21:40"
        self.pending_approvals = 0
        self.paused = False
        self.client: ClaudeSDKClient | None = None
        self.runner: asyncio.Task | None = None
        self.fails = 0
        self.turn_started = 0.0
        self.interrupted = False
        self.preempting = False
        self.eta: float | None = None
        self.human_text_in_turn = ""
        self.pending_q: list = []   # Chat only: human messages not yet answered (re-raised if they sit)
        self.status_at = 0.0   # when the agent last called set_status   # when this agent expects its current deliverable (set_status eta_minutes)
        self.last_msg_at = 0.0          # last message from Claude in the current turn (the stall watchdog reads it)
        self.stall_kicked = 0.0
        self.human_in_turn = False
        self.last_need = ""
        self.idle_since: float | None = None
        self.digest_seen: dict[str, int] = {}
        self.narr_buf: list = []
        self.narr_mark = 1
        self.narr_lock = asyncio.Lock()
        self.turn_notes: set = set()
        self.turn_note_refs: set = set()
        self.ov_last = 0.0
        self.ovchat: list = load_json(self.dir / "ovchat.json", []) if self.name.endswith("overview") else []
        self.led_seen: set = set()
        self.queue_nudged: set = set()
        self.traffic_seen = 0.0          # ledger ids this agent was shown or wrote (for invalidation notices)
        self.led_digest: dict = {}
        self.digest_full = True          # first turn after (re)start: the whole team picture
        self.context_tokens = 0
        self.context_max = 0
        self.usage: dict = {}             # latest usage-limit notice from Claude
        self.limit_reset: float | None = None
        self.model_switch: str | None = None
        self.use_api_key = False
        self.worktree_problem = ""
        self.cwd = self.workdir()

    # ---------------------------------------------------------------- persistence
    def save_meta(self):
        atomic_write(self.dir / "meta.json", json.dumps({
            "session_id": self.session_id, "task": self.task, "summary": self.summary, "policy": self.policy,
            "cost": self.cost, "running": self.runner is not None and not self.runner.done() and not self.paused}))

    def save_items(self):
        atomic_write(self.dir / "inbox.json", json.dumps(self.items))

    def view(self):
        return {"name": self.name, "title": self.title, "state": self.state, "substate": self.substate,
                "idle_since": self.idle_since,
                "task": self.task, "summary": self.summary, "policy": self.policy,
                "model": self.model(), "usage": self.usage, "api_key": self.use_api_key,
                "queued": sum(1 for i in self.items if not i.get("taken")), "cost": round(self.cost, 2),
                "overseer": self.name.endswith("overview"), "since": self.turn_started, "last_i": self.next_i - 1,
                "cwd": str(self.cwd), "context": self.context_tokens, "status_at": self.status_at}

    def model(self):
        if self.hub.model_override:
            return self.hub.model_override
        if self.model_switch:
            return self.model_switch
        if self.hub.worker_model and not self.name.endswith("overview"):
            return self.hub.worker_model   # saves the Opus allowance: Overseers keep Opus, workers use this
        return self.spec.get("model", "claude-opus-5-5")

    async def set_state(self, state: str, substate: str = ""):
        if self.pending_approvals > 0 and state not in ("stopped", "error", "limited"):
            state = "waiting"
        if state == "idle" and self.state != "idle":
            self.idle_since = time.time()
        elif state != "idle":
            self.idle_since = None
        self.state, self.substate = state, substate
        self.hub.emit("agent", self.view())
        self.hub.bus.publish(self.name, {"title": self.title, "state": self.state, "task": self.task, "idle_since": self.idle_since,
                                         "summary": self.summary})

    def ovwork_rows(self, since: float = 0, cap: int = 12000) -> str:
        rows = []
        for e in self.events[-200:]:
            if e.get("t", 0) < since:
                continue
            t = e.get("type")
            if t == "text" and not e.get("sub"):
                rows.append(f"[{hhmm(e['t'])}] Overseer: {e['text'][:1200]}")
            elif t in ("msg_in", "msg_out"):
                rows.append(f"[{hhmm(e['t'])}] {'from ' + str(e.get('from')) if t == 'msg_in' else 'to ' + str(e.get('to'))}: {str(e.get('text'))[:700]}")
        return "\n".join(rows)[-cap:]

    def record(self, ev: dict):
        if self.name.endswith("overview") and ev.get("type") in ("text", "msg_in", "msg_out") and \
                time.time() - getattr(self, "ovwork_at", 0) > 30:
            self.ovwork_at = time.time()
            asyncio.get_event_loop().call_later(1, lambda: asyncio.ensure_future(self.hub.bus.set_shared(
                "ovwork:" + self.name, {"text": self.ovwork_rows(time.time() - 1800, 8000), "updated": time.time()})))
        ev = {"i": self.next_i, "t": time.time(), **ev}
        self.next_i += 1
        self.events.append(ev)
        if len(self.events) > EVENT_CAP:
            self.events = self.events[-EVENT_CAP:]
        try:
            with self.log_file.open("a") as f:
                f.write(json.dumps(ev) + "\n")
        except OSError:
            pass
        self.hub.emit("event", {"agent": self.name, "event": ev})

    def workdir(self) -> Path:
        repo = self.hub.repo
        if not self.spec.get("worktree"):
            return repo
        wt = repo.parent / f"{repo.name}-{self.name}"

        def common(d):
            r = subprocess.run(["git", "-C", str(d), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                               capture_output=True, text=True, timeout=20)
            return r.stdout.strip() if r.returncode == 0 else None
        try:
            if not wt.exists():
                branch = self.spec.get("branch") or self.name.split("-", 1)[-1]   # builder, challenger, ...
                subprocess.run(["git", "-C", str(repo), "worktree", "add", "-B", branch, str(wt)],
                               check=True, capture_output=True, timeout=60)
            if common(wt) and common(wt) == common(repo):
                return wt
            self.worktree_problem = f"{wt} exists but is not a working copy of {repo}"
        except Exception as e:  # noqa: BLE001
            self.worktree_problem = f"could not create its own working copy ({type(e).__name__})"
        return repo

    # ---------------------------------------------------------------- inputs
    async def add_item(self, item: dict):
        item.setdefault("id", new_id())
        item.setdefault("at", time.time())
        self.items.append(item)
        self.save_items()
        if item.get("urgent") and self.state == "working" and self.client is not None and not self.preempting \
                and time.time() - (self.turn_started or time.time()) > 45:
            self.preempting = True   # data landed / decision time / a human: don't wait behind a long turn
            async def kick(c=self.client):
                try:
                    await asyncio.wait_for(c.interrupt(), 15)
                except Exception:  # noqa: BLE001
                    self.preempting = False
            asyncio.create_task(kick())   # never block the caller (the clock, the portal, a human) on a stuck agent
        if item.get("wake", True):
            self.wake.set()
        self.hub.emit("agent", self.view())

    async def receive(self, msg: dict):
        kind = msg.get("kind") or "question"
        if self.name.endswith("overview") and msg.get("from_kind") == "human":
            await self.ov_log(msg["from"], msg["text"])
        self.record({"type": "msg_in", "from": msg["from"], "text": msg["text"], "id": msg["id"],
                     "kind": kind, "reply_to": msg.get("reply_to"), "from_kind": msg.get("from_kind")})
        if self.name.endswith("overview"):   # the lead wakes for what needs a lead (each wake re-reads ~100k+ tokens)
            wake = kind in OVERSEER_WAKES or msg.get("from_kind") == "human" or msg.get("priority") == "high"
        else:
            wake = kind != "fyi" or msg.get("priority") == "high"
        if msg.get("from_kind") == "human" and not self.name.endswith("overview"):   # typed on the other laptop: tracked too
            self.pending_q.append({"who": msg["from"], "text": msg["text"][:300], "at": time.time()})
        await self.add_item({"kind": "msg", "wake": wake, "urgent": msg.get("from_kind") == "human" and kind != "fyi", **msg})
        if self.state == "stopped" and not self.paused and kind != "fyi":
            await self.start()

    async def human(self, text: str, who: str):
        if self.hub.view_only:
            if self.name.endswith("overview"):
                await self.ov_log(who, text)
                await self.ov_log("Hub", "This is a view-only preview: no agents are running, so nothing will answer.")
            return
        self.record({"type": "user", "text": text, "from": who, "queued": self.state in ("working", "waiting")})
        if self.name.endswith("overview"):
            await self.ov_log(who, text)
        else:   # a worker must answer the person too (the Chat's own tracking is in ov_log)
            self.pending_q.append({"who": who, "text": text[:300], "at": time.time()})
        await self.add_item({"kind": "human", "from": who, "text": text, "urgent": True})
        if self.state == "stopped":
            self.paused = False
            await self.start()

    def overview_context(self) -> str:
        """What the Overview reads before answering: the Overseer's recent work and the open notes."""
        hub = self.hub
        other = "d-overview" if self.name.startswith("s-") else "s-overview"
        work = (hub.bus.shared.get("ovwork:" + other) or {}).get("text", "")
        tiles = [f"- {t['label']}: {t['state']}" for t in hub.tiles()[:20]]
        waiting = [f"- #{p['id']} {p['title']}" + (f" (decide by {hhmm(p['deadline'])})" if p.get("deadline") else "")
                   + (f": {p.get('headline')}" if p.get("headline") else "") + "\n  " + (p.get("body") or "")[:900]
                   for p in hub.props() if p.get("kind") in ("bot", "question") and p.get("status") in ("needs_call", "revise")]
        return ("[the other laptop's lead, recent work]\n" + (work[-6000:] or "(nothing new)") +
                "\n\n[progress board]\n" + ("\n".join(tiles) or "(nothing yet)") +
                "\n\n[WAITING FOR THE HUMANS' ANSWER: ask in plain words in your reply, with the deadline; record their "
                "clear answer with update_proposal(id, status='approved'|'rejected', decided_by=<who>)]\n" + ("\n".join(waiting) or "(nothing)"))

    async def ov_log(self, who: str, text: str, urgent: bool = False):
        """The Overview conversation, shared so the other person can read (and write in) it too."""
        self.ovchat = (self.ovchat + [{"who": who, "at": time.time(), "text": text[:4000], "urgent": urgent}])[-40:]
        if who == "Chat":   # it answered what was asked before this turn began; later questions still wait
            t0_ = self.turn_started if self.state == "working" and getattr(self, "turn_started", 0) else time.time()
            self.pending_q = [q for q in self.pending_q if q["at"] > t0_]
        elif who in PEOPLE.values():
            self.pending_q.append({"who": who, "text": text[:300], "at": time.time()})
        atomic_write(self.dir / "ovchat.json", json.dumps(self.ovchat))
        await self.hub.bus.set_shared("ovchat:" + self.name, {"items": self.ovchat, "updated": time.time()})
        self.hub.emit("shared", {"ovchat": self.name})

    async def narr_ticker(self):
        """During a long Overseer turn, post progress to the notes every minute."""
        try:
            while True:
                await asyncio.sleep(60)
                n = len(self.narr_buf)
                if n > max(1, self.narr_mark):
                    since, self.narr_mark = self.narr_mark, n
                    await self.hub.narrate(self, self.narr_buf[:n], set(), False, since, set(self.turn_note_refs))
        except asyncio.CancelledError:
            pass

    def team_digest(self) -> str:
        """The context every agent gets at the top of each turn, highest priority first (the task itself comes last):
        P0 state (live bot, portal, rules card) and human instructions; P1 ledger results/methods that changed since its
        last turn (all for Overseers, relevant ones for workers); P3 hypotheses (Overseers); then other agents' briefs
        that changed. Each block has a size cap; detail stays in files and the ledger (cite ids)."""
        full = self.digest_full
        self.digest_full = False
        hub, ov = self.hub, self.name.endswith("overview")
        out = []
        live = hub.bus.shared.get("live") or {}
        act = hub.bus.shared.get("portal_active") or {}
        r = hub.rules()
        rules = ", ".join(f"{k}={v}" for k, v in r.items() if k not in ("set_by", "at")) if r else "NOT SET (d-platform sets it at minute 0)"
        out.append(f"[state] Live bot chosen: {live.get('filename', 'none')}; active on the portal: {act.get('filename', 'unknown')}. "
                   f"Rules card: {rules}.")
        led = hub.ledger()
        humans = [x for x in led if x.get("type") == "human"][-8:]
        if humans:
            out.append("[human instructions, newest last. One marked 'to <agent>' is that agent's to do; for everyone else it is "
                       "context. They override the plan, never the hard rules]\n" + "\n".join(
                f"- {'NEW ' if x['id'] not in self.led_digest else ''}{hhmm(x['at'])} {x.get('claim', '')}" for x in humans))
        changed = []
        for x in led:
            if x.get("type") in ("human",):
                continue
            key = x.get("status")
            if not full and self.led_digest.get(x["id"]) == key:
                continue
            rel = ov or x.get("by") == self.name or x["id"] in self.led_seen or x.get("status") in ("invalidated", "disputed") \
                or any(t in (x.get("tags") or []) for t in (self.name, self.name.split("-", 1)[-1]))
            if x.get("type") == "hypothesis" and not ov:
                rel = rel and x.get("by") == self.name
            if rel:
                changed.append(x)
        pri = {"invalidated": 0, "disputed": 0, "validated": 1, "proposed": 2}
        tpri = {"method": 0, "result": 1, "commitment": 2, "hypothesis": 3}
        changed.sort(key=lambda x: (pri.get(x.get("status"), 3), tpri.get(x.get("type"), 4), -x.get("at", 0)))
        cap, rows, used = (6000 if ov else 3200), [], 0
        for x in changed:
            line = (f"- {x['id']} [{x.get('type')}/{x.get('status')}] {x.get('claim', '')[:240]}"
                    + (f" ({x.get('effect')} ± {x.get('se')}, n={x.get('n')})" if x.get("n") else "")
                    + (f" — {x.get('invalid_reason') or x.get('verify_reason')}"[:200] if x.get("status") in ("invalidated", "disputed") else "")
                    + (f" [{x['file']}]" if x.get("file") else ""))
            if used + len(line) > cap:
                rows.append(f"- … {len(changed) - len(rows)} more: use the ledger tool")
                break
            rows.append(line)
            used += len(line)
        shown = changed[:len([r for r in rows if not r.startswith("- …")])]   # only what was actually emitted
        for x in shown + humans:
            self.led_digest[x["id"]] = x.get("status")
        self.led_seen |= {x["id"] for x in shown}
        if rows:
            out.append("[ledger: changed since your last turn, most important first]\n" + "\n".join(rows))
        if ov:   # workers talking to each other directly, on both laptops: the Overseer oversees without relaying
            tr = []
            for k, v in hub.bus.shared.items():
                if k.startswith("traffic:") and isinstance(v, dict):
                    tr += v.get("items", [])
            new_tr = [t for t in sorted(tr, key=lambda t: t["at"]) if t["at"] > self.traffic_seen]
            if new_tr:
                self.traffic_seen = new_tr[-1]["at"]
                out.append("[workers talking to each other since your last turn]\n" + "\n".join(
                    f"- {hhmm(t['at'])} {t['from']} → {t['to']} ({t['kind']}): {t['text']}" for t in new_tr[-12:]))
        if ov or self.name in ("s-data", "s-tester", "d-platform"):
            pl = persistent_leaks(led)
            if pl:
                out.append("[persistent leaks: the same leak in two or more rounds' data, same direction. Strong evidence: "
                           "ship the fix this window unless it's already in]\n" + "\n".join(
                               f"- {r['slug']}: " + ", ".join(f"{st} {e:+g}" for st, e in zip(r["stages"], r["effects"]))
                               + f" ({', '.join(r['ids'])})" for r in pl[:6]))
        if ov or self.name in ("s-data", "s-tester"):
            dis = disagreements(led)
            if dis:
                out.append("[experts disagree: resolve (re-run, or the skeptic decides) before citing these]\n" + "\n".join(dis[:6]))
        def stale(t):   # a brief not updated for a while may be out of date: say so instead of passing it on as fact
            return f"(brief last updated {(time.time() - t) / 60:.0f} min ago; may be stale) " if t and time.time() - t > 600 else ""
        rows = [(a.name, a.title, a.state, stale(a.status_at) + (a.summary or "")) for a in hub.agents.values() if a is not self]
        rows += [(n, v.get("title", n), v.get("state"), stale(v.get("status_at")) + (v.get("summary") or "")) for n, v in hub.bus.directory.items()
                 if v.get("person") != hub.person and not v.get("service")]
        briefs = []
        for n, title, st, summ in sorted(rows):
            summ = (summ or "").strip()
            if not summ:
                continue
            h = hash(summ)
            if not full and self.digest_seen.get(n) == h:
                continue
            self.digest_seen[n] = h
            keep = [ln.strip() for ln in summ.splitlines() if ln.strip()][:5]
            briefs.append(f"- {n} ({st}): " + " / ".join(keep)[:600])
        if briefs:
            out.append(("[every agent's brief]" if full else "[briefs that changed]") + "\n" + "\n".join(briefs)[:3600])
        if full:
            ps = [p for p in hub.props() if p.get("status") in OPEN]
            if ps:
                out.append("[open notes] " + "; ".join(f"#{p['id']} {p['kind']}/{p['status']}: {p['title'][:80]}" for p in ps[:12]))
        return "[team context]\n" + "\n\n".join(out) + "\n[end of team context; your new input follows]"

    def crunch(self) -> bool:
        """True in the minutes where a pause to compact would cost a deadline (T-9..T-2 of a scored round)."""
        sch = self.hub.bus.shared.get("schedule")
        if not sch:
            return False
        U, now = 60 * sch.get("scale", 1.0), time.time()
        for ts in round_starts(sch):
            if ts - 15 * U <= now < ts - 2 * U:   # from data landing (~T-13) to upload: never pause to compact
                return True
        return time.time() - getattr(self.hub, "last_landed", 0) < 8 * U

    async def maybe_compact(self):
        """Compact proactively, between turns, before the context gets long and slow, with a role-specific
        list of what must survive. Skipped in the decision crunch and when work is queued urgently."""
        try:
            u = await self.client.get_context_usage()
            tokens = int((u or {}).get("totalTokens") or 0)
            self.context_max = int((u or {}).get("maxTokens") or 0)
        except Exception:  # noqa: BLE001
            return
        self.context_tokens = tokens
        limit = COMPACT_AT_OVERSEER if self.name.endswith("overview") else COMPACT_AT_WORKER
        if self.context_max:   # stay well below the CLI's own auto-compact point
            limit = min(limit, int(0.65 * self.context_max))
        if tokens < limit or self.crunch():
            return
        await self.set_state("working", "compacting")
        self.record({"type": "note", "text": f"Compacting its context ({tokens // 1000}k tokens) to stay fast."})
        try:
            self.compacting = True
            await self.client.query("/compact " + COMPACT_KEEP + (" " + self.spec.get("keep", "")))
            async for m in self.client.receive_response():
                self.handle(m)
            self.digest_full = True
        except Exception as e:  # noqa: BLE001
            self.record({"type": "note", "text": f"Compaction failed ({e}); it carries on."})
        finally:
            self.compacting = False

    def format(self, b: dict) -> str:
        if b["kind"] == "human":
            return b["text"] if b.get("from") == PEOPLE[self.hub.person] else f"[from {b['from']}] {b['text']}"
        if b["kind"] in ("hub", "clock", "portal"):
            return f"[hub {b['kind']} · {hhmm(b['at'])}] {b['text']}"
        tag = f"[from {b['from']} · {b.get('kind') or 'message'} · id {b['id']}" + \
              (f" · reply to {b['reply_to']}" if b.get("reply_to") else "") + f" · {hhmm(b['at'])}]"
        return f"{tag}\n{b['text']}"

    # ---------------------------------------------------------------- lifecycle
    async def start(self, first_task: str | None = None):
        if self.hub.view_only or os.environ.get("AVALON_NO_AGENTS"):   # a preview / an integration test never runs agents
            return
        self.paused = False
        if first_task:
            await self.add_item({"kind": "human", "from": "overseer", "text": first_task})
            self.record({"type": "user", "text": first_task, "from": "Overseer"})
        if self.runner and not self.runner.done():
            return
        self.runner = asyncio.create_task(self.run())
        self.save_meta()

    async def stop(self):
        self.paused = True
        for ap in list(self.hub.approvals.values()):
            if ap["agent"] == self.name and not ap["future"].done():
                ap["future"].set_result("deny")
        if self.runner:
            self.runner.cancel()
        if self.client:
            try:
                await asyncio.wait_for(self.client.disconnect(), 10)
            except Exception:  # noqa: BLE001
                pass
        self.client = None
        for i in self.items:
            i.pop("taken", None)
        self.save_items()
        await self.set_state("stopped")
        self.save_meta()

    def options(self, resume: bool) -> ClaudeAgentOptions:
        role = (f"{self.spec['role']}\n\nYour hub name is `{self.name}` ({PEOPLE[self.hub.person]}'s laptop). "
                f"Your working folder is {self.cwd}; the team repo is {self.hub.repo}. This run's results and hand data are "
                f"in {self.hub.portal_data} (one folder per round); use only these, never older data elsewhere. Every board note's "
                f"full conversation is mirrored as markdown in {self.hub.data / 'board'} (<note id>.md)."
                f"\n{PROTOCOL}\n{team_directory(self.name)}\n\n{DECISION_RULES}\n{COMMON_RULES}")
        return ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code", "append": role},
            mcp_servers={"hub": self.tool_server()},
            allowed_tools=[f"mcp__hub__{t}" for t in HUB_TOOLS],
            can_use_tool=self.can_use_tool,
            cwd=str(self.cwd), add_dirs=[str(self.hub.repo), str(self.hub.portal_data), str(self.hub.data / "board")],
            env=({"ANTHROPIC_API_KEY": API_KEY_FILE.read_text().strip()} if self.use_api_key and API_KEY_FILE.exists() else {}),
            model=self.model(),
            fallback_model=None if self.hub.model_override else "claude-sonnet-5-5",
            resume=self.session_id if resume else None,
            setting_sources=[],       # no repo allow-rules can bypass the hub's permission check
            hooks={"PreToolUse": [HookMatcher(matcher="Agent|Task", hooks=[_subagent_foreground])]},
            permission_mode="default",
        )

    async def connect(self):
        resume = bool(self.session_id) and self.fails < 3
        if self.session_id and not resume:
            self.record({"type": "note", "text": "Could not resume the previous conversation; starting a fresh one."})
            self.session_id = None
        self.client = ClaudeSDKClient(options=self.options(resume))
        await asyncio.wait_for(self.client.connect(), 120)

    async def run(self):
        await self.set_state("starting")
        self.hub.portal_data.mkdir(parents=True, exist_ok=True)
        while True:
            batch = []
            try:
                if self.client is None:
                    await self.connect()
                    await self.set_state("idle")
                await self.wake.wait()
                self.wake.clear()
                batch = [i for i in self.items if not i.get("taken")]
                if not batch:
                    continue
                for i in batch:
                    i["taken"] = True
                self.save_items()
                self.human_in_turn = any(b["kind"] == "human" or b.get("from_kind") == "human" for b in batch)
                self.human_text_in_turn = "\n".join(str(b.get("text", "")) for b in batch
                                                     if b["kind"] == "human" or b.get("from_kind") == "human")
                prompt = "\n\n".join(self.format(b) for b in batch)
                if any(b.get("retry") for b in batch):
                    prompt = ("(Retrying this input after an error: some actions from the previous attempt may already have "
                              "happened. Check (ledger, notes, messages, files) before repeating any of them.)\n\n" + prompt)
                digest = self.team_digest()
                if digest:
                    prompt = digest + "\n\n" + prompt
                if self.name.endswith("overview"):   # the lead: where we are, the other lead's work, what waits on humans
                    prompt = situation(self.hub) + "\n\n" + self.overview_context() + "\n\n" + prompt
                self.turn_started = self.last_msg_at = time.time()
                self.stall_kicked = 0.0
                self.turn_text_n = 0
                await self.set_state("working")
                self.record({"type": "turn", "n": len(batch)})
                await self.client.query(prompt)
                ok, limited = True, False
                async for m in self.client.receive_response():
                    r = self.handle(m)
                    if r == "error":
                        ok = False
                    elif r == "limited":
                        ok, limited = False, True
                if self.preempting:             # stopped for urgent input; the partial turn stays in the session
                    ok, limited, self.preempting = True, False, False
                    self.interrupted = False
                    self.record({"type": "note", "text": "Interrupted for urgent input; it resumes after handling it."})
                    self.items.insert(0, {"id": new_id(), "at": time.time(), "kind": "hub", "wake": True,
                                          "text": "Your previous turn was interrupted because urgent input arrived (below). "
                                                  "Handle it first, then resume what you were doing."})
                if self.stall_kicked and not self.interrupted:   # the stall watchdog stopped it: resume, don't drop the task
                    self.items.insert(0, {"id": new_id(), "at": time.time(), "kind": "hub", "wake": True,
                                          "text": "Your previous turn produced no output for 12 minutes and was stopped by the "
                                                  "hub. Check what already finished (files, ledger, messages), then resume the "
                                                  "task. If a command hung, re-run it with a timeout, in the background, or on Modal."})
                    self.stall_kicked = 0.0
                if self.interrupted:            # paused by a human: the turn is over, don't replay it
                    ok, limited, self.interrupted = True, False, False
                    self.record({"type": "note", "text": "Paused."})
                if limited:
                    raise LimitHit("usage limit reached")
                if not ok:
                    raise RuntimeError("the turn ended with an error")
                done = {i["id"] for i in batch}
                if self.human_in_turn and getattr(self, "turn_text_n", 0) and not self.name.endswith("overview"):
                    self.pending_q = [q for q in self.pending_q if q["at"] > self.turn_started]   # it replied to them
                self.items = [i for i in self.items if i["id"] not in done]
                self.save_items()
                self.fails = 0
                await self.maybe_compact()
                await self.set_state("idle")
                if not self.name.endswith("overview") and not any(not i.get("taken") for i in self.items):
                    fresh = [x for x in self.hub.queue_for(self.name) if x["id"] not in self.queue_nudged]
                    if fresh:   # free now and there's work meant for you: pull it
                        self.queue_nudged |= {x["id"] for x in fresh}
                        await self.add_item({"kind": "hub", "wake": True, "text": f"You're free and {len(fresh)} queued "
                                             f"task(s) are waiting for you (top: {fresh[0]['task'][:120]}): call queue_claim."})
                if any(i.get("wake", True) for i in self.items if not i.get("taken")):
                    self.wake.set()
            except asyncio.CancelledError:
                for i in batch:
                    i.pop("taken", None)
                self.save_items()
                raise
            except Exception as e:  # noqa: BLE001
                for i in batch:
                    i.pop("taken", None)
                    i["retry"] = i.get("retry", 0) + 1
                self.save_items()
                text = f"{type(e).__name__}: {e}"
                is_limit = isinstance(e, LimitHit) or self.usage.get("status") == "rejected"
                transient = not is_limit and bool(LIMIT_RX.search(text)) and \
                    not isinstance(e, (TypeError, ValueError, KeyError, AttributeError))
                self.fails += 1
                wait = 90 if transient else min(5 * 2 ** min(self.fails, 5), 120)
                if is_limit:
                    kind = self.usage.get("type") or ""
                    if "opus" in kind and "sonnet" not in self.model() and not self.hub.model_override:
                        self.model_switch = "claude-sonnet-5-5"   # Opus allowance used up: carry on with Sonnet
                        self.usage = {}
                        wait = 5
                        msg = f"{self.title} used up its Opus allowance; it switched to Sonnet and carries on."
                    elif API_KEY_FILE.exists() and not self.use_api_key:
                        self.use_api_key = True          # subscription used up: continue on the team's API key
                        self.usage = {}
                        wait = 5
                        msg = (f"{self.title} used up the Claude subscription allowance; it switched to the team's "
                               "Anthropic API key (billed per use) and carries on.")
                    else:
                        wait = max(60, (self.limit_reset or time.time() + 300) - time.time() + 30)
                        msg = (f"{self.title} hit a Claude usage limit; it resumes at {hhmm(time.time() + wait)}. "
                               "Its messages are kept." + ("" if API_KEY_FILE.exists() else
                               f" To keep going now, save an Anthropic API key in {API_KEY_FILE}."))
                    await self.hub.add_alert(self.name, msg, True)
                self.record({"type": "error", "text": text, "trace": traceback.format_exc()[-1200:]})
                await self.set_state("limited" if is_limit else "error", f"retrying at {hhmm(time.time() + wait)}")
                try:
                    if self.client:
                        await asyncio.wait_for(self.client.disconnect(), 10)
                except Exception:  # noqa: BLE001
                    pass
                self.client = None
                await asyncio.sleep(wait)
                if batch:
                    self.wake.set()

    def handle(self, m):
        self.last_msg_at = time.time()
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock) and b.text.strip():
                    if not m.parent_tool_use_id:
                        self.turn_text_n = getattr(self, "turn_text_n", 0) + 1
                    self.record({"type": "text", "text": b.text, "sub": bool(m.parent_tool_use_id)})
                    if self.name.endswith("overview") and not m.parent_tool_use_id and not getattr(self, "compacting", False):
                        asyncio.create_task(self.ov_log("Chat", b.text))
                elif isinstance(b, ToolUseBlock):
                    self.record({"type": "tool", "name": b.name, "input": short(b.input), "id": b.id,
                                 "sub": bool(m.parent_tool_use_id)})
            if getattr(m, "error", None):
                return "limited" if HARD_LIMIT_RX.search(str(m.error)) or self.usage.get("status") == "rejected" else "error"
        elif isinstance(m, UserMessage) and isinstance(m.content, list):
            for b in m.content:
                if isinstance(b, ToolResultBlock):
                    self.record({"type": "tool_result", "id": b.tool_use_id, "error": bool(b.is_error),
                                 "text": short(b.content, 1200)})
        elif isinstance(m, ResultMessage):
            if m.session_id:
                self.session_id = m.session_id
            self.cost += m.total_cost_usd or 0
            self.save_meta()
            self.record({"type": "result", "ok": not m.is_error, "turns": m.num_turns, "ms": m.duration_ms})
            if m.is_error:
                text = f"{m.subtype} {m.result or ''} {m.errors or ''} {m.api_error_status or ''}"
                return "limited" if HARD_LIMIT_RX.search(text) or self.usage.get("status") == "rejected" else "error"
        elif isinstance(m, SystemMessage):
            if m.subtype == "init":
                sid = (m.data or {}).get("session_id")
                if sid:
                    self.session_id = sid
                    self.save_meta()
            elif m.subtype == "compact_boundary":
                self.digest_full = True
                self.items.append({"id": new_id(), "at": time.time(), "kind": "hub", "wake": False,
                                   "text": "Your context was just compacted. Re-read your PLAN file and your role "
                                           "before continuing; facts about rounds must come from the portal watcher. "
                                           "The team context above your next message lists every agent's brief and "
                                           "the open notes."})
                self.save_items()
        elif type(m).__name__ == "RateLimitEvent":
            info = m.rate_limit_info
            prev = self.usage.get("status")
            self.usage = {"status": info.status, "used": info.utilization, "type": info.rate_limit_type,
                          "resets_at": info.resets_at}
            if info.status == "rejected":
                self.limit_reset = float(info.resets_at) if info.resets_at else None
            self.hub.emit("agent", self.view())
            if info.status == "rejected":
                return "limited"
            if info.status == "allowed_warning" and prev != "allowed_warning":
                pct = f"{info.utilization * 100:.0f}%" if info.utilization is not None else "most"
                asyncio.create_task(self.hub.add_alert("hub-usage", f"The Claude {(info.rate_limit_type or '').replace('_', ' ')} "
                                    f"allowance is at {pct} (shared by every agent on this laptop)"
                                    + (f"; resets {hhmm(info.resets_at)}" if info.resets_at else "") + ". Work continues; "
                                    "at 100% agents switch to Sonnet, then to the API key if one is saved.", False))
        return None

    # ---------------------------------------------------------------- permissions
    def inside_allowed(self, p: str) -> bool:
        try:
            rp = Path(p).expanduser().resolve()
        except Exception:  # noqa: BLE001
            return False
        roots = [self.hub.repo, self.cwd, self.hub.portal_data, Path("/tmp"), Path("/private/tmp")]
        return any(rp == r or r in rp.parents for r in (x.resolve() for x in roots))

    async def can_use_tool(self, name, inp, ctx):
        if name.startswith("mcp__hub__"):
            return PermissionResultAllow()
        text = json.dumps(inp)
        if isinstance(inp.get("command"), str):   # deleting scratch space under /tmp is routine, not risky
            text = json.dumps(dict(inp, command=tmp_scrub(inp["command"])))
        risky = bool(DANGER.search(text))
        if name in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
            fp = inp.get("file_path") or inp.get("notebook_path") or ""
            if fp and not self.inside_allowed(fp):
                risky = True
        if self.policy == "auto" and not risky:
            return PermissionResultAllow()
        ap = {"id": new_id(), "agent": self.name, "tool": name, "input": short(inp, 800), "risky": risky,
              "at": time.time(), "future": asyncio.get_running_loop().create_future()}
        self.hub.approvals[ap["id"]] = ap
        self.hub.emit("approval", {k: v for k, v in ap.items() if k != "future"})
        self.pending_approvals += 1
        await self.set_state("waiting")
        try:
            decision = await asyncio.wait_for(ap["future"], APPROVAL_TIMEOUT)
        except asyncio.TimeoutError:
            decision = "timeout"
            await self.hub.add_alert(self.name, f"No one answered {self.title}'s request to run {name}; it was refused "
                                     "after 3 minutes and the agent will find another way.", False)
        finally:
            self.pending_approvals -= 1
            self.hub.approvals.pop(ap["id"], None)
            self.hub.emit("approval_done", {"id": ap["id"]})
            await self.set_state("working")
        self.record({"type": "permission", "tool": name, "decision": decision})
        if decision in ("allow", "always"):
            if decision == "always" and not risky:
                self.policy = "auto"
                self.save_meta()
            return PermissionResultAllow()
        return PermissionResultDeny(message="Not approved (declined or no answer in 3 minutes). Do it another way "
                                            "or explain to your Overseer why it is needed.", interrupt=False)

    # ---------------------------------------------------------------- hub tools
    def tool_server(self):
        me, hub = self, self.hub

        def ok(text):
            return {"content": [{"type": "text", "text": text}]}

        @tool("send_message", "Message ANY agent on either laptop (names in list_agents). kind: task | question | "
              "answer | fyi (fyi does not wake the receiver). Non-blocking; answers arrive as new turns. note: the board "
              "note this is about (its progress is posted there).",
              schema(["to", "text"], {"to": "string", "text": "string", "kind": "string", "reply_to": "string", "note": "string"}))
        async def send_message(a):
            if a.get("note"):
                me.turn_note_refs.add(a["note"].lstrip("#"))
            kind = (a.get("kind") or "question").lower()
            if kind not in ("task", "question", "answer", "fyi"):
                kind = "question"
            msg = {"id": new_id(), "from": me.name, "from_kind": "agent", "to": a["to"].strip(), "text": a["text"],
                   "kind": kind, "reply_to": a.get("reply_to") or None}
            if not me.name.endswith("overview") and not msg["to"].endswith("overview"):
                hub.traffic = (hub.traffic + [{"at": time.time(), "from": me.name, "to": msg["to"], "kind": kind,
                                               "text": a["text"][:160]}])[-30:]
                asyncio.create_task(hub.bus.set_shared("traffic:" + hub.person, {"items": hub.traffic, "updated": time.time()}))
            if kind == "answer" and msg["reply_to"]:
                orig = next((e for e in reversed(me.events) if e.get("type") == "msg_in" and e.get("id") == msg["reply_to"]), None)
                if orig and orig.get("kind") in ("answer", "fyi"):
                    return ok("Not sent: that message was an answer/fyi and needs no reply.")
            try:
                status = await hub.bus.send(msg)
            except OverflowError as e:
                await hub.add_alert(me.name, f"{me.title} and {msg['to']} were messaging each other in a loop; further "
                                    "messages between them are held for 10 minutes.", False)
                return ok(str(e))
            except ValueError as e:
                return ok(f"Not sent: {e}")
            me.record({"type": "msg_out", "to": msg["to"], "text": msg["text"], "id": msg["id"], "kind": kind,
                       "reply_to": msg["reply_to"]})
            if re.match(r"\W*plan challenge", a["text"], re.I):   # the humans see every plan challenge, once
                key = re.sub(r"\W+", " ", a["text"].lower())[:120]
                if key not in hub.plan_challenges:
                    hub.plan_challenges.add(key)
                    head = re.sub(r"(?i)^\W*plan challenge\W*", "", a["text"]).strip()
                    await hub.tile("challenge-" + new_id()[1:7], "Plan challenge", "raised", owner=me.name)
                    await hub.alert_all(me.name, f"Plan challenge from {me.title}: {head[:400]} (your Chat will explain; "
                                        "by default the Challenger builds the alternative and the next practice judges it)",
                                        False, chat=True)
            return ok(f"{status} (id {msg['id']})")

        @tool("list_agents", "Every agent and hub service on both laptops, with state and one-line status.", {})
        async def list_agents(a):
            rows = [f"{v['name']} [{v['state']}] {v['title']}: {v['task'] or '-'}" for v in (x.view() for x in hub.agents.values())]
            rows += [f"{s['name']} [{s['state']}] {s['title']} (hub service): {s['task']}" for s in hub.services.values()]
            for v in hub.remote_view():
                rows.append(f"{v['name']} [{'OFFLINE' if v['stale'] else v.get('state')}] {v.get('title')} "
                            f"({PEOPLE.get(v.get('person'), '?')}'s laptop): {v.get('task') or '-'}")
            if not hub.bus.online:
                rows.append(f"(Link to the other laptop: {hub.bus.error})")
            return ok("\n".join(rows))

        @tool("read_agent", "An agent's or service's latest work: recent transcript (this laptop) or posted summary.",
              schema(["name"], {"name": "string", "last": "integer"}))
        async def read_agent(a):
            n = a["name"].strip()
            last = max(1, min(int(a.get("last") or 30), 200))
            if n in hub.agents:
                ag = hub.agents[n]
                lines = [f"{ag.title} [{ag.state}] task: {ag.task}", f"summary:\n{ag.summary}", "recent:"]
                for e in ag.events[-last:]:
                    if e["type"] in ("text", "user", "msg_in", "msg_out"):
                        lines.append(f"- {e['type']}: {(e.get('text') or '')[:400]}")
                    elif e["type"] == "tool":
                        lines.append(f"- tool {e['name']}: {str(e.get('input'))[:160]}")
                return ok("\n".join(lines))
            if n in hub.services:
                s = hub.services[n]
                return ok(f"{s['title']} [{s['state']}] {s['task']}\n{s.get('summary', '')}\nlog:\n" +
                          "\n".join(f"- {hhmm(x['t'])} {x['text']}" for x in s["log"][-last:]))
            v = hub.bus.directory.get(n)
            if v:
                return ok(f"{v.get('title')} [{v.get('state')}] task: {v.get('task')}\nsummary:\n{v.get('summary')}")
            return ok(f"No agent named {n}.")

        @tool("set_status", "Update your state (working/waiting/blocked/done/idle), one-line task and markdown summary. "
              "Update it whenever a step finishes or your task changes: the humans and the Chat read it, and a stale "
              "status ('blocked on the kit' after the kit arrived) misleads them. "
              "eta_minutes: your honest estimate of event-minutes until your current deliverable is finished (the "
              "deadline guard uses it to re-plan early; it never makes anyone hurry, so don't shade it).",
              schema([], {"state": "string", "task": "string", "summary": "string", "eta_minutes": "number"}))
        async def set_status(a):
            if a.get("task") and a["task"] != me.task:
                me.eta = None   # a new task: the old estimate no longer applies
            me.task = (a.get("task") or me.task)[:200]
            me.status_at = time.time()
            if a.get("eta_minutes") is not None:
                try:
                    sc = (hub.bus.shared.get("schedule") or {}).get("scale", 1.0)
                    me.eta = time.time() + float(a["eta_minutes"]) * 60 * sc
                except (TypeError, ValueError):
                    pass
            if a.get("summary"):
                me.summary = a["summary"][:6000]
                need = re.search(r"\*\*Needs from a human:?\*\*:?\s*(.+)", me.summary)
                need = need.group(1).strip() if need else ""
                if need and not re.match(r"(nothing|none|n/?a|no\b)", need, re.I) and need != me.last_need:
                    me.last_need = need
                    if me.name.endswith("overview"):
                        await hub.add_alert(me.name, need[:400], False)
                    else:
                        await hub.overseer().add_item({"kind": "hub", "wake": False,
                                                       "text": f"{me.title} needs something from a human: {need[:400]}"})
            me.save_meta()
            st = a.get("state") if a.get("state") in STATES else None
            await me.set_state(st or me.state)
            return ok("Status updated.")

        @tool("notify_human", "Overseers only: ask your human to decide or act. Shown prominently on their screen. Say "
              "exactly what to do and where (e.g. 'open the Format page on the portal and paste its text into your Chat'). "
              "Don't repeat an ask within 10 minutes unless it became urgent: your new note replaces the old one.",
              schema(["text"], {"text": "string", "urgent": "boolean"}))
        async def notify_human(a):
            if not me.name.endswith("overview"):
                await hub.overseer().add_item({"kind": "hub", "wake": True,
                                               "text": f"{me.title} wanted to tell the human: {a['text']}"})
                return ok("Only your Overseer talks to humans; it has been passed to your Overseer.")
            await hub.add_alert(me.name, a["text"], bool(a.get("urgent")))
            await hub.chat_ping(f"{me.title} asks: {a['text']}")
            me.record({"type": "notify", "text": a["text"], "urgent": bool(a.get("urgent"))})
            return ok("Your human has been notified.")

        @tool("start_agent", "Overseer only: start one of this laptop's agents with a first task.",
              schema(["name"], {"name": "string", "task": "string"}))
        async def start_agent(a):
            if not me.name.endswith("overview"):
                return ok("Only the Overseer can start agents.")
            ag = hub.agents.get(a["name"].strip())
            if not ag or ag is me:
                return ok(f"No such agent here. This laptop's agents: {', '.join(hub.agents)}")
            await ag.start(a.get("task") or None)
            return ok(f"{ag.name} started.")

        @tool("stop_agent", "Overseer only: stop one of this laptop's agents (it stays stopped until restarted).",
              schema(["name"], {"name": "string"}))
        async def stop_agent(a):
            if not me.name.endswith("overview"):
                return ok("Only the Overseer can stop agents.")
            ag = hub.agents.get(a["name"].strip())
            if not ag or ag is me:
                return ok("Can't stop that agent.")
            await ag.stop()
            return ok(f"{ag.name} stopped.")

        @tool("declare_live", "d-overview only: record the bot that should be active on the portal: the EXACT file name "
              "Dylan uploads (e.g. 'v4.zip'), and its sha256 if known. The portal watcher checks the portal against it "
              "before every scored round, so tell Dylan to upload a file with this exact name.",
              schema(["filename"], {"filename": "string", "sha256": "string", "note": "string"}))
        async def declare_live(a):
            if me.name != "d-overview":
                return ok("Only d-overview declares the live bot.")
            v = {"filename": a["filename"], "sha256": a.get("sha256") or "", "note": a.get("note") or "", "at": time.time()}
            await hub.bus.set_shared("live", v)
            hub.emit("shared", {"live": v})
            return ok(f"Live bot declared: {v['filename']}.")

        @tool("set_schedule", "The Chats: set or correct the event clock when a HUMAN tells you a time or the format in "
              "this turn ('round 1 is in 5 minutes', 'practice 3 moved to 22:58', 'the variant was announced at 14:02', 'the "
              "build is 90 minutes', 'rounds are every 30 minutes', 'there are 5 scored rounds'). event: minute0 | practiceN | "
              "scoredN (e.g. scored1, practice3) | format. Give at='HH:MM' (today) or in_minutes (real minutes from now). "
              "minute0 or a build-hour practice moves the whole schedule; a later round (scoredN, or a practice after scored "
              "round 1) moves only that round and the ones after it. event='format' with build_minutes / gap_minutes / "
              "scored_rounds changes the shape. Both laptops update. Never change it on your own initiative.",
              schema(["event"], {"event": "string", "at": "string", "in_minutes": "number", "scored_rounds": "integer",
                                 "build_minutes": "number", "gap_minutes": "number"}))
        async def set_schedule(a):
            if not me.name.endswith("overview"):
                return ok("Only the Chat and the Overseers set the clock.")
            if hub.bus.shared.get("schedule") and not me.human_in_turn:
                return ok("The clock is set. Only change it when a human tells you a time in this turn; otherwise tell "
                          "your human with notify_human.")
            if hub.bus.shared.get("schedule") and not re.search(r"\d", me.human_text_in_turn or ""):
                s_ = hub.bus.shared["schedule"]
                return ok(f"The clock is already running (minute 0 = {time.strftime('%H:%M:%S', time.localtime(s_['start']))}). "
                          "A message without a time ('it's starting now') never moves it: ask the human for the exact time "
                          "of an event (e.g. 'practice 1 started at 14:25') and set that.")
            if me.name.endswith("overview") and not hub.bus.shared.get("schedule"):
                ov = hub.agents.get(me.name.replace("overview", "overseer"))
                if ov:
                    await ov.add_item({"kind": "hub", "wake": True, "urgent": True, "text": (
                        f"{PEOPLE[hub.person]} told the Chat the competition timing ({a.get('event')}"
                        + (f" at {a['at']}" if a.get("at") else f" in {a.get('in_minutes')} min" if a.get("in_minutes") is not None else "")
                        + "). The clock is now set on both laptops. Start the plan: read the game plan (START_HERE.md, "
                        "FIRST_PROMPT.md, TWIST_NOTES.md) and follow the clock's dispatches.")})
                    if ov.state == "stopped":
                        await ov.start()
            ev = (a.get("event") or "minute0").lower().replace(" ", "").replace("round", "")
            sch = hub.bus.shared.get("schedule") or {}
            scale = sch.get("scale", hub.default_scale)
            U = 60 * scale
            B = float(a.get("build_minutes") or sch.get("build") or 60)
            G = float(a.get("gap_minutes") or sch.get("gap") or 20)
            m = re.fullmatch(r"(minute0|start|practice(\d+)|scored(\d+)|format)", ev)
            if not m:
                return ok("event must be minute0, practiceN, scoredN or format (with build_minutes / gap_minutes).")
            if m.group(1) == "format":   # "the build is 90 minutes", "rounds are every 30 minutes": no time needed
                if not sch:
                    return ok("Set minute 0 first (event='minute0').")
                txt = await hub.clock.set_start("", int(a.get("scored_rounds") or sch.get("scored", 6)), scale, t0=sch["start"],
                                                build=float(a["build_minutes"]) if a.get("build_minutes") else None,
                                                gap=float(a["gap_minutes"]) if a.get("gap_minutes") else None)
                me.record({"type": "note", "text": f"Clock format updated: build {B:.0f} min, rounds every {G:.0f} min ({txt})"})
                return ok(f"Clock updated on both laptops: build {B:.0f} min, rounds every {G:.0f} min; {txt}")
            if a.get("in_minutes") is not None:
                when = time.time() + float(a["in_minutes"]) * 60
            else:
                mm = re.fullmatch(r"\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", a.get("at") or "")
                if not mm or int(mm.group(1)) > 23 or int(mm.group(2)) > 59:
                    return ok("Give at='HH:MM' (24-hour) or in_minutes.")
                lt = time.localtime()
                when = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(mm.group(1)), int(mm.group(2)),
                                    int(mm.group(3) or 0), 0, 0, -1))
            n_sc = int(a.get("scored_rounds") or sch.get("scored", 6))
            if sch and (m.group(3) or (m.group(2) and int(m.group(2)) > 4)):
                # a later round's real time: pin that scored round (later ones follow); minute 0 and the past stay put
                k = int(m.group(3)) if m.group(3) else int(m.group(2)) - 4 + 1
                if m.group(2):
                    when += 10 * U   # the practice round plays 10 minutes before the next scored round
                if a.get("scored_rounds") and n_sc != sch.get("scored", 6):
                    await hub.clock.set_start("", n_sc, scale, t0=sch["start"])
                txt = await hub.clock.pin_round(k, when, f"{PEOPLE[hub.person]} said so")
                me.record({"type": "note", "text": f"Clock updated: {ev} at {hhmm(when)} ({txt})"})
                return ok(f"Clock updated on both laptops: {txt}")
            if m.group(2):
                n = int(m.group(2))
                off = (B - 40, B - 30, B - 20, B - 10)[n - 1] if n <= 4 else B + G * (n - 4) - 10
            elif m.group(3):
                off = B + G * (int(m.group(3)) - 1)
            else:
                off = 0
            t0 = when - off * U
            txt = await hub.clock.set_start("", n_sc, scale, t0=t0, build=B if a.get("build_minutes") else None,
                                            gap=G if a.get("gap_minutes") else None)
            me.record({"type": "note", "text": f"Clock updated: {ev} at {hhmm(when)} ({txt})"})
            return ok(f"Clock updated on both laptops: {ev} at {hhmm(when)}; {txt}")

        @tool("codex_task", "Run an independent, well-specified job on OpenAI Codex in the background (separate credits: "
              "adds capacity without using Claude limits). Good for: a second-opinion bug hunt on a file, an alternative "
              "implementation of one function, a test script, a data crunch. Give exact files and a pass/fail check. "
              "The result arrives as a new turn.", schema(["task"], {"task": "string", "folder": "string", "check": "string"}))
        async def codex_task(a):
            if not hub.codex:
                return ok("Codex is not enabled on this hub.")
            return ok(await hub.codex.submit(me, a["task"], a.get("folder"), a.get("check")))

        @tool("propose", "Ask the humans a decision; it is pinned at the top of both Chats until answered. kind='bot': "
              "'Which bot plays?' (give bot= the exact released file, e.g. 'releases/v7.zip', and rule_answer= the released "
              "file the pre-registered rule picks: it plays automatically if nobody answers by the deadline; leave it out "
              "and the current live bot is the default). kind='question': something only a human can answer (e.g. a PLAN "
              "CHALLENGE that means a new base style). Findings and analysis don't go here: record them in the ledger. "
              "headline: ONE plain sentence a tired human understands in 5 seconds. body: markdown with the evidence "
              "(numbers, ± error, files) and what each answer means. deadline_minutes: when the default happens.",
              schema(["kind", "title", "headline", "body"], {"kind": "string", "title": "string", "headline": "string",
                                                             "body": "string", "bot": "string", "parent": "string",
                                                             "deadline_minutes": "number", "rule_answer": "string"}))
        async def propose(a):
            kind = {"decision": "bot", "change": "analysis", "finding": "analysis", "research": "analysis"}.get(a["kind"], a["kind"])
            if kind == "analysis":   # fold into the latest analysis note instead of a new note
                an = max((p for p in hub.props() if p.get("kind") == "analysis" and p.get("status") != "removed"),
                         key=lambda p: p.get("created", 0), default=None)
                if an:
                    await hub.note_append(an["id"], me.title, f"**{a['title']}** — {a.get('headline') or ''}\n\n{a['body']}"[:8000],
                                          action=a["kind"])
                    return ok(f"Added to note #{an['id']} ({an['title']}): findings and suggestions live in the round's "
                              "analysis note. Set its summary with update_proposal(id, summary=...) when you have the picture.")
                kind = "question"
            if kind not in ("bot", "question", "build"):
                kind = "question"
            if kind == "bot":
                if not a.get("bot") or not re.fullmatch(r"v\d+", bot_name(a["bot"])):
                    return ok("A 'Which bot?' note needs bot= a released file named vN (e.g. 'releases/v6.zip'). Have "
                              "d-platform release the candidate first (next_bot_name), then ask.")
                if not hub.find_bot_file(a["bot"]) and (hub.bus.shared.get("bot:" + bot_name(a["bot"])) or {}).get("status") != "ready":
                    return ok(f"{a['bot']} isn't released yet (no zip, not marked ready). Release it first, then ask.")
            sch = hub.bus.shared.get("schedule")
            p = {"id": "P" + new_id()[1:7].upper(), "kind": kind, "title": a["title"][:160], "body": a["body"][:8000],
                 "headline": (a.get("headline") or "")[:300], "bot": a.get("bot") or None,
                 "author": me.name, "author_person": hub.person, "decider": "both" if kind == "bot" else hub.person,
                 "owner": me.name if me.name.endswith("overview") else hub.owner_overseer(hub.person),
                 "parent": a.get("parent") or None, "stage": stage_of(sch, time.time()),
                 "status": "needs_call" if kind in ("bot", "question") else "running",
                 "created": time.time(), "thread": []}
            if a.get("deadline_minutes"):
                p["deadline"] = time.time() + float(a["deadline_minutes"]) * 60 * (sch or {}).get("scale", 1.0)
            if kind == "bot":
                await hub.register_bot(a["bot"], "ready", by=me.name)
                live_ = hub.bus.shared.get("live") or {}
                ra = (a.get("rule_answer") or "").strip()
                if ra and not re.fullmatch(r"v\d+", bot_name(ra)):
                    return ok("rule_answer must be a released file named vN (e.g. 'releases/v5.zip').")
                p["rule_answer"] = ra or live_.get("file") or (("releases/" + live_["filename"]) if live_.get("filename") else None)
                if p["rule_answer"]:
                    p["body"] = (f"**If nobody answers by the deadline: {bot_name(p['rule_answer'])} plays (the rule's answer).**\n\n"
                                 + p["body"])[:8000]
            await hub.save_prop(p)
            me.record({"type": "note", "text": f"Posted note #{p['id']} ({kind}): {p['title']}"})
            await hub.tile("decide-" + p["id"], ("Bot choice: " + bot_name(p["bot"])) if p.get("bot") else ("Question: " + p["title"][:60]),
                           "waiting for your answer", owner=hub.owner_overseer(hub.person))
            for lead in [x for x in hub.agents.values() if x.name.endswith("overview") and x is not me]:
                await lead.add_item({"kind": "hub", "wake": True, "text": f"[decision waiting] #{p['id']} {p['title']}: ask your "
                                     "human in plain words (what's decided, the evidence, what each answer means, the deadline)."})
            return ok(f"Note #{p['id']} posted ({p['status']}). Wait for a human answer; you'll get a message.")

        @tool("record", "Write to the team ledger (what every agent sees, by priority). type: result (a measured claim: needs "
              "effect, se, n, method; players/stack/big_blind/hands_per_match if relevant: a result that contradicts the "
              "rules card is rejected) | method (how something is measured: table size, opponents, paired deals) | "
              "hypothesis (weak evidence; never present it as a finding) | commitment (who does what by when). "
              "depends_on: ledger ids it builds on (the card, a method). note: the board note it belongs to. file: where "
              "the detail is. question: a short key shared by every answer to the same question (e.g. 'one-change Round 2'); "
              "lens: the angle (leaks, opponent:<team>, twist, sizing, engine, styles, aggregate); model: who produced it "
              "(opus, sonnet, codex); for a leak, tags=['leak:<slug>'] with a stable slug reused round to round (look up "
              "existing slugs with ledger(tag=...)) and data_stage= the round whose data it comes from (e.g. 'Practice 2'); "
              "(opus, sonnet, codex); proposer_of: for an aggregate, the ids it combines. Returns the id; cite ids.",
              schema(["type", "claim"], {"type": "string", "claim": "string", "effect": "number", "se": "number",
                                         "n": "integer", "unit": "string", "method": "string", "method_id": "string",
                                         "players": "integer", "stack": "number", "big_blind": "number",
                                         "hands_per_match": "integer", "bot": "string", "data": "string",
                                         "tags": "array", "depends_on": "array", "file": "string", "note": "string",
                                         "question": "string", "lens": "string", "model": "string", "proposer_of": "array",
                                         "scope": "string", "data_stage": "string"}))
        async def record(a):
            if a.get("note"):
                a["note"] = a["note"].lstrip("#")
            iid, err = await hub.record_item(dict(a), me.name)
            if a.get("note"):
                me.turn_note_refs.add(a["note"])
            if iid:
                me.led_seen.add(iid)
            return ok(err or f"Recorded {iid} (proposed; s-tester validates what decisions rest on).")

        @tool("verify", "s-tester (or an Overseer in a pinch): mark a ledger item validated or disputed after RE-RUNNING it.",
              schema(["id", "verdict", "reason"], {"id": "string", "verdict": "string", "reason": "string"}))
        async def verify(a):
            v = a["verdict"] if a["verdict"] in ("validated", "disputed") else "disputed"
            return ok(await hub.verify_item(a["id"], v, a["reason"], me.name))

        @tool("invalidate", "Mark a ledger item wrong (e.g. a method run at the wrong table size). Everything built on it is "
              "invalidated too, and every agent and note that used it is told.",
              schema(["id", "reason"], {"id": "string", "reason": "string"}))
        async def invalidate(a):
            bad = await hub.invalidate(a["id"], a["reason"], me.name)
            return ok(f"Invalidated: {', '.join(bad)}" if bad else f"No ledger item {a['id']}.")

        @tool("set_rules", "d-platform at minute 0 (s-tester checks it): the rules card every harness and result must match: "
              "players (per table), stack, big_blind, hands_per_match, time_per_decision, variant, notes, weights (the scored "
              "rounds' weights in order, e.g. [1,2,3,5,8,13]), payouts. Also written to "
              "rules.json in the repo.",
              schema(["players"], {"players": "integer", "stack": "number", "big_blind": "number", "hands_per_match": "integer",
                                   "time_per_decision": "string", "variant": "string", "notes": "string",
                                   "weights": "array", "payouts": "string"}))
        async def set_rules(a):
            r = dict(hub.rules(), **{k: v for k, v in a.items() if v not in (None, "")}, set_by=me.name, at=time.time())
            await hub.bus.set_shared("rules", r)
            try:
                atomic_write(hub.repo / "rules.json", json.dumps({k: v for k, v in r.items() if k not in ("set_by", "at")}, indent=1))
            except Exception:  # noqa: BLE001
                pass
            return ok("Rules card set: " + ", ".join(f"{k}={v}" for k, v in r.items() if k not in ("set_by", "at")))

        @tool("ledger", "Read ledger items: by id, or filter by type/status/tag/note (newest first, at most 30).",
              schema([], {"id": "string", "type": "string", "status": "string", "tag": "string", "note": "string"}))
        async def ledger(a):
            xs = hub.ledger()
            if a.get("id"):
                xs = [x for x in xs if x["id"] == a["id"]]
            for k in ("type", "status", "note"):
                if a.get(k):
                    xs = [x for x in xs if x.get(k) == a[k]]
            if a.get("tag"):
                xs = [x for x in xs if a["tag"] in (x.get("tags") or [])]
            me.led_seen |= {x["id"] for x in xs[-30:]}
            return ok("\n".join(json.dumps(x)[:700] for x in reversed(xs[-30:])) or "Nothing.")

        @tool("queue_post", "Post a task to the team's work queue instead of pushing it on a busy agent: idle experts "
              "pull it. for: agent names or roles that can do it (e.g. ['s-data', 'tester']); empty = any worker. "
              "priority: crit | opt.",
              schema(["task"], {"task": "string", "for": "array", "priority": "string", "note": "string"}))
        async def queue_post(a):
            qid = await hub.queue_post(a["task"], a.get("for") or [], a.get("priority") or "opt", a.get("note"), me.name)
            return ok(f"Queued {qid}.")

        @tool("queue_claim", "Take the most important unclaimed queued task meant for you (atomic: nobody else gets it).",
              schema([], {}))
        async def queue_claim(a):
            x = await hub.queue_claim(me.name)
            if not x:
                return ok("Nothing queued for you.")
            if x.get("note"):
                me.turn_note_refs.add(x["note"])
            return ok(f"You claimed {x['id']} ({x['priority']}, from {x['by']}): {x['task']}\nWhen finished: queue_done(id, result).")

        @tool("queue_done", "Mark a claimed queued task done, with a one-line result (the poster is told).",
              schema(["id", "result"], {"id": "string", "result": "string"}))
        async def queue_done(a):
            return ok(await hub.queue_done(a["id"], a["result"], me.name))

        @tool("share_file", "Make a file on THIS laptop available to agents on the OTHER laptop (each laptop has its own repo "
              "copy and folders: they can't see your paths). Give path (a file, or a folder: it is packed as .tar.gz) and "
              "optionally to= an agent name, which gets a message with the id. Returns the id; the receiver calls "
              "fetch_file(id). Max 60 MB. Use it for tables (theory/out/*.json) going to d-platform, candidate zips going to "
              "s-tester, analysis files for d-challenger. Hand histories may be shared this way (never into git).",
              schema(["path"], {"path": "string", "to": "string", "note": "string"}))
        async def share_file(a):
            src = Path(a["path"]).expanduser()
            if not src.is_absolute():
                src = Path(getattr(me, "cwd", hub.repo)) / src
            if not src.exists():
                return ok(f"No such file or folder: {src}")
            def pack() -> tuple[str, bytes]:
                if src.is_dir():
                    import io, tarfile
                    buf = io.BytesIO()
                    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
                        tf.add(str(src), arcname=src.name, filter=lambda ti: None if ".git" in Path(ti.name).parts else ti)
                    return src.name + ".tar.gz", buf.getvalue()
                return src.name, src.read_bytes()
            name, data = await asyncio.to_thread(pack)
            if len(data) > 60_000_000:
                return ok(f"{name} is {len(data) // 1_000_000} MB: too big to share (max 60). Share a smaller file.")
            fid = "S" + new_id()[1:7].upper()
            try:
                await asyncio.wait_for(hub.file_store().put.aio(fid, {"name": name, "data": data, "from": me.name,
                                                                      "at": time.time()}), 120)
            except Exception as e:  # noqa: BLE001
                return ok(f"Couldn't share it ({type(e).__name__}: the link may be down). Try again in a minute.")
            if a.get("to"):
                await hub.bus.send({"id": new_id(), "from": me.name, "from_kind": "agent", "to": a["to"].strip(), "kind": "fyi",
                                    "text": f"Shared file {name} ({len(data) // 1024} KB): fetch_file('{fid}')."
                                            + (f" {a['note']}" if a.get("note") else "")})
            return ok(f"Shared as {fid} ({name}, {len(data) // 1024} KB). The other laptop gets it with fetch_file('{fid}')"
                      + (f"; {a['to']} was told." if a.get("to") else "."))

        @tool("fetch_file", "Get a shared file from either laptop by its id: a human's attachment ('F3A9C1') or an agent's "
              "share_file ('S8B2D0'). Saved into your laptop's repo inbox/ (a shared folder arrives as .tar.gz: unpack it "
              "with tar -xzf); returns the path.", schema(["id"], {"id": "string"}))
        async def fetch_file(a):
            fid = a["id"].strip().upper()
            local = next(iter((hub.repo / "inbox").glob(f"{fid}-*")), None) if (hub.repo / "inbox").exists() else None
            if local:
                return ok(f"Already here: {local}")
            v, t0_ = None, time.time()
            while time.time() - t0_ < 90:   # it may still be uploading from the other laptop
                try:
                    v = await asyncio.wait_for(hub.file_store().get.aio(fid), 30)
                except Exception as e:  # noqa: BLE001
                    return ok(f"Couldn't fetch {fid}: {type(e).__name__}")
                if v:
                    break
                await asyncio.sleep(5)
            if not v:
                return ok(f"No shared file {fid} after 90 s (the upload from the other laptop may have failed: ask its owner).")
            (hub.repo / "inbox").mkdir(exist_ok=True)
            pth = hub.repo / "inbox" / f"{fid}-{v['name']}"
            pth.write_bytes(v["data"])
            return ok(f"Saved to {pth}")

        @tool("report_progress", "Show progress on the humans' board: item = a short plain label for one of YOUR main "
              "deliverables (e.g. 'Maths tables', 'Round 2 analysis', 'Challenger 3', 'Test rig'), state = in progress | "
              "done | failed. No context, no numbers: the humans click the tile to open you and read the detail. Call it when "
              "a main deliverable starts and when it ends; not for small steps.",
              schema(["item", "state"], {"item": "string", "state": "string"}))
        async def report_progress(a):
            item = re.sub(r"\s+", " ", str(a["item"])).strip()[:60]
            st = a["state"] if a["state"] in ("in progress", "done", "failed") else "in progress"
            if not item:
                return ok("Give the item a short label.")
            norm = lambda x: re.sub(r"[^a-z0-9]+", "-", re.sub(r"^build\s*·\s*", "", x.lower())).strip("-")   # noqa: E731
            key, label = norm(item), item
            for t in hub.tiles():   # the hub's own tile for the same thing ('Build · Test rig', 'Round 2 analysis') is updated, not duplicated
                if norm(t["label"]) == key:
                    key, label = t["id"], t["label"]
                    break
            await hub.tile(key, label, st, owner=me.name)
            return ok(f"Board: {item} · {st}.")

        @tool("next_bot_name", "The next free release name (v1, v2, ...). Use it for every release.", schema([], {}))
        async def next_bot_name(a):
            ns = [int(m.group(1)) for b in hub.bots() if (m := re.fullmatch(r"v(\d+)", b["name"]))]
            ns += [int(m.group(1)) for z in (hub.repo / "releases").glob("v*.zip") if (m := re.fullmatch(r"v(\d+)", z.stem))]
            return ok(f"v{max(ns, default=0) + 1}")

        @tool("register_bot", "Record a bot in the team's bot list (the humans' 'Live' menu): file (e.g. 'releases/v3.zip' or "
              "the planned name), status building / testing / ready / failed, and a short note (what it is, test result). "
              "Call it when you start a candidate, when it's in testing, and when it's released or fails.",
              schema(["file", "status"], {"file": "string", "status": "string", "note": "string"}))
        async def register_bot(a):
            st = a["status"] if a["status"] in ("building", "testing", "ready", "failed") else "building"
            if not re.fullmatch(r"v\d+", bot_name(a["file"])):
                return ok("Bots are named v1, v2, ... (get one from next_bot_name); register 'releases/vN.zip'.")
            await hub.register_bot(a["file"], st, a.get("note") or "", me.name)
            if st in ("testing", "ready") and me.name.startswith("d-"):
                await hub.route("candidate", bot_name(a["file"]) + ":" + st, bot=a["file"], status=st, by=me.name,
                                note=a.get("note") or "")
            return ok(f"{bot_name(a['file'])}: {st}.")

        @tool("update_proposal", "Update a decision or note. rule_answer= (a 'Which bot?' decision) the released file the "
              "pre-registered rule now picks, e.g. once the practice result lands; it plays if nobody answers. note= a progress line or a result shown in its chat; summary= replaces the "
              "note's pinned summary. status approved / rejected (with decided_by=<the human>) records a human's decision "
              "given in the note's chat, only when they clearly made it. Also: "
              "note's pinned summary (for an analysis note: the high-level picture in plain words + numbered suggestions "
              "for what to do); status planned / running / done / blocked. When a later result corrects or settles "
              "something the summary says (a withdrawn number, 'not confirmed yet'), rewrite the summary too: humans read "
              "it first.",
              schema(["id"], {"id": "string", "status": "string", "note": "string", "rule_answer": "string", "summary": "string", "decided_by": "string"}))
        async def update_proposal(a):
            me.turn_note_refs.add(a["id"].lstrip("#"))
            p = hub.get_prop(a["id"].lstrip("#"))
            if not p:
                return ok("No such card.")
            st = a.get("status")
            if p.get("status") == "removed":
                return ok(f"Card #{p['id']} was removed from the board by a human; it's no longer relevant. Stop work on it.")
            if st in ("approved", "rejected"):
                if p.get("status") in ("approved", "rejected") and st != p["status"] and me.human_in_turn and \
                        a.get("decided_by") in PEOPLE.values() and a.get("decided_by") != p.get("decided_by"):
                    return ok(await hub.decision_conflict(p, st, a["decided_by"], me.human_text_in_turn or ""))
                if p.get("status") not in ("needs_call", "revise", "expired") or p.get("kind") not in ("bot", "question"):
                    return ok(f"Note #{p['id']} isn't waiting for a decision ({p.get('status')}).")
                humans = [t for t in p.get("thread", []) if t.get("who") in PEOPLE.values() and t.get("at", 0) >= p.get("created", 0)]
                if not humans and me.name.endswith("overview") and me.human_in_turn and (me.human_text_in_turn or "").strip():
                    said = {"who": a.get("decided_by") if a.get("decided_by") in PEOPLE.values() else PEOPLE[hub.person],
                            "at": time.time(), "action": "answer (in the Chat)", "text": me.human_text_in_turn.strip()[:600]}
                    p.setdefault("thread", []).append(said)   # the human's own words, kept with the decision
                    humans = [said]
                who_ = a.get("decided_by") if a.get("decided_by") in PEOPLE.values() else (humans[-1]["who"] if humans else None)
                if not humans or not who_:
                    return ok("No human has answered in this note yet: a decision is recorded only from what a human said.")
                p["status"], p["decided_by"] = st, who_
                p.pop("conflict", None)
                p.setdefault("thread", []).append({"who": "Hub", "at": time.time(), "action": st,
                                                   "text": f"Recorded: {who_} {'approved' if st == 'approved' else 'said no to'} this."})
                if st == "approved" and p.get("bot"):
                    await hub.make_live(p["bot"], who_, f"approved by {who_} (decision #{p['id']})", tell=me.name != "d-overview")
                await hub.tile("decide-" + p["id"], ("Bot choice: " + bot_name(p["bot"])) if p.get("bot") else ("Question: " + p["title"][:60]),
                               (f"decided: {'use ' + bot_name(p['bot']) if p.get('bot') else 'yes'}" if st == "approved" else "decided: no"))
            elif st in ("planned", "running", "done", "blocked"):
                p["status"] = st
            if a.get("rule_answer") and p.get("kind") == "bot" and p.get("status") in ("needs_call", "revise"):
                if not re.fullmatch(r"v\d+", bot_name(a["rule_answer"])):
                    return ok("rule_answer must be a released file named vN.")
                p["rule_answer"] = a["rule_answer"]   # the practice landed: the rule's answer, applied if nobody answers
                p.setdefault("thread", []).append({"who": me.title, "at": time.time(), "action": "rule",
                                                   "text": f"The rule's answer is now {bot_name(a['rule_answer'])}."})
            if a.get("summary"):
                p["body"] = a["summary"][:8000]
                p["body_at"] = time.time()
                p["thread"] = p.get("thread", []) + [{"who": me.title, "at": time.time(), "action": "summary",
                                                     "text": "Updated the summary and suggestions (top of this note)."}]
            if a.get("note"):
                p.setdefault("thread", []).append({"who": me.title, "at": time.time(), "action": st or "note", "text": a["note"][:6000]})
            await hub.save_prop(p)
            return ok(f"Note #{p['id']} updated.")

        @tool("list_proposals", "Notes on the board (open ones first) with status and the humans' replies.",
              schema([], {"only_open": "boolean"}))
        async def list_proposals(a):
            ps = hub.props()
            if a.get("only_open", True):
                ps = [p for p in ps if p.get("status") in OPEN]
            rows = []
            for p in ps[:40]:
                last = (p.get("thread") or [{}])[-1]
                rows.append(f"#{p['id']} [{p['kind']}/{p['status']}] {p['title']} (by {p.get('author')}, owner {p.get('owner')})"
                            + (f" — last: {last.get('who')}: {str(last.get('text'))[:160]}" if last else ""))
            return ok("\n".join(rows) or "No cards.")

        return create_sdk_mcp_server("hub", tools=[send_message, share_file, list_agents, read_agent, set_status, notify_human,
                                                   start_agent, stop_agent, declare_live, set_schedule, propose,
                                                   update_proposal, list_proposals, codex_task, register_bot,
                                                   record, verify, invalidate, set_rules, ledger, next_bot_name,
                                                   queue_post, queue_claim, queue_done, fetch_file, report_progress])


# ======================================================================== playbook (START_HERE.md section 6)
BUILD = [  # (minute, who, what) for the build hour
    (0, "both", "Variant announced: fetch the kit, read the Format page (weights, payouts, anything unusual). d-overview starts d-platform on Part 1 with TWIST_NOTES.md."),
    (10, "dylan", "Deadline: a minimal legal bot uploaded and confirmed active on the portal."),
    (15, "both", "Test rig running (Part 3a: paired runs, sparring). Samuel's side measures every candidate."),
        (17, "dylan", "Practice round 1 starts in 3 minutes: the bot Dylan's Chat named for it should be uploaded and active now."),
    (20, "dylan", "Practice round 1 plays the first legal, upload-tested style. Which bot plays each practice is Dylan's Chat's call: the most informative test."),
    (27, "dylan", "Practice round 2 starts in 3 minutes: the bot Dylan's Chat named for it should be uploaded and active now."),
    (30, "dylan", "Practice round 2 plays the most informative candidate (A, B, C, the clean-room D or another), built with the newest shared tables."),
    (37, "dylan", "Practice round 3 starts in 3 minutes: the bot Dylan's Chat named for it should be uploaded and active now."),
    (40, "dylan", "Practice round 3 plays the most informative candidate not yet measured (or the leader's closest rival)."),
    (47, "dylan", "Practice round 4 starts in 3 minutes: the bot Dylan's Chat named for it should be uploaded and active now."),
    (50, "both", "Practice round 4: the leader, or the closest untested contender if the leader is already clear. Then hands off: the best real-field scorer (adjusted for field, tables and round size) is active for scored round 1."),
]
WINDOW = [  # (minutes before a scored round, who, what)
    (20, "both", "The previous scored round has started. The challenger should already be packed and tested."),
    (13, "both", "The previous scored round's result and hand data land about now. Samuel's side: run the round loop (Data on leaks/opponents, Tester on pending candidates). Dylan's side: challenger ready."),
    (12, "dylan", "Upload the challenger and confirm it is active (it plays the practice round). Skip if not ready."),
    (10, "both", "Practice round starts and plays the challenger."),
    (9, "dylan", "Put the live bot back as active straight away."),
    (8, "both", "DECIDE with the pre-registered rule (How we decide §3): the challenger if it clears the SE bar for our standing, else the live bot with this window's changes (up to three, independent, behind settings). s-overview's recommendation is due to d-overview now."),
    (6, "dylan", "Test the chosen bot under upload-test conditions (no time bank)."),
    (5, "both", "No human answer by now: the rule's answer plays (the challenger if it qualified, else the live bot)."),
    (3, "dylan", "Upload the chosen bot and confirm the active bot on the portal. After this, nothing changes."),
]


# What each Overseer dispatches at each step: (person, priority, agent, task). "crit" is the critical path;
# "opt" is worth doing only when on track (drop it first when behind). Keys: b<minute> (build hour) and
# T<minutes before a scored round>. Prompt-pack parts refer to FIRST_PROMPT.md.
DISPATCH = {
    # minute 0: every worker starts on its own build-hour stream (one task each, so nobody waits for a relay)
    "b0": [("dylan", "crit", "d-platform", "set_rules first (players per table, stacks, blinds, hands per match, time limits, weights, payouts) from the kit and the Format page; then FIRST_PROMPT.md Part 1 with TWIST_NOTES.md: a minimal legal bot in bot/ and releases/v1.zip by minute 10, the test harness by 15, today's hand ranking (from s-data) and the twist's value by 20, then the shared platform with every Part 1 check passing. report_progress('v1 and the platform')"),
                      ("dylan", "crit", "d-builder", "Read Part 1 (styles, shared defaults) and TWIST_NOTES.md; draft styles A (wide pressure), B (shove-heavy), C (tight) as settings, built on Platform's interface as soon as it's published. They are starting corners: if today's rules clearly favour another axis (the twist, postflop, short stacks), say so to d-overview and build that instead of the weakest corner. report_progress('Styles')"),
           ("dylan", "crit", "d-challenger", "Clean-room design D (your role): from the kit, the rules card, TWIST_NOTES.md and s-data's tables only (NOT the A/B/C definitions or FIRST_PROMPT's regional strategy), write candidates/D/DESIGN.md by minute 12: what today's variant rewards, the 2-3 strategic axes that matter most, the design you'd build if nobody had told you anything, and what would show it's wrong. Then build it on Platform's interface as a style; it may play any practice round once it passes the upload test. report_progress('Style D (clean-room)')"),
           ("samuel", "crit", "s-data", "Two streams, in parallel subagents: (1) the maths tables (FIRST_PROMPT.md Part 1b): ranking by m15, ICM by m22, twist by m25, push/fold + call tables by m30, exploit thresholds by m40, HANDOFF by m45, each sent to d-platform as it's ready; (2) parsers for today's hand-history format and analysis/roundcard.py (card in < 60 s), ready for practice 1's download (~minute 25). report_progress('Maths tables') and report_progress('Round card script')"),
           ("samuel", "crit", "s-tester", "Check the rules card against the kit and Format page as soon as d-platform sets it. Then Part 3a: the paired runner on identical deals plus sparring bots, running by minute 15. report_progress('Test rig')"),
           ("samuel", "crit", "s-scout", "Read docs/FINGERPRINTING.md; build analysis/fp_train.py so it runs on practice 1's labelled download (~minute 25) in under 60 s (quick mode). report_progress('Fingerprinting')")],
        # pre-event research: notes only, no bot code (event rules); started when a human types "start the research"
    "pre": [("samuel", "crit", "s-data", "Pre-event research (FIRST_PROMPT Part 0, topic A): the regional variants and Pittsburgh's (search for it), ten plausible Finals twists and the fastest correct way to value each by enumeration. Notes only, NO bot code. Write notes/pre/variants.md; one subagent per topic"),
            ("samuel", "crit", "s-scout", "Pre-event research: what will the Finals field do? Every finalist knows the regional lessons (wide 3-betting won, per-seat adaptation, fold-to-3-bet ~65%). Which styles will be crowded, what punishes them, what practice 1's field (mostly minimal bots) vs round 3's will look like, and what to watch for first. Notes only, NO code. notes/pre/field.md"),
            ("samuel", "crit", "s-tester", "Pre-event research (Part 0, topic D): the test plan for today: sparring bots to write, paired deals, noise first, replay testing on a download, the cloned field on Modal, a confirmation run. Notes only, NO bot code. notes/pre/testplan.md"),
            ("dylan", "crit", "d-platform", "Pre-event research (Part 0, topic C): the first-hour build plan: the safety shell, three layers, what to precompute at import, a 0.3 ms equity estimate, per-seat estimates with priors, the checks that catch the bugs that sank bots. Notes only, NO bot code. notes/pre/buildplan.md"),
            ("dylan", "crit", "d-builder", "Pre-event research (Part 0, topic B): what wins sit-and-gos of AI-built bots (preflop aggression with planned responses, postflop folding vs bluff rates, shove-or-fold by depth, ICM for different payouts, heads-up and 3-handed). Notes only, NO bot code. notes/pre/whatwins.md"),
            ("dylan", "crit", "d-challenger", "Pre-event research, the contrarian memo: assume 19 strong teams all read the same regional lessons. Three designs that would beat that field, what each loses to, and how we'd know within one practice round which one this field pays. Notes only, NO bot code. notes/pre/contrarian.md")],
    "b10": [("dylan", "crit", "d-platform", "v1 must be released now (releases/v1.zip, upload-tested) and d-overview told the exact file")],
    "b15": [("samuel", "crit", "s-tester", "The test rig must run now: first verdict on v1 (correct? timing?) to d-platform and both Chats")],
        "b20": [("dylan", "crit", "d-builder", "Have the next style ready (legal and upload-tested is enough); d-overview picks which plays each practice. Rebuild every style with the newest shared tables before its upload, so practice scores compare styles, not timing"),
            ("dylan", "crit", "d-platform", "Build s-data's hand ranking and ICM thresholds into the platform now (behind settings, ON by default once checked) so every style uploaded from now on uses them; push/fold tables follow at minute 30"),
            ("dylan", "crit", "d-overview", "Pick which bot plays practice 2 (minute 30): the most informative test, not a fixed rota. Tell Dylan the exact file by minute 28"),
            ("samuel", "crit", "s-data", "When practice 1's round card lands: the defaults check, then the leaks of the bot that played (Part 2), the top change in 5 minutes. report_progress('Practice 1 analysis') is automatic; record the one-change when done")],
        "b30": [("dylan", "crit", "d-platform", "Build s-data's push/fold and call tables and the twist rule into the platform now; every style picks them up at its next upload"),
            ("dylan", "crit", "d-builder", "Keep each style current with the platform; the next one ready for practice 3 as d-overview picks"),
            ("dylan", "crit", "d-overview", "Pick which bot plays practice 3 (minute 40): the candidate whose real-field score we most need (D if not yet measured). Tell Dylan the exact file by minute 38"),
            ("samuel", "crit", "s-data", "Refit the call tables' shove-width and fold-rate columns from practice 1's real data and re-issue; then practice 2's leaks and styles A vs B on the real field"),
                        ("samuel", "crit", "s-scout", "First FIELD TREND from practices 1-2 (field rates, what the best teams do; note that practice 1's field is mostly minimal bots), first profiles, recogniser accuracy (same-round) and how identifiable we are")],
        "b40": [("dylan", "crit", "d-builder", "Keep the styles current; whichever d-overview names for practice 4 ready by minute 48"),
            ("dylan", "crit", "d-challenger", "From practices 1-3 (real-field scores, s-scout's field trend and profiles): choose the first challenger for the practice before scored round 2: D matured, the best response to the field's measured mix, or what the data points to. Say why in one line. report_progress('Challenger 1')"),
            ("dylan", "crit", "d-overview", "Pick practice 4 (minute 50): the leader, or its closest unmeasured rival if the leader is already clear. Tell Dylan by minute 48"),
            ("samuel", "crit", "s-tester", "Rank every style that played (A, B, C, D, ...) for the round-1 choice, adjusting for confounds: which tables each had, practice size, how mature the field was. Add replay tests of each style on the same downloads (same field, same deals). Say which comparison carries the decision; send it to s-overview")],
    "b50": [("dylan", "crit", "d-platform", "Release the bot d-overview names for scored round 1 (the best real-field scorer unless the humans said otherwise)"),
                        ("samuel", "crit", "s-data", "Which style did the field reward, and what are the best teams doing (winners lens)? One paragraph with the numbers to s-overview for the round-1 decision; if no style we built matches what wins, say so (PLAN CHALLENGE)")],
    "T20": [("samuel", "crit", "s-tester", "Verify the challenger's paired-test verdicts and methods now (they don't depend on the new round), and pre-arm analysis/verify_change.py + a Codex brief that recompute the card's headline numbers from a hand file, so at T-12 only the data path changes"),
                        ("dylan", "crit", "d-overview", "Prepare the 'Which bot?' question for the next scored round: the pre-registered rule, both bots' numbers as they land, the rule's answer"),
            ("samuel", "crit", "s-overview", "Step back: from the last field trend and winners lens, is our base approach still right? Sync with d-overview in 3 lines; if not, raise it with Samuel now and make sure d-challenger builds the alternative")],
    "T13": [            ("samuel", "crit", "s-data", "As soon as DATA LANDED (not before; wait for it), from the round card (the hub runs it): the defaults check (a report), the winners lens, our leaks (Part 2), every independent change that clears the bar (lens subagents + a Codex recompute), recorded with question='one-change <stage>' by T-9; then opponent profiles where a profile pays most"),
            ("samuel", "crit", "s-tester", "Re-run the numbers the T-8 decision may rest on (card headline, s-data's changes) and verify each; give every pending candidate a verdict (correct? paired vs the live bot); optional if on track: the cloned field on Modal for the challenger"),
                        ("samuel", "crit", "s-scout", "First the FIELD TREND (analysis/<stage>/field_trend.md; plan assumptions checked; a PLAN CHALLENGE if one breaks), then the fingerprint card: counters on/off by the gate, counters.json to d-platform, accuracy/drift to s-tester, by T-9"),
                        ("dylan", "crit", "d-builder", "Opponent counters from s-scout and this window's live-bot fixes from s-data (each independent, each behind a setting), each in its own folder, each sent to s-tester"),
            ("dylan", "crit", "d-challenger", "This window's practice plays the challenger you already released (or the most informative released bot). Start the NEXT challenger now from this round's data, s-scout's field trend and any PLAN CHALLENGE: D, the best response to the measured mix, or a rewrite; say why in one line. report_progress('Challenger <n>')"),
            ("dylan", "crit", "d-platform", "Fix bugs s-tester reported; build this window's live-bot changes (each independent, each behind a setting)")],
        "T12": [("dylan", "crit", "d-platform", "Release the challenger d-challenger has ready and tested (releases/<name>.zip) so Dylan can upload it for the practice round; tell d-overview the exact file. Nothing tested: tell d-overview which released bot is the most informative to play instead")],
    "T9": [("samuel", "crit", "s-overview", "Send d-overview the recommendation now (it asks the humans at T-8), applying the pre-registered rule (standings, the field-adjusted bar), with both bots' numbers, the rule's answer as a released file, and the evidence (validated, or labelled unverified). Practice results usually land at T-8 to T-7: until then send the threshold (the practice score the challenger needs, given the yardstick teams), then the final answer the moment it lands; with no practice result by T-6 the rule's answer is the live bot")],
    "T8": [("dylan", "crit", "d-overview", "Ask the 'Which bot?' question now: propose(kind='bot', rule_answer=<the file the rule picks>, deadline_minutes until T-5) with s-overview's numbers, and ask Dylan in plain words in your reply")],
    "T6": [("dylan", "crit", "d-platform", "Test the chosen bot with no time bank; release it as releases/<name>.zip")],
    "T3": [("dylan", "crit", "d-platform", "The chosen bot's release must be ready; confirm the exact file to d-overview")],
}
# Standing reminders the clock re-sends to specific agents, so the habits that matter survive long runs and
# compaction: (trigger, person, agent or "*workers", text, wake). Triggers: b<min> (build hour), T<offset> (each
# scored round's window), "every10" (every 10 event-minutes during the event).
REMINDERS = [
    ("T13", "both", "*workers", "Round data is landing. Record every result you have in the ledger (effect, se, n, method, "
     "note), update your brief, and send a one-line fyi with the file path to whoever depends on it.", False),
    ("T13", "samuel", "s-data", "New real-field data: refit the call/fold columns of your tables from it and re-issue them "
     "(real-field numbers outrank the tables).", True),
        ("T13", "samuel", "s-scout", "New download: the field trend first (what moved, plan assumptions checked), then the fingerprint "
     "card (or run fp_train.py if the hub couldn't), counters by the gate, counters.json to d-platform and the accuracy/drift "
     "items to s-tester, all by T-9.", True),
    ("T13", "samuel", "s-tester", "Check the ledger's persistent leaks (the same leak in two rounds) first: verify them so the "
     "fix can ship this window.", False),
    ("T20", "both", "*overseers", "Sync with the other laptop's Chat (the other lead) in 3 lines (what changed on your side, what you need from "
     "theirs, the plan for this window) and update your PLAN file.", True),
    ("T3", "both", "*workers", "Before this round starts: anything you found that isn't in the ledger yet, record it now; "
     "update your brief.", False),
    ("T3", "both", "*overseers", "Update your PLAN file (what plays, what's running where, open promises) and make sure "
     "every worker has its next task queued for when data lands.", False),
    ("every10", "both", "*workers", "Capacity check: if you have independent work (tests, sweeps, re-checks, a second opinion), "
     "put it on Modal or Codex now rather than in line; we have budget to spend (Modal about $300, Codex credits).", False),
    ("every10", "both", "*overseers", "Is any finding still only in someone's head or chat rather than in the ledger, and is "
     "anyone idle while work is queued? Fix both now.", False),
    ("b0", "both", "*workers", "Reminders from the plan: record results in the ledger, keep your brief current, ask the owner "
     "when something is missing (team directory), fan out to subagents/Modal/Codex for independent pieces.", False),
]


def has_reminder(trig: str, person: str) -> bool:
    return any(t == trig and who in ("both", person) for t, who, _, _, _ in REMINDERS)


def reminder_targets(hub: "Hub", who: str) -> list:
    if who == "*workers":
        return [a for a in hub.agents.values() if not a.name.endswith("overview")]
    if who == "*overseers":
        return [a for a in hub.agents.values() if a.name.endswith("overview")]
    return [hub.agents[who]] if who in hub.agents else []


# checkpoints the Overseer compares against reality every turn (person, key, what must be true by then)
CHECKPOINTS = [
    ("dylan", "b10", "a legal bot is uploaded and active"), ("samuel", "b15", "the test rig gives verdicts"),
    ("dylan", "b20", "today's ranking and twist value exist; style A is tested"), ("dylan", "b40", "styles A, B, C all tested"),
    ("dylan", "T12", "the challenger is packed and tested"), ("samuel", "T8", "the recommendation is with d-overview"),
    ("dylan", "T8", "the decision card is posted"), ("dylan", "T3", "the chosen bot's release is ready"),
    ("dylan", "b10", "the rules card is set (players per table, stacks, blinds)"),
    ("samuel", "T12", "the round card for the round that just landed is written"),
    ("samuel", "b20", "s-data's ranking and ICM tables are with d-platform"),
    ("dylan", "b40", "the bot playing practice 3 uses s-data's push/fold tables and twist rule (so they get a real-field test before scored round 1)"),
    ("samuel", "T8", "the recommendation is with d-overview, citing ledger ids (validated preferred; none disputed)"),
]


# The gate: which expert gets which event, decided by rules, not by a model (the split of work is known in
# advance, so hand-written routing beats a learned router; RouteLLM-style routers fail out of distribution).
# Each event goes to ONE owner (top-1) plus, for decision-critical items only, a verifier (top-2). The Overseer
# is woken only for what needs a lead: disputes, invalidations, humans, deadlines and anything unrouted.
ROUTES = {
    "card_ready": [("s-data", "task", "Round card for {stage} is ready: {card}. The defaults check, then the one-change proposal "
                                      "(LENSES: 3 lens subagents in one message + 1 Codex recompute of the top number), aggregate "
                                      "by T-9, record with question='one-change {stage}'."),
                   ("s-tester", "task", "Round card for {stage} is ready: {card}. Check its headline numbers against the raw "
                                        "files (your pre-armed verify script), verify the card's ledger items, and recalibrate "
                                        "the sparring bots from its opponent table before the next paired test.")],
        "fp_ready": [("s-scout", "task", "Fingerprint card for {stage} is ready: {card}. First the field trend (analysis/<stage>/"
                                     "field_trend.md, plan assumptions checked; PLAN CHALLENGE if one breaks), then counters "
                                     "on/off per team by the gate, counters.json to d-platform, s-tester the accuracy/drift "
                                     "items, by T-9.")],
    "candidate": [("s-tester", "task", "New candidate {bot} ({status}) from {by}: give it a verdict (correct? stronger? paired, "
                                       "at the rules card's table size). {note}")],
}
OVERSEER_WAKES = ("task", "question")   # fyi/answers to an Overseer ride along with its next turn unless urgent


# How wide each dispatched job should fan out (effort scaling: the lead sets the budget, the worker splits).
FANOUT = {
    "d-platform": "fan out: one subagent per independent piece (engine adapter / hand ranking / packaging+checks); Sonnet for packaging and scripts",
    "d-builder": "fan out: one subagent per style, counter or fix, in parallel, each in its own folder; Modal (up to 20) for sparring each",
    "d-challenger": "fan out: 2-3 subagents on alternative challenger designs in parallel, each in its own folder; Modal (up to 20) for sparring and the cloned field; Codex for an independent review",
    "s-data": "fan out: build hour, one subagent per maths deliverable plus a Sonnet subagent for the parser/card; rounds, 3 lens subagents in ONE message (3-min cap) + 1 Codex recompute, aggregate by T-9; Sonnet for counting; Modal <= 20 for equity tables",
    "s-tester": "fan out: shard paired runs across Modal (up to 40 containers); one subagent per candidate for the 'correct?' review; one Codex re-implementation for numbers a decision rests on (2 minutes per item before T-8)",
    "s-scout": "fan out: one subagent per team for specialist studies; Codex for an independent re-implementation of the accuracy numbers; Modal for counter A/B sims",
    "s-overview": "", "d-overview": "",
}


def dispatch_text(key: str, person: str) -> str:
    rows = [(pr, ag, t) for (who, pr, ag, t) in DISPATCH.get(key, []) if who == person]
    if not rows:
        return ""
    return ("\nThe clock has ALREADY given each worker its task below (don't resend it). Your job: add context only you "
            "have (which bot played, what's already done, what your human asked), keep them unblocked, and drop optional "
            "work if you're behind:\n" + "\n".join(
                f"- [{'CRITICAL' if pr == 'crit' else 'optional'}] {ag}: {t}" for pr, ag, t in rows))


def worker_tasks(key: str, person: str) -> list[tuple[str, str, str]]:
    """(agent, priority, task text) the clock hands straight to each worker at this mark (no relay through the lead)."""
    return [(ag, pr, t + (f" ({FANOUT[ag]})" if FANOUT.get(ag) else "")) for (who, pr, ag, t) in DISPATCH.get(key, [])
            if who == person and not ag.endswith("overview")]


# steps a person does with their own hands (clock reminders shown to that person)
HUMAN_STEPS = {
    "b0": {"samuel": "Set the clock's minute 0 if it isn't set, and read the Format page.",
           "dylan": "Fetch the kit and read the Format page."},
    "b10": {"dylan": "UPLOAD"},
    "b17": {"dylan": "Practice 1 starts in 3 minutes: upload the bot your Chat named for it (Live menu) if it isn't active yet."},
    "b27": {"dylan": "Practice 2 starts in 3 minutes: upload the bot your Chat named for it (Live menu) if it isn't active yet."},
    "b37": {"dylan": "Practice 3 starts in 3 minutes: upload the bot your Chat named for it (Live menu) if it isn't active yet."},
    "b47": {"dylan": "Practice 4 starts in 3 minutes: upload the bot your Chat named for it (Live menu) if it isn't active yet."},
    "12": {"dylan": "UPLOAD"},
    "9": {"dylan": "UPLOAD"},
    "8": {"samuel": "Decision time: the 'Which bot?' question is pinned at the top of your Chat. Answer it there in words.",
          "dylan": "Decision time: the 'Which bot?' question is pinned at the top of your Chat. Answer it there in words."},
    "3": {"dylan": "UPLOAD"},
}


def situation(hub: "Hub") -> str:
    """Exact 'where are we' snapshot put at the top of every Overseer turn."""
    now = time.time()
    me = hub.person
    sch = hub.bus.shared.get("schedule")
    sim = sch and sch.get("scale", 1) < 1
    lines = [f"Now {hhmm(now)}."]
    if sim:
        lines.append(f"SIMULATED REHEARSAL: the event runs {1 / sch['scale']:.0f}x fast. One event-minute = "
                     f"{60 * sch['scale']:.0f} real seconds, so 'minute 20' or 'T-8' are event-minutes, while every HH:MM "
                     "shown is the real clock time it happens. Trust the HH:MM times; they are already converted. "
                     "Work fast: a 20-minute window is only a few real minutes.")
    if not sch:
        lines.append("PHASE: unknown (no clock set). Ask your human for minute 0 (the variant announcement) or set it "
                     "with set_schedule; until then, assume nothing is playing.")
    else:
        t0, nsc = sch["start"], sch.get("scored", 6)
        U = 60 * sch.get("scale", 1.0)   # seconds per event-minute (less than 60 only in sped-up simulations)
        m = (now - t0) / U
        rounds = round_starts(sch)
        if m < 0:
            lines.append(f"PHASE: before the event; minute 0 is at {hhmm(t0)} (in {-m:.0f} min).")
        elif now < rounds[0]:
            done = [f"min {mi}: {w}" for mi, who, w in BUILD if build_ts(sch, mi) <= now and who in ("both", me)]
            nxt = next(((mi, w) for mi, who, w in BUILD if build_ts(sch, mi) > now and who in ("both", me)), None)
            lines.append(f"PHASE: build hour, minute {m:.0f} of {(rounds[0] - t0) / U:.0f}. Scored round 1 at {hhmm(rounds[0])}.")
            if done:
                lines.append("Should be done by now: " + " | ".join(done[-2:]))
            if nxt:
                lines.append(f"Next (step {nxt[0]}, {hhmm(build_ts(sch, nxt[0]))}): {nxt[1]}")
            T1 = (rounds[0] - now) / U
            if T1 <= 9:
                r1 = [(o, w) for o, who, w in WINDOW if o <= 8 and who in ("both", me)]
                cur = [x for x in r1 if x[0] >= T1]
                nx = next((x for x in r1 if x[0] < T1), None)
                if cur:
                    lines.append(f"Scored round 1, T-{math.ceil(T1)}: current step (T-{cur[-1][0]}): {cur[-1][1]}")
                if nx:
                    lines.append(f"Next step at T-{nx[0]} ({hhmm(rounds[0] - nx[0] * U)}): {nx[1]}")
        elif now > rounds[-1] + 20 * U:
            lines.append("PHASE: the event is over.")
        else:
            k = next((i + 1 for i, ts in enumerate(rounds) if ts > now), None)
            if k is None:
                lines.append(f"PHASE: the last scored round ({nsc}) is playing; results due about {hhmm(rounds[-1] + 8 * U)}.")
            else:
                ts = rounds[k - 1]
                T = (ts - now) / U
                w = (hub.rules().get("weights") or [])
                wtxt = f"weight {w[k - 1]} of {sum(w)}" if isinstance(w, list) and len(w) >= k else "weight: read it from the rules card / Format page"
                lines.append(f"PHASE: window before scored round {k} ({wtxt}) at {hhmm(ts)}: T-{math.ceil(T)} min.")
                past = [(o, w) for o, who, w in WINDOW if o >= T and who in ("both", me)]
                nxt = next(((o, w) for o, who, w in WINDOW if o < T and who in ("both", me)), None)
                if past:
                    lines.append(f"Current step (T-{past[-1][0]}): {past[-1][1]}")
                if nxt:
                    lines.append(f"Next step at T-{nxt[0]} ({hhmm(ts - nxt[0] * U)}): {nxt[1]}")
    if sch:
        due = []
        U2 = 60 * sch.get("scale", 1.0)
        t0 = sch["start"]
        nsc = sch.get("scored", 6)
        for who, key, what in CHECKPOINTS:
            if who != me:
                continue
            if key.startswith("b"):
                at = build_ts(sch, int(key[1:]))
                if at <= now < round_starts(sch)[0]:
                    due.append(f"by minute {key[1:]}: {what}")
            else:
                off = int(key[1:])
                for k, ts in enumerate(round_starts(sch), 1):
                    if ts - off * U2 <= now < ts:
                        due.append(f"by T-{off} of scored round {k}: {what}")
        if due:
            lines.append("Checkpoints that should be TRUE now (check against your workers' briefs): " + "; ".join(due) +
                         ". If any isn't, you're behind: drop extra verification and polish first, put every worker on the "
                         "critical path, keep idea generation, opponent profiles and the challenger going, and say so in your brief.")
    if sch:   # who is free right now, on both laptops, so idle capacity gets used
        now2, load = time.time(), []
        for a in hub.agents.values():
            if not a.name.endswith("overview"):
                age = (time.time() - a.status_at) / 60 if a.status_at else None
                load.append((a.name, a.state, (a.task or "") + (f" [status {age:.0f} min old]" if age and age > 10 else ""), a.idle_since))
        for n, v in hub.bus.directory.items():
            if v.get("person") != me and not v.get("service") and not n.endswith("overview") and now2 - v.get("seen", 0) < 120:
                load.append((n, v.get("state"), v.get("task"), v.get("idle_since")))
        idle = [n for n, st, t, since in load if st in ("idle", "done") and (not since or now2 - since > 60)]
        lines.append("Team load: " + "; ".join(f"{n} {st}" + (f" ({(t or '')[:60]})" if st == 'working' and t else "")
                                              for n, st, t, _ in load) + ".")
        if idle:
            lines.append(f"IDLE NOW: {', '.join(idle)} (skip any whose brief says it's waiting on a background Modal/Codex job). Idle agents are wasted time: give each a slice of the critical path "
                         "(split the biggest job: one candidate, one analysis, one test shard each), or the next optional item "
                         "if you're on track. Message the other Overseer if the idle agent is theirs.")
    q = [x for x in hub.queue() if not x.get("done")]
    if q:
        lines.append(f"Work queue: {sum(1 for x in q if not x.get('claimed_by'))} unclaimed "
                     f"({sum(1 for x in q if not x.get('claimed_by') and x.get('priority') == 'crit')} critical), "
                     f"{sum(1 for x in q if x.get('claimed_by'))} in progress.")
    live = hub.bus.shared.get("live")
    lines.append(f"Declared live bot: {live['filename']} ({hhmm(live['at'])})." if live else "Declared live bot: none yet.")
    p = hub.services.get("s-portal") or hub.bus.directory.get("s-portal")
    if p:
        lines.append(f"Portal watcher ({hhmm(p.get('updated') or p.get('seen') or now)}): {p.get('task')}")
    act = hub.bus.shared.get("portal_active")
    if act:
        lines.append(f"Portal's active bot (checked {hhmm(act['at'])} by the portal watcher): {act.get('filename') or 'none'}"
                     + (f", sha256 {act['sha256'][:12]}…" if act.get("sha256") else "") + ". Never ask a human for this.")
    return "[hub situation]\n" + "\n".join(lines) + "\nFollow START_HERE.md section 6 for this phase; trust this brief over memory."


# ======================================================================== codex
class Codex:
    """Runs independent jobs on OpenAI Codex in the background (separate credits, so it adds capacity)."""

    def __init__(self, hub: "Hub", model: str | None, max_jobs: int):
        self.hub, self.model, self.max = hub, model, max_jobs
        self.bin = shutil.which("codex") or next((p for p in ("/Applications/Codex.app/Contents/Resources/codex",)
                                                  if Path(p).exists()), None)
        self.dir = hub.data / "codex"
        self.dir.mkdir(exist_ok=True)
        self.jobs: dict[str, dict] = {}
        self.sem = asyncio.Semaphore(max_jobs)
        self.broken = ""

    def status(self):
        running = [j for j in self.jobs.values() if j["state"] in ("queued", "running")]
        task = ("not installed" if not self.bin else self.broken or
                (f"{len(running)} job(s) running" if running else "idle"))
        summary = "\n".join(f"- **{j['state']}** · {j['agent']} · {j['task'][:90]}" for j in
                            sorted(self.jobs.values(), key=lambda j: -j["at"])[:12])
        self.hub.set_service(f"{self.hub.person[0]}-codex", "Codex", "working" if running else
                             ("error" if self.broken else "idle"), task, summary)

    async def submit(self, agent: "Agent", task: str, folder: str | None, check: str | None) -> str:
        if not self.bin:
            return "Codex isn't installed on this laptop; use a Claude subagent instead."
        if self.broken:
            return f"Codex isn't usable right now ({self.broken}); use a Claude subagent instead."
        jid = "C" + new_id()[1:7]
        wd = Path(folder).expanduser() if folder else agent.cwd
        j = {"id": jid, "agent": agent.name, "task": task, "folder": str(wd), "state": "queued", "at": time.time()}
        self.jobs[jid] = j
        self.status()
        asyncio.create_task(self.run(agent, j, check))
        return f"Codex job {jid} queued (at most {self.max} run at once). You'll get its result as a new turn."

    async def run(self, agent: "Agent", j: dict, check: str | None):
        async with self.sem:
            j["state"] = "running"
            self.status()
            out = self.dir / f"{j['id']}.md"
            log = self.dir / f"{j['id']}.log"
            brief = j["task"] + (f"\n\nWhen done, verify with: {check}" if check else "") + \
                "\n\nEnd with a short summary of what you did and the result."
            models = [self.model] if self.model else [None, "gpt-5-mini"]   # strong default, then a rate-limit fallback
            for mdl in models:
                cmd = [self.bin, "exec", "--ignore-user-config", "-s", "workspace-write", "--skip-git-repo-check",
                       "-C", j["folder"], "-o", str(out)] + (["-m", mdl] if mdl else []) + [brief]
                try:
                    with log.open("w") as lf:
                        proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.DEVNULL, stdout=lf, stderr=lf)
                        rc = await asyncio.wait_for(proc.wait(), 1800)
                except asyncio.TimeoutError:
                    proc.kill()
                    rc = -1
                except Exception as e:  # noqa: BLE001
                    rc, j["error"] = -2, str(e)
                text = out.read_text()[:3000] if out.exists() else ""
                tail = log.read_text()[-1500:] if log.exists() else ""
                if rc == 0 and text:
                    j["model"] = mdl or "default"
                    break
                if not re.search(r"Request too large|tokens per min|rate limit|TPM", tail, re.I):
                    break
            if rc == 0 and text:
                j["state"] = "done"
                msg = f"Codex job {j['id']} finished ({j['folder']}). Full output: {out}\n\n{text}"
            else:
                j["state"] = "failed"
                why = re.search(r'"message":"([^"]+)"', tail)
                reason = why.group(1) if why else (j.get("error") or tail.strip().splitlines()[-1:] or ["unknown error"])[0]
                if re.search(r"not supported when using Codex with a ChatGPT account|not logged in|unauthori|401|403", tail, re.I):
                    self.broken = "not signed in properly or the plan doesn't allow this model"
                    await self.hub.add_alert(f"{self.hub.person[0]}-codex", "Codex can't run jobs: " + reason[:200] +
                                             " Fix: in a terminal run `codex login` (or log in with an OpenAI API key), "
                                             "then restart the hub.", True)
                msg = f"Codex job {j['id']} failed: {reason[:300]}. Do it with a Claude subagent instead. Log: {log}"
            self.status()
            await agent.add_item({"kind": "hub", "wake": True, "text": msg})


# ======================================================================== clock
class Clock:
    """Round schedule shared by both hubs; wakes this laptop's Overseer at the deadlines."""

    def __init__(self, hub: Hub):
        self.hub = hub
        self.sent: set[str] = set(load_json(hub.data / "clock_sent.json", []))
        self.guard = DeadlineGuard(hub)
        self.started_at = time.time()

    def events(self):
        s = self.hub.bus.shared.get("schedule")
        if not s:
            return []
        out = [("practice", k, build_ts(s, m)) for k, m in enumerate((20, 30, 40, 50), 1)]
        rs = round_starts(s)
        for k, ts in enumerate(rs, 1):
            out.append(("scored", k, ts))
            if k < len(rs):
                out.append(("practice", 4 + k, rs[k] - 10 * sched_unit(s)))
        return sorted(out, key=lambda e: e[2])

    async def set_start(self, hhmm_s: str, scored: int = 6, scale: float = 1.0, t0: float | None = None,
                        build: float | None = None, gap: float | None = None):
        if t0 is None:
            m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", hhmm_s or "")
            if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59 or int(m.group(3) or 0) > 59:
                raise ValueError("use HH:MM (24-hour), e.g. 14:02")
            lt = time.localtime()
            cands = [time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, int(m.group(2)), int(m.group(3) or 0), 0, 0, -1))
                     for h in ({int(m.group(1)), int(m.group(1)) + 12} if int(m.group(1)) < 12 else {int(m.group(1))})]
            t0 = min(cands, key=lambda t: abs(t - time.time()))   # "2:05" typed at 14:07 is 14:05, not 02:05
        old = self.hub.bus.shared.get("schedule") or {}
        new = {"start": t0, "scored": scored, "scale": scale, "set_by": self.hub.person, "at": time.time()}
        for f_, v_ in (("build", build or old.get("build")), ("gap", gap or old.get("gap")), ("round_at", old.get("round_at"))):
            if v_:
                new[f_] = v_
        await self.hub.bus.set_shared("schedule", new)
        # marks are keyed by the start time: a new start gets new keys, the same start keeps "already sent"
        if old.get("start") and (abs(old["start"] - t0) > 1 or old.get("scored") != scored or
                                 old.get("build") != new.get("build") or old.get("gap") != new.get("gap")):
            await self.announce_change(old, t0, scored)
        self.hub.emit("shared", {"schedule": self.hub.bus.shared["schedule"]})
        for al in list(self.hub.alerts):   # notices asking for the start time are now answered
            if re.search(r"minute 0|set the clock|no clock", al["text"], re.I):
                self.hub.dismiss(al["id"])
        rs = round_starts(new)
        return f"minute 0 at {hhmm(t0)}; scored round 1 at {hhmm(rs[0])}; last scored round at {hhmm(rs[-1])}."

    async def pin_round(self, k: int, when: float, source: str) -> str:
        """Scored round k really starts at `when` (the portal saw it, or a human said so). Later rounds follow from it,
        and every deadline before them moves; the build hour and rounds already played don't."""
        s = dict(self.hub.bus.shared.get("schedule") or {})
        if not s or not 1 <= k <= int(s.get("scored", 6)):
            return f"no scored round {k} in the schedule"
        before = round_ts(s, k)
        if before is not None and abs(when - before) > 30:   # open decisions for this round move with it
            U = sched_unit(s)
            for p in self.hub.props():
                if p.get("kind") == "bot" and p.get("status") in ("needs_call", "revise") and p.get("deadline") and \
                        before - 20 * U <= p["deadline"] <= before:
                    p["deadline"] += when - before
                    await self.hub.save_prop(p)
        pins = {kk: v for kk, v in (s.get("round_at") or {}).items() if int(kk) < k}
        pins[str(k)] = when
        s["round_at"], s["at"] = pins, time.time()
        await self.hub.bus.set_shared("schedule", s)
        self.hub.emit("shared", {"schedule": s})
        rs = round_starts(s)
        if before is None or abs(before - when) > 30:
            text = (f"Scored round {k} starts at {hhmm(when)} (was {hhmm(before)}; {source}). Later rounds follow: "
                    + ", ".join(f"round {i} {hhmm(t)}" for i, t in enumerate(rs, 1) if i >= k)
                    + ". Every deadline in those windows moves with them; times quoted earlier are out of date.")
            await self.hub.alert_all(f"{self.hub.person[0]}-clock", text, False, chat=True)
            for a in self.hub.agents.values():
                if a.name.endswith("overview"):
                    await a.add_item({"kind": "clock", "wake": True, "text": "[clock changed] " + text})
            other = "d-overview" if self.hub.person == "samuel" else "s-overview"
            try:
                await self.hub.bus.send({"id": new_id(), "from": f"{self.hub.person[0]}-clock", "from_kind": "hub",
                                         "to": other, "kind": "task", "text": "[clock changed] " + text})
            except Exception as e:  # noqa: BLE001
                self.hub.note_error("clock-pin", e)
        return f"scored round {k} at {hhmm(when)}; " + ", ".join(f"round {i} {hhmm(t)}" for i, t in enumerate(rs, 1))

    def carry(self, old: dict, new: dict):
        """The clock moved (on either laptop). A step already sent stays sent only if it is the same occurrence (its
        time moved 5 minutes or less) or its new time is already over; a step now in the future fires at its new time.
        So a false start corrected later still gets the real minute 0, and a sync never re-fires the past."""
        if not old or not new or not old.get("start"):
            return
        otk, ntk, now_ = int(old["start"]), int(new["start"]), time.time()
        if otk == ntk and old.get("round_at") == new.get("round_at") and old.get("build") == new.get("build") \
                and old.get("gap") == new.get("gap"):
            return
        def times(s_):
            out = {f"b{mi}": build_ts(s_, mi) for mi, _, _ in BUILD}
            for kk, ts_ in enumerate(round_starts(s_), 1):
                for o, _, _ in WINDOW:
                    out[f"s{kk}-{o}"] = ts_ - o * sched_unit(s_)
            return out
        ot, nt = times(old), times(new)
        for step, t_new in nt.items():
            was = f"{otk}:{step}" in self.sent
            moved = t_new - ot.get(step, t_new)
            premature = step in ("b0", "b10", "b15") and moved > 300   # sent at a false start: the real one still fires
            if was and not premature and (abs(moved) <= 300 or t_new < now_ - 60):
                self.sent.add(f"{ntk}:{step}")
            elif not was and t_new < now_ - 60 and step not in ("b0", "b10", "b15"):
                self.sent.add(f"{ntk}:{step}")   # long past and never sent: no burst (the build hour's first steps still fire)
            elif was and t_new >= now_ - 60 and otk == ntk:
                self.sent.discard(f"{ntk}:{step}")   # a pinned round moved this step later: it fires again at its new time
        atomic_write(self.hub.data / "clock_sent.json", json.dumps(sorted(self.sent)))

    def tidy_bell(self, s: dict):
        """Clock and deadline notices go stale: a decision prompt once nothing waits for a decision, any clock notice
        after 10 event-minutes, an upload ask once that bot is active (or another bot is live)."""
        hub, now, U = self.hub, time.time(), 60 * s.get("scale", 1.0)
        waiting = any(p.get("kind") == "bot" and p.get("status") in ("needs_call", "revise") for p in hub.props())
        act = norm_bot((hub.bus.shared.get("portal_active") or {}).get("filename"))
        live = norm_bot((hub.bus.shared.get("live") or {}).get("filename"))
        for al in list(hub.alerts):
            t, mine = al.get("text", ""), al.get("agent", "").endswith("-clock")
            up = None if re.search(r"reject|fail", t, re.I) else UPLOAD_ASK.search(t)   # never clear a rejection
            ov_note = al.get("agent", "").endswith("overview") and not al.get("urgent")
            if (mine and "Decision time" in t and not waiting) or (mine and now - al["at"] > 10 * U) or \
                    (ov_note and now - al["at"] > 8 * U) or (al.get("agent", "").endswith("overview") and now - al["at"] > 15 * U) or \
                    (re.search(r"allowance", t) and now - al["at"] > 1800) or \
                    (up and (norm_bot(up.group(1)) == act or (live and norm_bot(up.group(1)) != live))):
                hub.dismiss(al["id"])

    async def announce_change(self, old: dict, t0: float, scored: int):
        """A clock that moves silently leaves the Chats and Overseers quoting the old time: tell everyone."""
        fmt = lambda t: time.strftime("%H:%M:%S", time.localtime(t))   # noqa: E731
        text = (f"The clock was changed by {PEOPLE[self.hub.person]}: minute 0 is now {fmt(t0)} (was {fmt(old['start'])})"
                + (f", {scored} scored rounds" if old.get("scored") != scored else "") + ". Use the new times; any time "
                "quoted earlier is out of date.")
        await self.hub.alert_all(f"{self.hub.person[0]}-clock", text, False, chat=True)   # both Chats show it
        ov = next((a for a in self.hub.agents.values() if a.name.endswith("overview")), None)
        if ov:
            await ov.ov_log("Hub", text)
        for a in self.hub.agents.values():
            if a.name.endswith("overview"):
                await a.add_item({"kind": "clock", "wake": True, "text": "[clock changed] " + text})
        other = "d-overview" if self.hub.person == "samuel" else "s-overview"
        try:
            await self.hub.bus.send({"id": new_id(), "from": f"{self.hub.person[0]}-clock", "from_kind": "hub", "to": other,
                                     "kind": "task", "text": "[clock changed] " + text})
        except Exception as e:  # noqa: BLE001
            self.hub.note_error("clock-change", e)

    def next_step(self):
        """The next clock step for this laptop's person: (epoch, text) or None."""
        s = self.hub.bus.shared.get("schedule")
        if not s:
            return None
        now, me = time.time(), self.hub.person
        t0, U = s["start"], 60 * s.get("scale", 1.0)
        strip = {20: "Practice round 1 starts: the bot chosen for it should be active", 30: "Practice round 2 starts",
                 40: "Practice round 3 starts", 50: "Practice round 4 starts; after it, the bot for scored round 1 goes active"}
        cands = [(build_ts(s, mi), f"min {mi}: {strip.get(mi, w)}") for mi, who, w in BUILD if who in ("both", me)]
        for k, ts in enumerate(round_starts(s), 1):
            cands += [(ts - o * U, f"Scored {k} T-{o}: {w}") for o, who, w in WINDOW
                      if who in ("both", me) and o != 20 and not (k == 1 and o > 9)]
            cands.append((ts, f"Scored round {k} starts"))
        fut = sorted(c for c in cands if c[0] > now)
        return fut[0] if fut else None

    def next_text(self):
        now = time.time()
        for kind, k, ts in self.events():
            if ts > now - 30:
                mins = (ts - now) / 60   # real minutes
                lbl = f"{'Scored' if kind == 'scored' else 'Practice'} round {k}"
                return f"{lbl} at {hhmm(ts)} ({'now' if mins < 0.5 else f'in {mins:.0f} min'})"
        return "No schedule set" if not self.events() else "Event finished"

    async def send_reminders(self, key: str):
        """Re-send the standing reminders tied to this clock mark (see REMINDERS)."""
        part = key.split(":", 1)[1]
        trig = ("T" + part.split("-")[-1]) if part.startswith("s") else part if part.startswith("b") else \
            ("every10" if part.startswith("p") and int(part[1:] or 0) % 2 == 0 else "")
        for t, who, target, text, wake in REMINDERS:
            if t != trig or who not in ("both", self.hub.person):
                continue
            for a in reminder_targets(self.hub, target):
                if a.state == "stopped" and not wake:
                    continue
                await a.add_item({"kind": "hub", "wake": wake, "text": "[standing reminder] " + text})
                if wake and a.state == "stopped" and not a.paused:
                    await a.start()

    async def loop(self):
        while True:
            for job in (self.tick, self.hub.expire_decisions, self.guard.tick, self.hub.watch_stalls,
                        self.hub.watch_unanswered):
                try:
                    await asyncio.wait_for(job(), 120)
                except Exception as e:  # noqa: BLE001   one failing job must not switch off the others
                    self.hub.note_error(f"clock/{getattr(job, '__name__', 'job')}", e)
            await asyncio.sleep(10)

    async def tick(self):
        now = time.time()
        ov = self.hub.overseer()
        me = self.hub.person
        s = self.hub.bus.shared.get("schedule")
        if s and getattr(self, "last_sched", None) and self.last_sched != s:
            self.carry(self.last_sched, s)
        self.last_sched = dict(s) if s else None
        marks = []
        if s:
            t0, U = s["start"], 60 * s.get("scale", 1.0)
            tk = int(t0)
            for mi, who, w in BUILD:
                if who in ("both", me) or dispatch_text(f"b{mi}", me) or has_reminder(f"b{mi}", me):
                    mine = who in ("both", me) or dispatch_text(f"b{mi}", me)
                    marks.append((f"{tk}:b{mi}", build_ts(s, mi), (f"Build hour, minute {mi}: {w}" + dispatch_text(f"b{mi}", me))
                                  if mine else "[reminders-only]"))
            seen_ = self.hub.bus.shared.get("rounds_seen")
            for k, ts in enumerate(round_starts(s), 1):
                if k > 1 and isinstance(seen_, dict) and seen_ and f"Round {k - 1}" not in seen_ and \
                        now > round_ts(s, k - 1) + 3 * U:
                    continue   # round k-1 is late on the portal: this window's steps wait for it (the clock follows the pin)
                for o, who, w in WINDOW:
                    if (who in ("both", me) or dispatch_text(f"T{o}", me) or has_reminder(f"T{o}", me)) and not (k == 1 and o > 9):   # round 1: the build hour covers T-20..T-9
                        mine = who in ("both", me) or dispatch_text(f"T{o}", me)
                        marks.append((f"{tk}:s{k}-{o}", ts - o * U, (f"Scored round {k} at {hhmm(ts)}, T-{o}: {w}" + dispatch_text(f"T{o}", me))
                                      if mine else "[reminders-only]"))
        if s:   # a regular check-in every 5 event-minutes from minute 0 to the end of the last round
            t0, U = s["start"], 60 * s.get("scale", 1.0)
            end = round_starts(s)[-1] + 10 * U
            n = int((now - t0) // (5 * U))
            if t0 <= now < end:
                marks.append((f"{int(t0)}:p{n}", t0 + n * 5 * U, "Regular clock check. Re-read the situation brief: is "
                              "everything for the current and next step on track? Nudge your workers or tell your human if not; "
                              "if all is on track, just update set_status (no messages needed)."))
        for key, at, text in marks:
            U_ = 60 * (s or {}).get("scale", 1.0)
            grace = max(60, 2 * U_)
            if not key.split(":", 1)[1].startswith("p"):   # a step missed during a hub restart still fires, marked late
                grace = max(grace, min(300, 5 * U_))
            if key.endswith(("-13", "-8", "-3")):
                grace = max(grace, 300)   # decision steps: always within 5 minutes
            if key.split(":", 1)[1] in ("b0", "b10", "b15") and s:
                grace = max(grace, round_starts(s)[0] - at)   # minute 0 typed late, a link down, a laptop asleep: still fires
            if key not in self.sent and at <= now < at + grace:
                if at < self.started_at and now - at > 90 and text != "[reminders-only]":
                    text = f"(LATE: this step was due at {hhmm(at)}, while the hub was restarting) " + text
                self.sent.add(key)
                atomic_write(self.hub.data / "clock_sent.json", json.dumps(sorted(self.sent)))
                if text == "[reminders-only]":
                    await self.send_reminders(key)
                    continue
                if key.endswith(":b0"):
                    await self.hub.build_notes(int(key.split(":")[0]))
                part = key.split(":", 1)[1]
                dkey = ("T" + part.split("-")[-1]) if part.startswith("s") else part
                for ag_name, pr, task in worker_tasks(dkey, me):   # straight to the worker who does it
                    ag = self.hub.agents.get(ag_name)
                    if ag is None:
                        continue
                    await ag.add_item({"kind": "clock", "wake": True, "urgent": pr == "crit" and key.endswith(("-13", "-8")),
                                       "text": f"[clock: {text.split(':', 1)[0]}] Your task now ({'CRITICAL' if pr == 'crit' else 'optional: only if on track'}): "
                                               f"{task}\nWhen it's a main deliverable, report_progress(item, 'in progress') now and 'done' when finished."})
                    if ag.state == "stopped" and not ag.paused:
                        await ag.start()
                await ov.add_item({"kind": "clock", "wake": not part.startswith("p"), "text": text,
                                   "urgent": key.endswith(("-13", "-8", "-3"))})
                await self.send_reminders(key)
                if ov.state == "stopped" and not ov.paused:
                    await ov.start()
                human = HUMAN_STEPS.get(key.split(":", 1)[1].split("-")[-1] if ":s" in key else key.split(":", 1)[1], {}).get(me)
                if human == "UPLOAD":   # upload reminders follow the actual state, never a fixed plan
                    live = (self.hub.bus.shared.get("live") or {}).get("filename")
                    act = (self.hub.bus.shared.get("portal_active") or {}).get("filename")
                    human = (f"Upload **{live}** now (Live menu → download) and make it active; the portal is running "
                             f"{act or 'nothing'}." if live and norm_bot(live) != norm_bot(act) else None)
                if human:   # a step a person must do: remind them directly
                    await self.hub.add_alert(f"{me[0]}-clock", text.split(": ", 1)[0] + ": " + human,
                                             urgent=key.endswith(("-8", "-3")))
        if s:
            await self.hub.close_build_notes(s)
            self.tidy_bell(s)
        if s:   # the clock may have been set on the other laptop: clear "need minute 0" notices here too
            for al in list(self.hub.alerts):
                if re.search(r"minute 0|set the clock|no clock", al["text"], re.I):
                    self.hub.dismiss(al["id"])
        self.hub.set_service(f"{me[0]}-clock", "Clock", "working" if s else "idle", self.next_text())


# ======================================================================== deadline guard
# Cut-offs that change WHAT we do when a step runs late, never HOW CAREFULLY. At the regional, countdown reminders
# made agents rush and ship untested bots; here a late step loses its slot and the safe default plays (the live
# bot, active again since T-9), so nobody gains by hurrying. Workers get no countdowns from this: before a cut-off
# only the Overseer hears (to re-scope); at the cut-off the owner is stopped and told the fallback. Every rule is
# known in advance (the "Cut-offs" table in DECISION_RULES.md).
# (id, person, cut-off in event-minutes before the scored round, heads-up at, owner, what, fallback)
GUARD = [
    ("data", "samuel", 10, None, "s-portal", "the previous scored round's results and hands have landed",
     "No new data this window. The live bot plays with only changes already supported by earlier rounds (persistent "
     "leaks, validated items); s-data works from pooled earlier rounds; nothing waits for this data. When it lands it "
     "feeds the next window."),
    ("card", "samuel", 8, None, "s-data", "the round card is written (within 3 event-minutes of the data landing)",
     "Stop fixing the card script. s-data computes the numbers the decision needs (the challenger's practice score vs "
     "the live bot's last comparable round, the top leak's size and z) with a one-off script, 3-minute cap; "
     "s-data fixes the script after T-3 for the next window."),
    ("change", "samuel", 8, 10, "s-data", "this window's one-change proposal is recorded (question 'one-change ...')",
     "No change from this window's new data goes into the live bot. Record what you have as a hypothesis with the "
     "same question key; it goes to the challenger or the next practice round to be measured. The live bot plays "
     "with changes that were already validated."),
    ("challenger", "dylan", 12, 14, "d-challenger", "a new challenger is released (a ready vN since the window opened)",
     "Keep building at normal care; don't pack it in a hurry. The practice round plays the most informative bot "
     "already released and upload-tested (else the live bot). The challenger's next slot is the next window's T-12."),
    ("note", "dylan", 7, None, "d-overview", "the 'Which bot?' note for this round is posted",
     "The clock posted the note itself with the live bot as the default; the pre-registered rule still applies if "
     "d-overview adds the numbers before T-5."),
    ("chosen", "dylan", 4, 6, "d-platform", "the bot chosen at T-8 is released and upload-tested",
     "The chosen bot doesn't play this round: the live bot (active since T-9) plays and nothing is uploaded. Stop "
     "packing it for this round; it plays the next practice round instead."),
]


def norm_stage(t: str) -> str:
    """'Practice-1', 'practice 1', 'round2.5', 'R2' -> the hub's stage names ('Practice 1', 'Round 2.5')."""
    m = re.search(r"(practice|round|r)\W*(\d+(?:\.5)?)", t or "", re.I)
    if not m:
        return (t or "").strip()
    return ("Practice " if m.group(1).lower() == "practice" else "Round ") + m.group(2)


def stage_slug(stage: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", stage)


class DeadlineGuard:
    def __init__(self, hub: "Hub"):
        self.hub = hub
        self.done: set[str] = set(load_json(hub.data / "guard_done.json", []))
        self.log: list = load_json(hub.data / "guard_log.json", [])

    def mark(self, key: str):
        self.done.add(key)
        atomic_write(self.hub.data / "guard_done.json", json.dumps(sorted(self.done)))

    def met(self, gid: str, k: int, start: float, U: float) -> bool | None:
        """True: done. False: not done. None: not due (nothing to check yet). Observable state only, never an agent's say-so."""
        hub, prev = self.hub, f"Round {k - 1}"
        if gid == "data":
            return hub.landed_at.get(prev, 0) > start - 2 * U
        if gid == "card":
            landed = hub.landed_at.get(prev, 0)
            if landed <= start - 2 * U:
                return None   # no data, no card due ("data" covers it)
            roots = [hub.repo / "analysis"] + [Path(getattr(a, "cwd", hub.repo)) / "analysis" for a in hub.agents.values() if getattr(a, "cwd", hub.repo) != hub.repo]
            for root in roots:   # agents name the folder their own way (Round-1, round1, r1...): any card counts
                try:
                    if any(f.stat().st_mtime > landed - 60 and "fp" not in f.parts and "fp" not in f.name.lower()
                           for f in root.rglob("*card*.md")):
                        return True
                except OSError:
                    pass
            if any("card" in (x.get("tags") or []) and x.get("at", 0) > landed - 60 for x in hub.ledger()):
                return True
            return None if time.time() < landed + 3 * U else False
        if gid == "change":
            return any(str(x.get("question", "")).lower().startswith("one-change") and x.get("at", 0) > start
                       for x in hub.ledger())
        if gid == "challenger":
            return any(b.get("status") == "ready" and (b.get("updated") or b.get("at") or 0) > start - 2 * U for b in hub.bots())
        if gid == "note":
            return any(p.get("kind") == "bot" and p.get("created", 0) > start for p in hub.props())
        if gid == "chosen":
            live = hub.bus.shared.get("live") or {}
            if not live or live.get("at", 0) <= start:
                return True   # nothing new chosen this window: the live bot plays as it is
            if norm_bot((hub.bus.shared.get("portal_active") or {}).get("filename")) == norm_bot(live.get("filename")):
                return True   # already uploaded and active: nothing to cut
            b = hub.bus.shared.get("bot:" + norm_bot(live.get("filename") or "")) or {}
            return b.get("status") == "ready" and bool(hub.find_bot_file(live.get("file") or live.get("filename") or "")
                                                                 or b.get("sha256"))
        return True

    def windows(self):
        s = self.hub.bus.shared.get("schedule")
        if not s:
            return []
        t0, U = s["start"], 60 * s.get("scale", 1.0)
        return [(k, ts, U) for k, ts in enumerate(round_starts(s), 1)]   # round 1: only the decision and the chosen bot

    async def tick(self):
        hub, now = self.hub, time.time()
        for k, ts, U in self.windows():
            start = ts - (10 * U if k == 1 else min(20 * U, ts - round_ts(self.hub.bus.shared.get("schedule"), k - 1)))
            if not (start <= now < ts):
                continue
            rid = f"{int(self.hub.bus.shared['schedule']['start'])}:r{k}"
            seen = hub.bus.shared.get("rounds_seen")
            if k > 1 and isinstance(seen, dict) and seen and f"Round {k - 1}" not in seen and \
                    now > round_ts(hub.bus.shared.get("schedule"), k - 1) + 3 * U:
                if f"{rid}:late" not in self.done:   # the portal hasn't started round k-1: it's late, not us
                    self.mark(f"{rid}:late")
                    await hub.alert_all(f"{hub.person[0]}-clock", f"Scored round {k - 1} hasn't started on the portal "
                                        f"(expected {hhmm(round_ts(hub.bus.shared.get('schedule'), k - 1))}). Deadlines for "
                                        "the next window wait; the clock moves when the portal starts it, or tell your Chat "
                                        "the new time.", False)
                continue
            for gid, who, cut, warn, owner, what, fallback in GUARD:
                key = f"{rid}:{gid}"
                if who != hub.person or key in self.done or (k == 1 and gid not in ("note", "chosen")):
                    continue
                if gid == "card" and f"{rid}:data:cut" in self.done:
                    continue
                m = self.met(gid, k, start, U)
                if m:
                    self.mark(key)
                    continue
                if m is False and (gid == "card" or now >= ts - cut * U):
                    self.mark(key)
                    self.mark(key + ":cut")
                    await self.cut(k, gid, owner, what, fallback, ts, U)
                    continue
                if m is None:
                    continue
                ag = hub.agents.get(owner)
                late_eta = ag is not None and ag.eta and now < ag.eta and ag.eta > ts - cut * U
                if (warn and now >= ts - warn * U or late_eta) and key + ":warn" not in self.done:
                    self.mark(key + ":warn")
                    await self.heads_up(k, owner, what, cut, fallback, ag, ts, U)

    async def heads_up(self, k, owner, what, cut, fallback, ag, ts, U):
        """Before a cut-off only the Overseer hears, so it can re-scope; the worker is never told to hurry."""
        eta = (f"{owner} expects to finish at {hhmm(ag.eta)}" if ag is not None and ag.eta else f"{owner} hasn't given an ETA")
        await self.hub.overseer().add_item({"kind": "hub", "wake": True, "text": (
            f"[deadline guard] Scored round {k}: '{what}' isn't done; its cut-off is T-{cut} ({hhmm(ts - cut * U)}). {eta}. "
            f"If it matters this window, re-scope now: cut it to the smallest useful version, or give {owner} a helper. Do NOT "
            f"tell anyone to hurry or skip a test. If it misses, this fallback plays, and it is fine: {fallback}")})
        self.note(k, "heads-up", owner, what)

    async def cut(self, k, gid, owner, what, fallback, ts, U):
        hub = self.hub
        msg = (f"[deadline guard] Cut-off passed for scored round {k}: '{what}' didn't happen in time. The plan changes "
               f"(the pre-registered fallback, not a request to go faster): {fallback}")
        ag = hub.agents.get(owner)
        if ag is not None and gid != "challenger":   # stop the late work for this round; the challenger keeps going
            await ag.add_item({"kind": "hub", "wake": True, "urgent": True, "text": msg + " Stop that work for this round "
                               "now, record what you have (ledger: hypothesis, or result if measured), set_status with "
                               "what's left, then take your next task."})
        elif ag is not None:
            await ag.add_item({"kind": "hub", "wake": False, "text": msg})
        await hub.overseer().add_item({"kind": "hub", "wake": True, "urgent": True, "text": msg + " Re-plan the rest of "
                                       "this window around it; report the cause at the next T-20 sync so it doesn't repeat."})
        posted = await self.post_default_note(k, ts, U) if gid == "note" else None
        if gid == "chosen":
            await self.revert_live(k)
        human = {"challenger": "no challenger this window. Leave the live bot active for the practice round (or the "
                               "released bot your Overseer names).",
                 "chosen": "the chosen bot wasn't ready by T-4. **Upload nothing**: the live bot already active plays.",
                 "data": "round data hadn't landed by T-10. The live bot plays with already-validated changes only.",
                 "change": "no change from this round's data in time. The live bot plays with already-validated changes.",
                 "card": "the round-card script failed or was too slow. Data is computing the decision numbers by hand.",
                 "note": ("no 'Which bot?' note by T-7. The clock posted one with the live bot as default." if posted else
                          "no 'Which bot?' note by T-7 and no live bot is declared: the bot active on the portal plays.")}[gid]
        await hub.alert_all(f"{hub.person[0]}-clock", f"Before scored round {k}: {human}", urgent=gid in ("chosen", "challenger"))
        self.note(k, "cut", owner, what)

    def note(self, k, kind, owner, what):
        self.log = (self.log + [{"at": time.time(), "round": k, "kind": kind, "owner": owner, "what": what}])[-200:]
        atomic_write(self.hub.data / "guard_log.json", json.dumps(self.log))
        cuts = [x for x in self.log if x["kind"] == "cut"]
        self.hub.set_service(f"{self.hub.person[0]}-guard", "Deadlines", "working",
                             f"Round {k}: {'missed' if kind == 'cut' else 'at risk'}: {what}",
                             "### Cut-offs missed\n" + ("\n".join(f"- Round {x['round']}: {x['what']} ({x['owner']})"
                                                                   for x in cuts) or "none"))

    async def post_default_note(self, k, ts, U):
        hub = self.hub
        live = hub.bus.shared.get("live") or {}
        f = live.get("file") or (("releases/" + live["filename"]) if live.get("filename") else "")
        if not f:
            return False
        live = dict(live, file=f)
        p = {"id": "P" + new_id()[1:7].upper(), "kind": "bot", "title": f"Which bot plays scored round {k}?",
             "headline": f"Default: the live bot {bot_name(live['filename'])} keeps playing.",
             "body": "Asked by the clock because nobody had asked it by T-7. The live bot plays unless the pre-registered "
                     "rule (How we decide §3) picks a challenger that's released and upload-tested; Dylan's Chat is asked to "
                     "fill in both bots' numbers and the rule's answer. Answer in the Chat in words (e.g. 'keep the live bot' "
                     "or 'use v7'); with no answer by T-5 the rule's answer plays.",
             "bot": live["file"], "rule_answer": live["file"], "author": "d-overview", "author_person": hub.person, "decider": "both",
             "owner": "d-overview", "parent": None, "stage": stage_of(hub.bus.shared.get("schedule"), time.time()),
             "status": "needs_call", "created": time.time(), "deadline": ts - 5 * U, "thread": []}
        await hub.save_prop(p)
        await hub.tile("decide-" + p["id"], "Bot choice: " + bot_name(f), "waiting for your answer", owner="d-overview")
        return True

    async def revert_live(self, k):
        hub = self.hub
        live = hub.bus.shared.get("live") or {}
        prev = live.get("prev")
        if norm_bot((hub.bus.shared.get("portal_active") or {}).get("filename")) == norm_bot(live.get("filename")):
            return   # the portal already runs the chosen bot: leave it
        if prev and (prev.get("file") or prev.get("filename")):
            prev = dict(prev, file=prev.get("file") or prev.get("filename"))
            await hub.make_live(prev["file"], "deadline guard", note=f"{live.get('filename')} wasn't ready by T-4 of round "
                                f"{k}; {prev.get('filename')} stays live", tell=False)

# ======================================================================== portal watcher
class PortalWatcher:
    """Read-only: polls the organizers' portal (or the rehearsal copy), saves results and our hand data,
    and wakes the agents that need them. Same API paths as the real site."""

    UA = "avalon-portal-watcher/1.0"

    def __init__(self, hub: Hub, base: str, keyfile: Path, hands_url: str | None, out: Path | None = None,
                 small_only: bool = False):
        self.hub, self.base = hub, base.rstrip("/")
        self.key = keyfile.expanduser().read_text().strip()
        # {tid} = round id, {q} = "?subset=first-1000" for the small file and "" for the full one
        self.hands_url = hands_url or (self.base + "/tournaments/{tid}/hands{q}")
        self.out = (out or Path.home() / "portal-data").expanduser()
        self.out.mkdir(parents=True, exist_ok=True)
        self.st = load_json(hub.data / "portal_state.json", {"done": [], "subs": [], "standings": None})
        self.st.setdefault("need_hands", {})   # round id -> folder, until its hand files are saved
        hub.landed_at.update(self.st.get("landed_at", {}))   # the deadline guard must not think data never landed
        self.fails = 0
        self.small_only = small_only   # on a phone hotspot: only the first-1000 file, to save data
        self.team = self.cid = None
        self.want_cid = os.environ.get("AVALON_COMPETITION_ID") or None
        self.comp_name, self.team_name = "", "avalon"
        self.checked: set[str] = set(self.st.get("checked", []))
        if not hands_url and self.st.get("hands_url"):
            self.hands_url = self.st["hands_url"]   # given in the Chat earlier: survives a restart

    def set_hands_url(self, url: str) -> str:
        """The hand-history link Samuel copied from the portal: the round's id becomes {tid}; retried at once."""
        url = url.strip().strip("<>").rstrip(".,)")
        if "{tid}" not in url:
            ids = sorted({x for d in (self.st.get("done", []), list(self.st.get("need_hands", {}))) for x in d}, key=len, reverse=True)
            hit = next((i for i in ids if i and i in url), None)
            if not hit:
                m = re.search(r"/(?:tournaments|rounds?)/([^/?#]+)", url)
                hit = m.group(1) if m else None
            if not hit:
                return "I couldn't find the round's id in that link. Paste the link for a round's hand download as copied."
            url = url.replace(hit, "{tid}")
        if "{q}" not in url:
            from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
            u = urlsplit(url)
            rest = [(k_, v_) for k_, v_ in parse_qsl(u.query, keep_blank_values=True) if k_ != "subset"]
            if rest:   # other parameters (a signature) stay; the small file adds &subset=... (handled in fetch_hands)
                url = urlunsplit(u._replace(query=urlencode(rest))) + "{qa}"
            else:
                url = urlunsplit(u._replace(query="")) + "{q}"
        self.hands_url = self.st["hands_url"] = url
        for info in self.st.get("need_hands", {}).values():
            info["since"] = time.time()
            info.pop("pinged", None)
            info.pop("warned", None)
        self.save()
        asyncio.create_task(self.retry_hands())
        return f"Hand-history link set: {url}. Retrying the missing downloads now; it's kept across restarts."

    def save(self):
        self.st["checked"] = sorted(self.checked)
        atomic_write(self.hub.data / "portal_state.json", json.dumps(self.st))

    def get(self, path, raw=False):
        req = urllib.request.Request(path if path.startswith("http") else self.base + path,
                                     headers={"Authorization": f"Bearer {self.key}", "User-Agent": self.UA})
        with urllib.request.urlopen(req, timeout=60 if raw else 20) as r:
            data = r.read()
        return data if raw else json.loads(data)

    async def aget(self, path, raw=False):
        return await asyncio.to_thread(self.get, path, raw)

    FAST, SLOW = 6, 30   # seconds between checks: around the moment a round should finish / the rest of the time

    def finishing(self) -> bool:
        """True while a round the clock knows about should be finishing: from 2 to 15 event-minutes after it starts,
        until its result has landed."""
        sch = self.hub.bus.shared.get("schedule")
        if not sch:
            return False
        now, U = time.time(), 60 * sch.get("scale", 1.0)
        landed = set(self.st.get("done_stages", []))
        return any(ts + 2 * U <= now < ts + 15 * U and stage_of_round(kind, k) not in landed
                   for kind, k, ts in self.hub.clock.events())

    async def round_ids(self) -> tuple:
        """The light check: just the round list (which rounds exist, which have finished)."""
        rounds = (await self.aget(f"/competitions/{self.cid}/tournaments"))["items"]
        return tuple(sorted((r["id"], bool(r.get("completed_at"))) for r in rounds))

    async def loop(self):
        last_full, seen = 0.0, None
        while True:
            try:
                fast = self.finishing()
                live = self.hub.bus.shared.get("live") or {}
                pending = bool(live.get("filename")) and norm_bot(live.get("filename")) != norm_bot(
                    (self.hub.bus.shared.get("portal_active") or {}).get("filename")) and time.time() - live.get("at", 0) < 1800
                if not fast or pending or time.time() - last_full >= self.SLOW or seen is None:
                    await self.poll()          # the full check: rounds, results, standings, the active bot
                    last_full = time.time()
                    seen = await self.round_ids() if fast else None
                else:   # in the fast window, a 6 s check reads only the round list; a change triggers the full check
                    now_ids = await self.round_ids()
                    if now_ids != seen:
                        await self.poll()
                        last_full, seen = time.time(), now_ids
                self.fails = 0
            except Exception as e:  # noqa: BLE001
                self.fails += 1
                self.hub.set_service("s-portal", "Portal", "error", f"Portal not answering ({type(e).__name__}); retrying")
                if self.fails == 3:
                    await self.hub.add_alert("s-portal", "The portal has not answered for 3 checks in a row.", True)
            live = self.hub.bus.shared.get("live") or {}
            act = self.hub.bus.shared.get("portal_active") or {}
            uploading = bool(live.get("filename")) and norm_bot(live.get("filename")) != norm_bot(act.get("filename")) \
                and time.time() - live.get("at", 0) < 1800   # Dylan is uploading the live bot: confirm it fast
            await asyncio.sleep(self.FAST if self.finishing() else 10 if uploading else self.SLOW)

    async def identify(self):
        """Our team and competition. The real portal answers /auth/api-key for API keys (/me is browser-only)."""
        teams = []
        for path in ("/auth/api-key", "/me"):
            try:
                d = await self.aget(path)
                teams = [{"id": t.get("team_id") or t.get("id"), "competition_id": t.get("competition_id")}
                         for t in (d.get("teams") or [])]
                if teams:
                    break
            except Exception:  # noqa: BLE001
                continue
        if self.want_cid:
            teams = [t for t in teams if t["competition_id"] == self.want_cid] or teams
        if not teams:
            raise RuntimeError("the key lists no team")
        if len(teams) > 1 and not self.want_cid:   # e.g. Bay Area and Finals: take the newest competition
            comps = {c["id"]: c for c in (await self.aget("/competitions")).get("items", [])}
            teams.sort(key=lambda t: str(comps.get(t["competition_id"], {}).get("created_at") or comps.get(t["competition_id"], {}).get("starts_at") or ""))
        t = teams[-1]
        self.team, self.cid = t["id"], t["competition_id"]
        comp = await self.aget(f"/competitions/{self.cid}")
        self.comp_name = comp.get("name", self.cid)
        self.team_name = (await self.aget(f"/teams/{self.team}")).get("name", "avalon")

    async def poll(self) -> bool:
        if not self.cid:
            await self.identify()
        rounds = [r for r in (await self.aget(f"/competitions/{self.cid}/tournaments"))["items"]
                  if not r.get("cancelled_at") and r.get("status") not in ("cancelled", "canceled")]
        counts: dict[str, int] = {}
        for r in sorted(rounds, key=lambda r: r["created_at"]):   # the real portal has no labels: name them
            if r["kind"] != "practice":   # "scored", "final", ...: one counter, so a "final" round isn't round 1
                r["kind"] = "scored"
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
            r.setdefault("label", f"{'Scored' if r['kind'] != 'practice' else 'Practice'} round {counts[r['kind']]}"
                                  + (f" (x{r['weight']})" if r.get("weight") else ""))
            r["_n"] = counts[r["kind"]]
            if r["kind"] == "practice":   # "Practice n" in the build; "Round k.5" after scored round k
                ks = counts.get("scored", 0)
                r["stage"] = f"Practice {counts['practice']}" if ks == 0 else f"Round {ks}.5"
                r["_n"] = counts["practice"] if ks == 0 else 4 + ks
            else:
                r["stage"] = stage_of_round(r["kind"], counts[r["kind"]])
        await self.check_clock(rounds)
        await self.check_silent(rounds)
        new_done = [r for r in rounds if r.get("completed_at") and r["id"] not in self.st["done"]]
        if not self.st.get("baseline_done"):
            self.st["baseline_done"] = True
            if new_done:   # rounds that finished before this hub started: one catch-up note, not N "new" rounds
                for r in sorted(new_done, key=lambda r: r["created_at"]):
                    await self.landed(r, quiet=True)
                ov = self.hub.agents.get("s-overview")
                if ov:
                    await ov.add_item({"kind": "portal", "wake": True, "text": (
                        f"Catch-up: {len(new_done)} round(s) had already finished before I started; their results and our "
                        f"hand data are saved under {self.out}/ (one folder per round). These are NOT new rounds; check "
                        "PLAN-samuel.md / data/RATES.md for what has already been analysed before assigning work.")})
                new_done = []
        for r in sorted(new_done, key=lambda r: r["created_at"]):
            try:
                await self.landed(r)
                self.st.get("land_fail", {}).pop(r["id"], None)
            except Exception as e:  # noqa: BLE001   results not ready yet, a timeout: try again next poll
                fails = self.st.setdefault("land_fail", {})
                fails[r["id"]] = fails.get(r["id"], 0) + 1
                if fails[r["id"]] == 3:
                    await self.hub.alert_all("s-portal", f"Can't read the result of {r.get('label', r['id'])} yet "
                                             f"({type(e).__name__}); still retrying every poll. Check the portal page.", True)
                if fails[r["id"]] >= 15:   # ~10+ minutes of failures: stop, say so
                    self.st["done"].append(r["id"])
                    await self.hub.alert_all("s-portal", f"Gave up reading the result of {r.get('label', r['id'])} after "
                                             f"15 tries ({type(e).__name__}: {e}). Download it from the portal and drop it "
                                             "into the Chat.", True)
                self.save()
        await self.retry_hands()
        try:   # a held leaderboard must never stop the active-bot checks below
            standings = (await self.aget(f"/competitions/{self.cid}/standings"))["items"]
            self.st["standings"], self.st["standings_held"] = standings, False
        except Exception as e:  # noqa: BLE001
            standings = self.st.get("standings") or []
            if not self.st.get("standings_held"):
                self.st["standings_held"] = True
                await self.hub.alert_all("s-portal", f"The standings can't be read ({type(e).__name__}): the leaderboard may be "
                                         "held. Active-bot checks continue. Until it's back, How we decide treats us as outside "
                                         "the top 3 unless we were clearly in it; the Chats work out our total from each round's "
                                         "results x weights.", False, chat=True)
        await self.watch_competition()
        team = await self.aget(f"/teams/{self.team}")
        subs = await self.aget(f"/teams/{self.team}/submissions")
        team["submissions"] = subs.get("items", subs) if isinstance(subs, dict) else subs
        act = next((x for x in team["submissions"] if x["id"] == team.get("active_submission_id")), None)
        team["active_filename"] = team.get("active_filename") or (act or {}).get("filename")
        cur = {"filename": team["active_filename"], "sha256": (act or {}).get("sha256") or "", "at": time.time()}
        prev = self.hub.bus.shared.get("portal_active") or {}
        if prev.get("filename") != cur["filename"] or time.time() - prev.get("at", 0) > 45:
            await self.hub.bus.set_shared("portal_active", cur)   # both laptops' briefs show the active bot
        await self.check_team(team)
        for r_ in getattr(self, "new_started", []):
            await self.start_check(r_)
        self.new_started = []
        rs_ = dict(self.hub.bus.shared.get("rounds_seen") or {})
        miss = {r["stage"]: time.time() for r in rounds if r["kind"] == "scored" and r["stage"] not in rs_}
        if miss:   # a round that ran while this hub was down still counts as started
            await self.hub.bus.set_shared("rounds_seen", dict(rs_, **miss))
        pb = self.st.setdefault("played_by", {})
        for r in rounds:   # a round that is playing: "<stage> · playing vN" (the bot active when it was first seen)
            if not r.get("completed_at"):
                if r["id"] not in pb:
                    pb[r["id"]] = cur["filename"] or "no bot"
                    if r["kind"] == "practice":   # tell the Chats while it's playing: its result is that bot's number
                        rs = self.hub.bus.shared.get("rounds_seen") or {}
                        if r["stage"] not in rs:
                            await self.hub.bus.set_shared("rounds_seen", dict(rs, **{r["stage"]: time.time()}))
                f = pb[r["id"]]
                await self.hub.tile("round-" + stage_slug(r["stage"]), r["stage"], f"playing {bot_name(f)}", owner="d-overview", stage=r["stage"])
                continue
                await self.hub.ensure_note("L-" + r["id"][:12], kind="live", stage=r["stage"], owner="d-overview",
                                           author="s-portal", author_person="dylan",
                                           title=f"{bot_name(f)} live · {r['stage']}",
                                           headline=f"{bot_name(f)} is playing {r['stage']}.",
                                           thread=[{"who": "Portal", "at": time.time(), "action": "update",
                                                    "text": f"{r['stage']} started; {f} is the active bot on the portal."}])
        self.save()
        ours = next((x for x in standings if x["team_name"] == self.team_name), None)
        third = (standings[2].get("total") or 0) if len(standings) >= 3 else None
        summary = "### Standings\n| # | Team | Total |\n|---|---|---|\n" + "\n".join(
            f"| {x.get('rank')} | {'**' + x['team_name'] + '**' if x['team_name'] == self.team_name else x['team_name']} | {(x.get('total') or 0):.2f} |"
            for x in standings[:10])
        summary += f"\n\nActive bot: {team.get('active_filename') or 'none'} · competition: {self.comp_name}"
        running = [r for r in rounds if not r.get("completed_at")]
        task = (f"We're {ours.get('rank')} ({(ours.get('total') or 0):.1f}; 3rd has {third:.1f})" if ours and third is not None else
                f"{len(rounds)} rounds seen") + (f" · {len(running)} running" if running else "")
        self.hub.set_service("s-portal", "Portal", "working", task, summary)
        return bool(running) or bool(self.st.get("land_fail")) or bool(self.st.get("need_hands"))

    async def check_silent(self, rounds: list):
        """No round seen on the portal 8 event-minutes after one should have started: the competition id, the key or
        the schedule is wrong. Say so once per expected round."""
        sch = self.hub.bus.shared.get("schedule")
        if not sch:
            return
        U, now = 60 * sch.get("scale", 1.0), time.time()
        started = [r for r in rounds if r.get("created_at")]
        for kind, k, ts in self.hub.clock.events():
            key = f"silent:{kind}{k}"
            if ts + 8 * U < now < ts + 20 * U and key not in self.checked:
                n_kind = sum(1 for r in started if r["kind"] == kind)
                need = k if kind == "scored" else min(k, 4) if k <= 4 else None
                if need and n_kind < need:
                    self.checked.add(key)
                    await self.hub.alert_all("s-portal", f"{'Scored' if kind == 'scored' else 'Practice'} round {k} should have "
                                             f"started at {hhmm(ts)}, but the portal ({self.comp_name or self.cid}) shows "
                                             f"{n_kind} {kind} round(s). Is the clock right, or the competition (AVALON_COMPETITION_ID)?",
                                             True, chat=True)

    async def check_clock(self, rounds: list):
        """The portal shows when rounds really start. If the hub's clock is off by minutes (minute 0 set late, or a
        stray 'it starts now'), every step and stage label is off too: say so in both Chats, with the fix."""
        sch = self.hub.bus.shared.get("schedule")
        if not sch:
            return
        seen = self.st.setdefault("seen_start", {})
        exp = {(kind, k): ts for kind, k, ts in self.hub.clock.events()}
        U = 60 * sch.get("scale", 1.0)
        for r in rounds:
            if r.get("completed_at") or r["id"] in seen:
                continue
            seen[r["id"]] = time.time()   # first seen running (polls are <= 60 s apart)
            try:   # the portal's own creation time, when it's earlier (a round that started while this hub was down)
                ca = datetime.fromisoformat(str(r.get("created_at")).replace("Z", "+00:00")).timestamp()
                if seen[r["id"]] - 600 < ca < seen[r["id"]]:
                    seen[r["id"]] = ca
            except (ValueError, TypeError):
                pass
            key = ("practice" if r["kind"] == "practice" else "scored", r.get("_n"))
            if key not in exp:
                continue
            drift = seen[r["id"]] - exp[key]
            if key[0] == "scored":
                self.new_started = getattr(self, "new_started", []) + [r]   # checked after the active bot is refreshed
            if key[0] == "scored" and max(90, 3 * U) < abs(drift) < 45 * U:   # its real start: every later deadline follows it
                await self.hub.clock.pin_round(key[1], seen[r["id"]], "seen on the portal")
                continue
            last = self.st.get("drift_alerted")
            if abs(drift) > max(180, 6 * U) and (last is None or abs(drift - last) > 120):
                self.st["drift_alerted"] = drift
                t0 = sch["start"] + drift
                await self.hub.alert_all("s-portal", (
                    f"The clock looks off by about {abs(drift) / 60:.0f} min: the portal started {r['stage']} at "
                    f"{hhmm(seen[r['id']])}, but the clock expected it at {hhmm(exp[key])}. If the portal is right, minute 0 "
                    f"was {time.strftime('%H:%M:%S', time.localtime(t0))}: tell your Chat \"minute 0 was "
                    f"{time.strftime('%H:%M:%S', time.localtime(t0))}\" (every step and deadline moves with it)."), True, chat=True)
        self.save()

    async def start_check(self, r):
        """A scored round just started: is it playing the bot we decided on? (The last chance to know before results.)"""
        rs = self.hub.bus.shared.get("rounds_seen") or {}
        if r["stage"] not in rs:
            await self.hub.bus.set_shared("rounds_seen", dict(rs, **{r["stage"]: time.time()}))
        live = (self.hub.bus.shared.get("live") or {}).get("filename")
        act = (self.hub.bus.shared.get("portal_active") or {}).get("filename")
        if live and act and not same_bot(live, act):
            await self.hub.alert_all("s-portal", f"{r['stage']} has started with {act} active, but the decided bot is {live}. "
                                     "It plays the whole round with " + bot_name(act) + "; tell your Chat if that was intended "
                                     "(the next window starts from the bot that really played).", True, chat=True)

    async def landed(self, r, quiet: bool = False):
        """A round finished. Order matters: tell the agents first (seconds), then run the card and fingerprinting in the
        background. Raises if the results can't be read; poll() then retries the round instead of skipping it."""
        await self.hub.tile("data-" + stage_slug(r.get("stage") or r["id"]), f"{r.get('stage') or 'Round'} data", "in progress",
                            owner="s-data", stage=r.get("stage"))
        res = await self.aget(f"/tournaments/{r['id']}/results")
        if not isinstance(res, dict) or not isinstance(res.get("items"), list):
            raise RuntimeError("results not ready")
        if not res["items"] and self.st.get("land_fail", {}).get(r["id"], 0) < 5:
            raise RuntimeError("results list empty (not ready yet?)")
        label = r.get("label") or f"{r['kind']} {r['created_at'][11:16]}"
        n = len(self.st["done"]) + 1
        folder = self.out / f"{n:02d}-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "results.json").write_text(json.dumps(res, indent=1))
        stage = r.get("stage") or label
        files = await self.fetch_hands(r["id"], folder, small_first=True)
        if not files:
            self.st["need_hands"][r["id"]] = {"folder": str(folder), "label": label, "stage": stage, "since": time.time()}
        elif not self.small_only:
            asyncio.create_task(self.fetch_hands(r["id"], folder))   # the full file, off the critical path
        self.hub.last_landed = time.time()
        items = sorted(res["items"], key=lambda x: -(x.get("average_points") or 0))
        if files:   # "data landed" means the hand file is here (the deadline guard and card cut-off read this)
            self.hub.landed_at[stage] = time.time()
            self.st.setdefault("landed_at", {})[stage] = self.hub.landed_at[stage]   # survives a restart
        aid = "A-" + r["id"][:12]
        self.st.setdefault("note_of", {})[r["id"]] = aid
        await self.hub.tile("round-" + stage_slug(stage), stage, "finished", owner="d-overview", stage=stage)
        await self.hub.tile("data-" + stage_slug(stage), f"{stage} data", "done" if files else "in progress (hands not downloadable yet)",
                            owner="s-data", stage=stage)
        if files and not quiet:
            for t in self.hub.tiles():   # an older round's analysis that never recorded a change is over now
                if t["id"].startswith("analysis-") and t["state"] == "in progress" and t["id"] != "analysis-" + stage_slug(stage):
                    await self.hub.tile(t["id"], t["label"], "done")
            await self.hub.tile("analysis-" + stage_slug(stage), f"{stage} analysis", "in progress", owner="s-data", stage=stage)
        older = sorted([p for p in self.hub.props() if p.get("kind") == "analysis" and p["id"] != aid
                        and p.get("status") in ("running", "planned", "new")], key=lambda p: p.get("created", 0))
        for p in older[:-1]:   # superseded by two newer rounds: the round's analysis is over
            await self.hub.note_append(p["id"], "Portal", "Closed: two newer rounds have landed since.", status="done")
        ours = next((i for i, x in enumerate(items, 1) if x.get("team_name") == self.team_name), None)
        me = items[ours - 1] if ours else None
        pbot = (self.st.get("played_by") or {}).get(r["id"])
        line = (f"{label} finished" + (f" (played by {bot_name(pbot)}, the bot active when it started)" if pbot else "")
                + f": we were {ours} of {len(items)} with {(me.get('average_points') or 0):.2f} "
                f"(±{me.get('margin_of_error') or 0:.2f}); 1st {items[0].get('team_name')} {(items[0].get('average_points') or 0):.2f}."
                if me else f"{label} finished (we had no result: forfeit?).")
        if me and (me.get("contender") is False or me.get("culled_at_look")):
            await self.hub.alert_all("s-portal", f"After {label} the portal marks us out of contention ({me.get('culled_at_look') or 'culled'}). "
                                     "If that's final, nothing is lost by bold play: the challenger plays from now on.", True, chat=True)
        nt_ = next((me.get(k_) for k_ in ("tables", "tables_played", "n_tables") if me and me.get(k_) is not None), None)
        if me and nt_ == 0:
            await self.hub.alert_all("s-portal", f"We played no tables in {label}: forfeit or crash? Check the active bot now.", True, chat=True)
        if pbot:
            try:
                (folder / "played_by.txt").write_text(pbot + "\n")
            except OSError:
                pass
        paths = f"\nResults: {folder}/results.json" + "".join(f"\nHands: {p}" for p in files) + \
                ("" if files else "\nHand history not downloadable yet; I'll keep trying.")
        await self.hub.note_append(aid, "Portal", line + " " + (f"Hand data downloaded ({', '.join(Path(f).name for f in files)}). "
                                   "Analysis starting." if files else "Hand data isn't downloadable yet; I'll keep trying."))
        lid = "L-" + r["id"][:12]
        for lp in [p for p in self.hub.props() if p.get("kind") == "live" and p.get("status") not in ("done", "removed")
                   and (p["id"] == lid or p.get("stage") == stage)]:
            await self.hub.note_append(lp["id"], "Portal", line, status="done")
        if quiet:
            self.st["done"].append(r["id"])
            self.st.setdefault("done_stages", []).append(stage)
            self.save()
            return
        has_card = (self.hub.repo / "analysis" / "roundcard.py").exists() and bool(files)
        pl = self.hub.agents.get("s-data")
        mid = r.get("kind") == "practice" and ".5" in stage   # a practice between scored rounds: the challenger's number
        if pl:   # standing order: numbers first, no Overseer hop (the decision window is only 5 minutes)
            if mid:
                await self.tell("d-overview", "task", f"{line} This is the practice result the 'Which bot?' rule needs: with "
                                "s-overview's numbers, set the rule's answer now (update_proposal(id, rule_answer='releases/vN.zip')).")
            await pl.add_item({"kind": "portal", "wake": True, "urgent": not mid, "note": aid, "text": (
                ("(Practice result: for the T-8 rule this is the challenger's number. Don't drop the scored round's "
                 "analysis for it; record the headline numbers when your current step is done.) " if mid else "") +
                f"DATA LANDED for {stage}. {line}{paths}\n" + (
                    "The hub is running analysis/roundcard.py on it now and sends you the output within 90 s: don't start "
                    "a second run. Meanwhile check the hand file opens. When the output arrives, check it, " if has_card else
                    "Run the round card now (analysis/roundcard.py), write "
                    f"analysis/{re.sub(r'[^A-Za-z0-9.]+', '-', stage)}/card.md, ") +
                "record the headline numbers as results, and fyi s-overview and s-tester with the path. "
                "Finish within 2 minutes.")})
            if pl.state == "stopped" and not pl.paused:
                await pl.start()
        for nm in ("s-scout", "s-tester"):   # they need the files too, whether or not the hub's scripts run
            ag_ = self.hub.agents.get(nm)
            if ag_:
                await ag_.add_item({"kind": "portal", "wake": not mid, "text": f"Data for {stage} is saved. {line}{paths}\n" + (
                    "The hub runs the fingerprint script now; the field trend and counters are yours." if nm == "s-scout" else
                    "Use it for your checks (the card's numbers, the challenger's practice number).")})
        ov = self.hub.agents.get("s-overview")
        if ov:   # the Overseer decides what to do with it and dispatches the workers with context
            await ov.add_item({"kind": "portal", "wake": True, "urgent": True, "text": "NEW ROUND RESULT. " + line + paths +
                               "\ns-data has the data (the hub runs the round card); the board shows its progress. Make "
                               "sure the window's plan runs (analysis, tests, the T-8 recommendation) and tell your human "
                               "the result in one line when they next talk to you."})
            if ov.state == "stopped" and not ov.paused:
                await ov.start()
        await self.tell("d-overview", "task", line + " Tell Dylan the result in one line now (the Chat is how he hears it).")
        sch_ = self.hub.bus.shared.get("schedule") or {}
        if r.get("kind") != "practice" and stage == f"Round {sch_.get('scored', 6)}":
            await self.hub.alert_all("s-portal", f"That was the last scored round. {line} The event is over: agents record "
                                     "what they have and stop; stop any Modal apps still running.", False, chat=True)
        self.st["done"].append(r["id"])   # only now: a crash before this re-announces the round after the restart
        self.st.setdefault("done_stages", []).append(stage)
        self.save()
        self.hub.set_service("s-portal", "Portal", "working", line)
        if files:
            asyncio.create_task(self.analyse(folder, stage, aid))
        asyncio.create_task(self.mirror(folder, stage, line))

    async def mirror(self, folder: Path, stage: str, line: str):
        """Dylan's agents (Challenger, Styles & fixes) need the round's data too: put the results and the hand sample
        in the shared store; Dylan's hub saves them locally and tells its agents."""
        try:
            ids = {}
            for f in [folder / "results.json"] + sorted(folder.glob("hands-first-1000.jsonl.gz"))[:1]:
                if f.exists() and f.stat().st_size <= 60_000_000:
                    fid = "R" + new_id()[1:7].upper()
                    await asyncio.wait_for(self.hub.file_store().put.aio(fid, {"name": f.name, "data": f.read_bytes(),
                                                                               "from": "s-portal", "at": time.time()}), 120)
                    ids[f.name] = fid
            if ids:
                rf = dict(self.hub.bus.shared.get("round_files") or {})
                rf[stage] = {"files": ids, "line": line, "at": time.time()}
                await self.hub.bus.set_shared("round_files", rf)
        except Exception as e:  # noqa: BLE001
            self.hub.note_error("mirror", e)

    async def analyse(self, folder: Path, stage: str, aid: str | None):
        """The hub's own runs of the card and fingerprint scripts, side by side, each routed as soon as it is done."""
        async def fp_job():
            fp = await self.run_card(folder, stage, "fp_train.py")
            if fp.startswith("(exit 0)"):
                await self.hub.route("fp_ready", stage, stage=stage, card=f"analysis/{stage}/fp/ (the hub ran fp_train.py)", note_id=aid)
            elif fp:
                sc = self.hub.agents.get("s-scout")
                if sc:
                    await sc.add_item({"kind": "hub", "wake": True, "text": f"The hub's run of analysis/fp_train.py for "
                                       f"{stage} failed:\n{fp[-1500:]}\nRun it by hand (quick mode) or ask s-data to fix it."})
        asyncio.create_task(fp_job())
        card = await self.run_card(folder, stage)
        if not card:
            return
        pl = self.hub.agents.get("s-data")
        if card.startswith("(exit 0)"):
            self.hub.card_ok = True
            await self.hub.route("card_ready", stage, stage=stage, card=f"analysis/{stage}/card.md (the hub ran it)", note_id=aid)
            if pl:
                await pl.add_item({"kind": "hub", "wake": True, "note": aid, "text": f"The hub ran analysis/roundcard.py for "
                                   f"{stage}:\n{card}\nCheck it, record the headline numbers, fyi s-overview and s-tester."})
        elif pl:
            await pl.add_item({"kind": "hub", "wake": True, "urgent": True, "note": aid, "text": f"The hub's run of "
                               f"analysis/roundcard.py for {stage} FAILED:\n{card}\nRun the card yourself now (fix the script "
                               "after T-3), write the card, record the headline numbers."})

    async def run_card(self, folder: Path, stage: str, name: str = "roundcard.py") -> str:
        """If the pipeline's round-card script exists (built and tested in the build hour), run it at once, so the
        numbers exist before any agent has taken a turn."""
        script = self.hub.repo / "analysis" / name
        if not script.exists():
            return ""
        py = self.hub.repo / ".venv" / "bin" / "python"
        uvb = shutil.which("uv")
        cmd = [str(py)] if py.exists() else ([uvb, "run", "--no-project", "--with", "numpy", "--with", "pandas", "python"]
                                             if uvb else ["python3"])
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, "-I", "-c",
                "import runpy, sys; sys.path.insert(0, sys.argv[1]); sys.argv = sys.argv[2:]; "
                "runpy.run_path(sys.argv[0], run_name='__main__')",
                str(script.parent), str(script), str(folder), cwd=str(self.hub.repo),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "AVALON_STAGE": stage})
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), 90)
            except asyncio.TimeoutError:
                proc.kill()   # a hung script must not hold the data path (or leak a process)
                return f"(the hub stopped {name} after 90 s: too slow; the agents run it by hand)"
            return (f"(exit {proc.returncode}) " + out.decode(errors="replace")[-3000:]).strip()
        except Exception as e:  # noqa: BLE001
            return f"(the hub couldn't run it: {type(e).__name__})"

    async def fetch_hands(self, tid: str, folder: Path, small_first: bool = False) -> list[str]:
        files = []
        for suffix, q in (("first-1000", "?subset=first-1000"),) + ((("full", ""),) if not (self.small_only or small_first) else ()):
            p = folder / f"hands-{suffix}.jsonl.gz"
            if p.exists() and p.stat().st_size > 100:
                files.append(str(p))
                continue
            try:
                data = await self.aget(self.hands_url.replace("{tid}", tid).replace("{q}", q)
                                       .replace("{qa}", q.replace("?", "&")), raw=True)
                if data[:1] in (b"{", b"[") and len(data) > 100 and b"<html" not in data[:400].lower():
                    data = gzip.compress(data)   # plain JSON lines: keep them, in the format everything reads
                if data[:2] != b"\x1f\x8b":
                    self.st["hands_err"] = f"got {len(data)} bytes that aren't hand data ({data[:60]!r})"
                if data[:2] == b"\x1f\x8b" and len(data) > 100:
                    def save():
                        gzip.decompress(data)   # a truncated download must never count as saved
                        tmp = p.with_suffix(".tmp")
                        tmp.write_bytes(data)
                        tmp.replace(p)
                    await asyncio.to_thread(save)
                    files.append(str(p))
            except Exception as e:  # noqa: BLE001
                self.st["hands_err"] = f"{type(e).__name__}: {str(e)[:160]}"
        return files

    async def retry_hands(self):
        if getattr(self, "_retrying", False):   # the Chat's hands link and the poll loop must not fetch the same round twice
            return
        self._retrying = True
        try:
            await self._retry_hands()
        finally:
            self._retrying = False

    async def _retry_hands(self):
        for tid, info in list(self.st["need_hands"].items()):
            files = await self.fetch_hands(tid, Path(info["folder"]))
            if files:
                if self.st["need_hands"].pop(tid, None) is None:
                    continue
                st_ = info.get("stage") or info["label"]
                self.hub.landed_at[st_] = time.time()
                await self.hub.tile("data-" + stage_slug(st_), f"{st_} data", "done", owner="s-data", stage=st_)
                await self.hub.tile("analysis-" + stage_slug(st_), f"{st_} analysis", "in progress", owner="s-data", stage=st_)
                self.st.setdefault("landed_at", {})[st_] = self.hub.landed_at[st_]
                self.save()
                aid = self.st.get("note_of", {}).get(tid)
                if aid:
                    await self.hub.note_append(aid, "Portal", f"Hand data downloaded ({', '.join(Path(f).name for f in files)}). "
                                               "Analysis starting.")
                pl = self.hub.agents.get("s-data")
                has_card = (self.hub.repo / "analysis" / "roundcard.py").exists()
                if pl:
                    await pl.add_item({"kind": "portal", "wake": True, "note": aid, "text": f"DATA LANDED (late) for "
                                       f"{info['label']}: " + " ".join(files) + (". The hub is running the round card now and "
                                       "sends you the output." if has_card else ". Run the round card now.")})
                asyncio.create_task(self.analyse(Path(info["folder"]), info.get("stage") or info["label"], aid))
                ov = self.hub.agents.get("s-overview")
                if ov:
                    await ov.add_item({"kind": "portal", "wake": True, "text": f"Hand history for {info['label']} is now "
                                       "saved:\n" + "\n".join(f"Hands: {f}" for f in files)})
            elif time.time() - info["since"] > 300 and not info.get("pinged"):
                info["pinged"] = True
                self.save()
                await self.hub.alert_all("s-portal", f"The hand history for {info['label']} hasn't downloaded for 5 minutes "
                                         f"(last error: {self.st.get('hands_err') or 'none recorded'}). "
                                         "Please download it from the portal (team page / round page) and drop the file into "
                                         "the Chat: it goes straight to the Pipeline.", True)
            elif time.time() - info["since"] > 1200 and not info.get("warned"):
                info["warned"] = True
                self.save()
                await self.hub.add_alert("s-portal", f"The hand history for {info['label']} still can't be downloaded after "
                                         "20 minutes. On the real portal, copy the download link from the round page and "
                                         "paste it into Samuel's Chat as 'hands link: <the link>' (no restart needed).", True)

    async def tell(self, to: str, kind: str, text: str):
        try:
            await self.hub.bus.send({"id": new_id(), "from": "s-portal", "from_kind": "hub", "to": to, "kind": kind,
                                     "text": text})
        except Exception:  # noqa: BLE001
            pass

    async def watch_competition(self):
        """Format settings the organizers can change mid-event (a late final weight, a held leaderboard): say so."""
        try:
            comp = await self.aget(f"/competitions/{self.cid}")
        except Exception:  # noqa: BLE001
            return
        keys = ("final_weight", "final_revealed_at", "leaderboard_held", "round_weighting", "weights", "icm_luck_correction")
        now_ = {k: comp.get(k) for k in keys if k in comp}
        old = self.st.get("comp_settings")
        self.st["comp_settings"] = now_
        if old is not None and now_ != old:
            diff = "; ".join(f"{k}: {old.get(k)} -> {now_.get(k)}" for k in keys if old.get(k) != now_.get(k))
            await self.hub.alert_all("s-portal", f"The organizers changed the competition settings: {diff}. Weights or the "
                                     "standings rule may have changed: d-platform updates the rules card, the Chats re-check "
                                     "the bar for the next decision.", True, chat=True)
            await self.tell("d-platform", "task", f"Competition settings changed on the portal: {diff}. Update the rules card "
                            "(set_rules) and tell both Chats what it changes.")

    async def check_team(self, team: dict):
        for s in team.get("submissions") or []:
            if s["id"] in self.st["subs"]:
                continue
            if s["status"] in ("ready", "rejected"):
                self.st["subs"].append(s["id"])
                if s["status"] == "rejected":
                    text = f"Upload {s['filename']} was REJECTED by the portal: {s.get('rejection_reason')}. The previous bot stays active."
                    live_ = self.hub.bus.shared.get("live") or {}
                    if same_bot(live_.get("filename") or "", s["filename"]):
                        prev = live_.get("prev") or {}
                        if prev.get("file") or prev.get("filename"):
                            await self.hub.make_live(prev.get("file") or prev.get("filename"), "portal",
                                                     note=f"{s['filename']} was rejected by the portal", tell=False)
                            text += f" {bot_name(prev.get('filename') or prev.get('file'))} is the declared live bot again; upload nothing unless your Chat gives a fixed file."
                        b = self.hub.bus.shared.get("bot:" + norm_bot(s["filename"]))
                        if isinstance(b, dict):
                            await self.hub.bus.set_shared("bot:" + norm_bot(s["filename"]), dict(b, status="failed", updated=time.time()))
                    await self.hub.alert_all("s-portal", text, True)
                    await self.tell("d-overview", "question", text)
        live = self.hub.bus.shared.get("live")
        now = time.time()
        if not self.team:
            return
        sch = self.hub.bus.shared.get("schedule") or {}
        for kind, k, ts in self.hub.clock.events():
            # scored rounds: some bot active at T-7; the declared live bot at T-2. Practice: some bot at T-2.
            for mins in ((7, 2) if kind == "scored" else (2,)):
                key = f"{int(sch.get('start', 0))}:{kind}{k}-{mins}"
                if key in self.checked or not (ts - mins * 60 * sch.get("scale", 1.0) <= now < ts):
                    continue
                self.checked.add(key)
                active = team.get("active_filename")
                if not active:
                    msg = f"{kind.title()} round {k} starts at {hhmm(ts)} and there is NO active bot. We forfeit unless one is made active."
                elif kind == "scored" and mins == 2 and live and live.get("filename") and \
                        not same_bot(live["filename"], active):
                    msg = (f"{kind.title()} round {k} starts at {hhmm(ts)}: the portal's active bot is {active}, but "
                           f"d-overview declared {live['filename']}.")
                else:
                    continue
                await self.hub.alert_all("s-portal", msg, True)
                await self.tell("d-overview", "question", msg)


# ======================================================================== web
@web.middleware
async def json_only(request, handler):
    """Every state-changing call must be JSON: a plain form or text POST from another web page can't trigger it.
    File uploads are raw bytes but need a custom header, which another site can't send without a CORS preflight."""
    if request.path == "/api/upload" and request.headers.get("X-Avalon") == "1":
        return await handler(request)
    if request.method == "POST" and not request.content_type.startswith("application/json"):
        return web.json_response({"error": "JSON only"}, status=403)
    return await handler(request)


def make_app(hub: Hub) -> web.Application:
    app = web.Application(client_max_size=400 * 1024 * 1024, middlewares=[json_only])
    r = app.router

    async def index(_):
        return web.FileResponse(HERE / "ui" / "index.html", headers={"Cache-Control": "no-store"})

    async def state(_):
        return web.json_response(hub.state())

    async def events(req):
        a = hub.agents.get(req.match_info["name"])
        if not a:
            return web.json_response({"error": "no such agent"}, status=404)
        try:
            since = int(req.query.get("since", "-1"))
        except ValueError:
            since = -1
        evs = [e for e in a.events if e["i"] > since][-800:]
        return web.json_response({"events": evs, "last_i": a.next_i - 1})

    async def stream(req):
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"})
        await resp.prepare(req)
        q: asyncio.Queue = asyncio.Queue(maxsize=5000)
        hub.subs.add(q)
        await resp.write(b"data: {\"kind\": \"hello\"}\n\n")
        try:
            while True:
                if q not in hub.subs:          # we fell behind: tell the page to resync, then rejoin
                    await resp.write(b"data: {\"kind\": \"resync\"}\n\n")
                    q = asyncio.Queue(maxsize=5000)
                    hub.subs.add(q)
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    await resp.write(f"data: {json.dumps(ev)}\n\n".encode())
                except asyncio.TimeoutError:
                    await resp.write(b": ping\n\n")
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            hub.subs.discard(q)
        return resp

    async def body(req):
        try:
            return await req.json()
        except Exception:  # noqa: BLE001
            return {}

    async def send(req):
        name = req.match_info["name"]
        text = ((await body(req)).get("text") or "").strip()
        if not text:
            return web.json_response({"error": "Type a message first."}, status=400)
        who = PEOPLE[hub.person]
        if name.endswith("overview") and not hub.view_only:
            done = await hub.chat_command(text, who)
            if done:   # the hub did it itself: log both lines in the Chat the human wrote in
                ov = hub.agents.get(name)
                if ov:
                    await ov.ov_log(who, text)
                    await ov.ov_log("Hub", done)
                    ov.pending_q = []
                return web.json_response({"ok": True, "hub": done})
        if not name.endswith("overview"):
            await hub.human_item(f"to {name}: {text}")
        if name in hub.agents:
            await hub.agents[name].human(text, who)
            return web.json_response({"ok": True})
        try:
            await hub.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": name, "text": text,
                                "kind": "task"})
        except (ValueError, OverflowError) as e:
            return web.json_response({"error": str(e)}, status=404)
        return web.json_response({"ok": True, "remote": True})

    async def control(req):
        a = hub.agents.get(req.match_info["name"])
        act = req.match_info["action"]
        if not a:
            return web.json_response({"error": "no such agent"}, status=404)
        if act == "start":
            await a.start()
        elif act == "stop":
            await a.stop()
        elif act == "interrupt" and a.client:
            a.interrupted = True
            try:
                await a.client.interrupt()
            except Exception:  # noqa: BLE001
                pass
        elif act == "policy":
            p = (await body(req)).get("policy")
            if p in ("auto", "ask"):
                a.policy = p
                a.save_meta()
                hub.emit("agent", a.view())
        else:
            return web.json_response({"error": "unknown action"}, status=400)
        return web.json_response(a.view())

    async def approve(req):
        ap = hub.approvals.get(req.match_info["id"])
        if not ap:
            return web.json_response({"error": "This request was already answered or timed out."}, status=404)
        d = (await body(req)).get("decision")
        if d not in ("allow", "always", "deny"):
            return web.json_response({"error": "bad decision"}, status=400)
        if not ap["future"].done():
            ap["future"].set_result(d)
        return web.json_response({"ok": True})

    async def dismiss(req):
        hub.dismiss(req.match_info["id"])
        return web.json_response({"ok": True})

    async def schedule(req):
        b = await body(req)
        try:
            s = await hub.clock.set_start(b.get("start", ""), int(b.get("scored") or 6), float(b.get("scale") or hub.default_scale))
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response({"ok": True, "text": s})

    r.add_get("/", index)
    r.add_static("/vendor", HERE / "ui" / "vendor")
    r.add_get("/api/state", state)
    r.add_get("/api/agents/{name}/events", events)
    r.add_get("/api/stream", stream)
    r.add_post("/api/agents/{name}/send", send)
    r.add_post("/api/agents/{name}/{action}", control)
    r.add_post("/api/approvals/{id}", approve)
    r.add_post("/api/alerts/{id}/dismiss", dismiss)
    r.add_post("/api/schedule", schedule)

    async def new_prop(req):
        b = await body(req)
        title = (b.get("title") or "").strip()
        if not title:
            return web.json_response({"error": "Give the idea a short title."}, status=400)
        fp = b.get("for") if b.get("for") in PEOPLE else hub.person
        try:
            p = await hub.new_idea(title, (b.get("body") or "").strip(), fp)
        except (ValueError, OverflowError) as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response(p)

    async def act_prop(req):
        b = await body(req)
        try:
            p = await hub.human_act(req.match_info["id"], b.get("action", ""), (b.get("text") or "").strip())
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response(p)

    async def ask_prop(req):
        b = await body(req)
        t = (b.get("text") or "").strip()
        if not t:
            return web.json_response({"error": "Type a question or instruction first."}, status=400)
        try:
            p = await hub.card_ask(req.match_info["id"], t)
        except (ValueError, OverflowError) as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response(p)

    async def start_event(req):
        if hub.bus.shared.get("schedule"):
            return web.json_response({"error": "The clock is already running. To change it, tell your Overseer the right time."}, status=400)
        s = await hub.start_now(PEOPLE[hub.person])
        return web.json_response({"ok": True, "text": s})

    async def preflight_ep(req):
        asyncio.create_task(hub.preflight(PEOPLE[hub.person]))
        return web.json_response({"ok": True})
    r.add_post("/api/preflight", preflight_ep)

    r.add_post("/api/props/{id}/ask", ask_prop)

    async def report_prop(req):
        try:
            p = await hub.note_report(req.match_info["id"])
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        except Exception as e:  # noqa: BLE001
            return web.json_response({"error": f"Couldn't write the update ({type(e).__name__})."}, status=500)
        return web.json_response(p)
    r.add_post("/api/props/{id}/report", report_prop)
    r.add_post("/api/start", start_event)

    async def set_live(req):
        b = await body(req)
        f = (b.get("file") or "").strip()
        if not f:
            return web.json_response({"error": "Pick a bot."}, status=400)
        v = await hub.make_live(f, PEOPLE[hub.person])
        return web.json_response(v)
    r.add_post("/api/live", set_live)

    async def bot_download(req):
        name = req.match_info["name"]
        data = await hub.bot_bytes(name)
        if not data:
            return web.json_response({"error": f"{name}.zip isn't on this laptop or in the shared store yet."}, status=404)
        return web.Response(body=data, content_type="application/zip",
                            headers={"Content-Disposition": f'attachment; filename="{name}.zip"'})
    r.add_get("/api/bots/{name}/download", bot_download)

    async def upload(req):
        name = req.query.get("name") or "file"
        data = await req.read()
        if not data:
            return web.json_response({"error": "Empty file."}, status=400)
        return web.json_response(await hub.take_upload(name, data, PEOPLE[hub.person], notify=req.query.get("hold") != "1"))
    r.add_post("/api/upload", upload)

    async def inbox_file(req):
        fid = re.sub(r"[^A-Z0-9]", "", req.match_info["fid"].upper())
        f = next(iter((hub.repo / "inbox").glob(f"{fid}-*")), None) if (hub.repo / "inbox").exists() and fid else None
        if not f and fid:   # attached on the other laptop: fetch it from the shared store once, keep a copy
            try:
                v = await asyncio.wait_for(hub.file_store().get.aio(fid), 25)
                if isinstance(v, dict) and v.get("data"):
                    (hub.repo / "inbox").mkdir(exist_ok=True)
                    f = hub.repo / "inbox" / f"{fid}-{re.sub(r'[^A-Za-z0-9._-]+', '_', v.get('name') or 'file')[:80]}"
                    f.write_bytes(v["data"])
            except Exception:  # noqa: BLE001
                f = None
        if not f:
            return web.json_response({"error": "not on this laptop or in the shared store"}, status=404)
        return web.FileResponse(f)
    r.add_get("/api/inbox/{fid}", inbox_file)
    r.add_post("/api/props", new_prop)
    r.add_post("/api/props/{id}/act", act_prop)
    return app


# ======================================================================== child processes
# Agents run as `claude` processes with their own children (test rigs, Modal clients, Codex). If the hub dies, they
# keep running and a restarted hub would run a second set beside them (duplicate work, clashing edits, usage). So the
# hub records its descendants every 15 s and stops leftovers on start, and stops its own on Ctrl+C / kill.
def descendants(root: int) -> list[tuple[int, str]]:
    try:
        out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,command="], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return []
    kids, cmd = {}, {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        pid, ppid = int(parts[0]), int(parts[1])
        kids.setdefault(ppid, []).append(pid)
        cmd[pid] = parts[2] if len(parts) > 2 else ""
    res, stack = [], [root]
    while stack:
        for c in kids.get(stack.pop(), []):
            res.append((c, cmd.get(c, "")))
            stack.append(c)
    return res


def stop_processes(procs: list) -> int:
    """SIGTERM, then SIGKILL after 3 s, every listed process still running the SAME command (a reused pid is spared)."""
    import signal
    try:
        out = subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return 0
    now = {int(p): c for p, c in (l.strip().split(None, 1) for l in out.splitlines() if l.strip() and " " in l.strip())
           if p.isdigit()}
    hit = [pid for pid, c in procs if pid != os.getpid() and now.get(pid) == c]
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for pid in hit:
            try:
                os.kill(pid, sig)
            except Exception:  # noqa: BLE001
                pass
        if sig == signal.SIGTERM and hit:
            time.sleep(3)
    return len(hit)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--person", required=True, choices=list(PEOPLE))
    ap.add_argument("--repo", required=True, help="the team repo the agents work in")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--data", default=None, help="hub state folder (default ~/.avalon-hub/<person>)")
    ap.add_argument("--namespace", default="", help="message-line suffix, e.g. --namespace=-live on Sunday")
    ap.add_argument("--no-autostart", action="store_true")
    ap.add_argument("--view-only", action="store_true", help="show the screen with saved data; start no agents or services")
    ap.add_argument("--model", default=None, help="run every agent on this model (e.g. claude-haiku-5-5 for tests)")
    ap.add_argument("--worker-model", default=None, help="run the workers (not the Overseers) on this model, e.g. "
                    "claude-sonnet-5-5 to save the Opus allowance")
    ap.add_argument("--start", default=None, help="event minute 0 as HH:MM[:SS] (sets the shared clock)")
    ap.add_argument("--scale", type=float, default=1.0, help="simulations only: event-minutes run this fast (0.25 = 4x)")
    ap.add_argument("--portal-base", default=None, help="portal API base, e.g. http://127.0.0.1:8765/tournament/api")
    ap.add_argument("--portal-key-file", default=None)
    ap.add_argument("--codex-model", default=None, help="Codex model for codex_task jobs (default: Codex's own)")
    ap.add_argument("--codex-max", type=int, default=6, help="Codex jobs running at once (separate credits: use them)")
    ap.add_argument("--no-codex", action="store_true")
    ap.add_argument("--portal-data", default=None, help="where the portal watcher saves results and hand data (default ~/portal-data)")
    ap.add_argument("--small-hands", action="store_true", help="download only the first-1000 hand file (phone hotspot)")
    ap.add_argument("--hands-url", default=None, help="hand-history URL template with {tid} (real portal: copy it on the day)")
    a = ap.parse_args()
    data = Path(a.data or Path.home() / ".avalon-hub" / a.person).expanduser()
    data.mkdir(parents=True, exist_ok=True)
    hub = Hub(a.person, Path(a.repo).expanduser().resolve(), data, a.namespace, a.model)
    if a.portal_data:
        hub.portal_data = Path(a.portal_data).expanduser().resolve()
    await hub.bus.start()
    try:   # restart safety: see the shared state before acting on it (bounded, so a dead link can't block startup)
        await asyncio.wait_for(hub.bus.synced.wait(), 12)
    except asyncio.TimeoutError:
        pass
    for ag in hub.agents.values():
        hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task, "summary": ag.summary})
    try:   # the pre-flight compares both laptops' hub code
        ver = subprocess.run(["git", "-C", str(Path(__file__).parent), "rev-parse", "--short", "HEAD"], capture_output=True,
                             text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(Path(__file__).parent), "status", "--porcelain", "--", "."], capture_output=True,
                               text=True, timeout=10).stdout.strip()
        await hub.bus.set_shared("codever:" + hub.person, ver + ("+local changes" if dirty else ""))
    except Exception:  # noqa: BLE001
        pass
    for pr in hub.local_props.values():   # re-share this laptop's notes (e.g. after a restart), merged with the remote copy
        other = hub.bus.shared.get("prop:" + pr["id"])
        merged = merge_note(other, pr) if isinstance(other, dict) else pr
        if merged != other:
            asyncio.create_task(hub.bus.set_shared("prop:" + pr["id"], merged))
    hub.default_scale = a.scale
    left = load_json(hub.data / "children.json", [])
    if left and not a.view_only:   # a previous run of this hub died: stop what it left running
        n = await asyncio.to_thread(stop_processes, [tuple(x) for x in left])
        if n:
            print(f"stopped {n} process(es) left running by the previous hub run", flush=True)
    atomic_write(hub.data / "children.json", "[]")
    if not a.view_only:
        import signal as _sig

        def _bye(*_):   # Ctrl+C or kill: take the agents' processes down too, incl. ones already detached from us
            stop_processes(descendants(os.getpid()) + [tuple(x) for x in load_json(hub.data / "children.json", [])])
            atomic_write(hub.data / "children.json", "[]")
            os._exit(0)
        for s_ in (_sig.SIGTERM, _sig.SIGINT):
            asyncio.get_running_loop().add_signal_handler(s_, _bye)

        async def record_children():
            while True:
                kids = await asyncio.to_thread(descendants, os.getpid())
                atomic_write(hub.data / "children.json", json.dumps(kids))
                await asyncio.sleep(15)
        asyncio.create_task(hub.forever("children", record_children))
    hub.view_only = a.view_only
    hub.worker_model = a.worker_model
    hub.bus.scale = a.scale
    if a.start:
        await hub.clock.set_start(a.start, scale=a.scale)
    if not a.view_only:
        asyncio.create_task(hub.forever("clock", hub.clock.loop))

        async def consistency_loop():   # its model call must never hold up the clock's marks
            while True:
                try:
                    await asyncio.wait_for(hub.consistency_check(), 120)
                except Exception as e:  # noqa: BLE001
                    hub.note_error("consistency", e)
                await asyncio.sleep(10)
        asyncio.create_task(hub.forever("consistency", consistency_loop))
        asyncio.create_task(hub.forever("releases", hub.scan_releases))
        asyncio.create_task(hub.forever("watch_live", hub.watch_live))

        async def pull_loop():   # Dylan's laptop: round data from Samuel's, off the upload-alert loop
            while True:
                try:
                    await hub.pull_round_files()
                except Exception as e:  # noqa: BLE001
                    hub.note_error("pull-round", e)
                await asyncio.sleep(5)
        asyncio.create_task(hub.forever("pull_round_files", pull_loop))
    if not a.no_codex and not a.view_only:
        hub.codex = Codex(hub, a.codex_model, a.codex_max)
        hub.codex.status()
    if a.portal_base and a.portal_key_file and not a.view_only:
        hub.portal = PortalWatcher(hub, a.portal_base, Path(a.portal_key_file), a.hands_url,
                                   Path(a.portal_data) if a.portal_data else None, a.small_hands)
        asyncio.create_task(hub.forever("portal", hub.portal.loop))
    runner = web.AppRunner(make_app(hub))
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", a.port).start()
    print(f"avalon hub ({PEOPLE[a.person]}): http://127.0.0.1:{a.port}   link: "
          f"{'online' if hub.bus.online else hub.bus.error}", flush=True)
    for ag in hub.agents.values():
        if ag.worktree_problem:
            await hub.add_alert(ag.name, f"{ag.title} {ag.worktree_problem}; it is working in the main repo instead. "
                                "Ask your Overseer to keep its edits to its own folders.", True)
    if a.view_only:
        print("view-only: no agents or services started", flush=True)
        await asyncio.Event().wait()
    restarted = any(ag.was_running for ag in hub.agents.values())
    for ag in hub.agents.values():
        if ag.was_running:
            await ag.add_item({"kind": "hub", "wake": True, "text": f"The hub restarted at {hhmm(time.time())}. "
                               "Re-check your PLAN file, your inbox and the latest portal notice, then carry on."})
            await ag.start()
        elif not a.no_autostart and ag.spec.get("autostart") and (not restarted or ag.name.endswith("overview")):
            if not ag.session_id and ag.name in KICKOFF:
                await ag.add_item({"kind": "hub", "wake": True, "text": KICKOFF[ag.name]})
            await ag.start()

    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            for ag in hub.agents.values():
                hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task, "summary": ag.summary[:2000],
                                          "status_at": ag.status_at,
                                          "idle_since": ag.idle_since})
                ag.save_meta()
            if hub.bus.outbox and hub.bus.oldest_unsent_age() > 120:
                await hub.add_alert("hub", "Messages to the other laptop have been waiting over 2 minutes: the link "
                                    "is down. Talk to your teammate directly until it's back.", True)
    asyncio.create_task(heartbeat())
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
