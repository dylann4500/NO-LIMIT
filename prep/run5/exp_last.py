import json, sys
sys.path.insert(0, ".")
from run import evaluate
if __name__ == "__main__":
    mu = json.load(open("tuned_robust.json"))["mu"]
    which = sys.argv[1]
    if which == "table":
        H = {"mc_r40": dict(mu), "table": dict(mu, cls="table"), "mc_r15": dict(mu, rollouts=15)}
    else:
        H = {"base": dict(mu), "eqcall": dict(mu, eqcall=1.0), "eqcall_nobluff": dict(mu, eqcall=1.0, bluff_freq=0.0), "nobluff": dict(mu, bluff_freq=0.0)}
    P = ["top3", "steep", "linear"]
    for f in ["holdout", "mirror", "typical"]:
        r, _ = evaluate(H, field=f, payouts=P, tables=2000, procs=5, seed=2024)
        print(f"== {which} field={f}")
        for k, row in r.items():
            print("  " + k.ljust(15) + "".join(f"{p}:{row[p][0]:7.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
