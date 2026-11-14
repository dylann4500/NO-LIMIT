"""The lean hub's own pieces: report_progress tiles, the decision tile's life (asked -> decided / no answer), the
lead's context (decisions waiting, the board), direct clock dispatch to workers, roster consistency. No network,
no model.   uv run ... python hub/tests/eval/unit_lean.py hub"""
import asyncio, sys, tempfile, time, subprocess
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import hub as H, roster as R
fails = []
def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]")); cond or fails.append(name)

async def main():
    # roster: 4 per laptop, one lead each, every name the hub uses exists
    names = {a["name"] for p in R.ROSTER.values() for a in p}
    check("four agents per laptop", all(len(R.ROSTER[p]) == 4 for p in R.ROSTER), str({p: len(v) for p, v in R.ROSTER.items()}))
    check("one lead (the Chat) per laptop", all(sum(1 for a in R.ROSTER[p] if a.get("lead")) == 1 and R.ROSTER[p][0]["name"].endswith("overview") for p in R.ROSTER))
    check("every agent has a directory entry", names <= set(R.ASK_FOR), str(names - set(R.ASK_FOR)))
    check("dispatch, routes, fan-out and guard only name real agents",
          {ag for v in H.DISPATCH.values() for (_, _, ag, _) in v} <= names and {a for v in H.ROUTES.values() for (a, _, _) in v} <= names
          and set(H.FANOUT) <= names and {g[4] for g in H.GUARD} <= names | {"s-portal"})
    check("every worker gets a minute-0 task except the challenger (it starts at 40)",
          {ag for (_, _, ag, _) in H.DISPATCH["b0"]} == names - {"s-overview", "d-overview", "d-challenger"})
    check("no prompt mentions a removed agent", not any(x in (R.PROTOCOL + str(R.ROSTER) + str(R.ASK_FOR)) for x in ("s-overseer", "d-overseer", "s-pipeline", "s-skeptic", "s-theory")))

    d = Path(tempfile.mkdtemp()); repo = d / "repo"; subprocess.run(["git", "init", "-q", str(repo)])
    hub = H.Hub("dylan", repo, d / "data", "-unit", None)
    H.create_sdk_mcp_server = lambda name, tools, **kw: {t.name: t for t in tools}
    lead, plat = hub.agents["d-overview"], hub.agents["d-platform"]
    T = lambda ag: ag.tool_server()
    txt = lambda r: r["content"][0]["text"]
    # report_progress
    await T(plat)["report_progress"].handler({"item": "v1 and the platform", "state": "in progress"})
    t = next((x for x in hub.tiles() if x["label"] == "v1 and the platform"), None)
    check("report_progress makes a plain tile owned by the agent", t and t["state"] == "in progress" and t["owner"] == "d-platform", str(t))
    await T(plat)["report_progress"].handler({"item": "V1 and the Platform", "state": "done"})
    ts = [x for x in hub.tiles() if x["label"].lower() == "v1 and the platform"]
    check("the same item again updates it (no duplicate)", len(ts) == 1 and ts[0]["state"] == "done", str(ts))
    await T(plat)["report_progress"].handler({"item": "Maths", "state": "whatever"})
    check("unknown states fall back to 'in progress'", any(x["label"] == "Maths" and x["state"] == "in progress" for x in hub.tiles()))
    # bots feed tiles
    await hub.register_bot("releases/v3.zip", "testing", "", "d-builder"); await asyncio.sleep(0.05)
    check("a bot in testing shows as 'Bot v3 · testing'", any(x["label"] == "Bot v3" and x["state"] == "testing" for x in hub.tiles()))
    # a decision: asked -> tile waiting, both leads told; expired -> 'no answer'
    (repo / "releases").mkdir(exist_ok=True); (repo / "releases" / "v3.zip").write_bytes(b"PK\x05\x06" + b"\0" * 18)
    r = await T(lead)["propose"].handler({"kind": "decision", "title": "Which bot plays round 2?", "headline": "v3 is ahead by 1.2 SE",
                                          "body": "rule...", "bot": "releases/v3.zip", "deadline_minutes": 0.01})
    pid = txt(r).split("#")[1].split(" ")[0]
    dt = hub.bus.shared.get("tile:decide-" + pid) or {}
    check("asking a decision makes a 'waiting for your answer' tile", dt.get("state") == "waiting for your answer", str(dt))
    ctx = lead.overview_context()
    check("the lead's context lists it under WAITING FOR THE HUMANS' ANSWER", "WAITING FOR THE HUMANS' ANSWER" in ctx and pid in ctx.split("WAITING FOR")[1])
    check("the lead's context shows the progress board", "Bot v3: testing" in ctx)
    await asyncio.sleep(1.0); await hub.expire_decisions()
    check("no answer by the deadline: the tile says the rule decides", (hub.bus.shared.get("tile:decide-" + pid) or {}).get("state") == "no answer: the rule decides")
    # direct dispatch: the clock's worker tasks
    wt = H.worker_tasks("b0", "dylan")
    check("the clock's minute-0 tasks for Dylan's laptop go to Platform and Styles & fixes", {a for a, _, _ in wt} == {"d-platform", "d-builder"}, str(wt))
    check("the lead's dispatch text says the workers already have their tasks", "ALREADY given each worker" in H.dispatch_text("b0", "dylan"))
    print("FAILED:", fails if fails else "none")
asyncio.run(main())
