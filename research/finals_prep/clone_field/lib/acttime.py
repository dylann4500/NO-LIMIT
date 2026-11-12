"""Time Clone.act in-process over clone-only tables: acttime.py FIELD [tables]"""
import asyncio, json, os, random, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clonecore as cc
from poker_agent_protocol.game import Action
from poker_agent_protocol.runner import Reply
from poker_engine.play import play_table
from poker_engine.table import SitAndGo, TableRules
from poker_engine.variant import load_variant

field = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
F = json.load(open(field + "/field.json"))
cdf = json.load(open(field + "/cdf.json")) if os.path.exists(field + "/cdf.json") else None
T = []


class B:
    def __init__(self, c):
        self.c = c

    async def act(self, state, memory):
        t = time.perf_counter()
        a, m = self.c.act(state, memory)
        T.append((time.perf_counter() - t, state.phase, len(state.board)))
        return Reply(a, m)


bots = []
for e in F["entries"][:40]:
    p = json.load(open(os.path.join(field, e["folder"], "params.json")))
    p["cdf"] = cdf
    p["eps"] = 0.1
    bots.append(B(cc.Clone(p, Action)))
rules = TableRules(variant="flop_discard_reveal", players=8, decision_ms=1, time_bank_ms=100, hand_cap=250, hands_per_level=20)
v = load_variant(rules.variant)
t0 = time.perf_counter()
for i in range(n):
    rng = random.Random(i)
    asyncio.run(play_table(SitAndGo(rules=rules, variant=v, table_id=f"t{i}", seed=f"x:{i}"), rng.sample(bots, 8)))
el = time.perf_counter() - t0
xs = sorted(t[0] for t in T)
print(f"{n} tables {el:.1f}s single process ({n / el:.1f} tables/s); decisions {len(xs)}; act() total {sum(xs):.2f}s "
      f"mean {sum(xs) / len(xs) * 1e6:.0f}us p50 {xs[len(xs) // 2] * 1e6:.0f}us p99 {xs[int(len(xs) * .99)] * 1e6:.0f}us "
      f"p99.9 {xs[int(len(xs) * .999)] * 1e6:.0f}us max {xs[-1] * 1e6:.0f}us")
