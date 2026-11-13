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
import hashlib
import json
import math
import shutil
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
from roster import COMMON_RULES, KICKOFF, PEOPLE, PROTOCOL, ROSTER

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
HUB_TOOLS = ["send_message", "list_agents", "read_agent", "set_status", "notify_human", "start_agent", "stop_agent",
             "declare_live", "set_schedule", "propose", "update_proposal", "list_proposals", "codex_task", "register_bot",
             "record", "verify", "invalidate", "set_rules", "ledger", "next_bot_name"]
API_KEY_FILE = Path.home() / ".config" / "avalon-hub" / "anthropic-api-key"
KINDS = ("idea", "build", "live", "analysis", "bot", "question", "research", "finding", "change", "decision")
BUILD_NOTES = [  # (person, agent, name): one note per build-hour work stream, created at minute 0
    ("dylan", "d-platform", "Legal bot v1, test harness, today's hand ranking"),
    ("dylan", "d-builder", "Styles A, B and C"),
    ("samuel", "s-tester", "Test rig (paired runs, sparring)"),
    ("samuel", "s-pipeline", "Round card: today's hand data in numbers within a minute"),
]


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
    if old.get("status") == "removed" or (old.get("status") in ("approved", "rejected") and new.get("status") in ("needs_call", "revise")):
        m["status"] = old["status"]
        m["decided_by"] = old.get("decided_by", m.get("decided_by"))
    if not m.get("body") and old.get("body"):
        m["body"] = old["body"]
    return m


