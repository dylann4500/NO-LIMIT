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
import os
import re
import subprocess
import time
import traceback
import urllib.request
from pathlib import Path

from aiohttp import web
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
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
             "declare_live", "set_schedule"]
LIMIT_RX = re.compile(r"usage limit|rate.?limit|overloaded|429|quota|limit reached|too many requests", re.I)
APPROVAL_TIMEOUT = 180


class LimitHit(Exception):
    pass
EVENT_CAP = 4000


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
        self.clock = Clock(self)
        self.portal: PortalWatcher | None = None

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
        al = {"id": new_id(), "agent": agent, "text": text, "urgent": urgent, "at": now}
        self.alerts = (self.alerts + [al])[-50:]
        atomic_write(self.data / "alerts.json", json.dumps(self.alerts))
        self.emit("alert", al)

    def dismiss(self, aid: str):
        self.alerts = [a for a in self.alerts if a["id"] != aid]
        atomic_write(self.data / "alerts.json", json.dumps(self.alerts))
        self.emit("alert_done", {"id": aid})

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
                "live": self.bus.shared.get("live"), "clock": self.clock.next_text(),
                "bus": {"online": self.bus.online, "error": self.bus.error, "outbox": len(self.bus.outbox),
                        "oldest": round(self.bus.oldest_unsent_age())}}


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
        self.usage: dict = {}             # latest usage-limit notice from Claude
        self.limit_reset: float | None = None
        self.model_switch: str | None = None
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
                "task": self.task, "summary": self.summary, "policy": self.policy,
                "model": self.model(), "usage": self.usage,
                "queued": sum(1 for i in self.items if not i.get("taken")), "cost": round(self.cost, 2),
                "overseer": self.name.endswith("overseer"), "since": self.turn_started, "last_i": self.next_i - 1,
                "cwd": str(self.cwd)}

    def model(self):
        return self.hub.model_override or self.model_switch or self.spec.get("model", "claude-opus-5-5")

    async def set_state(self, state: str, substate: str = ""):
        if self.pending_approvals > 0 and state not in ("stopped", "error", "limited"):
            state = "waiting"
        self.state, self.substate = state, substate
        self.hub.emit("agent", self.view())
        self.hub.bus.publish(self.name, {"title": self.title, "state": self.state, "task": self.task,
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
        if not wt.exists():
            try:
                subprocess.run(["git", "-C", str(repo), "worktree", "add", "-B", "builder", str(wt)],
                               check=True, capture_output=True, timeout=60)
            except Exception:  # noqa: BLE001
                return repo
        return wt

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
                f"Your working folder is {self.cwd}; the team repo is {self.hub.repo}.\n{PROTOCOL}\n{COMMON_RULES}")
        return ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code", "append": role},
            mcp_servers={"hub": self.tool_server()},
            allowed_tools=[f"mcp__hub__{t}" for t in HUB_TOOLS],
            can_use_tool=self.can_use_tool,
            cwd=str(self.cwd), add_dirs=[str(self.hub.repo), str(Path.home() / "portal-data")],
            model=self.model(),
            fallback_model=None if self.hub.model_override else "claude-sonnet-5-5",
            resume=self.session_id if resume else None,
            setting_sources=[],       # no repo allow-rules can bypass the hub's permission check
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
        Path.home().joinpath("portal-data").mkdir(exist_ok=True)
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
                prompt = "\n\n".join(self.format(b) for b in batch)
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
                if limited:
                    raise LimitHit("usage limit reached")
                if not ok:
                    raise RuntimeError("the turn ended with an error")
                done = {i["id"] for i in batch}
                self.items = [i for i in self.items if i["id"] not in done]
                self.save_items()
                self.fails = 0
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
                is_limit = isinstance(e, LimitHit) or (bool(LIMIT_RX.search(text)) and
                                                       not isinstance(e, (TypeError, ValueError, KeyError, AttributeError)))
                self.fails += 1
                wait = min(5 * 2 ** min(self.fails, 5), 120)
                if is_limit:
                    kind = self.usage.get("type") or ""
                    if "opus" in kind and "sonnet" not in self.model():
                        self.model_switch = "claude-sonnet-5-5"   # Opus allowance used up: carry on with Sonnet
                        wait = 5
                        msg = f"{self.title} used up its Opus allowance; it switched to Sonnet and carries on."
                    else:
                        wait = max(60, (self.limit_reset or time.time() + 300) - time.time() + 30)
                        msg = (f"{self.title} hit a Claude usage limit; it resumes at {hhmm(time.time() + wait)}. "
                               "Its messages are kept. Consider moving its work to another agent or Codex.")
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
            elif "compact" in (m.subtype or ""):
                self.items.append({"id": new_id(), "at": time.time(), "kind": "hub", "wake": False,
                                   "text": "Your context was just compacted. Re-read your PLAN file and your role "
                                           "before continuing; facts about rounds must come from the portal watcher."})
                self.save_items()
        elif type(m).__name__ == "RateLimitEvent":
            info = m.rate_limit_info
            prev = self.usage.get("status")
            self.usage = {"status": info.status, "used": info.utilization, "type": info.rate_limit_type,
                          "resets_at": info.resets_at}
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
        roots = [self.hub.repo, self.cwd, Path.home() / "portal-data", Path("/tmp"), Path("/private/tmp")]
        return any(rp == r or r in rp.parents for r in (x.resolve() for x in roots))

    async def can_use_tool(self, name, inp, ctx):
        if name.startswith("mcp__hub__"):
            return PermissionResultAllow()
        text = json.dumps(inp)
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

        @tool("declare_live", "d-overseer only: record the bot that should be active on the portal (file name, and "
              "sha256 if known). The portal watcher checks the portal against it before every round.",
              schema(["filename"], {"filename": "string", "sha256": "string", "note": "string"}))
        async def declare_live(a):
            if me.name != "d-overseer":
                return ok("Only d-overseer declares the live bot.")
            v = {"filename": a["filename"], "sha256": a.get("sha256") or "", "note": a.get("note") or "", "at": time.time()}
            await hub.bus.set_shared("live", v)
            hub.emit("shared", {"live": v})
            return ok(f"Live bot declared: {v['filename']}.")

        @tool("set_schedule", "Overseers: set the event clock. start = local time of minute 0 (HH:MM, today), e.g. the "
              "variant announcement. Practice at +20/+30/+40/+50, scored rounds every 20 min from +60.",
              schema(["start"], {"start": "string", "scored_rounds": "integer"}))
        async def set_schedule(a):
            if not me.name.endswith("overseer"):
                return ok("Only Overseers set the schedule.")
            try:
                s = await hub.clock.set_start(a["start"], int(a.get("scored_rounds") or 6))
            except ValueError as e:
                return ok(f"Not set: {e}")
            return ok("Schedule set: " + s)

        return create_sdk_mcp_server("hub", tools=[send_message, list_agents, read_agent, set_status, notify_human,
                                                   start_agent, stop_agent, declare_live, set_schedule])


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
        t0, out = s["start"], []
        for k, m in enumerate((20, 30, 40, 50), 1):
            out.append(("practice", k, t0 + m * 60))
        for k in range(1, s.get("scored", 6) + 1):
            ts = t0 + (60 + 20 * (k - 1)) * 60
            out.append(("scored", k, ts))
            if k < s.get("scored", 6):
                out.append(("practice", 4 + k, ts + 600))
        return sorted(out, key=lambda e: e[2])

    async def set_start(self, hhmm_s: str, scored: int = 6):
        m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", hhmm_s or "")
        if not m:
            raise ValueError("use HH:MM")
        lt = time.localtime()
        t0 = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2)), 0, 0, 0, -1))
        await self.hub.bus.set_shared("schedule", {"start": t0, "scored": scored, "set_by": self.hub.person, "at": time.time()})
        self.sent = set()
        self.hub.emit("shared", {"schedule": self.hub.bus.shared["schedule"]})
        return f"minute 0 at {hhmm(t0)}; scored round 1 at {hhmm(t0 + 3600)}; last scored round at {hhmm(t0 + 3600 + 1200 * (scored - 1))}."

    def next_text(self):
        now = time.time()
        for kind, k, ts in self.events():
            if ts > now - 30:
                mins = (ts - now) / 60
                lbl = f"{'Scored' if kind == 'scored' else 'Practice'} round {k}"
                return f"{lbl} at {hhmm(ts)} ({'now' if mins < 0.5 else f'in {mins:.0f} min'})"
        return "No schedule set" if not self.events() else "Event finished"

    async def loop(self):
        while True:
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(10)

    async def tick(self):
        now = time.time()
        ov = self.hub.overseer()
        for kind, k, ts in self.events():
            label = f"{'Scored' if kind == 'scored' else 'Practice'} round {k}"
            if kind == "scored":
                marks = [(13, "T-13: the previous round's results should be in. Plan this window."),
                         (8, "T-8: decision time. " + ("Send d-overseer your recommendation now." if self.hub.person == "samuel"
                                                     else "Decide what plays (s-overseer's recommendation should be in).")),
                         (5, "T-5: if nothing is decided, the live bot plays; no upload."),
                         (3, "T-3: last moment to upload. After this, uploads may miss the round.")]
            else:
                marks = [(3, "starts in 3 minutes." + (" Make sure the bot for it is uploaded and active."
                                                       if self.hub.person == "dylan" else ""))]
            for mins, text in marks:
                key = f"{kind}{k}-{mins}"
                if key not in self.sent and ts - mins * 60 <= now < ts - mins * 60 + 120:
                    self.sent.add(key)
                    atomic_write(self.hub.data / "clock_sent.json", json.dumps(sorted(self.sent)))
                    await ov.add_item({"kind": "clock", "wake": True, "text": f"{label} at {hhmm(ts)}: {text}"})
                    if ov.state == "stopped" and not ov.paused:
                        await ov.start()
        self.hub.set_service("hub-clock", "Clock", "working" if self.events() else "idle", self.next_text())


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
        self.fails = 0
        self.small_only = small_only   # on a phone hotspot: only the first-1000 file, to save data
        self.team = self.cid = None
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

    async def poll(self) -> bool:
        if not self.cid:
            me = await self.aget("/me")
            t = (me.get("teams") or [{}])[0]
            self.team, self.cid = t.get("id"), t.get("competition_id")
            if not self.cid:
                comps = (await self.aget("/competitions"))["items"]
                self.cid = comps[0]["id"]
        rounds = (await self.aget(f"/competitions/{self.cid}/tournaments"))["items"]
        new_done = [r for r in rounds if r.get("completed_at") and r["id"] not in self.st["done"]]
        for r in sorted(new_done, key=lambda r: r["created_at"]):
            await self.landed(r)
        standings = (await self.aget(f"/competitions/{self.cid}/standings"))["items"]
        self.st["standings"] = standings
        team = await self.aget(f"/teams/{self.team}") if self.team else {}
        await self.check_team(team)
        self.save()
        ours = next((x for x in standings if x["team_name"] == "avalon"), None)
        third = standings[2]["total"] if len(standings) >= 3 else None
        summary = "### Standings\n| # | Team | Total |\n|---|---|---|\n" + "\n".join(
            f"| {x['rank']} | {'**' + x['team_name'] + '**' if x['team_name'] == 'avalon' else x['team_name']} | {x['total']:.2f} |"
            for x in standings[:10])
        summary += f"\n\nActive bot: {team.get('active_filename') or 'none'}"
        running = [r for r in rounds if not r.get("completed_at")]
        task = (f"We're {ours['rank']} ({ours['total']:.1f}; 3rd has {third:.1f})" if ours and third is not None else
                f"{len(rounds)} rounds seen") + (f" · {len(running)} running" if running else "")
        self.hub.set_service("s-portal", "Portal", "working", task, summary)
        return bool(running)

    async def landed(self, r):
        res = await self.aget(f"/tournaments/{r['id']}/results")
        label = r.get("label") or f"{r['kind']} {r['created_at'][11:16]}"
        n = len(self.st["done"]) + 1
        folder = self.out / f"{n:02d}-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "results.json").write_text(json.dumps(res, indent=1))
        files = []
        for suffix, q in (("first-1000", "?subset=first-1000"),) + ((("full", ""),) if not self.small_only else ()):
            try:
                url = self.hands_url.replace("{tid}", r["id"]).replace("{q}", q)
                data = await self.aget(url, raw=True)
                if data[:2] == b"\x1f\x8b" and len(data) > 100:
                    p = folder / f"hands-{suffix}.jsonl.gz"
                    p.write_bytes(data)
                    files.append(str(p))
            except Exception:  # noqa: BLE001
                pass
        items = sorted(res["items"], key=lambda x: -x["average_points"])
        ours = next((i for i, x in enumerate(items, 1) if x["team_name"] == "avalon"), None)
        me = items[ours - 1] if ours else None
        line = (f"{label} finished: we were {ours} of {len(items)} with {me['average_points']:.2f} "
                f"(±{me['margin_of_error'] or 0:.2f}); 1st {items[0]['team_name']} {items[0]['average_points']:.2f}."
                if me else f"{label} finished (we had no result: forfeit?).")
        paths = f"\nResults: {folder}/results.json" + "".join(f"\nHands: {p}" for p in files) + \
                ("" if files else "\nHand history not downloadable yet; I'll keep trying.")
        self.st["done"].append(r["id"])
        self.save()
        ov = self.hub.agents.get("s-overseer")
        if ov:
            await ov.add_item({"kind": "portal", "wake": True, "text": line + paths})
        data_agent = self.hub.agents.get("s-data")
        if data_agent and files:
            await data_agent.add_item({"kind": "portal", "wake": True, "text": line + paths + "\nAnalyse it (your role)."})
            if data_agent.state == "stopped" and not data_agent.paused:
                await data_agent.start()
        try:
            await self.hub.bus.send({"id": new_id(), "from": "s-portal", "from_kind": "hub", "to": "d-overseer",
                                     "kind": "fyi", "text": line})
        except Exception:  # noqa: BLE001
            pass
        self.hub.set_service("s-portal", "Portal", "working", line)

    async def check_team(self, team: dict):
        for s in team.get("submissions") or []:
            if s["id"] in self.st["subs"]:
                continue
            if s["status"] in ("ready", "rejected"):
                self.st["subs"].append(s["id"])
                if s["status"] == "rejected":
                    text = f"Upload {s['filename']} was REJECTED by the portal: {s.get('rejection_reason')}. The previous bot stays active."
                    await self.hub.add_alert("s-portal", text, True)
                    await self.hub.bus.send({"id": new_id(), "from": "s-portal", "from_kind": "hub", "to": "d-overseer",
                                             "kind": "question", "text": text})
        live = self.hub.bus.shared.get("live")
        now = time.time()
        for kind, k, ts in self.hub.clock.events():
            for mins in (9, 2):
                key = f"{kind}{k}-{mins}"
                if key in self.checked or not (ts - mins * 60 <= now < ts - mins * 60 + 90):
                    continue
                self.checked.add(key)
                active = team.get("active_filename")
                if not active:
                    msg = f"{kind.title()} round {k} starts at {hhmm(ts)} and there is NO active bot. We forfeit unless one is made active."
                elif live and live.get("filename") and live["filename"] != active:
                    msg = (f"{kind.title()} round {k} starts at {hhmm(ts)}: the portal's active bot is {active}, but "
                           f"d-overseer declared {live['filename']}.")
                else:
                    continue
                await self.hub.add_alert("s-portal", msg, True)
                try:
                    await self.hub.bus.send({"id": new_id(), "from": "s-portal", "from_kind": "hub", "to": "d-overseer",
                                             "kind": "question", "text": msg})
                except Exception:  # noqa: BLE001
                    pass


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
            s = await hub.clock.set_start(b.get("start", ""), int(b.get("scored") or 6))
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
    return app


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--person", required=True, choices=list(PEOPLE))
    ap.add_argument("--repo", required=True, help="the team repo the agents work in")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--data", default=None, help="hub state folder (default ~/.avalon-hub/<person>)")
    ap.add_argument("--namespace", default="", help="message-line suffix, e.g. --namespace=-live on Sunday")
    ap.add_argument("--no-autostart", action="store_true")
    ap.add_argument("--model", default=None, help="run every agent on this model (e.g. claude-haiku-5-5 for tests)")
    ap.add_argument("--start", default=None, help="event minute 0 as HH:MM (sets the shared clock)")
    ap.add_argument("--portal-base", default=None, help="portal API base, e.g. http://127.0.0.1:8765/tournament/api")
    ap.add_argument("--portal-key-file", default=None)
    ap.add_argument("--portal-data", default=None, help="where the portal watcher saves results and hand data (default ~/portal-data)")
    ap.add_argument("--small-hands", action="store_true", help="download only the first-1000 hand file (phone hotspot)")
    ap.add_argument("--hands-url", default=None, help="hand-history URL template with {tid} (real portal: copy it on the day)")
    a = ap.parse_args()
    data = Path(a.data or Path.home() / ".avalon-hub" / a.person).expanduser()
    data.mkdir(parents=True, exist_ok=True)
    hub = Hub(a.person, Path(a.repo).expanduser().resolve(), data, a.namespace, a.model)
    await hub.bus.start()
    for ag in hub.agents.values():
        hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task, "summary": ag.summary})
    if a.start:
        await hub.clock.set_start(a.start)
    asyncio.create_task(hub.clock.loop())
    if a.portal_base and a.portal_key_file:
        hub.portal = PortalWatcher(hub, a.portal_base, Path(a.portal_key_file), a.hands_url,
                                   Path(a.portal_data) if a.portal_data else None, a.small_hands)
        asyncio.create_task(hub.portal.loop())
    runner = web.AppRunner(make_app(hub))
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", a.port).start()
    print(f"avalon hub ({PEOPLE[a.person]}): http://127.0.0.1:{a.port}   link: "
          f"{'online' if hub.bus.online else hub.bus.error}", flush=True)
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
