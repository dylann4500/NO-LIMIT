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
from claude_agent_sdk import (HookMatcher, AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
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
    r"\bdd\s+if=", r">\s*/dev/sd", r"\b(p?kill|killall)\b", r"\bkill\s+-9",
    r"modal\s+(app\s+(stop|delete)|volume\s+(rm|delete)|secret\s+delete)",
    r"(pokerbot\.sequoiacap\.com|/tournament/api)[^\n]*(-X\s*(POST|PATCH|PUT|DELETE)|--data|\s-d\s)",
    r"(-X\s*(POST|PATCH|PUT|DELETE)|--data|\s-d\s)[^\n]*(pokerbot\.sequoiacap\.com|/tournament/api)",
    r"\.(post|patch|put|delete)\([^\n]*(sequoiacap|tournament/api)",
]))
HUB_TOOLS = ["send_message", "list_agents", "read_agent", "set_status", "notify_human", "start_agent", "stop_agent",
             "declare_live", "set_schedule", "propose", "update_proposal", "list_proposals", "codex_task"]
API_KEY_FILE = Path.home() / ".config" / "avalon-hub" / "anthropic-api-key"
KINDS = ("idea", "research", "finding", "change", "decision")
OPEN = ("new", "planned", "running", "needs_call", "revise")
COMPACT_AT_OVERSEER = int(os.environ.get("AVALON_COMPACT_AT", 180_000))   # tokens of context; above this, compact between turns (outside the T-9..T-2 crunch)
COMPACT_AT_WORKER = int(os.environ.get("AVALON_COMPACT_AT", 250_000))
COMPACT_KEEP = ("Summarize for yourself to continue the day without loss. Keep, exactly: your role and current "
                "assignments; the event phase and schedule; the declared live bot (exact file) and every candidate "
                "with its status, test results and file path; every human decision and instruction, near-verbatim; "
                "open notes on the board by id; numbers from analyses with sample sizes and confidence; what is "
                "running where (subagents, Modal app ids, Codex job ids) and where results will land; promises you "
                "made to other agents; open questions. Drop: raw tool output, logs, superseded plans, chit-chat.")
LIMIT_RX = re.compile(r"usage limit|rate.?limit|overloaded|429|quota|limit reached|too many requests", re.I)
APPROVAL_TIMEOUT = 180


class LimitHit(Exception):
    pass
EVENT_CAP = 4000


