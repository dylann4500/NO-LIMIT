"""Benchmark at endgame depth vs. the exact chart, and tournament value of adding the chart to our bot."""
import json, os, random, sys, math
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["CAND_PATH"] = "tuned_blend.json"; os.environ["CAND_TABLE"] = "1"
from engine import play_table, START
from run import make, evaluate
import engine

def duel(a):
    me, opp, S, n, seed = a
    random.seed(seed)
    w = 0
    sch = [(max(1, START // (2 * S)), START // S)]
    for i in range(n):
        h, v = make(me), make(opp)
        bots = [h, v] if i % 2 else [v, h]
        idx = 0 if i % 2 else 1
        e, nh, s = play_table(bots, sch)
        if idx in s and (len(s) == 1 or s[idx] > s[1 - idx]):
            w += 1
    return w

if __name__ == "__main__":
    b = json.load(open("tuned_blend.json"))["mu"]
    Hs = {"blend": dict(b, cls="table"), "blend+hu_def.4": dict(b, cls="table", hu_defend=0.4), "blend+nash15": dict(b, cls="nash", nash_max=15.0), "blend+nash25": dict(b, cls="nash", nash_max=25.0)}
    opp = dict(b, cls="purenash")
    with Pool(4) as p:
        print("Win% of a full match from equal stacks vs. the pure Nash jam-or-fold chart (blinds fixed; 4,000 matches, ±0.8):")
        for k, sp in Hs.items():
            row = []
            for S in (6, 10, 15, 20):
                r = sum(p.map(duel, [(sp, opp, S, 1000, x + S) for x in range(4)]))
                row.append(f"{S}BB {r/40:5.1f}%")
            print(" ", k.ljust(16), "  ".join(row), flush=True)
    P = ["gym", "top3", "linear", "wta"]
    for f in ["holdout", "stress_mix", "mirror", "all_mirror"]:
        r, _ = evaluate(Hs, field=f, payouts=P, tables=3000, procs=4, seed=99)
        print(f"== {f}")
        for k, row in r.items():
            print("  " + k.ljust(16) + "".join(f"{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
