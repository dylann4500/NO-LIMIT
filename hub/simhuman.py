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

COMMON = """How the screen works: the board of notes is everything. Notes are grouped by stage of the day (Build,
Practice 1-4, Round 1, Round 1.5, ...). Each note is a conversation with an Overseer: it posts live updates there,
and you can ask questions or steer with note_chat (it reaches the Overseer, which hands the work to agents and
answers in the note). 'Analysis for <stage>' notes hold the round's analysis, a pinned summary with numbered
suggestions, and progress. 'Which bot?' notes ask whether to use a bot: answer with note_action approve/reject.
The Live menu lists bots; make_live makes a ready bot live. Close (note_action remove) notes that are finished
and no longer relevant. The bell shows permission requests and urgent messages. Your main conversation is your Overview
(message_agent to s-overview for Samuel, d-overview for Dylan): a readable chat that knows everything the
Overseer knows. Ask it what's going on and steer through it (it passes instructions to the Overseer). You
don't message the Overseer directly. The screen shows the last lines of your Overview chat."""

PERSONA = {
    "samuel": COMMON + """

You are Samuel, one of two students on team avalon in a live AI pokerbot competition. Dylan uploads bots; you own
analysis and testing. Act like a sharp, busy, slightly skeptical human:
- If the board has a 'Start building' button and the variant is announced (the clock says so or minute 0 is now),
  press it with start_building.
- Follow the current stage's notes. Open the newest analysis note and read its updates; ask a pointed question or
  steer there at least once per analysis note (e.g. 'what's the sample size?', 'also check the 3-bet calls').
- Accept or push back on suggestions in the note chat. When a note is finished and stale, close it.
- About twice in the event, post an idea of your own.
- Answer permission requests sensibly. Don't do the agents' work.
- In your NOTE line, report whether the note updates are timely, informative and faithful, and anything confusing.""",
    "dylan": COMMON + """

You are Dylan, one of two students on team avalon in a live AI pokerbot competition. You upload bots to the
organizers' portal (here: the rehearsal portal) by hand and make them active. Act like a focused, busy human:
- When a bot becomes live (a 'Which bot?' note you approved, the Live menu, or an urgent bell message 'Upload X
  now'), upload exactly that file with upload_bot and check it's active.
- Follow the Build notes and ask your Overseer a question in one of them at least once.
- Answer 'Which bot?' notes quickly with a reason. Answer permission requests sensibly. Don't write code.
- In your NOTE line, report whether the note updates are timely, informative and faithful, and anything confusing.""",
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
        bots = st.get("bots") or []
        L.append(f"LIVE MENU: declared live {live['filename'] if live else 'none'}; active on portal "
                 f"{(st.get('portal_active') or {}).get('filename') or 'unknown'}; bots: "
                 + (", ".join(f"{b['name']} ({b['status']}, file {b['file']})" for b in bots[:10]) or "none"))
        if not st.get("schedule"):
            L.append("BOARD: a big 'Start building' button (the clock hasn't started).")
        L.append(f"BOARD (current stage: {st.get('stage')}):")
        ps = [p for p in st.get("props", []) if p.get("status") != "removed"]
        for p in sorted(ps, key=lambda p: -(p.get("updated") or 0))[:14]:
            call = p["status"] == "needs_call" and (not p.get("decider") or p["decider"] in (me, "both"))
            L.append(f"  [note {p['id']}] {p.get('stage', '?')} · {p['kind']} · {p['status']}{' · YOUR CALL' if call else ''}: {p['title']}")
            if p.get("body"):
                L.append("      summary: " + p["body"][:700].replace("\n", " / "))
            for t in (p.get("thread") or [])[-3:]:
                L.append(f"      {time.strftime('%H:%M:%S', time.localtime(t['at']))} {t['who']}: {str(t['text'])[:500].replace(chr(10), ' / ')}")
        ovn = ("s" if me == "samuel" else "d") + "-overview"
        ov = (st.get("overviews") or {}).get(ovn, [])
        if ov:
            L.append("YOUR OVERVIEW CHAT (latest last):")
            for t in ov[-4:]:
                L.append(f"  {time.strftime('%H:%M:%S', time.localtime(t['at']))} {t['who']}: {t['text'][:1200].replace(chr(10), ' / ')}")
        L.append("YOUR AGENTS (brief):")
        for a in st["agents"]:
            L.append(f"  {a['name']} [{a['state']}] {a['task'][:140]}")
            if a["name"].endswith("overseer") and a.get("summary"):
                L.append("    brief: " + a["summary"][:700].replace("\n", " / "))

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

        @tool("note_action", "Act on a note: approve | reject (a 'Which bot?' or question note) | remove (close it). text: optional reason.",
              {"id": str, "action": str, "text": str})
        async def note_action(a):
            h.write(f"ACT note {a['id']} {a['action']}: {a.get('text', '')[:200]}")
            r = http("POST", f"{h.hub}/api/props/{a['id']}/act", {"action": a["action"], "text": a.get("text", "")})
            return ok(r.get("error") or f"note is now {r.get('status')}")

        @tool("note_chat", "Type in a note's chat: a question or an instruction for the Overseer.", {"id": str, "text": str})
        async def note_chat(a):
            h.write(f"ACT chat {a['id']}: {a['text'][:200]}")
            r = http("POST", f"{h.hub}/api/props/{a['id']}/ask", {"text": a["text"]})
            return ok(r.get("error") or "sent")

        @tool("make_live", "Live menu: make a ready bot live (file as listed).", {"file": str})
        async def make_live(a):
            h.write(f"ACT make live {a['file']}")
            r = http("POST", f"{h.hub}/api/live", {"file": a["file"]})
            return ok(r.get("error") or f"live is now {r.get('filename')}")

        @tool("start_building", "Press the Start building button (minute 0).", {})
        async def start_building(a):
            h.write("ACT start building")
            r = http("POST", f"{h.hub}/api/start", {})
            return ok(r.get("error") or "started")

        @tool("post_idea", "Post a research idea for an Overseer. for: samuel | dylan", {"title": str, "body": str, "for": str})
        async def post_idea(a):
            h.write(f"ACT idea: {a['title']}")
            r = http("POST", f"{h.hub}/api/props", {"title": a["title"], "body": a.get("body", "")})
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

        return create_sdk_mcp_server("human", tools=[answer_permission, dismiss_note, note_action, note_chat, make_live, start_building, post_idea, message_agent, upload_bot])

    async def run(self):
        names = ["answer_permission", "dismiss_note", "note_action", "note_chat", "make_live", "start_building", "post_idea",
                 "message_agent", "upload_bot"]
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
