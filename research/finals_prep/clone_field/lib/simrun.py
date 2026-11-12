"""Simulate a candidate bot against a fitted clone field on the kit's engine.

usage (kit Python, from anywhere):
  python simrun.py --field FIELDDIR --hero /abs/bots/v3b --tables 4000 --seed S --out OUT.pkl
  --hero none        : clone-only tables (8 clones), for calibration
Each table: the hero plus 7 distinct clones drawn in proportion to field weights (tables met),
from a stream that depends only on (seed, table number); hero seat and the deck (kit table seed
"<seed>:<n>", one deck stream per hand number) are the same for every candidate -> paired runs.
Clones run in-process (no time limit applied to them); the hero is a real kit bot process
with the kit's 1 ms limit and 100 ms bank.
"""
import argparse, asyncio, json, multiprocessing, os, pickle, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def worker(job):
    a, first, count = job
    return asyncio.run(run(a, first, count))


async def run(a, first, count):
    import clonecore as cc
    import fitlib
    from poker_agent_protocol.game import Action
    from poker_agent_protocol.process import BotPool
    from poker_agent_protocol.runner import BotError, Reply
    from poker_engine.play import play_table
    from poker_engine.scoring import table_places, table_points
    from poker_engine.table import SitAndGo, TableRules
    from poker_engine.variant import load_variant

    field = json.load(open(os.path.join(a.field, "field.json")))
    cdf = None
    cp = a.cdf or os.path.join(a.field, "cdf.json")
    if os.path.exists(cp) and not a.no_cdf:
        cdf = json.load(open(cp))
    adj = None
    ap_ = a.adj or os.path.join(a.field, "adj.json")
    if os.path.exists(ap_) and not a.no_adj:
        adj = json.load(open(ap_))
    beta = [float(x) for x in a.beta.split(",")]

    class InProc:
        def __init__(self, clone):
            self.clone = clone

        async def act(self, state, memory):
            try:
                act, mem = self.clone.act(state, memory)
            except Exception as e:  # counted as a failed decision, like a crashing bot
                raise BotError(repr(e))
            return Reply(act, mem)

    names, weights, bots = [], [], {}
    for e in field["entries"]:
        p = json.load(open(os.path.join(a.field, e["folder"], "params.json")))
        if cdf:
            p["cdf"] = cdf
        if adj and e["team"] in adj:
            for k, v in adj[e["team"]].items():
                p["cells"][k] = v
        p["eps"] = a.eps
        p["beta"] = [0.0] + beta
        names.append(e["team"])
        weights.append(e["weight"])
        bots[e["team"]] = InProc(cc.Clone(p, Action))
    hero_pool = None
    if a.hero != "none":
        hero_pool = BotPool([sys.executable, "-m", "poker_agent_sdk.guest", a.hero], copies=1, cwd=a.hero)
    rules = TableRules(variant="flop_discard_reveal", players=8, decision_ms=1, time_bank_ms=a.bank,
                       hand_cap=250, hands_per_level=20)
    variant = load_variant(rules.variant)
    acc = fitlib.new_acc()
    rows = []
    nopp = 7 if hero_pool else 8
    try:
        for n in range(first, first + count):
            rng = random.Random(f"{a.seed}:opps:{n}")
            hero_seat = rng.randrange(8)
            opps = []
            while len(opps) < 8:   # always draw 8 so hero and clone-only runs share opponents
                t = rng.choices(names, weights)[0]
                if t not in opps:
                    opps.append(t)
            seat_names = opps[:7]
            if hero_pool:
                seat_names.insert(hero_seat, "HERO")
            else:
                seat_names.insert(hero_seat, opps[7])
            seats = [hero_pool if x == "HERO" else bots[x] for x in seat_names]
            table = SitAndGo(rules=rules, variant=variant, table_id=f"t{n}", seed=f"{a.seed}:{n}")
            result = await play_table(table, seats)
            pts = table_points(result, table.payouts)
            places = table_places(result)
            fitlib.add_table(acc, {"seats": seat_names, "hands": table.log}, {})
            rows.append((n, hero_seat, pts[hero_seat], places[hero_seat], result.hands_played,
                         result.failures[hero_seat], result.decisions[hero_seat],
                         sum(result.failures) - result.failures[hero_seat]))
    finally:
        if hero_pool:
            await hero_pool.stop()
    return rows, acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    ap.add_argument("--hero", default="none")
    ap.add_argument("--tables", type=int, default=400)
    ap.add_argument("--first-table", type=int, default=0)
    ap.add_argument("--seed", default="s1")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--bank", type=int, default=100)
    ap.add_argument("--eps", type=float, default=0.0, help="share of decisions taken with a random strength")
    ap.add_argument("--beta", default="0,0,0", help="bluff share of bets when checked to: flop,turn,river")
    ap.add_argument("--cdf", default=None)
    ap.add_argument("--no-cdf", action="store_true")
    ap.add_argument("--adj", default=None)
    ap.add_argument("--no-adj", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.hero != "none":
        a.hero = os.path.abspath(a.hero)
    import fitlib
    per = 25
    jobs = [(a, f, min(per, a.first_table + a.tables - f))
            for f in range(a.first_table, a.first_table + a.tables, per)]
    t0 = time.perf_counter()
    rows, acc = [], fitlib.new_acc()
    with multiprocessing.Pool(a.workers, maxtasksperchild=8) as pool:
        for r, part in pool.imap_unordered(worker, jobs):
            rows += r
            fitlib.merge(acc, part)
    el = time.perf_counter() - t0
    rows.sort()
    with open(a.out, "wb") as f:
        pickle.dump({"args": vars(a), "rows": rows, "acc": acc, "elapsed": el}, f)
    n = len(rows)
    m = sum(r[2] for r in rows) / n
    se = (sum((r[2] - m) ** 2 for r in rows) / (n - 1) / n) ** 0.5 if n > 1 else 0
    fails = sum(r[5] for r in rows)
    decs = sum(r[6] for r in rows)
    print(f"hero={a.hero} tables={n} pts={m:.2f} se={se:.2f} failed={fails}/{decs} clone_fail={sum(r[7] for r in rows)} "
          f"elapsed={el:.0f}s ({n / el:.1f} tables/s)")


if __name__ == "__main__":
    main()
