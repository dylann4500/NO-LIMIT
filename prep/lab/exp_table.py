"""Do we need live Monte Carlo? Live MC at several budgets vs. the small lookup model."""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate
if __name__ == "__main__":
    mu = json.load(open("tuned_robust.json"))["mu"]
    H = {"mc_r5": dict(mu, rollouts=5), "mc_r15": dict(mu, rollouts=15), "mc_r40": dict(mu, rollouts=40), "mc_r150": dict(mu, rollouts=150),
         "table": dict(mu, cls="table")}
    try:
        H["table_tuned"] = dict(json.load(open("tuned_tablebot.json"))["mu"], cls="table")
    except Exception as e:
        print("no table-tuned params", e)
    P = ["top3", "steep", "linear", "wta"]
    for f in ["holdout", "holdout_soft", "typical", "strong", "mirror"]:
        r, _ = evaluate(H, field=f, payouts=P, tables=8000, seed=555)
        print(f"\n== field={f}\n" + "".ljust(13) + "".join(p.rjust(14) for p in P))
        for k, row in r.items():
            print(k.ljust(13) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
