"""E4/E5/E6: ablations answering how much each component is worth.
- rollouts: precision of postflop equity
- adapt: within-table opponent modelling
- simplifications: preflop-only jam bots, and no-bluff
"""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate
from hero import DEFAULT

if __name__ == "__main__":
    base = {}
    try:
        base = json.load(open(sys.argv[1]))["mu"] if len(sys.argv) > 1 else {}
    except Exception:
        pass
    V = {
        "base_r40": dict(base),
        "r5": dict(base, rollouts=5),
        "r15": dict(base, rollouts=15),
        "r100": dict(base, rollouts=100),
        "noadapt": dict(base, adapt=0),
        "nobluff": dict(base, bluff_freq=0.0),
        "noicm": dict(base, icm_margin=0.0),
        "alwaysjamshort_30m": dict(base, jam_m=30.0),
        "jam_m_6": dict(base, jam_m=6.0),
    }
    payouts = ["top3", "linear", "steep", "wta"]
    for f in ["typical", "strong", "aggro", "passive"]:
        r, _ = evaluate(V, field=f, payouts=payouts, tables=6000)
        print(f"\n== {f}")
        print("".ljust(20) + "".join(p.rjust(14) for p in payouts))
        for k, row in r.items():
            print(k.ljust(20) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in payouts), flush=True)
