"""Fold-drift-adjusted class values, negative-cell scan, bet-vs-check, R5 vs R6 rate/quality split.
Fold drift: when we fold, the hand continues among others and our ICM drifts up (others' busts / chip
concentration); the static fold counterfactual misses that, so a fair action-vs-fold value is
  adj = d - r,  r = mean(U_after - V) over OUR FOLDS in the same context x alive bin (x HU/multi postflop).
usage: python -I analyze2.py r6 r5   (needs *_dec.pkl from analyze.py)"""
import sys
import numpy as np
import pandas as pd

pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500); pd.set_option("display.max_columns", 30)

FOLDCTX = {}
for lab in ["raise", "jam", "call"]:
    FOLDCTX[f"pf_unopened_{lab}"] = "pf_unopened_fold"
    FOLDCTX[f"pf_limped_{lab}"] = "pf_limped_fold"
    FOLDCTX[f"pf_vs1_{lab}"] = "pf_vs1_fold"
    FOLDCTX[f"pf_bb_vs1_{lab}"] = "pf_bb_vs1_fold"
    FOLDCTX[f"pf_cold_vs2_{lab}"] = "pf_cold_vs2_fold"
    FOLDCTX[f"pf_reraised_{lab}"] = "pf_reraised_fold"
FOLDCTX["pf_vsjam_call"] = "pf_vsjam_fold"
for s in "FTR":
    for a in ["call", "raise", "xr"]:
        FOLDCTX[f"{s}_{a}"] = f"{s}_fold"


def prep(prefix):
    d = pd.read_pickle(prefix + "_dec.pkl")
    d["hu"] = np.where(d["nopp"] == 1, "HU", "multi")
    d["fctx"] = d["label"].map(FOLDCTX)
    folds = d[d["act"] == "fold"].copy()
    folds["r"] = folds["d"]
    key = ["label", "alive_b", "hu"]
    r = folds.groupby(key, observed=True)["r"].agg(["mean", "size"]).reset_index().rename(columns={"label": "fctx", "mean": "r", "size": "nf"})
    d = d.merge(r, on=["fctx", "alive_b", "hu"], how="left")
    d["r"] = d["r"].fillna(0.0)
    d["adj"] = np.where(d["fctx"].notna(), d["d"] - d["r"], np.nan)
    return d


def summ(g, nt, col):
    n = len(g); m = g[col].mean(); se = g[col].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    pt = g.groupby("tid")[col].sum(); full = np.zeros(nt); full[: len(pt)] = pt.values
    tot = full.sum() / nt; se_t = full.std(ddof=1) / np.sqrt(nt)
    return pd.Series({"n": n, "mean": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se, "per_table": tot,
                      "pt_lo": tot - 1.96 * se_t, "pt_hi": tot + 1.96 * se_t, "flag": "n<300" if n < 300 else ""})


