"""E1: every archetype and the default candidate, across field guesses and point tables."""
import sys, json, time
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate, PAYOUTS
from field import ARCHETYPES, FIELDS

if __name__ == "__main__":
    heroes = {k: k for k in ARCHETYPES}
    heroes["HERO"] = {}
    N = 3000
    out = {}
    payouts = list(PAYOUTS)
    for f in FIELDS:
        t = time.time()
        r, hands = evaluate(heroes, field=f, payouts=payouts, tables=N)
        out[f] = r
        print(f"\n== field {f}  ({hands/(N*len(heroes)):.0f} hands/table, {time.time()-t:.0f}s)")
        print("".ljust(10) + "".join(p.rjust(14) for p in payouts))
        for h, row in sorted(r.items(), key=lambda x: -x[1]["top3"][0]):
            print(h.ljust(10) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in payouts), flush=True)
    json.dump(out, open("results_matrix.json", "w"))
