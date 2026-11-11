"""Q1/Q3/Q4 from extract.py output: forward ICM value of each decision class vs folding at that moment.
usage: python -I analyze.py r6 [r5]"""
import sys
import numpy as np
import pandas as pd

pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500); pd.set_option("display.max_columns", 30)


def load(prefix):
    d = pd.read_csv(prefix + "_dec.csv.gz", low_memory=False)
    d["d"] = d["U_after"] - d["V"]
    d = d.sort_values(["tid", "hand", "dec"]).reset_index(drop=True)
    # incremental (additive) value: V_next - V, last decision of the hand: U_after - V
    nxt = d.groupby(["tid", "hand"])["V"].shift(-1)
    d["inc"] = np.where(nxt.isna(), d["U_after"] - d["V"], nxt - d["V"])
    d["pre"] = np.where(d["dec"] == 0, d["V"] - d["U_before"], 0.0)
    d["cls"] = d["label"].map(CLASSMAP).fillna(d["label"])
    d["alive_b"] = pd.cut(d["alive"], [0, 2, 3, 4, 6, 8], labels=["2", "3", "4", "5-6", "7-8"])
    d["stack_b"] = pd.cut(d["stack_bb"], [0, 12, 20, 40, 1e9], labels=["<=12", "12-20", "20-40", "40+"])
    d["pct_b"] = pd.cut(d["pct"], [-2, -0.5, 0.10, 0.25, 0.45, 1.01], labels=["na", "top10", "10-25", "25-45", "45+"])
    return d


CLASSMAP = {
    "pf_unopened_raise": "PF open", "pf_unopened_jam": "PF open-jam", "pf_unopened_call": "PF limp",
    "pf_limped_raise": "PF iso-raise", "pf_limped_jam": "PF iso-jam", "pf_limped_call": "PF overlimp",
    "pf_bboption_raise": "PF BB raise vs limp", "pf_bboption_jam": "PF BB jam vs limp",
    "pf_vs1_call": "PF flat (non-BB)", "pf_vs1_raise": "PF 3-bet (non-BB)", "pf_vs1_jam": "PF re-jam (non-BB)",
    "pf_bb_vs1_call": "PF BB defend call", "pf_bb_vs1_raise": "PF BB 3-bet", "pf_bb_vs1_jam": "PF BB jam vs open",
    "pf_vsjam_call": "PF call-jam", "pf_cold_vs2_call": "PF cold call vs 3bet", "pf_cold_vs2_raise": "PF cold 4bet",
    "pf_cold_vs2_jam": "PF cold 4bet-jam", "pf_reraised_call": "PF call vs reraise", "pf_reraised_raise": "PF 4bet",
    "pf_reraised_jam": "PF jam vs reraise",
    "F_bet": "Flop bet", "F_call": "Flop call", "F_raise": "Flop raise", "F_xr": "Flop check-raise", "F_check": "Flop check",
    "T_bet": "Turn bet", "T_call": "Turn call", "T_raise": "Turn raise", "T_xr": "Turn check-raise", "T_check": "Turn check",
    "R_bet": "River bet", "R_call": "River call", "R_raise": "River raise", "R_xr": "River check-raise", "R_check": "River check",
}


def summ(g, nt, col="d"):
    n = len(g)
    m = g[col].mean()
    se = g[col].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    # clustered (by table) SE of the per-table total
    pt = g.groupby("tid")[col].sum()
    tot = pt.sum() / nt
    full = np.zeros(nt); full[: len(pt)] = pt.values
    se_tot = full.std(ddof=1) / np.sqrt(nt)
    return pd.Series({"n": n, "mean": m, "lo": m - 1.96 * se, "hi": m + 1.96 * se, "per_table": tot,
                      "pt_lo": tot - 1.96 * se_tot, "pt_hi": tot + 1.96 * se_tot, "inc_per_table": g["inc"].sum() / nt,
                      "flag": "n<300" if n < 300 else ""})


def classes(d, nt, title):
    print(f"\n==== {title}: forward value vs fold (ICM points), {nt} tables, mean final pts {d.groupby('tid')['final_pts'].first().mean():.3f}")
    nonfold = d[~d["act"].isin(["fold"]) & (d["label"] != "nodecision")]
    t = nonfold.groupby("cls").apply(lambda g: summ(g, nt), include_groups=False)
    t = t[t["n"] >= 30].sort_values("per_table")
    print(t.round(3).to_string())
    # additive check
    tot_inc = d["inc"].sum() / nt + d["pre"].sum() / nt
    print(f"additive check: sum(inc)+sum(pre) per table = {tot_inc:.3f}  (= mean final - 12.5 = {d.groupby('tid')['final_pts'].first().mean() - 12.5:.3f})")
    fold_inc = d[d["act"] == "fold"].groupby("street")["inc"].sum() / nt
    print("fold residual inc per table by street:", fold_inc.round(3).to_dict(), " pre-decision (blinds etc):", round(d["pre"].sum() / nt, 3),
          " no-decision hands:", round(d.loc[d.label == "nodecision", "inc"].sum() / nt, 3))
    return t


