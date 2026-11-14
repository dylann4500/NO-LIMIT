"""A simulated teammate for rehearsals: an AI that plays Samuel or Dylan at their own hub.

It sees only what a person would see on their screen (the bell: permission requests, notes, cards waiting
for their call; the agents' briefs; the clock), every 40-90 seconds like a busy human, and acts only through
the same controls: allow/deny, answering decision notes in words, post an idea, message an agent, and (Dylan) upload a
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

COMMON = """How the screen works: on the left, your agents: your Chat first (the lead of your side), then three
workers with one job each (Samuel: Analyst, Tester, Opponents; Dylan: Platform & releases, Styles & fixes, Challenger),
then your teammate's side. The Board shows only progress tiles ("Round 1 data · in progress", "Bot v3 · testing",
"Bot choice: v7 · waiting for your answer"); clicking a tile opens the agent doing it. Your Chat is your main
conversation: ask what's going on, tell it what to change. DECISIONS are asked in your Chat (a red box with the
question, the evidence and the deadline): answer in your own words with message_agent to your Chat ('yes, use v7' /
'no, keep v4 because ...'), after reading what's asked; ask first if unsure. To check on one job, read that worker's
brief (shown below) and steer or ask it for research directly with message_agent to that worker. The Live menu lists
bots; the bell shows permission requests and urgent messages."""

# Questions real people asked this hub during rehearsals (and ones they'd reasonably ask on the day). The simulated
# teammate asks some of these in its Chat or in a note, adapted to what's on screen, and rates each answer.
QUESTIONS = {
    "samuel": [
        "What's going on right now? Anything I need to do?",
        "Why is it testing an old bot while a newer one is live?",
        "What are the build notes (Build 1, 2, ...) and why are they still running?",
        "Is the live bot simple on purpose?",
        "What's our biggest leak this round, in plain words, with the sample size?",
        "Should we switch bots for the next scored round? What does the rule say?",
        "How sure are we about that number? Has anyone re-checked it?",
        "What did the field reward in practice: wide, shove or tight?",
        "Is anything blocked or behind schedule?",
        "What changed in the last 10 minutes?",
        "Are we using Modal and Codex enough, or is anyone idle?",
        "What does this permission request mean, and is it safe to allow?",
        "Which teams are we exploiting, and is the fingerprinting accurate enough to use?",
        "(to the Analyst) What's the single biggest leak in the last round, with n and the change you'd make?",
        "(to the Tester) Did the last candidate pass correctness, and how did it do paired against the live bot?",
        "(to Opponents) Research: does any team adapt to us after hand 40? 5 minutes max.",
    ],
    "dylan": [
        "What do I need to upload right now, if anything?",
        "Which file exactly is the live bot, and is it what the portal is running?",
        "Why did the upload get rejected and what happens now?",
        "What's the challenger and when is it ready?",
        "What exactly is the 'which bot?' decision asking me? Explain it simply.",
        "Is the bot on the portal the one we decided on?",
        "What happens if I don't answer the decision in time?",
        "What is Samuel's side working on right now?",
        "Are we on track for the next deadline?",
        "(to Platform & releases) Which exact file should I upload next, and is it upload-tested?",
        "(to the Challenger) What's different about the next challenger, and when will it be ready?",
    ],
}
ASK_RULES = """
Asking questions like a real teammate:
- About every third turn, ask ONE question: in your Chat (message_agent to s-overview / d-overview), or directly to
  the worker whose job it is (message_agent to that worker; the "(to ...)" questions). Prefer the bank below; adapt it to what's on screen; never ask the same thing twice. Questions bank:
{bank}
- On a later turn, once the answer has arrived, rate it in a line starting 'RATING:' as
  'RATING: <the question> | good / partial / bad / no answer | <why: correct? specific? plain words? timely?>'.
  'no answer' if nothing came within about 3 of your turns.
- Also add 'BUG:' lines for anything on the screen that looks wrong, stale, contradictory or confusing.
"""

PERSONA = {
    "samuel": COMMON + """

You are Samuel, one of two students on team avalon in a live AI pokerbot competition. Dylan uploads bots; you own
analysis and testing. Act like a sharp, busy, slightly skeptical human:
- If the clock is already set (the strip shows a countdown), never change it: minute 0 comes from the schedule. Only
  if the board shows a 'Start building' button and the variant is announced, press it with start_building.
