"""Tuned vs. default vs. baselines, on seeds and fields unused in tuning. Field `holdout` is new opponents."""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate
from engine import SCHEDULE_DEFAULT

SCHEDS = {
    "assumed": SCHEDULE_DEFAULT,
    "slow": [(10,20),(15,30),(20,40),(25,50),(30,60),(40,80),(50,100),(75,150)],
    "double": [(10,20),(20,40),(40,80),(80,160),(160,320),(320,640),(640,1280),(1280,2560)],
}
if __name__ == "__main__":
    tuned = json.load(open(sys.argv[1]))["mu"]
    H = {"tuned": dict(tuned), "default": {}, "tag": "tag", "nit": "nit", "shortfold": "shortfold", "fold": "fold"}
    P = ["top3", "steep", "linear", "wta"]
    for s, sch in SCHEDS.items():
        for f in (["holdout", "holdout_soft", "early_buggy", "mirror", "all_mirror"] if s == "assumed" else ["typical", "holdout"]):
            r, hands = evaluate(H, field=f, payouts=P, tables=4000, seed=99, schedule=sch)
            print(f"\n== sched={s} field={f} hands/table={hands/(4000*len(H)):.0f}")
            print("".ljust(11) + "".join(p.rjust(14) for p in P))
            for k, row in r.items():
                print(k.ljust(11) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
