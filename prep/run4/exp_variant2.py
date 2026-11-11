"""Lookup vs. the live Monte Carlo that actually fits in 1 ms, per variant. Lab parameters unchanged."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import evaluate
if __name__ == "__main__":
    mu = json.load(open("tuned_robust.json"))["mu"]
    v = os.environ.get("POKER_VARIANT", "holdem")
    feas = int(sys.argv[1])
    tables = int(sys.argv[2])
    H = {"lookup": dict(mu, cls="table"), f"mc_r{feas}": dict(mu, rollouts=feas), "mc_r40": dict(mu), "tag": "tag"}
    r, _ = evaluate(H, field="holdout", payouts=["top3", "steep"], tables=tables, procs=2, seed=71)
    print("== variant", v)
    for k, row in r.items():
        print("  " + k.ljust(10) + f"top3 {row['top3'][0]:6.2f}±{row['top3'][1]:4.2f}  steep {row['steep'][0]:6.2f}±{row['steep'][1]:4.2f}", flush=True)