def stage_of(sch: dict | None, t: float) -> str:
    """The competition stage at time t: Build, Practice 1-4, Round k, Round k.5 (the practice after round k)."""
    if not sch:
        return "Before the start"
    m = (t - sch["start"]) / (60 * sch.get("scale", 1.0))
    if m < 0:
        return "Before the start"
    if m < 20:
        return "Build"
    if m < 60:
        return f"Practice {int((m - 20) // 10) + 1}"
    j, nsc = int((m - 60) // 10), sch.get("scored", 6)
    k = j // 2 + 1
    if k > nsc:
        return f"Round {nsc}"
    return f"Round {k}" if j % 2 == 0 else f"Round {k}.5"


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
APPROVAL_TIMEOUT = 120


class LimitHit(Exception):
    pass
EVENT_CAP = 4000


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
        self.agents: dict[str, Agent] = {s["name"]: Agent(self, s) for s in ROSTER[person]}
        self.bus.local_names = set(self.agents)
        self.services: dict[str, dict] = {}
        self.local_props: dict[str, dict] = load_json(data / "props.json", {})
        self.clock = Clock(self)
        self.codex: Codex | None = None
        self.portal: PortalWatcher | None = None
        self.portal_data = Path.home() / "portal-data"
        self.default_scale = 1.0
        self.report_busy: set[str] = set()
        self.last_landed = 0.0

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
        return next(a for a in self.agents.values() if a.name.endswith("overseer"))

    async def add_alert(self, agent: str, text: str, urgent: bool):
        now = time.time()
        for a in self.alerts:
            if a["agent"] == agent and a["text"] == text and now - a["at"] < 600:
                return
        if agent.endswith("overseer"):   # one live note per Overseer: a new one replaces the old
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

    def rules(self) -> dict:
        return self.bus.shared.get("rules") or {}

    async def put_item(self, it: dict):
        it["updated"] = time.time()
        self.bus.shared["led:" + it["id"]] = it
        await self.bus.set_shared("led:" + it["id"], it)

    def rule_conflict(self, it: dict) -> str:
        """A result or method that contradicts the rules card is rejected when it is written."""
        r = self.rules()
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
        stage = stage_of(self.bus.shared.get("schedule"), time.time())
        n = sum(1 for x in self.ledger() if x.get("type") == typ) + 1
        iid = f"{typ[0].upper()}{n}-{by.split('-')[0]}{int(time.time()) % 10000:04d}"
        it = {k: v for k, v in it.items() if v not in (None, "", [])}
        it.update({"id": iid, "type": typ, "by": by, "stage": it.get("stage") or stage, "at": time.time(),
                   "status": "validated" if typ in ("human", "commitment") else "proposed"})
        await self.put_item(it)
        if it.get("note") and typ in ("result", "hypothesis"):
            await self.note_append(it["note"], by, f"**{'Result' if typ == 'result' else 'Hypothesis'}:** {it.get('claim', '')}"
                                   + (f" ({it.get('effect')} ± {it.get('se')}, n={it.get('n')})" if it.get("n") else ""), action="update")
        return iid, ""

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
                await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": u, "kind": "task", "text": msg})
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
                    await self.bus.send({"id": new_id(), "from": "hub", "from_kind": "hub", "to": u, "kind": "fyi", "text": text})
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
            await self.ensure_note(f"B{i}-{t0}", kind="build", stage="Build", owner=self.owner_overseer(who),
                                   author=agent, title=f"Build {i} of {len(BUILD_NOTES)} · {name}",
                                   headline=f"{name}: {agent.split('-', 1)[1].title()} is on it.",
                                   thread=[{"who": "Clock", "at": time.time(), "action": "update",
                                            "text": f"Started at minute 0. Plan: {task}"}])

    async def note_append(self, pid: str, who: str, text: str, action: str = "update", **fields):
        p = self.get_prop(pid)
        if not p or p.get("status") == "removed":
            return
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": action, "text": text[:12000]})
        p.update(fields)
        await self.save_prop(p)

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
        self.emit("shared", {"bots": True})
        await self.bus.set_shared("bot:" + name, v)

    def find_bot_file(self, file: str) -> Path | None:
        """The bot's zip on this laptop: the path as given (repo-relative), else any releases/<name>.zip in the repo
        or an agent's worktree."""
        cands = [self.repo / file, self.repo / "releases" / (bot_name(file) + ".zip")]
        cands += [a.cwd / "releases" / (bot_name(file) + ".zip") for a in self.agents.values()]
        return next((c for c in cands if c.is_file() and c.suffix == ".zip"), None)

    def bot_store(self):
        import modal
        return modal.Dict.from_name("avalon-botfiles" + self.bus.ns, create_if_missing=True)

    async def store_bot_file(self, name: str, f: Path):
        """Keep a copy of each ready bot where both laptops can download it (fetched only on demand)."""
        try:
            data = f.read_bytes()
            if len(data) <= 8_000_000:
                await self.bot_store().put.aio(name, data)
        except Exception:  # noqa: BLE001
            pass

    async def bot_bytes(self, name: str) -> bytes | None:
        b = self.bus.shared.get("bot:" + name) or {}
        f = self.find_bot_file(b.get("file") or name)
        if f:
            return f.read_bytes()
        try:
            return await self.bot_store().get.aio(name)
        except Exception:  # noqa: BLE001
            return None

    async def scan_releases(self):
        """Every zip in the repo's releases/ is a bot that exists (Platform packs releases there)."""
        await self.bus.synced.wait()
        while True:
            try:
                for z in sorted((self.repo / "releases").glob("*.zip")):
                    if z.is_symlink() or not re.fullmatch(r"v\d+[a-z]?", z.stem):
                        continue   # aliases, not bots
                    cur = self.bus.shared.get("bot:" + bot_name(z.name)) or {}
                    if cur.get("status") != "failed" and (cur.get("status") != "ready" or cur.get("size") != z.stat().st_size):
                        await self.register_bot(cur.get("file") or "releases/" + z.name, "ready", by=cur.get("by") or "releases/")
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(30)

    async def make_live(self, file: str, who: str, note: str = "", tell: bool = True) -> dict:
        v = {"filename": Path(file).name, "file": file, "sha256": "", "note": note or f"made live by {who}",
             "by": who, "at": time.time()}
        await self.bus.set_shared("live", v)
        self.emit("shared", {"live": v})
        if not tell:
            return v
        try:
            await self.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": "d-overseer", "kind": "task",
                                 "text": f"{who} made {file} the live bot. Make sure Dylan uploads exactly that file on the "
                                         "portal and makes it active now (the portal watcher will confirm)."})
        except Exception:  # noqa: BLE001
            pass
        return v

    async def alert_all(self, agent: str, text: str, urgent: bool):
        """An alert for both screens (the portal watcher runs on one laptop, but Dylan's hands do the uploads)."""
        await self.add_alert(agent, text, urgent)
        aid = new_id()
        await self.bus.set_shared("palert:" + aid, {"id": aid, "agent": agent, "text": text, "urgent": urgent,
                                                    "from": self.person, "updated": time.time()})

    async def watch_live(self):
        """Dylan's laptop: when the live bot changes and the portal isn't running it yet, ask Dylan to upload it."""
        await self.bus.synced.wait()
        seen = (self.bus.shared.get("live") or {}).get("at")
        pseen = {k for k in self.bus.shared if k.startswith("palert:")}
        while True:
            await asyncio.sleep(3)
            for k, v in list(self.bus.shared.items()):
                if k.startswith("palert:") and k not in pseen and isinstance(v, dict):
                    pseen.add(k)
                    if v.get("from") != self.person and time.time() - v.get("updated", 0) < 900:
                        await self.add_alert(v.get("agent", "s-portal"), v.get("text", ""), bool(v.get("urgent")))
            live = self.bus.shared.get("live") or {}
            act = (self.bus.shared.get("portal_active") or {}).get("filename")
            if live.get("filename") and norm_bot(act) == norm_bot(live.get("filename")):
                for al in [x for x in self.alerts if "Upload " in x.get("text", "") and live["filename"] in x.get("text", "")]:
                    self.dismiss(al["id"])
            if live.get("at") and live.get("at") != seen:
                seen = live["at"]
                act = (self.bus.shared.get("portal_active") or {}).get("filename")
                if self.person == "dylan" and norm_bot(act) != norm_bot(live.get("filename")):
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
                out = ""
                async for m in sdk_query(prompt=prompt, options=ClaudeAgentOptions(
                        model=NARRATOR_MODEL, tools=[], max_turns=1, setting_sources=[], cwd=str(self.data),
                        system_prompt="You write short, faithful progress updates. Output JSON only.")):
                    if isinstance(m, ResultMessage):
                        out = m.result or ""
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
            briefs = "\n".join(f"- {a.name} ({a.state}): {a.task} | {(a.summary or '')[:500]}" for a in self.agents.values())
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
                      "right now'). Use only facts below; if the agents disagree or something was corrected, say so. No "
                      "ids or jargon a human wouldn't know; name agents by role (the analyst, the tester, the builder). "
                      f"Keep it under 350 words.\n\nLive bot chosen: {live.get('filename', 'none')}; active on the portal: "
                      f"{act.get('filename', 'unknown')}. Time now {hhmm(time.time())}.\n\nNOTE SUMMARY:\n{p.get('body') or '(none yet)'}"
                      f"\n\nNOTE CONVERSATION (latest last):\n{thread or '(empty)'}\n\nTHE OVERSEER'S RECENT WORK (latest last):\n"
                      f"{work or '(not on this laptop)'}\n\nEVERY AGENT'S CURRENT BRIEF:\n{briefs}")
            out = ""
            async for m in sdk_query(prompt=prompt, options=ClaudeAgentOptions(
                    model=REPORT_MODEL, tools=[], max_turns=1, setting_sources=[], cwd=str(self.data),
                    system_prompt="You write clear, faithful status reports from the material given. Never invent facts.")):
                if isinstance(m, ResultMessage):
                    out = (m.result or "").strip()
            if out:
                p = self.get_prop(pid) or p
                p["report"] = {"text": out, "at": time.time(), "n": len(p.get("thread", []))}
                await self.save_prop(p)
            return p
        finally:
            self.report_busy.discard(pid)

    def owner_overseer(self, person: str) -> str:
        return ("s-" if person == "samuel" else "d-") + "overseer"

    async def human_act(self, pid: str, action: str, text: str) -> dict:
        p = self.get_prop(pid)
        if not p:
            raise ValueError("That card no longer exists.")
        who = PEOPLE[self.person]
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": action, "text": text})
        if action in ("approve", "reject", "comment"):
            await self.human_item(f"{action} on note \"{p['title']}\"" + (f": {text}" if text else ""), p["id"])
        target = p.get("owner") or p.get("author")
        if action == "approve" and p.get("deadline") and time.time() > p["deadline"]:
            raise ValueError("Too late: the deadline for this decision has passed, so the default applies.")
        if action == "approve" and p.get("bot"):
            await self.make_live(p["bot"], who, f"greenlit on note #{p['id']}", tell=False)
            p["status"], p["decided_by"] = "approved", who
            note = f"GREENLIT by {who}: #{p['id']} use {p['bot']}. It is now the declared live bot; Dylan uploads it."
        elif action == "approve":
            p["status"], p["decided_by"] = "approved", who
            note = f"GREENLIT by {who}: #{p['id']} \"{p['title']}\"." + (f" Note: {text}" if text else "") + " Go ahead."
        elif action == "reject":
            p["status"], p["decided_by"] = "rejected", who
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
            target = p.get("owner") if str(p.get("owner", "")).endswith("overseer") else self.owner_overseer(p.get("author_person") or self.person)
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
            raise ValueError("That card no longer exists.")
        who = PEOPLE[self.person]
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": "ask", "text": text})
        await self.human_item(f"on note \"{p['title']}\": {text}", p["id"])
        await self.save_prop(p)
        ov = p.get("owner") if str(p.get("owner", "")).endswith("overseer") else self.owner_overseer(p.get("author_person") or self.person)
        recent = "\n".join(f"  {t['who']}: {str(t['text'])[:400]}" for t in p["thread"][-7:-1])
        await self.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": ov, "kind": "task", "note": p["id"], "text": (
            f"[note #{p['id']} \"{p['title']}\" ({p.get('stage', '')}) chat] {who}: {text}\n"
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

    async def expire_decisions(self):
        now = time.time()
        for p in self.props():
            if p.get("status") in ("needs_call", "revise") and p.get("deadline") and now > p["deadline"] and \
                    (p.get("author") in self.agents):
                p["status"] = "expired"
                p.setdefault("thread", []).append({"who": "Hub", "at": now, "action": "expire",
                                                   "text": "No greenlight before the deadline: the default applies."})
                await self.save_prop(p)
                a = self.agents[p["author"]]
                await a.add_item({"kind": "hub", "wake": True, "text": f"Card #{p['id']} \"{p['title']}\" got no greenlight "
                                  "before its deadline. Apply the default (for a live-bot decision: the live bot stays)."})

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
                "alerts": self.alerts, "schedule": self.bus.shared.get("schedule"),
                "live": self.bus.shared.get("live"), "clock": self.clock.next_text(), "props": self.props()[:200],
                "bots": self.bots()[:40], "portal_active": self.bus.shared.get("portal_active"),
                "overviews": {k[7:]: v.get("items", []) for k, v in self.bus.shared.items()
                              if k.startswith("ovchat:") and isinstance(v, dict)},
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
        self.led_seen: set = set()          # ledger ids this agent was shown or wrote (for invalidation notices)
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
                "overseer": self.name.endswith("overseer"), "since": self.turn_started, "last_i": self.next_i - 1,
                "cwd": str(self.cwd), "context": self.context_tokens}

    def model(self):
        return self.hub.model_override or self.model_switch or self.spec.get("model", "claude-opus-5-5")

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
        if self.name.endswith("overseer") and ev.get("type") in ("text", "msg_in", "msg_out") and \
                time.time() - getattr(self, "ovwork_at", 0) > 30:
            self.ovwork_at = time.time()
            asyncio.get_event_loop().call_later(1, lambda: asyncio.ensure_future(self.hub.bus.set_shared(
                "ovwork:" + self.name, {"text": self.ovwork_rows(time.time() - 1800, 8000), "updated": time.time()})))
        if self.name.endswith("overseer"):
            t = ev.get("type")
            if t == "text" and not ev.get("sub"):
                self.narr_buf.append(("text", ev.get("text", "")))
            elif t == "msg_out":
                self.narr_buf.append(("msg_out", f"to {ev.get('to')}: {str(ev.get('text'))[:1500]}"))
            elif t == "msg_in":
                self.narr_buf.append(("msg_in", f"from {ev.get('from')}: {str(ev.get('text'))[:1500]}"))
            elif t == "tool":
                self.narr_buf.append(("tool", f"{ev.get('name')} {str(ev.get('input'))[:200]}"))
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
                subprocess.run(["git", "-C", str(repo), "worktree", "add", "-B", "builder", str(wt)],
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
            try:
                await self.client.interrupt()
            except Exception:  # noqa: BLE001
                self.preempting = False
        if item.get("wake", True):
            self.wake.set()
        self.hub.emit("agent", self.view())

    async def receive(self, msg: dict):
        kind = msg.get("kind") or "question"
        if self.name.endswith("overview") and msg.get("from_kind") == "human":
            await self.ov_log(msg["from"], msg["text"])
        self.record({"type": "msg_in", "from": msg["from"], "text": msg["text"], "id": msg["id"],
                     "kind": kind, "reply_to": msg.get("reply_to"), "from_kind": msg.get("from_kind")})
        wake = kind not in ("fyi", "answer_to_answer") or msg.get("from") in ("s-pipeline", "s-skeptic", "hub") or bool(msg.get("note"))
        await self.add_item({"kind": "msg", "wake": wake, "urgent": msg.get("from_kind") == "human" and kind != "fyi", **msg})
        if self.state == "stopped" and not self.paused and kind != "fyi":
            await self.start()

    async def human(self, text: str, who: str):
        self.record({"type": "user", "text": text, "from": who, "queued": self.state in ("working", "waiting")})
        if self.name.endswith("overview"):
            await self.ov_log(who, text)
        await self.add_item({"kind": "human", "from": who, "text": text, "urgent": True})
        if self.state == "stopped":
            self.paused = False
            await self.start()

    def overview_context(self) -> str:
        """What the Overview reads before answering: the Overseer's recent work and the open notes."""
        hub = self.hub
        ov = hub.agents.get(self.name.replace("overview", "overseer"))
        since = max(self.ov_last - 300, time.time() - 1800)
        self.ov_last = time.time()
        rows = []
        if not ov:
            rows = [(hub.bus.shared.get("ovwork:" + self.name.replace("overview", "overseer")) or {}).get("text", "")]
        if ov:
            for e in ov.events[-200:]:
                if e.get("t", 0) < since:
                    continue
                t = e.get("type")
                if t == "text" and not e.get("sub"):
                    rows.append(f"[{hhmm(e['t'])}] Overseer: {e['text'][:1200]}")
                elif t in ("msg_in", "msg_out"):
                    rows.append(f"[{hhmm(e['t'])}] {'from ' + str(e.get('from')) if t == 'msg_in' else 'to ' + str(e.get('to'))}: {str(e.get('text'))[:700]}")
        notes = []
        for p in hub.props():
            if p.get("status") == "removed":
                continue
            last = (p.get("thread") or [{}])[-1]
            notes.append(f"- {p.get('stage', '')} · {p['kind']} · {p['status']}: {p['title']}"
                         + (f"\n  summary: {p['body'][:400]}" if p.get("body") else "")
                         + (f"\n  latest: {str(last.get('text', ''))[:300]}" if last else ""))
        return ("[the Overseer's recent work, latest last]\n" + ("\n".join(rows)[-12000:] or "(nothing new)") +
                "\n\n[notes on the board]\n" + ("\n".join(notes[:16])[:6000] or "(none)"))

    async def ov_log(self, who: str, text: str):
        """The Overview conversation, shared so the other person can read (and write in) it too."""
        self.ovchat = (self.ovchat + [{"who": who, "at": time.time(), "text": text[:4000]}])[-40:]
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
        hub, ov = self.hub, self.name.endswith("overseer")
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
            out.append("[human instructions, newest last; these override anything else]\n" + "\n".join(
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
        rows = [(a.name, a.title, a.state, a.summary) for a in hub.agents.values() if a is not self]
        rows += [(n, v.get("title", n), v.get("state"), v.get("summary") or "") for n, v in hub.bus.directory.items()
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
        for k in range(1, sch.get("scored", 6) + 1):
            ts = sch["start"] + (60 + 20 * (k - 1)) * U
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
        limit = COMPACT_AT_OVERSEER if self.name.endswith("overseer") else COMPACT_AT_WORKER
        if self.context_max:   # stay well below the CLI's own auto-compact point
            limit = min(limit, int(0.65 * self.context_max))
        if tokens < limit or self.crunch():
            return
        await self.set_state("working", "compacting")
        self.record({"type": "note", "text": f"Compacting its context ({tokens // 1000}k tokens) to stay fast."})
        try:
            await self.client.query("/compact " + COMPACT_KEEP + (" " + self.spec.get("keep", "")))
            async for m in self.client.receive_response():
                self.handle(m)
            self.digest_full = True
        except Exception as e:  # noqa: BLE001
            self.record({"type": "note", "text": f"Compaction failed ({e}); it carries on."})

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
                f"\n{PROTOCOL}\n{COMMON_RULES}")
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
                prompt = "\n\n".join(self.format(b) for b in batch)
                if any(b.get("retry") for b in batch):
                    prompt = ("(Retrying this input after an error: some actions from the previous attempt may already have "
                              "happened. Check (ledger, notes, messages, files) before repeating any of them.)\n\n" + prompt)
                digest = self.team_digest()
                if digest:
                    prompt = digest + "\n\n" + prompt
                if self.name.endswith("overview"):
                    prompt = situation(self.hub) + "\n\n" + self.overview_context() + "\n\n" + prompt
                if self.name.endswith("overseer"):
                    prompt = situation(self.hub) + "\n\n" + prompt
                    self.narr_buf, self.narr_mark = [("input", prompt[-6000:])], 1
                    self.turn_notes = {b["note"] for b in batch if b.get("note") and b.get("from_kind") == "human"}
                    self.turn_note_refs = {b["note"] for b in batch if b.get("note")}
                    ticker = asyncio.create_task(self.narr_ticker())
                self.turn_started = time.time()
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
                if self.interrupted:            # paused by a human: the turn is over, don't replay it
                    ok, limited, self.interrupted = True, False, False
                    self.record({"type": "note", "text": "Paused."})
                if limited:
                    raise LimitHit("usage limit reached")
                if not ok:
                    raise RuntimeError("the turn ended with an error")
                done = {i["id"] for i in batch}
                self.items = [i for i in self.items if i["id"] not in done]
                self.save_items()
                self.fails = 0
                if self.name.endswith("overseer"):
                    ticker.cancel()
                    buf, self.narr_buf = self.narr_buf, []
                    asyncio.create_task(self.hub.narrate(self, buf, self.turn_notes, True, self.narr_mark, set(self.turn_note_refs)))
                await self.maybe_compact()
                await self.set_state("idle")
                if any(i.get("wake", True) for i in self.items if not i.get("taken")):
                    self.wake.set()
            except asyncio.CancelledError:
                if "ticker" in locals():
                    ticker.cancel()
                for i in batch:
                    i.pop("taken", None)
                self.save_items()
                raise
            except Exception as e:  # noqa: BLE001
                if "ticker" in locals():
                    ticker.cancel()
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
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock) and b.text.strip():
                    self.record({"type": "text", "text": b.text, "sub": bool(m.parent_tool_use_id)})
                    if self.name.endswith("overview") and not m.parent_tool_use_id:
                        asyncio.create_task(self.ov_log("Overview", b.text))
                elif isinstance(b, ToolUseBlock):
                    self.record({"type": "tool", "name": b.name, "input": short(b.input), "id": b.id,
                                 "sub": bool(m.parent_tool_use_id)})
            if getattr(m, "error", None):
                return "limited" if LIMIT_RX.search(str(m.error)) else "error"
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
                return "limited" if LIMIT_RX.search(text) else "error"
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
                asyncio.create_task(self.hub.add_alert(self.name, f"{self.title} has used {pct} of its Claude "
                                    f"{(info.rate_limit_type or '').replace('_', ' ')} allowance"
                                    + (f" (resets {hhmm(info.resets_at)})" if info.resets_at else "") + ".", False))
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

        @tool("set_status", "Update your state (working/waiting/blocked/done/idle), one-line task and markdown summary.",
              schema([], {"state": "string", "task": "string", "summary": "string"}))
        async def set_status(a):
            me.task = (a.get("task") or me.task)[:200]
            if a.get("summary"):
                me.summary = a["summary"][:6000]
                need = re.search(r"\*\*Needs from a human:?\*\*:?\s*(.+)", me.summary)
                need = need.group(1).strip() if need else ""
                if need and not re.match(r"(nothing|none|n/?a|no\b)", need, re.I) and need != me.last_need:
                    me.last_need = need
                    if me.name.endswith("overseer"):
                        await hub.add_alert(me.name, need[:400], False)
                    else:
                        await hub.overseer().add_item({"kind": "hub", "wake": False,
                                                       "text": f"{me.title} needs something from a human: {need[:400]}"})
            me.save_meta()
            st = a.get("state") if a.get("state") in STATES else None
            await me.set_state(st or me.state)
            return ok("Status updated.")

        @tool("notify_human", "Overseers only: ask your human to decide or act. Shown prominently on their screen.",
              schema(["text"], {"text": "string", "urgent": "boolean"}))
        async def notify_human(a):
            if not me.name.endswith("overseer"):
                await hub.overseer().add_item({"kind": "hub", "wake": True,
                                               "text": f"{me.title} wanted to tell the human: {a['text']}"})
                return ok("Only your Overseer talks to humans; it has been passed to your Overseer.")
            await hub.add_alert(me.name, a["text"], bool(a.get("urgent")))
            me.record({"type": "notify", "text": a["text"], "urgent": bool(a.get("urgent"))})
            return ok("Your human has been notified.")

        @tool("start_agent", "Overseer only: start one of this laptop's agents with a first task.",
              schema(["name"], {"name": "string", "task": "string"}))
        async def start_agent(a):
            if not me.name.endswith("overseer"):
                return ok("Only the Overseer can start agents.")
            ag = hub.agents.get(a["name"].strip())
            if not ag or ag is me:
                return ok(f"No such agent here. This laptop's agents: {', '.join(hub.agents)}")
            await ag.start(a.get("task") or None)
            return ok(f"{ag.name} started.")

        @tool("stop_agent", "Overseer only: stop one of this laptop's agents (it stays stopped until restarted).",
              schema(["name"], {"name": "string"}))
        async def stop_agent(a):
            if not me.name.endswith("overseer"):
                return ok("Only the Overseer can stop agents.")
            ag = hub.agents.get(a["name"].strip())
            if not ag or ag is me:
                return ok("Can't stop that agent.")
            await ag.stop()
            return ok(f"{ag.name} stopped.")

        @tool("declare_live", "d-overseer only: record the bot that should be active on the portal: the EXACT file name "
              "Dylan uploads (e.g. 'v4.zip'), and its sha256 if known. The portal watcher checks the portal against it "
              "before every scored round, so tell Dylan to upload a file with this exact name.",
              schema(["filename"], {"filename": "string", "sha256": "string", "note": "string"}))
        async def declare_live(a):
            if me.name != "d-overseer":
                return ok("Only d-overseer declares the live bot.")
            v = {"filename": a["filename"], "sha256": a.get("sha256") or "", "note": a.get("note") or "", "at": time.time()}
            await hub.bus.set_shared("live", v)
            hub.emit("shared", {"live": v})
            return ok(f"Live bot declared: {v['filename']}.")

        @tool("set_schedule", "Overseers: set or correct the event clock when a HUMAN tells you a time in this turn "
              "(e.g. 'round 1 is in 5 minutes', 'practice 3 moved to 22:58', 'the variant was announced at 14:02'). "
              "event: minute0 | practiceN | scoredN (e.g. scored1, practice3). Give either at='HH:MM' (today) or "
              "in_minutes (real minutes from now). The whole schedule shifts so that event lands at that time; both "
              "laptops update. Never change it on your own initiative.",
              schema(["event"], {"event": "string", "at": "string", "in_minutes": "number", "scored_rounds": "integer"}))
        async def set_schedule(a):
            if not me.name.endswith("overseer"):
                return ok("Only Overseers set the clock.")
            if hub.bus.shared.get("schedule") and not me.human_in_turn:
                return ok("The clock is set. Only change it when a human tells you a time in this turn; otherwise tell "
                          "your human with notify_human.")
            ev = (a.get("event") or "minute0").lower().replace(" ", "").replace("round", "")
            sch = hub.bus.shared.get("schedule") or {}
            scale = sch.get("scale", hub.default_scale)
            m = re.fullmatch(r"(minute0|start|practice(\d+)|scored(\d+))", ev)
            if not m:
                return ok("event must be minute0, practiceN or scoredN.")
            if m.group(2):
                n = int(m.group(2))
                off = (20, 30, 40, 50)[n - 1] if n <= 4 else 70 + 20 * (n - 5)
            elif m.group(3):
                off = 60 + 20 * (int(m.group(3)) - 1)
            else:
                off = 0
            if a.get("in_minutes") is not None:
                when = time.time() + float(a["in_minutes"]) * 60
            else:
                mm = re.fullmatch(r"\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", a.get("at") or "")
                if not mm:
                    return ok("Give at='HH:MM' or in_minutes.")
                lt = time.localtime()
                when = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(mm.group(1)), int(mm.group(2)),
                                    int(mm.group(3) or 0), 0, 0, -1))
            t0 = when - off * 60 * scale
            txt = await hub.clock.set_start("", int(a.get("scored_rounds") or sch.get("scored", 6)), scale, t0=t0)
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

        @tool("propose", "Put a note on the humans' board. The hub already makes the Build, Live and 'Analysis for <round>' "
              "notes; findings, research and suggested changes go INTO the round's analysis note (update_proposal with "
              "note= for progress, summary= for the high-level summary + numbered suggestions), not new notes. Use propose "
              "only for: kind='bot': ask the humans whether to use a bot ('Use v3 for Practice 2?'); give bot= the exact "
              "release file (e.g. 'releases/v3.zip'); greenlighting it makes that bot live. kind='question': something "
              "only a human can answer. headline: ONE plain-English sentence a tired human understands in 5 seconds. "
              "body: markdown with the evidence (numbers, ± error, files). deadline_minutes: when the default happens.",
              schema(["kind", "title", "headline", "body"], {"kind": "string", "title": "string", "headline": "string",
                                                             "body": "string", "bot": "string", "parent": "string",
                                                             "deadline_minutes": "number"}))
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
            if kind == "bot" and not a.get("bot"):
                return ok("Give bot= the exact release file (e.g. 'releases/v3.zip').")
            sch = hub.bus.shared.get("schedule")
            p = {"id": "P" + new_id()[1:7].upper(), "kind": kind, "title": a["title"][:160], "body": a["body"][:8000],
                 "headline": (a.get("headline") or "")[:300], "bot": a.get("bot") or None,
                 "author": me.name, "author_person": hub.person, "decider": "both" if kind == "bot" else hub.person,
                 "owner": me.name if me.name.endswith("overseer") else hub.owner_overseer(hub.person),
                 "parent": a.get("parent") or None, "stage": stage_of(sch, time.time()),
                 "status": "needs_call" if kind in ("bot", "question") else "running",
                 "created": time.time(), "thread": []}
            if a.get("deadline_minutes"):
                p["deadline"] = time.time() + float(a["deadline_minutes"]) * 60 * (sch or {}).get("scale", 1.0)
            if kind == "bot":
                await hub.register_bot(a["bot"], "ready", by=me.name)
            await hub.save_prop(p)
            me.record({"type": "note", "text": f"Posted note #{p['id']} ({kind}): {p['title']}"})
            return ok(f"Note #{p['id']} posted ({p['status']}). Wait for a human answer; you'll get a message.")

        @tool("record", "Write to the team ledger (what every agent sees, by priority). type: result (a measured claim: needs "
              "effect, se, n, method; players/stack/big_blind/hands_per_match if relevant: a result that contradicts the "
              "rules card is rejected) | method (how something is measured: table size, opponents, paired deals) | "
              "hypothesis (weak evidence; never present it as a finding) | commitment (who does what by when). "
              "depends_on: ledger ids it builds on (the card, a method). note: the board note it belongs to. file: where "
              "the detail is. Returns the id; cite ids, not copies.",
              schema(["type", "claim"], {"type": "string", "claim": "string", "effect": "number", "se": "number",
                                         "n": "integer", "unit": "string", "method": "string", "method_id": "string",
                                         "players": "integer", "stack": "number", "big_blind": "number",
                                         "hands_per_match": "integer", "bot": "string", "data": "string",
                                         "tags": "array", "depends_on": "array", "file": "string", "note": "string"}))
        async def record(a):
            if a.get("note"):
                a["note"] = a["note"].lstrip("#")
            iid, err = await hub.record_item(dict(a), me.name)
            if a.get("note"):
                me.turn_note_refs.add(a["note"])
            if iid:
                me.led_seen.add(iid)
            return ok(err or f"Recorded {iid} (proposed; s-skeptic validates what decisions rest on).")

        @tool("verify", "s-skeptic (or an Overseer in a pinch): mark a ledger item validated or disputed after RE-RUNNING it.",
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

        @tool("set_rules", "d-platform at minute 0 (s-skeptic checks it): the rules card every harness and result must match: "
              "players (per table), stack, big_blind, hands_per_match, time_per_decision, variant, notes. Also written to "
              "rules.json in the repo.",
              schema(["players"], {"players": "integer", "stack": "number", "big_blind": "number", "hands_per_match": "integer",
                                   "time_per_decision": "string", "variant": "string", "notes": "string"}))
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
            if not re.fullmatch(r"v\d+[a-z]?", bot_name(a["file"])):
                return ok("Bots are named v1, v2, ... (get one from next_bot_name); register 'releases/vN.zip'.")
            await hub.register_bot(a["file"], st, a.get("note") or "", me.name)
            return ok(f"{bot_name(a['file'])}: {st}.")

        @tool("update_proposal", "Update a note: note= a progress line or a result shown in its chat; summary= replaces the "
              "note's pinned summary (for an analysis note: the high-level picture in plain words + numbered suggestions "
              "for what to do); status planned / running / done / blocked.",
              schema(["id"], {"id": "string", "status": "string", "note": "string", "summary": "string"}))
        async def update_proposal(a):
            me.turn_note_refs.add(a["id"].lstrip("#"))
            p = hub.get_prop(a["id"].lstrip("#"))
            if not p:
                return ok("No such card.")
            st = a.get("status")
            if p.get("status") == "removed":
                return ok(f"Card #{p['id']} was removed from the board by a human; it's no longer relevant. Stop work on it.")
            if st in ("planned", "running", "done", "blocked"):
                p["status"] = st
            if a.get("summary"):
                p["body"] = a["summary"][:8000]
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

        return create_sdk_mcp_server("hub", tools=[send_message, list_agents, read_agent, set_status, notify_human,
                                                   start_agent, stop_agent, declare_live, set_schedule, propose,
                                                   update_proposal, list_proposals, codex_task, register_bot,
                                                   record, verify, invalidate, set_rules, ledger, next_bot_name])


# ======================================================================== playbook (START_HERE.md section 6)
BUILD = [  # (minute, who, what) for the build hour
    (0, "both", "Variant announced: fetch the kit, read the Format page (weights, payouts, anything unusual). d-overseer starts d-platform on Part 1 with TWIST_NOTES.md."),
    (10, "dylan", "A minimal legal bot must be uploaded and confirmed active by now."),
    (15, "both", "Test rig running (Part 3a: paired runs, sparring). Samuel's side measures every candidate."),
    (20, "dylan", "Practice round 1 plays style A (a different style each practice round)."),
    (30, "dylan", "Practice round 2 plays style B."),
    (40, "dylan", "Practice round 3 plays style C."),
    (50, "both", "Practice round 4 re-plays the leader. Then hands off: the best real-field scorer is active for scored round 1."),
]
WINDOW = [  # (minutes before a scored round, who, what)
    (20, "both", "The previous scored round has started. The challenger should already be packed and tested."),
    (13, "both", "The previous scored round's result and hand data land about now. Samuel's side: run the round loop (Data on leaks/opponents, Tester on pending candidates). Dylan's side: challenger ready."),
    (12, "dylan", "Upload the challenger and confirm it is active (it plays the practice round). Skip if not ready."),
    (10, "both", "Practice round starts and plays the challenger."),
    (9, "dylan", "Put the live bot back as active straight away."),
    (8, "both", "DECIDE: live bot, live bot + this window's one tested change, or the challenger. s-overseer's recommendation is due to d-overseer now."),
    (6, "dylan", "Test the chosen bot under upload-test conditions (no time bank)."),
    (5, "both", "No decision by now means the live bot plays; no upload."),
    (3, "dylan", "Upload the chosen bot and confirm the active bot on the portal. After this, nothing changes."),
]


# What each Overseer dispatches at each step: (person, priority, agent, task). "crit" is the critical path;
# "opt" is worth doing only when on track (drop it first when behind). Keys: b<minute> (build hour) and
# T<minutes before a scored round>. Prompt-pack parts refer to FIRST_PROMPT.md.
DISPATCH = {
    "b0": [("dylan", "crit", "d-platform", "set_rules first (players per table, stacks, blinds, hands per match, time limits) from the kit and Format page, then FIRST_PROMPT.md Part 1 with TWIST_NOTES.md: minimal legal bot in bot/ and releases/v1.zip by minute 10; test harness by 15; today's hand ranking and the twist's value by 20; then the shared platform with every Part 1 check passing"),
           ("dylan", "crit", "d-builder", "Read Part 1 (styles) and TWIST_NOTES.md; draft styles A (wide pressure), B (shove-heavy), C (tight, fold <=75% to re-raises) as settings; build them on Platform's interface as soon as it's published"),
           ("samuel", "crit", "s-tester", "Part 3a: paired runner on identical deals plus sparring bots, running by minute 15"),
           ("samuel", "crit", "s-pipeline", "Parsers for today's hand-history format and analysis/roundcard.py (round card in <60 s); test it on practice 1"),
           ("samuel", "crit", "s-skeptic", "Check the rules card against the kit and Format page as soon as d-platform sets it; then check the test rig's method (table size, paired deals, seat rotation)"),
           ("samuel", "opt", "s-data", "Read the Format page and twist; list the questions each round's analysis must answer today")],
    "b10": [("dylan", "crit", "d-platform", "v1 must be released (releases/v1.zip) and Dylan told to upload it now if not done")],
    "b15": [("samuel", "crit", "s-tester", "Test rig must run now: first verdict on v1 (correct? timing?)")],
    "b20": [("dylan", "crit", "d-builder", "Style A ready (tested by s-tester) for practice round 1; B next"),
            ("samuel", "crit", "s-data", "When practice 1's round card lands: leaks of the bot that played (Part 2), top change in 5 minutes")],
    "b30": [("dylan", "crit", "d-builder", "Style B for practice 2; C next"),
            ("samuel", "crit", "s-data", "Practice 2 leaks; compare styles A vs B on the real field"),
            ("samuel", "opt", "s-data", "Opponent profiles (Part 4) from practice rounds so far")],
    "b40": [("dylan", "crit", "d-builder", "Style C for practice 3"),
            ("samuel", "crit", "s-tester", "Rank A, B, C (paired tests + real practice scores) for the round-1 choice")],
    "b50": [("dylan", "crit", "d-platform", "Release the best real-field scorer as the live bot for scored round 1"),
            ("samuel", "crit", "s-data", "Which style did the field reward? One paragraph for the round-1 decision")],
    "T13": [("samuel", "crit", "s-data", "As soon as DATA LANDED (not before; if it hasn't, wait for it), from the round card (s-pipeline writes it within a minute of the data): our leaks first (Part 2), one recommended change with size, z and n, recorded in the ledger"),
            ("samuel", "crit", "s-skeptic", "Re-run the numbers behind every proposed result the T-8 decision may rest on (card headline, s-tester verdicts, s-data's change); verify each"),
            ("samuel", "crit", "s-tester", "Verdict on every pending candidate: correct? and paired test vs the live bot"),
            ("samuel", "opt", "s-data", "Opponent profiles and counters (Part 4)"),
            ("samuel", "opt", "s-tester", "Cloned field on Modal (Part 3b) for the challenger"),
            ("dylan", "crit", "d-builder", "Challenger packed and tested, ready for the T-12 upload"),
            ("dylan", "crit", "d-platform", "Fix bugs s-tester reported; build this window's one tested change on the live bot")],
    "T20": [("samuel", "crit", "s-skeptic", "Verify the challenger's paired-test verdicts and methods now (they don't depend on the new round), so only the new round's card is left to check at T-13"),
            ("dylan", "crit", "d-overseer", "Draft the 'Which bot?' note for the next scored round now (default: the live bot); fill in the evidence as it lands")],
    "T12": [("dylan", "crit", "d-platform", "Release the challenger (releases/<name>.zip) so Dylan can upload it for the practice round")],
    "T8": [("samuel", "crit", "s-overseer", "Send d-overseer the recommendation now (live / live + one tested change / challenger) with evidence"),
           ("dylan", "crit", "d-overseer", "Post the live-bot decision card now (deadline_minutes until T-5)")],
    "T6": [("dylan", "crit", "d-platform", "Test the chosen bot with no time bank; release it as releases/<name>.zip")],
    "T3": [("dylan", "crit", "d-platform", "The greenlit bot's release must be ready; Dylan uploads it now")],
}
# checkpoints the Overseer compares against reality every turn (person, key, what must be true by then)
CHECKPOINTS = [
    ("dylan", "b10", "a legal bot is uploaded and active"), ("samuel", "b15", "the test rig gives verdicts"),
    ("dylan", "b20", "today's ranking and twist value exist; style A is tested"), ("dylan", "b40", "styles A, B, C all tested"),
    ("dylan", "T12", "the challenger is packed and tested"), ("samuel", "T8", "the recommendation is with d-overseer"),
    ("dylan", "T8", "the decision card is posted"), ("dylan", "T3", "the chosen bot's release is ready"),
    ("dylan", "b10", "the rules card is set (players per table, stacks, blinds)"),
    ("samuel", "T12", "the round card for the round that just landed is written"),
    ("samuel", "T8", "the recommendation is with d-overseer, citing ledger ids (validated preferred; none disputed)"),
]


# How wide each dispatched job should fan out (effort scaling: the lead sets the budget, the worker splits).
FANOUT = {
    "d-platform": "fan out: one subagent per independent piece (engine adapter / hand ranking / packaging+checks); Sonnet for packaging and scripts",
    "d-builder": "fan out: one subagent per style or candidate, in parallel, each in its own folder; Modal (up to 20) for sparring each",
    "s-tester": "fan out: shard paired runs across Modal (up to 40 containers); one subagent per candidate for the 'correct?' review",
    "s-data": "fan out: one subagent per question (our leaks / each top-5 opponent / the twist), Sonnet for counting; Codex for a second-opinion check",
    "s-pipeline": "fan out: at most 2 Sonnet subagents (parser / card); keep the card script under 60 s",
    "s-skeptic": "fan out: 1-2 subagents plus one Codex re-implementation for numbers that matter; 2 minutes per item before T-8",
    "s-overseer": "", "d-overseer": "",
}


def dispatch_text(key: str, person: str) -> str:
    rows = [(pr, ag, t) for (who, pr, ag, t) in DISPATCH.get(key, []) if who == person]
    if not rows:
        return ""
    extra = ("\nThe board now has a 'Build i of 4' note for each work stream (ids B1-B4 + the clock key). Progress is posted "
             "there automatically from what you say and do; when a stream is finished, update_proposal(id, status='done', "
             "summary=...)." if key == "b0" else "")
    return extra + "\nDispatch now (task messages; optional ones only if on track):\n" + "\n".join(
        f"- [{'CRITICAL' if pr == 'crit' else 'optional'}] {ag}: {t}" + (f" ({FANOUT[ag]})" if FANOUT.get(ag) else "")
        for pr, ag, t in rows)


# steps a person does with their own hands (clock reminders shown to that person)
HUMAN_STEPS = {
    "b0": {"samuel": "Set the clock's minute 0 if it isn't set, and read the Format page.",
           "dylan": "Fetch the kit and read the Format page."},
    "b10": {"dylan": "UPLOAD"},
    "b20": {"dylan": "UPLOAD"},
    "b30": {"dylan": "UPLOAD"},
    "b40": {"dylan": "UPLOAD"},
    "12": {"dylan": "UPLOAD"},
    "9": {"dylan": "UPLOAD"},
    "8": {"samuel": "Decision time: open the Use-which-bot note on the board and greenlight or reject.",
          "dylan": "Decision time: open the Use-which-bot note on the board and greenlight or reject."},
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
        rounds = [t0 + (60 + 20 * (k - 1)) * U for k in range(1, nsc + 1)]
        if m < 0:
            lines.append(f"PHASE: before the event; minute 0 is at {hhmm(t0)} (in {-m:.0f} min).")
        elif m < 60:
            done = [f"min {mi}: {w}" for mi, who, w in BUILD if mi <= m and who in ("both", me)]
            nxt = next(((mi, w) for mi, who, w in BUILD if mi > m and who in ("both", me)), None)
            lines.append(f"PHASE: build hour, minute {m:.0f} of 60. Scored round 1 at {hhmm(rounds[0])}.")
            if done:
                lines.append("Should be done by now: " + " | ".join(done[-2:]))
            if nxt:
                lines.append(f"Next (minute {nxt[0]}, {hhmm(t0 + nxt[0] * U)}): {nxt[1]}")
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
                lines.append(f"PHASE: window before scored round {k} (weight x{k}) at {hhmm(ts)}: T-{math.ceil(T)} min.")
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
                at = t0 + int(key[1:]) * U2
                if at <= now < t0 + 60 * U2:
                    due.append(f"by minute {key[1:]}: {what}")
            else:
                off = int(key[1:])
                for k in range(1, nsc + 1):
                    ts = t0 + (60 + 20 * (k - 1)) * U2
                    if ts - off * U2 <= now < ts:
                        due.append(f"by T-{off} of scored round {k}: {what}")
        if due:
            lines.append("Checkpoints that should be TRUE now (check against your workers' briefs): " + "; ".join(due) +
                         ". If any isn't, you're behind: drop optional work, put every worker on the critical path, "
                         "and say so in your brief.")
    if sch:   # who is free right now, on both laptops, so idle capacity gets used
        now2, load = time.time(), []
        for a in hub.agents.values():
            if not a.name.endswith(("overseer", "overview")):
                load.append((a.name, a.state, a.task, a.idle_since))
        for n, v in hub.bus.directory.items():
            if v.get("person") != me and not v.get("service") and not n.endswith(("overseer", "overview")) and now2 - v.get("seen", 0) < 120:
                load.append((n, v.get("state"), v.get("task"), v.get("idle_since")))
        idle = [n for n, st, t, since in load if st in ("idle", "done") and (not since or now2 - since > 60)]
        lines.append("Team load: " + "; ".join(f"{n} {st}" + (f" ({(t or '')[:60]})" if st == 'working' and t else "")
                                              for n, st, t, _ in load) + ".")
        if idle:
            lines.append(f"IDLE NOW: {', '.join(idle)} (skip any whose brief says it's waiting on a background Modal/Codex job). Idle agents are wasted time: give each a slice of the critical path "
                         "(split the biggest job: one candidate, one analysis, one test shard each), or the next optional item "
                         "if you're on track. Message the other Overseer if the idle agent is theirs.")
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

    def events(self):
        s = self.hub.bus.shared.get("schedule")
        if not s:
            return []
        t0, out, U = s["start"], [], 60 * s.get("scale", 1.0)
        for k, m in enumerate((20, 30, 40, 50), 1):
            out.append(("practice", k, t0 + m * U))
        for k in range(1, s.get("scored", 6) + 1):
            ts = t0 + (60 + 20 * (k - 1)) * U
            out.append(("scored", k, ts))
            if k < s.get("scored", 6):
                out.append(("practice", 4 + k, ts + 10 * U))
        return sorted(out, key=lambda e: e[2])

    async def set_start(self, hhmm_s: str, scored: int = 6, scale: float = 1.0, t0: float | None = None):
        if t0 is None:
            m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*", hhmm_s or "")
            if not m:
                raise ValueError("use HH:MM")
            lt = time.localtime()
            t0 = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), 0, 0, -1))
        await self.hub.bus.set_shared("schedule", {"start": t0, "scored": scored, "scale": scale,
                                                   "set_by": self.hub.person, "at": time.time()})
        self.sent = set()
        self.hub.emit("shared", {"schedule": self.hub.bus.shared["schedule"]})
        for al in list(self.hub.alerts):   # notices asking for the start time are now answered
            if re.search(r"minute 0|set the clock|no clock", al["text"], re.I):
                self.hub.dismiss(al["id"])
        U = 60 * scale
        return f"minute 0 at {hhmm(t0)}; scored round 1 at {hhmm(t0 + 60 * U)}; last scored round at {hhmm(t0 + (60 + 20 * (scored - 1)) * U)}."

    def next_step(self):
        """The next clock step for this laptop's person: (epoch, text) or None."""
        s = self.hub.bus.shared.get("schedule")
        if not s:
            return None
        now, me = time.time(), self.hub.person
        t0, U = s["start"], 60 * s.get("scale", 1.0)
        cands = [(t0 + mi * U, f"min {mi}: {w}") for mi, who, w in BUILD if who in ("both", me)]
        for k in range(1, s.get("scored", 6) + 1):
            ts = t0 + (60 + 20 * (k - 1)) * U
            cands += [(ts - o * U, f"Scored {k} T-{o}: {w}") for o, who, w in WINDOW
                      if who in ("both", me) and o != 20 and not (k == 1 and o > 8)]
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

    async def loop(self):
        while True:
            try:
                await self.tick()
                await self.hub.expire_decisions()
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(10)

    async def tick(self):
        now = time.time()
        ov = self.hub.overseer()
        me = self.hub.person
        s = self.hub.bus.shared.get("schedule")
        marks = []
        if s:
            t0, U = s["start"], 60 * s.get("scale", 1.0)
            tk = int(t0)
            for mi, who, w in BUILD:
                if who in ("both", me) or dispatch_text(f"b{mi}", me):
                    marks.append((f"{tk}:b{mi}", t0 + mi * U, f"Build hour, minute {mi}: {w}" + dispatch_text(f"b{mi}", me)))
            for k in range(1, s.get("scored", 6) + 1):
                ts = t0 + (60 + 20 * (k - 1)) * U
                for o, who, w in WINDOW:
                    if (who in ("both", me) or dispatch_text(f"T{o}", me)) and not (k == 1 and o > 8):   # round 1: the build hour covers T-20..T-9
                        marks.append((f"{tk}:s{k}-{o}", ts - o * U, f"Scored round {k} at {hhmm(ts)}, T-{o}: {w}" + dispatch_text(f"T{o}", me)))
        if s:   # a regular check-in every 5 event-minutes from minute 0 to the end of the last round
            t0, U = s["start"], 60 * s.get("scale", 1.0)
            end = t0 + (60 + 20 * (s.get("scored", 6) - 1) + 10) * U
            n = int((now - t0) // (5 * U))
            if t0 <= now < end:
                marks.append((f"{int(t0)}:p{n}", t0 + n * 5 * U, "Regular clock check. Re-read the situation brief: is "
                              "everything for the current and next step on track? Nudge your workers or tell your human if not; "
                              "if all is on track, just update set_status (no messages needed)."))
        for key, at, text in marks:
            if key not in self.sent and at <= now < at + max(60, 2 * (60 * (s or {}).get("scale", 1.0))):
                self.sent.add(key)
                atomic_write(self.hub.data / "clock_sent.json", json.dumps(sorted(self.sent)))
                if key.endswith(":b0"):
                    await self.hub.build_notes(int(key.split(":")[0]))
                await ov.add_item({"kind": "clock", "wake": not key.split(":", 1)[1].startswith("p"), "text": text,
                                   "urgent": key.endswith(("-13", "-8", "-3"))})
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
        if s:   # the clock may have been set on the other laptop: clear "need minute 0" notices here too
            for al in list(self.hub.alerts):
                if re.search(r"minute 0|set the clock|no clock", al["text"], re.I):
                    self.hub.dismiss(al["id"])
        self.hub.set_service(f"{me[0]}-clock", "Clock", "working" if s else "idle", self.next_text())


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
        self.fails = 0
        self.small_only = small_only   # on a phone hotspot: only the first-1000 file, to save data
        self.team = self.cid = None
        self.want_cid = os.environ.get("AVALON_COMPETITION_ID") or None
        self.comp_name, self.team_name = "", "avalon"
        self.checked: set[str] = set(self.st.get("checked", []))

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

    async def loop(self):
        while True:
            fast = False
            try:
                fast = await self.poll()
                self.fails = 0
            except Exception as e:  # noqa: BLE001
                self.fails += 1
                self.hub.set_service("s-portal", "Portal", "error", f"Portal not answering ({type(e).__name__}); retrying")
                if self.fails == 3:
                    await self.hub.add_alert("s-portal", "The portal has not answered for 3 checks in a row.", True)
            live = self.hub.bus.shared.get("live") or {}
            act = self.hub.bus.shared.get("portal_active") or {}
            waiting = live.get("filename") and norm_bot(live.get("filename")) != norm_bot(act.get("filename")) and time.time() - live.get("at", 0) < 1800
            await asyncio.sleep(10 if waiting else 30 if fast else 60)   # an upload is pending: confirm it fast

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
        rounds = (await self.aget(f"/competitions/{self.cid}/tournaments"))["items"]
        counts: dict[str, int] = {}
        for r in sorted(rounds, key=lambda r: r["created_at"]):   # the real portal has no labels: name them
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
            r.setdefault("label", f"{'Scored' if r['kind'] != 'practice' else 'Practice'} round {counts[r['kind']]}"
                                  + (f" (x{r['weight']})" if r.get("weight") else ""))
            r["stage"] = stage_of_round(r["kind"], counts[r["kind"]])
        new_done = [r for r in rounds if r.get("completed_at") and r["id"] not in self.st["done"]]
        if not self.st.get("baseline_done"):
            self.st["baseline_done"] = True
            if new_done:   # rounds that finished before this hub started: one catch-up note, not N "new" rounds
                for r in sorted(new_done, key=lambda r: r["created_at"]):
                    await self.landed(r, quiet=True)
                ov = self.hub.agents.get("s-overseer")
                if ov:
                    await ov.add_item({"kind": "portal", "wake": True, "text": (
                        f"Catch-up: {len(new_done)} round(s) had already finished before I started; their results and our "
                        f"hand data are saved under {self.out}/ (one folder per round). These are NOT new rounds; check "
                        "PLAN-samuel.md / data/RATES.md for what has already been analysed before assigning work.")})
                new_done = []
        for r in sorted(new_done, key=lambda r: r["created_at"]):
            try:
                await self.landed(r)
            except Exception as e:  # noqa: BLE001
                self.st["done"].append(r["id"])
                await self.hub.add_alert("s-portal", f"Couldn't process the result of {r.get('label', r['id'])} "
                                         f"({type(e).__name__}: {e}); tell your Overseer to look at the portal directly.", True)
        await self.retry_hands()
        standings = (await self.aget(f"/competitions/{self.cid}/standings"))["items"]
        self.st["standings"] = standings
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
        for r in rounds:   # a round that is playing gets a "<bot> live · <stage>" note
            if not r.get("completed_at"):
                f = cur["filename"] or "no bot"
                await self.hub.ensure_note("L-" + r["id"][:12], kind="live", stage=r["stage"], owner="d-overseer",
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
        return bool(running)

    async def landed(self, r, quiet: bool = False):
        res = await self.aget(f"/tournaments/{r['id']}/results")
        label = r.get("label") or f"{r['kind']} {r['created_at'][11:16]}"
        n = len(self.st["done"]) + 1
        folder = self.out / f"{n:02d}-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "results.json").write_text(json.dumps(res, indent=1))
        files = await self.fetch_hands(r["id"], folder, small_first=True)
        if not files:
            self.st["need_hands"][r["id"]] = {"folder": str(folder), "label": label, "since": time.time()}
        elif not self.small_only:
            asyncio.create_task(self.fetch_hands(r["id"], folder))   # the full file, off the critical path
        self.hub.last_landed = time.time()
        items = sorted(res["items"], key=lambda x: -(x.get("average_points") or 0))
        stage = r.get("stage") or label
        aid = "A-" + r["id"][:12]
        self.st.setdefault("note_of", {})[r["id"]] = aid
        await self.hub.ensure_note(aid, kind="analysis", stage=stage, owner="s-overseer", author="s-portal",
                                   author_person="samuel", title=f"Analysis for {stage}", status="running")
        ours = next((i for i, x in enumerate(items, 1) if x["team_name"] == self.team_name), None)
        me = items[ours - 1] if ours else None
        line = (f"{label} finished: we were {ours} of {len(items)} with {(me.get('average_points') or 0):.2f} "
                f"(±{me.get('margin_of_error') or 0:.2f}); 1st {items[0]['team_name']} {(items[0].get('average_points') or 0):.2f}."
                if me else f"{label} finished (we had no result: forfeit?).")
        paths = f"\nResults: {folder}/results.json" + "".join(f"\nHands: {p}" for p in files) + \
                ("" if files else "\nHand history not downloadable yet; I'll keep trying.")
        self.st["done"].append(r["id"])
        self.save()
        await self.hub.note_append(aid, "Portal", line + " " + (f"Hand data downloaded ({', '.join(Path(f).name for f in files)}). "
                                   "Analysis starting." if files else "Hand data isn't downloadable yet; I'll keep trying."))
        lid = "L-" + r["id"][:12]
        if self.hub.get_prop(lid):
            await self.hub.note_append(lid, "Portal", line, status="done")
        if quiet:
            return
        card = await self.run_card(folder, stage) if files else ""
        pl = self.hub.agents.get("s-pipeline")
        if pl:   # standing order: numbers first, no Overseer hop (the decision window is only 5 minutes)
            await pl.add_item({"kind": "portal", "wake": True, "urgent": True, "note": aid, "text": (
                f"DATA LANDED for {stage}. {line}{paths}\n" + (f"The hub already ran analysis/roundcard.py:\n{card}\nCheck it, "
                "record the headline numbers, and fyi s-overseer, s-data and s-skeptic. " if card else "") +
                "Run the round card now (analysis/roundcard.py), write "
                f"analysis/{re.sub(r'[^A-Za-z0-9.]+', '-', stage)}/card.md, record the headline numbers as results (note='{aid}'), "
                "and fyi s-overseer and s-data with the path. Finish within 2 minutes.")})
            if pl.state == "stopped" and not pl.paused:
                await pl.start()
        ov = self.hub.agents.get("s-overseer")
        if ov:   # the Overseer decides what to do with it and dispatches the workers with context
            await ov.add_item({"kind": "portal", "wake": True, "urgent": True, "note": aid, "text": "NEW ROUND RESULT. " + line + paths +
                               f"\nThe humans follow this round on note #{aid} \"Analysis for {stage}\": your progress there is "
                               "posted automatically from what you say and do. When you have the picture, set its summary "
                               f"with update_proposal(id='{aid}', summary=...): the high-level story in plain words, then "
                               "numbered suggestions for what to do. Keep adding results there as they come in."})
            if ov.state == "stopped" and not ov.paused:
                await ov.start()
        await self.tell("d-overseer", "fyi", line)
        self.hub.set_service("s-portal", "Portal", "working", line)

    async def run_card(self, folder: Path, stage: str) -> str:
        """If the pipeline's round-card script exists (built and tested in the build hour), run it at once, so the
        numbers exist before any agent has taken a turn."""
        script = self.hub.repo / "analysis" / "roundcard.py"
        if not script.exists():
            return ""
        py = self.hub.repo / ".venv" / "bin" / "python"
        try:
            proc = await asyncio.create_subprocess_exec(
                str(py if py.exists() else "python3"), "-I", "-c",
                "import runpy, sys; sys.path.insert(0, sys.argv[1]); sys.argv = sys.argv[2:]; "
                "runpy.run_path(sys.argv[0], run_name='__main__')",
                str(script.parent), str(script), str(folder), cwd=str(self.hub.repo),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "AVALON_STAGE": stage})
            out, _ = await asyncio.wait_for(proc.communicate(), 90)
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
                data = await self.aget(self.hands_url.replace("{tid}", tid).replace("{q}", q), raw=True)
                if data[:2] == b"\x1f\x8b" and len(data) > 100:
                    p.write_bytes(data)
                    files.append(str(p))
            except Exception:  # noqa: BLE001
                pass
        return files

    async def retry_hands(self):
        for tid, info in list(self.st["need_hands"].items()):
            files = await self.fetch_hands(tid, Path(info["folder"]))
            if files:
                del self.st["need_hands"][tid]
                self.save()
                aid = self.st.get("note_of", {}).get(tid)
                if aid:
                    await self.hub.note_append(aid, "Portal", f"Hand data downloaded ({', '.join(Path(f).name for f in files)}). "
                                               "Analysis starting.")
                pl = self.hub.agents.get("s-pipeline")
                if pl:
                    await pl.add_item({"kind": "portal", "wake": True, "note": aid, "text": f"DATA LANDED (late) for "
                                       f"{info['label']}: " + " ".join(files) + ". Run the round card now."})
                ov = self.hub.agents.get("s-overseer")
                if ov:
                    await ov.add_item({"kind": "portal", "wake": True, "text": f"Hand history for {info['label']} is now "
                                       "saved:\n" + "\n".join(f"Hands: {f}" for f in files)})
            elif time.time() - info["since"] > 1200 and not info.get("warned"):
                info["warned"] = True
                self.save()
                await self.hub.add_alert("s-portal", f"The hand history for {info['label']} still can't be downloaded after "
                                         "20 minutes. On the real portal, copy the download link from the team page and "
                                         "restart the hub with --hands-url.", True)

    async def tell(self, to: str, kind: str, text: str):
        try:
            await self.hub.bus.send({"id": new_id(), "from": "s-portal", "from_kind": "hub", "to": to, "kind": kind,
                                     "text": text})
        except Exception:  # noqa: BLE001
            pass

    async def check_team(self, team: dict):
        for s in team.get("submissions") or []:
            if s["id"] in self.st["subs"]:
                continue
            if s["status"] in ("ready", "rejected"):
                self.st["subs"].append(s["id"])
                if s["status"] == "rejected":
                    text = f"Upload {s['filename']} was REJECTED by the portal: {s.get('rejection_reason')}. The previous bot stays active."
                    await self.hub.alert_all("s-portal", text, True)
                    await self.tell("d-overseer", "question", text)
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
                           f"d-overseer declared {live['filename']}.")
                else:
                    continue
                await self.hub.alert_all("s-portal", msg, True)
                await self.tell("d-overseer", "question", msg)