- Follow the board's tiles. When a round's analysis is in progress, read the Analyst's brief and ask it a pointed
  question or steer it at least once per round (e.g. 'what's the sample size?', 'also check the 3-bet calls').
- Accept or push back on suggestions in the note chat. When a note is finished and stale, close it.
- About twice in the event, post an idea of your own.
- Answer permission requests sensibly. Don't do the agents' work.
- In your NOTE line, report whether the tiles, briefs and Chat are timely, informative and faithful, and anything confusing.""",
    "dylan": COMMON + """

You are Dylan, one of two students on team avalon in a live AI pokerbot competition. You upload bots to the
organizers' portal (here: the rehearsal portal) by hand and make them active. Act like a focused, busy human:
- When a bot becomes live (a decision you answered in the Chat, the Live menu, or an urgent bell message 'Upload X
  now'), click it in the Live menu and upload it with upload_from_live_menu (your normal way); use upload_bot only
  if the Live menu download fails. Check it's active.
- Follow the build tiles; open Platform & releases at least once and ask it something.
- Answer decisions in your Chat quickly, in words, with a reason, once you understand them. Answer permission requests sensibly. Don't write code.
- In your NOTE line, report whether the tiles, briefs and Chat are timely, informative and faithful, and anything confusing.""",
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
        L.append(f"BOARD tiles (current stage: {st.get('stage')}):")
        for t in (st.get("tiles") or [])[:18]:
            L.append(f"  [{t.get('stage', '?')}] {t['label']} · {t['state']} (opens {t.get('owner')})")
        waiting = [p for p in st.get("props", []) if p.get("status") == "needs_call" and p.get("kind") in ("bot", "question")]
        if waiting:
            L.append("WAITING FOR YOUR ANSWER (pinned at the top of your Chat):")
            for p in waiting:
                L.append(f"  {p['title']} (deadline {time.strftime('%H:%M:%S', time.localtime(p['deadline'])) if p.get('deadline') else 'none'}): "
                         f"{p.get('headline', '')} | {str(p.get('body', ''))[:600].replace(chr(10), ' / ')}")
        L.append("(old-style notes, for reference only):")
        ps = [p for p in st.get("props", []) if p.get("status") != "removed"]
        for p in sorted(ps, key=lambda p: -(p.get("updated") or 0))[:3]:
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
        L.append("YOUR AGENTS (brief, and its latest reply on its page):")
        for a in st["agents"]:
            L.append(f"  {a['name']} [{a['state']}] {a['task'][:140]}")
            if not a["name"].endswith("overview"):
                try:
                    evs = http("GET", f"{self.hub}/api/agents/{a['name']}/events?since={max(-1, (a.get('last_i') or 0) - 40)}").get("events", [])
                    last = [e for e in evs if e.get("type") == "text" and not e.get("sub")][-1:]
                    if last:
                        L.append(f"    latest reply ({time.strftime('%H:%M:%S', time.localtime(last[0]['t']))}): {str(last[0]['text'])[:400].replace(chr(10), ' / ')}")
                except Exception:  # noqa: BLE001
                    pass
            if a.get("summary"):
                L.append("    brief: " + a["summary"][:400].replace("\n", " / "))

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

        @tool("upload_from_live_menu", "Dylan's normal way: click a bot in the Live menu (downloads vN.zip from the hub) and "
              "upload that file to the portal, then make it active. name: e.g. v4.", {"name": str})
        async def upload_from_live_menu(a):
            if h.a.person != "dylan":
                return ok("Only Dylan uploads.")
            name = a["name"].removesuffix(".zip")
            try:
                with urllib.request.urlopen(f"{h.hub}/api/bots/{name}/download", timeout=40) as r:
                    data = r.read()
            except Exception as e:  # noqa: BLE001
                h.write(f"ACT live-menu download {name} FAILED: {e}")
                return ok(f"The Live menu download of {name} failed: {e}")
            hdr = {"Authorization": f"Bearer {h.key}", "Content-Type": "application/zip"}
            r = http("POST", f"{h.a.portal}/teams/avalon/submissions?filename={name}.zip", raw=data, headers=hdr)
            if "id" not in r:
                return ok(f"upload failed: {r}")
            s = {}
            for _ in range(60):
                subs = http("GET", f"{h.a.portal}/teams/avalon/submissions", headers=hdr).get("items", [])
                s = next((x for x in subs if x["id"] == r["id"]), {})
                if s.get("status") in ("ready", "rejected"):
                    break
                time.sleep(1)
            if s.get("status") != "ready":
                h.write(f"ACT upload {name}.zip (live menu) REJECTED: {s.get('rejection_reason')}")
                return ok(f"{name}.zip was rejected: {s.get('rejection_reason')}. The previous bot stays active.")
            t = http("PATCH", f"{h.a.portal}/teams/avalon", {"active_submission_id": r["id"]}, headers=hdr)
            h.write(f"ACT upload {name}.zip (live menu) ok, active={t.get('active_filename')}")
            return ok(f"Uploaded {name}.zip from the Live menu; active bot is now {t.get('active_filename')}.")

        return create_sdk_mcp_server("human", tools=[answer_permission, dismiss_note, note_action, note_chat, make_live,
                                                     start_building, post_idea, message_agent, upload_bot, upload_from_live_menu])

    async def run(self):
        names = ["answer_permission", "dismiss_note", "note_action", "note_chat", "make_live", "start_building", "post_idea",
                 "message_agent", "upload_bot", "upload_from_live_menu"]
        opts = ClaudeAgentOptions(
            system_prompt=PERSONA[self.a.person] + ASK_RULES.format(bank="\n".join("  - " + q for q in QUESTIONS[self.a.person]))
            + "\n\nEach turn you get a snapshot of your screen. Act with the tools "
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
                                if isinstance(b, TextBlock):
                                    for ln in b.text.splitlines():
                                        if ln.strip().startswith(("NOTE:", "RATING:", "BUG:")):
                                            self.write(ln.strip()[:700])
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