def same_bot(declared: str, active: str) -> bool:
    """Compare a declared live-bot name with the portal's active file name, ignoring folders and .zip."""
    norm = lambda x: re.sub(r"\.zip$", "", (x or "").strip().split("/")[-1].lower())   # noqa: E731
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
            if v["id"] not in out or v.get("updated", 0) >= out[v["id"]].get("updated", 0):
                out[v["id"]] = v
        return sorted(out.values(), key=lambda p: p.get("updated", 0), reverse=True)

    def get_prop(self, pid: str) -> dict | None:
        return next((p for p in self.props() if p["id"] == pid), None)

    async def save_prop(self, p: dict):
        p["updated"] = time.time()
        self.local_props[p["id"]] = p
        self.bus.shared["prop:" + p["id"]] = p
        atomic_write(self.data / "props.json", json.dumps(self.local_props))
        self.emit("prop", {"prop": p})
        await self.bus.set_shared("prop:" + p["id"], p)

    def owner_overseer(self, person: str) -> str:
        return ("s-" if person == "samuel" else "d-") + "overseer"

    async def human_act(self, pid: str, action: str, text: str) -> dict:
        p = self.get_prop(pid)
        if not p:
            raise ValueError("That card no longer exists.")
        who = PEOPLE[self.person]
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": action, "text": text})
        target = p.get("owner") or p.get("author")
        if action == "approve":
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
            note = (f"{who} removed #{p['id']} \"{p['title']}\" from the board: no longer relevant. Stop any work on it "
                    "and tell the agents you gave it to." if was in OPEN or was == "blocked" else "")
        elif action == "close":
            p["status"] = "done"
            note = f"{who} closed #{p['id']} \"{p['title']}\"." + (f" {text}" if text else "")
        else:
            raise ValueError("unknown action")
        await self.save_prop(p)
        if note and target and target.startswith(("s-", "d-")):
            try:
                await self.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": target, "kind": "task",
                                     "text": note + " (Update the card with update_proposal.)"})
            except Exception:  # noqa: BLE001
                pass
        return p

    async def card_ask(self, pid: str, text: str) -> dict:
        p = self.get_prop(pid)
        if not p:
            raise ValueError("That card no longer exists.")
        who = PEOPLE[self.person]
        p.setdefault("thread", []).append({"who": who, "at": time.time(), "action": "ask", "text": text})
        await self.save_prop(p)
        ov = self.owner_overseer(p.get("author_person") or self.person)
        await self.bus.send({"id": new_id(), "from": who, "from_kind": "human", "to": ov, "kind": "task", "text": (
            f"[card #{p['id']} chat] {who} says about \"{p['title']}\": {text}\n\nAnswer in the card's chat with "
            f"update_proposal(id='{p['id']}', note=<your answer>) (keep it short and plain). If it's an instruction, "
            "route it to the right agent and say so in the note.")})
        return p

    async def new_idea(self, title: str, body: str, for_person: str) -> dict:
        p = {"id": "P" + new_id()[1:7].upper(), "kind": "idea", "title": title[:160], "body": body[:6000],
             "author": PEOPLE[self.person], "author_person": self.person, "owner": self.owner_overseer(for_person),
             "status": "new", "created": time.time(), "thread": []}
        await self.save_prop(p)
        await self.bus.send({"id": new_id(), "from": PEOPLE[self.person], "from_kind": "human", "to": p["owner"],
                             "kind": "task", "text": (
            f"NEW IDEA from {PEOPLE[self.person]} (card #{p['id']}): {p['title']}\n{body}\n\nHuman ideas come first. "
            f"Plan it, mark the card planned/running with update_proposal (say what runs where), run it with your workers "
            f"/ subagents / Modal, and post what you found with propose(kind='finding', parent='{p['id']}'). If it "
            "implies a change to the bot, propose that as kind='change' for a greenlight.")})
        return p

    async def expire_decisions(self):
        now = time.time()
        for p in self.props():
            if p.get("status") == "needs_call" and p.get("deadline") and now > p["deadline"] and \
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
        self.human_in_turn = False
        self.last_need = ""
        self.idle_since: float | None = None
        self.digest_seen: dict[str, int] = {}
        self.digest_full = True          # first turn after (re)start: the whole team picture
        self.context_tokens = 0
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

    def record(self, ev: dict):
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
        if item.get("wake", True):
            self.wake.set()
        self.hub.emit("agent", self.view())

    async def receive(self, msg: dict):
        kind = msg.get("kind") or "question"
        self.record({"type": "msg_in", "from": msg["from"], "text": msg["text"], "id": msg["id"],
                     "kind": kind, "reply_to": msg.get("reply_to"), "from_kind": msg.get("from_kind")})
        await self.add_item({"kind": "msg", "wake": kind not in ("fyi", "answer_to_answer"), **msg})
        if self.state == "stopped" and not self.paused and kind != "fyi":
            await self.start()

    async def human(self, text: str, who: str):
        self.record({"type": "user", "text": text, "from": who, "queued": self.state in ("working", "waiting")})
        await self.add_item({"kind": "human", "from": who, "text": text})
        if self.state == "stopped":
            self.paused = False
            await self.start()

    def team_digest(self) -> str:
        """Every other agent's brief (both laptops) that changed since this agent's last turn, so context flows
        between agents automatically. After a compaction, all of them."""
        full = self.digest_full
        self.digest_full = False
        rows = [(a.name, a.title, a.state, a.summary) for a in self.hub.agents.values() if a is not self]
        rows += [(n, v.get("title", n), v.get("state"), v.get("summary") or "") for n, v in self.hub.bus.directory.items()
                 if v.get("person") != self.hub.person and not v.get("service")]
        out = []
        for n, title, st, summ in sorted(rows):
            summ = (summ or "").strip()
            if not summ:
                continue
            h = hash(summ)
            if not full and self.digest_seen.get(n) == h:
                continue
            self.digest_seen[n] = h
            keep = [ln.strip() for ln in summ.splitlines() if ln.strip()][:5]
            out.append(f"- {n} ({st}): " + " / ".join(keep)[:600])
        if not out:
            return ""
        head = ("[team context: every agent's current brief]" if full else
                "[team context: briefs that changed since your last turn]")
        if full:
            ps = [p for p in self.hub.props() if p.get("status") in OPEN]
            if ps:
                out.append("Open notes on the board: " + "; ".join(f"#{p['id']} {p['kind']}/{p['status']}: {p['title'][:80]}"
                                                                   for p in ps[:12]))
        return head + "\n" + "\n".join(out)

    def crunch(self) -> bool:
        """True in the minutes where a pause to compact would cost a deadline (T-9..T-2 of a scored round)."""
        sch = self.hub.bus.shared.get("schedule")
        if not sch:
            return False
        U, now = 60 * sch.get("scale", 1.0), time.time()
        for k in range(1, sch.get("scored", 6) + 1):
            ts = sch["start"] + (60 + 20 * (k - 1)) * U
            if ts - 9 * U <= now < ts - 2 * U:
                return True
        return False

    async def maybe_compact(self):
        """Compact proactively, between turns, before the context gets long and slow, with a role-specific
        list of what must survive. Skipped in the decision crunch and when work is queued urgently."""
        try:
            u = await self.client.get_context_usage()
            tokens = int((u or {}).get("totalTokens") or 0)
        except Exception:  # noqa: BLE001
            return
        self.context_tokens = tokens
        limit = COMPACT_AT_OVERSEER if self.name.endswith("overseer") else COMPACT_AT_WORKER
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
                f"in {self.hub.portal_data} (one folder per round); use only these, never older data elsewhere."
                f"\n{PROTOCOL}\n{COMMON_RULES}")
        return ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code", "append": role},
            mcp_servers={"hub": self.tool_server()},
            allowed_tools=[f"mcp__hub__{t}" for t in HUB_TOOLS],
            can_use_tool=self.can_use_tool,
            cwd=str(self.cwd), add_dirs=[str(self.hub.repo), str(self.hub.portal_data)],
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
                digest = self.team_digest()
                if digest:
                    prompt = digest + "\n\n" + prompt
                if self.name.endswith("overseer"):
                    prompt = situation(self.hub) + "\n\n" + prompt
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
                await self.maybe_compact()
                await self.set_state("idle")
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
              "answer | fyi (fyi does not wake the receiver). Non-blocking; answers arrive as new turns.",
              schema(["to", "text"], {"to": "string", "text": "string", "kind": "string", "reply_to": "string"}))
        async def send_message(a):
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
            scale = sch.get("scale", 1.0)
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

        @tool("propose", "Put a card on the Decisions board that both humans see. kind: research (a study you plan/ran), "
              "finding (an analysis result), change (a change to the bot or plan; needs a greenlight before it is built/"
              "shipped), decision (what plays in a round; needs a greenlight; give deadline_minutes, e.g. until T-5). "
              "headline: ONE plain-English sentence a tired human understands in 5 seconds (no jargon, no ids), e.g. "
              "'We fold too often on the flop; calling more should gain about 0.7 points per table.' "
              "body: markdown with the evidence (numbers, ± error, files). parent: the card this answers (e.g. a human idea).",
              schema(["kind", "title", "headline", "body"], {"kind": "string", "title": "string", "headline": "string",
                                                             "body": "string", "parent": "string",
                                                             "deadline_minutes": "number", "needs_call": "boolean"}))
        async def propose(a):
            kind = a["kind"] if a["kind"] in KINDS[1:] else "finding"
            needs = a.get("needs_call")
            if needs is None:
                needs = kind in ("change", "decision")
            p = {"id": "P" + new_id()[1:7].upper(), "kind": kind, "title": a["title"][:160], "body": a["body"][:8000],
                 "headline": (a.get("headline") or "")[:300],
                 "author": me.name, "author_person": hub.person, "decider": "both" if kind == "decision" else hub.person,
                 "owner": me.name,
                 "parent": a.get("parent") or None,
                 "status": "needs_call" if needs else ("running" if kind == "research" else "done"),
                 "created": time.time(), "thread": []}
            if a.get("deadline_minutes"):
                sc = (hub.bus.shared.get("schedule") or {}).get("scale", 1.0)
                p["deadline"] = time.time() + float(a["deadline_minutes"]) * 60 * sc
            await hub.save_prop(p)
            if p.get("parent"):
                par = hub.get_prop(p["parent"])
                if par and par.get("status") in OPEN:
                    par["status"] = "done" if kind == "finding" and not needs else par["status"]
                    par.setdefault("thread", []).append({"who": me.title, "at": time.time(), "action": "result",
                                                         "text": f"Result posted: #{p['id']} {p['title']}"})
                    await hub.save_prop(par)
            me.record({"type": "note", "text": f"Posted card #{p['id']} ({kind}): {p['title']}"})
            return ok(f"Card #{p['id']} posted ({p['status']}). " + ("Wait for a human greenlight before acting on it; "
                      "you'll get a message when they decide." if needs else ""))

        @tool("update_proposal", "Update a card: status (planned / running / done / blocked) and a short note, e.g. "
              "progress on a human's idea, or that an approved change is built and tested.",
              schema(["id", "note"], {"id": "string", "status": "string", "note": "string"}))
        async def update_proposal(a):
            p = hub.get_prop(a["id"].lstrip("#"))
            if not p:
                return ok("No such card.")
            st = a.get("status")
            if p.get("status") == "removed":
                return ok(f"Card #{p['id']} was removed from the board by a human; it's no longer relevant. Stop work on it.")
            if st in ("planned", "running", "done", "blocked"):
                p["status"] = st
            p.setdefault("thread", []).append({"who": me.title, "at": time.time(), "action": st or "note", "text": a["note"][:2000]})
            await hub.save_prop(p)
            return ok(f"Card #{p['id']} updated.")

        @tool("list_proposals", "Cards on the Decisions board (open ones first) with status and the humans' replies.",
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
                                                   update_proposal, list_proposals, codex_task])


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
    "b0": [("dylan", "crit", "d-platform", "FIRST_PROMPT.md Part 1 with TWIST_NOTES.md: minimal legal bot in bot/ and releases/v1.zip by minute 10; test harness by 15; today's hand ranking and the twist's value by 20; then the shared platform with every Part 1 check passing"),
           ("dylan", "crit", "d-builder", "Read Part 1 (styles) and TWIST_NOTES.md; draft styles A (wide pressure), B (shove-heavy), C (tight, fold <=75% to re-raises) as settings; build them on Platform's interface as soon as it's published"),
           ("samuel", "crit", "s-tester", "Part 3a: paired runner on identical deals plus sparring bots, running by minute 15"),
           ("samuel", "opt", "s-data", "Prepare Part 2 (leaks) and Part 4 (opponents) scripts for today's hand-history format, so the first round is analysed within 5 minutes of landing")],
    "b10": [("dylan", "crit", "d-platform", "v1 must be released (releases/v1.zip) and Dylan told to upload it now if not done")],
    "b15": [("samuel", "crit", "s-tester", "Test rig must run now: first verdict on v1 (correct? timing?)")],
    "b20": [("dylan", "crit", "d-builder", "Style A ready (tested by s-tester) for practice round 1; B next"),
            ("samuel", "crit", "s-data", "When practice 1 lands: leaks of the bot that played (Part 2), first-1000 file, top change in 5 minutes")],
    "b30": [("dylan", "crit", "d-builder", "Style B for practice 2; C next"),
            ("samuel", "crit", "s-data", "Practice 2 leaks; compare styles A vs B on the real field"),
            ("samuel", "opt", "s-data", "Opponent profiles (Part 4) from practice rounds so far")],
    "b40": [("dylan", "crit", "d-builder", "Style C for practice 3"),
            ("samuel", "crit", "s-tester", "Rank A, B, C (paired tests + real practice scores) for the round-1 choice")],
    "b50": [("dylan", "crit", "d-platform", "Release the best real-field scorer as the live bot for scored round 1"),
            ("samuel", "crit", "s-data", "Which style did the field reward? One paragraph for the round-1 decision")],
    "T13": [("samuel", "crit", "s-data", "The round that just landed: our leaks first (Part 2), one recommended change with size and z"),
            ("samuel", "crit", "s-tester", "Verdict on every pending candidate: correct? and paired test vs the live bot"),
            ("samuel", "opt", "s-data", "Opponent profiles and counters (Part 4)"),
            ("samuel", "opt", "s-tester", "Cloned field on Modal (Part 3b) for the challenger"),
            ("dylan", "crit", "d-builder", "Challenger packed and tested, ready for the T-12 upload"),
            ("dylan", "crit", "d-platform", "Fix bugs s-tester reported; build this window's one tested change on the live bot")],
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
]