def main():
    p6, p5 = sys.argv[1], sys.argv[2]
    d6 = prep(p6); d5 = prep(p5)
    nt6 = d6["tid"].nunique(); nt5 = d5["tid"].nunique()
    print("fold drift r (mean U_after - V over our folds) R6 by context:")
    f6 = d6[d6.act == "fold"]
    print(f6.groupby(["label"])["d"].agg(["size", "mean"]).round(4).to_string())
    out = {}
    for nm, d, nt in (("R6", d6, nt6), ("R5", d5, nt5)):
        a = d[d["fctx"].notna()]
        t = a.groupby("cls").apply(lambda g: summ(g, nt, "adj"), include_groups=False)
        t = t[t.n >= 30].sort_values("per_table")
        out[nm] = t
        print(f"\n==== {nm}: drift-adjusted value vs fold (adj = d - r), {nt} tables")
        print(t.round(3).to_string())
    # ---- negative cell scan R6
    for nm, d, nt in (("R6", d6, nt6), ("R5", d5, nt5)):
        pre = d[d["fctx"].notna() & (d.street == 0)]
        c1 = pre.groupby(["cls", "alive_b", "stack_b", "pct_b"], observed=True).apply(lambda g: summ(g, nt, "adj"), include_groups=False)
        post = d[d["fctx"].notna() & (d.street > 0)]
        c2 = post.groupby(["cls", "hu", "hcls", "vexp"], observed=True).apply(lambda g: summ(g, nt, "adj"), include_groups=False)
        for title, c in (("preflop cells cls x alive x stack x pct", c1), ("postflop cells cls x HU x handclass x villain-exposed-pairs", c2)):
            neg = c[(c.n >= 100) & (c.hi < 0)].sort_values("per_table")
            print(f"\n==== {nm} significantly NEGATIVE {title} (n>=100, CI<0), sorted by per-table total")
            print(neg.head(25).round(3).to_string())
            print(f"     sum of all significantly negative cells per table: {neg.per_table.sum():.3f}")
            pos = c[(c.n >= 100)].sort_values("per_table", ascending=False)
            print(f"---- {nm} top positive {title}")
            print(pos.head(12).round(3).to_string())
        # coarser negative scan, single-dimension
        for by in (["cls", "alive_b"], ["cls", "pct_b"], ["cls", "stack_b"], ["cls", "pos"]):
            c = pre.groupby(by, observed=True).apply(lambda g: summ(g, nt, "adj"), include_groups=False)
            neg = c[(c.n >= 100) & (c.hi < 0)].sort_values("per_table")
            if len(neg):
                print(f"\n-- {nm} negative preflop {by}"); print(neg.round(3).to_string())
        for by in (["cls", "hu"], ["cls", "hu", "hcls"], ["cls", "hu", "vexp"]):
            c = post.groupby(by, observed=True).apply(lambda g: summ(g, nt, "adj"), include_groups=False)
            neg = c[(c.n >= 100) & (c.hi < 0)].sort_values("per_table")
            if len(neg):
                print(f"\n-- {nm} negative postflop {by}"); print(neg.round(3).to_string())
    # ---- bet vs check (not facing a bet), matched on street x HU x hand class x villain-exposed-pairs
    for nm, d, nt in (("R6", d6, nt6), ("R5", d5, nt5)):
        nf = d[(d.street > 0) & (d.facing == 0) & d.act.isin(["check", "raise", "jam"])].copy()
        nf["a"] = np.where(nf.act == "check", "check", "bet")
        g = nf.groupby(["street", "hu", "hcls", "vexp", "a"], observed=True)["d"].agg(["size", "mean", "var"]).unstack("a")
        g = g.dropna()
        g["diff"] = g[("mean", "bet")] - g[("mean", "check")]
        g["se"] = np.sqrt(g[("var", "bet")] / g[("size", "bet")] + g[("var", "check")] / g[("size", "check")])
        g["tot"] = g["diff"] * g[("size", "bet")] / nt
        print(f"\n==== {nm} bet minus check (matched cells), per street: weighted by our bets")
        for st in (1, 2, 3):
            x = g.loc[st]
            tot = x["tot"].sum(); se = np.sqrt(((x["se"] * x[("size", "bet")] / nt) ** 2).sum())
            print(f"  street {st}: bets {int(x[('size','bet')].sum())}  bet-check value {tot:+.3f} ±{1.96*se:.3f} pts/table")
        x = g.reset_index()
        x.columns = ["_".join(str(c) for c in col if c) if isinstance(col, tuple) else col for col in x.columns]
        x = x[(x["size_bet"] >= 200) & (x["size_check"] >= 200)].sort_values("tot")
        print("  most negative bet-vs-check cells:"); print(x.head(10).round(3).to_string())
    # ---- R5 vs R6, adjusted, rate vs quality
    a6 = out["R6"]; a5 = out["R5"]
    j = a6[["n", "mean", "per_table", "pt_lo", "pt_hi"]].join(a5[["n", "mean", "per_table", "pt_lo", "pt_hi"]], lsuffix="6", rsuffix="5", how="inner")
    j["diff"] = j["per_table6"] - j["per_table5"]
    j["diff_se"] = np.sqrt(((j.pt_hi6 - j.pt_lo6) / 3.92) ** 2 + ((j.pt_hi5 - j.pt_lo5) / 3.92) ** 2)
    j["quality"] = j["n6"] / nt6 * (j["mean6"] - j["mean5"])
    j["rate"] = (j["n6"] / nt6 - j["n5"] / nt5) * j["mean5"]
    j["rate6"] = j["n6"] / nt6; j["rate5"] = j["n5"] / nt5
    print("\n==== R6 - R5 drift-adjusted per-table value; quality = rate6*(mean6-mean5), rate = (rate6-rate5)*mean5")
    print(j.sort_values("diff").round(3).to_string())
    # call-jam by alive (ICM fix)
    for nm, d, nt in (("R6", d6, nt6), ("R5", d5, nt5)):
        g = d[d.cls == "PF call-jam"]; f = d[d.label == "pf_vsjam_fold"]
        print(f"\n-- {nm} call-jam by alive: calls, call rate, adj mean, per table")
        for ab in ["2", "3", "4", "5-6", "7-8"]:
            gg = g[g.alive_b == ab]; ff = f[f.alive_b == ab]
            s = summ(gg, nt, "adj")
            print(f"   alive {ab:4s} calls {len(gg):6d} folds {len(ff):6d} call% {len(gg)/(len(gg)+len(ff)):.1%}  adj {s['mean']:+.3f} [{s['lo']:+.3f},{s['hi']:+.3f}]  {s['per_table']:+.3f}/table")
            for pb in ["top10", "10-25", "25-45", "45+"]:
                g3 = gg[gg.pct_b == pb]; f3 = ff[ff.pct_b == pb]
                if len(g3) >= 50:
                    s = summ(g3, nt, "adj")
                    print(f"        {pb:6s} calls {len(g3):5d} call% {len(g3)/(len(g3)+len(f3)):.1%} adj {s['mean']:+.3f} [{s['lo']:+.3f},{s['hi']:+.3f}] {s['per_table']:+.3f}/table")


if __name__ == "__main__":
    main()
