"""Team avalon's agent hub: one per laptop.

  uv run --with aiohttp --with claude-agent-sdk --with modal python hub/hub.py \
      --person samuel --repo ~/nolimit-rehearsal            # then open http://127.0.0.1:7777

Runs every agent on this laptop as a real Claude Code session (Claude Agent SDK, your own login),
serves the UI, asks you before risky commands, and moves messages between agents on both laptops
(see bus.py). The UI listens on 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
import traceback
from pathlib import Path

from aiohttp import web
from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, PermissionResultAllow,
                              PermissionResultDeny, ResultMessage, SystemMessage, TextBlock, ThinkingBlock,
                              ToolResultBlock, ToolUseBlock, UserMessage, create_sdk_mcp_server, tool)

from bus import Bus, new_id
from roster import COMMON_RULES, PEOPLE, PROTOCOL, ROSTER

HERE = Path(__file__).resolve().parent
DANGER = re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+(/|~|\$HOME|\.\.)|git\s+push\b[^\n]*(--force|-f\b)|"
                    r"git\s+reset\s+--hard|\bsudo\b|\bmkfs|curl[^|\n]*\|\s*(ba)?sh|chmod\s+-R\s+777|"
                    r"git\s+clean\s+-[a-z]*f|\bdd\s+if=|>\s*/dev/sd|modal\s+app\s+stop|git\s+branch\s+-D")
HUB_TOOLS = ["send_message", "list_agents", "read_agent", "set_status", "notify_human", "start_agent", "stop_agent"]


class Hub:
    def __init__(self, person: str, repo: Path, data: Path, namespace: str):
        self.person = person
        self.repo = repo
        self.data = data
        self.agents: dict[str, "Agent"] = {}
        self.subs: set[asyncio.Queue] = set()
        self.approvals: dict[str, dict] = {}
        self.alerts: list[dict] = []
        self.model_override: str | None = None
        self.bus = Bus(person, data, self.deliver, namespace)
        for spec in ROSTER[person]:
            self.agents[spec["name"]] = Agent(self, spec)
        self.bus.local_names = set(self.agents)

    def emit(self, kind: str, payload: dict):
        ev = {"kind": kind, **payload}
        for q in list(self.subs):
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass

    async def deliver(self, msg: dict):
        a = self.agents.get(msg["to"])
        if a is None:
            return
        await a.receive(msg)

    def roster_view(self):
        return [a.view() for a in self.agents.values()]

    def remote_view(self):
        return [dict(name=k, **v) for k, v in sorted(self.bus.directory.items())
                if v.get("person") != self.person]

    async def add_alert(self, agent: str, text: str, urgent: bool):
        al = {"id": new_id(), "agent": agent, "text": text, "urgent": urgent, "at": time.time()}
        self.alerts.append(al)
        self.alerts = self.alerts[-50:]
        self.emit("alert", al)


class Agent:
    def __init__(self, hub: Hub, spec: dict):
        self.hub = hub
        self.spec = spec
        self.name = spec["name"]
        self.title = spec["title"]
        self.state = "stopped"
        self.task = ""
        self.summary = ""
        self.policy = "auto"
        self.client: ClaudeSDKClient | None = None
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.runner: asyncio.Task | None = None
        self.dir = hub.data / "agents" / self.name
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.dir / "events.jsonl"
        self.events: list[dict] = [json.loads(l) for l in self.log_file.open()] if self.log_file.exists() else []
        meta = self.dir / "meta.json"
        m = json.loads(meta.read_text()) if meta.exists() else {}
        self.session_id = m.get("session_id")
        self.task, self.summary, self.policy = m.get("task", ""), m.get("summary", ""), m.get("policy", "auto")
        self.cost = m.get("cost", 0.0)
        self.unread = 0

    # ---------------------------------------------------------------- state
    def save_meta(self):
        (self.dir / "meta.json").write_text(json.dumps({"session_id": self.session_id, "task": self.task,
                                                        "summary": self.summary, "policy": self.policy,
                                                        "cost": self.cost}))

    def view(self):
        return {"name": self.name, "title": self.title, "state": self.state, "task": self.task,
                "summary": self.summary, "policy": self.policy, "model": self.spec.get("model", "claude-opus-5-5"),
                "events": len(self.events), "queued": self.inbox.qsize(), "cost": round(self.cost, 2),
                "overseer": self.name.endswith("overseer")}

    async def set_state(self, state: str):
        self.state = state
        self.hub.emit("agent", self.view())
        await self.hub.bus.publish(self.name, {"title": self.title, "state": self.state, "task": self.task,
                                               "summary": self.summary})

    def record(self, ev: dict):
        ev = {"i": len(self.events), "t": time.time(), **ev}
        self.events.append(ev)
        with self.log_file.open("a") as f:
            f.write(json.dumps(ev) + "\n")
        self.hub.emit("event", {"agent": self.name, "event": ev})

    # ---------------------------------------------------------------- lifecycle
    async def start(self, first_task: str | None = None):
        if self.runner and not self.runner.done():
            if first_task:
                await self.inbox.put({"kind": "human", "text": first_task, "from": "overseer"})
            return
        if first_task:
            await self.inbox.put({"kind": "human", "text": first_task, "from": "overseer"})
        self.runner = asyncio.create_task(self.run())

    async def stop(self):
        if self.runner:
            self.runner.cancel()
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self.client = None
        await self.set_state("stopped")

    async def receive(self, msg: dict):
        self.record({"type": "msg_in", "from": msg["from"], "text": msg["text"], "id": msg["id"],
                     "reply_to": msg.get("reply_to")})
        await self.inbox.put({"kind": "msg", **msg})
        if self.state == "stopped":
            await self.start()

    def options(self) -> ClaudeAgentOptions:
        role = (f"{self.spec['role']}\n\nYour hub name is `{self.name}` ({PEOPLE[self.hub.person]}'s laptop). "
                f"Your working folder is the team repo {self.hub.repo}.\n{PROTOCOL}\n{COMMON_RULES}")
        return ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code", "append": role},
            mcp_servers={"hub": self.tool_server()},
            allowed_tools=[f"mcp__hub__{t}" for t in HUB_TOOLS],
            can_use_tool=self.can_use_tool,
            cwd=str(self.hub.repo),
            model=self.hub.model_override or self.spec.get("model", "claude-opus-5-5"),
            resume=self.session_id,
            setting_sources=["project", "local"],
            permission_mode="default",
        )

    async def connect(self):
        self.client = ClaudeSDKClient(options=self.options())
        try:
            await self.client.connect()
        except Exception:  # noqa: BLE001  (a stale session id: start fresh)
            self.session_id = None
            self.client = ClaudeSDKClient(options=self.options())
            await self.client.connect()

    async def run(self):
        backoff = 5
        await self.set_state("starting")
        while True:
            try:
                if self.client is None:
                    await self.connect()
                    await self.set_state("idle")
                item = await self.inbox.get()
                batch = [item]
                while not self.inbox.empty():
                    batch.append(self.inbox.get_nowait())
                prompt = "\n\n".join(self.format(b) for b in batch)
                for b in batch:
                    if b["kind"] == "human":
                        self.record({"type": "user", "text": b["text"], "from": b.get("from", "human")})
                await self.set_state("working")
                await self.client.query(prompt)
                async for m in self.client.receive_response():
                    self.handle(m)
                await self.set_state("idle")
                backoff = 5
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                self.record({"type": "error", "text": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]})
                await self.set_state("error")
                try:
                    if self.client:
                        await self.client.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                self.client = None
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 120)

    def format(self, b: dict) -> str:
        if b["kind"] == "human":
            who = b.get("from", "human")
            return b["text"] if who in ("human", PEOPLE[self.hub.person]) else f"[from {who}] {b['text']}"
        tag = f"[from {b['from']} · id {b['id']}" + (f" · reply to {b['reply_to']}" if b.get("reply_to") else "") + "]"
        return f"{tag}\n{b['text']}"

    def handle(self, m):
        if isinstance(m, AssistantMessage):
            for b in m.content:
                if isinstance(b, TextBlock) and b.text.strip():
                    self.record({"type": "text", "text": b.text, "sub": bool(m.parent_tool_use_id)})
                elif isinstance(b, ToolUseBlock):
                    self.record({"type": "tool", "name": b.name, "input": short(b.input), "id": b.id,
                                 "sub": bool(m.parent_tool_use_id)})
                elif isinstance(b, ThinkingBlock):
                    pass
        elif isinstance(m, UserMessage) and isinstance(m.content, list):
            for b in m.content:
                if isinstance(b, ToolResultBlock):
                    self.record({"type": "tool_result", "id": b.tool_use_id, "error": bool(b.is_error),
                                 "text": short(b.content, 1200)})
        elif isinstance(m, ResultMessage):
            self.session_id = m.session_id
            self.cost += m.total_cost_usd or 0
            self.save_meta()
            self.record({"type": "result", "ok": not m.is_error, "turns": m.num_turns, "ms": m.duration_ms})
        elif isinstance(m, SystemMessage) and m.subtype == "init":
            sid = (m.data or {}).get("session_id")
            if sid:
                self.session_id = sid
                self.save_meta()

    # ---------------------------------------------------------------- permissions
    async def can_use_tool(self, name, inp, ctx):
        if name.startswith("mcp__hub__"):
            return PermissionResultAllow()
        text = json.dumps(inp)[:4000]
        risky = bool(DANGER.search(text))
        if self.policy == "auto" and not risky:
            return PermissionResultAllow()
        ap = {"id": new_id(), "agent": self.name, "tool": name, "input": short(inp, 800), "risky": risky,
              "at": time.time(), "future": asyncio.get_running_loop().create_future()}
        self.hub.approvals[ap["id"]] = ap
        self.hub.emit("approval", {k: v for k, v in ap.items() if k != "future"})
        prev = self.state
        await self.set_state("waiting")
        try:
            decision = await ap["future"]
        finally:
            self.hub.approvals.pop(ap["id"], None)
            self.hub.emit("approval_done", {"id": ap["id"]})
            await self.set_state(prev if prev != "waiting" else "working")
        self.record({"type": "permission", "tool": name, "decision": decision})
        if decision in ("allow", "always"):
            if decision == "always" and not risky:
                self.policy = "auto"
                self.save_meta()
            return PermissionResultAllow()
        return PermissionResultDeny(message="A human declined this action. Choose another way or ask.", interrupt=False)

    # ---------------------------------------------------------------- hub tools
    def tool_server(self):
        me, hub = self, self.hub

        def ok(text):
            return {"content": [{"type": "text", "text": text}]}

        @tool("send_message", "Send a message to any agent on either laptop (see list_agents). Non-blocking; replies arrive as new turns.",
              schema(["to", "text"], {"to": "string", "text": "string", "reply_to": "string"}))
        async def send_message(a):
            msg = {"id": new_id(), "from": me.name, "to": a["to"].strip(), "text": a["text"],
                   "reply_to": a.get("reply_to") or None}
            try:
                status = await hub.bus.send(msg)
            except ValueError as e:
                names = sorted(set(hub.agents) | set(hub.bus.directory))
                return ok(f"Not sent: {e}. Known agents: {', '.join(names)}")
            me.record({"type": "msg_out", "to": msg["to"], "text": msg["text"], "id": msg["id"],
                       "reply_to": msg["reply_to"]})
            return ok(f"{status} (id {msg['id']})")

        @tool("list_agents", "Every agent on both laptops with state and one-line status.", {})
        async def list_agents(a):
            rows = [f"{v['name']} [{v['state']}] {v['title']}: {v['task'] or '-'}" for v in hub.roster_view()]
            for v in hub.remote_view():
                age = int(time.time() - v.get("seen", 0))
                rows.append(f"{v['name']} [{v.get('state')}{', not seen for %ds' % age if age > 120 else ''}] "
                            f"{v.get('title')} ({PEOPLE.get(v.get('person'), '?')}'s laptop): {v.get('task') or '-'}")
            return ok("\n".join(rows) + ("" if hub.bus.online else f"\n(Note: {hub.bus.error})"))

        @tool("read_agent", "Latest work of an agent: recent transcript (this laptop) or posted summary (other laptop).",
              schema(["name"], {"name": "string", "last": "integer"}))
        async def read_agent(a):
            n = a["name"].strip()
            if n in hub.agents:
                ag = hub.agents[n]
                lines = [f"{ag.title} [{ag.state}] task: {ag.task}", f"summary:\n{ag.summary}", "recent:"]
                for e in ag.events[-int(a.get("last") or 30):]:
                    if e["type"] in ("text", "user", "msg_in", "msg_out"):
                        lines.append(f"- {e['type']}: {(e.get('text') or '')[:400]}")
                    elif e["type"] == "tool":
                        lines.append(f"- tool {e['name']}: {str(e.get('input'))[:160]}")
                return ok("\n".join(lines))
            v = hub.bus.directory.get(n)
            if v:
                return ok(f"{v.get('title')} [{v.get('state')}] task: {v.get('task')}\nsummary:\n{v.get('summary')}")
            return ok(f"No agent named {n}.")

        @tool("set_status", "Update your state (working/waiting/blocked/done/idle), task line and markdown summary.",
              schema([], {"state": "string", "task": "string", "summary": "string"}))
        async def set_status(a):
            me.task = a.get("task") or me.task
            if a.get("summary"):
                me.summary = a["summary"]
            me.save_meta()
            await me.set_state(me.state)
            return ok("Status updated.")

        @tool("notify_human", "Ask a human to decide or act. Shown at the top of their screen.", schema(["text"], {"text": "string", "urgent": "boolean"}))
        async def notify_human(a):
            await hub.add_alert(me.name, a["text"], bool(a.get("urgent")))
            me.record({"type": "notify", "text": a["text"], "urgent": bool(a.get("urgent"))})
            return ok("The human has been notified.")

        @tool("start_agent", "Overseer only: start one of your laptop's agents (see list_agents), with a first task.",
              schema(["name"], {"name": "string", "task": "string"}))
        async def start_agent(a):
            if not me.name.endswith("overseer"):
                return ok("Only the overseer can start agents.")
            ag = hub.agents.get(a["name"].strip())
            if not ag:
                return ok(f"No agent {a['name']} on this laptop. Choose from: {', '.join(hub.agents)}")
            await ag.start(a.get("task") or None)
            return ok(f"{ag.name} started.")

        @tool("stop_agent", "Overseer only: stop one of your laptop's agents.", {"name": str})
        async def stop_agent(a):
            if not me.name.endswith("overseer"):
                return ok("Only the overseer can stop agents.")
            ag = hub.agents.get(a["name"].strip())
            if not ag or ag is me:
                return ok("Can't stop that agent.")
            await ag.stop()
            return ok(f"{ag.name} stopped.")

        return create_sdk_mcp_server("hub", tools=[send_message, list_agents, read_agent, set_status, notify_human,
                                                   start_agent, stop_agent])


def schema(required, props):
    return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()}, "required": required}


def short(x, n=400):
    if isinstance(x, list):
        x = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in x)
    s = x if isinstance(x, str) else json.dumps(x)
    return s if len(s) <= n else s[:n] + "…"


# -------------------------------------------------------------------- web
def make_app(hub: Hub) -> web.Application:
    app = web.Application(client_max_size=4 * 1024 * 1024)
    r = app.router

    async def index(_):
        return web.FileResponse(HERE / "ui" / "index.html")

    async def state(_):
        return web.json_response({
            "me": hub.person, "people": PEOPLE, "agents": hub.roster_view(), "remote": hub.remote_view(),
            "approvals": [{k: v for k, v in a.items() if k != "future"} for a in hub.approvals.values()],
            "alerts": hub.alerts[-20:], "bus": {"online": hub.bus.online, "error": hub.bus.error,
                                                "outbox": len(hub.bus.outbox)}})

    async def events(req):
        a = hub.agents.get(req.match_info["name"])
        if not a:
            return web.json_response({"error": "no such agent"}, status=404)
        since = int(req.query.get("since", "0"))
        return web.json_response({"events": a.events[since:][-600:]})

    async def stream(req):
        resp = web.StreamResponse(headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"})
        await resp.prepare(req)
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        hub.subs.add(q)
        try:
            while True:
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

    async def send(req):
        name = req.match_info["name"]
        body = await req.json()
        text = (body.get("text") or "").strip()
        if not text:
            return web.json_response({"error": "empty"}, status=400)
        if name in hub.agents:
            a = hub.agents[name]
            await a.inbox.put({"kind": "human", "text": text, "from": PEOPLE[hub.person]})
            if a.state == "stopped":
                await a.start()
            return web.json_response({"ok": True})
        try:  # an agent on the other laptop: goes over the bus, from this person
            await hub.bus.send({"id": new_id(), "from": PEOPLE[hub.person], "to": name, "text": text})
        except ValueError as e:
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
            await a.client.interrupt()
        elif act == "policy":
            a.policy = (await req.json()).get("policy", "auto")
            a.save_meta()
            hub.emit("agent", a.view())
        return web.json_response(a.view())

    async def approve(req):
        ap = hub.approvals.get(req.match_info["id"])
        if not ap:
            return web.json_response({"error": "gone"}, status=404)
        d = (await req.json()).get("decision", "deny")
        if not ap["future"].done():
            ap["future"].set_result(d)
        return web.json_response({"ok": True})

    async def dismiss(req):
        hub.alerts = [a for a in hub.alerts if a["id"] != req.match_info["id"]]
        hub.emit("alert_done", {"id": req.match_info["id"]})
        return web.json_response({"ok": True})

    r.add_get("/", index)
    r.add_get("/api/state", state)
    r.add_get("/api/agents/{name}/events", events)
    r.add_get("/api/stream", stream)
    r.add_post("/api/agents/{name}/send", send)
    r.add_post("/api/agents/{name}/{action}", control)
    r.add_post("/api/approvals/{id}", approve)
    r.add_post("/api/alerts/{id}/dismiss", dismiss)
    return app


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--person", required=True, choices=list(PEOPLE))
    ap.add_argument("--repo", required=True, help="the team repo the agents work in")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--data", default=None, help="hub state folder (default ~/.avalon-hub/<person>)")
    ap.add_argument("--namespace", default="", help="suffix for the Modal queue/dict (e.g. -test)")
    ap.add_argument("--no-autostart", action="store_true")
    ap.add_argument("--model", default=None, help="run every agent on this model (e.g. claude-haiku-5-5 for tests)")
    a = ap.parse_args()
    data = Path(a.data or Path.home() / ".avalon-hub" / a.person).expanduser()
    data.mkdir(parents=True, exist_ok=True)
    hub = Hub(a.person, Path(a.repo).expanduser().resolve(), data, a.namespace)
    hub.model_override = a.model
    await hub.bus.start()
    for ag in hub.agents.values():
        await hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task, "summary": ag.summary})
    runner = web.AppRunner(make_app(hub))
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", a.port).start()
    print(f"avalon hub ({PEOPLE[a.person]}): http://127.0.0.1:{a.port}   bus: "
          f"{'online' if hub.bus.online else hub.bus.error}", flush=True)
    if not a.no_autostart:
        for ag in hub.agents.values():
            if ag.spec.get("autostart"):
                await ag.start()

    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            for ag in hub.agents.values():
                await hub.bus.publish(ag.name, {"title": ag.title, "state": ag.state, "task": ag.task,
                                                "summary": ag.summary})
    asyncio.create_task(heartbeat())
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