def dispatch_text(key: str, person: str) -> str:
    rows = [(pr, ag, t) for (who, pr, ag, t) in DISPATCH.get(key, []) if who == person]
    if not rows:
        return ""
    return "\nDispatch now (task messages; optional ones only if on track):\n" + "\n".join(
        f"- [{'CRITICAL' if pr == 'crit' else 'optional'}] {ag}: {t}" for pr, ag, t in rows)


# steps a person does with their own hands (clock reminders shown to that person)
HUMAN_STEPS = {
    "b0": {"samuel": "Set the clock's minute 0 if it isn't set, and read the Format page.",
           "dylan": "Fetch the kit and read the Format page."},
    "b10": {"dylan": "Upload the minimal bot and make it active."},
    "b20": {"dylan": "Upload style A for practice round 1 (if Overseer says so) and make it active."},
    "b30": {"dylan": "Upload style B for practice round 2 and make it active."},
    "b40": {"dylan": "Upload style C for practice round 3 and make it active."},
    "12": {"dylan": "Upload the challenger and make it active (only if your Overseer says it's ready)."},
    "9": {"dylan": "Put the LIVE bot back as active now."},
    "8": {"samuel": "Decision time: check the Decisions board and greenlight or reject.",
          "dylan": "Decision time: check the Decisions board and greenlight or reject."},
    "3": {"dylan": "Upload the chosen bot (if one was greenlit) and confirm the active bot on the portal."},
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
            if not a.name.endswith("overseer"):
                load.append((a.name, a.state, a.task, a.idle_since))
        for n, v in hub.bus.directory.items():
            if v.get("person") != me and not v.get("service") and not n.endswith("overseer") and now2 - v.get("seen", 0) < 120:
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
                await ov.add_item({"kind": "clock", "wake": True, "text": text})
                if ov.state == "stopped" and not ov.paused:
                    await ov.start()
                human = HUMAN_STEPS.get(key.split(":", 1)[1].split("-")[-1] if ":s" in key else key.split(":", 1)[1], {}).get(me)
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
            await asyncio.sleep(30 if fast else 60)

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
            await self.landed(r)
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
        if prev.get("filename") != cur["filename"] or time.time() - prev.get("at", 0) > 300:
            await self.hub.bus.set_shared("portal_active", cur)   # both laptops' briefs show the active bot
        await self.check_team(team)
        self.save()
        ours = next((x for x in standings if x["team_name"] == self.team_name), None)
        third = standings[2]["total"] if len(standings) >= 3 else None
        summary = "### Standings\n| # | Team | Total |\n|---|---|---|\n" + "\n".join(
            f"| {x['rank']} | {'**' + x['team_name'] + '**' if x['team_name'] == self.team_name else x['team_name']} | {x['total']:.2f} |"
            for x in standings[:10])
        summary += f"\n\nActive bot: {team.get('active_filename') or 'none'} · competition: {self.comp_name}"
        running = [r for r in rounds if not r.get("completed_at")]
        task = (f"We're {ours['rank']} ({ours['total']:.1f}; 3rd has {third:.1f})" if ours and third is not None else
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
        files = await self.fetch_hands(r["id"], folder)
        if not files:
            self.st["need_hands"][r["id"]] = {"folder": str(folder), "label": label, "since": time.time()}
        items = sorted(res["items"], key=lambda x: -x["average_points"])
        ours = next((i for i, x in enumerate(items, 1) if x["team_name"] == self.team_name), None)
        me = items[ours - 1] if ours else None
        line = (f"{label} finished: we were {ours} of {len(items)} with {me['average_points']:.2f} "
                f"(±{me['margin_of_error'] or 0:.2f}); 1st {items[0]['team_name']} {items[0]['average_points']:.2f}."
                if me else f"{label} finished (we had no result: forfeit?).")
        paths = f"\nResults: {folder}/results.json" + "".join(f"\nHands: {p}" for p in files) + \
                ("" if files else "\nHand history not downloadable yet; I'll keep trying.")
        self.st["done"].append(r["id"])
        self.save()
        if quiet:
            return
        ov = self.hub.agents.get("s-overseer")
        if ov:   # the Overseer decides what to do with it and dispatches the workers with context
            await ov.add_item({"kind": "portal", "wake": True, "text": "NEW ROUND RESULT. " + line + paths})
            if ov.state == "stopped" and not ov.paused:
                await ov.start()
        await self.tell("d-overseer", "fyi", line)
        self.hub.set_service("s-portal", "Portal", "working", line)

    async def fetch_hands(self, tid: str, folder: Path) -> list[str]:
        files = []
        for suffix, q in (("first-1000", "?subset=first-1000"),) + ((("full", ""),) if not self.small_only else ()):
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
                    await self.hub.add_alert("s-portal", text, True)
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
                await self.hub.add_alert("s-portal", msg, True)
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
            s = await hub.clock.set_start(b.get("start", ""), int(b.get("scored") or 6), float(b.get("scale") or 1.0))
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
        s = await hub.clock.set_start("", 6, 1.0, t0=time.time())
        ov = hub.overseer()
        await ov.human("Start building: the variant is announced now (minute 0). Kick off the build-hour plan.",
                       PEOPLE[hub.person])
        return web.json_response({"ok": True, "text": s})

    r.add_post("/api/props/{id}/ask", ask_prop)
    r.add_post("/api/start", start_event)
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
    for ag in hub.agents.values():
        hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task, "summary": ag.summary})
    for pr in hub.local_props.values():   # re-share this laptop's cards (e.g. after a restart)
        asyncio.create_task(hub.bus.set_shared("prop:" + pr["id"], pr))
    if a.start:
        await hub.clock.set_start(a.start, scale=a.scale)
    if not a.view_only:
        asyncio.create_task(hub.clock.loop())
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
        elif not a.no_autostart and ag.spec.get("autostart") and not restarted:
            if not ag.session_id and ag.name in KICKOFF:
                await ag.add_item({"kind": "hub", "wake": True, "text": KICKOFF[ag.name]})
            await ag.start()

    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            for ag in hub.agents.values():
                hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task, "summary": ag.summary})
                ag.save_meta()
            if hub.bus.outbox and hub.bus.oldest_unsent_age() > 120:
                await hub.add_alert("hub", "Messages to the other laptop have been waiting over 2 minutes: the link "
                                    "is down. Talk to your teammate directly until it's back.", True)
    asyncio.create_task(heartbeat())
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
