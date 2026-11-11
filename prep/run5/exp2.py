"""Evaluation stages for the driver."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import evaluate, PAYOUTS
P = ["top3", "steep", "linear", "wta"]

def L(name):
    return json.load(open(name))["mu"]

def T(d, **kw):
    return dict(d, cls="table", **kw)

def show(H, f, tables, seed, payouts=P):
    r, hands = evaluate(H, field=f, payouts=payouts, tables=tables, seed=seed)
    print(f"\n== field={f} hands/table={hands/(tables*len(H)):.0f}\n" + "".ljust(16) + "".join(p.rjust(14) for p in payouts))
    for k, row in r.items():
        print(k.ljust(16) + "".join(f"{row[p][0]:8.2f}±{row[p][1]:4.2f} " for p in payouts), flush=True)
    return r

if __name__ == "__main__":
    s = sys.argv[1]
    if s == "compare":
        H = {"lookup_tuned": T(L("tuned_lookup.json")), "lookup_mcparams": T(L("tuned_robust.json")), "mc_r40": L("tuned_robust.json"), "tag": "tag"}
        for f in ["holdout", "holdout_soft", "mirror", "typical", "strong", "aggro", "passive"]:
            show(H, f, 6000, 4001)
    elif s == "sensitivity":
        # One parameter at a time, x0.6 and x1.4, against the mean of holdout and mirror-style fields.
        from tune import KEYS, SEARCH
        mu = L("tuned_lookup.json")
        H = {"BASE": T(mu)}
        for k in KEYS:
            if k in mu:
                lo, hi = SEARCH[k]
                H[k + ":-"] = T(mu, **{k: max(lo, mu[k] * 0.6)})
                H[k + ":+"] = T(mu, **{k: min(hi, mu[k] * 1.4)})
        res = {}
        for f in ["holdout", "strong"]:
            r, _ = evaluate(H, field=f, payouts=["top3", "steep"], tables=2500, seed=5150)
            for k, row in r.items():
                res.setdefault(k, []).append(row["top3"][0])
        base = sum(res["BASE"]) / 2
        print(f"base mean top3 {base:.2f}; about ±0.4 noise per mean")
        imp = {}
        for k in mu:
            if k + ":-" in res:
                a, b = sum(res[k + ":-"]) / 2 - base, sum(res[k + ":+"]) / 2 - base
                imp[k] = (min(a, b), a, b)
        for k, (w, a, b) in sorted(imp.items(), key=lambda x: x[1][0]):
            print(f"{k:18} value {mu[k]:7.3f}  x0.6: {a:+6.2f}  x1.4: {b:+6.2f}")
    elif s == "specific":
        H = {"robust": T(L("tuned_lookup.json"))}
        for p in P:
            H["only_" + p] = T(L(f"tuned_lookup_{p}.json"))
        for f in ["holdout", "typical", "mirror"]:
            show(H, f, 4000, 6006)
        h = json.load(open("tuned_lookup.json"))["hist"]
        H2 = {f"gen{g}": T(h[g]) for g in [0, 1, 2, 3, 5, 8, 11]}
        H2["start_mc_params"] = T(L("tuned_robust.json"))
        show(H2, "holdout", 4000, 6007, ["top3", "steep"])
        # Tuning from a bad start shows how much a short tune buys at the event.
        h3 = json.load(open("tuned_robust.json"))["hist"]
        H3 = {"default": {"cls": "table"}}
        H3.update({f"cold_gen{g}": T(h3[g]) for g in [0, 1, 2, 3, 5, 8, 11]})
        show(H3, "holdout", 4000, 6008, ["top3", "steep"])
    elif s == "v3":
        base, v3 = L("tuned_lookup.json"), L("tuned_lookup_v3.json")
        print({k: round(v3[k], 3) for k in ["bully", "cbet_pfr", "cap_tight"]})
        H = {"base": T(base), "v3_all": T(v3)}
        for k in ["bully", "cbet_pfr", "cap_tight"]:
            H["base+" + k] = T(base, **{k: v3[k]})
        for f in ["holdout", "mirror", "typical", "aggro"]:
            show(H, f, 6000, 7007)
    elif s == "meta":
        import subprocess
        names = {"r0": "tuned_lookup.json", "r1": "tuned_meta1.json", "r2": "tuned_meta2.json", "r3": "tuned_meta3.json"}
        code = """
import json, os, sys
sys.path.insert(0, '.')
from run import evaluate
if __name__ == '__main__':
    names = json.loads(os.environ['NAMES'])
    H = {k: dict(json.load(open(v))['mu'], cls='table') for k, v in names.items()}
    H['tag'] = 'tag'
    r, _ = evaluate(H, field=os.environ['F'], payouts=['top3', 'steep', 'linear'], tables=4000, seed=88)
    print(json.dumps({k: {q: round(v[q][0], 2) for q in v} for k, v in r.items()}))
"""
        for f, cands in [("all_mirror", names), ("mirror", names), ("holdout", {"r0": names["r0"]}), ("typical", {"r0": names["r0"]})]:
            for c, path in cands.items():
                env = dict(os.environ, CAND_PATH=path, CAND_TABLE="1", NAMES=json.dumps(names), F=f)
                o = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
                print(f"field={f} cand={c}: {o.stdout.strip() or o.stderr[-300:]}", flush=True)
        for k, v in names.items():
            m = L(v)
            print(k, {x: round(m[x], 3) for x in ["open_a", "open_b", "hu_open", "jam_m", "jam_scale", "call_jam", "call_open", "threebet", "call_margin", "value_eq", "bluff_freq", "bet_frac"]})
