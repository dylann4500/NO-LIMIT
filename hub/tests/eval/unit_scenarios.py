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
    # pattern kills are refused (they match the agents' own processes); a PID kill is fine
    ag = hs.agents["s-tester"]
    for cmd in ('pkill -f "modal run"', "killall python3", "pgrep -f compare.py | xargs kill", "kill -9 $(pgrep -f run4.sh)"):
        r_ = await ag.can_use_tool("Bash", {"command": cmd}, None)
        check(f"refused: {cmd}", type(r_).__name__ == "PermissionResultDeny" and "by PID" in getattr(r_, "message", ""))
    r_ = await ag.can_use_tool("Bash", {"command": "kill $(cat /tmp/paired.pid); modal app stop ap-123"}, None)
    check("allowed: kill by PID file, modal app stop", type(r_).__name__ == "PermissionResultAllow", str(r_))
    # no permission prompts: ordinary commands run, dangerous ones and blocking waits are refused with the reason
    for cmd, want in (("python3 run.py --n 2000 > /tmp/x.log 2>&1 &", "Allow"), ("git push origin builder", "Allow"),
                      ("rm -rf ~/Documents", "Deny"), ("git push --force origin main", "Deny"),
                      ("for b in a b; do modal run x.py & done; wait; echo done", "Deny"), ("sleep 120 && cat log", "Deny"),
                      ("sleep 3; tail log", "Allow"), ("python3 -c 'import asyncio; asyncio.run(main())  # await x'", "Allow")):
        r_ = await ag.can_use_tool("Bash", {"command": cmd}, None)
        check(f"{want.lower()}: {cmd[:40]}", type(r_).__name__ == "PermissionResult" + want, getattr(r_, "message", "")[:80])
    check("no approval was ever queued for a human", not hs.approvals)
    # answer-first: a worker's message from a person counts as answered only by a reply that starts with their name
    from claude_agent_sdk import AssistantMessage, TextBlock
    hd = mkhub("dylan"); pl = hd.agents["d-platform"]
    await pl.human("which zip do I upload?", "Dylan")
    pl.turn_started = time.time() + 1
    pl.handle(AssistantMessage(content=[TextBlock(text="Running the no-bank test on v4 now.")], model="m", parent_tool_use_id=None))
    check("a reply that ignores the person doesn't clear the question", len(pl.pending_q) == 1)
    pl.handle(AssistantMessage(content=[TextBlock(text="Dylan: upload releases/v4.zip, it passed.")], model="m", parent_tool_use_id=None))
    check("a reply that starts with their name clears it", not pl.pending_q)
    # one plan challenge from one agent = one alert, however many recipients and wordings
    sc = hs.agents["s-scout"]; Ts = sc.tool_server(); n0 = len(hs.alerts)
    for to, txt_ in (("s-overview", "PLAN CHALLENGE p1: the field folds 75% to 3-bets"), ("d-overview", "PLAN CHALLENGE practice1: folds to 3-bets 74.8%"),
                     ("d-challenger", "PLAN CHALLENGE (for challenger-2): field folds a lot")):
        await Ts["send_message"].handler({"to": to, "text": txt_, "kind": "task"})
    check("one plan challenge, three recipients: one alert", len(hs.alerts) - n0 == 1, str([a["text"][:50] for a in hs.alerts[n0:]]))
    check("...and it's one line, not a pop-up", not hs.alerts[-1].get("urgent") and len(hs.alerts[-1]["text"]) < 300)
    # the team chat: each laptop's lines under its own key, merged in time order
    await hs.team_say("ready for practice 2?", []); await hd.team_say("yes", [])
    hs.bus.shared.update({k: v for k, v in hd.bus.shared.items() if k.startswith("tchat:")})
    tc = hs.team_chat()
    check("team chat merges both people's lines in time order", [x["who"] for x in tc][-2:] == ["Samuel", "Dylan"], str(tc))
    # build-hour practice picks: the upload reminder follows the declared bot
    check("practice reminders follow the declared bot (UPLOAD)", all(H.HUMAN_STEPS[k]["dylan"] == "UPLOAD" for k in ("b17", "b27", "b37", "b47")))
    # the Live menu says "tested" until a zip exists
    hs.bus.shared["bot:v9"] = {"file": "releases/v9.zip", "status": "ready", "at": time.time()}
    m9 = next(b for b in hs.bots_for_menu() if b["name"] == "v9")
    check("a bot marked ready with no zip anywhere shows as 'tested'", m9["status"] == "tested", m9["status"])
    # the model's contradiction guess goes to the lead only, never into the humans' Chat
    async def fake_one_shot(*a, **k): return '[{"issue": "declared v3 but portal runs v6", "fix": "check"}]'
    H.one_shot = fake_one_shot
    hs.bus.shared["schedule"] = {"start": time.time() - 600, "scored": 6, "scale": 1.0}
    lead = hs.agents["s-overview"]; before = len(lead.ovchat); hs.last_consistency = 0
    await hs.consistency_check()
    check("contradiction guess: nothing in the Chat", len(lead.ovchat) == before, str(lead.ovchat[before:])[:200])
    check("...the lead gets it, marked as a guess", any("a model's guess" in i.get("text", "") for i in lead.items))
    # review fixes: routine deletes in the agent's own places are allowed; risky ones refused; worktree git is its own business
    rp = str(hs.repo.resolve())
    for cmd, want in ((f"rm -rf {rp}/build", "Allow"), ("rm -rf build/ && python3 b.py", "Allow"), ("find . -name '*.pyc' -delete", "Allow"),
                      ("unlink /tmp/s-tester/job.pid", "Allow"), ("rm -rf ~/Documents", "Deny"), (f"rm -rf {rp}", "Deny"),
                      ("rm -rf ../other", "Deny"), ("git stash", "Deny"),
                      ("cat > x.sh <<'EOF'\nsleep 30\nEOF\nbash x.sh &", "Allow"), ("nohup sh -c 'sleep 60; ls' > /tmp/x &", "Allow"),
                      ("while ! test -f out; do sleep 5; done", "Deny"), ("sleep 2m", "Deny")):
        r_ = await ag.can_use_tool("Bash", {"command": cmd}, None)
        check(f"review: {want.lower()} {cmd[:38]!r}", type(r_).__name__ == "PermissionResult" + want, getattr(r_, "message", "")[:70])
    r_ = await ag.can_use_tool("Bash", {"command": "sleep 300", "run_in_background": True}, None)
    check("a background Bash call may sleep", type(r_).__name__ == "PermissionResultAllow")
    wt = hd.agents["d-builder"]; wt.cwd = Path(tempfile.mkdtemp())
    r_ = await wt.can_use_tool("Bash", {"command": "git stash && git rebase origin/main"}, None)
    check("git stash/rebase in an agent's own worktree is allowed", type(r_).__name__ == "PermissionResultAllow", getattr(r_, "message", "")[:60])
    # a stale unanswered question doesn't hide newer ones
    pl.pending_q = [{"who": "Dylan", "text": "old", "at": time.time() - 900, "nudged": True, "told": True},
                    {"who": "Dylan", "text": "new", "at": time.time() - 200}]
    pl.items.clear(); await hd.watch_unanswered()
    check("a stale question is dropped and the newer one is nudged", [q["text"] for q in pl.pending_q] == ["new"] and any("new" in i.get("text", "") for i in pl.items))
    # a re-registration on a laptop without the zip keeps its fingerprint
    hs.bus.shared["bot:v12"] = {"file": "releases/v12.zip", "status": "ready", "at": time.time(), "sha256": "abc", "size": 10}
    await hs.register_bot("releases/v12.zip", "ready", "tested again", "s-tester")
    check("re-registering keeps the zip's sha", (hs.bus.shared.get("bot:v12") or {}).get("sha256") == "abc")
    print("FAILED:", fails if fails else "none")
asyncio.run(main())
