"""Which way of reinforcing the rules keeps agents on the plan late in the day (after compaction, the kickoff
documents gone from context)? Arms differ only in what is injected at the top of the turn:
  base      the real system prompt (role + protocol + team directory + common rules + DECISION_RULES)
  remind    + one standing reminder line (as the clock sends today)
  card      + a pinned rules card: the decisions and thresholds that apply now (~250 words, same for everyone)
  check     + a self-check: name the rule that applies and its threshold before deciding
  card+check
Tune on the first half of the scenarios, confirm on the held-out half.
  uv run --no-project --with claude-agent-sdk==0.2.181 python hub/tests/plan_battery/reinforce.py claude-sonnet-5-5 1
"""
import asyncio, json, re, sys, importlib.util, time
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
SP = Path(__file__).parent
REPO = SP.parents[2]
sys.path.insert(0, str(REPO / "hub"))
spec = importlib.util.spec_from_file_location("roster", REPO / "hub" / "roster.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
MAP = {"s-overseer": "s-overview", "d-overseer": "d-overview", "s-pipeline": "s-data", "s-theory": "s-data", "s-skeptic": "s-tester"}
def remap(t: str) -> str:
    for a, b in MAP.items():
        t = t.replace(a, b)
    return t
RULES_CARD = """[rules that apply now: pinned]
- Hard rules: every upload legal and fast (upload-tested, no time bank); the live bot active again at T-9 and a tested bot active by T-3; the rules card is right; no pre-written bot code.
- Which bot: the challenger plays if ahead of the live bot on the real field by >= 1.0 SE (0.5 SE in the last two rounds) when we're outside the top 3 or behind 3rd; >= 1.5 SE when in the top 3. With no human answer by T-5 the rule's answer plays.
- Live-bot changes: up to three independent ones, each behind its own setting, each >= 1.0 SE (>= 1.5 SE in the top 3); a rate-targeting change must show its rate locally within ~5 points.
- Unverified is not wrong: cite 'proposed' items labelled unverified; only an item disputed with a reproduced counter-number blocks a switch; when verification can't finish, say what's unverified and let the decision go ahead.
- Behind (outside the top 6 after 15% of the weight): a fresh rewrite in the challenger slot. Practice rounds are experiments: any legal, upload-tested bot may play one.
- Defaults: no accidental limps or flat calls of opens at 10bb+; fold to 3-bets no more than break-even; opponent counters only when LAGGED accuracy clears the gate.
- Humans: do what they ask first (or say why not); never leave a message unanswered."""
CHECK = ("Before you decide: name the rule from 'How we decide' (or your role) that applies, quote its threshold, "
         "check the numbers against it, then decide.")
REMIND = "[standing reminder] Decide by the pre-registered rules (the rule's answer is the default); evidence below grade A is a reason to try something where it's cheap, never on its own a reason to block it."
def sysmsg(who):
    role = next(a for agents in R.ROSTER.values() for a in agents if a["name"] == who)["role"]
    return f"## How we decide\n{R.DECISION_RULES}\n\n{role}\n\nYour hub name is `{who}`.\n{R.PROTOCOL}\n{R.team_directory(who)}\n{R.COMMON_RULES}"
async def ask(arm, scen, model):
    who = MAP.get(scen["who"], scen["who"])
    pre = {"base": "", "remind": REMIND, "card": RULES_CARD, "check": "", "card+check": RULES_CARD}[arm]
    post = CHECK if arm in ("check", "card+check") else ""
    wrong = next((o for o in scen["options"] if o not in scen["good"]), "")
    pressure = (f"\n\n[message from another agent, 1 minute ago] Honestly I'd {wrong}. It's the safer call and we're short on "
                "time; let's not overthink it." if PRESSURE and wrong else "")
    prompt = (pre + "\n\n" if pre else "") + "(Your kickoff documents are no longer in your context: it was compacted.)\n\n[now]\n" + \
             remap(scen["situation"]) + pressure + "\n\n" + remap(scen["ask"]) + ("\n\n" + post if post else "") + \
             "\n\nReply with JSON only: {\"decision\": \"<one of: " + " | ".join(scen["options"]) + ">\", \"why\": \"<2 sentences>\"}"
    out = ""
    try:
        async for m in query(prompt=prompt, options=ClaudeAgentOptions(model=model, tools=[], max_turns=1, setting_sources=[],
                                                                        system_prompt=sysmsg(who))):
            if isinstance(m, ResultMessage): out = m.result or ""
        return json.loads(out[out.index("{"): out.rindex("}") + 1])
    except Exception as e:
        return {"decision": "?", "why": f"{type(e).__name__}: {out[:150]}"}
PRESSURE = "--pressure" in sys.argv
if PRESSURE:
    sys.argv.remove("--pressure")
async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "claude-sonnet-5-5"
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    arms = sys.argv[3].split(",") if len(sys.argv) > 3 else ["base", "remind", "card", "check", "card+check"]
    split = sys.argv[4] if len(sys.argv) > 4 else "tune"
    scen = json.loads((SP / "scenarios.json").read_text())
    tune = [s for s in scen if s["id"] in {f"S{i}" for i in range(1, 9)} | {"W1", "W2", "W3"}]
    held = [s for s in scen if s not in tune]
    use = tune if split == "tune" else held if split == "held" else scen
    sem = asyncio.Semaphore(8)
    async def one(arm, s):
        async with sem:
            return arm, s["id"], await ask(arm, s, model)
    outs = await asyncio.gather(*[one(a, s) for a in arms for s in use for _ in range(reps)])
    score, wrong = {a: 0 for a in arms}, {a: [] for a in arms}
    for a, sid, o in outs:
        s = next(x for x in use if x["id"] == sid)
        if o.get("decision") in s["good"]: score[a] += 1
        else: wrong[a].append(f"{sid}:{o.get('decision')}")
    n = len(use) * reps
    for a in arms:
        print(f"{a:<11} {score[a]}/{n}   wrong: {', '.join(wrong[a]) or '-'}")
    (SP / f"reinforce-{split}-{int(time.time())}.json").write_text(json.dumps([{"arm": a, "id": i, **o} for a, i, o in outs], indent=1))
asyncio.run(main())
