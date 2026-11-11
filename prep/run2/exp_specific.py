"""Robust vs. point-table-specific tuning on holdout, plus improvement versus tuning time."""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate

if __name__ == "__main__":
    rob = json.load(open("tuned_robust.json"))
    H = {"default": {}, "robust": rob["mu"]}
    for p in ["top3", "linear", "steep", "wta"]:
        H["only_" + p] = json.load(open(f"tuned_{p}.json"))["mu"]
    P = ["top3", "linear", "steep", "wta"]
    for f in ["holdout", "holdout_soft", "typical", "mirror"]:
        r, _ = evaluate(H, field=f, payouts=P, tables=5000, seed=123)
        print(f"\n== field={f}\n" + "".ljust(12) + "".join(p.rjust(14) for p in P))
        for k, row in r.items():
            print(k.ljust(12) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
    # Tuning curve: each generation took about 14 s on 10 processes.
    H2 = {"default": {}}
    for g in [0, 1, 2, 3, 5, 7, 9, 11]:
        H2[f"gen{g}"] = rob["hist"][g]
    for f in ["holdout", "typical"]:
        r, _ = evaluate(H2, field=f, payouts=["top3", "steep"], tables=5000, seed=321)
        print(f"\n== tuning curve, field={f}")
        for k, row in r.items():
            print(k.ljust(10) + f"top3 {row['top3'][0]:6.2f}±{row['top3'][1]:4.2f}  steep {row['steep'][0]:6.2f}±{row['steep'][1]:4.2f}", flush=True)
