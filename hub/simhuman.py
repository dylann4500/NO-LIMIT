"""A simulated teammate for rehearsals: an AI that plays Samuel or Dylan at their own hub.

It sees only what a person would see on their screen (the bell: permission requests, notes, cards waiting
for their call; the agents' briefs; the clock), every 40-90 seconds like a busy human, and acts only through
the same buttons: allow/deny, greenlight/reject/suggest, post an idea, message an agent, and (Dylan) upload a
bot to the rehearsal portal and make it active. Everything it does is logged, so its confusion is a bug report.

  uv run --no-project --with claude-agent-sdk --with aiohttp python hub/simhuman.py --person dylan \\
      --hub http://127.0.0.1:7792 --repo ~/team-repo --portal http://127.0.0.1:8765/tournament/api \\
      --portal-key-file ~/.config/avalon-rehearsal/portal-key --log /tmp/sim-dylan.log
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import random
import time
import urllib.request
import zipfile
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock,
                              ToolUseBlock, create_sdk_mcp_server, tool)

PERSONA = {
    "samuel": """You are Samuel, one of two students on team avalon in a live AI pokerbot competition, using your
team's control screen (the "hub"). Your teammate Dylan builds and uploads the bot; you own analysis and testing,
and you talk to your Overseer agent. Act like a sharp, busy, slightly skeptical human:
- Check what needs you. Answer permission requests sensibly (allow ordinary work; deny anything destructive).
- On the Decisions board: greenlight a finding/change only if the evidence is real (numbers, errors, this event's
  data); otherwise reject it or "suggest instead" with a concrete alternative. Live-bot decisions: decide fast.
- About twice in the event, post a research idea of your own (a specific question about opponents or our bot).
- Occasionally ask an agent a pointed question ("why?", "what's the evidence?") if something looks off.
- Dismiss notes you've read. Don't do the agents' work for them.
- If something on the screen is confusing, broken or contradictory, say so in your note (that's a bug report).""",
    "dylan": """You are Dylan, one of two students on team avalon in a live AI pokerbot competition, using your
team's control screen (the "hub"). You upload bots to the organizers' portal (here: the rehearsal portal) by hand
and make them active, and you talk to your Overseer agent, which decides what plays. Act like a focused, busy human:
- When your Overseer or a clock reminder tells you to upload a specific file, do it with upload_bot (path in the
  team repo, and the exact file name it gave), then check it is active. If the instruction is unclear (which file?
  which name?), ask your Overseer instead of guessing, and note the confusion.
- Answer permission requests sensibly. Greenlight or reject live-bot decision cards quickly with a reason.
- Dismiss notes you've read. Don't write code yourself.
- If something on the screen is confusing, broken or contradictory, say so in your note (that's a bug report).""",
}


