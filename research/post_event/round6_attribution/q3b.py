"""R5 vs R6: how the field answered our preflop opens (non-jam, first in) and how often BB-jam spots arose.
usage: python -I q3b.py r6 r5"""
import sys
import numpy as np
import pandas as pd
for p in sys.argv[1:]:
    d = pd.read_pickle(p + "_dec.pkl")
    nt = d.tid.nunique()
    d["nxt_label"] = d.groupby(["tid", "hand"])["label"].shift(-1)
    d["nxt_street"] = d.groupby(["tid", "hand"])["street"].shift(-1)
    o = d[d.label == "pf_unopened_raise"].copy()
    o["out"] = np.select([o.nxt_label.isna(), o.nxt_street == 0, o.nxt_street > 0], ["stole (all fold)", "faced 3bet/jam", "called, saw flop"], "other")
    o["pct_b"] = o["pct_b"].astype(str)
    print(f"\n{p}: {len(o)} opens ({len(o)/nt:.2f}/table)")
    t = o.groupby("out").agg(share=("d", lambda x: len(x) / len(o)), d_mean=("d", "mean"), chips=("chips_bb", "mean"))
    print(t.round(3).to_string())
    for pb in ["top10", "10-25", "25-45"]:
        x = o[o.pct_b == pb]
        print(f"  {pb:6s} n={len(x):6d} " + " ".join(f"{k} {v:.1%}" for k, v in x.out.value_counts(normalize=True).items()) + f"  d {x.d.mean():+.3f}")
    bb = d[d.label.str.startswith("pf_bb_vs1_")]
    print(f"  BB facing single non-all-in open: {len(bb)/nt:.2f}/table; our jam share {bb.label.eq('pf_bb_vs1_jam').mean():.1%}")
    oj = d[d.label == "pf_unopened_jam"]
    print(f"  open-jams {len(oj)/nt:.2f}/table, avg stack {oj.stack_bb.mean():.1f}bb; alive-2 share {(oj.alive==2).mean():.1%}")
    h = d[d.dec == 0]
    print(f"  hands per table {len(h)/nt:.1f}; share of hands at alive<=3 {(h.alive<=3).mean():.1%}; mean stack bb {h.stack_bb.median():.1f} (median)")
