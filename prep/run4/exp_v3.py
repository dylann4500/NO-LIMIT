"""Do the optional v3 features earn their place on fields the tuner never saw?"""
import sys, json
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from run import evaluate
if __name__ == "__main__":
    base = json.load(open("tuned_robust.json"))["mu"]
    v3 = dict(json.load(open("tuned_v3.json"))["mu"], eqcall=1.0)
    H = {"v2_robust": base, "v3_tuned": v3, "v3_nobluff": dict(v3, bluff_freq=0.0), "v3_noeqcall": dict(v3, eqcall=0.0),
         "v2+eqcall": dict(base, eqcall=1.0, eqcall_margin=v3["eqcall_margin"], vwidth_mult=v3["vwidth_mult"])}
    for k in ["bully", "cbet_pfr", "cap_tight"]:
        H["v2+" + k] = dict(base, **{k: v3[k]})
    P = ["top3", "steep", "linear", "wta"]
    print({k: round(v3[k], 3) for k in ["bully", "cbet_pfr", "cap_tight", "eqcall_margin", "vwidth_mult"]})
    for f in ["holdout", "holdout_soft", "mirror", "typical"]:
        r, _ = evaluate(H, field=f, payouts=P, tables=8000, seed=909)
        print(f"\n== field={f}\n" + "".ljust(14) + "".join(p.rjust(14) for p in P))
        for k, row in r.items():
            print(k.ljust(14) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in P), flush=True)
    # Heads-up check against the opponents that exposed the weakness.
    from exp_hu import hu
    from multiprocessing import Pool
    with Pool(10) as pool:
        for name, params in [("v2_robust", base), ("v3_tuned", v3)]:
            for o in ["maniac", "random", "jam20", "allin", "minraise", "tag", "shortfold"]:
                r = sum(pool.map(hu, [(o, params, 100, s) for s in range(10)]))
                print(f"HU {name:10} vs {o:9} {r/10:5.1f}%", flush=True)
