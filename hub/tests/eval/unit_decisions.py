"""Decisions are made in words, not buttons: the Overseer can record a decision only after a human answered in the
note; approving a 'Which bot?' note makes that bot live. Also: a running clock isn't moved by a message without a
time. No network, no model.   uv run ... python hub/tests/eval/unit_decisions.py hub"""
import asyncio, sys, tempfile, time, subprocess
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import hub as H

fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]")); cond or fails.append(name)

async def main():
    d = Path(tempfile.mkdtemp()); repo = d / "repo"; subprocess.run(["git", "init", "-q", str(repo)])
    hub = H.Hub("dylan", repo, d / "data", "-unit", None)
    captured = {}
    H.create_sdk_mcp_server = lambda name, tools, **kw: {t.name: t for t in tools}
    ov = hub.agents["d-overseer"]
    tools = ov.tool_server()
    up = lambda **a: tools["update_proposal"].handler(a)
    txt = lambda r: r["content"][0]["text"]
    (repo / "releases").mkdir(); (repo / "releases" / "v7.zip").write_bytes(b"PK\x05\x06" + b"\0" * 18)
    p = {"id": "PDEC1", "kind": "bot", "title": "Which bot? v7", "bot": "releases/v7.zip", "status": "needs_call",
         "created": time.time() - 5, "thread": [], "author": "d-overseer", "author_person": "dylan", "owner": "d-overseer",
         "decider": "both", "stage": "Round 1.5"}
    await hub.save_prop(p)
    r = await up(id="PDEC1", status="approved", decided_by="Dylan")
    check("no decision without a human answer in the note", "No human has answered" in txt(r) and hub.get_prop("PDEC1")["status"] == "needs_call", txt(r))
    check("nothing made live", not (hub.bus.shared.get("live") or {}).get("filename"))
    hub.note_pending.clear()
    p = hub.get_prop("PDEC1"); p["thread"].append({"who": "Dylan", "at": time.time(), "action": "ask", "text": "yes, use v7"}); await hub.save_prop(p)
    r = await up(id="PDEC1", status="approved", decided_by="Dylan")
    check("a clear human answer is recorded", hub.get_prop("PDEC1")["status"] == "approved" and hub.get_prop("PDEC1")["decided_by"] == "Dylan", txt(r))
    check("approving a Which-bot note makes that bot live", (hub.bus.shared.get("live") or {}).get("filename") == "v7.zip")
    r = await up(id="PDEC1", status="rejected", decided_by="Dylan")
    check("a decided note can't be flipped by the agent", hub.get_prop("PDEC1")["status"] == "approved", txt(r))
    # clock: a running clock is not moved by a message without a time
    await hub.clock.set_start("", 6, 1.0, t0=time.time())
    t0 = hub.bus.shared["schedule"]["start"]
    chat = hub.agents["d-overview"]; ctools = chat.tool_server()
    chat.human_in_turn, chat.human_text_in_turn = True, "ok it's starting now"
    r = await ctools["set_schedule"].handler({"event": "minute0", "in_minutes": 0})
    check("vague 'starting now' doesn't move a running clock", hub.bus.shared["schedule"]["start"] == t0 and "never moves it" in txt(r), txt(r))
    chat.human_text_in_turn = "practice 1 started at 14:25"
    print("      (with a time, set_schedule proceeds:", txt(await ctools["set_schedule"].handler({"event": "practice1", "at": "14:25"}))[:80], ")")
    # the Chat's pending-answer tracking
    await chat.ov_log("Dylan", "what's the live bot?")
    check("a human message is tracked until answered", len(chat.pending_q) == 1)
    await chat.ov_log("Chat", "v7, since 14:30")
    check("the Chat's reply clears it", chat.pending_q == [])
    print("FAILED:", fails if fails else "none")

asyncio.run(main())
