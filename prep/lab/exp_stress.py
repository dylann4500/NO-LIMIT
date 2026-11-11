"""Is "open wide" an artifact of opponents who don't punish it? Same bot with narrower opens and larger opens."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import evaluate
if __name__ == "__main__":
    m = dict(json.load(open("tuned_lookup.json"))["mu"], cls="table")
    H = {"tuned": m, "opens_x0.75": dict(m, open_a=m["open_a"] * .75, open_b=m["open_b"] * .75),
         "opens_x0.5": dict(m, open_a=m["open_a"] * .5, open_b=m["open_b"] * .5),
         "open_size_3": dict(m, open_size=3.0), "tag": "tag", "nit": "nit", "shortfold": "shortfold", "fold": "fold"}
    P = ["top3", "steep", "linear"]
    for f in ["stress_3bet", "stress_trap", "stress_mix"]:
        r, hands = evaluate(H, field=f, payouts=P, tables=2000, procs=2, seed=41)
        print(f"== {f} hands/table={hands/(2000*len(H)):.0f}")
        for k, row in r.items():
            print("  " + k.ljust(13) + "".join(f"{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
