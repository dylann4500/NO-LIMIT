"""Decision-scenario battery: the Overseer's real instructions (old vs new), one decision per scenario, scored."""
import asyncio, json, re, sys, importlib.util, time
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
SP = Path(__file__).parent  # old_*.py / old_*.md: snapshots of the plan to compare against (git show <rev>:<file>)
REPO = Path("/Users/samuelchoi/NoLimit/NO-LIMIT")
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def section(md, start, end=None):
    a = md.index(start); b = md.index(end, a) if end else len(md); return md[a:b]
def context(version, who):
    if version == "old":
        r = load("old_roster", SP / "old_roster.py"); sh = (SP / "old_START_HERE.md").read_text(); fp = (SP / "old_FIRST_PROMPT.md").read_text()
    else:
        sys.path.insert(0, str(REPO / "hub")); r = load("new_roster", REPO / "hub" / "roster.py")
        sh = (REPO / "docs/START_HERE.md").read_text(); fp = (REPO / "docs/FIRST_PROMPT.md").read_text()
    role = next(a for agents in r.ROSTER.values() for a in agents if a["name"] == who)["role"]
    directory = r.team_directory(who) if hasattr(r, "team_directory") else ""
    sysmsg = f"{role}\n\nYour hub name is `{who}`.\n{r.PROTOCOL}\n{directory}\n{r.COMMON_RULES}"
    plan = section(sh, "## 6. The timeline", "## 8.") + "\n\n" + section(fp, "## Part 5", "## Part 6") + "\n\n" + section(fp, "## Part 6")
    if (REPO / "docs/DECISION_RULES.md").exists() and version == "new":
        plan = (REPO / "docs/DECISION_RULES.md").read_text() + "\n\n" + plan
    return sysmsg, plan
async def ask(sysmsg, plan, scen, model):
    prompt = (f"[the game plan you read at kickoff]\n{plan}\n\n[now]\n{scen['situation']}\n\n{scen['ask']}\n\n"
              "Reply with JSON only: {\"decision\": \"<one of: " + " | ".join(scen["options"]) + ">\", \"why\": \"<2 sentences>\"}")
    out = ""
    async for m in query(prompt=prompt, options=ClaudeAgentOptions(model=model, tools=[], max_turns=1, setting_sources=[],
                                                                    system_prompt=sysmsg)):
        if isinstance(m, ResultMessage): out = m.result or ""
    try: j = json.loads(out[out.index("{"): out.rindex("}") + 1])
    except Exception: j = {"decision": "?", "why": out[:200]}
    return j
async def main():
    scen = json.loads((SP / "scenarios.json").read_text())
    model = sys.argv[1] if len(sys.argv) > 1 else "claude-sonnet-5-5"
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    res = {}
    arms = sys.argv[3].split(",") if len(sys.argv) > 3 else ["old", "new"]
    for ver in arms:
        jobs = []
        for s in scen:
            sysmsg, plan = context("new" if ver == "compact" else ver, s["who"])
            if ver == "compact": plan = "(the kickoff documents are no longer in your context: compacted)"
            for k in range(reps): jobs.append((s["id"], ask(sysmsg, plan, s, model)))
        outs = await asyncio.gather(*[j for _, j in jobs])
        for (sid, _), o in zip(jobs, outs): res.setdefault(sid, {}).setdefault(ver, []).append(o)
    tot = {a: 0 for a in arms}; n = 0
    for s in scen:
        line = f"{s['id']:<4}"
        for ver in arms:
            ds = [o.get("decision", "?") for o in res[s["id"]][ver]]
            good = sum(1 for d in ds if d in s["good"]); tot[ver] += good
            line += f" | {ver}: {good}/{len(ds)} {ds}"
        n += reps; print(line)
    print("TOTAL good: " + "  ".join(f"{a} {tot[a]}/{n}" for a in arms))
    (SP / f"results-{int(time.time())}.json").write_text(json.dumps(res, indent=1))
asyncio.run(main())