# ======================================================================== web
def make_app(hub: Hub) -> web.Application:
    app = web.Application(client_max_size=2 * 1024 * 1024)
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
        if req.method == "POST" and not req.content_type.startswith("application/json"):
            raise web.HTTPForbidden(text="JSON only")
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
        s = await hub.clock.set_start("", 6, hub.default_scale, t0=time.time())
        ov = hub.overseer()
        await ov.human("Start building: the variant is announced now (minute 0). Kick off the build-hour plan.",
                       PEOPLE[hub.person])
        return web.json_response({"ok": True, "text": s})

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
    r.add_post("/api/props", new_prop)
    r.add_post("/api/props/{id}/act", act_prop)
    return app


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
    ap.add_argument("--start", default=None, help="event minute 0 as HH:MM[:SS] (sets the shared clock)")
    ap.add_argument("--scale", type=float, default=1.0, help="simulations only: event-minutes run this fast (0.25 = 4x)")
    ap.add_argument("--portal-base", default=None, help="portal API base, e.g. http://127.0.0.1:8765/tournament/api")
    ap.add_argument("--portal-key-file", default=None)
    ap.add_argument("--codex-model", default=None, help="Codex model for codex_task jobs (default: Codex's own)")
    ap.add_argument("--codex-max", type=int, default=3, help="Codex jobs running at once")
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
    for pr in hub.local_props.values():   # re-share this laptop's notes (e.g. after a restart), merged with the remote copy
        other = hub.bus.shared.get("prop:" + pr["id"])
        merged = merge_note(other, pr) if isinstance(other, dict) else pr
        if merged != other:
            asyncio.create_task(hub.bus.set_shared("prop:" + pr["id"], merged))
    hub.default_scale = a.scale
    hub.bus.scale = a.scale
    if a.start:
        await hub.clock.set_start(a.start, scale=a.scale)
    if not a.view_only:
        asyncio.create_task(hub.clock.loop())
        asyncio.create_task(hub.scan_releases())
        asyncio.create_task(hub.watch_live())
    if not a.no_codex and not a.view_only:
        hub.codex = Codex(hub, a.codex_model, a.codex_max)
        hub.codex.status()
    if a.portal_base and a.portal_key_file and not a.view_only:
        hub.portal = PortalWatcher(hub, a.portal_base, Path(a.portal_key_file), a.hands_url,
                                   Path(a.portal_data) if a.portal_data else None, a.small_hands)
        asyncio.create_task(hub.portal.loop())
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
                                          "idle_since": ag.idle_since})
                ag.save_meta()
            if hub.bus.outbox and hub.bus.oldest_unsent_age() > 120:
                await hub.add_alert("hub", "Messages to the other laptop have been waiting over 2 minutes: the link "
                                    "is down. Talk to your teammate directly until it's back.", True)
    asyncio.create_task(heartbeat())
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