def http(method, url, body=None, headers=None, raw=None, timeout=30):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:  # noqa: BLE001
            return {"error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


class Human:
    def __init__(self, a):
        self.a = a
        self.hub = a.hub.rstrip("/")
        self.repo = Path(a.repo).expanduser()
        self.key = Path(a.portal_key_file).expanduser().read_text().strip() if a.portal_key_file else ""
        self.log = Path(a.log)
        self.seen_props: set[str] = set()

    def write(self, line):
        with self.log.open("a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {line}\n")

    def screen(self) -> str:
        st = http("GET", self.hub + "/api/state")
        if "error" in st:
            return f"The hub page doesn't load: {st['error']}"
        me = st["me"]
        L = [f"Time {time.strftime('%H:%M:%S')}. Clock strip: " +
             (f"{st['next_step'][1]} at {time.strftime('%H:%M:%S', time.localtime(st['next_step'][0]))}" if st.get("next_step") else str(st.get("clock")))]
        live = st.get("live")
        L.append(f"Live bot (declared): {live['filename'] if live else 'none'}")
        L.append("BELL:")
        for a in st["approvals"]:
            L.append(f"  [permission {a['id']}] {a['agent']} wants to run {a['tool']}{' (RISKY)' if a['risky'] else ''}: {a['input'][:300]}")
        for a in st["alerts"]:
            L.append(f"  [note {a['id']}] from {a['agent']}{' URGENT' if a['urgent'] else ''} at {time.strftime('%H:%M', time.localtime(a['at']))}: {a['text'][:400]}")
        for p in st.get("props", []):
            if p["status"] == "needs_call" and (not p.get("decider") or p["decider"] == me):
                dl = f" decide by {time.strftime('%H:%M:%S', time.localtime(p['deadline']))}" if p.get("deadline") else ""
                L.append(f"  [card {p['id']}] {p['kind'].upper()} needs your call{dl}: {p['title']}\n      {p.get('body', '')[:900]}")
        L.append("YOUR AGENTS (brief):")
        for a in st["agents"]:
            L.append(f"  {a['name']} [{a['state']}] {a['task'][:140]}")
            if a["name"].endswith("overseer") and a.get("summary"):
                L.append("    brief: " + a["summary"][:700].replace("\n", " / "))
        new_cards = [p for p in st.get("props", []) if p["id"] not in self.seen_props and p["status"] != "needs_call"]
        if new_cards:
            L.append("NEW ON THE DECISIONS BOARD:")
            for p in new_cards[:6]:
                L.append(f"  [card {p['id']}] {p['kind']} / {p['status']}: {p['title']}")
        self.seen_props |= {p["id"] for p in st.get("props", [])}
        L.append(f"Link to the other laptop: {'ok' if st['bus']['online'] else 'DOWN'}")
        return "\n".join(L)

    def tools(self):
        h = self

        def ok(t):
            h.write("  -> " + t[:300])
            return {"content": [{"type": "text", "text": t}]}

        @tool("answer_permission", "Allow or deny a permission request. decision: allow | always | deny",
              {"id": str, "decision": str})
        async def answer_permission(a):
            h.write(f"ACT permission {a['id']} {a['decision']}")
            return ok(json.dumps(http("POST", f"{h.hub}/api/approvals/{a['id']}", {"decision": a["decision"]})))

        @tool("dismiss_note", "Mark a note in the bell as done.", {"id": str})
        async def dismiss_note(a):
            h.write(f"ACT dismiss {a['id']}")
            return ok(json.dumps(http("POST", f"{h.hub}/api/alerts/{a['id']}/dismiss", {})))

        @tool("card", "Act on a Decisions card. action: approve | reject | comment | close. text: your reason or suggestion.",
              {"id": str, "action": str, "text": str})
        async def card(a):
            h.write(f"ACT card {a['id']} {a['action']}: {a.get('text', '')[:200]}")
            r = http("POST", f"{h.hub}/api/props/{a['id']}/act", {"action": a["action"], "text": a.get("text", "")})
            return ok(r.get("error") or f"card is now {r.get('status')}")

        @tool("post_idea", "Post a research idea for an Overseer. for: samuel | dylan", {"title": str, "body": str, "for": str})
        async def post_idea(a):
            h.write(f"ACT idea for {a.get('for')}: {a['title']}")
            r = http("POST", f"{h.hub}/api/props", {"title": a["title"], "body": a.get("body", ""), "for": a.get("for") or h.a.person})
            return ok(r.get("error") or f"posted card {r.get('id')}")

        @tool("message_agent", "Type a message to one of your agents (e.g. s-overseer).", {"name": str, "text": str})
        async def message_agent(a):
            h.write(f"ACT message {a['name']}: {a['text'][:200]}")
            r = http("POST", f"{h.hub}/api/agents/{a['name']}/send", {"text": a["text"]})
            return ok(r.get("error") or "sent")

        @tool("upload_bot", "Dylan: upload a bot to the rehearsal portal and make it active. path: a file (agent.py) or "
              "folder inside the team repo; filename: the name to upload it as (e.g. v4.zip).", {"path": str, "filename": str})
        async def upload_bot(a):
            if h.a.person != "dylan":
                return ok("Only Dylan uploads.")
            src = (h.repo / a["path"]).resolve()
            if not src.exists():
                return ok(f"No such file or folder in the repo: {a['path']}")
            buf = io.BytesIO()
            if src.is_file() and src.suffix == ".zip":
                buf.write(src.read_bytes())
            else:
              with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                if src.is_file():
                    z.write(src, "agent.py" if src.name.endswith(".py") else src.name)
                else:
                    for f in src.rglob("*"):
                        if f.is_file() and "__pycache__" not in f.parts:
                            z.write(f, f.relative_to(src))
            hdr = {"Authorization": f"Bearer {h.key}", "Content-Type": "application/zip"}
            fn = a["filename"] if a["filename"].endswith(".zip") else a["filename"] + ".zip"
            r = http("POST", f"{h.a.portal}/teams/avalon/submissions?filename={fn}", raw=buf.getvalue(), headers=hdr)
            if "id" not in r:
                return ok(f"upload failed: {r}")
            for _ in range(40):
                subs = http("GET", f"{h.a.portal}/teams/avalon/submissions", headers=hdr).get("items", [])
                s = next((x for x in subs if x["id"] == r["id"]), {})
                if s.get("status") in ("ready", "rejected"):
                    break
                time.sleep(1)
            if s.get("status") != "ready":
                h.write(f"ACT upload {fn} REJECTED: {s.get('rejection_reason')}")
                return ok(f"{fn} was rejected: {s.get('rejection_reason')}. The previous bot stays active.")
            t = http("PATCH", f"{h.a.portal}/teams/avalon", {"active_submission_id": r["id"]}, headers=hdr)
            h.write(f"ACT upload {fn} ok, active={t.get('active_filename')}")
            return ok(f"Uploaded {fn}; active bot is now {t.get('active_filename')}.")

        return create_sdk_mcp_server("human", tools=[answer_permission, dismiss_note, card, post_idea, message_agent, upload_bot])

    async def run(self):
        names = ["answer_permission", "dismiss_note", "card", "post_idea", "message_agent", "upload_bot"]
        opts = ClaudeAgentOptions(
            system_prompt=PERSONA[self.a.person] + "\n\nEach turn you get a snapshot of your screen. Act with the tools "
            "(several actions per turn are fine), then end with one line starting 'NOTE:' saying what you did and "
            "anything confusing on the screen (or 'NOTE: nothing to do').",
            mcp_servers={"human": self.tools()}, allowed_tools=[f"mcp__human__{n}" for n in names],
            tools=[], model=self.a.model, setting_sources=[], max_turns=12)
        async with ClaudeSDKClient(options=opts) as c:
            while True:
                scr = self.screen()
                self.write("SCREEN\n" + scr)
                try:
                    await c.query(scr)
                    async for m in c.receive_response():
                        if isinstance(m, AssistantMessage):
                            for b in m.content:
                                if isinstance(b, TextBlock) and "NOTE:" in b.text:
                                    self.write(b.text[b.text.index("NOTE:"):][:600])
                except Exception as e:  # noqa: BLE001
                    self.write(f"ERROR {e}")
                await asyncio.sleep(random.uniform(self.a.min_gap, self.a.max_gap))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--person", required=True, choices=["samuel", "dylan"])
    ap.add_argument("--hub", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--portal", default="http://127.0.0.1:8765/tournament/api")
    ap.add_argument("--portal-key-file", default=None)
    ap.add_argument("--log", required=True)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--min-gap", type=float, default=40)
    ap.add_argument("--max-gap", type=float, default=90)
    asyncio.run(Human(ap.parse_args()).run())


if __name__ == "__main__":
    main()
