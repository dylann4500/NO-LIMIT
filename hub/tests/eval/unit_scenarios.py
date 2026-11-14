"""Scenario fixes from the 14 Nov walk-through: decisions (the rule applied at the deadline, opposite answers),
the clock (a false start corrected, questions never start it, a late round pins later ones), the portal (held
standings, a rejected live upload, cancelled/'final' rounds, the hands link from the Chat). No network, no model.
   uv run ... python hub/tests/eval/unit_scenarios.py hub"""
import asyncio, sys, tempfile, time, subprocess, json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import hub as H
H.os.environ["AVALON_NO_AGENTS"] = "1"
fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]")); cond or fails.append(name)

def mkhub(person):
    d = Path(tempfile.mkdtemp()); repo = d / "repo"; subprocess.run(["git", "init", "-q", str(repo)])
    (repo / "releases").mkdir()
    for v in ("v4", "v5", "v7"):
        (repo / "releases" / f"{v}.zip").write_bytes(b"PK\x05\x06" + b"\0" * 18)
    h = H.Hub(person, repo, d / "data", "-unit", None)
    async def nosend(msg): return "sent"
    h.bus.send = nosend
    return h

async def main():
    H.create_sdk_mcp_server = lambda name, tools, **kw: {t.name: t for t in tools}
    txt = lambda r: r["content"][0]["text"]
    # --- decisions
    h = mkhub("dylan"); lead = h.agents["d-overview"]; T = lead.tool_server()
    await h.make_live("releases/v4.zip", "test", tell=False)
    r = await T["propose"].handler({"kind": "bot", "title": "Which bot plays round 3?", "headline": "v5 clears the bar",
                                    "body": "rule...", "bot": "releases/v5.zip", "rule_answer": "releases/v5.zip",
                                    "deadline_minutes": 0.005})
    pid = txt(r).split("#")[1].split(" ")[0]
    p = h.get_prop(pid)
    check("the rule's answer is stored and stated first in the question", p.get("rule_answer") == "releases/v5.zip" and "v5 plays" in p["body"][:120], p.get("body", "")[:120])
    await asyncio.sleep(0.6); await h.expire_decisions()
    check("no answer by the deadline: the hub itself makes the rule's answer live", H.norm_bot((h.bus.shared.get("live") or {}).get("filename")) == "v5",
          str(h.bus.shared.get("live")))
    check("...and the bell says so", any("rule's answer" in a["text"] and "v5" in a["text"] for a in h.alerts))
    # opposite answers
    await h.make_live("releases/v4.zip", "test", tell=False)
    r = await T["propose"].handler({"kind": "bot", "title": "Which bot plays round 4?", "headline": "x", "body": "y",
                                    "bot": "releases/v7.zip", "rule_answer": "releases/v4.zip", "deadline_minutes": 5})
    pid = txt(r).split("#")[1].split(" ")[0]
    p = h.get_prop(pid); p["status"], p["decided_by"] = "approved", "Samuel"
    await h.make_live("releases/v7.zip", "Samuel", tell=False); await h.save_prop(p)
    await h.human_act(pid, "reject", "no, keep v4")
    p = h.get_prop(pid)
    check("Samuel yes + Dylan no: flagged as a conflict, back to waiting", p.get("conflict") and p["status"] == "needs_call", str(p.get("status")))
    check("...the rule's answer stands meanwhile", H.norm_bot((h.bus.shared.get("live") or {}).get("filename")) == "v4")
    check("...and both are told to talk", any("disagree" in a["text"] for a in h.alerts))
    # --- chat commands
    hs = mkhub("samuel")
    for q in ("when does the competition start?", "the competition starts in 10 minutes", "the event will start soon"):
        out = await hs.chat_command(q, "Samuel")
        check(f"'{q}' doesn't start the clock", out is None and not hs.bus.shared.get("schedule"), str(out))
    check("'run the tests on v3' is not the pre-flight", await hs.chat_command("run the tests on v3", "Samuel") is None)
    check("'run the check' is", H.PREFLIGHT_RX.search("run the check") and H.PREFLIGHT_RX.search("Check everything works."))
    # --- clock: a false start corrected later still fires the real minute 0; a small correction doesn't re-fire
    c = hs.clock
    now = time.time()
    old = {"start": now - 600, "scored": 6, "scale": 1.0}
    c.sent = {f"{int(old['start'])}:b0"}
    new = dict(old, start=now + 120)
    c.carry(old, new)
    check("false start corrected to the real minute 0: minute 0 fires again", f"{int(new['start'])}:b0" not in c.sent)
    c.sent = {f"{int(old['start'])}:b0"}
    new2 = dict(old, start=now - 560)
    c.carry(old, new2)
    check("a 40-second correction keeps minute 0 sent (no duplicate dispatch)", f"{int(new2['start'])}:b0" in c.sent)
    # false start 12 min early, corrected after the real minute 0 has passed: minute 0 still fires (late), once
    old = {"start": now - 12 * 60, "scored": 6, "scale": 1.0}
    c.sent = {f"{int(old['start'])}:b0"}
    new3 = dict(old, start=now - 2 * 60)
    c.carry(old, new3)
    check("false start corrected after the fact: the real minute 0 still fires", f"{int(new3['start'])}:b0" not in c.sent)
    # started 8 min late, corrected earlier: minute 0 already happened for real, no second dispatch
    old = {"start": now - 60, "scored": 6, "scale": 1.0}
    c.sent = {f"{int(old['start'])}:b0"}
    new4 = dict(old, start=now - 9 * 60)
    c.carry(old, new4)
    check("a late start corrected earlier: minute 0 isn't dispatched twice", f"{int(new4['start'])}:b0" in c.sent)
    # a pinned (late) round: its not-yet-due steps fire at the new time
    s0 = {"start": now - 85 * 60, "scored": 6, "scale": 1.0}   # round 2 expected 5 min ago
    c.sent = {f"{int(s0['start'])}:s3-20"}
    s1 = dict(s0, round_at={"2": now + 60})
    c.carry(s0, s1)
    check("round 2 pinned late: round 3's T-20 step (now in the future) fires again at its new time", f"{int(s0['start'])}:s3-20" not in c.sent)
    # --- portal
    key = Path(tempfile.mkdtemp()) / "k"; key.write_text("x")
    pw = H.PortalWatcher(hs, "http://portal", key, None, out=Path(tempfile.mkdtemp()))
    hs.portal = pw
    pw.team, pw.cid, pw.team_name = "T1", "C1", "avalon"
    pw.st["done"] = ["tour-abc123"]
    msg = pw.set_hands_url("https://portal/x/tournaments/tour-abc123/hands?subset=first-1000")
    check("hands link from the Chat: the round id becomes {tid}", pw.hands_url == "https://portal/x/tournaments/{tid}/hands{q}", pw.hands_url)
    check("...and it survives a restart", json.loads((hs.data / "portal_state.json").read_text()).get("hands_url") == pw.hands_url)
    pw.set_hands_url("https://portal/x/tournaments/tour-abc123/hands?subset=first-1000&sig=XYZ")
    check("a hands link with a signature keeps it and adds the subset correctly",
          pw.hands_url.replace("{tid}", "T9").replace("{qa}", "&subset=first-1000") == "https://portal/x/tournaments/T9/hands?sig=XYZ&subset=first-1000", pw.hands_url)
    for q in ("don't start the research yet", "did you start the research?"):
        check(f"'{q}' doesn't start the research", await hs.chat_command(q, "Samuel") is None)
    check("'reset the clock' empties the schedule (syncs as an empty value)", "cleared" in (await hs.chat_command("reset the clock", "Samuel") or "")
          and hs.bus.shared.get("schedule") == {})
    rounds = [{"id": "p1", "kind": "practice", "created_at": "2026-11-15T14:20:00", "completed_at": "x"},
              {"id": "s1", "kind": "final", "created_at": "2026-11-15T15:00:00"},
              {"id": "s0", "kind": "scored", "created_at": "2026-11-15T14:59:00", "cancelled_at": "x"}]
    calls = []
    async def aget(path, raw=False):
        calls.append(path)
        if path.endswith("/tournaments"): return {"items": [dict(r) for r in rounds]}
        if path.endswith("/standings"): raise RuntimeError("403 leaderboard held")
        if path == "/teams/T1": return {"name": "avalon", "active_submission_id": "u2", "active_filename": "v4.zip"}
        if path.endswith("/submissions"): return {"items": [{"id": "u2", "filename": "v4.zip", "status": "ready"},
                                                            {"id": "u3", "filename": "v7.zip", "status": "rejected", "rejection_reason": "timeout"}]}
        if path.startswith("/competitions/C1"): return {"name": "Finals"}
        if path.endswith("/results"): return {"items": []}
        return {}
    pw.aget = aget
    pw.st["baseline_done"] = True; pw.st["done"] = ["p1"]
    await hs.make_live("releases/v4.zip", "t", tell=False); await hs.make_live("releases/v7.zip", "t", tell=False)
    await pw.poll()
    check("held standings: the active-bot checks still run", any(c_.endswith("/submissions") for c_ in calls), str(calls[-4:]))
    check("...and the humans are told the leaderboard may be held", any("standings can't be read" in a["text"] for a in hs.alerts))
    check("a rejected upload of the declared live bot: the previous bot is live again", H.norm_bot((hs.bus.shared.get("live") or {}).get("filename")) == "v4",
          str(hs.bus.shared.get("live")))
    pb = pw.st.get("played_by", {})
    check("a 'final'-kind round counts as scored round 1; a cancelled round is ignored", pb.get("s1") and "s0" not in pb, str(pb))
    print("FAILED:", fails if fails else "none")
asyncio.run(main())
