"""Q4: reveal policy on hands where we kept top pair (exactly one kept card pairs the top flop card).
exp_pairs = 1: our exposed card pairs the flop (i.e. we showed the top-pair card); 0: we hid it.
Outcome = forward ICM value from our first flop decision vs giving up there (d), and chips from hand start.
usage: python -I q4.py r6 [r5]"""
import sys
import numpy as np
import pandas as pd


def ci(x):
    return x.mean(), 1.96 * x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else np.nan


for prefix in sys.argv[1:]:
    d = pd.read_pickle(prefix + "_dec.pkl")
    f = d[d.street == 1].sort_values(["tid", "hand", "dec"]).groupby(["tid", "hand"]).head(1)
    print(f"\n#### {prefix}: first flop decisions {len(f)}; class mix:", f.hcls.value_counts(normalize=True).round(3).to_dict())
    for cl in ["top", "weak", "over", "strong", "air"]:
        g = f[f.hcls == cl]
        sh = (g.exp_pairs == 1).mean()
        print(f"  {cl:6s} n={len(g):6d} exposed a board-pairing card {sh:6.2%}")
    g = f[f.hcls == "top"]
    for hu in (True, False):
        gg = g[(g.nopp == 1) == hu]
        for e in (0, 1):
            x = gg[gg.exp_pairs == e]
            if len(x) >= 10:
                m, c = ci(x["d"]); mc, cc = ci(x["chips_bb"])
                auto = x["auto"].mean()
                print(f"  top pair {'HU' if hu else 'multi'} {'SHOWN' if e else 'hidden'}: n={len(x):6d} d={m:+.3f}±{c:.3f} pts  chips {mc:+.2f}±{cc:.2f}bb  "
                      f"first act {x.act.value_counts(normalize=True).round(2).to_dict()}  auto {auto:.1%}")
    # what villains do vs our hidden top pair: HU, we bet first / we check, villain response
    hu = d[(d.street == 1) & (d.nopp == 1)]
    print("  HU flop, our first decision with top pair hidden: act mix", g[(g.nopp == 1) & (g.exp_pairs == 0)].act.value_counts(normalize=True).round(3).to_dict())
