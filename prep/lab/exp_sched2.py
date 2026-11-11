import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import evaluate
from engine import SCHEDULE_DEFAULT
S = {"assumed": SCHEDULE_DEFAULT,
     "slow": [(10,20),(15,30),(20,40),(25,50),(30,60),(40,80),(50,100),(75,150)],
     "double": [(10,20),(20,40),(40,80),(80,160),(160,320),(320,640),(640,1280),(1280,2560)],
     "exhibit_like": [(10,20),(20,40),(30,60),(50,100),(75,150),(100,200),(150,300),(200,400)]}
if __name__ == "__main__":
    m = dict(json.load(open("tuned_lookup.json"))["mu"], cls="table")
    H = {"lookup": m, "tag": "tag", "nit": "nit", "fold": "fold"}
    P = ["top3", "steep", "linear"]
    for s, sch in S.items():
        for f in ["holdout", "strong"]:
            r, hands = evaluate(H, field=f, payouts=P, tables=1500, procs=2, seed=64, schedule=sch)
            print(f"== {s} {f} hands/table={hands/(1500*len(H)):.0f}: " + "  ".join(f"{k} " + "/".join(f"{row[p][0]:.1f}" for p in P) for k, row in r.items()), flush=True)