def strat(d, nt, cls, by, minn=30):
    g = d[d["cls"] == cls]
    t = g.groupby(by, observed=True).apply(lambda x: summ(x, nt), include_groups=False)
    t = t[t["n"] >= minn]
    return t


def main():
    p6 = sys.argv[1]
    d6 = load(p6)
    nt6 = d6["tid"].nunique()
    t6 = classes(d6, nt6, p6)
    d5 = None
    if len(sys.argv) > 2:
        d5 = load(sys.argv[2]); nt5 = d5["tid"].nunique(); t5 = classes(d5, nt5, sys.argv[2])
        both = t6[["n", "mean", "per_table", "pt_lo", "pt_hi"]].join(t5[["n", "mean", "per_table", "pt_lo", "pt_hi"]], lsuffix="_6", rsuffix="_5", how="outer")
        both["diff_pt"] = both["per_table_6"] - both["per_table_5"]
        se = np.sqrt(((both["pt_hi_6"] - both["pt_lo_6"]) / 3.92) ** 2 + ((both["pt_hi_5"] - both["pt_lo_5"]) / 3.92) ** 2)
        both["diff_lo"] = both["diff_pt"] - 1.96 * se; both["diff_hi"] = both["diff_pt"] + 1.96 * se
        print("\n==== R6 vs R5 per-table forward value by class (sorted by diff)")
        print(both.sort_values("diff_pt").round(3).to_string())
        f6 = d6.groupby("tid")["final_pts"].first(); f5 = d5.groupby("tid")["final_pts"].first()
        print(f"points/table R6 {f6.mean():.3f} ±{1.96*f6.std()/np.sqrt(len(f6)):.3f} (n={len(f6)})  R5 {f5.mean():.3f} ±{1.96*f5.std()/np.sqrt(len(f5)):.3f} (n={len(f5)}) "
              f"diff {f6.mean()-f5.mean():+.3f} ±{1.96*np.sqrt(f6.var()/len(f6)+f5.var()/len(f5)):.3f}")
        # additive decomposition by class, R6 - R5
        a6 = d6.groupby("cls")["inc"].sum() / nt6; a5 = d5.groupby("cls")["inc"].sum() / nt5
        a = pd.DataFrame({"inc6": a6, "inc5": a5}).fillna(0); a["diff"] = a["inc6"] - a["inc5"]
        a.loc["(pre-decision blinds)"] = [d6["pre"].sum() / nt6, d5["pre"].sum() / nt5, d6["pre"].sum() / nt6 - d5["pre"].sum() / nt5]
        print("\n==== additive (incremental) decomposition, per table, R6 vs R5 (sum = points - 12.5)")
        print(a.sort_values("diff").round(3).to_string())
        print("sum inc6", round(a["inc6"].sum(), 3), "sum inc5", round(a["inc5"].sum(), 3))
    # drilldowns for R6
    for cls in ["PF call-jam", "PF open-jam", "PF re-jam (non-BB)", "PF BB jam vs open", "PF open", "PF BB defend call", "PF flat (non-BB)", "PF 3-bet (non-BB)", "PF BB 3-bet"]:
        for by in (["alive_b"], ["stack_b"], ["pct_b"], ["pos"]):
            t = strat(d6, nt6, cls, by)
            if len(t):
                print(f"\n-- {cls} by {by[0]}"); print(t[["n", "mean", "lo", "hi", "per_table", "flag"]].round(3).to_string())
    for cls in ["Flop call", "Turn call", "River call", "Flop raise", "Turn raise", "River raise", "Flop check-raise", "Turn check-raise", "Flop bet", "Turn bet", "River bet"]:
        g = d6[d6["cls"] == cls].copy(); g["hu"] = np.where(g["nopp"] == 1, "HU", "multi")
        for by in (["hu", "hcls"], ["hu", "vexp"]):
            t = g.groupby(by, observed=True).apply(lambda x: summ(x, nt6), include_groups=False)
            t = t[t["n"] >= 30]
            print(f"\n-- {cls} by {by}"); print(t[["n", "mean", "lo", "hi", "per_table", "flag"]].round(3).to_string())
    d6.to_pickle(p6 + "_dec.pkl")
    if d5 is not None:
        d5.to_pickle(sys.argv[2] + "_dec.pkl")


if __name__ == "__main__":
    main()
